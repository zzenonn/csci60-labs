# Ryu port of of_switch_flow.py (POX tutorial, James McCauley), CSCI 60 2026.
# GPLv3 or later, like the POX original.
"""Plain MAC-learning switch, one instance per connected switch.

This is the controller to use when a lab just needs the network to work
(for example the two-controller exercise, or as a partner for flow_stats).

    csci60 ryu start simple_switch

Set HUB = True below to make every switch act like a hub instead (the
`act_like_hub` exercise from the POX tutorial).
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import ethernet, packet
from ryu.ofproto import ofproto_v1_0

HUB = False


class SimpleSwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch, self).__init__(*args, **kwargs)
        self.mac_to_port = {}   # dpid -> {mac: port}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features(self, ev):
        dp = ev.msg.datapath
        self.logger.info("Controlling switch %016x", dp.id)
        p = dp.ofproto_parser
        dp.send_msg(p.OFPFlowMod(datapath=dp, match=p.OFPMatch(),
                                 command=dp.ofproto.OFPFC_DELETE))

    def send_packet(self, msg, out_port):
        dp = msg.datapath
        ofp, p = dp.ofproto, dp.ofproto_parser
        data = msg.data if msg.buffer_id == ofp.OFP_NO_BUFFER else None
        dp.send_msg(p.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id,
                                   in_port=msg.in_port, data=data,
                                   actions=[p.OFPActionOutput(out_port)]))

    def add_flow(self, msg, match, out_port):
        dp = msg.datapath
        ofp, p = dp.ofproto, dp.ofproto_parser
        dp.send_msg(p.OFPFlowMod(datapath=dp, match=match,
                                 command=ofp.OFPFC_ADD, idle_timeout=10,
                                 hard_timeout=30,
                                 actions=[p.OFPActionOutput(out_port)]))
        self.send_packet(msg, out_port)

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status(self, ev):
        msg = ev.msg
        reason = {msg.datapath.ofproto.OFPPR_ADD: "added",
                  msg.datapath.ofproto.OFPPR_DELETE: "deleted"}.get(
                      msg.reason, "modified")
        self.logger.debug("Port %d %s (%016x).", msg.desc.port_no, reason,
                          msg.datapath.id)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp, p = dp.ofproto, dp.ofproto_parser
        eth = packet.Packet(msg.data).get_protocol(ethernet.ethernet)
        if eth is None:
            return
        if HUB:
            self.logger.debug("installing flow for %s.%i -> %s.%i", eth.src,
                              msg.in_port, eth.dst, ofp.OFPP_FLOOD)
            self.add_flow(msg, p.OFPMatch(in_port=msg.in_port,
                                          dl_src=haddr_to_bin(eth.src),
                                          dl_dst=haddr_to_bin(eth.dst)),
                          ofp.OFPP_FLOOD)
            return
        table = self.mac_to_port.setdefault(dp.id, {})
        table[eth.src] = msg.in_port
        port = table.get(eth.dst)
        if port is None:
            self.send_packet(msg, ofp.OFPP_FLOOD)
            return
        self.logger.debug("installing flow for %s.%i -> %s.%i", eth.src,
                          msg.in_port, eth.dst, port)
        self.add_flow(msg, p.OFPMatch(dl_src=haddr_to_bin(eth.src),
                                      dl_dst=haddr_to_bin(eth.dst)), port)
