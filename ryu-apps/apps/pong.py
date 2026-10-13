# Copyright 2012 James McCauley (original POX version)
# Ryu port for CSCI 60, 2026. GPLv3 or later, like the POX original.
"""Answer every ARP and ping from the controller (from pong2.py).

Hosts can ping any address, even ones that do not exist, because the
controller itself sends the replies. Nothing else works: TCP and UDP
packets are only logged. A good way to see that the controller, not the
switch, is in charge.

    csci60 ryu start pong
    csci60> h1 ping -c2 10.99.99.99     (replies come from the controller)
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, set_ev_cls
from ryu.lib.packet import arp, ethernet, icmp, ipv4, packet, tcp, udp
from ryu.ofproto import ether, inet, ofproto_v1_0

FAKE_MAC = "02:00:de:ad:be:ef"


class Pong(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Pong, self).__init__(*args, **kwargs)
        self.logger.info("Pong component running.")

    def reply(self, msg, pkt):
        dp = msg.datapath
        p = dp.ofproto_parser
        pkt.serialize()
        dp.send_msg(p.OFPPacketOut(
            datapath=dp, buffer_id=dp.ofproto.OFP_NO_BUFFER,
            in_port=dp.ofproto.OFPP_NONE, data=pkt.data,
            actions=[p.OFPActionOutput(msg.in_port)]))

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in(self, ev):
        msg = ev.msg
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        a = pkt.get_protocol(arp.arp)
        if a and a.opcode == arp.ARP_REQUEST:
            out = packet.Packet()
            out.add_protocol(ethernet.ethernet(
                ethertype=ether.ETH_TYPE_ARP, dst=a.src_mac, src=FAKE_MAC))
            out.add_protocol(arp.arp(
                opcode=arp.ARP_REPLY, src_mac=FAKE_MAC, src_ip=a.dst_ip,
                dst_mac=a.src_mac, dst_ip=a.src_ip))
            self.reply(msg, out)
            self.logger.info("%s ARPed for %s", a.src_ip, a.dst_ip)
            return
        ip = pkt.get_protocol(ipv4.ipv4)
        ic = pkt.get_protocol(icmp.icmp)
        if ip and ic and ic.type == icmp.ICMP_ECHO_REQUEST:
            out = packet.Packet()
            out.add_protocol(ethernet.ethernet(
                ethertype=ether.ETH_TYPE_IP, dst=eth.src, src=eth.dst))
            out.add_protocol(ipv4.ipv4(
                proto=inet.IPPROTO_ICMP, src=ip.dst, dst=ip.src))
            out.add_protocol(icmp.icmp(
                type_=icmp.ICMP_ECHO_REPLY, code=0, data=ic.data))
            self.reply(msg, out)
            self.logger.info("%s pinged %s", ip.src, ip.dst)
            return
        t = pkt.get_protocol(tcp.tcp)
        u = pkt.get_protocol(udp.udp)
        if ip and t:
            self.logger.info("tcp found: %s:%s to %s:%s", ip.src, t.src_port,
                             ip.dst, t.dst_port)
        elif ip and u:
            self.logger.info("udp found: %s:%s to %s:%s", ip.src, u.src_port,
                             ip.dst, u.dst_port)
