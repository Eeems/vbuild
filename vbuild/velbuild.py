import os
import shlex

from collections.abc import Generator
from inspect import cleandoc
from typing import override

from . import bash

from .apkbuild import APKBUILD
from .apkbuild import ErrorType
from .apkbuild import string_property


INSTALL_FUNCTION_NAME_MAP = {
    "preinstall": "pre-install",
    "postinstall": "post-install",
    "preupgrade": "pre-upgrade",
    "postupgrade": "post-upgrade",
    "predeinstall": "pre-deinstall",
    "postdeinstall": "post-deinstall",
    "postosupgrade": "post-os-upgrade",
}

INSTALL_FUNCTION_NAMES = set(INSTALL_FUNCTION_NAME_MAP.keys())


class VELBUILD(APKBUILD):
    @APKBUILD.text.getter
    def text(self) -> str:
        lines: list[str] = []

        for name, value in self.variables.items():
            if value is None or name in bash.DEFAULT_VARIABLE_NAMES:
                continue

            if name in ("upstream_author", "category"):
                name = f"_{name}"

            if isinstance(value, str):
                lines.append(f"{name}={shlex.quote(value)}")

            elif isinstance(value, list):
                lines.append(f"{name}=(")
                for x in value:
                    if x is not None:
                        lines.append(f"  {shlex.quote(x)}")

                lines.append(")")

            elif isinstance(value, dict):  # pyright: ignore[reportUnnecessaryIsInstance]
                lines.append(f"{name}=(")
                for k, v in value.items():
                    lines.append(f"  [{k}]={shlex.quote(v)}")

                lines.append(")")

        lines.append(f"install={shlex.quote(self.install)}")  # pyright: ignore[reportAny]
        for name, value in self.functions.items():
            if name not in INSTALL_FUNCTION_NAMES:
                lines.append(f"{name}() {{{value}}}")

        return "\n".join(lines)

    def save(self, path: str):
        with open(os.path.join(path, "APKBUILD"), "w") as f:
            _ = f.write(self.text)

        for name, _ in INSTALL_FUNCTION_NAME_MAP.items():
            src = getattr(self, name)  # pyright: ignore[reportAny]
            if src is None:
                continue

            with open(
                os.path.join(path, f"{self.pkgname}.{INSTALL_FUNCTION_NAME_MAP[name]}"),  # pyright: ignore[reportAny]
                "w",
            ) as f:
                _ = f.write(f"#!/bin/sh\n{src}")

    @override
    def validate(self) -> Generator[tuple[ErrorType, str]]:
        if self.upstream_author is None:  # pyright: ignore[reportAny]
            yield ErrorType.Error, "_upstream_author is not set"

        if self.category is None:  # pyright: ignore[reportAny]
            yield ErrorType.Error, "_category is not set"

        pkgdesc_len = len(self.pkgdesc)  # pyright: ignore[reportAny]
        if pkgdesc_len >= 128:
            yield (
                ErrorType.Error,
                f"pkgdesc is too long ({pkgdesc_len} chars, must be <128)",
            )

        if self.maintainer is None:  # pyright: ignore[reportAny]
            yield ErrorType.Error, "maintainer is not set"

    @APKBUILD.install.getter
    def install(self) -> str:
        data = ""
        for name in INSTALL_FUNCTION_NAMES:
            if name in self.functions and name != "postosupgrade":
                data += f"\n{self.pkgname}.{INSTALL_FUNCTION_NAME_MAP[name]}"  # pyright: ignore[reportAny]

        return data + "\n"

    def _getsrc(self, name: str) -> str | None:
        src = self.functions.get(name, None)
        if src is None:
            return None

        return cleandoc(src)

    @property
    def preinstall(self) -> str | None:
        return self._getsrc("preinstall")

    @property
    def postinstall(self) -> str | None:
        return self._getsrc("postinstall")

    @property
    def preupgrade(self) -> str | None:
        return self._getsrc("preupgrade")

    @property
    def postupgrade(self) -> str | None:
        return self._getsrc("postupgrade")

    @property
    def predeinstall(self) -> str | None:
        return self._getsrc("predeinstall")

    @property
    def postdeinstall(self) -> str | None:
        return self._getsrc("postdeinstall")

    @property
    def postosupgrade(self) -> str | None:
        return self._getsrc("postosupgrade")

    @string_property
    def category(self, value: str | None) -> str | None:
        return value

    @string_property
    def upstream_author(self, value: str | None) -> str | None:
        return value


def parse(path: str) -> VELBUILD:
    with open(path, "r") as f:
        variables, functions = bash.parse(f.read())

    return VELBUILD(variables, functions)
