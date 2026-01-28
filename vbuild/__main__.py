# nuitka-project: --enable-plugin=pylint-warnings
# nuitka-project: --enable-plugin=upx
# nuitka-project: --warn-implicit-exceptions
# nuitka-project: --onefile
# nuitka-project: --lto=yes
# nuitka-project:--python-flag=-m
import sys

from subprocess import CalledProcessError

from .recipe import parse


def main() -> int:
    try:
        recipe = parse(sys.argv[1])
        print(recipe.text)

        return 0

    except CalledProcessError as e:
        print(e)
        if e.stderr is not None:
            print(e.stderr)

        return 1


if __name__ == "__main__":
    sys.exit(main())
