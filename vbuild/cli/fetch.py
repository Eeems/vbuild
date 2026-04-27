from argparse import (
    ArgumentParser,
    Namespace,
)
from typing import cast

from ..abuild import abuild

kwds: dict[str, str] = {
    "help": "Fetch sources to $SRCDEST",
}


def register(_: ArgumentParser) -> None:
    pass


def command(args: Namespace) -> int:
    return abuild(cast(str, args.C), "fetch")
