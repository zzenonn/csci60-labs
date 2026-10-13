# Lab server setup (Rocky Linux 10)

Run these commands one at a time, in order, on a fresh Rocky Linux 10 server.
Each step says what it does and how to check it worked. The whole setup takes
about 5 minutes; most of that is step 9.

Tested on Rocky Linux 10.2 (x86_64, SELinux enforcing). Rocky 9 uses the same
steps.

## 0. The server

- Rocky Linux 10 (x86_64), minimal or cloud image.
- 2 vCPU / 4 GB RAM is plenty for one student. Each lab host container uses
  about 1 MB of RAM; Ryu uses about 60 MB.
- Outbound internet access during setup (packages and container images).
- SELinux can stay **enforcing**.
- Give each student their own server or VM, as with the old Mininet VM. See
  `docs/instructor-notes.md` for why.

## 1. Get this repository

```bash
sudo dnf -y install git
git clone https://github.com/zzenonn/csci60-labs.git
cd csci60-labs
```

The repository is private: log in with a GitHub account that has access
(a personal access token works as the password).

## 2. Base packages

```bash
sudo dnf -y install dnf-plugins-core python3 python3-pyyaml \
    iproute iputils tcpdump ethtool tar curl
```

## 3. Kernel modules

Rocky's cloud and minimal images ship a trimmed set of kernel modules. These
are needed and live in `kernel-modules-extra`:

| Module         | Needed for                                           |
| -------------- | ---------------------------------------------------- |
| `br_netfilter` | Docker networking                                    |
| `xt_addrtype`  | Docker networking (without it Docker will not start) |
| `sch_netem`    | link delay and loss (`--link tc,delay=10ms,loss=5`)  |
| `openvswitch`  | Open vSwitch (already in the base kernel)            |

```bash
sudo dnf -y install kernel-modules-extra-$(uname -r)
printf '%s\n' openvswitch br_netfilter xt_addrtype sch_netem | sudo tee /etc/modules-load.d/csci60.conf
sudo modprobe -a openvswitch br_netfilter xt_addrtype sch_netem
lsmod | grep -E 'openvswitch|br_netfilter|xt_addrtype|sch_netem'
```

The last command should list all four modules. If `dnf` cannot find
`kernel-modules-extra` for the running kernel, the kernel was updated but the
server was not rebooted: run `sudo reboot`, then do this step again.

## 4. Docker

```bash
sudo dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo
sudo dnf -y install docker-ce docker-ce-cli containerd.io
sudo systemctl enable --now docker
sudo docker info --format '{{.ServerVersion}}'
```

The last command prints Docker's version. If Docker fails to start and
`journalctl -u docker` mentions `xt_addrtype` or `br_netfilter`, step 3 is
missing.

## 5. Open vSwitch

Rocky does not ship Open vSwitch itself. The CentOS NFV SIG repository does:

```bash
sudo dnf -y install centos-release-nfv-openvswitch
sudo dnf -y install openvswitch3.5
sudo systemctl enable --now openvswitch
sudo ovs-vsctl show
```

`ovs-vsctl show` prints an id and `ovs_version: "3.5..."`. If `openvswitch3.5`
is not found, `dnf list 'openvswitch3.*'` shows the versions available; use
the newest.

## 6. Containerlab

```bash
bash -c "$(curl -sL https://get.containerlab.dev)" -- -v 0.81.0
containerlab version
```

## 7. SELinux: OpenFlow ports

Open vSwitch may only connect to TCP ports labelled `openflow_port_t`, which by
default are 6633 and 6653. Labs with a second controller use 6644. Without this
step that switch logs `connect: Permission denied` and its hosts cannot reach
each other.

```bash
sudo dnf -y install policycoreutils-python-utils
sudo semanage port -a -t openflow_port_t -p tcp 6633-6660
sudo semanage port -l | grep openflow
```

The last line should include `6633-6660`.

## 8. The csci60 tool and the Ryu apps

From the top of the `csci60-labs` checkout:

```bash
sudo mkdir -p /opt/csci60 /var/lib/csci60/labs
sudo cp -a setup/toolkit /opt/csci60/toolkit
sudo cp -a ryu-apps /opt/csci60/ryu-apps
sudo chmod -R a+rX /opt/csci60
sudo ln -sf /opt/csci60/toolkit/bin/csci60 /usr/bin/csci60
```

`csci60` goes in `/usr/bin` because `sudo` on Rocky does not search
`/usr/local/bin`. `csci60 ryu start <name>` looks for
`/opt/csci60/ryu-apps/apps/<name>.py`.

Then let Python find the toolkit, so Mininet scripts
(`from mininet.net import Mininet`) work unchanged:

```bash
SITE=$(python3 -c 'import sysconfig; print(sysconfig.get_path("purelib", vars={"base": "/usr"}))')
sudo mkdir -p "$SITE"
echo /opt/csci60/toolkit/compat | sudo tee "$SITE/csci60-mininet-compat.pth"
echo /opt/csci60/toolkit        | sudo tee "$SITE/csci60.pth"
python3 -c 'import mininet.net, csci60; print("ok")'
```

The last command prints `ok`.

## 9. Container images

```bash
sudo docker build -t csci60/host:latest setup/images/host   # lab hosts (Alpine + tools)
sudo docker build -t csci60/ryu:latest  setup/images/ryu    # Ryu 4.34 on Python 3.9
```

Ryu is no longer maintained and does not install on the Python that ships with
Rocky 10 (3.12). The image pins the last versions that work together:
Python 3.9, Ryu 4.34, eventlet 0.30.2 and setuptools < 58.

## 10. Student access

Building networks needs root (network namespaces, Open vSwitch, Docker).
Students do not get general sudo, or Docker access. Members of the `csci60`
group may run `csci60` as root, and nothing else:

```bash
sudo groupadd csci60
sudo tee /etc/sudoers.d/csci60 <<'EOF'
%csci60 ALL=(root) NOPASSWD: /usr/bin/csci60, /opt/csci60/toolkit/bin/csci60
Defaults!/usr/bin/csci60 !requiretty
EOF
sudo chmod 440 /etc/sudoers.d/csci60
sudo visudo -cf /etc/sudoers.d/csci60
```

`visudo` should print `parsed OK`. Then, for yourself and for each student
(they log out and back in afterwards):

```bash
sudo usermod -aG csci60 $USER
sudo usermod -aG csci60 student01
```

`csci60` re-runs itself with `sudo` when it needs to, so students never type
`sudo` themselves.

Anyone allowed to run `csci60` can run their own Python scripts as root
(`csci60 run x.py`), just as with `sudo mn` / `sudo python` before. That is
another reason to give each student their own server.

## 11. Check

Log out and back in (for the group), then:

```bash
csci60 doctor
csci60 start --test pingall --topo single,3
```

`doctor` ends with `All good.`; the second command ends with
`*** Results: 0% dropped (6/6 received)`.

## Updating

```bash
cd csci60-labs && git pull
sudo rm -rf /opt/csci60/toolkit /opt/csci60/ryu-apps
sudo cp -a setup/toolkit /opt/csci60/toolkit
sudo cp -a ryu-apps /opt/csci60/ryu-apps
sudo chmod -R a+rX /opt/csci60
```

Rebuild the images (step 9) only if `setup/images/` changed.
