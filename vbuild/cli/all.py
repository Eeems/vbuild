from argparse import ArgumentParser
from argparse import Namespace

from .__modules__ import commands

kwds: dict[str, str] = {
    "help": "Runs the entire build process. This is the default when no other command is specified.",
}


def register(_: ArgumentParser):
    pass


def command(args: Namespace) -> int:
    for name in [
        "gen",
        "validate",
        "clean",
        "fetch",
        "unpack",
        "prepare",
        "build",
        "check",
        "rootpkg",
    ]:
        ret = commands[name](args)
        if ret:
            return ret

    return 0
