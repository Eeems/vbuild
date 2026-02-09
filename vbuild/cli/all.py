import sys

from argparse import ArgumentParser
from argparse import Namespace
from typing import Any
from typing import cast

from ..__main__ import commands

kwds: dict[str, str] = {
    "help": "Runs the entire build process. This is the default when no other command is specified.",
}


def register(_: ArgumentParser):
    pass


def command(args: Namespace) -> int:
    for name in [
        "validate",
        "gen",
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


if __name__ == "__main__":
    kwds["description"] = kwds["help"]
    del kwds["help"]
    parser = ArgumentParser(
        **cast(  # pyright: ignore[reportAny]
            dict[str, Any],  # pyright: ignore[reportExplicitAny]
            kwds,
        ),
    )
    register(parser)
    args = parser.parse_args()
    ret = command(args)
    sys.exit(ret)
