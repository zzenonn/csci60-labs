# CSCI 60 Network Labs

The CSCI 60 network labs on a **Rocky Linux** server with **Containerlab**,
**Open vSwitch** and the **Ryu** SDN controller. This replaces the old Mininet
VM + POX setup.

Students get one command, `csci60`. It works the way Mininet did:

| Mininet / POX (old)                                   | csci60 (new)                                               |
| ----------------------------------------------------- | ---------------------------------------------------------- |
| `sudo mn --test pingall --topo single,3`              | `csci60 start --test pingall --topo single,3`              |
| `sudo mn --topo single,3 --mac --controller remote`   | `csci60 start --topo single,3 --mac --controller remote`   |
| `sudo python lab4.py`                                 | `csci60 run lab4.py`                                       |
| `mininet>` console (`pingall`, `h1 ping h2`, `net`)   | `csci60>` console, same commands                           |
| `xterm h1`                                            | `csci60 shell h1` (in a second SSH session)                |
| `./pox.py ... of_sw_tutorial_oo`                      | `csci60 ryu start sw_tutorial`                             |
| `MySwitch.attach_packetin_listener('SW_LAZYHUB')`     | `csci60 ryu mode SW_LAZYHUB`                               |
| `sudo mn -c` / `sudo killall controller`              | `csci60 reset`                                             |

Mininet Python scripts (`from mininet.net import Mininet`) run unchanged under
`csci60 run`, including the original course scripts in
[hip2b2/poxstuff](https://github.com/hip2b2/poxstuff).

## Students: start here

```bash
ssh <username>@<lab-server>
git clone https://github.com/zzenonn/csci60-labs.git
cd csci60-labs
csci60 doctor            # should end with "All good."
```

Then read, in order:

1. [Getting started with csci60](setup/docs/getting-started.md)
   (the old *Introduction to Mininet*, redone for csci60)
2. [Lab 2: Hubs and switches with OpenFlow](lab2-hubs-switches/README.md)
3. [Lab 3: TCP/IP addressing](lab3-ip-addressing/README.md)
4. [Lab 4: TCP/IP routing](lab4-ip-routing/README.md)

Every step is a command you type yourself.

## What is in here

| Folder                | What it is                                                         |
| --------------------- | ------------------------------------------------------------------ |
| `lab2-hubs-switches/` | Lab 2 handout                                                      |
| `lab3-ip-addressing/` | Lab 3 handout                                                      |
| `lab4-ip-routing/`    | Lab 4 handout and `lab4.py`                                        |
| `ryu-apps/`           | The POX controller apps, ported to Ryu                             |
| `setup/README.md`     | Lab server setup, one command at a time (instructors)              |
| `setup/docs/`         | Getting started, how the pieces fit, instructor notes              |
| `setup/toolkit/`      | The `csci60` command and the Mininet-compatible Python API         |
| `setup/images/`       | Container images for lab hosts and for Ryu                         |
| `setup/examples/`     | Every script from the Mininet deck, runnable with `csci60 run`     |

## Instructors

Set up a server with [setup/README.md](setup/README.md). Give each student
their own small server or VM, as with the Mininet VM; see
[instructor notes](setup/docs/instructor-notes.md).
[How the pieces fit together](setup/docs/how-it-fits.md) explains what
`csci60` does behind the scenes.

Tested on Rocky Linux 10.2 with Docker 29.9, Open vSwitch 3.5.3 (CentOS NFV
SIG), Containerlab 0.81.0 and Ryu 4.34, SELinux enforcing.
