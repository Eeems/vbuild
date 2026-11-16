import os
from argparse import (
    ArgumentParser,
    Namespace,
)
from typing import cast

from ..abuild import abuild
from ..velbuild import (
    parse,
)

kwds: dict[str, str] = {
    "help": "Fetch sources to $SRCDEST",
}


def register(_: ArgumentParser) -> None:
    pass


def command(args: Namespace) -> int:
    directory = cast(str, args.C)
    parse(os.path.join(directory, "VELBUILD")).download()
    return abuild(directory, "fetch", verbose=cast(bool, args.v))
