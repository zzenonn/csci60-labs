# Lab server setup (Rocky Linux 10)

Run these commands one at a time, in order, on a fresh Rocky Linux 10 server.
Each step says what it does and how to check it worked. The whole setup takes
about 5 minutes; most of that is step 8.

Tested on Rocky Linux 10.2 (x86_64, SELinux enforcing). Rocky 9 uses the same
steps.

## 0. The server

- Rocky Linux 10 (x86_64), minimal or cloud image.
- 2 vCPU / 4 GB RAM is plenty for one student. Each lab host container uses
  about 1 MB of RAM; Ryu uses about 60 MB.
- Outbound internet access during setup (packages and container images).
- SELinux can stay **enforcing**.
- One server or VM per student (or pair). Students need `sudo` on it, and the
  labs use fixed names (`s1`, `h1`), so two students cannot share one.
  In the cloud, a `t3.medium` is plenty; stop it outside lab hours.

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
sudo dnf -y install dnf-plugins-core iproute tar curl nano
```

## 3. Kernel modules

Rocky's cloud and minimal images ship a trimmed set of kernel modules. These
are needed and live in `kernel-modules-extra`:

| Module         | Needed for                                           |
| -------------- | ---------------------------------------------------- |
| `br_netfilter` | Docker networking                                    |
| `xt_addrtype`  | Docker networking (without it Docker will not start) |
| `sch_netem`    | link speed and delay (`tc ... netem`)                |
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
default are 6633 and 6653. This step adds the ports up to 6660, so students
can run a second controller on another port. Without it, a switch pointed at
such a port logs `connect: Permission denied`.

```bash
sudo dnf -y install policycoreutils-python-utils
sudo semanage port -a -t openflow_port_t -p tcp 6633-6660
sudo semanage port -l | grep openflow
```

The last line should include `6633-6660`.

## 8. Container images

From the top of the `csci60-labs` checkout:

```bash
sudo docker build -t csci60/host setup/images/host   # lab hosts (Alpine Linux + tools)
sudo docker build -t csci60/ryu  setup/images/ryu    # Ryu 4.34 on Python 3.9 (Lab 2)
sudo docker images csci60/*
```

The last command lists both images.

Ryu is no longer maintained and does not install on the Python that ships with
Rocky 10 (3.12). The image pins the last versions that work together:
Python 3.9, Ryu 4.34, eventlet 0.30.2 and setuptools < 58.

## 9. Student account

Building networks needs root (Open vSwitch, Docker, Containerlab), so each
student's account needs `sudo`. This is why each student gets their own
server.

```bash
sudo useradd -m -G wheel student01
sudo passwd student01
```

## 10. Check

Run the network from *Getting Started* once:

```bash
cd getting-started
sudo ovs-vsctl add-br s1
sudo containerlab deploy -t first.clab.yml
sudo docker exec h1 ping -c3 10.0.0.2
sudo containerlab destroy -t first.clab.yml
sudo ovs-vsctl del-br s1
```

The ping should show `0% packet loss`.

## Updating

```bash
cd csci60-labs && git pull
```

Rebuild the images (step 8) only if `setup/images/` changed.
