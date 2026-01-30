# nuitka-project: --enable-plugin=pylint-warnings
# nuitka-project: --enable-plugin=upx
# nuitka-project: --warn-implicit-exceptions
# nuitka-project: --onefile
# nuitka-project: --lto=yes
# nuitka-project:--python-flag=-m
import os
import sys
import argparse

from subprocess import CalledProcessError
from typing import cast
from typing import Callable
from inspect import cleandoc

from .velbuild import parse

CommandCallable = Callable[[argparse.Namespace], int]
CommandRegisterCallable = Callable[[argparse.ArgumentParser | None], CommandCallable]
commands: list[CommandRegisterCallable] = []


def command(func: CommandRegisterCallable) -> CommandCallable:
    commands.append(func)
    return func(None)


@command
def all(parser: argparse.ArgumentParser | None) -> CommandCallable:
    """Runs the entire build process. This is the default when no other command is specified."""
    if parser is not None:
        pass

    def func(args: argparse.Namespace) -> int:
        ret = validate(args)
        if ret:
            return ret

        ret = gen(args)
        if ret:
            return ret

        ret = clean(args)
        if ret:
            return ret

        ret = fetch(args)
        if ret:
            return ret

        ret = unpack(args)
        if ret:
            return ret

        ret = prepare(args)
        if ret:
            return ret

        ret = build(args)
        if ret:
            return ret

        ret = check(args)
        if ret:
            return ret

        ret = rootpkg(args)
        if ret:
            return ret

        return 0

    return func


@command
def validate(parser: argparse.ArgumentParser | None) -> CommandCallable:
    """check the APKBUILD file for violations of policy, superfluous statements, stylistic violations and others"""

    if parser is not None:
        pass

    def func(args: argparse.Namespace) -> int:
        return 0

    return func


@command
def gen(parser: argparse.ArgumentParser | None) -> CommandCallable:
    """Generate the APKBUILD and install files for a given VELBUILD"""

    if parser is not None:
        pass

    def func(args: argparse.Namespace) -> int:
        directory = cast(str, args.C)
        filepath = os.path.join(directory, "VELBUILD")
        if not os.path.exists(filepath):
            print(f"{filepath} not found")
            return 1

        parse(filepath).save(directory)
        return 0

    return func


@command
def clean(parser: argparse.ArgumentParser | None) -> CommandCallable:
    def func(args: argparse.Namespace) -> int:
        return 0

    return func


@command
def fetch(parser: argparse.ArgumentParser | None) -> CommandCallable:
    """Fetch sources to $SRCDEST"""
    if parser is not None:
        pass

    def func(args: argparse.Namespace) -> int:
        return 0

    return func


@command
def unpack(parser: argparse.ArgumentParser | None) -> CommandCallable:
    if parser is not None:
        pass

    def func(args: argparse.Namespace) -> int:
        return 0

    return func


@command
def prepare(parser: argparse.ArgumentParser | None) -> CommandCallable:
    if parser is not None:
        pass

    def func(args: argparse.Namespace) -> int:
        return 0

    return func


@command
def build(parser: argparse.ArgumentParser | None) -> CommandCallable:
    if parser is not None:
        pass
    """Compile and install the package into $pkgdir"""

    def func(args: argparse.Namespace) -> int:
        return 0

    return func


@command
def check(parser: argparse.ArgumentParser | None) -> CommandCallable:
    if parser is not None:
        pass

    def func(args: argparse.Namespace) -> int:
        return 0

    return func


@command
def rootpkg(parser: argparse.ArgumentParser | None) -> CommandCallable:
    if parser is not None:
        pass

    def func(args: argparse.Namespace) -> int:
        return 0

    return func


@command
def checksum(parser: argparse.ArgumentParser | None) -> CommandCallable:
    if parser is not None:
        pass
    """Generate checksum to be included in APKBUILD"""

    def func(args: argparse.Namespace) -> int:
        return 0

    return func


def main() -> int:
    try:
        parser = argparse.ArgumentParser()
        _ = parser.add_argument(
            "-C",
            help="Change directory to DIR before running any commands",
            default=".",
            metavar="DIR",
        )
        parser.set_defaults(func=None)
        subparsers = parser.add_subparsers(help="COMMANDS")
        for func in commands:
            name = func.__name__
            subparser = subparsers.add_parser(name, help=cleandoc(func.__doc__ or ""))
            subparser.set_defaults(func=func(subparser))

        args = parser.parse_args()
        func = cast(CommandCallable | None, args.func)
        if func is None:
            parser.print_usage()
            return 1

        return func(args)

    except CalledProcessError as e:
        if e.stderr is not None:
            print(e.stderr)

        raise


if __name__ == "__main__":
    sys.exit(main())
