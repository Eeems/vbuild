import os
import argparse
import importlib

from subprocess import CalledProcessError
from types import ModuleType
from typing import cast
from typing import Callable
from glob import iglob

CommandCallable = Callable[[argparse.Namespace], int]
commands: dict[str, CommandCallable] = {}
modules: dict[str, ModuleType] = {}

__dirname__ = os.path.dirname(__file__)
modulename = os.path.basename(os.path.dirname(__dirname__))
for file in sorted(iglob(os.path.join(__dirname__, "*.py"))):
    if os.path.basename(file).startswith("__") or file.endswith("__.py"):
        continue

    name = os.path.splitext(os.path.basename(file))[0]
    module = importlib.import_module(f"{modulename}.cli.{name}", modulename)
    modules[name] = module
    assert hasattr(module, "register"), f"Missing register method: {name}"
    assert hasattr(module, "command"), f"Missing command method: {name}"
    commands[name] = module.command  # pyright: ignore[reportAny]


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
