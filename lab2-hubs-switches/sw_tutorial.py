# Copyright 2012 James McCauley, William Yu (original POX version)
# os-ken / OpenFlow 1.3 version for CSCI 60, 2026.
#
# Licensed under the GNU General Public License v3 or later, like the POX
# original (of_sw_tutorial_oo.py in hip2b2/poxstuff).
"""Switch / Hub Teaching Demo (Lab 2): an OpenFlow 1.3 controller app.

Six forwarding behaviours, switchable while the network is running:

  SW_DUMBHUB          every packet goes to the controller, which floods it.
                      No flows are installed.
  SW_PAIRHUB          installs a flood flow per (source MAC, destination MAC).
  SW_LAZYHUB          installs one flood flow that matches every packet.
  SW_BADSWITCH        installs flows on destination MAC only. Find the problem!
  SW_PAIRSWITCH       learns MACs; installs a flow per (source, destination)
                      that forwards to the right port.
  SW_IDEALPAIRSWITCH  like SW_PAIRSWITCH but installs both directions at once.

Run it (it listens for switches on TCP port 6653):
    python3 sw_tutorial.py

It starts with no switch type attached. Type commands at its prompt:
    modes                 list the switch types and show the active one
    mode SW_DUMBHUB       clear all flows, then attach that switch type
    clear                 clear all flows
    detach                stop handling packets

Every packet the switch has no flow for goes to the controller, because of
one flow this app installs on every switch: the *table-miss* flow (priority
0, matches everything, action: send to controller). It is the one flow you
see in the switch even with SW_DUMBHUB.

Log lines:
    Installing <src MAC>.<in port> -> <dst MAC>.<out port>
    Broadcasting / Sending ...
ff:ff:ff:ff:ff:ff means "any MAC" and port ALL means "all ports".
"""

import os
import sys
import threading
import time

from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import (CONFIG_DISPATCHER, DEAD_DISPATCHER,
                                       MAIN_DISPATCHER, set_ev_cls)
from os_ken.lib.packet import ethernet, packet
from os_ken.ofproto import ofproto_v1_3

ANY_MAC = "ff:ff:ff:ff:ff:ff"
IDLE_TIMEOUT = 10
HARD_TIMEOUT = 30


class SwitchTutorial(app_manager.OSKenApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    MODES = ("SW_DUMBHUB", "SW_PAIRHUB", "SW_LAZYHUB", "SW_BADSWITCH",
             "SW_PAIRSWITCH", "SW_IDEALPAIRSWITCH")

    def __init__(self, *args, **kwargs):
        super(SwitchTutorial, self).__init__(*args, **kwargs)
        # (dpid, MAC) -> port where that MAC was last seen
        self.table = {}
        self.datapaths = {}
        self.mode = None
        self.logger.info("Switch / Hub Teaching Demo. No switch type attached.")
        self.logger.info("Commands: modes | mode <SW_...> | clear | detach")
        threading.Thread(target=self.console, daemon=True).start()

    # ----- the controller console ------------------------------------------

    def console(self):
        """Read commands typed at the controller, like the POX console."""
        while True:
            line = sys.stdin.readline()
            if not line:          # no terminal attached (stdin closed)
                return
            words = line.split()
            if not words:
                continue          # ENTER just separates the output
            cmd, arg = words[0].lower(), (words[1:] or [None])[0]
            try:
                if cmd == "modes":
                    self.logger.info("Available: %s", " ".join(self.MODES))
                    self.logger.info("Active: %s", self.mode)
                elif cmd == "mode" and arg:
                    self.set_mode(arg.upper())
                elif cmd == "clear":
                    self.clear_all_flows()
                elif cmd == "detach":
                    self.set_mode(None)
                else:
                    self.logger.info("Commands: modes | mode <SW_...> | "
                                     "clear | detach")
            except ValueError as exc:
                self.logger.info("%s", exc)

    # ----- helpers -------------------------------------------------------

    @staticmethod
    def port_name(dp, port):
        return "ALL" if port == dp.ofproto.OFPP_ALL else str(port)

    def log_flow(self, verb, dp, src, in_port, dst, out_port):
        self.logger.info("%s %s.%s -> %s.%s", verb, src, in_port, dst,
                         self.port_name(dp, out_port))

    def resend_packet(self, msg, out_port):
        """Send the packet that caused this PacketIn out of out_port."""
        dp = msg.datapath
        ofp, parser = dp.ofproto, dp.ofproto_parser
        data = msg.data if msg.buffer_id == ofp.OFP_NO_BUFFER else None
        out = parser.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id,
                                  in_port=msg.match["in_port"],
                                  actions=[parser.OFPActionOutput(out_port)],
                                  data=data)
        dp.send_msg(out)

    def add_flow(self, dp, priority, match, actions, idle=0, hard=0,
                 buffer_id=None):
        ofp, parser = dp.ofproto, dp.ofproto_parser
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        dp.send_msg(parser.OFPFlowMod(
            datapath=dp, priority=priority, match=match, instructions=inst,
            command=ofp.OFPFC_ADD, idle_timeout=idle, hard_timeout=hard,
            buffer_id=ofp.OFP_NO_BUFFER if buffer_id is None else buffer_id))

    def install(self, dp, out_port, src=None, dst=None, msg=None):
        """Install a flow; if msg is given, also forward that packet."""
        ofp, parser = dp.ofproto, dp.ofproto_parser
        fields = {}
        if src:
            fields["eth_src"] = src
        if dst:
            fields["eth_dst"] = dst
        buffer_id = ofp.OFP_NO_BUFFER
        if msg is not None and msg.buffer_id != ofp.OFP_NO_BUFFER:
            buffer_id = msg.buffer_id
        self.add_flow(dp, ofp.OFP_DEFAULT_PRIORITY, parser.OFPMatch(**fields),
                      [parser.OFPActionOutput(out_port)],
                      idle=IDLE_TIMEOUT, hard=HARD_TIMEOUT, buffer_id=buffer_id)
        # Open vSwitch does not buffer packets, so send this one ourselves.
        if msg is not None and buffer_id == ofp.OFP_NO_BUFFER:
            self.resend_packet(msg, out_port)

    def install_table_miss(self, dp):
        """Priority-0 flow: anything no other flow matches -> controller."""
        ofp, parser = dp.ofproto, dp.ofproto_parser
        self.add_flow(dp, 0, parser.OFPMatch(),
                      [parser.OFPActionOutput(ofp.OFPP_CONTROLLER,
                                              ofp.OFPCML_NO_BUFFER)])

    def clear_flows(self, dp):
        ofp, parser = dp.ofproto, dp.ofproto_parser
        dp.send_msg(parser.OFPFlowMod(datapath=dp, table_id=ofp.OFPTT_ALL,
                                      command=ofp.OFPFC_DELETE,
                                      out_port=ofp.OFPP_ANY,
                                      out_group=ofp.OFPG_ANY,
                                      match=parser.OFPMatch()))
        self.install_table_miss(dp)
        self.logger.info("Clearing all flows from %016x "
                         "(keeping the table-miss flow).", dp.id)

    def clear_all_flows(self):
        for dp in list(self.datapaths.values()):
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

    def dumbhub(self, msg, src, dst, in_port):
        dp = msg.datapath
        ALL = dp.ofproto.OFPP_ALL
        self.resend_packet(msg, ALL)
        self.log_flow("Broadcasting", dp, src, in_port, dst, ALL)

    def pairhub(self, msg, src, dst, in_port):
        dp = msg.datapath
        ALL = dp.ofproto.OFPP_ALL
        self.install(dp, ALL, src=src, dst=dst, msg=msg)
        self.log_flow("Installing", dp, src, in_port, dst, ALL)

    def lazyhub(self, msg, src, dst, in_port):
        dp = msg.datapath
        ALL = dp.ofproto.OFPP_ALL
        self.install(dp, ALL, msg=msg)
        self.log_flow("Installing", dp, ANY_MAC, in_port, ANY_MAC, ALL)

    def badswitch(self, msg, src, dst, in_port):
        dp = msg.datapath
        ALL = dp.ofproto.OFPP_ALL
        self.table[(dp.id, src)] = in_port
        # Flow towards the source, matching the destination MAC only.
        self.install(dp, in_port, dst=src)
        self.log_flow("Installing", dp, ANY_MAC, in_port, src, in_port)
        dst_port = self.table.get((dp.id, dst))
        if dst_port is None:
            self.resend_packet(msg, ALL)
            self.log_flow("Broadcasting", dp, src, in_port, dst, ALL)
        else:
            self.resend_packet(msg, dst_port)
            self.log_flow("Sending", dp, src, in_port, dst, dst_port)

    def pairswitch(self, msg, src, dst, in_port):
        dp = msg.datapath
        ALL = dp.ofproto.OFPP_ALL
        self.table[(dp.id, src)] = in_port
        dst_port = self.table.get((dp.id, dst))
        if dst_port is None:
            self.resend_packet(msg, ALL)
            self.log_flow("Broadcasting", dp, src, in_port, dst, ALL)
        else:
            self.install(dp, dst_port, src=src, dst=dst, msg=msg)
            self.log_flow("Installing", dp, src, in_port, dst, dst_port)

    def idealpairswitch(self, msg, src, dst, in_port):
        dp = msg.datapath
        ALL = dp.ofproto.OFPP_ALL
        self.table[(dp.id, src)] = in_port
        dst_port = self.table.get((dp.id, dst))
        if dst_port is None:
            self.resend_packet(msg, ALL)
            self.log_flow("Broadcasting", dp, src, in_port, dst, ALL)
        else:
            # Both directions at once: dst -> src and src -> dst.
            self.install(dp, in_port, src=dst, dst=src)
            self.install(dp, dst_port, src=src, dst=dst, msg=msg)
            self.logger.info("Installing %s.%s -> %s.%s AND %s.%s -> %s.%s",
                             dst, dst_port, src, in_port,
                             src, in_port, dst, dst_port)

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
        handler(msg, eth.src, eth.dst, msg.match["in_port"])


def main():
    """Start os-ken with this app (os-ken has no osken-manager command)."""
    from os_ken import cfg, log
    cfg.CONF(args=sys.argv[1:], project="os_ken")
    log.init_log()
    mgr = app_manager.AppManager.get_instance()
    mgr.load_apps([__name__])
    mgr.instantiate_apps(**mgr.create_contexts())
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    os._exit(0)


if __name__ == "__main__":
    main()
