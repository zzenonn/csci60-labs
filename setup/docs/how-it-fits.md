# How the pieces fit together

```text
 student (SSH)
     |
     v
  csci60  ──────────────┬──────────────────────────────┐
  (one command)         |                              |
     |                  v                              v
     |          Containerlab                     Ryu controller
     |          builds the network               (container, host network,
     |            |            |                  OpenFlow on 6633, 6644, ...)
     |            v            v                       ^
     |      host containers   Open vSwitch bridges ────┘  OpenFlow 1.0
     |      h1, h2, ...       s1, s2, ...
     |      (Alpine Linux)    (on the server)
     |            \____ veth links ____/
     v
  csci60> console  (pingall, h1 ping h2, dpctl dump-flows, link s1 h2 down, ...)
```

## The repository

Everything is in one repository, `csci60-labs`:

| Folder                 | Installed where                       | Used by                         |
| ---------------------- | ------------------------------------- | ------------------------------- |
| `setup/`               | `/opt/csci60/toolkit` and `/usr/bin/csci60`, once per server (`setup/README.md`) | every lab: the `csci60` command |
| `ryu-apps/`            | `/opt/csci60/ryu-apps`, once per server | `csci60 ryu start <app>`      |
| `lab2-hubs-switches/`  | students read it in their own clone   | Lab 2 handout                   |
| `lab3-ip-addressing/`  | students read it in their own clone   | Lab 3 handout                   |
| `lab4-ip-routing/`     | students read it in their own clone   | Lab 4 handout + `lab4.py`       |

Each lab folder holds only its handout and, for Lab 4, its topology script.
Students type every command themselves; nothing is hidden in a script.

## What happens on `csci60 start --topo single,3`

1. The topology (`single,3`) becomes a list of hosts, switches and links,
   exactly as in Mininet (`h1`..`h3`, `s1`, `h1-eth0 <-> s1-eth1`, ...).
2. `csci60` writes a Containerlab topology file to
   `/var/lib/csci60/labs/csci60/csci60.clab.yml` and runs
   `containerlab deploy`. Hosts become containers (`kind: linux`, image
   `csci60/host`), switches become Open vSwitch bridges (`kind: ovs-bridge`).
3. Each host gets Mininet's addresses (`10.0.0.N/8`, and with `--mac`
   `00:00:00:00:00:0N`) and link limits (`tc`: `bw`, `delay`, `loss`).
4. Each switch is set to OpenFlow 1.0 with Mininet's datapath ids
   (`s1` = `0000000000000001`), then:
   * `--controller default`: OVS acts as a normal learning switch
     (fail mode standalone). This replaces Mininet's reference controller.
   * `--controller remote`: OVS connects to `tcp:127.0.0.1:6633`
     (fail mode secure, so with no controller nothing is forwarded).
5. The `csci60>` console starts. `h1 ping h2` runs `ping 10.0.0.2` inside the
   `h1` container.
6. `exit` (or `csci60 stop`) runs `containerlab destroy` and removes the
   bridges.

## Mininet scripts

`csci60 run lab4.py` runs the script with Python 3 as root. A small
compatibility package named `mininet` (in `toolkit/compat/mininet`) maps
`Mininet`, `addHost`, `addSwitch`, `addLink`, `addController`, `setIP`,
`cmd`, `CLI`, `RemoteController`, `TCLink`, `CPULimitedHost`, `LinearTopo`,
`TreeTopo`, `dumpNodeConnections`, ... onto the same machinery.
Python 2 `print` statements are the one thing that needs editing.

## Ryu

Ryu runs in a container (`csci60/ryu`, Ryu 4.34 on Python 3.9) with host
networking, so switches reach it on `127.0.0.1:6633`. `csci60 ryu start`
mounts the app file(s) into the container. Apps in `ryu-apps/` that
need to be steered at run time (Lab 2's mode switch, the firewall rules) have
a small REST API on port 8080 that `csci60 ryu mode` / `csci60 ryu ctl` call.
This replaces typing Python into the POX console.

## What is not the same as Mininet

| Mininet                               | csci60                                               |
| ------------------------------------- | ---------------------------------------------------- |
| `xterm h1` opens a window             | `csci60 shell h1` in a second SSH session            |
| hosts share the server's filesystem   | each host has its own small filesystem (copy files in with `docker cp`, or use the `csci60>` console) |
| `--switch user` (user-space switch)   | always the Open vSwitch kernel datapath              |
| one network per VM                    | one network per server at a time; give each student their own small server/VM (see `instructor-notes.md`) |
| Python 2 (old VM)                     | Python 3                                             |
