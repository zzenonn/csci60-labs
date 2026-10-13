# CSCI 60 Lab Exercise 4: TCP/IP Routing

*Original by William Emmanuel Yu, Ph.D. (September 2021). Updated for the
csci60 lab server (Containerlab + Open vSwitch).*

## Objectives

- Familiarize students with PC network configuration.
- Familiarize students with IP addressing.
- Familiarize students with basic IP subnetting.
- Familiarize students with basic IP routing.
- Learn to configure a PC as a basic router.
- Perform these activities on both a real and an emulated network.

## Materials

- PCs with a working MS Windows / Linux installation (Live Network part).
  On Windows you need administrator rights to change network settings and
  routes. To enable IP routing on Windows see
  <https://www.wikihow.com/Enable-IP-Routing>.
- An account on the CSCI 60 lab server (ask your instructor), and an SSH
  client: `ssh` on Linux/macOS/Windows PowerShell, or PuTTY.
- Familiarity with the Linux command line
  (<http://www.tldp.org/LDP/abs/html/basic.html>).
- *Getting Started with csci60* (`setup/docs/getting-started.md` in this repository).

## Live Network Procedure

1. Make sure you have a working network connection by pinging the
   instructor's PC (LECTURER_PC). The instructor will write its IP on the board.
2. Each table is assigned a separate subnet:
   - CLASSROOM subnet: the default classroom configuration
   - Table 1L: 10.255.1.0/24
   - Table 1R: 10.255.2.0/24
   - Table 2L: 10.255.3.0/24
   - Table 2R: 10.255.4.0/24
   - Table 3L: 10.255.5.0/24
   - Table 3R: 10.255.6.0/24
   - Table 4L: 10.255.7.0/24
   - Table 4R: 10.255.8.0/24
   - Table 5L: 10.255.9.0/24
   - Table 5R: 10.255.10.0/24
3. Write down the old IP settings before making changes to the workstations!
   Set them back after the lab.
4. Study the figure from the lecture: each group has a separate subnet.
   Although physically connected to each other, the groups are in logically
   different networks.
5. Configure both workstations with IP addresses in the assigned subnet. One
   should be 10.255.X.1 and the other 10.255.X.2. Leave the gateway and DNS
   settings blank.
6. Configure the first workstation to also be part of the CLASSROOM subnet
   (workstation 1 is now part of two networks).
7. Give the instructor your subnet and both IP addresses of workstation 1 (so
   the instructor can add the route on the LECTURER_PC). Do not continue until
   this is done.
8. Set the second workstation's (10.255.X.2) default route to the first
   workstation (10.255.X.1).
9. Configure the first workstation to route packets to the CLASSROOM subnet.
   Enabling routing may need registry settings on Windows. Test by pinging the
   LECTURER_PC.
10. Make sure workstation 1 and workstation 2 can both ping the LECTURER_PC.
11. Configure the first workstation to route packets to at least one other
    subnet in the classroom (another table): add a static route on your
    workstation 1 to the other subnet, and on the other group's workstation 1
    to your subnet.
12. Return the workstations to their original configuration.

## csci60 Network Procedure

1. Log in to the lab server and get this lab's files:

   ```bash
   ssh <username>@<lab-server>
   cd csci60-labs/lab4-ip-routing
   csci60 doctor            # should end with "All good."
   ```

   (If you have not cloned the course repository yet, see the top-level
   README.)

2. Look at `lab4.py`. It builds 6 hosts and 4 switches: h0 and h1 are
   connected to s0, h2 and h3 to s1, h4 and h5 to s2, and s3 is connected to
   nothing.

   ```python
   from mininet.net import Mininet
   from mininet.cli import CLI

   net = Mininet()
   c0 = net.addController('c0')
   s0 = net.addSwitch('s0')
   s1 = net.addSwitch('s1')
   s2 = net.addSwitch('s2')
   s3 = net.addSwitch('s3')
   h0 = net.addHost('h0')
   h1 = net.addHost('h1')
   h2 = net.addHost('h2')
   h3 = net.addHost('h3')
   h4 = net.addHost('h4')
   h5 = net.addHost('h5')
   net.addLink(s0, h0)
   net.addLink(s0, h1)
   net.addLink(s1, h2)
   net.addLink(s1, h3)
   net.addLink(s2, h4)
   net.addLink(s2, h5)

   net.start()
   CLI(net)
   net.stop()
   ```

3. Run it:

   ```bash
   csci60 run lab4.py
   ```

   This runs the Python script and drops you into the `csci60>` console,
   where you can type the usual commands. Test connectivity with `pingall`.
   Notice that only hosts connected to the same switch can ping each other.
   Type `exit` to leave.

4. Notice switch s3 is alone. **Edit `lab4.py`** so that hosts h0, h2 and h4
   are also connected to s3. Run it again. h0, h2 and h4 are now connected to
   each other but still cannot ping each other. `h0 ifconfig -a` shows that the
   new interface (`h0-eth1`) has no IP address yet.

5. Let us fix that. From the console of the new `lab4.py`, change the IP
   addresses of the hosts so that:
   - h0 and h1 are in network **192.168.0.0/255.255.255.128**,
   - h2 and h3 are in network **192.168.0.128/255.255.255.128**,
   - h4 and h5 are in network **192.168.1.0/255.255.255.128**,
   - h0, h2 and h4 are in network **192.168.1.128/255.255.255.128**
     (on their second interface).

   These are network addresses. See Lab 3 for how to set IP addresses with
   `ifconfig`.

6. The hosts still cannot all reach each other. You need to turn the
   designated routers into routers, and add the right routes.

   **Enable IP forwarding** on each host you use as a router. Every host has
   its own network stack, so this is done per host, in the console:

   ```text
   csci60> h0 sysctl -w net.ipv4.ip_forward=1
   ```

   (The old Mininet VM asked for `sudo sysctl -w net.ipv4.ip_forward=1` on the
   VM itself. Here each host is its own machine, so you enable it on the
   router hosts instead.)

7. **Add routes.** In the console (as in Linux):

   ```text
   <host> route add -net <destination network> netmask <destination mask> gw <next hop router>
   <host> route add default gw <next hop router>
   ```

   For example:

   ```text
   csci60> h0 route add -net 192.168.0.128 netmask 255.255.255.128 gw 192.168.1.131
   csci60> h2 route add -net 192.168.0.0 netmask 255.255.255.128 gw 192.168.1.130
   ```

   Routes must be reciprocal: there must be a route to and from each source and
   destination. Do not forget the default routes on the hosts that are not
   routers.

   (Careful: the example above shows the command format. Work out yourself
   whether its next hops are right.)

   When `pingall` shows `0% dropped`, you are done. `h1 traceroute -n <ip>`
   shows the path a packet takes.

8. Look at the result, one command at a time:

   ```text
   csci60> net                        # s3 is now linked to h0, h2 and h4
   csci60> h0 route -n                # the routes on a router
   csci60> h1 route -n                # the default route on a host
   csci60> h1 traceroute -n 192.168.1.2
   csci60> pingall                    # should end with 0% dropped (30/30 received)
   ```

   Keep a copy of your edited `lab4.py` and of every command you typed in
   steps 5 to 7. The console does not save them, and you need them for
   question 9.

9. Exit the console (`exit`). Then check that nothing is left running:

   ```bash
   csci60 status
   ```

## Questions

1. For the classroom exercise, what is the network address, subnet mask,
   prefix length, broadcast address, subnet size, first usable IP address and
   last usable IP address of the CLASSROOM subnet?
2. For the classroom exercise, what is the network address, subnet mask,
   prefix length, broadcast address, subnet size, first usable IP address and
   last usable IP address of your assigned subnet?
3. For the classroom exercise, after configuring step 5, are the workstations
   within your subnet able to communicate with each other? Why?
4. For the classroom exercise, after configuring step 5, are both
   workstations within your subnet able to communicate with workstations
   outside your subnet even if they are connected to the same network device?
   Why?
5. For the classroom exercise, after configuring step 7, are both
   workstations able to communicate with each other? With the lecturer PC?
   With another subnet? Why?
6. For the classroom exercise, after configuring step 9, are both
   workstations able to communicate with each other? With the lecturer PC?
   With another subnet? Why?
7. For the csci60 exercise, after step 4, is it now possible for all hosts to
   ping each other?
8. For the csci60 exercise, which hosts do you think are ideal as the
   designated routers? (Hint: there are 3 of them.) Which hosts are the
   designated hosts? (Hint: the remaining 3.)
9. For the csci60 exercise, to allow all machines to ping each other, which
   routes were added in step 7? List the routes for both the designated
   routers and the designated hosts.

## Frequently Asked Questions

1. **"network 'csci60' is still running" or "a controller is running on port
   6633".**
   An earlier network was not stopped (for example a closed SSH window).
   `csci60 stop` removes it; `csci60 reset` removes everything. (This
   replaces `sudo killall controller`.)
2. **`pingall` does not work but `<host> ping <host>` does.**
   `pingall` pings every host's first interface (`-eth0`). Check those
   addresses and the routes back to them.
3. **How do I list the routes of a host?** `<host> route -n`
4. **How do I list all interfaces of a host?** `<host> ifconfig -a`
5. **How do I delete a route?**
   `<host> route del -net <network> netmask <mask> gw <next hop>` or
   `<host> route del default gw <next hop>`
6. **I edited `lab4.py` and now it fails to run.**
   The error message points at the line. Every `addLink` needs two nodes
   that were created with `addHost` / `addSwitch` before it.

## How this lab fits together

```text
              s3  (after step 4)
           /   |   \
         h0   h2   h4          <- designated routers (2 interfaces each)
          |    |    |
         s0   s1   s2
          |    |    |
         h1   h3   h5
```

- `csci60 run lab4.py` runs the Mininet-style script on the lab server. The
  `mininet` Python package there is a compatibility layer from `setup/` in
  this repository: it builds the network with Containerlab
  (hosts are containers, switches are Open vSwitch bridges).
- No SDN controller is needed: the switches are normal learning switches,
  so all routing is done by the hosts you turn into routers.

