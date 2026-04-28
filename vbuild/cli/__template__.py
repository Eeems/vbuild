from argparse import (
    ArgumentParser,
    Namespace,
)

kwds: dict[str, str] = {
    "help": "What does this do?",
}


def register(_: ArgumentParser) -> None:
    pass


def command(_: Namespace) -> int:
    return 0
