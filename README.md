# CSCI 60 Network Labs

The CSCI 60 network labs on your own **Rocky Linux** virtual machine, using
**Containerlab** (hosts and links), **Open vSwitch** (switches) and the
**os-ken** SDN controller (Lab 2).

You use these tools directly. Every step is a command you type yourself.

## Start here

Work through, in order:

1. [Getting started](getting-started/README.md): set up your VM and build
   your first network
2. [Lab 2: Hubs and switches with OpenFlow](lab2-hubs-switches/README.md)
3. [Lab 3: TCP/IP addressing](lab3-ip-addressing/README.md)
4. [Lab 4: TCP/IP routing](lab4-ip-routing/README.md)

## What is in here

| Folder                | What it is                                                     |
| --------------------- | -------------------------------------------------------------- |
| `getting-started/`    | VM setup, first steps, and `first.clab.yml`: two hosts on one switch |
| `lab2-hubs-switches/` | Lab 2 handout, `lab2.clab.yml`, and `sw_tutorial.py` (the os-ken controller app) |
| `lab3-ip-addressing/` | Lab 3 handout and `lab3.clab.yml`                              |
| `lab4-ip-routing/`    | Lab 4 handout and `lab4.clab.yml`                              |
| `images/`             | Container images: lab hosts, and the os-ken controller         |

Only Lab 2 uses a controller. In Labs 3 and 4 the switches are normal
learning switches.

Tested on Rocky Linux 10.2 (x86_64 and ARM64) with Docker 29.9, Open vSwitch
3.5.3 (CentOS NFV SIG), Containerlab 0.81.0 and os-ken 4.2.2, SELinux enforcing.

`lab2-hubs-switches/sw_tutorial.py` is a port of `of_sw_tutorial_oo.py` from
[hip2b2/poxstuff](https://github.com/hip2b2/poxstuff) and is GPLv3, like the
original (see `lab2-hubs-switches/COPYING`).
