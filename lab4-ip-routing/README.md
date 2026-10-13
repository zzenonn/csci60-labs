# CSCI 60 Lab Exercise 4: TCP/IP Routing

*Original by William Emmanuel Yu, Ph.D. (September 2021). Updated for
Containerlab and Open vSwitch on your CSCI 60 VM.*

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
- Your CSCI 60 VM, set up as in *Getting Started*.
- Familiarity with the Linux command line
  (<http://www.tldp.org/LDP/abs/html/basic.html>).
- *Getting Started* (`getting-started/README.md` in this repository).
- `lab4.clab.yml` in this folder: the emulated network.

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

## Emulated Network Procedure

1. Log in to your VM and go to this lab's folder.

   ```bash
   cd ~/csci60-labs/lab4-ip-routing
   ```

2. Create the four switches. With no controller set, each works as a normal
   learning switch.

   ```bash
   sudo ovs-vsctl add-br s0
   sudo ovs-vsctl add-br s1
   sudo ovs-vsctl add-br s2
   sudo ovs-vsctl add-br s3
   ```

3. Look at `lab4.clab.yml`. It has 6 hosts: h0 and h1 are connected to s0,
   h2 and h3 to s1, h4 and h5 to s2, and s3 is connected to nothing.

   ```bash
   cat lab4.clab.yml
   ```

4. Create the hosts:

   ```bash
   sudo containerlab deploy -t lab4.clab.yml
   ```

5. Give each host an address in one network, `10.0.0.0/8`, and test:

   ```bash
   sudo docker exec h0 ifconfig eth0 10.0.0.1 netmask 255.0.0.0
   sudo docker exec h1 ifconfig eth0 10.0.0.2 netmask 255.0.0.0
   sudo docker exec h2 ifconfig eth0 10.0.0.3 netmask 255.0.0.0
   sudo docker exec h0 ping -c1 10.0.0.2
   sudo docker exec h0 ping -c1 10.0.0.3
   ```

   h0 can reach h1 (same switch) but not h2 (different switch, and the
   switches are not connected).

6. Notice switch s3 is alone. **Edit `lab4.clab.yml`** so that hosts h0, h2
   and h4 are also connected to s3: add three links at the end, one per
   host, using each host's second interface (`eth1`) and a new port on s3:

   ```yaml
       - {endpoints: ["h0:eth1", "s3:s3-eth1"], mtu: 1500}
   ```

   Then rebuild the hosts with the new links. `--reconfigure` removes the old
   hosts first, so all addresses are gone after this.

   ```bash
   nano lab4.clab.yml
   sudo containerlab deploy -t lab4.clab.yml --reconfigure
   ```

   Check that h0 now has two interfaces, `eth0` and `eth1`, with no IPv4
   address (no `inet` line):

   ```bash
   sudo docker exec h0 ifconfig -a
   sudo ovs-vsctl list-ports s3
   ```

7. Now configure the IP addresses so that:
   - h0 and h1 are in network **192.168.0.0/255.255.255.128**,
   - h2 and h3 are in network **192.168.0.128/255.255.255.128**,
   - h4 and h5 are in network **192.168.1.0/255.255.255.128**,
   - h0, h2 and h4 are in network **192.168.1.128/255.255.255.128**
     (on their second interface, `eth1`).

   These are network addresses. See Lab 3 for how to set IP addresses with
   `ifconfig`, for example:

   ```bash
   sudo docker exec h0 ifconfig eth1 192.168.1.129 netmask 255.255.255.128
   ```

8. The hosts still cannot all reach each other. You need to turn the
   designated routers into routers, and add the right routes.

   **Enable IP forwarding** on each host you use as a router. Every host is
   its own machine with its own network settings, so you do this on each
   router host:

   ```bash
   sudo docker exec h0 sysctl -w net.ipv4.ip_forward=1
   ```

9. **Add routes**, with the Linux `route` command:

   ```text
   sudo docker exec <host> route add -net <destination network> netmask <destination mask> gw <next hop router>
   sudo docker exec <host> route add default gw <next hop router>
   ```

   For example:

   ```bash
   sudo docker exec h0 route add -net 192.168.0.128 netmask 255.255.255.128 gw 192.168.1.131
   sudo docker exec h2 route add -net 192.168.0.0 netmask 255.255.255.128 gw 192.168.1.130
   ```

   Routes must be reciprocal: there must be a route to and from each source
   and destination. Do not forget the default routes on the hosts that are
   not routers.

   (Careful: the example above shows the command format. Work out yourself
   whether its next hops are right.)

10. Test every host against every other host with `ping`, one command at a
    time. You are done when all 30 pairs answer. `traceroute` shows the path
    a packet takes:

    ```bash
    sudo docker exec h1 ping -c1 192.168.1.2
    sudo docker exec h1 traceroute -n 192.168.1.2
    ```

11. Look at the result:

    ```bash
    sudo docker exec h0 route -n        # the routes on a router
    sudo docker exec h1 route -n        # the default route on a host
    ```

    Keep a copy of your edited `lab4.clab.yml` and of every command you typed
    in steps 7 to 9. You need them for question 9.

12. When you are done, remove the hosts and the switches:

    ```bash
    sudo containerlab destroy -t lab4.clab.yml
    sudo ovs-vsctl del-br s0
    sudo ovs-vsctl del-br s1
    sudo ovs-vsctl del-br s2
    sudo ovs-vsctl del-br s3
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
7. For the emulated network, after step 6, is it now possible for all hosts to
   ping each other?
8. For the emulated network, which hosts do you think are ideal as the
   designated routers? (Hint: there are 3 of them.) Which hosts are the
   designated hosts? (Hint: the remaining 3.)
9. For the emulated network, to allow all machines to ping each other, which
   routes were added in step 9? List the routes for both the designated
   routers and the designated hosts.

## Frequently Asked Questions

1. **`deploy` says the lab already exists, `add-br` says a switch already
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

2. **`deploy` says it cannot find a bridge.**
   Containerlab connects hosts to switches that must already exist. Run
   step 2 first.

3. **`deploy` fails after I edited `lab4.clab.yml`.**
   The error message points at the line. Every link joins `host:interface`
   to `switch:port`, each port can be used only once, and the lines must be
   indented exactly like the others.

4. **How do I list the routes of a host?**
   `sudo docker exec h1 route -n`

5. **How do I list all interfaces of a host?**
   `sudo docker exec h1 ifconfig -a`

6. **How do I delete a route?**
   `sudo docker exec <host> route del -net <network> netmask <mask> gw <next hop>`
   or `sudo docker exec <host> route del default gw <next hop>`

7. **How do I get a shell on a host?**
   `sudo docker exec -it h1 bash`. Then type commands without the
   `sudo docker exec h1` part. Type `exit` to leave it.

## The network after step 6

```text
              s3
           /   |   \
         h0   h2   h4          <- designated routers (2 interfaces each)
          |    |    |
         s0   s1   s2
          |    |    |
         h1   h3   h5
```

The switches are normal learning switches; no SDN controller is used. All
routing is done by the hosts you turn into routers.
