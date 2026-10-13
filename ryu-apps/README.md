# CSCI 60 Ryu apps

The CSCI 60 SDN controller apps, ported from POX
([hip2b2/poxstuff](https://github.com/hip2b2/poxstuff)) to
[Ryu](https://ryu-sdn.org/) 4.34, OpenFlow 1.0.

The lab server setup (`setup/README.md`, step 8) copies this folder to
`/opt/csci60/ryu-apps`. Students start the apps by name:

```bash
csci60 ryu apps                      # list them
csci60 ryu start sw_tutorial         # run one in the foreground (Ctrl-C stops it)
csci60 ryu start simple_switch -d    # run one in the background
csci60 ryu logs                      # follow a background controller's output (Ctrl-C to quit)
csci60 ryu stop                      # stop all controllers
```

Ryu runs in a container (`csci60/ryu`), with the server's network, listening for
OpenFlow on port 6633 (`--port` for another one).

## The apps

| App                 | POX original              | What it does                                      | Used in |
| ------------------- | ------------------------- | ------------------------------------------------- | ------- |
| `sw_tutorial`       | `of_sw_tutorial_oo.py`    | Six hub/switch behaviours, switchable at run time | Lab 2   |
| `simple_switch`     | `of_switch_flow.py`       | Plain MAC-learning switch, one flow per pair      | multi-controller exercise, general use |
| `firewall`          | `of_firewall.py`          | Learning switch + inbound per-port IP rules       | SDN exercises |
| `flow_stats`        | `flow_stats.py`           | Every 5 s, asks switches for flow and port stats; reports web (TCP 80) traffic | SDN exercises, run next to a switch app |
| `pong`              | `pong2.py`                | Controller answers every ARP and ping itself      | SDN exercises |

`ping_and_drop.py` and `of_sw_tutorial.py` / `of_sw_tutorial_resend.py` in
the POX repo are earlier versions of the above, and are covered by
`sw_tutorial` (modes `SW_DUMBHUB` ... `SW_IDEALPAIRSWITCH`).

## sw_tutorial (Lab 2)

| POX console (old)                                       | csci60 (new)                      |
| ------------------------------------------------------- | --------------------------------- |
| `./pox.py py --completion log.level --DEBUG of_sw_tutorial_oo` | `csci60 ryu start sw_tutorial` |
| `MySwitch.list_available_listeners()`                   | `csci60 ryu modes`                |
| `MySwitch.clear_all_flows()`                            | `csci60 ryu clear`                |
| `MySwitch.detach_packetin_listener()` + `MySwitch.attach_packetin_listener('SW_LAZYHUB')` | `csci60 ryu mode SW_LAZYHUB` (also clears flows) |
| `exit()`                                                | Ctrl-C                            |

The modes are the same as in POX:

| Mode                  | Behaviour                                                         |
| --------------------- | ----------------------------------------------------------------- |
| `SW_DUMBHUB`          | every packet goes to the controller and is flooded; no flows      |
| `SW_PAIRHUB`          | flows per (source MAC, destination MAC) pair that flood           |
| `SW_LAZYHUB`          | one flow that floods everything                                   |
| `SW_BADSWITCH`        | flows only on destination MAC (find out what is wrong!)            |
| `SW_PAIRSWITCH`       | flows per MAC pair that forward to the right port                  |
| `SW_IDEALPAIRSWITCH`  | like `SW_PAIRSWITCH`, but installs both directions at once (default) |

The log lines keep POX's format, so Lab 2's OUTPUT A / OUTPUT B comparison
reads the same:

```text
Installing 00:00:00:00:00:01.1 -> 00:00:00:00:00:02.2
Broadcasting 00:00:00:00:00:01.1 -> ff:ff:ff:ff:ff:ff.65532
```

`ff:ff:ff:ff:ff:ff` means "any MAC" and port `65532` means "all ports"
(OpenFlow 1.0 `OFPP_ALL`).

## firewall

```bash
csci60 ryu start firewall -d
csci60 start --topo single,3 --mac --controller remote -d
csci60 ryu ctl /csci60/firewall/add '{"proto": "icmp", "in_port": 1}'
csci60 ryu ctl /csci60/firewall/add '{"proto": "icmp", "in_port": 2}'
csci60 cli         # pingall: only h1 <-> h2 work
csci60 ryu ctl /csci60/firewall          # list rules
csci60 ryu ctl /csci60/firewall/delete '{"proto": "icmp", "in_port": 1}'
csci60 ryu ctl /csci60/firewall/clear '{}'
```

| Field     | Meaning                                                | Default |
| --------- | ------------------------------------------------------ | ------- |
| `proto`   | `icmp`, `tcp`, `udp`, or an IP protocol number         | `icmp`  |
| `tp_src`  | TCP/UDP source port, or ICMP type; `0` = any           | `0`     |
| `in_port` | switch port the packet comes **in** on; `0` = any      | `0`     |
| `dpid`    | switch id (`1` for `s1`); `0` = every switch           | `0`     |

Rules are inbound only, as in the POX original: for a ping between h1 and h2,
both the request (in on port 1) and the reply (in on port 2) need a rule.
With no rules all IP traffic is dropped; ARP still works.

These calls replace POX's `AddRule(...)`, `DeleteRule(...)` and
`ShowRules()` typed into the POX console.

## Writing your own app

Copy `simple_switch.py`, change it, and start it by path:

```bash
cp /opt/csci60/ryu-apps/apps/simple_switch.py ~/myswitch.py
csci60 ryu start ~/myswitch.py
```

Several apps can run together: `csci60 ryu start simple_switch flow_stats`.

### POX to Ryu cheat sheet

| POX                                         | Ryu (OpenFlow 1.0)                                      |
| ------------------------------------------- | ------------------------------------------------------- |
| `def launch(): core.openflow.addListenerByName("PacketIn", f)` | `class App(app_manager.RyuApp)` + `@set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)` |
| `ConnectionUp` event                        | `EventOFPSwitchFeatures` (`CONFIG_DISPATCHER`)          |
| `event.connection`, `event.dpid`            | `ev.msg.datapath`, `datapath.id`                        |
| `event.parsed`                              | `packet.Packet(msg.data)`, then `get_protocol(ethernet.ethernet)` |
| `event.port`                                | `msg.in_port`                                           |
| `of.ofp_flow_mod()`, `msg.match.dl_dst = x` | `parser.OFPFlowMod(datapath, match=parser.OFPMatch(dl_dst=haddr_to_bin(x)), ...)` |
| `of.ofp_action_output(port=p)`              | `parser.OFPActionOutput(p)`                             |
| `of.ofp_packet_out(resend=event.ofp)`       | `parser.OFPPacketOut(datapath, buffer_id=msg.buffer_id, in_port=msg.in_port, actions=..., data=...)` |
| `of.OFPP_ALL`, `of.OFPP_FLOOD`              | `ofproto.OFPP_ALL`, `ofproto.OFPP_FLOOD`                |
| `connection.send(of.ofp_stats_request(body=of.ofp_flow_stats_request()))` | `datapath.send_msg(parser.OFPFlowStatsRequest(datapath, 0, parser.OFPMatch(), 0xff, ofproto.OFPP_NONE))` |
| `Timer(5, f, recurring=True)`               | `hub.spawn` + `hub.sleep(5)` loop                        |
| `log.debug(...)`                            | `self.logger.info(...)`                                 |

## Testing an app

On the lab server:

```bash
csci60 ryu start simple_switch -d
csci60 start --topo single,3 --controller remote --test pingall   # expect 0% dropped
csci60 ryu stop
```

## License

The POX originals are GPLv3 (POX tutorial code by James McCauley and the
CSCI 60 versions by William Emmanuel Yu). These ports keep that license.
