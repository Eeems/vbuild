from __future__ import annotations

import os
import sys
import traceback
from collections.abc import Callable
from typing import Any

from vbuild.apkbuild import (
    APKBUILD,
    Property,
    is_type,  # noqa: F401  # pyright: ignore[reportUnusedImport]
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


_assert("is_type(None, type(None))")
_assert("not is_type(1, type(None))")
_assert('is_type("hello", str)')
_assert("not is_type(1, str)")
_assert("is_type(None, str | None)")
_assert('is_type("hello", str | None)')
_assert("not is_type(1, str | None)")
_assert("is_type(None, list[str] | None)")
_assert('is_type(["a", "b"], list[str] | None)')
_assert('not is_type("hello", list[str] | None)')
_assert("not is_type([1, 2], list[str] | None)")
_assert("is_type(None, list[str] | str | None)")
_assert('is_type("hello", list[str] | str | None)')
_assert('is_type(["a", "b"], list[str] | str | None)')
_assert("not is_type(1, list[str] | str | None)")
_assert("not is_type([1], list[str] | str | None)")
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
_isinstance("APKBUILD.maintainer", Property)
_isinstance("APKBUILD.arch", Property)
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
_isinstance("VELBUILD.image", property)
velbuild = VELBUILD({}, {})
_assert("velbuild.image is None")
velbuild.image = "my-custom-image:latest"
_assert("\"'my-custom-image:latest'\" in velbuild.image", lambda: velbuild.image)
_raises('setattr(velbuild, "image", 1)', AssertionError)
_assert(
    'set(velbuild.options) == {"!check", "!fhs", "!strip", "!tracedeps"}',
    lambda: set(velbuild.options),
)
velbuild.variables["options"] = "check"
_assert(
    'set(velbuild.options) == {"!fhs", "!strip", "!tracedeps"}',
    lambda: set(velbuild.options),
)
velbuild.variables["options"] += "\nfhs"
_assert(
    'set(velbuild.options) == {"!strip", "!tracedeps"}',
    lambda: set(velbuild.options),
)
velbuild.variables["options"] += "\nstrip"
_assert('set(velbuild.options) == {"!tracedeps"}', lambda: set(velbuild.options))
velbuild.variables["options"] += "\ntracedeps"
_assert("not velbuild.options", lambda: set(velbuild.options))
velbuild.pkgname = "test-pkg"
velbuild.pkgver = "1.0"
velbuild.pkgrel = "0"
os.environ["VBUILD_DRIVER"] = "docker"
text = velbuild.text
_assert("'image=' not in text", lambda: text)
_assert("'my-custom-image' not in text", lambda: text)
velbuild.functions["build"] = "echo 'building...'"
os.environ["VBUILD_DRIVER"] = "podman"
text = velbuild.text
_assert("'VBUILD_BUILD_SCRIPT' in text", lambda: text)
_assert("'my-custom-image:latest' in text", lambda: text)
_assert("'podman' in text and 'run' in text", lambda: text)
velbuild = VELBUILD({}, {})
velbuild.pkgname = "test-pkg"
velbuild.pkgver = "1.0"
velbuild.pkgrel = "0"
velbuild.functions["build"] = "echo 'building...'"
text = velbuild.text
_assert("'VBUILD_BUILD_SCRIPT' not in text", lambda: text)

if FAILED:
    sys.exit(1)
