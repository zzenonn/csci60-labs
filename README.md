# CSCI 60 Network Labs

The CSCI 60 network labs on a **Rocky Linux** server, using
**Containerlab** (hosts and links), **Open vSwitch** (switches) and the
**Ryu** SDN controller (Lab 2).

Students use these tools directly. Every step is a command you type yourself.

## Students: start here

```bash
ssh <username>@<lab-server>
git clone https://github.com/zzenonn/csci60-labs.git
cd csci60-labs
```

Then work through, in order:

1. [Getting started](getting-started/README.md): build your first network
2. [Lab 2: Hubs and switches with OpenFlow](lab2-hubs-switches/README.md)
3. [Lab 3: TCP/IP addressing](lab3-ip-addressing/README.md)
4. [Lab 4: TCP/IP routing](lab4-ip-routing/README.md)

## What is in here

| Folder                | What it is                                                     |
| --------------------- | -------------------------------------------------------------- |
| `getting-started/`    | First steps, and `first.clab.yml`: two hosts on one switch     |
| `lab2-hubs-switches/` | Lab 2 handout, `lab2.clab.yml`, and `sw_tutorial.py` (the Ryu controller app) |
| `lab3-ip-addressing/` | Lab 3 handout and `lab3.clab.yml`                              |
| `lab4-ip-routing/`    | Lab 4 handout and `lab4.clab.yml`                              |
| `setup/`              | Lab server setup, one command at a time (instructors)          |
| `setup/images/`       | Container images: lab hosts, and Ryu                           |

Only Lab 2 uses a controller. In Labs 3 and 4 the switches are normal
learning switches.

## Instructors

Set up a server with [setup/README.md](setup/README.md). Give each student
their own small server or VM: students need `sudo`, and the labs use fixed
names (`s1`, `h1`), so two students cannot share one server.

Tested on Rocky Linux 10.2 with Docker 29.9, Open vSwitch 3.5.3 (CentOS NFV
SIG), Containerlab 0.81.0 and Ryu 4.34, SELinux enforcing.

`lab2-hubs-switches/sw_tutorial.py` is a port of `of_sw_tutorial_oo.py` from
[hip2b2/poxstuff](https://github.com/hip2b2/poxstuff) and is GPLv3, like the
original (see `lab2-hubs-switches/COPYING`).
