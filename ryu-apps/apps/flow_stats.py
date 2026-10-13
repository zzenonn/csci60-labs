# Copyright 2012 William Yu (original POX version)
# Ryu port for CSCI 60, 2026. GPLv3 or later, like the POX original.
"""Flow and port statistics every 5 seconds (from flow_stats.py).

Run it next to a forwarding app so there is traffic to measure:
    csci60 ryu start simple_switch flow_stats

Every 5 seconds each switch is asked for its flow and port counters. The log
shows a summary of web traffic (TCP port 80) per switch:
    Web traffic from 0000000000000001: 1234 bytes (20 packets) over 2 flows
Port counters are printed with --verbose (csci60 ryu start -v ...).

Try it: start a web server on one host and fetch from another, e.g.
    csci60> h2 python3 -m http.server 80 &
    csci60> h1 curl -s h2 > /dev/null
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import (CONFIG_DISPATCHER, DEAD_DISPATCHER,
                                    MAIN_DISPATCHER, set_ev_cls)
from ryu.lib import hub
from ryu.ofproto import ofproto_v1_0

INTERVAL = 5


class FlowStats(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(FlowStats, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.thread = hub.spawn(self._timer)

    @set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def state_change(self, ev):
        dp = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            self.datapaths[dp.id] = dp
        elif dp.id in self.datapaths:
            del self.datapaths[dp.id]

    def _timer(self):
        while True:
            for dp in list(self.datapaths.values()):
                ofp, p = dp.ofproto, dp.ofproto_parser
                dp.send_msg(p.OFPFlowStatsRequest(
                    dp, 0, p.OFPMatch(), 0xff, ofp.OFPP_NONE))
                # OFPP_NONE = all ports (the fix from the POX ANY_PORT patch).
                dp.send_msg(p.OFPPortStatsRequest(dp, 0, ofp.OFPP_NONE))
            if self.datapaths:
                self.logger.debug("Sent %i flow/port stats request(s)",
                                  len(self.datapaths))
            hub.sleep(INTERVAL)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def flow_stats(self, ev):
        web_bytes = web_packets = web_flows = 0
        for f in ev.msg.body:
            if f.match.tp_dst == 80 or f.match.tp_src == 80:
                web_bytes += f.byte_count
                web_packets += f.packet_count
                web_flows += 1
        self.logger.info("Web traffic from %016x: %s bytes (%s packets) "
                         "over %s flows", ev.msg.datapath.id, web_bytes,
                         web_packets, web_flows)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats(self, ev):
        for s in ev.msg.body:
            self.logger.debug("Port stats %016x port %s: rx %s pkts, tx %s pkts",
                              ev.msg.datapath.id, s.port_no, s.rx_packets,
                              s.tx_packets)
