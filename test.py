from __future__ import annotations

import sys

from typing import Callable
from typing import Any

from vbuild.apkbuild import quoted_string

FAILED = False


def _assert(source: str, debug: Callable[[], Any] | None = None):  # pyright: ignore[reportExplicitAny]
    global FAILED
    print(f"check {source}: ", end="")
    if eval(source):
        print("pass")
        return

    FAILED = True  # pyright: ignore[reportConstantRedefinition]
    print("fail")
    if debug is not None:
        print(f"  {debug()}")

_assert('quoted_string("x") == "\'x\'"', lambda: quoted_string("x"))
_assert('quoted_string("$srcdir") == "$srcdir"', lambda: quoted_string("$srcdir"))
_assert('quoted_string("${srcdir}") == "$srcdir"', lambda: quoted_string("${srcdir}"))
_assert('quoted_string("x${srcdir}x") == "\'x\'$srcdir\'x\'"', lambda: quoted_string("x${srcdir}x"))
_assert('quoted_string("x/${srcdir}/x") == "\'x/\'$srcdir\'/x\'"', lambda: quoted_string("x/${srcdir}/x"))
_assert('quoted_string("x/$srcdir/x") == "\'x/\'$srcdir\'/x\'"', lambda: quoted_string("x/$srcdir/x"))
_assert('quoted_string("${srcdir}x") == "$srcdir\'x\'"', lambda: quoted_string("${srcdir}x"))
_assert('quoted_string("${srcdir}/x") == "$srcdir\'/x\'"', lambda: quoted_string("${srcdir}/x"))
_assert('quoted_string("$srcdir/x") == "$srcdir\'/x\'"', lambda: quoted_string("$srcdir/x"))

if FAILED:
    sys.exit(1)
