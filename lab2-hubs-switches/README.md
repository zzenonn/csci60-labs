# CSCI 60 Lab Exercise 2: Connectivity Devices (Hubs and Switches) with OpenFlow

*Original by William Emmanuel Yu, Ph.D. (September 2022). Updated for the
csci60 lab server (Containerlab + Open vSwitch + Ryu).*

## Objectives

- Understand the differences among network devices, in particular hubs and
  switches. This is an essential concept in physical network design.
- Gain insight on best practices in designing these devices.
- Gain hands-on experience with a network emulator and an introduction to
  software defined networks.

## Materials

- An account on the CSCI 60 lab server (ask your instructor), and an SSH
  client: `ssh` on Linux/macOS/Windows PowerShell, or PuTTY.
- Familiarity with the Linux command line
  (<http://www.tldp.org/LDP/abs/html/basic.html>).
- *Getting Started with csci60* (`setup/docs/getting-started.md` in this repository).
- The **Switch / Hub Teaching Demo**, a simple OpenFlow app with several
  switch implementations. It is installed on the server as the Ryu app
  `sw_tutorial`:
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

## How to use the Switch / Hub Teaching Demo

| Command (from any shell; in the `csci60>` console leave out `csci60`) | What it does |
| ------------------------------------------------------------------------ | ------------ |
| `csci60 ryu modes`                | list the available switch types and show the active one |
| `csci60 ryu clear`                | clear all flows from the attached switches              |
| `csci60 ryu detach`               | stop handling packets (no switch type attached)         |
| `csci60 ryu mode SW_LAZYHUB`      | clear all flows, then attach the given switch type      |

(These replace the POX console's `MySwitch.list_available_listeners()`,
`MySwitch.clear_all_flows()`, `MySwitch.detach_packetin_listener()` and
`MySwitch.attach_packetin_listener('SW_LAZYHUB')`.)

## Procedure

1. Log in to the lab server.

   ```bash
   ssh <username>@<lab-server>
   ```

2. Check that the server is ready. It should end with `All good.`

   ```bash
   csci60 doctor
   ```

3. Start the Switch / Hub Teaching Demo controller. This is the
   **CONTROLLER console**. Leave it running.

   ```bash
   csci60 ryu start sw_tutorial
   ```

4. Log in again in a second SSH session. Set the controller to the
   *Dumb Hub* logic (this also clears any old flows):

   ```bash
   csci60 ryu mode SW_DUMBHUB
   ```

5. In the same second session, start the network. This is the
   **NETWORK console**.

   ```bash
   csci60 start --topo single,3 --link tc,bw=10,delay=10ms --mac --switch ovsk --controller remote
   ```

6. Watch the **CONTROLLER console**. Wait until the traffic stops (a few
   seconds; this is the switch connecting to the controller). Then, in the
   **NETWORK console**, type:

   ```text
   csci60> pingall
   ```

7. Look at the **CONTROLLER console**. You should see broadcast and OpenFlow
   rule installation output, like:

   ```text
   Broadcasting 00:00:00:00:00:01.1 -> ff:ff:ff:ff:ff:ff.65532
   Installing 00:00:00:00:00:01.1 -> 00:00:00:00:00:02.2
   ```

   Call this **OUTPUT A**. Press ENTER a few times in the CONTROLLER console
   to separate the outputs. Wait 5 to 15 seconds, then run `pingall` again in
   the NETWORK console. Call the new controller output **OUTPUT B**.

   Port `65532` means "all ports" and `ff:ff:ff:ff:ff:ff` means "any
   address".

   Tip: `dpctl dump-flows` in the NETWORK console shows the flows the
   controller installed in the switch.

8. Change the switch type, in the NETWORK console (or a third session with
   `csci60 ryu mode ...`):

   ```text
   csci60> ryu mode SW_PAIRHUB
   csci60> pingall
   ```

   Compare OUTPUT A and OUTPUT B for every switch and hub type:
   `SW_DUMBHUB`, `SW_PAIRHUB`, `SW_LAZYHUB`, `SW_BADSWITCH`,
   `SW_PAIRSWITCH`, `SW_IDEALPAIRSWITCH`. Summarize your observations in your
   submission.

9. To exit the **NETWORK console**:

   ```text
   csci60> exit
   ```

10. To exit the **CONTROLLER console**: press `Ctrl-C`.

11. Check that nothing is left running. Both lines should say `none running`:

    ```bash
    csci60 status
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

1. **How do I transfer files to and from the lab server?**
   `scp` (Linux, macOS, Windows PowerShell) or WinSCP on Windows.

2. **Strange errors appear in the controller (stack traces).**
   Exit both the network and the controller, then try again. You need to redo
   the experiment for that switch type.

3. **"network 'csci60' is still running" or "a controller is already running
   on port 6633".**
   A network or controller from an earlier try is still there.
   `csci60 status` shows what is running; `csci60 reset` removes everything
   (this replaces `sudo mn -c` and `sudo killall controller`).

4. **`pingall` does not work, or "command not found".**
   `pingall` only works in the NETWORK console (`csci60>` prompt). Start it
   with the `csci60 start ...` command in step 5. If you are in the console
   and every ping fails, check that the controller is running (step 3) and a
   mode that forwards traffic is set.

5. **The controller output scrolls too fast.**
   Run the controller in the background instead
   (`csci60 ryu start sw_tutorial -d`) and read the output with
   `csci60 ryu logs` after each `pingall`. It keeps following new output;
   press `Ctrl-C` to get your prompt back.

## How this lab fits together

```text
 SSH session 1                         SSH session 2
 csci60 ryu start sw_tutorial          csci60 start --topo single,3 ... --controller remote
        |                                       |
        v                                       v
 Ryu controller  <--- OpenFlow 1.0 --->  Open vSwitch "s1"
 (sw_tutorial app,  tcp 127.0.0.1:6633        |   |   |
  REST port 8080 for `ryu mode`)             h1  h2  h3   (containers)
```

- The `csci60` command comes from `setup/` in this repository (installed on
  the server by the instructor).
- The `sw_tutorial` app is `ryu-apps/apps/sw_tutorial.py` in this repository.
  It is the Ryu port of the POX `of_sw_tutorial_oo.py` used by the earlier
  version of this lab.
