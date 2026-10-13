#!/usr/bin/python3
# --topo linear,4 as a script (slide "Some Topologies to Try Out").
from mininet.net import Mininet
from mininet.topo import LinearTopo

Linear4 = LinearTopo(k=4)
net = Mininet(topo=Linear4)
net.start()
net.pingAll()
net.stop()
