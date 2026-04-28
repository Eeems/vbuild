import os
from argparse import (
    ArgumentParser,
    Namespace,
)
from typing import cast

from ..abuild import abuild
from ..apkbuild import (
    ErrorType,
    parse,
)

kwds: dict[str, str] = {
    "help": "check the APKBUILD file for violations of policy, superfluous statements, stylistic violations and others",
}


def register(_: ArgumentParser) -> None:
    pass


def command(args: Namespace) -> int:
    ret = abuild(cast(str, args.C), "validate")
    if ret:
        return ret

    directory = cast(str, args.C)
    filepath = os.path.join(directory, "APKBUILD")
    if not os.path.exists(filepath):
        print(f"{filepath} not found")
        return 1

    package = parse(filepath)
    fail = False
    for type, msg in package.validate():
        if type == ErrorType.Error:
            fail = True

        print(f">>> {ErrorType.string(type).upper()}: {package.pkgname}: {msg}")  # pyright: ignore[reportAny]

    return 1 if fail else 0
