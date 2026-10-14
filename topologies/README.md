# Sample topologies

All the sample networks: `first.clab.yml` from Getting Started, and the
common shapes. Each file starts with a comment that
draws the topology, says what it is used for, and lists the commands to build
and remove it. Read that comment before you deploy.

| Shape  | File                 | Switches              | Hosts |
| ------ | -------------------- | --------------------- | ----- |
| First  | `first.clab.yml`     | s1                    | 2     |
| Single | `single.clab.yml`    | s1                    | 3     |
| Linear | `linear.clab.yml`    | s1 .. s4              | 4     |
| Tree   | `tree.clab.gotmpl`   | s1 .. s3              | 4     |
| Fanout | `fanout.clab.gotmpl` | s1                    | 100   |
| Clos   | `clos.clab.gotmpl`   | spine1-2, leaf1-4     | 8     |

Every host is called `hN` and has the address `10.0.0.N/24`, so h3 is
`10.0.0.3`. All hosts are in one subnet; there are no routers.

As in [Getting Started](../getting-started/README.md), create the switches
with `ovs-vsctl` first, then deploy. Containerlab never creates or deletes
switches.

```bash
cd ~/csci60-labs/topologies
```

## Plain files and templates

`first.clab.yml`, `single.clab.yml` and `linear.clab.yml` are plain topology files: every host
and every cable is written out. Read them first; they show how a topology file
describes a network.

The other three end in `.clab.gotmpl`. They are **templates**: instead of
listing every host, they use loops (`{{ range ... }}`) that Containerlab
expands before it builds the network. The numbers the loops use (how many
hosts, how deep the tree) are in the matching `.clab_vars.yaml` file. Change
the numbers there to get a bigger or smaller network from the same file.

To see what a template expands to, without building anything:

```bash
sudo containerlab graph -t tree.clab.gotmpl --mermaid --offline
cat clab-tree/graph/tree.clab.mermaid
```

The first command writes a text diagram of the network to a file; the second
prints it. Each `---` line is one cable, for example `s1---s2`. Before you deploy a template with new numbers,
use this to find out which switches you need to create.

To try other numbers without editing the vars file, put them in a file of your
own and pass it with `--vars` to `deploy` and `destroy`:

```bash
printf 'depth: 2\nfanout: 3\n' > ~/tree23.yaml
sudo containerlab deploy -t tree.clab.gotmpl --vars ~/tree23.yaml
```

## Cleaning up cables between switches

`containerlab destroy` removes the hosts, and with them every cable that has
one end in a host. A cable between two switches (in `linear`, `tree` and
`clos`) has no end in a host, so it stays behind on the VM, and the next
`deploy` of the same topology fails because the interface already exists.
The remove commands at the top of each file delete those cables with
`ip link del`. Deleting one end of a cable removes both ends.

To check that nothing is left:

```bash
ip -br link | grep -- -eth     # should print nothing
```

## Clos needs spanning tree

The Clos topology has more than one path between hosts, which means it has
loops. Without the Rapid Spanning Tree Protocol (RSTP), one broadcast circles
the loops forever and nothing works. The build commands in `clos.clab.gotmpl`
turn RSTP on for each switch (`rstp_enable=true`). Give it about 10 seconds
after `deploy` before you ping.

To see which ports RSTP turned off (look for `Alternate Discarding`):

```bash
sudo ovs-appctl rstp/show leaf1
```

## Exercises

1. Deploy `single`, `linear` and `tree` one at a time. In each, ping from h1
   to h4 and compare the times. Then add 10 ms delay on every switch-to-switch
   link (Getting Started, section 10) and compare again. Which shape is
   fastest for h1 to h4, and why?
2. Build a tree with depth 2 and fanout 3. How many switches and hosts does
   it have? Draw it, then check your drawing with `containerlab graph`.
3. Write a plain `.clab.yml` file for a single switch with 5 hosts.
4. In `clos`, ping continuously from h1 to h8, then take one of leaf1's
   uplinks down with `sudo ip link set leaf1-eth1 down`. What happens to the
   pings? Bring it back with `up`.

Clean up after each one.
