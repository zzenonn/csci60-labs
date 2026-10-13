"""Run the Ryu SDN controller in a container (`csci60 ryu ...`)."""

import json
import os
import subprocess
import sys
import time
import urllib.request

from . import util
from .util import info, run

APPS_DIR = os.path.join(util.INSTALL_ROOT, "ryu-apps", "apps")
PREFIX = "csci60-ryu-"


def container_name(port):
    return "%s%d" % (PREFIX, int(port))


def resolve_app(app):
    """Find a Ryu app: a path to a .py file, or a name from ryu-apps."""
    if os.path.isfile(app):
        return os.path.abspath(app)
    for candidate in (app, app + ".py"):
        path = os.path.join(APPS_DIR, candidate)
        if os.path.isfile(path):
            return path
    builtin = app if app.startswith("ryu.") else None
    if builtin:
        return builtin
    util.die("cannot find Ryu app %r. Give a path to a .py file or one of: %s"
             % (app, ", ".join(list_apps()) or "(no Ryu apps in /opt/csci60/ryu-apps)"))


def list_apps():
    if not os.path.isdir(APPS_DIR):
        return []
    return sorted(f[:-3] for f in os.listdir(APPS_DIR)
                  if f.endswith(".py") and not f.startswith("_"))


def start(apps, port=6633, rest_port=None, detach=False, verbose=False,
          observe_links=False):
    util.require_root()
    name = container_name(port)
    run(["docker", "rm", "-f", name], check=False)
    rest_port = rest_port or (8080 + int(port) - 6633)

    mounts, app_args = [], []
    for i, app in enumerate(apps):
        path = resolve_app(app)
        if path.startswith("ryu."):
            app_args.append(path)
            continue
        # Mount each app's directory so helper modules next to it import too.
        d = "/apps/%d" % i
        mounts += ["-v", "%s:%s:ro" % (os.path.dirname(path), d)]
        app_args.append("%s/%s" % (d, os.path.basename(path)))

    args = ["docker", "run", "--name", name, "--network", "host",
            "--label", "csci60=ryu", "--init",
            # Apps may live in a student's home directory; don't relabel it.
            "--security-opt", "label=disable"]
    args += ["-d"] if detach else ["--rm", "-it" if util.interactive() else "-i"]
    args += mounts
    args += ["-e", "PYTHONUNBUFFERED=1", "-e", "PYTHONDONTWRITEBYTECODE=1",
             util.RYU_IMAGE, "ryu-manager",
             "--ofp-tcp-listen-port", str(port),
             "--wsapi-port", str(rest_port)]
    if verbose:
        args.append("--verbose")
    if observe_links:
        args.append("--observe-links")
    args += app_args

    info("Starting Ryu on port %s (control commands on port %s): %s"
         % (port, rest_port, " ".join(apps)))
    if detach:
        run(args)
        info("Ryu is running in the background. Logs: csci60 ryu logs %s"
             % port)
        return 0
    info("Press Ctrl-C to stop the controller")
    try:
        return subprocess.call(args)
    except KeyboardInterrupt:
        return 0
    finally:
        run(["docker", "rm", "-f", name], check=False)


def running():
    out = run(["docker", "ps", "--filter", "label=csci60=ryu", "--format",
               "{{.Names}}"], check=False).stdout.split()
    return sorted(out)


def stop(port=None):
    util.require_root()
    names = [container_name(port)] if port else running()
    for n in names:
        run(["docker", "rm", "-f", n], check=False)
        info("Stopped %s" % n)


def logs(port=6633, follow=True):
    args = ["docker", "logs"]
    if follow:
        args.append("-f")
    args.append(container_name(port))
    try:
        return subprocess.call(args)
    except KeyboardInterrupt:
        return 0


def rest(path, port=6633, data=None):
    """Talk to the control API of a running csci60 Ryu app."""
    rest_port = 8080 + int(port) - 6633
    url = "http://127.0.0.1:%d%s" % (rest_port, path)
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method="POST" if body else "GET",
                                 headers={"Content-Type": "application/json"})
    for _ in range(20):
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read().decode() or "null")
        except urllib.error.HTTPError as exc:
            util.die("controller said: %s" % exc.read().decode().strip())
        except (urllib.error.URLError, ConnectionError):
            time.sleep(0.5)
    util.die("no controller answering on port %d. Start one with: "
             "csci60 ryu start <app>" % rest_port)


def control(args, port=6633):
    """`ryu modes`, `ryu mode SW_LAZYHUB`, `ryu clear`, `ryu detach`."""
    if not args or args[0] in ("modes", "list"):
        res = rest("/csci60/modes", port=port)
        print("Active: %s" % res.get("active"))
        for m in res.get("modes", []):
            print("  %s" % m)
    elif args[0] == "mode" and len(args) == 2:
        res = rest("/csci60/mode", port=port, data={"mode": args[1]})
        print("Cleared all flows; now running %s" % res.get("active"))
    elif args[0] == "clear":
        res = rest("/csci60/clear", port=port, data={})
        print("Cleared flows on %d switch(es)" % res.get("switches", 0))
    elif args[0] == "detach":
        rest("/csci60/mode", port=port, data={"mode": None})
        print("Detached: PacketIns are ignored until you pick a mode")
    else:
        print("usage: ryu modes | ryu mode <NAME> | ryu clear | ryu detach "
              "[--port N]")


def wait_for_switches(count, port=6633, timeout=30):
    """Wait until `count` switches are connected to the controller."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                    "http://127.0.0.1:%d/csci60/switches"
                    % (8080 + int(port) - 6633), timeout=2) as resp:
                if len(json.loads(resp.read().decode())) >= count:
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False
