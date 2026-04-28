from __future__ import annotations

import os
import sys
import traceback
from collections.abc import Callable
from typing import Any

from vbuild.apkbuild import (
    APKBUILD,
    StringArrayProperty,
    StringProperty,
    quoted_string,
)
from vbuild.velbuild import VELBUILD

FAILED = False


def _assert(source: str, debug: Callable[[], Any] | None = None) -> None:  # pyright: ignore[reportExplicitAny]
    global FAILED
    print(f"check {source}: ", end="")
    try:
        if eval(source):  # noqa: S307
            print("pass")
            return

    except Exception:
        FAILED = True  # pyright: ignore[reportConstantRedefinition]
        print("fail")
        traceback.print_exc()
        return

    FAILED = True  # pyright: ignore[reportConstantRedefinition]
    print("fail")
    if debug is not None:
        print(f"  {debug()}")


def _raises(
    source: str,
    exc: type[Exception],
    debug: Callable[[], Any] | None = None,  # pyright: ignore[reportExplicitAny]
) -> None:
    global FAILED
    print(f"check {source} raises {exc.__name__}: ", end="")
    try:
        eval(source)  # noqa: S307
        FAILED = True  # pyright: ignore[reportConstantRedefinition]
        print("fail")
        if debug is not None:
            print(f"  {debug()}")

    except Exception as e:
        if isinstance(e, exc):
            print("pass")
            return

        print("fail")
        traceback.print_exc()


def _isinstance(source: str, cls: type, debug: Callable[[], Any] | None = None) -> None:  # pyright: ignore[reportExplicitAny]
    global FAILED
    print(f"checking that {source} is {cls.__name__}: ", end="")
    try:
        value = eval(source)  # pyright: ignore[reportAny]  # noqa: S307
        if isinstance(value, cls):
            print("pass")
            return

    except Exception:
        FAILED = True  # pyright: ignore[reportConstantRedefinition]
        print("fail")
        traceback.print_exc()
        return

    FAILED = True  # pyright: ignore[reportConstantRedefinition]
    print("fail")
    if debug is not None:
        print(f"  {debug()}")


_assert('quoted_string("x") == "\'x\'"', lambda: quoted_string("x"))
_assert('quoted_string("$srcdir") == "$srcdir"', lambda: quoted_string("$srcdir"))
_assert('quoted_string("${srcdir}") == "$srcdir"', lambda: quoted_string("${srcdir}"))
_assert(
    "quoted_string(\"x${srcdir}x\") == \"'x'$srcdir'x'\"",
    lambda: quoted_string("x${srcdir}x"),
)
_assert(
    'quoted_string("x${srcdir}") == "\'x\'$srcdir"',
    lambda: quoted_string("x${srcdir}"),
)
_assert(
    "quoted_string(\"x/${srcdir}/x\") == \"'x/'$srcdir'/x'\"",
    lambda: quoted_string("x/${srcdir}/x"),
)
_assert(
    "quoted_string(\"x/$srcdir/x\") == \"'x/'$srcdir'/x'\"",
    lambda: quoted_string("x/$srcdir/x"),
)
_assert(
    'quoted_string("${srcdir}x") == "$srcdir\'x\'"', lambda: quoted_string("${srcdir}x")
)
_assert(
    'quoted_string("${srcdir}/x") == "$srcdir\'/x\'"',
    lambda: quoted_string("${srcdir}/x"),
)
_assert(
    'quoted_string("$srcdir/x") == "$srcdir\'/x\'"', lambda: quoted_string("$srcdir/x")
)
_assert('quoted_string("${x}") == "\'${x}\'"', lambda: quoted_string("${x}"))
_assert('quoted_string("$x") == "\'$x\'"', lambda: quoted_string("$x"))
_assert('quoted_string("x${x}") == "\'x${x}\'"', lambda: quoted_string("x${x}"))
_assert('quoted_string("x$x") == "\'x$x\'"', lambda: quoted_string("x$x"))
_assert('quoted_string("") == ""', lambda: quoted_string(""))
_assert('quoted_string("x$") == "\'x$\'"', lambda: quoted_string("x$"))
_assert('quoted_string("x${") == "\'x${\'"', lambda: quoted_string("x${"))
_assert('quoted_string("\'") == "\\"\\\'\\""', lambda: quoted_string("'"))
""
_assert(
    "quoted_string(\"it's\") == \"'it'\\\"'\\\"'s'\"", lambda: quoted_string("it's")
)
_isinstance("APKBUILD.maintainer", StringProperty)
_isinstance("APKBUILD.arch", StringArrayProperty)
apkbuild = APKBUILD({}, {})
_assert("not apkbuild.text.strip()")
_raises("apkbuild.maintainer", AssertionError)
apkbuild.maintainer = "test"
_assert('apkbuild.maintainer == "test"')
_assert("apkbuild.text.strip() == \"maintainer='test'\"")
_raises('setattr(apkbuild, "maintainer", 1)', AssertionError)
_assert("apkbuild.arch is None")
apkbuild.arch = ["test"]
_assert('apkbuild.arch == ["test"]')
_raises('setattr(apkbuild, "arch", "test")', AssertionError)
_assert("apkbuild.text.strip() == \"maintainer='test'\\narch='\\ntest\\n'\"")
apkbuild.arch = ["test", "test2"]
_assert('apkbuild.arch == ["test", "test2"]')
_assert("apkbuild.text.strip() == \"maintainer='test'\\narch='\\ntest\\ntest2\\n'\"")

# Test VELBUILD image property
_isinstance("VELBUILD.image", StringProperty)
velbuild = VELBUILD({}, {})
_assert("velbuild.image is None")
velbuild.image = "my-custom-image:latest"
_assert('velbuild.image == "my-custom-image:latest"')
_raises('setattr(velbuild, "image", 1)', AssertionError)

# Test that image does NOT appear in generated APKBUILD text
velbuild.pkgname = "test-pkg"
velbuild.pkgver = "1.0"
velbuild.pkgrel = "0"
os.environ["VBUILD_DRIVER"] = "docker"
text = velbuild.text
_assert("'image=' not in text", lambda: text)
_assert("'my-custom-image' not in text", lambda: text)

# Test that build() function gets wrapped when image is set
velbuild.functions["build"] = "echo 'building...'"
os.environ["VBUILD_DRIVER"] = "podman"
text = velbuild.text
_assert("'VBUILD_BUILD_SCRIPT' in text", lambda: text)
_assert("'my-custom-image:latest' in text", lambda: text)
_assert("'podman' in text and 'run' in text", lambda: text)

# Test that build() function is NOT wrapped when image is not set
velbuild2 = VELBUILD({}, {})
velbuild2.pkgname = "test-pkg2"
velbuild2.pkgver = "1.0"
velbuild2.pkgrel = "0"
velbuild2.functions["build"] = "echo 'building...'"
text2 = velbuild2.text
_assert("'VBUILD_BUILD_SCRIPT' not in text2", lambda: text2)

if FAILED:
    sys.exit(1)
