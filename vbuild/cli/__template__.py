from argparse import ArgumentParser
from argparse import Namespace

kwds: dict[str, str] = {
    "help": "What does this do?",
}


def register(_: ArgumentParser):
    pass


def command(_: Namespace) -> int:
    return 0
