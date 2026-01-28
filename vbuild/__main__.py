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

from .velbuild import parse


def main() -> int:
    try:
        parser = argparse.ArgumentParser()
        _ = parser.add_argument("directory")
        args = parser.parse_args()
        recipe = parse(os.path.join(args.directory, "VELBUILD"))
        print(recipe.text)

        return 0

    except CalledProcessError as e:
        print(e)
        if e.stderr is not None:
            print(e.stderr)

        return 1


if __name__ == "__main__":
    sys.exit(main())
