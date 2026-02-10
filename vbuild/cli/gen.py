import sys
import os

from argparse import ArgumentParser
from argparse import Namespace
from typing import Any
from typing import cast

from ..velbuild import parse

kwds: dict[str, str] = {
    "help": "Generate the APKBUILD and install files for a given VELBUILD",
}


def register(_: ArgumentParser):
    pass


def command(args: Namespace) -> int:
    directory = cast(str, args.C)
    filepath = os.path.join(directory, "VELBUILD")
    if not os.path.exists(filepath):
        print(f"{filepath} not found")
        return 1

    package = parse(filepath)
    if package.pkgname is None:  # pyright: ignore[reportAny]
        raise Exception("pkgname is missing")

    print(f">>> {package.pkgname}: Generating APKBUILD")  # pyright: ignore[reportAny]
    package.save(directory)
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
