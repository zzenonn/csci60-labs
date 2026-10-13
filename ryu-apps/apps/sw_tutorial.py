# Copyright 2012 James McCauley, William Yu (original POX version)
# Ryu port for CSCI 60, 2026.
#
# Licensed under the GNU General Public License v3 or later, like the POX
# original (of_sw_tutorial_oo.py in hip2b2/poxstuff).
"""Switch / Hub Teaching Demo (Lab 2), ported from POX to Ryu.

Six forwarding behaviours, switchable while the network is running:

  SW_DUMBHUB          every packet goes to the controller, which floods it.
                      No flows are installed.
  SW_PAIRHUB          installs a flood flow per (source MAC, destination MAC).
  SW_LAZYHUB          installs one flood flow that matches every packet.
  SW_BADSWITCH        installs flows on destination MAC only. Find the problem!
  SW_PAIRSWITCH       learns MACs; installs a flow per (source, destination)
                      that forwards to the right port.
  SW_IDEALPAIRSWITCH  like SW_PAIRSWITCH but installs both directions at once.

Start it (default mode SW_IDEALPAIRSWITCH):
    csci60 ryu start sw_tutorial
Change the mode (this also clears every flow, like the POX steps
MySwitch.clear_all_flows(); detach_packetin_listener(); attach_...):
    csci60 ryu mode SW_DUMBHUB          (from a shell)
    ryu mode SW_DUMBHUB                 (from the csci60> console)

Log lines keep the POX format, so the lab handout's OUTPUT A / OUTPUT B
comparison still works:
    Installing <src MAC>.<in port> -> <dst MAC>.<out port>
    Broadcasting / Sending ...
ff:ff:ff:ff:ff:ff means "any MAC" and port 65532 means "all ports".
"""

import json

from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import (CONFIG_DISPATCHER, DEAD_DISPATCHER,
                                    MAIN_DISPATCHER, set_ev_cls)
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import ethernet, packet
from ryu.ofproto import ofproto_v1_0
from webob import Response

ANY_MAC = "ff:ff:ff:ff:ff:ff"
APP_KEY = "csci60_sw_tutorial"
IDLE_TIMEOUT = 10
HARD_TIMEOUT = 30


class SwitchTutorial(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]
    _CONTEXTS = {"wsgi": WSGIApplication}

    MODES = ("SW_DUMBHUB", "SW_PAIRHUB", "SW_LAZYHUB", "SW_BADSWITCH",
             "SW_PAIRSWITCH", "SW_IDEALPAIRSWITCH")

    def __init__(self, *args, **kwargs):
        super(SwitchTutorial, self).__init__(*args, **kwargs)
        # (dpid, MAC) -> port where that MAC was last seen
        self.table = {}
        self.datapaths = {}
        self.mode = "SW_IDEALPAIRSWITCH"
        kwargs["wsgi"].register(TutorialRest, {APP_KEY: self})
        self.logger.info("Switch / Hub Teaching Demo running in %s mode",
                         self.mode)

    # ----- helpers -------------------------------------------------------

    @staticmethod
    def _send(dp, msg):
        dp.send_msg(msg)

    def resend_packet(self, msg, out_port):
        """Send the packet that caused this PacketIn out of out_port."""
        dp = msg.datapath
        ofp, parser = dp.ofproto, dp.ofproto_parser
        data = msg.data if msg.buffer_id == ofp.OFP_NO_BUFFER else None
        out = parser.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id,
                                  in_port=msg.in_port,
                                  actions=[parser.OFPActionOutput(out_port)],
                                  data=data)
        dp.send_msg(out)

    def install(self, dp, out_port, src=None, dst=None, msg=None):
        """Install a flow; if msg is given, also forward that packet."""
        ofp, parser = dp.ofproto, dp.ofproto_parser
        fields = {}
        if src:
            fields["dl_src"] = haddr_to_bin(src)
        if dst:
            fields["dl_dst"] = haddr_to_bin(dst)
        buffer_id = ofp.OFP_NO_BUFFER
        if msg is not None and msg.buffer_id != ofp.OFP_NO_BUFFER:
            buffer_id = msg.buffer_id
        mod = parser.OFPFlowMod(
            datapath=dp, match=parser.OFPMatch(**fields),
            command=ofp.OFPFC_ADD, idle_timeout=IDLE_TIMEOUT,
            hard_timeout=HARD_TIMEOUT, buffer_id=buffer_id,
            actions=[parser.OFPActionOutput(out_port)])
        dp.send_msg(mod)
        # Open vSwitch does not buffer packets, so send this one ourselves.
        if msg is not None and buffer_id == ofp.OFP_NO_BUFFER:
            self.resend_packet(msg, out_port)

    def clear_flows(self, dp):
        ofp, parser = dp.ofproto, dp.ofproto_parser
        dp.send_msg(parser.OFPFlowMod(datapath=dp, match=parser.OFPMatch(),
                                      command=ofp.OFPFC_DELETE))
        self.logger.info("Clearing all flows from %016x.", dp.id)

    def clear_all_flows(self):
        for dp in self.datapaths.values():
            self.clear_flows(dp)
        self.table.clear()

    def set_mode(self, mode):
        if mode is not None and mode not in self.MODES:
            raise ValueError("unknown mode %r; choose one of %s"
                             % (mode, ", ".join(self.MODES)))
        self.clear_all_flows()
        if mode is None:
            self.logger.info("Detaching switch %s.", self.mode)
        else:
            self.logger.info("Attach switch %s.", mode)
        self.mode = mode

    # ----- the six behaviours ---------------------------------------------

    def dumbhub(self, msg, src, dst):
        ALL = msg.datapath.ofproto.OFPP_ALL
        self.resend_packet(msg, ALL)
        self.logger.info("Broadcasting %s.%i -> %s.%i",
                         src, msg.in_port, dst, ALL)

    def pairhub(self, msg, src, dst):
        ALL = msg.datapath.ofproto.OFPP_ALL
        self.install(msg.datapath, ALL, src=src, dst=dst, msg=msg)
        self.logger.info("Installing %s.%i -> %s.%i",
                         src, msg.in_port, dst, ALL)

    def lazyhub(self, msg, src, dst):
        ALL = msg.datapath.ofproto.OFPP_ALL
        self.install(msg.datapath, ALL, msg=msg)
        self.logger.info("Installing %s.%i -> %s.%i",
                         ANY_MAC, msg.in_port, ANY_MAC, ALL)

    def badswitch(self, msg, src, dst):
        dp = msg.datapath
        ALL = dp.ofproto.OFPP_ALL
        self.table[(dp.id, src)] = msg.in_port
        # Flow towards the source, matching the destination MAC only.
        self.install(dp, msg.in_port, dst=src)
        self.logger.info("Installing %s.%i -> %s.%i",
                         ANY_MAC, msg.in_port, src, msg.in_port)
        dst_port = self.table.get((dp.id, dst))
        if dst_port is None:
            self.resend_packet(msg, ALL)
            self.logger.info("Broadcasting %s.%i -> %s.%i",
                             src, msg.in_port, dst, ALL)
        else:
            self.resend_packet(msg, dst_port)
            self.logger.info("Sending %s.%i -> %s.%i",
                             src, msg.in_port, dst, dst_port)

    def pairswitch(self, msg, src, dst):
        dp = msg.datapath
        ALL = dp.ofproto.OFPP_ALL
        self.table[(dp.id, src)] = msg.in_port
        dst_port = self.table.get((dp.id, dst))
        if dst_port is None:
            self.resend_packet(msg, ALL)
            self.logger.info("Broadcasting %s.%i -> %s.%i",
                             src, msg.in_port, dst, ALL)
        else:
            self.install(dp, dst_port, src=src, dst=dst, msg=msg)
            self.logger.info("Installing %s.%i -> %s.%i",
                             src, msg.in_port, dst, dst_port)

    def idealpairswitch(self, msg, src, dst):
        dp = msg.datapath
        ALL = dp.ofproto.OFPP_ALL
        self.table[(dp.id, src)] = msg.in_port
        dst_port = self.table.get((dp.id, dst))
        if dst_port is None:
            self.resend_packet(msg, ALL)
            self.logger.info("Broadcasting %s.%i -> %s.%i",
                             src, msg.in_port, dst, ALL)
        else:
            # Both directions at once: dst -> src and src -> dst.
            self.install(dp, msg.in_port, src=dst, dst=src)
            self.install(dp, dst_port, src=src, dst=dst, msg=msg)
            self.logger.info("Installing %s.%i -> %s.%i AND %s.%i -> %s.%i",
                             dst, dst_port, src, msg.in_port,
                             src, msg.in_port, dst, dst_port)

    # ----- OpenFlow events -------------------------------------------------

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features(self, ev):
        dp = ev.msg.datapath
        self.datapaths[dp.id] = dp
        self.logger.info("Switch %016x connected.", dp.id)
        self.clear_flows(dp)

    @set_ev_cls(ofp_event.EventOFPStateChange, DEAD_DISPATCHER)
    def switch_gone(self, ev):
        dp = ev.datapath
        if dp.id in self.datapaths:
            del self.datapaths[dp.id]
            self.logger.info("Switch %016x disconnected.", dp.id)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in(self, ev):
        if self.mode is None:
            return
        msg = ev.msg
        eth = packet.Packet(msg.data).get_protocol(ethernet.ethernet)
        if eth is None:
            return
        handler = getattr(self, self.mode[3:].lower())
        handler(msg, eth.src, eth.dst)


class TutorialRest(ControllerBase):
    """Small control API used by `csci60 ryu mode ...`."""

    def __init__(self, req, link, data, **config):
        super(TutorialRest, self).__init__(req, link, data, **config)
        self.app = data[APP_KEY]

    @staticmethod
    def _json(obj, status=200):
        return Response(status=status, content_type="application/json",
                        charset="utf-8", body=json.dumps(obj).encode())

    @route("csci60", "/csci60/modes", methods=["GET"])
    def modes(self, req, **kwargs):
        return self._json({"active": self.app.mode,
                           "modes": list(self.app.MODES)})

    @route("csci60", "/csci60/mode", methods=["POST"])
    def mode(self, req, **kwargs):
        try:
            mode = json.loads(req.body.decode() or "{}").get("mode")
            self.app.set_mode(mode)
        except ValueError as exc:
            return self._json({"error": str(exc)}, status=400)
        return self._json({"active": self.app.mode})

    @route("csci60", "/csci60/clear", methods=["POST"])
    def clear(self, req, **kwargs):
        self.app.clear_all_flows()
        return self._json({"switches": len(self.app.datapaths)})

    @route("csci60", "/csci60/switches", methods=["GET"])
    def switches(self, req, **kwargs):
        return self._json(["%016x" % d for d in sorted(self.app.datapaths)])
