import sys

from argparse import ArgumentParser
from argparse import Namespace
from typing import Any
from typing import cast

kwds: dict[str, str] = {
    "help": "Fetch sources to $SRCDEST",
}


def register(_: ArgumentParser):
    pass


def command(_: Namespace) -> int:
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
