import sys

_level = "info"


def setLogLevel(level):
    global _level
    _level = level


def info(*args):
    sys.stdout.write("".join(str(a) for a in args))
    sys.stdout.flush()


output = info


def error(*args):
    sys.stderr.write("".join(str(a) for a in args))


def debug(*args):
    if _level == "debug":
        info(*args)
