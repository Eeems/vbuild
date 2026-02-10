import os
import shlex

from argparse import ArgumentParser
from argparse import Namespace
from typing import cast

from ..abuild import abuild
from .gen import command as gen
from ..apkbuild import parse as parse_apkbuild
from ..velbuild import parse as parse_velbuild

kwds: dict[str, str] = {
    "help": "Generate checksum to be included in APKBUILD",
}


def register(_: ArgumentParser):
    pass


def command(args: Namespace) -> int:
    directory = cast(str, args.C)
    apkbuild_path = os.path.join(directory, "APKBUILD")
    ret = gen(args)
    if ret:
        return ret

    ret = abuild(directory, "checksum")
    if ret:
        return ret

    apkbuild = parse_apkbuild(apkbuild_path)
    checksums = apkbuild.sha512sums  # pyright: ignore[reportAny]
    velbuild_path = os.path.join(directory, "VELBUILD")
    velbuild = parse_velbuild(velbuild_path)
    print(f">>> {velbuild.pkgname}: Updating the sha512sums in {velbuild_path}...")  # pyright: ignore[reportAny]
    if velbuild.sha512sums == checksums:  # pyright: ignore[reportAny]
        return 0

    with open(velbuild_path, "r") as f:
        lines_in = f.readlines()

    in_block = False
    quote_character = ""
    lines_out: list[str] = []
    for line in lines_in:
        meaningful = line.strip()
        if not in_block and meaningful.startswith("sha512sums="):
            in_block = True
            quote_character = ""
            for character in ("'", '"'):
                parts = meaningful.split(character)
                if len(parts) == 0:
                    continue

                quote_character = character
                if len(parts) > 2:
                    in_block = False

                break

            if not quote_character:
                raise Exception("Failed to find quote character on sha512sums= line")

            continue

        if in_block and meaningful.endswith(quote_character):
            in_block = False
            continue

        if not in_block:
            lines_out.append(line)

    with open(velbuild_path, "w") as f:
        f.writelines(lines_out)
        _ = f.write(f"sha512sums={shlex.quote(checksums)}")  # pyright: ignore[reportAny]

    return 0
