"""Small helpers shared by the csci60 toolkit."""

import os
import pwd
import subprocess
import sys

STATE_ROOT = "/var/lib/csci60"
LABS_ROOT = os.path.join(STATE_ROOT, "labs")
CURRENT_FILE = os.path.join(STATE_ROOT, "current")
HOST_IMAGE = "csci60/host:latest"
RYU_IMAGE = "csci60/ryu:latest"
INSTALL_ROOT = "/opt/csci60"

# containerlab otherwise checks GitHub for a new release on every run.
CLAB_ENV = dict(os.environ, CLAB_VERSION_CHECK="disable")


class CmdError(RuntimeError):
    def __init__(self, cmd, proc):
        self.cmd = cmd
        self.proc = proc
        out = (proc.stdout or "") + (proc.stderr or "")
        super().__init__("command failed (%s): %s\n%s" % (
            proc.returncode, " ".join(cmd), out.strip()))


def run(cmd, check=True, capture=True, input=None, env=None):
    """Run a command given as a list. Returns CompletedProcess."""
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        universal_newlines=True,
        input=input,
        env=env,
    )
    if check and proc.returncode != 0:
        raise CmdError(cmd, proc)
    return proc


def sh(script, check=True, capture=True):
    """Run a shell snippet on the server itself (not inside a node)."""
    return run(["sh", "-c", script], check=check, capture=capture)


def is_root():
    return os.geteuid() == 0


def elevate():
    """Re-run the current csci60 command through sudo.

    Building networks needs root (Open vSwitch, Docker, network namespaces),
    exactly like `sudo mn`. Re-executing keeps the student-facing command short.
    """
    if is_root():
        return
    script = os.path.realpath(sys.argv[0])
    os.execvp("sudo", ["sudo", script] + sys.argv[1:])


def require_root():
    if not is_root():
        die("this needs root. Run it with sudo, e.g.  sudo python3 %s"
            % os.path.basename(sys.argv[0]))


def invoking_user_home():
    """Home directory of the person who ran the command (even under sudo)."""
    user = os.environ.get("SUDO_USER")
    if user:
        try:
            return pwd.getpwnam(user).pw_dir
        except KeyError:
            pass
    return os.path.expanduser("~")


def die(msg, code=1):
    sys.stderr.write("csci60: %s\n" % msg)
    sys.exit(code)


def info(msg):
    sys.stdout.write("*** %s\n" % msg)
    sys.stdout.flush()


def interactive():
    return sys.stdin.isatty() and sys.stdout.isatty()
