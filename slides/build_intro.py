"""Builds intro-to-containerlab.bento.html with the DISCS Bento template tools.

Usage: python3 slides/build_intro.py <path to discs-bento-template> slides/intro-to-containerlab.bento.html
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.abspath(sys.argv[1]), "tools"))
from discs import *

# ---------- topology diagram helper (morphs between slides) ----------
def node(nid, label, x, y, kind):
    """kind: 'sw' (blue square) or 'h' (white circle). Returns [shape, label]."""
    if kind == "sw":
        return [rect("n-" + nid, x, y, 64, 64, fill=BLUE, radius=8),
                text("l-" + nid, label, x, y, 64, 64, size=22, family=HEAD, weight=700,
                     color="#FFFFFF", align="center", valign="middle", lh=1)]
    return [ellipse("n-" + nid, x + 4, y + 4, 56, 56, fill="#FFFFFF", stroke=BLUE, sw=3),
            text("l-" + nid, label, x + 4, y + 4, 56, 56, size=20, family=HEAD, weight=700,
                 color=INK, align="center", valign="middle", lh=1)]


def diagram(nodes, links):
    els = []
    for a, b in links:  # lines first so nodes sit on top
        els.append(line(f"e-{a}-{b}", "n-" + a, "n-" + b, color=INK, sw=3))
    for nid, x, y in nodes:
        els += node(nid, nid, x, y, "sw" if nid.startswith(("s", "leaf", "spine")) else "h")
    return els


def caption(eid, html, x, y, w, h=40, size=22, color=GREY):
    return text(eid, html, x, y, w, h, size=size, color=color)


# Topology layouts in the right-hand diagram area (x 700..1216, y 140..620)
TOPO = {
    "first": ([("h1", 720, 330), ("s1", 920, 330), ("h2", 1120, 330)],
              [("h1", "s1"), ("s1", "h2")]),
    "single": ([("s1", 920, 230), ("h1", 760, 440), ("h2", 920, 440), ("h3", 1080, 440)],
               [("s1", "h1"), ("s1", "h2"), ("s1", "h3")]),
    "linear": ([("s1", 720, 260), ("s2", 860, 260), ("s3", 1000, 260), ("s4", 1140, 260),
                ("h1", 720, 440), ("h2", 860, 440), ("h3", 1000, 440), ("h4", 1140, 440)],
               [("s1", "s2"), ("s2", "s3"), ("s3", "s4"),
                ("s1", "h1"), ("s2", "h2"), ("s3", "h3"), ("s4", "h4")]),
    "tree": ([("s1", 930, 180), ("s2", 800, 330), ("s3", 1060, 330),
              ("h1", 730, 480), ("h2", 870, 480), ("h3", 990, 480), ("h4", 1130, 480)],
             [("s1", "s2"), ("s1", "s3"), ("s2", "h1"), ("s2", "h2"), ("s3", "h3"), ("s3", "h4")]),
}


def topo_slide(sid, title, key, bullets_html, code_txt, cap, notes, code_h=None, csize=17, cy=330, body_h=190):
    nodes, links = TOPO[key]
    extra = [text("df-body", bullets_html, MX, 130, 600, body_h, size=24, lh=1.45, role="body")]
    lines = code_txt.count("\n") + 1
    h = code_h or (28 + int(lines * csize * 1.45) + 4)
    assert cy + h <= 636, (sid, cy + h)
    extra += code("cd-topo", code_txt, MX, cy, 600, h, grammar="yaml", size=csize, lh=1.45)
    extra += [rect("dg-frame", 690, 140, 526, 470, fill="rgba(0,176,240,0.04)",
                   stroke="rgba(0,176,240,0.25)", sw=1, radius=8)]
    extra += diagram(nodes, links)
    extra.append(caption("dg-cap", cap, 706, 566, 494, 34, size=18))
    return slide_default(sid, title, None, notes=notes, extra=extra)


S = []
S.append(slide_cover(
    "cover", "CSCI 60: Introduction to Containerlab", "Building virtual networks from code",
    "Department of Information Systems and Computer Science", "Last revised October 2026",
    "DISCS", "Ateneo de Manila University",
    notes="Students build every network with Containerlab and Open vSwitch on their own Rocky Linux VM. The hands-on steps are in getting-started/README.md and topologies/ in the csci60-labs repository."))

S.append(slide_default("why", "Why build networks in software?", (bullets([
    "Try out <b>new protocols and topologies</b> without buying equipment",
    "Run a <b>realistic network</b> with real Linux hosts on one machine",
    "Break it, inspect it, rebuild it in seconds",
    "Software-defined networking (SDN): a <b>controller</b> program decides how switches forward",
    "Lab 2 uses an SDN controller; Labs 3 and 4 use normal switches",
]), 140, 420, 28), notes="Motivation: test beds, new protocols, no need for real equipment. Point out where SDN appears in the course (Lab 2 only)."))

# ---------- virtualization vs containers ----------
def layer(eid, label, x, y, w, h, fill, color=INK, stroke="none", sw=0):
    return [rect(eid, x, y, w, h, fill=fill, stroke=stroke, sw=sw, radius=6),
            text(eid + "-t", label, x, y, w, h, size=20, family=HEAD, weight=500, color=color,
                 align="center", valign="middle", lh=1)]


def stack_diagram():
    RH, G = 52, 8                      # row height, gap
    y_inf = 576; y_os = y_inf - RH - G; y_mid = y_os - RH - G
    els = []
    for side, x0, title, mid, guest in [("c", MX, "Containers", "Docker", False),
                                         ("v", 664, "Virtual machines", "Hypervisor", True)]:
        w = 552
        els.append(text(f"vz-h-{side}", title, x0, 140, w, 48, size=30, family=HEAD, weight=700,
                        color=BLUE, align="center"))
        els += layer(f"vz-inf-{side}", "Infrastructure (the computer)", x0, y_inf, w, RH, "#E6E6E6")
        if side == "c":
            els += layer(f"vz-os-{side}", "Host operating system", x0, y_os, w, RH, INK, color="#FFFFFF")
            els += layer(f"vz-mid-{side}", mid, x0, y_mid, w, RH, BLUE, color="#FFFFFF")
            top = y_mid - G
        else:
            els += layer(f"vz-os-{side}", "Hypervisor", x0, y_os, w, RH, BLUE, color="#FFFFFF")
            top = y_os - G
        bw = (w - 24) // 2
        for i, app in enumerate(["App A", "App B"]):
            bx = x0 + i * (bw + 24)
            rows = (["Guest operating system"] if guest else []) + ["Bins / Libs", app]
            fh = 36 + len(rows) * (RH + G) + 4
            fy = top - fh
            els.append(rect(f"vz-fr-{side}{i}", bx, fy, bw, fh, fill="rgba(0,176,240,0.05)",
                            stroke=BLUE, sw=2, radius=8))
            els.append(text(f"vz-fl-{side}{i}", "Container" if side == "c" else "VM", bx, fy + 6, bw, 28,
                            size=18, family=HEAD, weight=700, color=BLUE, align="center"))
            ry = top - 4 - RH
            for j, r in enumerate(rows):
                fill, col = ("#FFFFFF", INK)
                if r.startswith("Guest"):
                    fill, col = (INK, "#FFFFFF")
                elif r.startswith("Bins"):
                    fill = PANEL
                els += layer(f"vz-r-{side}{i}{j}", r, bx + 12, ry, bw - 24, RH, fill, color=col,
                             stroke="rgba(64,64,64,0.25)" if fill != INK else "none", sw=1)
                ry -= RH + G
    els.append(rect("vz-div", 640, 140, 1, 488, fill="rgba(64,64,64,0.2)"))
    return els


S.append(slide_default("virt", "Virtual machines and containers", None, extra=stack_diagram(),
    notes="Two ways to run many isolated systems on one computer. A virtual machine runs a whole guest operating system, with its own kernel, on top of a hypervisor. A container shares the host's kernel: Docker only gives each container its own files, processes and network. Your Rocky Linux VM is the left-hand picture inside the right-hand one: the VM runs on your laptop's hypervisor, and the lab hosts are containers inside it."))

S.append(slide_default("vz-compare", "Why containers for network labs?", None, extra=[table("vz-tbl", [
    ["", "Virtual machine", "Container"],
    ["Runs its own kernel", "yes", "no, shares the host's"],
    ["Starts in", "a minute or more", "under a second"],
    ["Size", "gigabytes", "megabytes"],
    ["How many on a laptop", "a few", "hundreds"],
    ["Isolation", "strong: a separate machine", "processes, files and network kept apart"],
], MX, 140, CW, 330, cols=[1.3, 1.5, 1.8], size=22),
    text("vz-take", "A lab host only needs its own <b>network</b>: interfaces, addresses and routes. "
         "A container gives exactly that, so a 100-host network fits on one VM.", MX, 500, CW, 80, size=24, lh=1.45)],
    notes="Tested: 100 lab hosts deploy in about 26 seconds and use about 1.7 GB of memory in total."))

S.append(slide_default("docker", "What is Docker?", (bullets([
    "Docker runs <b>containers</b>: isolated Linux programs that share the VM's kernel",
    "An <b>image</b> is the template; a <b>container</b> is a running copy of it",
    ("Each container gets its own", ["files (from the image)", "processes", "network: its own interfaces, addresses and routing table"]),
    "Our lab hosts are containers from the <code>csci60/host</code> image",
]), 136, 330, 26), extra=code("dk-code", "sudo docker images          # the images on your VM\nsudo docker ps              # the running containers\nsudo docker exec h1 ip addr # run a command inside h1",
                              MX, 476, CW, 124, grammar="sh", size=20),
    notes="The network part is a Linux network namespace. Containerlab asks Docker to start each host with no network at all (network-mode: none), then plugs in the cables listed in the topology file."))

# Tools: three columns
cols = [("Containerlab", "Builds the network from a topology file: starts the hosts and connects the cables.", "containerlab deploy"),
        ("Open vSwitch", "The switches. A software switch built into Linux, that speaks OpenFlow.", "ovs-vsctl add-br s1"),
        ("Docker", "Runs each host as a small Linux container with its own interfaces.", "docker exec h1 ping …")]
extra = []
for i, (h, body, cmd) in enumerate(cols):
    x = MX + i * 392
    extra += [rect(f"tc-{i}", x, 150, 368, 400, fill=PANEL, radius=10),
              rect(f"tb-{i}", x, 150, 368, 10, fill=BLUE, radius=0),
              text(f"th-{i}", h, x + 24, 184, 320, 44, size=32, family=HEAD, weight=700, color=BLUE),
              text(f"tt-{i}", body, x + 24, 244, 320, 170, size=24, lh=1.45),
              text(f"tx-{i}", cmd, x + 24, 470, 320, 40, size=18, family=MONO, color=INK)]
S.append(slide_default("tools", "The tools", None, extra=extra,
                       notes="Containerlab builds the network from a file; Open vSwitch provides the switches; Docker gives each host its own network namespace. Students type each tool's commands directly; there is no wrapper."))

S.append(slide_default("setup", "Getting started", (bullets([
    "Install a <b>Rocky Linux 10</b> VM on your own machine (VirtualBox, VMware or UTM)",
    ("Install the tools, one command at a time:", ["Docker, Open vSwitch, Containerlab",
                                                   "the lab images: <code>csci60/host</code>, <code>csci60/controller</code>"]),
    "Get the course files: <code>git clone</code> the csci60-labs repository",
    "Everything is in <b>getting-started/README.md</b>",
]), 140, 420, 28), notes="Students install their own VM, then the tools. Apple-silicon Macs use the ARM64 Rocky image."))

S.append(slide_section("sec-first", "Your first network", "Is it working?"))

first_yaml = '''name: first
prefix: ""
topology:
  defaults:
    kind: linux
    image: csci60/host
    network-mode: none
  nodes:
    h1: {exec: [ip addr add 10.0.0.1/24 dev eth0]}
    h2: {exec: [ip addr add 10.0.0.2/24 dev eth0]}
    s1: {kind: ovs-bridge}
  links:
    - endpoints: ["h1:eth0", "s1:s1-eth1"]
    - endpoints: ["h2:eth0", "s1:s1-eth2"]'''
S.append(topo_slide("topofile", "A topology file", "first",
    bullets(["The file <b>is</b> the network: every host, switch and cable",
             "Each link is one virtual cable: <code>host:interface</code> to <code>switch:port</code>"]),
    first_yaml, "topologies/first.clab.yml (shortened)", csize=14, cy=262, body_h=120,
    notes="The full file is topologies/first.clab.yml; the slide drops the comments and mtu lines. Stress that Containerlab has no built-in topologies, so students learn how each one is wired by writing it down."))

steps = [("1", "Create the switch", "sudo ovs-vsctl add-br s1"),
         ("2", "Build the network", "sudo containerlab deploy -t first.clab.yml"),
         ("3", "Ping h2 from h1", "sudo docker exec h1 ping -c3 10.0.0.2"),
         ("4", "Remove it", "sudo containerlab destroy -t first.clab.yml\nsudo ovs-vsctl del-br s1")]
extra = []
y = 140
for i, (n, h, cmd) in enumerate(steps):
    hh = 92 if "\n" not in cmd else 118
    extra += [ellipse(f"st-n{i}", MX, y + 6, 48, 48, fill=BLUE, stroke="none", sw=0),
              text(f"st-d{i}", n, MX, y + 6, 48, 48, size=24, family=HEAD, weight=700, color="#FFFFFF", align="center", valign="middle", lh=1),
              text(f"st-h{i}", h, MX + 72, y + 12, 300, 40, size=26, family=HEAD, weight=500)]
    extra += code(f"st-c{i}", cmd, MX + 380, y, CW - 380, hh - 20, grammar="sh", size=19)
    extra[-1]["fx"] = {"enter": "fade-up", "order": i}
    extra[-2]["fx"] = {"enter": "fade-up", "order": i}
    y += hh
extra.append(caption("st-cap", "Success: <b>0% packet loss</b>. Containerlab never creates or deletes switches; you do.", MX, 560, CW, 40, size=22, color=INK))
S.append(slide_default("isitworking", "Is it working?", None, extra=extra,
    notes="Each command is typed separately. Step 1 matters: Containerlab attaches hosts to an existing Open vSwitch bridge and never creates or deletes it."))

S.append(slide_default("commands", "Basic commands", None, extra=[table("cmd-tbl", [
    ["Command", "What it does"],
    ["<code>containerlab inspect -t &lt;file&gt;</code>", "list the hosts"],
    ["<code>cat &lt;file&gt;</code> &nbsp;/&nbsp; <code>containerlab graph</code>", "show the topology"],
    ["<code>ovs-vsctl show</code>", "switches and their ports"],
    ["<code>docker exec h1 ifconfig -a</code>", "a host's interfaces"],
    ["<code>docker exec h1 route -n</code>", "a host's routing table"],
    ["<code>docker exec h1 ping -c3 10.0.0.2</code>", "ping between hosts"],
    ["<code>iperf -s</code> on h2, <code>iperf -c</code> on h1", "measure bandwidth"],
    ["<code>docker exec -it h1 bash</code>", "a shell on a host"],
    ["<code>containerlab exec -t &lt;file&gt; --cmd \"ip -br addr\"</code>", "run one command on every host"],
], MX, 136, CW, 470, cols=[2.3, 1.5], size=20)],
    notes="The commands students use most. All of them need sudo. 'containerlab exec -t <file> --cmd \"ip -br addr\"' runs one command on every host at once."))

S.append(slide_section("sec-topos", "Some topologies to try", "All in the topologies/ folder"))

single_yaml = '''  nodes:
    s1: {kind: ovs-bridge}
    h1: {}
    h2: {}
    h3: {}
  links:
    - endpoints: ["h1:eth0", "s1:s1-eth1"]
    - endpoints: ["h2:eth0", "s1:s1-eth2"]
    - endpoints: ["h3:eth0", "s1:s1-eth3"]'''
S.append(topo_slide("t-single", "Single: one switch", "single",
    bullets(["Every host on <b>one switch</b>", "A small office or lab bench"]),
    single_yaml, "topologies/single.clab.yml",
    notes="single.clab.yml. Each host gets 10.0.0.N/24 through its exec line (not shown). Every pair of hosts is one switch apart."))

linear_yaml = '''  links:
    # switch to switch: the chain
    - endpoints: ["s1:s1-eth2", "s2:s2-eth1"]
    - endpoints: ["s2:s2-eth3", "s3:s3-eth1"]
    - endpoints: ["s3:s3-eth3", "s4:s4-eth1"]
    # one host on each switch
    - endpoints: ["h1:eth0", "s1:s1-eth1"]
    - endpoints: ["h2:eth0", "s2:s2-eth2"]'''
S.append(topo_slide("t-linear", "Linear: a chain of switches", "linear",
    bullets(["Switches in a <b>line</b>, one host on each", "The path grows with every switch"]),
    linear_yaml, "topologies/linear.clab.yml",
    notes="linear.clab.yml. h1 to h4 crosses all four switches. Cables between two switches are not removed by destroy; the file's header lists the ip link del commands."))

tree_tmpl = '''# tree.clab_vars.yaml
depth: 2
fanout: 2

# tree.clab.gotmpl (a template)
{{- range $i := seq 1 $hosts }}
    h{{ $i }}: {}
{{- end }}'''
S.append(topo_slide("t-tree", "Tree: levels of switches", "tree",
    bullets(["A root switch, then levels below it", "Campus networks: core, floor, desk"]),
    tree_tmpl, "topologies/tree.clab.gotmpl",
    notes="tree.clab.gotmpl is a template: loops write the hosts and links. Change depth and fanout in tree.clab_vars.yaml. Preview with containerlab graph -t tree.clab.gotmpl --mermaid --offline."))

# Fanout & Clos: two-column comparison
extra = []
for i, (h, items, file) in enumerate([
    ("Fanout", ["One switch with <b>100 hosts</b>", "Written with a loop, not by hand",
                "Change <code>hosts:</code> in the vars file"], "fanout.clab.gotmpl"),
    ("Clos (leaf-spine)", ["Every leaf connects to every spine", "Many paths between hosts: data centres",
                           "Loops, so it needs <b>spanning tree</b> (RSTP)"], "clos.clab.gotmpl")]):
    x = MX + i * 592
    extra += [rect(f"fc-{i}", x, 150, 560, 400, fill=PANEL, radius=10),
              rect(f"fb-{i}", x, 150, 560, 10, fill=BLUE),
              text(f"fh-{i}", h, x + 28, 182, 500, 50, size=34, family=HEAD, weight=700, color=BLUE),
              text(f"fl-{i}", bullets(items), x + 28, 250, 504, 200, size=24, lh=1.5),
              text(f"fn-{i}", file, x + 28, 490, 504, 32, size=18, family=MONO)]
S.append(slide_default("t-big", "Bigger networks: templates", None, extra=extra,
    notes="Containerlab templates (.clab.gotmpl) avoid writing 100 host entries. Tested: 100 hosts deploy in about 26 seconds and use about 1.7 GB of memory. Clos without RSTP loses every ping, which is a good demonstration."))

perf_extra = code("pf-code", "sudo docker exec h1 tc qdisc add dev eth0 root netem \\\n     delay 5ms rate 10mbit loss 10%\nsudo docker exec h1 ping -c5 10.0.0.2\nsudo docker exec h1 tc qdisc del dev eth0 root",
                  MX, 330, CW, 150, grammar="sh", size=20)
S.append(slide_default("perf", "Setting performance limits", (bullets([
    "Real links have limited <b>bandwidth</b>, some <b>delay</b> and some <b>loss</b>; set them with <code>tc</code>",
    "Set it on the host's interface, live, or in the topology file's <code>exec</code> list",
    "Measure with <code>ping</code> (delay, loss) and <code>iperf</code> (bandwidth)",
]), 136, 180, 26), extra=perf_extra,
    notes="tc netem shapes traffic on an interface. The example gives h1 a 10 Mbit/s link with 5 ms delay and 10% loss."))

S.append(slide_default("interfaces", "Where are the cables?", (bullets([
    "Each link is a <b>veth pair</b>: a virtual cable with two ends",
    "One end goes inside the host as <code>eth0</code>",
    "The other stays on the VM as <code>s1-eth1</code>, plugged into switch s1",
    "See them: <code>ip -br link</code> on the VM, <code>docker exec h1 ip -br link</code> on the host",
]), 136, 300, 26), extra=[
    rect("vp-vm", MX, 456, CW, 150, fill="rgba(0,176,240,0.05)", stroke="rgba(0,176,240,0.35)", sw=1, radius=8),
    text("vp-vml", "the VM", MX + 16, 466, 200, 28, size=18, color=GREY),
    rect("vp-h1", MX + 60, 500, 220, 80, fill="#FFFFFF", stroke=BLUE, sw=2, radius=8),
    text("vp-h1t", "h1<br><code>eth0</code>", MX + 60, 500, 220, 80, size=20, align="center", valign="middle", lh=1.3),
    rect("vp-s1", CW - 216, 500, 220, 80, fill=BLUE, radius=8),
    text("vp-s1t", "s1<br><code>s1-eth1</code>", CW - 216, 500, 220, 80, size=20, color="#FFFFFF", align="center", valign="middle", lh=1.3),
    line("vp-cable", "vp-h1", "vp-s1", color=INK, sw=4, style="dashed", fx={"loop": {"type": "dash-march", "distance": 18, "duration": 1.4}}),
    text("vp-cap", "veth pair", 540, 506, 200, 28, size=18, color=GREY, align="center"),
], notes="Interfaces are created at the OS level. The number after @if in 'ip link' output is the interface index of the other end. Run ip -br link before deploy, after it, and after destroy."))

S.append(slide_default("cleanup", "Cleaning up", (bullets([
    "Always remove the network when you are done",
    "<code>containerlab destroy</code> removes hosts and their cables",
    "It does <b>not</b> remove switches, or cables between two switches",
    "Leftovers keep their old settings, even after a reboot",
    "Errors like <i>lab already exists</i>? See the FAQ in each handout",
]), 136, 300, 26), extra=code("cu-code", "sudo containerlab destroy --all -y\nsudo ovs-vsctl list-br          # then del-br each one\nsudo docker ps -q; sudo ovs-vsctl list-br   # both print nothing",
                               MX, 460, CW, 120, grammar="sh", size=20),
    notes="The full fix is in the FAQ of each handout."))

S.append(slide_default("exercises", "Exercises", (
    "1.&nbsp; Build these with <code>tree.clab.gotmpl</code> and a topology file of your own:"
    "<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;◦&nbsp; tree, depth 2, fanout 3 &nbsp;&nbsp;◦&nbsp; single switch, 5 hosts"
    "<br>2.&nbsp; Create your own topology: 2 switches connected to each other, 3 hosts on each"
    "<br>3.&nbsp; Which network performs better? Compare tree (depth 2, fanout 2), single (4 hosts) and linear (4 switches)"
    "<br>4.&nbsp; Add 10 ms delay to one link. How does it change ping between each pair?",
    136, 440, 26), notes="Exercises 1 and 2 use the files in topologies/. Exercise 3 compares paths of different lengths."))

S.append(slide_end("end", "Thank You", "Next: Lab 2, Hubs and switches with OpenFlow"))

d = doc("CSCI 60: Introduction to Containerlab", S,
        meta={"author": "Miguel Zenon Nicanor L. Saavedra, Ph.D.", "company": "Ateneo de Manila University",
              "subject": "CSCI 60", "event": "Introduction to Containerlab"})
write(d, sys.argv[2])
print("wrote", sys.argv[2], len(S), "slides")
