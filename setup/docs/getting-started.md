# CSCI 60: Getting Started with csci60 (Containerlab)

*Replaces "CSCI 60: Introduction to Mininet". The same topics, in the same
order, for the new lab server.*

---

## 1. Software Defined Networks

- SDN separates the **control plane** (deciding where packets go) from the
  **data plane** (moving packets).
- A **controller** programs **switches** using the **OpenFlow** protocol.
- It lets us build network test beds quickly and try out new protocols and
  topologies, without real equipment.

## 2. The tools behind csci60

You only type `csci60`. Behind it:

| Piece            | Role                                                    | Old equivalent    |
| ---------------- | ------------------------------------------------------- | ----------------- |
| **Containerlab** | Builds the network: hosts, switches, links              | Mininet           |
| **Open vSwitch** | The switches (`s1`, `s2`, ...), speaking OpenFlow 1.0   | Open vSwitch      |
| **Containers**   | The hosts (`h1`, `h2`, ...): small Linux machines       | Mininet hosts     |
| **Ryu**          | The SDN controller, programmed in Python                | POX               |

Each host is a real, separate Linux network stack: its own interfaces,
IP addresses, routing table and processes, running on one server.

## 3. Getting connected

There is no VM to download any more. Your instructor gives you an account on
the lab server.

```bash
ssh <username>@<lab-server>
csci60 doctor          # should end with "All good."
```

Get your own copy of the course repository (handouts, scripts and these
notes). Do this once:

```bash
git clone https://github.com/zzenonn/csci60-labs.git
cd csci60-labs
```

The examples below (`examples/python/...`) are in `setup/examples/python/`.

Windows: use the built-in `ssh` in PowerShell / Windows Terminal, or PuTTY.

## 4. Is it working?

```bash
csci60 start --test pingall --topo single,3
```

This will:

- create a network with 3 hosts connected to a single switch,
- ping from every host to every other host,
- remove the network again.

It uses the built-in controller (a normal learning switch), so it should
always work.

```text
*** Creating network
*** Adding switches: s1
*** Adding hosts: h1 h2 h3
*** Adding links: (h1, s1) (h2, s1) (h3, s1)
*** Configuring hosts
*** Starting 1 switches
*** Controllers: c0(built-in)
*** Ping: testing ping reachability
h1 -> h2 h3
h2 -> h1 h3
h3 -> h1 h2
*** Results: 0% dropped (6/6 received)
*** Stopping network 'csci60'
*** Done
```

## 5. Basic interactive commands

Leave out `--test` to get the interactive console:

```bash
csci60 start --topo single,3
csci60>
```

| Command                    | What it does                                               |
| -------------------------- | ---------------------------------------------------------- |
| `help`                     | list the console commands                                  |
| `nodes`                    | list the nodes                                             |
| `net`                      | show the links of each node                                |
| `links`                    | show every link and whether it is up                       |
| `dump`                     | show interfaces and IP addresses of each node              |
| `<node> ifconfig`          | configure / show interfaces (like Linux `ifconfig`)        |
| `<node> route`             | show / edit the routing table (like Linux `route`)         |
| `<node> ping <node>`       | ping between two nodes; host names are replaced by their IP |
| `pingall`                  | ping between all hosts                                     |
| `iperf <node> <node>`      | measure TCP bandwidth between two hosts                    |
| `link s1 h2 down` / `up`   | unplug / plug a cable                                      |
| `dpctl dump-flows`         | show the OpenFlow table of every switch                    |
| `sh <command>`             | run a command on the server itself                         |
| `exit` (or Ctrl-D)         | stop the network and leave                                 |

**xterm**: there is no graphical desktop on the server. Open a second SSH
session and run `csci60 shell h1` to get a shell inside `h1`.

## 6. Basic command line

| Option                    | Meaning                                                            |
| ------------------------- | ------------------------------------------------------------------ |
| `--topo`                  | the topology to build when the network starts                      |
| `--switch`                | accepted for compatibility; the switch is always Open vSwitch      |
| `--controller`            | `default` (built-in learning switch) or `remote` (Ryu, port 6633)  |
| `--mac`                   | easy-to-read MACs: `h1` = `00:00:00:00:00:01`, ...                 |
| `--link tc,bw=10,delay=10ms` | bandwidth (Mbit/s), delay, loss (%) on every link               |
| `-d`                      | leave the network running and return to the shell; reopen the console with `csci60 cli` |

## 7. Some topologies to try out

| Command                                     | Network                                                   |
| ------------------------------------------- | --------------------------------------------------------- |
| `csci60 start --topo minimal`               | 2 hosts on 1 switch                                       |
| `csci60 start --topo single,3`              | 3 hosts on 1 switch                                       |
| `csci60 start --topo linear,4`              | 4 switches in a line, one host on each                    |
| `csci60 start --topo tree,depth=2,fanout=2` | a tree of switches, 2 levels deep, 2 branches per switch  |

Each of these is also a Python script in `examples/python/`:

```python
from mininet.net import Mininet
from mininet.topo import LinearTopo

Linear4 = LinearTopo(k=4)
net = Mininet(topo=Linear4)
net.start()
net.pingAll()
net.stop()
```

To run a script: `csci60 run linear4.py` (instead of `sudo python linear4.py`).

The `mininet` import name is kept on purpose, so scripts from the old course
material and from the internet work as they are.

## 8. Any topology

```python
from mininet.net import Mininet
from mininet.cli import CLI

net = Mininet()
# Creating nodes in the network.
c0 = net.addController()
h0 = net.addHost('h0')
s0 = net.addSwitch('s0')
h1 = net.addHost('h1')
# Creating links between nodes in network
net.addLink(h0, s0)
net.addLink(h1, s0)
# Configuration of IP addresses in interfaces
h0.setIP('192.168.1.1', 24)
h1.setIP('192.168.1.2', 24)

net.start()
net.pingAll()
CLI(net)      # interactive console; leave it out to stop right away
net.stop()
```

What does this network look like? (`examples/python/custom.py`)

## 9. Setting performance limits

```python
from mininet.net import Mininet
from mininet.node import CPULimitedHost
from mininet.link import TCLink

net = Mininet(host=CPULimitedHost, link=TCLink)
c0 = net.addController()
s0 = net.addSwitch('s0')
h0 = net.addHost('h0')
h1 = net.addHost('h1', cpu=0.5)
h2 = net.addHost('h2', cpu=0.5)
net.addLink(s0, h0, bw=10, delay='5ms', max_queue_size=1000, loss=10, use_htb=True)
net.addLink(s0, h1)
net.addLink(s0, h2)
net.start()
net.pingAll()
net.stop()
```

- **cpu**: share of one CPU for that host (0.5 = half a CPU)
- **bw**: bandwidth in Mbit/s
- **delay**: delay, e.g. `'5ms'`
- **max_queue_size**: queue length in packets
- **loss**: packet loss in percent

(`examples/python/perf.py`; with `loss=10` some pings will fail. That is the point.)

## 10. Testing your networks

```python
from mininet.util import dumpNodeConnections

dumpNodeConnections(net.hosts)   # print each host's links
net.pingAll()                    # ping from all hosts to all hosts
net.ping((h0, h1))               # ping from one host to another
net.iperf((h0, h1))              # TCP bandwidth from one host to another
```

## 11. Running Python in the console

```text
csci60> py net.pingAll()
csci60> px from mininet.util import dumpNodeConnections
csci60> py dumpNodeConnections(net.hosts)
csci60> py h1.cmd('ip route')
```

`py` evaluates a Python expression, `px` runs a Python statement. `net` and
every node name (`h1`, `s1`, ...) are already defined.

## 12. Other things

- **Remote controller**: `Mininet(controller=RemoteController)` with
  `net.addController('c0', ip='127.0.0.1', port=6633)` uses an external
  OpenFlow controller (Ryu) instead of the built-in one.
  Start Ryu first: `csci60 ryu start simple_switch`.
  (`examples/python/remote_controller.py`)
- **Two controllers**: start a second Ryu with `--port 6644` and give each
  switch its own controller with `s0.start([c0])`, `s1.start([c1])`.
- **Ryu apps**: `csci60 ryu apps` lists the course apps. Write your own and
  start it with `csci60 ryu start ./myapp.py`.
- **OVSSwitch** is the only switch type. `UserSwitch` and `OVSKernelSwitch`
  are accepted and mean the same thing.

## 13. Exercises

- Write Python scripts for these topologies:
  `--topo tree,depth=2,fanout=3` and `--topo single,5`.
- Create your own topology: 2 switches connected to each other with 3 hosts
  each (`examples/python/two_switches.py` is one answer).
- Which network "performs" better: `tree,depth=2,fanout=2`, `single,4` or
  `linear,4`? Use `iperf` and `ping` to find out, then try again with
  `--link tc,bw=10,delay=10ms`.

---

## FAQ

1. **How do I get files to and from the server?**
   `scp` (Linux/macOS/Windows PowerShell) or WinSCP. Example:
   `scp lab4.py <username>@<lab-server>:~/`

2. **`csci60: network 'csci60' is still running`?**
   You left a network running (`-d`, or a closed SSH window).
   `csci60 cli` reopens it; `csci60 stop` removes it.

3. **Something is stuck or behaving strangely.**
   `csci60 reset` removes every network and controller you started.
   This replaces `sudo mn -c` and `sudo killall controller`.

4. **`pingall` fails with `--controller remote`.**
   Is the controller running? `csci60 status` shows it. Start it with
   `csci60 ryu start <app>` (for example `simple_switch`).

5. **The controller output scrolled away.**
   `csci60 ryu logs` shows it again (for one started with `-d`).

6. **`xterm` does not open.**
   No graphics on the server. Use `csci60 shell <host>` in a second SSH
   session.

7. **Where is POX?**
   Replaced by Ryu. The course POX apps are ported; see `ryu-apps/` in the
   course repository and `csci60 ryu apps`.
