"""Mininet-style network building on top of Containerlab and Open vSwitch.

The class and method names mirror Mininet on purpose (addHost, addSwitch,
addLink, start, pingAll, CLI, ...) so the course's existing scripts port with
only their import lines changed. Under the hood:

  * every host is a Containerlab `linux` node (a small Alpine container with
    no management network, so its only interfaces are the ones you link),
  * every switch is an Open vSwitch bridge that Containerlab plugs into,
  * every link is a veth pair created by Containerlab,
  * controllers are plain OpenFlow endpoints (usually Ryu started with
    `csci60 ryu ...`) that the bridges connect to.
"""

import json
import os
import re
import shutil
import threading
import time

from . import util
from .util import info, run, sh

DEFAULT_CONTROLLER_PORT = 6633


def _container(lab, node):
    return "clab-%s-%s" % (lab, node)


class Node(object):
    """Something that has interfaces: a host or a switch."""

    kind = "node"

    def __init__(self, net, name):
        self.net = net
        self.name = name
        self.intfs = []          # interface names in creation order
        self.next_port = 0       # next interface index

    def newIntf(self):
        idx = self.next_port
        self.next_port += 1
        intf = "%s-eth%d" % (self.name, idx)
        self.intfs.append(intf)
        return intf

    def defaultIntf(self):
        return self.intfs[0] if self.intfs else None

    def __repr__(self):
        return "<%s %s: %s>" % (self.__class__.__name__, self.name,
                                ",".join(self.intfs) or "no interfaces")

    __str__ = __repr__


class Host(Node):
    kind = "host"

    def __init__(self, net, name, ip=None, mac=None, defaultRoute=None):
        Node.__init__(self, net, name)
        self.params_ip = ip
        self.params_mac = mac
        self.defaultRoute = defaultRoute
        self.pending_ips = {}
        self.ip_auto = None

    @property
    def container(self):
        return _container(self.net.name, self.name)

    def cmd(self, command, check=False):
        """Run a shell command inside the host and return its output."""
        proc = run(["docker", "exec", self.container, "sh", "-c", command],
                   check=check)
        return (proc.stdout or "") + (proc.stderr or "")

    def popen_args(self, command, tty=False):
        args = ["docker", "exec"]
        if tty:
            args.append("-it")
        return args + [self.container, "sh", "-c", command]

    def setIP(self, *args, **kwargs):
        """Set an IPv4 address on an interface.

        Accepts every form used in the course material:
            h1.setIP('10.0.0.1', 24)
            h1.setIP('10.0.0.1/24')
            h1.setIP('h1-eth0', '10.0.0.1', 24)      (Mininet 2.0 order)
        Called before net.start(), the address is applied during start-up.
        """
        intf, ip = _parse_setip(self, args, kwargs)
        if not self.net.built:
            self.pending_ips[intf] = ip
            return
        self.cmd("ip addr flush dev %s && ip addr add %s dev %s" %
                 (intf, ip, intf), check=True)

    def setMAC(self, mac, intf=None):
        intf = intf or self.defaultIntf()
        if not self.net.built:
            self.params_mac = mac
            return
        self.cmd("ip link set dev %s address %s" % (intf, mac), check=True)

    def IP(self, intf=None):
        intf = intf or self.defaultIntf()
        if not intf:
            return None
        out = self.cmd("ip -4 -o addr show dev %s" % intf)
        m = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", out)
        return m.group(1) if m else None

    def MAC(self, intf=None):
        intf = intf or self.defaultIntf()
        out = self.cmd("cat /sys/class/net/%s/address" % intf).strip()
        return out or None


class Switch(Node):
    kind = "switch"

    def __init__(self, net, name, dpid=None, failMode=None,
                 protocols="OpenFlow10"):
        Node.__init__(self, net, name)
        self.next_port = 1       # Mininet numbers switch ports from 1
        self.dpid = dpid or self._default_dpid(name)
        self.failMode = failMode
        self.protocols = protocols
        self.controllers = None  # None = "all controllers of the network"
        self.pending_ips = {}

    @staticmethod
    def _default_dpid(name):
        digits = re.findall(r"\d+", name)
        num = int(digits[-1]) if digits else 1
        return "%016x" % num

    def start(self, controllers):
        """Attach this switch to a list of controllers (Mininet's s.start)."""
        self.controllers = [c.name for c in controllers]
        if self.net.built:
            self.net._apply_controllers(self)
            self.net._save_state()

    def cmd(self, command, check=False):
        """Commands on a switch run on the server, like in Mininet."""
        proc = sh(command, check=check)
        return (proc.stdout or "") + (proc.stderr or "")

    def setIP(self, *args, **kwargs):
        """Give a switch port an IP address (it lives on the server)."""
        intf, ip = _parse_setip(self, args, kwargs)
        if not self.net.built:
            self.pending_ips[intf] = ip
            return
        sh("ip addr flush dev %s && ip addr add %s dev %s" % (intf, ip, intf))

    def dpctl(self, args):
        return sh("ovs-ofctl -O %s %s %s" % (self.protocols, args, self.name),
                  check=False).stdout


class Controller(object):
    """Mininet's default controller: every switch acts as a learning switch.

    No controller process is needed. Open vSwitch runs in "standalone" mode,
    which forwards like an ordinary Ethernet switch.
    """

    kind = "controller"
    remote = False

    def __init__(self, name, **_ignored):
        self.name = name
        self.ip = None
        self.port = None

    def target(self):
        return None

    def __repr__(self):
        return "<Controller %s: built-in learning switch>" % self.name

    __str__ = __repr__


class RemoteController(Controller):
    """An external OpenFlow controller such as Ryu (`csci60 ryu ...`)."""

    remote = True

    def __init__(self, name, ip="127.0.0.1", port=DEFAULT_CONTROLLER_PORT,
                 **_ignored):
        Controller.__init__(self, name)
        self.ip = ip
        self.port = int(port)

    def target(self):
        return "tcp:%s:%d" % (self.ip, self.port)

    def __repr__(self):
        return "<RemoteController %s: %s:%d>" % (self.name, self.ip, self.port)

    __str__ = __repr__


class Link(object):
    def __init__(self, node1, intf1, node2, intf2, params):
        self.node1, self.intf1 = node1, intf1
        self.node2, self.intf2 = node2, intf2
        self.params = params

    def __repr__(self):
        return "%s<->%s" % (self.intf1, self.intf2)


class Network(object):
    """A Mininet-like network. `Mininet` is an alias for this class."""

    def __init__(self, name="csci60", controller=None, autoSetMacs=False,
                 ipBase="10.0.0.0/8", topo=None, link=None, host=None,
                 switch=None, build=True, **_ignored):
        if not re.match(r"^[a-z0-9][a-z0-9-]{0,20}$", name):
            util.die("network name %r: use lowercase letters, digits, '-'"
                     % name)
        self.name = name
        self.autoSetMacs = autoSetMacs
        self.ipBase = ipBase
        self.hosts = []
        self.switches = []
        self.controllers = []
        self.links = []
        self.nameToNode = {}
        self.started = False
        self.built = False
        self._next_ip = 1
        self._default_controller = controller
        self.dir = os.path.join(util.LABS_ROOT, name)
        if topo is not None:
            topo.build(self)

    # ----- building -------------------------------------------------------

    def _register(self, node):
        if node.name in self.nameToNode:
            util.die("duplicate node name %s" % node.name)
        self.nameToNode[node.name] = node
        return node

    def addHost(self, name, ip=None, mac=None, defaultRoute=None, **_ignored):
        host = Host(self, name, ip=ip, mac=mac, defaultRoute=defaultRoute)
        self.hosts.append(host)
        return self._register(host)

    def addSwitch(self, name, dpid=None, failMode=None, protocols="OpenFlow10",
                  **_ignored):
        switch = Switch(self, name, dpid=dpid, failMode=failMode,
                        protocols=protocols)
        self.switches.append(switch)
        return self._register(switch)

    def addController(self, name="c0", controller=None, ip=None, port=None,
                      defaultIP=None, **_ignored):
        """Add a controller, with Mininet's rules.

        addController('c0')                              built-in learning switch
        addController('c0', controller=RemoteController) Ryu on 127.0.0.1:6633
        addController('c1', controller=RemoteController, port=6644)
        """
        kind = controller or self._default_controller
        if kind is None and (ip or port or defaultIP):
            kind = RemoteController
        if kind is RemoteController or (isinstance(kind, type) and
                                        issubclass(kind, RemoteController)):
            ctrl = RemoteController(name, ip=ip or defaultIP or "127.0.0.1",
                                    port=port or DEFAULT_CONTROLLER_PORT)
        else:
            ctrl = Controller(name)
        self.controllers.append(ctrl)
        self.nameToNode[name] = ctrl
        return ctrl

    def addLink(self, node1, node2, bw=None, delay=None, loss=None,
                max_queue_size=None, **_ignored):
        node1 = self.get(node1) if isinstance(node1, str) else node1
        node2 = self.get(node2) if isinstance(node2, str) else node2
        params = {}
        if bw is not None:
            params["bw"] = bw
        if delay is not None:
            params["delay"] = delay
        if loss is not None:
            params["loss"] = loss
        if max_queue_size is not None:
            params["max_queue_size"] = max_queue_size
        link = Link(node1, node1.newIntf(), node2, node2.newIntf(), params)
        self.links.append(link)
        return link

    def get(self, *names):
        nodes = [self.nameToNode[n] for n in names]
        return nodes[0] if len(nodes) == 1 else nodes

    def __getitem__(self, name):
        return self.nameToNode[name]

    def __contains__(self, name):
        return name in self.nameToNode

    # ----- lifecycle ------------------------------------------------------

    def _clab_topology(self):
        nodes = {}
        for h in self.hosts:
            nodes[h.name] = {"kind": "linux", "image": util.HOST_IMAGE,
                             "network-mode": "none"}
        for s in self.switches:
            nodes[s.name] = {"kind": "ovs-bridge"}
        # mtu 1500 like Mininet and real Ethernet (containerlab defaults to 9500)
        links = [{"endpoints": ["%s:%s" % (l.node1.name, l.intf1),
                                "%s:%s" % (l.node2.name, l.intf2)],
                  "mtu": 1500}
                 for l in self.links]
        return {"name": self.name,
                "topology": {"nodes": nodes, "links": links}}

    @property
    def topo_file(self):
        return os.path.join(self.dir, "%s.clab.yml" % self.name)

    def build(self):
        """Create switches, hosts and links (does not attach controllers)."""
        util.require_root()
        current = current_network()
        if current and current != self.name:
            util.die("network '%s' is still running. Stop it first with: "
                     "csci60 stop" % current)
        if current == self.name:
            info("Cleaning up the previous run of '%s'" % self.name)
            destroy(self.name)
        if not self.hosts and not self.switches:
            util.die("the network has no nodes")
        if self._default_controller and not self.controllers:
            self.addController("c0")

        os.makedirs(self.dir, exist_ok=True)
        # Interfaces left behind by a crash would make containerlab refuse.
        for s in self.switches:
            for intf in s.intfs:
                sh("ip link del %s 2>/dev/null" % intf, check=False)
        with open(self.topo_file, "w") as f:
            # JSON is valid YAML, so containerlab reads this file directly.
            json.dump(self._clab_topology(), f, indent=2)
        self._save_state()
        with open(util.CURRENT_FILE, "w") as f:
            f.write(self.name)

        info("Creating network")
        info("Adding switches: %s" % " ".join(s.name for s in self.switches))
        for s in self.switches:
            sh("ovs-vsctl --if-exists del-br %s" % s.name)
            sh("ovs-vsctl add-br {n} -- set bridge {n} protocols={p} "
               "other-config:datapath-id={d} "
               "other-config:disable-in-band=true "
               "external_ids:csci60={lab}".format(
                   n=s.name, p=s.protocols, d=s.dpid, lab=self.name))
            # Until a controller is attached, act like a normal switch.
            sh("ovs-vsctl set-fail-mode %s standalone" % s.name)
        info("Adding hosts: %s" % " ".join(h.name for h in self.hosts))
        info("Adding links: %s" % " ".join(
            "(%s, %s)" % (l.node1.name, l.node2.name) for l in self.links))
        proc = run(["containerlab", "deploy", "--reconfigure", "-t",
                    self.topo_file], check=False, env=util.CLAB_ENV)
        if proc.returncode != 0:
            print(proc.stdout + proc.stderr)
            util.die("containerlab deploy failed (see output above)")

        self._fix_switch_port_numbers()
        info("Configuring hosts")
        self._configure_hosts()
        self._apply_link_params()
        self.built = True

    def start(self):
        if not self.built:
            self.build()
        info("Starting %d switches" % len(self.switches))
        for s in self.switches:
            self._apply_controllers(s)
        if self.controllers:
            info("Controllers: %s" % " ".join(
                "%s(%s)" % (c.name, c.target() or "built-in")
                for c in self.controllers))
        self.started = True
        self._save_state()

    def stop(self):
        if detached():
            info("Leaving network '%s' running (detached). Use 'csci60 cli' "
                 "to open its console and 'csci60 stop' to remove it."
                 % self.name)
            return
        info("Stopping network '%s'" % self.name)
        destroy(self.name)
        info("Done")

    # ----- internals ------------------------------------------------------

    def _fix_switch_port_numbers(self):
        """Make OpenFlow port N match interface sN-ethN, as in Mininet.

        Containerlab plugs veths into a bridge in whatever order it creates
        them, so the OpenFlow port numbers would otherwise be random.
        """
        for s in self.switches:
            for i, intf in enumerate(s.intfs):
                sh("ovs-vsctl set interface %s ofport_request=%d"
                   % (intf, 1000 + i))
            for intf in s.intfs:
                num = int(intf.rsplit("eth", 1)[1])
                sh("ovs-vsctl set interface %s ofport_request=%d"
                   % (intf, num))
            for intf in s.intfs:
                sh("ip link set dev %s up" % intf)

    def _configure_hosts(self):
        def configure(index, h):
            script = [
                # Quiet hosts: no IPv6 chatter in controller logs.
                "sysctl -qw net.ipv6.conf.all.disable_ipv6=1",
                "sysctl -qw net.ipv6.conf.default.disable_ipv6=1",
                # A host is not a router until you make it one (Lab 4).
                "sysctl -qw net.ipv4.ip_forward=0",
                "sysctl -qw net.ipv4.conf.all.rp_filter=0",
                "sysctl -qw net.ipv4.conf.default.rp_filter=0",
            ]
            for intf in h.intfs:
                script.append("ip link set dev %s up" % intf)
            mac = h.params_mac
            if not mac and self.autoSetMacs:
                mac = "00:00:00:00:00:%02x" % (index + 1)
            if mac and h.intfs:
                script.append("ip link set dev %s address %s"
                              % (h.intfs[0], mac))
            ip = h.params_ip or h.ip_auto
            if ip and "/" not in ip:
                ip += "/" + self.ipBase.split("/")[1]
            if ip and h.intfs and h.intfs[0] not in h.pending_ips:
                script.append("ip addr flush dev %s" % h.intfs[0])
                script.append("ip addr add %s dev %s" % (ip, h.intfs[0]))
            for intf, addr in h.pending_ips.items():
                script.append("ip addr flush dev %s" % intf)
                script.append("ip addr add %s dev %s" % (addr, intf))
            h.pending_ips = {}
            if h.defaultRoute:
                script.append("ip route replace default %s" % h.defaultRoute)
            h.cmd(" ; ".join(script))

        base, plen = self.ipBase.split("/")
        base_int = _ip_to_int(base)
        for i, h in enumerate(self.hosts):
            h.ip_auto = "%s/%s" % (_int_to_ip(base_int + i + 1), plen)

        threads = [threading.Thread(target=configure, args=(i, h))
                   for i, h in enumerate(self.hosts)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        for s in self.switches:
            for intf, addr in s.pending_ips.items():
                sh("ip addr flush dev %s && ip addr add %s dev %s"
                   % (intf, addr, intf))
            s.pending_ips = {}

    def _apply_link_params(self):
        for l in self.links:
            if not l.params:
                continue
            netem = _netem_args(l.params)
            for node, intf in ((l.node1, l.intf1), (l.node2, l.intf2)):
                command = "tc qdisc replace dev %s root netem %s" % (intf,
                                                                      netem)
                node.cmd(command, check=True)

    def _apply_controllers(self, switch):
        names = switch.controllers
        ctrls = (self.controllers if names is None else
                 [self.nameToNode[n] for n in names])
        ctrls = [c for c in ctrls if c.remote]
        if ctrls:
            sh("ovs-vsctl set-controller %s %s" % (
                switch.name, " ".join(c.target() for c in ctrls)))
            sh("ovs-vsctl set-fail-mode %s %s" % (
                switch.name, switch.failMode or "secure"))
        else:
            sh("ovs-vsctl del-controller %s" % switch.name)
            sh("ovs-vsctl set-fail-mode %s %s" % (
                switch.name, switch.failMode or "standalone"))

    def _save_state(self):
        os.makedirs(self.dir, exist_ok=True)
        state = {
            "name": self.name,
            "autoSetMacs": self.autoSetMacs,
            "hosts": [{"name": h.name, "intfs": h.intfs} for h in self.hosts],
            "switches": [{"name": s.name, "intfs": s.intfs, "dpid": s.dpid,
                          "protocols": s.protocols,
                          "controllers": s.controllers}
                         for s in self.switches],
            "controllers": [{"name": c.name, "remote": c.remote, "ip": c.ip,
                             "port": c.port} for c in self.controllers],
            "links": [{"node1": l.node1.name, "intf1": l.intf1,
                       "node2": l.node2.name, "intf2": l.intf2,
                       "params": l.params} for l in self.links],
            "started": self.started,
        }
        with open(os.path.join(self.dir, "state.json"), "w") as f:
            json.dump(state, f, indent=2)

    @classmethod
    def load(cls, name):
        """Re-open a network that is already running (for `csci60 cli`)."""
        path = os.path.join(util.LABS_ROOT, name, "state.json")
        with open(path) as f:
            state = json.load(f)
        net = cls(name)
        for h in state["hosts"]:
            host = net.addHost(h["name"])
            host.intfs = h["intfs"]
        for s in state["switches"]:
            sw = net.addSwitch(s["name"], dpid=s["dpid"],
                               protocols=s["protocols"])
            sw.intfs = s["intfs"]
            sw.controllers = s["controllers"]
        for c in state["controllers"]:
            if c["remote"]:
                net.addController(c["name"], controller=RemoteController,
                                  ip=c["ip"], port=c["port"])
            else:
                net.addController(c["name"])
        for l in state["links"]:
            net.links.append(Link(net[l["node1"]], l["intf1"],
                                  net[l["node2"]], l["intf2"], l["params"]))
        net.built = net.started = True
        return net

    # ----- testing helpers (Mininet names) --------------------------------

    def ping(self, hosts=None, timeout=1, quiet=False):
        """Ping between every pair of hosts. Returns the % of lost pings."""
        hosts = hosts or self.hosts
        hosts = [self.get(h) if isinstance(h, str) else h for h in hosts]
        if not quiet:
            info("Ping: testing ping reachability")
        ips = dict((h.name, h.IP()) for h in hosts)
        sent = received = 0
        for src in hosts:
            line = "%s -> " % src.name
            for dst in hosts:
                if dst is src:
                    continue
                sent += 1
                ok = False
                if ips[dst.name]:
                    out = src.cmd("ping -c1 -W%d %s" % (timeout, ips[dst.name]))
                    ok = " 0% packet loss" in out
                if ok:
                    received += 1
                line += (dst.name if ok else "X") + " "
            if not quiet:
                print(line.rstrip())
        lost = 100.0 * (sent - received) / sent if sent else 0.0
        if not quiet:
            info("Results: %d%% dropped (%d/%d received)"
                 % (lost, received, sent))
        return lost

    def pingAll(self, timeout=1):
        return self.ping(timeout=timeout)

    def pingPair(self):
        return self.ping(self.hosts[:2])

    def iperf(self, hosts=None, seconds=5):
        """TCP throughput between two hosts using iperf (v2), like Mininet."""
        if not hosts:
            hosts = self.hosts[0], self.hosts[-1]
        client, server = [self.get(h) if isinstance(h, str) else h
                          for h in hosts]
        info("Iperf: testing TCP bandwidth between %s and %s"
             % (client.name, server.name))
        server.cmd("pkill iperf; (iperf -s >/dev/null 2>&1 &)")
        time.sleep(0.5)
        out = client.cmd("iperf -f m -t %d -c %s" % (seconds, server.IP()))
        server.cmd("pkill iperf")
        m = re.findall(r"([\d.]+ [KMG]bits/sec)", out)
        result = m[-1] if m else "no result (are the hosts reachable?)"
        info("Results: %s" % result)
        return result

    def configLinkStatus(self, src, dst, status):
        """Bring the link between two nodes 'up' or 'down'."""
        found = False
        for l in self.links:
            names = (l.node1.name, l.node2.name)
            if names in ((src, dst), (dst, src)):
                found = True
                for node, intf in ((l.node1, l.intf1), (l.node2, l.intf2)):
                    node.cmd("ip link set dev %s %s" % (intf, status))
        if not found:
            print("*** no link between %s and %s" % (src, dst))
        return found


# Mininet compatibility name.
Mininet = Network


# ----- module-level helpers ----------------------------------------------

def detached():
    return os.environ.get("CSCI60_DETACH") == "1"


def current_network():
    try:
        with open(util.CURRENT_FILE) as f:
            name = f.read().strip()
    except IOError:
        return None
    if name and os.path.exists(os.path.join(util.LABS_ROOT, name)):
        return name
    return None


def destroy(name):
    """Remove a network: containers, links, bridges, state."""
    lab_dir = os.path.join(util.LABS_ROOT, name)
    topo = os.path.join(lab_dir, "%s.clab.yml" % name)
    if os.path.exists(topo):
        run(["containerlab", "destroy", "--cleanup", "-t", topo], check=False,
            env=util.CLAB_ENV)
    # Switch-to-switch links are veth pairs on the server itself; containers
    # going away does not remove them.
    try:
        with open(os.path.join(lab_dir, "state.json")) as f:
            state = json.load(f)
        for s in state.get("switches", []):
            for intf in s.get("intfs", []):
                sh("ip link del %s 2>/dev/null" % intf, check=False)
    except (IOError, ValueError):
        pass
    bridges = sh("ovs-vsctl --bare --columns=name find bridge "
                 "external_ids:csci60=%s" % name, check=False).stdout.split()
    for br in bridges:
        sh("ovs-vsctl --if-exists del-br %s" % br, check=False)
    shutil.rmtree(lab_dir, ignore_errors=True)
    if current_network() in (None, name):
        try:
            os.remove(util.CURRENT_FILE)
        except OSError:
            pass


def _parse_setip(node, args, kwargs):
    args = list(args)
    intf = kwargs.get("intf")
    if args and isinstance(args[0], str) and args[0] in node.intfs:
        intf = args.pop(0)
    ip = kwargs.get("ip", args[0] if args else None)
    plen = kwargs.get("prefixLen", args[1] if len(args) > 1 else 8)
    if ip is None:
        util.die("setIP needs an address")
    if "/" not in ip:
        ip = "%s/%s" % (ip, plen)
    return intf or node.defaultIntf(), ip


def _netem_args(params):
    parts = []
    if "delay" in params:
        parts.append("delay %s" % params["delay"])
    if "loss" in params:
        parts.append("loss %s%%" % params["loss"])
    if "bw" in params:
        parts.append("rate %smbit" % params["bw"])
    if "max_queue_size" in params:
        parts.append("limit %d" % int(params["max_queue_size"]))
    return " ".join(parts)


def _ip_to_int(ip):
    a, b, c, d = [int(x) for x in ip.split(".")]
    return (a << 24) | (b << 16) | (c << 8) | d


def _int_to_ip(n):
    return ".".join(str((n >> s) & 255) for s in (24, 16, 8, 0))
