import argparse
from subprocess import CalledProcessError
from typing import cast

from rich.markdown import Markdown
from rich_argparse import RichHelpFormatter

from .__modules__ import (
    CommandCallable,
    commands,
    modules,
)


def main() -> int:
    try:
        parser = argparse.ArgumentParser(
            epilog=Markdown(  # pyright: ignore[reportArgumentType]
                """
### ENVIRONMENT VARIABLES:

| Name | Description |
| ---- | ---------- |
| `$REPODEST` | Packages shall be stored in `$REPODEST/$repo/$arch/$pkgname-$pkgver-r$pkgrel.apk`, where `$repo` is the base name of the parent directory of `$startdir`. |
| `$CARCH` | Architecture to compile package as. |
| `$VBUILD_KEY_NAME` | Key name to use when signing packages. |
| `$VBUILD_DRIVER` | Driver to use for running containers. Possible values are `podman` and `docker`. |
                    """,
                style="argparse.txt",
            ),
            formatter_class=RichHelpFormatter,
        )
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


__all__ = ["commands", "main"]
