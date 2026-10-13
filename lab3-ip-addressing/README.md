# CSCI 60 Lab Exercise 3: TCP/IP PC Networking Configuration

*Original by William Emmanuel Yu, Ph.D. (September 2021). Updated for the
csci60 lab server (Containerlab + Open vSwitch).*

## Objectives

- Familiarize students with basic TCP/IP PC networking configuration.
- Familiarize students with TCP/IP addressing in an emulated network.

## Materials

- PCs with a working MS Windows / Linux installation (Physical Host part).
- An account on the CSCI 60 lab server (ask your instructor), and an SSH
  client: `ssh` on Linux/macOS/Windows PowerShell, or PuTTY.
- Familiarity with the Linux command line
  (<http://www.tldp.org/LDP/abs/html/basic.html>).
- *Getting Started with csci60* (`setup/docs/getting-started.md` in this repository).

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

## Procedure for the csci60 Set

1. Log in to the lab server.

   ```bash
   ssh <username>@<lab-server>
   ```

2. Check that the server is ready. It should end with `All good.`

   ```bash
   csci60 doctor
   ```

3. Launch an interactive network with 4 hosts connected to one switch.
   (If you forgot how to do this, review *Getting Started with csci60*.)

4. Configure IP addresses on your virtual hosts. The syntax is:

   ```text
   <host> ifconfig <host>-<interface> <ip address> netmask <subnet mask>
   ```

   For example:

   ```text
   csci60> h1 ifconfig h1-eth0 192.168.0.1 netmask 255.255.255.0
   ```

   This configures IP address **192.168.0.1** with network mask
   **255.255.255.0** on host **h1**. The syntax is the same as the Linux
   `ifconfig` command, except that the host name comes first to say which host
   runs it.

5. Configure the rest of the hosts. Hosts **h1** and **h2** must be in the
   network **192.168.0.0/255.255.255.128**, and hosts **h3** and **h4** must
   be in the network **192.168.0.128/255.255.255.128**. These are network
   addresses.

6. Check each host's address. Look for the `inet` line:

   ```text
   csci60> h1 ifconfig h1-eth0
   ```

7. Test connectivity between hosts using `ping` (not `pingall`). Try every
   pair, one command at a time, and write down which ones work:

   ```text
   csci60> h1 ping -c3 192.168.0.2
   csci60> h1 ping -c3 192.168.0.129
   ...
   ```

   Some pings answer and some print `connect: Network unreachable`. Both are
   results: explain them in the questions below.

8. Exit the console (`exit`). Then check that nothing is left running:

   ```bash
   csci60 status
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

**csci60 Set**

- Which hosts can connect to (ping) each other? Why?

## Frequently Asked Questions

1. **`ping: connect: Network unreachable`.**
   This is an answer, not an error with the server: the host has no route to
   that address. Think about which network each address is in.

2. **"network 'csci60' is still running".**
   `csci60 cli` reopens it; `csci60 stop` removes it.

3. **How do I see a host's addresses and routes?**
   `h1 ifconfig -a`, `h1 route -n` (or `h1 ip addr`, `h1 ip route`).

## How this lab fits together

```text
 csci60 start --topo single,4
        |
        v
 Open vSwitch "s1" (built-in controller: normal learning switch)
   |      |      |      |
  h1     h2     h3     h4      (containers, one Linux network stack each)
```

- The `csci60` command comes from `setup/` in this repository (installed on
  the server by the instructor).
- No SDN controller is needed: the switch learns MAC addresses by itself, so
  what you see depends only on the IP addresses you configure.
