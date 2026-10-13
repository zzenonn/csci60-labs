#!/usr/bin/python3
# Use an external controller (Ryu) instead of the built-in one.
# First, in another terminal:   csci60 ryu start simple_switch
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI

net = Mininet(controller=RemoteController)
net.addController('c0', ip='127.0.0.1', port=6633)
s1 = net.addSwitch('s1')
for i in (1, 2, 3):
    net.addLink(net.addHost('h%d' % i), s1)

net.start()
net.pingAll()
CLI(net)
net.stop()
