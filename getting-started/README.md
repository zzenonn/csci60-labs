# CSCI 60: Getting Started

You will set up your own lab machine, a Rocky Linux virtual machine (VM) on
your computer, then build your first network on it. The labs build on this.

Every step is a command you type yourself. Type them one at a time and check
each result before going on.

## 1. What you will use

| Tool             | What it does                                                  |
| ---------------- | ------------------------------------------------------------- |
| **Containerlab** | Builds a network from a topology file: hosts and the links between them |
| **Docker**       | Runs each host as a *container*: a small Linux machine with its own network interfaces, addresses and routing table |
| **Open vSwitch** | Provides the switches (`s1`, `s2`, ...)                       |
| **os-ken**       | An SDN controller framework: a Python program that tells OpenFlow switches what to do (Lab 2 only) |

Everything runs inside your VM, but each host behaves like a separate
computer. A command you run "on h1" sees only h1's interfaces and routes.

## 2. Create the VM

Install a hypervisor and create a VM from the Rocky Linux 10 DVD or minimal
ISO (<https://rockylinux.org/download>):

| Your computer                    | Hypervisor                         | Rocky Linux ISO |
| -------------------------------- | ---------------------------------- | --------------- |
| Windows or Linux, Intel/AMD      | VirtualBox or VMware Workstation   | x86_64          |
| Mac with Apple silicon (M1 to M4)| UTM or VMware Fusion               | ARM64 (aarch64) |
| Mac with Intel                   | VirtualBox or VMware Fusion        | x86_64          |

- 2 CPUs, 4 GB RAM, 20 GB disk.
- Network: NAT (the default) is enough. The VM needs internet access for
  this setup.
- During installation, create a user and tick **Make this user
  administrator**. You need `sudo` for everything below.

Rocky Linux 10 needs a CPU from about 2013 or later (x86-64-v3). If the
installer refuses to start on an older Intel/AMD computer, use Rocky Linux 9
instead: the steps are the same.

Log in to the VM at its console, or with `ssh` from your computer.

## 3. Get the course files

```bash
sudo dnf -y install git
git clone https://github.com/zzenonn/csci60-labs.git
cd csci60-labs
```

The repository is private: log in with your GitHub account (a personal access
token works as the password). The rest of this guide runs from this
`csci60-labs` folder.

## 4. Install the tools

This takes about 10 minutes, most of it downloads.

### 4.1 Base packages

```bash
sudo dnf -y install dnf-plugins-core iproute tar curl nano
```

### 4.2 Kernel modules

The Linux kernel needs these modules. Some are in the `kernel-modules-extra`
package, which a minimal install leaves out:

| Module         | Needed for                                           |
| -------------- | ---------------------------------------------------- |
| `openvswitch`  | Open vSwitch                                         |
| `br_netfilter` | Docker networking                                    |
| `xt_addrtype`  | Docker networking (without it Docker will not start) |
| `sch_netem`    | link speed and delay (`tc ... netem`, section 10)    |

```bash
sudo dnf -y install kernel-modules-extra-$(uname -r)
printf '%s\n' openvswitch br_netfilter xt_addrtype sch_netem | sudo tee /etc/modules-load.d/csci60.conf
sudo modprobe -a openvswitch br_netfilter xt_addrtype sch_netem
lsmod | grep -E 'openvswitch|br_netfilter|xt_addrtype|sch_netem'
```

The last command should list all four modules. If `dnf` cannot find
`kernel-modules-extra` for the running kernel, the kernel was updated but the
VM was not restarted: run `sudo reboot`, log in again, and repeat this step.

### 4.3 Docker

```bash
sudo dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo
sudo dnf -y install docker-ce docker-ce-cli containerd.io
sudo systemctl enable --now docker
sudo docker info --format '{{.ServerVersion}}'
```

The last command prints Docker's version. If Docker fails to start and
`sudo journalctl -u docker` mentions `xt_addrtype` or `br_netfilter`, step 4.2
is missing.

### 4.4 Open vSwitch

Rocky Linux does not ship Open vSwitch itself. The CentOS NFV SIG repository
does:

```bash
sudo dnf -y install centos-release-nfv-openvswitch
sudo dnf -y install openvswitch3.5
sudo systemctl enable --now openvswitch
sudo ovs-vsctl show
```

`ovs-vsctl show` prints an id and `ovs_version: "3.5..."`. If `openvswitch3.5`
is not found, `dnf list 'openvswitch3.*'` shows the versions available; use
the newest.

### 4.5 Containerlab

```bash
bash -c "$(curl -sL https://get.containerlab.dev)" -- -v 0.81.0
containerlab version
```

### 4.6 SELinux: OpenFlow ports

SELinux only lets Open vSwitch connect to TCP ports labelled
`openflow_port_t`, which by default are 6633 and 6653. This adds the ports up
to 6660, so you can also run a controller on another port:

```bash
sudo dnf -y install policycoreutils-python-utils
sudo semanage port -a -t openflow_port_t -p tcp 6633-6660
sudo semanage port -l | grep openflow
```

The last line should include `6633-6660`.

### 4.7 Container images

The lab hosts and the Lab 2 controller run from two container images, built
from the `images/` folder:

```bash
sudo docker build -t csci60/host images/host   # lab hosts (Alpine Linux + tools)
sudo docker build -t csci60/controller images/controller   # os-ken 4.2.2 (Lab 2)
sudo docker images 'csci60/*'
```

The last command lists both images.

os-ken is an OpenFlow controller framework maintained by OpenStack. It runs
in a container so its version is pinned and nothing is installed into the
VM's own Python.

## 5. Your first network

```bash
cd getting-started
```

A topology file describes the network. `first.clab.yml` in this folder has
two hosts and one switch:

```bash
cat first.clab.yml
```

```yaml
name: first
prefix: ""            # name the containers just h1, h2

topology:
  defaults:
    kind: linux       # a host is a Linux container ...
    image: csci60/host  # ... started from this image (Alpine Linux + tools)
    network-mode: none  # with no network except the links below
  nodes:
    h1:
      exec:
        - ip addr add 10.0.0.1/24 dev eth0
    h2:
      exec:
        - ip addr add 10.0.0.2/24 dev eth0
    s1:
      kind: ovs-bridge  # an Open vSwitch switch
  links:
    - {endpoints: ["h1:eth0", "s1:s1-eth1"], mtu: 1500}
    - {endpoints: ["h2:eth0", "s1:s1-eth2"], mtu: 1500}
```

Each link is a virtual cable: `h1:eth0` is interface `eth0` on h1, and
`s1:s1-eth1` is port `s1-eth1` on switch s1.

1. Create the switch. Containerlab connects hosts to a switch, but does not
   create it. Open vSwitch calls a switch a *bridge*:

   ```bash
   sudo ovs-vsctl add-br s1
   ```

2. Build the network:

   ```bash
   sudo containerlab deploy -t first.clab.yml
   ```

   It ends with a table of the hosts it started.

3. Look at what you built:

   ```bash
   sudo containerlab inspect -t first.clab.yml   # the hosts
   sudo ovs-vsctl show                           # the switch and its ports
   ```

## 6. Running commands on a host

`docker exec <host> <command>` runs a command on a host:

```bash
sudo docker exec h1 ifconfig -a        # h1's interfaces: eth0 and lo
sudo docker exec h1 ping -c3 10.0.0.2  # h1 pings h2
sudo docker exec h1 route -n           # h1's routing table
sudo docker exec h1 hostname           # prints h1
```

The ping should show `0% packet loss`. If it does, your VM is ready for the
labs.

To work on a host for longer, open a shell on it. The prompt changes to the
host's name, and every command runs on that host until you type `exit`:

```bash
sudo docker exec -it h1 bash
```

```text
h1# ifconfig eth0
h1# ping -c3 10.0.0.2
h1# exit
```

Useful commands on a host:

| Command                                   | What it does                         |
| ----------------------------------------- | ------------------------------------ |
| `ifconfig -a`                             | list interfaces and addresses        |
| `ifconfig eth0 10.0.0.5 netmask 255.255.255.0` | set an address                  |
| `route -n`                                | show the routing table               |
| `route add default gw 10.0.0.254`         | add a default route                  |
| `ping -c3 <ip>`                           | test reachability                    |
| `traceroute -n <ip>`                      | show the path to an address          |
| `tcpdump -n -i eth0`                      | watch packets on an interface (Ctrl-C stops) |
| `iperf -s` / `iperf -c <ip>`              | measure bandwidth (server / client)  |

## 7. Looking at the switch

```bash
sudo ovs-vsctl show                 # bridges and their ports
sudo ovs-vsctl list-ports s1        # just the ports of s1
sudo ovs-ofctl show s1              # OpenFlow port numbers
sudo ovs-ofctl dump-flows s1        # the switch's flow table
```

With no controller set, an Open vSwitch bridge is a normal learning switch:
the flow table has one rule, `actions=NORMAL`. In Lab 2 a controller fills
the flow table instead.

## 8. Cleaning up

Always remove the network when you are done:

```bash
sudo containerlab destroy -t first.clab.yml
sudo ovs-vsctl del-br s1
```

Check that nothing is left. Both commands should print nothing:

```bash
sudo docker ps -q
sudo ovs-vsctl list-br
```

## 9. Changing a network

Edit the topology file, then deploy again with `--reconfigure`. This removes
the old hosts and builds new ones, so any addresses you set by hand are gone.

Try it, starting after the clean-up in section 8: add a third host `h3` with
address `10.0.0.3/24`, connected to `s1:s1-eth3`. Then create the switch
again and deploy.

```bash
nano first.clab.yml
sudo ovs-vsctl add-br s1
sudo containerlab deploy -t first.clab.yml --reconfigure
sudo docker exec h3 ping -c3 10.0.0.1
```

## 10. Link speed and delay

Real links have limited speed and some delay. The `tc` command sets them on an
interface:

```bash
sudo docker exec h1 tc qdisc add dev eth0 root netem delay 50ms rate 10mbit
sudo docker exec h1 ping -c3 10.0.0.2      # about 50 ms more than before
```

To set them when the network is built, add the `tc` command to the host's
`exec` list in the topology file. To remove them:

```bash
sudo docker exec h1 tc qdisc del dev eth0 root
```

Measure bandwidth with `iperf`. Run the server on h2 in the background
(`-d`), then the client on h1:

```bash
sudo docker exec -d h2 iperf -s
sudo docker exec h1 iperf -c 10.0.0.2 -t 5
```

## 11. Exercises

1. Build two switches connected through a host, with two hosts on each switch.
   Can the hosts on different switches ping each other? Why?
2. Build `first.clab.yml` again, then compare `ping` between h1 and h2 with no
   delay, with 10 ms delay on h1, and with 10 ms delay on both h1 and h2.
3. Use `tcpdump` on h2 while h1 pings it. Which packets do you see?

Remember to clean up (section 8) after each one.

## Updating the course files

```bash
cd ~/csci60-labs && git pull
```

Rebuild the images (step 4.7) only if `images/` changed.

## FAQ

1. **`deploy` says it cannot find the bridge.**
   Create the switch first: `sudo ovs-vsctl add-br s1`.

2. **`deploy` says the lab already exists, or `add-br` says the switch
   already exists.**
   Something is left over from an earlier try. Clean up (section 8) and
   start again.

3. **`ping: connect: Network unreachable`.**
   The host has no route to that address. Check its address and mask
   (`ifconfig`) and its routes (`route -n`).

4. **I restarted the VM and my network is broken.**
   Containers and switches do not survive a restart cleanly. Clean up
   (section 8), then build the network again.

5. **What is `prefix: ""` in the topology file?**
   Without it, Containerlab names the containers `clab-first-h1` and so on.
   With it, they are just `h1`, `h2`, which is shorter to type.

6. **Docker or `dnf` fails with a network error.**
   The VM has no internet access. Check the VM's network adapter is set to
   NAT, and that `ping -c3 rockylinux.org` works in the VM.
