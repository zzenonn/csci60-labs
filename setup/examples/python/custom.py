#!/usr/bin/python3
# "Unknown Topology": build any network by hand (slide 13).
from mininet.net import Mininet
from mininet.cli import CLI

net = Mininet()
# Creating nodes in the network.
c0 = net.addController()
h0 = net.addHost('h0')
s0 = net.addSwitch('s0')
h1 = net.addHost('h1')
# Creating links between nodes in network
net.addLink(h0, s0)
net.addLink(h1, s0)
# Configuration of IP addresses in interfaces
h0.setIP('192.168.1.1', 24)
h1.setIP('192.168.1.2', 24)

net.start()
net.pingAll()
CLI(net)        # remove this line to drop the network when the script ends
net.stop()
