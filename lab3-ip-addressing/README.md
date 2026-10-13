# CSCI 60 Lab Exercise 3: TCP/IP PC Networking Configuration

*Original by William Emmanuel Yu, Ph.D. (September 2021).
Updated for Containerlab by Miguel Zenon Nicanor L. Saavedra, Ph.D.*

## Objectives

- Familiarize students with basic TCP/IP PC networking configuration.
- Familiarize students with TCP/IP addressing in an emulated network.

## Materials

- PCs with a working MS Windows / Linux installation (Physical Host part).
- Your CSCI 60 VM, set up as in *Getting Started*.
- Familiarity with the Linux command line
  (<http://www.tldp.org/LDP/abs/html/basic.html>).
- *Getting Started* (`getting-started/README.md` in this repository).
- `lab3.clab.yml` in this folder: four hosts (`h1` to `h4`) on one switch
  (`s1`), with no IP addresses yet.

## Procedure for Physical Host IP Configuration

Before you start, write down these settings of your computer. These are
classroom computers and must be returned to their previous configuration.

- IP Address
- Subnet Mask
- Default Gateway

**First Set**

1. Each group is given a network address and prefix length, by this formula:
   `10.<row>.<column>.0/24` (e.g. `10.1.2.0/24`). Each group has a unique
   network address. To change the IP address:
   - **Windows**: Settings → Network & Internet → (Ethernet) → Edit IP
     assignment → Manual → IPv4. Or: Control Panel → Network and Sharing
     Center → Change adapter settings → right-click the adapter →
     Properties → Internet Protocol Version 4 (TCP/IPv4) → Properties →
     *Use the following IP address*.
   - **Linux**: `nmcli` or the network settings dialog.
2. From this network address, compute and configure the appropriate subnet
   mask and choose the IP addresses for two (2) computers.

**Second Set**

1. Configure your computers back to the original settings from the start of
   the class.

## Procedure for the Emulated Network

1. Log in to your VM and go to this lab's folder.

   ```bash
   cd ~/csci60-labs/lab3-ip-addressing
   ```

2. Create the switch. Open vSwitch calls a switch a *bridge*. With no
   controller set, it works as a normal learning switch.

   ```bash
   sudo ovs-vsctl add-br s1
   ```

3. Create the four hosts and connect them to `s1`. Read `lab3.clab.yml`
   first to see what will be built.

   ```bash
   cat lab3.clab.yml
   sudo containerlab deploy -t lab3.clab.yml
   ```

4. Look at a host's interfaces. Each host is a container, and
   `docker exec <host> <command>` runs a command on it. `eth0` is the link
   to the switch. It has no IPv4 address (no `inet` line) yet.

   ```bash
   sudo docker exec h1 ifconfig -a
   ```

5. Configure an IP address. The syntax is the Linux `ifconfig` command:

   ```text
   sudo docker exec <host> ifconfig <interface> <ip address> netmask <subnet mask>
   ```

   For example:

   ```bash
   sudo docker exec h1 ifconfig eth0 192.168.0.1 netmask 255.255.255.0
   ```

   This configures IP address **192.168.0.1** with network mask
   **255.255.255.0** on interface **eth0** of host **h1**.

6. Configure the rest of the hosts. Hosts **h1** and **h2** must be in the
   network **192.168.0.0/255.255.255.128**, and hosts **h3** and **h4** must
   be in the network **192.168.0.128/255.255.255.128**. These are network
   addresses. (Set h1 again too: the example in step 5 used a different mask.)

7. Check each host's address. Look for the `inet` line:

   ```bash
   sudo docker exec h1 ifconfig eth0
   ```

8. Test connectivity between hosts using `ping`. Try every pair, one command
   at a time, and write down which ones work:

   ```bash
   sudo docker exec h1 ping -c3 192.168.0.2
   sudo docker exec h1 ping -c3 192.168.0.129
   ...
   ```

   Some pings answer and some print `connect: Network unreachable`. Both are
   results: explain them in the questions below.

9. Look at a host's routing table. It shows which networks the host can
   reach directly:

   ```bash
   sudo docker exec h1 route -n
   ```

10. When you are done, remove the hosts and the switch:

    ```bash
    sudo containerlab destroy -t lab3.clab.yml
    sudo ovs-vsctl del-br s1
    ```

## Questions

**Physical Host First Set**

- What are the IP addresses and subnet masks used?
- Can you ping one of the group's computers from the other computer? Why?
- Can you ping your other classmates' computers? Why?

**Physical Host Second Set**

- What are the IP addresses and subnet masks used?
- Can you ping one of the group's computers from the other computer? Why?
- Can you ping your other classmates' computers (choose one that has reverted
  to the original classroom setting)? Why?

**Emulated Network**

- Which hosts can connect to (ping) each other? Why?

## Frequently Asked Questions

1. **`ping: connect: Network unreachable`.**
   This is an answer, not a problem with your VM: the host has no route to
   that address. Think about which network each address is in.

2. **`deploy` says the lab already exists, `add-br` says a switch already
   exists, or pings fail for no clear reason.**
   Something from an earlier try or another lab is still running: a lab you
   did not destroy, or a switch you did not delete. Containerlab never
   deletes switches, so a leftover switch keeps its old settings and ports,
   even after a restart of the VM. Remove everything:

   ```bash
   sudo containerlab destroy --all -y
   sudo ovs-vsctl list-br
   ```

   Delete every switch `list-br` printed, one by one:

   ```bash
   sudo ovs-vsctl del-br s1
   ```

   Check that both of these print nothing, then start again from step 2:

   ```bash
   sudo docker ps -q
   sudo ovs-vsctl list-br
   ```

3. **`deploy` says it cannot find the bridge `s1`.**
   Containerlab connects hosts to a switch that must already exist. Run
   step 2 first.

4. **How do I get a shell on a host?**
   `sudo docker exec -it h1 bash`. Then type commands without the
   `sudo docker exec h1` part (`ifconfig -a`, `ping ...`). Type `exit` to
   leave it.
