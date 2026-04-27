# nuitka-project: --enable-plugin=pylint-warnings
## nuitka-project: --enable-plugin=upx
# nuitka-project: --warn-implicit-exceptions
# nuitka-project: --lto=yes
# nuitka-project:--include-package=vbuild.cli
# nuitka-project:--report=build/report.xml
import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
