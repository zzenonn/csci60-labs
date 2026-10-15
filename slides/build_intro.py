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
                text("l-" + nid, label, x, y, 64, 64, size=24, family=HEAD, weight=700,
                     color="#FFFFFF", align="center", valign="middle", lh=1)]
    return [ellipse("n-" + nid, x + 2, y + 2, 60, 60, fill="#FFFFFF", stroke=BLUE, sw=3),
            text("l-" + nid, label, x + 2, y + 2, 60, 60, size=24, family=HEAD, weight=700,
                 color=INK, align="center", valign="middle", lh=1)]


FRAME_X, FRAME_W = 740, 476


def diagram(nodes, links):
    """Scale and centre the node layout inside the diagram frame, then draw it."""
    xs = [x for _, x, _ in nodes]
    span = max(xs) - min(xs) + 64
    room = FRAME_W - 2 * 32
    k = min(1.0, room / span)
    left = FRAME_X + (FRAME_W - span * k) / 2
    pos = {nid: (round(left + (x - min(xs)) * k), y) for nid, x, y in nodes}
    els = []
    for a, b in links:  # lines first so nodes sit on top
        (ax, ay), (bx, by) = pos[a], pos[b]
        els.append(line(f"e-{a}-{b}", (ax + 32, ay + 32), (bx + 32, by + 32), color=INK, sw=3))
    for nid, _, _ in nodes:
        x, y = pos[nid]
        els += node(nid, nid, x, y, "sw" if nid.startswith(("s", "leaf", "spine")) else "h")
    return els


def caption(eid, html, x, y, w, h=44, size=28, color=GREY):
    return text(eid, html, x, y, w, h, size=size, color=color)


# Topology layouts in the right-hand diagram area
TOPO = {
    "first": ([("h1", 720, 330), ("s1", 920, 330), ("h2", 1120, 330)],
              [("h1", "s1"), ("s1", "h2")]),
    "single": ([("s1", 920, 230), ("h1", 760, 440), ("h2", 920, 440), ("h3", 1080, 440)],
               [("s1", "h1"), ("s1", "h2"), ("s1", "h3")]),
    "linear": ([("s1", 720, 260), ("s2", 860, 260), ("s3", 1000, 260), ("s4", 1140, 260),
                ("h1", 720, 440), ("h2", 860, 440), ("h3", 1000, 440), ("h4", 1140, 440)],
               [("s1", "s2"), ("s2", "s3"), ("s3", "s4"),
                ("s1", "h1"), ("s2", "h2"), ("s3", "h3"), ("s4", "h4")]),
    "tree": ([("s1", 930, 180), ("s2", 790, 330), ("s3", 1070, 330),
              ("h1", 720, 480), ("h2", 860, 480), ("h3", 1000, 480), ("h4", 1140, 480)],
             [("s1", "s2"), ("s1", "s3"), ("s2", "h1"), ("s2", "h2"), ("s3", "h3"), ("s3", "h4")]),
}
LW = 660            # left column width; the diagram frame starts at 740


def topo_slide(sid, title, key, bullets_html, code_txt, cap, notes, csize=22, body_h=110, cy=250):
    nodes, links = TOPO[key]
    extra = []
    if bullets_html:
        extra.append(text("df-body", bullets_html, MX, 130, LW, body_h, size=32, lh=1.35, role="body"))
    if code_txt:
        h = code_h(code_txt, csize, 1.45)
        assert cy + h <= 636, (sid, cy + h)
        extra += code("cd-topo", code_txt, MX, cy, LW, h, grammar="yaml", size=csize, lh=1.45)
    extra += [rect("dg-frame", 740, 140, 476, 470, fill="rgba(0,176,240,0.04)",
                   stroke="rgba(0,176,240,0.25)", sw=1, radius=8)]
    extra += diagram(nodes, links)
    extra.append(caption("dg-cap", cap, 756, 562, 444, 36, size=22))
    return slide_default(sid, title, None, notes=notes, extra=extra)


S = []
S.append(slide_cover(
    "cover", "CSCI 60: Introduction to Containerlab", "Building virtual networks from code",
    "Department of Information Systems and Computer Science", "Last revised October 2026",
    "DISCS", "Ateneo de Manila University",
    notes="Students build every network with Containerlab and Open vSwitch on their own Rocky Linux VM. The hands-on steps are in getting-started/README.md and topologies/ in the csci60-labs repository."))

S.append(slide_default("why", "Why build networks in software?", (bullets([
    "Try out <b>new protocols and topologies</b> without buying equipment",
    "Run a <b>realistic network</b> of real Linux hosts on one machine",
    "Break it, inspect it, rebuild it in seconds",
    "SDN: a <b>controller</b> program tells switches how to forward",
    "Lab 2 uses an SDN controller; Labs 3 and 4 use normal switches",
]), 136, 490, 36), notes="Motivation: test beds, new protocols, no need for real equipment. Point out where SDN appears in the course (Lab 2 only)."))

# ---------- virtualization vs containers ----------
def layer(eid, label, x, y, w, h, fill, color=INK, stroke="none", sw=0, size=26):
    return [rect(eid, x, y, w, h, fill=fill, stroke=stroke, sw=sw, radius=6),
            text(eid + "-t", label, x + 6, y, w - 12, h, size=size, family=HEAD, weight=500, color=color,
                 align="center", valign="middle", lh=1.05)]


def stack_diagram():
    RH, G = 64, 8                      # row height, gap
    y_inf = 568; y_os = y_inf - RH - G; y_mid = y_os - RH - G
    els = []
    for side, x0, title, mid, guest in [("c", MX, "Containers", "Docker", False),
                                         ("v", 664, "Virtual machines", "Hypervisor", True)]:
        w = 552
        els.append(text(f"vz-h-{side}", title, x0, 134, w, 56, size=40, family=HEAD, weight=700,
                        color=BLUE, align="center", lh=1.2))
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
            rows = (["Guest OS"] if guest else []) + ["Bins / Libs", app]
            fh = 40 + len(rows) * (RH + G) + 4
            fy = top - fh
            els.append(rect(f"vz-fr-{side}{i}", bx, fy, bw, fh, fill="rgba(0,176,240,0.05)",
                            stroke=BLUE, sw=2, radius=8))
            els.append(text(f"vz-fl-{side}{i}", "Container" if side == "c" else "VM", bx, fy + 4, bw, 36,
                            size=24, family=HEAD, weight=700, color=BLUE, align="center", lh=1.2))
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
    els.append(rect("vz-div", 640, 140, 1, 492, fill="rgba(64,64,64,0.2)"))
    return els


S.append(slide_default("virt", "Virtual machines and containers", None, extra=stack_diagram(),
    notes="Two ways to run many isolated systems on one computer. A virtual machine runs a whole guest operating system, with its own kernel, on top of a hypervisor. A container shares the host's kernel: Docker only gives each container its own files, processes and network. Your Rocky Linux VM is the right-hand picture, and the lab hosts are the left-hand picture inside it."))

S.append(slide_default("vz-compare", "Why containers for network labs?", None, extra=[table("vz-tbl", [
    ["", "Virtual machine", "Container"],
    ["Own kernel", "yes", "no, shares the host's"],
    ["Starts in", "a minute or more", "under a second"],
    ["Size", "gigabytes", "megabytes"],
    ["On a laptop", "a few", "hundreds"],
    ["Isolation", "a separate machine", "own files, processes, network"],
], MX, 132, CW, 400, cols=[1.1, 1.5, 2.0], size=30),
    text("vz-take", "A lab host only needs its own <b>network</b>, so 100 hosts fit on one VM.",
         MX, 560, CW, 56, size=34, lh=1.3)],
    notes="Tested: 100 lab hosts deploy in about 26 seconds and use about 1.7 GB of memory in total. A host only needs its own interfaces, addresses and routes, which a container gives."))

S.append(slide_default("docker", "What is Docker?", (bullets([
    "Docker runs <b>containers</b>: isolated Linux programs that share the VM's kernel",
    "An <b>image</b> is the template; a <b>container</b> is a running copy of it",
    ("Each container gets its own", ["files, from the image", "processes",
                                    "network: interfaces, addresses, routing table"]),
]), 136, 490, 36), notes="The network part is a Linux network namespace. Containerlab asks Docker to start each host with no network at all (network-mode: none), then plugs in the cables listed in the topology file."))

dk = "sudo docker images            # images on your VM\nsudo docker ps                # running containers\nsudo docker exec h1 ip addr   # a command inside h1"
S.append(slide_default("docker-try", "Our hosts are containers", (bullets([
    "Every lab host is a container from the <code>csci60/host</code> image",
    "Look at them with the <code>docker</code> command:",
]), 136, 120, 36), extra=code("dk-code", dk, MX, 284, CW, code_h(dk, 28), grammar="sh", size=28),
    notes="Run these during a lab to see the hosts Containerlab started. docker exec runs one command inside a host."))

# Tools: three columns
cols = [("Containerlab", "Builds the network from a topology file: starts the hosts and connects the cables.", "containerlab deploy"),
        ("Open vSwitch", "The switches: a software switch built into Linux that speaks OpenFlow.", "ovs-vsctl add-br s1"),
        ("Docker", "Runs each host as a small Linux container with its own interfaces.", "docker exec h1 …")]
extra = []
for i, (h, body, cmd) in enumerate(cols):
    x = MX + i * 392
    extra += [rect(f"tc-{i}", x, 136, 368, 480, fill=PANEL, radius=10),
              rect(f"tb-{i}", x, 136, 368, 10, fill=BLUE, radius=0),
              text(f"th-{i}", h, x + 24, 164, 320, 56, size=40, family=HEAD, weight=700, color=BLUE, lh=1.2),
              text(f"tt-{i}", body, x + 24, 232, 320, 300, size=32, lh=1.35),
              text(f"tx-{i}", cmd, x + 24, 556, 320, 40, size=24, family=MONO, color=INK, lh=1.3)]
S.append(slide_default("tools", "The tools", None, extra=extra,
                       notes="Containerlab builds the network from a file; Open vSwitch provides the switches; Docker gives each host its own network namespace. Students type each tool's commands directly; there is no wrapper."))

S.append(slide_default("setup", "Getting started", (bullets([
    "Install a <b>Rocky Linux 10</b> VM on your own machine",
    ("Install the tools, one command at a time:", ["Docker, Open vSwitch, Containerlab",
                                                   "the lab images"]),
    "Get the course files: <code>git clone</code> the csci60-labs repository",
    "Everything is in <b>getting-started/README.md</b>",
]), 136, 490, 36), notes="Students install their own VM (VirtualBox, VMware or UTM), then the tools and the csci60/host and csci60/controller images. Apple-silicon Macs use the ARM64 Rocky image."))

S.append(slide_section("sec-first", "Your first network", "Is it working?"))

S.append(topo_slide("topofile", "A topology file", "first",
    bullets(["The file <b>is</b> the network: every host, switch and cable",
             "<b>nodes</b>: the hosts and switches",
             "<b>links</b>: the cables, one per line"]),
    None, "h1 and h2 on switch s1", body_h=470,
    notes="Containerlab has no built-in topologies, so students learn how each one is wired by writing it down."))

first_yaml = """name: first
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
    - endpoints: ["h2:eth0", "s1:s1-eth2"]"""
S.append(topo_slide("topofile-2", "first.clab.yml", "first", None, first_yaml,
    "topologies/first.clab.yml (shortened)", csize=20, cy=132,
    notes="The full file is topologies/first.clab.yml; the slide drops the comments and mtu lines. Walk through defaults, then nodes, then links."))

steps = [("1", "Create the switch", "sudo ovs-vsctl add-br s1"),
         ("2", "Build the network", "sudo containerlab deploy -t first.clab.yml"),
         ("3", "Ping h2 from h1", "sudo docker exec h1 ping -c3 10.0.0.2"),
         ("4", "Remove it", "sudo containerlab destroy -t first.clab.yml\nsudo ovs-vsctl del-br s1")]
extra = []
y = 132
for i, (n, h, cmd) in enumerate(steps):
    ch = code_h(cmd, 24, 1.4)
    extra += [ellipse(f"st-n{i}", MX, y + 8, 52, 52, fill=BLUE, stroke="none", sw=0),
              text(f"st-d{i}", n, MX, y + 8, 52, 52, size=28, family=HEAD, weight=700, color="#FFFFFF", align="center", valign="middle", lh=1),
              text(f"st-h{i}", h, MX + 72, y + 12, 300, 48, size=32, family=HEAD, weight=500, lh=1.2)]
    extra += code(f"st-c{i}", cmd, MX + 380, y, CW - 380, ch, grammar="sh", size=24, lh=1.4)
    extra[-1]["fx"] = {"enter": "fade-up", "order": i}
    extra[-2]["fx"] = {"enter": "fade-up", "order": i}
    y += ch + 14
extra.append(caption("st-cap", "Success: <b>0% packet loss</b>. You create and delete the switches yourself.", MX, y + 8, CW, 44, size=30, color=INK))
assert y + 52 <= 636, y
S.append(slide_default("isitworking", "Is it working?", None, extra=extra,
    notes="Each command is typed separately. Step 1 matters: Containerlab attaches hosts to an existing Open vSwitch bridge and never creates or deletes it."))

S.append(slide_default("commands", "Looking around", None, extra=[table("cmd-tbl", [
    ["Command", "What it shows"],
    ["<code>containerlab inspect -t first.clab.yml</code>", "the hosts"],
    ["<code>cat first.clab.yml</code>", "the topology"],
    ["<code>ovs-vsctl show</code>", "switches and their ports"],
    ["<code>docker exec h1 ifconfig -a</code>", "a host's interfaces"],
    ["<code>docker exec h1 route -n</code>", "a host's routing table"],
], MX, 132, CW, 480, cols=[2.3, 1.3], size=28)],
    notes="All of these need sudo. containerlab graph -t first.clab.yml draws the topology in a browser on port 50080."))

S.append(slide_default("commands-2", "Testing", None, extra=[table("cmd-tbl", [
    ["Command", "What it does"],
    ["<code>docker exec h1 ping -c3 10.0.0.2</code>", "ping h2 from h1"],
    ["<code>iperf -s</code> on h2, <code>iperf -c 10.0.0.2</code> on h1", "measure bandwidth"],
    ["<code>docker exec -it h1 bash</code>", "a shell on h1"],
    ["<code>containerlab exec -t first.clab.yml --cmd \"ip -br addr\"</code>", "one command on every host"],
], MX, 132, CW, 480, cols=[2.3, 1.3], size=28)],
    notes="All of these need sudo. containerlab exec runs the same command on every host, which is the quickest way to list every address."))

S.append(slide_section("sec-topos", "Some topologies to try", "All in the topologies/ folder"))

single_yaml = """  nodes:
    s1: {kind: ovs-bridge}
    h1: {}
    h2: {}
    h3: {}
  links:
    - endpoints: ["h1:eth0", "s1:s1-eth1"]
    - endpoints: ["h2:eth0", "s1:s1-eth2"]
    - endpoints: ["h3:eth0", "s1:s1-eth3"]"""
S.append(topo_slide("t-single", "Single: one switch", "single",
    bullets(["Every host on <b>one switch</b>", "A small office or lab bench"]),
    single_yaml, "topologies/single.clab.yml",
    notes="single.clab.yml. Each host gets 10.0.0.N/24 through its exec line (not shown). Every pair of hosts is one switch apart."))

linear_yaml = """  links:
    # switch to switch: the chain
    - endpoints: ["s1:s1-eth2", "s2:s2-eth1"]
    - endpoints: ["s2:s2-eth3", "s3:s3-eth1"]
    - endpoints: ["s3:s3-eth3", "s4:s4-eth1"]
    # one host on each switch
    - endpoints: ["h1:eth0", "s1:s1-eth1"]
    - endpoints: ["h2:eth0", "s2:s2-eth2"]
    # ... h3 and h4 the same way"""
S.append(topo_slide("t-linear", "Linear: a chain of switches", "linear",
    bullets(["Switches in a <b>line</b>, a host on each", "The path grows with every switch"]),
    linear_yaml, "topologies/linear.clab.yml",
    notes="linear.clab.yml. h1 to h4 crosses all four switches. Cables between two switches are not removed by destroy; the file's header lists the ip link del commands."))

tree_tmpl = """# tree.clab_vars.yaml
depth: 2
fanout: 2

# tree.clab.gotmpl (a template)
{{- range $i := seq 1 $hosts }}
    h{{ $i }}: {}
{{- end }}"""
S.append(topo_slide("t-tree", "Tree: levels of switches", "tree",
    bullets(["A root switch, then levels below", "Campus: core, floor, desk"]),
    tree_tmpl, "topologies/tree.clab.gotmpl",
    notes="tree.clab.gotmpl is a template: loops write the hosts and links. Change depth and fanout in tree.clab_vars.yaml. Preview with containerlab graph -t tree.clab.gotmpl --mermaid --offline."))

# Fanout & Clos: two columns
extra = []
for i, (h, items, file) in enumerate([
    ("Fanout", ["One switch, <b>100 hosts</b>", "Written with a loop", "Change <code>hosts:</code> in the vars file"],
     "fanout.clab.gotmpl"),
    ("Clos (leaf-spine)", ["Every leaf links to every spine", "Many paths: data centres",
                           "Loops, so it needs <b>RSTP</b>"], "clos.clab.gotmpl")]):
    x = MX + i * 592
    extra += [rect(f"fc-{i}", x, 136, 560, 480, fill=PANEL, radius=10),
              rect(f"fb-{i}", x, 136, 560, 10, fill=BLUE),
              text(f"fh-{i}", h, x + 28, 164, 504, 60, size=42, family=HEAD, weight=700, color=BLUE, lh=1.2),
              text(f"fl-{i}", bullets(items), x + 28, 240, 504, 280, size=32, lh=1.4),
              text(f"fn-{i}", file, x + 28, 556, 504, 40, size=24, family=MONO, lh=1.3)]
S.append(slide_default("t-big", "Bigger networks: templates", None, extra=extra,
    notes="Containerlab templates (.clab.gotmpl) avoid writing 100 host entries. Tested: 100 hosts deploy in about 26 seconds and use about 1.7 GB of memory. RSTP is the Rapid Spanning Tree Protocol; Clos without it loses every ping, which is a good demonstration."))

pf = "sudo docker exec h1 tc qdisc add dev eth0 root \\\n     netem delay 5ms rate 10mbit loss 10%\nsudo docker exec h1 ping -c5 10.0.0.2\nsudo docker exec h1 tc qdisc del dev eth0 root"
S.append(slide_default("perf", "Setting performance limits", (bullets([
    "Real links have limited <b>bandwidth</b>, <b>delay</b> and <b>loss</b>",
    "Set them on a host's interface with <code>tc</code>",
    "Measure with <code>ping</code> and <code>iperf</code>",
]), 136, 160, 34), extra=code("pf-code", pf, MX, 330, CW, code_h(pf, 26), grammar="sh", size=26),
    notes="tc netem shapes traffic on an interface. The example gives h1 a 10 Mbit/s link with 5 ms delay and 10% loss. It can also go in the topology file's exec list."))

S.append(slide_default("interfaces", "Where are the cables?", (bullets([
    "Each link is a <b>veth pair</b>: a virtual cable with two ends",
    "One end is inside the host, as <code>eth0</code>",
    "The other stays on the VM, as <code>s1-eth1</code> on switch s1",
    "See them with <code>ip -br link</code>",
]), 136, 270, 34), extra=[
    rect("vp-vm", MX, 436, CW, 180, fill="rgba(0,176,240,0.05)", stroke="rgba(0,176,240,0.35)", sw=1, radius=8),
    text("vp-vml", "the VM", MX + 16, 444, 200, 32, size=24, color=GREY, lh=1.2),
    rect("vp-h1", MX + 60, 488, 240, 100, fill="#FFFFFF", stroke=BLUE, sw=2, radius=8),
    text("vp-h1t", "h1<br><code>eth0</code>", MX + 60, 488, 240, 100, size=28, align="center", valign="middle", lh=1.3),
    rect("vp-s1", CW - 236, 488, 240, 100, fill=BLUE, radius=8),
    text("vp-s1t", "s1<br><code>s1-eth1</code>", CW - 236, 488, 240, 100, size=28, color="#FFFFFF", align="center", valign="middle", lh=1.3),
    line("vp-cable", (MX + 300, 538), (CW - 236, 538), color=INK, sw=4, style="dashed", fx={"loop": {"type": "dash-march", "distance": 18, "duration": 1.4}}),
    text("vp-cap", "veth pair", 520, 494, 240, 36, size=24, color=GREY, align="center", lh=1.2),
], notes="Interfaces are created at the OS level. Run ip -br link on the VM and docker exec h1 ip -br link inside the host. The number after @if is the interface index of the other end. Try it before deploy, after it, and after destroy."))

cu = "sudo containerlab destroy --all -y\nsudo ovs-vsctl list-br     # then del-br each one"
S.append(slide_default("cleanup", "Cleaning up", (bullets([
    "<code>containerlab destroy</code> removes hosts and their cables",
    "It does <b>not</b> remove switches, or switch-to-switch cables",
    "Leftovers survive a reboot",
    "Errors? See the FAQ in each handout",
]), 136, 270, 34), extra=code("cu-code", cu, MX, 430, CW, code_h(cu, 26), grammar="sh", size=26),
    notes="Always remove the network when you are done. The full fix, including the check that docker ps -q and ovs-vsctl list-br both print nothing, is in the FAQ of each handout."))

S.append(slide_default("exercises", "Exercises", (
    "1.&nbsp; Build a tree (depth 2, fanout 3) and a single switch with 5 hosts"
    "<br>2.&nbsp; Write a topology: 2 linked switches, 3 hosts on each"
    "<br>3.&nbsp; Compare ping times: tree, single and linear, 4 hosts each"
    "<br>4.&nbsp; Add 10 ms delay to one link. How does ping change?",
    136, 490, 34), notes="Exercises 1 and 2 use the files in topologies/: tree.clab.gotmpl with its vars file, and single.clab.yml as a starting point. Exercise 3 compares paths of different lengths."))

S.append(slide_end("end", "Thank You", "Next: Lab 2, Hubs and switches with OpenFlow"))

d = doc("CSCI 60: Introduction to Containerlab", S,
        meta={"author": "Miguel Zenon Nicanor L. Saavedra, Ph.D.", "company": "Ateneo de Manila University",
              "subject": "CSCI 60", "event": "Introduction to Containerlab"})
write(d, sys.argv[2])
print("wrote", sys.argv[2], len(S), "slides")
