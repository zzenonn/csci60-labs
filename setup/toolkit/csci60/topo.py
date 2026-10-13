"""Built-in topologies, named and numbered exactly like Mininet's.

  minimal          2 hosts, 1 switch
  single,N         N hosts on 1 switch
  linear,N         N switches in a line, one host each
  tree,depth=D,fanout=F
"""

from .net import Network


class Topo(object):
    """Base class. Subclasses implement build(net)."""

    def build(self, net):
        raise NotImplementedError


class MinimalTopo(Topo):
    def build(self, net):
        s1 = net.addSwitch("s1")
        for i in (1, 2):
            net.addLink(net.addHost("h%d" % i), s1)


class SingleSwitchTopo(Topo):
    def __init__(self, k=2):
        self.k = int(k)

    def build(self, net):
        s1 = net.addSwitch("s1")
        for i in range(1, self.k + 1):
            net.addLink(net.addHost("h%d" % i), s1)


class LinearTopo(Topo):
    def __init__(self, k=2):
        self.k = int(k)

    def build(self, net):
        prev = None
        for i in range(1, self.k + 1):
            s = net.addSwitch("s%d" % i)
            net.addLink(net.addHost("h%d" % i), s)
            if prev:
                net.addLink(prev, s)
            prev = s


class TreeTopo(Topo):
    def __init__(self, depth=1, fanout=2):
        self.depth = int(depth)
        self.fanout = int(fanout)

    def build(self, net):
        self.hosts = 0
        self.switches = 0
        self._add(net, self.depth)

    def _add(self, net, depth):
        if depth == 0:
            self.hosts += 1
            return net.addHost("h%d" % self.hosts)
        self.switches += 1
        s = net.addSwitch("s%d" % self.switches)
        for _ in range(self.fanout):
            child = self._add(net, depth - 1)
            net.addLink(s, child)
        return s


TOPOS = {
    "minimal": MinimalTopo,
    "single": SingleSwitchTopo,
    "linear": LinearTopo,
    "tree": TreeTopo,
}


def parse(spec):
    """'single,3' or 'tree,depth=2,fanout=2' -> Topo instance."""
    parts = spec.split(",")
    name = parts[0]
    if name not in TOPOS:
        raise ValueError("unknown topology %r (choose from %s)"
                         % (name, ", ".join(sorted(TOPOS))))
    args, kwargs = [], {}
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            kwargs[k] = v
        else:
            args.append(p)
    return TOPOS[name](*args, **kwargs)


def build(spec, net_name="csci60", **net_kwargs):
    net = Network(net_name, **net_kwargs)
    parse(spec).build(net)
    return net
