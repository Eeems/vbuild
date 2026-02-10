import sys

from argparse import ArgumentParser
from argparse import Namespace
from typing import Any
from typing import cast

from ..abuild import abuild

kwds: dict[str, str] = {
    "help": "Generate checksum to be included in APKBUILD",
}


def register(_: ArgumentParser):
    pass


def command(args: Namespace) -> int:
    return abuild(cast(str, args.C), "checksum")


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
