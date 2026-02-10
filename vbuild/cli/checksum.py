from argparse import ArgumentParser
from argparse import Namespace
from typing import cast

from ..abuild import abuild

kwds: dict[str, str] = {
    "help": "Generate checksum to be included in APKBUILD",
}


def register(_: ArgumentParser):
    pass


def command(args: Namespace) -> int:
    return abuild(cast(str, args.C), "checksum")
