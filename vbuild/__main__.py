# nuitka-project: --enable-plugin=pylint-warnings
# nuitka-project: --enable-plugin=upx
# nuitka-project: --warn-implicit-exceptions
# nuitka-project: --onefile
# nuitka-project: --lto=yes
# nuitka-project:--python-flag=-m
import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
