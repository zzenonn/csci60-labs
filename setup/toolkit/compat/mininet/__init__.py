"""Mininet compatibility layer for the CSCI 60 toolkit.

Lets the course's original Mininet scripts (lab4.py, of_simple_topo.py, ...)
run unchanged on Containerlab: `from mininet.net import Mininet` resolves
here and builds the same network with Open vSwitch + Containerlab.
New material should import from `csci60` directly.
"""
