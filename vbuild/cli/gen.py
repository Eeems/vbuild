import os

from argparse import ArgumentParser
from argparse import Namespace
from typing import cast

from ..apkbuild import ErrorType
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
    fail = False
    for type, msg in package.validate():
        if type == ErrorType.Error:
            fail = True

        print(f">>> {ErrorType.string(type).upper()}: {package.pkgname}: {msg}")  # pyright: ignore[reportAny]

    if fail:
        return 1

    package.save(directory)
    return 0
