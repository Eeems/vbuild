from argparse import (
    ArgumentParser,
    Namespace,
)
from typing import cast

from ..abuild import abuild

kwds: dict[str, str] = {
    "help": "",
}


def register(_: ArgumentParser) -> None:
    pass


def command(args: Namespace) -> int:
    return abuild(cast(str, args.C), "rootpkg")
