def createLink(node1, node2, **params):
    """Mininet 2.0 helper: returns the two new interface names."""
    link = node1.net.addLink(node1, node2, **params)
    return link.intf1, link.intf2


def dumpNodeConnections(nodes):
    for node in nodes:
        peers = []
        for l in node.net.links:
            if l.node1 is node:
                peers.append("%s:%s" % (l.intf1, l.intf2))
            elif l.node2 is node:
                peers.append("%s:%s" % (l.intf2, l.intf1))
        print("%s %s" % (node.name, " ".join(peers)))
