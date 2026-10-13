"""The interactive network console (`mininet>` becomes `csci60>`)."""

import cmd
import os
import re
import subprocess
import sys

from .net import Host, Switch


class CLI(cmd.Cmd):
    """Same commands as the Mininet CLI.

    Type `<node> <command>` to run a command inside a node, for example
        h1 ip addr
        h1 ping -c3 h2       (node names are replaced by their IP address)
    """

    prompt = "csci60> "

    def __init__(self, net, script=None):
        from .net import detached
        cmd.Cmd.__init__(self)
        if detached() and not script:
            return
        self.net = net
        self.locals = {"net": net}
        for name, node in net.nameToNode.items():
            self.locals[name] = node
        if script:
            with open(script) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        print(self.prompt + line)
                        self.onecmd(line)
            return
        print("*** Starting CLI (type 'help' for commands, 'exit' to leave)")
        while True:
            try:
                self.cmdloop()
                break
            except KeyboardInterrupt:
                print("\nInterrupt (type 'exit' to leave)")

    # ---- plumbing --------------------------------------------------------

    def emptyline(self):
        pass

    def default(self, line):
        first, _, rest = line.partition(" ")
        node = self.net.nameToNode.get(first)
        if node is None or not hasattr(node, "cmd"):
            print("*** Unknown command: %s" % line)
            return
        rest = self._substitute_ips(rest)
        if isinstance(node, Host):
            # Stream output and allow Ctrl-C (for ping, tcpdump, ...).
            try:
                subprocess.call(node.popen_args(rest, tty=sys.stdin.isatty()))
            except KeyboardInterrupt:
                pass
        else:
            try:
                subprocess.call(["sh", "-c", rest])
            except KeyboardInterrupt:
                pass

    def _substitute_ips(self, rest):
        words = rest.split(" ")
        out = []
        for w in words:
            node = self.net.nameToNode.get(w)
            if isinstance(node, Host):
                ip = node.IP()
                out.append(ip or w)
            else:
                out.append(w)
        return " ".join(out)

    def do_help(self, line):
        print("""Commands (same as Mininet):
  nodes                    list nodes
  net                      show links
  dump                     show node interfaces and addresses
  links                    show links and whether they are up
  pingall                  ping between all hosts
  pingpair                 ping between the first two hosts
  iperf [h1 h2]            TCP throughput between two hosts
  link <n1> <n2> up|down   bring a link up or down
  dpctl <args>             run ovs-ofctl on every switch, e.g. 'dpctl dump-flows'
  ryu modes | mode <NAME> | clear
                           control the Lab 2 hub/switch app (sw_tutorial)
  <node> <command>         run a command on a node, e.g. 'h1 ip addr', 'h1 ping h2'
  sh <command>             run a command on the server
  py <expr>                evaluate Python (net, h1, s1 ... are defined)
  px <stmt>                execute a Python statement
  exit | quit              leave the console""")

    # ---- informational ---------------------------------------------------

    def do_nodes(self, line):
        names = [h.name for h in self.net.hosts] + \
                [s.name for s in self.net.switches] + \
                [c.name for c in self.net.controllers]
        print("available nodes are: \n%s" % " ".join(names))

    def do_net(self, line):
        for node in self.net.hosts + self.net.switches:
            peers = []
            for l in self.net.links:
                if l.node1 is node:
                    peers.append("%s:%s" % (l.intf1, l.intf2))
                elif l.node2 is node:
                    peers.append("%s:%s" % (l.intf2, l.intf1))
            print("%s %s" % (node.name, " ".join(peers)))
        for c in self.net.controllers:
            print(c.name)

    def do_dump(self, line):
        for h in self.net.hosts:
            addrs = []
            for intf in h.intfs:
                addrs.append("%s:%s" % (intf, h.IP(intf)))
            print("<Host %s: %s>" % (h.name, ",".join(addrs)))
        for s in self.net.switches:
            print("<OVSSwitch %s: %s dpid=%s>" % (s.name, ",".join(s.intfs),
                                                  s.dpid))
        for c in self.net.controllers:
            print(c)

    def do_links(self, line):
        for l in self.net.links:
            out = l.node1.cmd("cat /sys/class/net/%s/operstate" % l.intf1)
            state = "OK" if "up" in out else "DOWN"
            print("%s<->%s (%s)" % (l.intf1, l.intf2, state))

    # ---- tests -----------------------------------------------------------

    def do_pingall(self, line):
        self.net.pingAll()

    def do_pingpair(self, line):
        self.net.pingPair()

    def do_iperf(self, line):
        args = line.split()
        if args and len(args) != 2:
            print("usage: iperf [host1 host2]")
            return
        self.net.iperf(args or None)

    def do_link(self, line):
        args = line.split()
        if len(args) != 3 or args[2] not in ("up", "down"):
            print("usage: link node1 node2 up|down")
            return
        self.net.configLinkStatus(*args)

    def do_dpctl(self, line):
        for s in self.net.switches:
            print("*** %s %s" % (s.name, "-" * 60))
            sys.stdout.write(s.dpctl(line or "dump-flows"))

    def do_ryu(self, line):
        from . import ryu
        args = line.split()
        port = 6633
        if "--port" in args:
            i = args.index("--port")
            port = int(args[i + 1])
            del args[i:i + 2]
        try:
            ryu.control(args, port=port)
        except SystemExit:
            pass

    # ---- escape hatches --------------------------------------------------

    def do_sh(self, line):
        subprocess.call(["sh", "-c", line])

    def do_py(self, line):
        try:
            result = eval(line, globals(), self.locals)
            if result is not None:
                print(result)
        except Exception as exc:  # show the error, keep the console alive
            print("*** %s: %s" % (exc.__class__.__name__, exc))

    def do_px(self, line):
        try:
            exec(line, globals(), self.locals)
        except Exception as exc:
            print("*** %s: %s" % (exc.__class__.__name__, exc))

    def do_xterm(self, line):
        print("*** No graphical xterm on the server. Open another SSH session"
              " and run:  csci60 shell <node>")

    def do_exit(self, line):
        return True

    do_quit = do_exit

    def do_EOF(self, line):
        print()
        return True
