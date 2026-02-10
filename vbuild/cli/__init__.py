import argparse

from subprocess import CalledProcessError
from typing import cast

from .__modules__ import modules
from .__modules__ import commands
from .__modules__ import CommandCallable


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
        for name in sorted(modules.keys()):
            module = modules[name]
            subparser = subparsers.add_parser(
                name,
                **getattr(module, "kwds", {}),  # pyright:ignore [reportAny]
            )
            module.register(subparser)  # pyright:ignore [reportAny]
            subparser.set_defaults(func=module.command)  # pyright:ignore [reportAny]

        args = parser.parse_args()
        func = cast(CommandCallable | None, args.func)
        if func is None:
            func = commands["all"]

        return func(args)

    except CalledProcessError as e:
        if e.stderr is not None:  # pyright: ignore[reportAny]
            print(e.stderr)  # pyright: ignore[reportAny]

        raise
