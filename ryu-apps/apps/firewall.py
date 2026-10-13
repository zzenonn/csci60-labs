# Copyright 2012 William Yu (original POX version)
# Ryu port for CSCI 60, 2026. GPLv3 or later, like the POX original.
"""Simple per-port firewall with a learning switch (from of_firewall.py).

Every IP packet is checked against a rule table. A packet is allowed when a
rule (protocol, source port/ICMP type, switch in-port) exists for it; then
the normal learning-switch logic runs and a flow is installed. Everything
else is dropped by the controller. Non-IP traffic (ARP) always passes, so
hosts can still find each other.

  This is the "noisy" firewall from the POX lab: only allowed traffic gets a
  flow, so every blocked packet still reaches the controller. Watch the log
  and think about why that is a bad design.

Rules are managed while the network runs:
    csci60 ryu ctl /csci60/firewall                        (list rules)
    csci60 ryu ctl /csci60/firewall/add '{"proto": "icmp", "in_port": 1}'
    csci60 ryu ctl /csci60/firewall/add '{"proto": "tcp", "tp_src": 80, "in_port": 2}'
    csci60 ryu ctl /csci60/firewall/delete '{"proto": "icmp", "in_port": 1}'
    csci60 ryu ctl /csci60/firewall/clear '{}'

Fields:
    proto    "icmp" | "tcp" | "udp" | IP protocol number      (default icmp)
    tp_src   TCP/UDP source port or ICMP type, 0 = any         (default 0)
    in_port  switch port the packet arrives on, 0 = any port   (default 0)
    dpid     switch id, e.g. 1, 0 = every switch               (default 0)

With no rules, all IP traffic is blocked (ping fails, ARP still works).
The original POX file had the default rule hard-coded; this version starts
with an empty table so you can add rules one at a time.
"""

import json

from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import ethernet, icmp, ipv4, packet, tcp, udp
from ryu.ofproto import ether, ofproto_v1_0
from webob import Response

APP_KEY = "csci60_firewall"
PROTOS = {"icmp": 1, "tcp": 6, "udp": 17}


def _rule(body):
    proto = body.get("proto", "icmp")
    proto = PROTOS.get(str(proto).lower(), proto)
    return (int(body.get("dpid", 0)), int(proto), int(body.get("tp_src", 0)),
            int(body.get("in_port", 0)))


class Firewall(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]
    _CONTEXTS = {"wsgi": WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(Firewall, self).__init__(*args, **kwargs)
        self.table = {}     # (dpid, mac) -> port
        self.rules = set()  # (dpid, proto, tp_src, in_port); 0 = wildcard
        self.datapaths = {}
        kwargs["wsgi"].register(FirewallRest, {APP_KEY: self})
        self.logger.info("Firewall Tutorial is running. No rules yet: all IP "
                         "traffic is blocked.")

    def allowed(self, dpid, proto, tp_src, in_port):
        for r_dpid, r_proto, r_src, r_port in self.rules:
            if (r_dpid in (0, dpid) and r_proto == proto and
                    r_src in (0, tp_src) and r_port in (0, in_port)):
                return True
        return False

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features(self, ev):
        dp = ev.msg.datapath
        self.datapaths[dp.id] = dp
        self.clear(dp)

    def clear(self, dp):
        p = dp.ofproto_parser
        dp.send_msg(p.OFPFlowMod(datapath=dp, match=p.OFPMatch(),
                                 command=dp.ofproto.OFPFC_DELETE))

    def send(self, msg, out_port):
        dp = msg.datapath
        ofp, p = dp.ofproto, dp.ofproto_parser
        data = msg.data if msg.buffer_id == ofp.OFP_NO_BUFFER else None
        dp.send_msg(p.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id,
                                   in_port=msg.in_port, data=data,
                                   actions=[p.OFPActionOutput(out_port)]))

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp, p = dp.ofproto, dp.ofproto_parser
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth is None:
            return
        self.table[(dp.id, eth.src)] = msg.in_port
        dst_port = self.table.get((dp.id, eth.dst))

        ip = pkt.get_protocol(ipv4.ipv4)
        if ip is None:
            # ARP and friends: behave like a learning switch, no flows.
            self.send(msg, dst_port if dst_port else ofp.OFPP_FLOOD)
            return

        l4 = pkt.get_protocol(tcp.tcp) or pkt.get_protocol(udp.udp)
        ic = pkt.get_protocol(icmp.icmp)
        tp_src = l4.src_port if l4 else (ic.type if ic else 0)
        if not self.allowed(dp.id, ip.proto, tp_src, msg.in_port):
            self.logger.info("Rule (%s %s %s %s) NOT FOUND in %016x: dropped",
                             hex(eth.ethertype), ip.proto, tp_src,
                             msg.in_port, dp.id)
            return
        self.logger.info("Rule (%s %s %s %s) FOUND in %016x",
                         hex(eth.ethertype), ip.proto, tp_src, msg.in_port,
                         dp.id)
        if dst_port is None:
            self.send(msg, ofp.OFPP_ALL)
            self.logger.info("Broadcasting %s.%i -> %s.%i", eth.src,
                             msg.in_port, eth.dst, ofp.OFPP_ALL)
            return
        fields = dict(dl_type=ether.ETH_TYPE_IP, nw_proto=ip.proto,
                      dl_src=haddr_to_bin(eth.src),
                      dl_dst=haddr_to_bin(eth.dst))
        if l4:
            fields["tp_src"] = tp_src
        dp.send_msg(p.OFPFlowMod(
            datapath=dp, match=p.OFPMatch(in_port=msg.in_port, **fields),
            command=ofp.OFPFC_ADD, idle_timeout=10, hard_timeout=30,
            actions=[p.OFPActionOutput(dst_port)]))
        self.send(msg, dst_port)
        self.logger.info("Installing %s.%i -> %s.%i", eth.src, msg.in_port,
                         eth.dst, dst_port)


class FirewallRest(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(FirewallRest, self).__init__(req, link, data, **config)
        self.app = data[APP_KEY]

    def _ok(self):
        rules = [dict(zip(("dpid", "proto", "tp_src", "in_port"), r))
                 for r in sorted(self.app.rules)]
        return Response(content_type="application/json", charset="utf-8",
                        body=json.dumps({"rules": rules}).encode())

    def _body(self, req):
        return json.loads(req.body.decode() or "{}")

    def _flush(self):
        for dp in self.app.datapaths.values():
            self.app.clear(dp)

    @route("fw", "/csci60/firewall", methods=["GET"])
    def show(self, req, **kw):
        for r in sorted(self.app.rules):
            self.app.logger.info("Rule %s defined", r)
        return self._ok()

    @route("fw", "/csci60/firewall/add", methods=["POST"])
    def add(self, req, **kw):
        r = _rule(self._body(req))
        self.app.rules.add(r)
        self.app.logger.info("Adding firewall rule: %s", r)
        return self._ok()

    @route("fw", "/csci60/firewall/delete", methods=["POST"])
    def delete(self, req, **kw):
        r = _rule(self._body(req))
        if r in self.app.rules:
            self.app.rules.discard(r)
            self.app.logger.info("Deleting firewall rule: %s", r)
            self._flush()  # remove flows that the rule had allowed
        else:
            self.app.logger.error("Cannot find rule: %s", r)
        return self._ok()

    @route("fw", "/csci60/firewall/clear", methods=["POST"])
    def clear(self, req, **kw):
        self.app.rules.clear()
        self._flush()
        return self._ok()

    @route("fw", "/csci60/switches", methods=["GET"])
    def switches(self, req, **kw):
        return Response(content_type="application/json", charset="utf-8",
                        body=json.dumps(["%016x" % d for d in
                                         sorted(self.app.datapaths)]).encode())
