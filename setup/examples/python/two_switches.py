#!/usr/bin/python3
# Exercise: 2 switches connected to each other with 3 hosts each.
from mininet.net import Mininet
from mininet.cli import CLI

net = Mininet()
net.addController('c0')
s1 = net.addSwitch('s1')
s2 = net.addSwitch('s2')
net.addLink(s1, s2)
for i in range(1, 7):
    h = net.addHost('h%d' % i)
    net.addLink(h, s1 if i <= 3 else s2)

net.start()
net.pingAll()
CLI(net)
net.stop()
