# Instructor notes

## One server per student (recommended)

The old setup was one Mininet VM per student. The closest equivalent is one
small Rocky Linux server or VM per student (or per pair), set up by following
`setup/README.md`:

- Cloud: `t3.medium` (2 vCPU, 4 GB) is plenty. A full class costs little
  if servers are stopped outside lab hours.
- On-premises: a Rocky Linux VM in VirtualBox/VMware/Proxmox, 2 vCPU / 2-4 GB.
  Students SSH in exactly as they did to the Mininet VM.

**Why not one big shared server?** Each server runs one `csci60` network at a
time, like one Mininet per VM. Switch names (`s1`), controller ports (6633) and
host names (`h1`) are fixed by the lab handouts, so two students cannot both
have an `s1` on the same machine. Students on a shared server would also be able
to run their own scripts as root through `csci60 run`. Use separate servers.

## Adding students

```bash
sudo usermod -aG csci60 student01
```

The `csci60` group may run `csci60` as root without a password (and nothing
else). Students do not need Docker access.

## Updating

See *Updating* at the end of `setup/README.md`.

## Commands worth knowing

| Command                         | Use                                                      |
| ------------------------------- | -------------------------------------------------------- |
| `csci60 doctor`                 | checks Docker, OVS, kernel modules, images, SELinux ports |
| `csci60 status`                 | running network, switches, controllers                    |
| `csci60 reset`                  | removes every network and controller (`mn -c` + `killall controller`) |
| `csci60 flows [s1]`             | flow tables of the running network                         |
| `csci60 ryu logs`               | output of a background controller                          |
| `sudo ovs-vsctl show`           | raw Open vSwitch state                                     |
| `sudo containerlab inspect --all` | raw Containerlab state                                   |

## Troubleshooting

| Symptom                                                 | Cause / fix                                               |
| ------------------------------------------------------- | --------------------------------------------------------- |
| Docker will not start; journal mentions `xt_addrtype`    | `kernel-modules-extra` missing; redo step 3 of `setup/README.md` (reboot first if the kernel was just updated) |
| `--link tc,delay=...` fails with `Specified qdisc kind is unknown` | `sch_netem` missing; same fix                    |
| A switch on port 6644 never connects; `ovs-vswitchd.log` says `Permission denied` | SELinux port label missing: `sudo semanage port -a -t openflow_port_t -p tcp 6633-6660` |
| `Interface ... already exists` on start                  | leftover from a crash: `csci60 reset`                     |
| `pingall` 100% dropped with `--controller remote`        | no controller running, or a mode that drops traffic       |

## Limits and differences from Mininet

- No `xterm` (no graphics on the server); use `csci60 shell h1`.
- Python 3 only. The course scripts in `hip2b2/poxstuff` run unchanged;
  scripts with Python 2 `print` statements need parentheses.
- `--switch user` / `UserSwitch` behave as Open vSwitch.
- The compatibility layer covers what the CSCI 60 labs and the Mininet
  intro deck use. Less common Mininet APIs (`Node.popen`, `NAT`,
  `net.addNAT`, `OVSController`, `MiniEdit`) are not implemented.
- POX is gone; Ryu takes its place. See `ryu-apps/README.md` for the mapping
  of each POX app.
