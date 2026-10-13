#!/usr/bin/python3
# "Setting Performance Limits": CPU, bandwidth, delay, loss, queue size.
from mininet.net import Mininet
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.util import dumpNodeConnections

net = Mininet(host=CPULimitedHost, link=TCLink)
c0 = net.addController()
s0 = net.addSwitch('s0')
h0 = net.addHost('h0')
h1 = net.addHost('h1', cpu=0.5)
h2 = net.addHost('h2', cpu=0.5)
net.addLink(s0, h0, bw=10, delay='5ms', max_queue_size=1000, loss=10,
            use_htb=True)
net.addLink(s0, h1)
net.addLink(s0, h2)

net.start()
# display network information
dumpNodeConnections(net.hosts)
# testing ping from all hosts to all hosts
net.pingAll()
# test ping from one host to another host
net.ping((h0, h1))
# test packet performance from one host to another host
net.iperf((h0, h1))
net.stop()
