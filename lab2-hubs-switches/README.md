# CSCI 60 Lab Exercise 2: Connectivity Devices (Hubs and Switches) with OpenFlow

*Original by William Emmanuel Yu, Ph.D. (September 2022). Updated for
Containerlab, Open vSwitch and Ryu on your CSCI 60 VM.*

## Objectives

- Understand the differences among network devices, in particular hubs and
  switches. This is an essential concept in physical network design.
- Gain insight on best practices in designing these devices.
- Gain hands-on experience with a network emulator and an introduction to
  software defined networks.

## Materials

- Your CSCI 60 VM, set up as in *Getting Started*.
- Familiarity with the Linux command line
  (<http://www.tldp.org/LDP/abs/html/basic.html>).
- *Getting Started* (`getting-started/README.md` in this repository).
- The files in this folder:
  - `lab2.clab.yml`: the network. Three hosts (`h1`, `h2`, `h3`) on one
    switch (`s1`). Each link is limited to 10 Mbit/s with 10 ms delay.
  - `sw_tutorial.py`: the **Switch / Hub Teaching Demo**, a Ryu controller app
    with several switch implementations:
    - *Dumb Hub*: all packets are sent to the controller and then broadcast to
      all ports. No flows are installed.
    - *Pair Hub*: flows are installed for source and destination MAC address
      pairs that instruct packets to be broadcast.
    - *Lazy Hub*: a single flow is installed to broadcast every packet to all
      ports.
    - *Bad Switch*: flows are installed only based on destination MAC
      addresses. Find out what the problem is!
    - *Pair Switch*: similar to a pair hub in that it installs flows based on
      source and destination MAC addresses, but it forwards packets to the
      appropriate port instead of broadcasting.
    - *Ideal Pair Switch*: improvement of the above switch where flows both to
      the source and to the destination MAC address are installed. Why is this
      an improvement over the above switch?

## The pieces

```text
 Terminal 1: CONTROLLER                 Terminal 2: NETWORK
 Ryu running sw_tutorial.py                docker exec h1 ping ...
        ^                                          |
        |  OpenFlow 1.0, tcp 127.0.0.1:6633        v
        +------------------------------  Open vSwitch bridge "s1"
                                              |    |    |
                                             h1   h2   h3   (containers)
```

- **Open vSwitch** provides the switch `s1`. It does not decide anything by
  itself: for every packet it does not have a flow for, it asks the
  controller.
- **Ryu** is the controller. It runs `sw_tutorial.py`, which decides what the
  switch does: act like a hub, or like a switch.
- **Containerlab** creates the hosts (small Linux containers) and the links
  between them and `s1`, from `lab2.clab.yml`.

## How to use the Switch / Hub Teaching Demo

Type these commands in the **CONTROLLER** session, where Ryu is running:

| Command           | What it does                                            |
| ----------------- | ------------------------------------------------------- |
| `modes`           | list the available switch types and show the active one |
| `mode SW_LAZYHUB` | clear all flows, then attach the given switch type      |
| `clear`           | clear all flows from the switch                         |
| `detach`          | stop handling packets (no switch type attached)         |

The controller starts with no switch type attached, so nothing is forwarded
until you choose one.

## Procedure

1. Log in to your VM and go to this lab's folder.

   ```bash
   cd ~/csci60-labs/lab2-hubs-switches
   ```

2. Create the switch. Open vSwitch calls a switch a *bridge*.

   ```bash
   sudo ovs-vsctl add-br s1
   ```

3. Make `s1` an OpenFlow switch that takes all its decisions from a
   controller: speak OpenFlow 1.0, forward nothing on its own
   (`fail_mode=secure`), and connect to the controller on this VM, port
   6633.

   ```bash
   sudo ovs-vsctl set bridge s1 protocols=OpenFlow10 fail_mode=secure
   sudo ovs-vsctl set-controller s1 tcp:127.0.0.1:6633
   ```

4. Create the hosts and connect them to `s1`. Read `lab2.clab.yml` first to
   see what will be built.

   ```bash
   cat lab2.clab.yml
   sudo containerlab deploy -t lab2.clab.yml
   ```

   Look at the switch: it should have ports `s1-eth1`, `s1-eth2` and
   `s1-eth3`, and show the controller as not yet connected.

   ```bash
   sudo ovs-vsctl show
   ```

5. Start the controller. This is the **CONTROLLER session**. Leave it
   running.

   ```bash
   sudo docker run --rm -it --name ryu --net host -v $PWD:/lab:ro,z csci60/ryu ryu-manager /lab/sw_tutorial.py
   ```

   (Ryu runs inside a container, `csci60/ryu`. `--net host` lets it listen on
   the VM's port 6633. `-v $PWD:/lab` makes this folder, with
   `sw_tutorial.py`, visible inside it.)

   You should see `Switch ... connected.` Then set the *Dumb Hub* logic by
   typing in this session:

   ```text
   mode SW_DUMBHUB
   ```

6. Open a second terminal on your VM (a second login, or `ssh` from your
   computer) and go to the lab folder. This is the **NETWORK session**.

   ```bash
   cd ~/csci60-labs/lab2-hubs-switches
   ```

7. Ping between every pair of hosts. Each host is a container, and
   `docker exec <host> <command>` runs a command on it. The hosts have the
   addresses `10.0.0.1` (h1), `10.0.0.2` (h2) and `10.0.0.3` (h3).

   ```bash
   sudo docker exec h1 ping -c1 10.0.0.2
   sudo docker exec h1 ping -c1 10.0.0.3
   sudo docker exec h2 ping -c1 10.0.0.3
   ```

8. Look at the **CONTROLLER session**. You should see broadcast and OpenFlow
   rule installation output, like:

   ```text
   Broadcasting 00:00:00:00:00:01.1 -> ff:ff:ff:ff:ff:ff.65532
   Installing 00:00:00:00:00:01.1 -> 00:00:00:00:00:02.2
   ```

   Call this **OUTPUT A**. Press ENTER a few times in the CONTROLLER session
   to separate the outputs. Wait 5 to 15 seconds, then run the same three
   pings again in the NETWORK session. Call the new controller output
   **OUTPUT B**.

   Port `65532` means "all ports" and `ff:ff:ff:ff:ff:ff` means "any
   address".

9. In the NETWORK session, look at the flows the controller installed in the
   switch:

   ```bash
   sudo ovs-ofctl dump-flows s1
   ```

10. Change the switch type in the CONTROLLER session:

    ```text
    mode SW_PAIRHUB
    ```

    Then repeat steps 7 to 9. Do this for every switch and hub type:
    `SW_DUMBHUB`, `SW_PAIRHUB`, `SW_LAZYHUB`, `SW_BADSWITCH`,
    `SW_PAIRSWITCH`, `SW_IDEALPAIRSWITCH`. Compare OUTPUT A and OUTPUT B for
    each, and summarize your observations in your submission.

11. When you are done, stop the controller: press `Ctrl-C` in the CONTROLLER
    session.

12. Remove the hosts and the switch (in either session):

    ```bash
    sudo containerlab destroy -t lab2.clab.yml
    sudo ovs-vsctl del-br s1
    ```

13. Check that nothing is left. Both commands should print nothing.

    ```bash
    sudo docker ps -q
    sudo ovs-vsctl list-br
    ```

## Questions

- With the various hub and switch types available, what are the differences
  between OUTPUT A and OUTPUT B of each switch or hub?
  - Study the differences between what you see and what you expected from the
    lectures.
  - TIP: you need to see how a good switch works before you know what is wrong
    with the bad switch.
- Which do you think is the most efficient and performs best?
- Which do you think is the least efficient and performs worst? In terms of
  controller effort? In terms of network traffic?
- Why is `SW_BADSWITCH` bad?
- What is the difference between `SW_IDEALPAIRSWITCH` and a regular
  `SW_PAIRSWITCH`?

## Frequently Asked Questions

1. **How do I transfer files to and from my VM?**
   `scp` (Linux, macOS, Windows PowerShell) or WinSCP on Windows, or the
   hypervisor's shared folders.

2. **Every ping fails.**
   Check that the controller is running (step 5) and that you chose a switch
   type with `mode ...`. With no switch type attached the switch forwards
   nothing: that is what `fail_mode=secure` means.

3. **Strange errors appear in the controller (stack traces).**
   Stop the controller (`Ctrl-C`), clean up (step 12), and start again from
   step 2. You need to redo the experiment for that switch type.

4. **`sudo docker run ...` says the name "ryu" is already in use.**
   A controller from an earlier try is still running. Stop it with
   `sudo docker rm -f ryu`.

5. **`containerlab deploy` says the lab already exists, or `ovs-vsctl add-br`
   says `s1` already exists.**
   Something is left over from an earlier try. Run step 12, then start again
   from step 2.

6. **`deploy` says it cannot find the bridge `s1`.**
   Containerlab connects hosts to a switch that must already exist. Run
   step 2 first.

7. **How do I get a shell on a host?**
   `sudo docker exec -it h1 bash`. Type `exit` to leave it.
