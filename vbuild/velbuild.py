import os
import shlex

from . import bash

from .apkbuild import APKBUILD


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

        lines.append(f"install={shlex.quote(self.install)}")
        for name, value in self.functions.items():
            if name not in INSTALL_FUNCTION_NAMES:
                lines.append(f"{name}() {{{value}}}")

        return "\n".join(lines)

    def save(self, path: str):
        with open(os.path.join(path, "APKBUILD"), "w") as f:
            _ = f.write(self.text)

        for name, suffix in INSTALL_FUNCTION_NAME_MAP.items():
            src = getattr(self, name)
            if src is None:
                continue

            with open(
                os.path.join(path, f"{self.pkgname}.{INSTALL_FUNCTION_NAME_MAP[name]}"),
                "w",
            ) as f:
                _ = f.write("#!/bin/sh" + src)

    @APKBUILD.install.getter
    def install(self) -> str:
        data = ""
        for name in INSTALL_FUNCTION_NAMES:
            if name in self.functions:
                data += f"\n{self.pkgname}.{INSTALL_FUNCTION_NAME_MAP[name]}"

        return data + "\n"

    @property
    def preinstall(self) -> str | None:
        return self.functions.get("preinstall", None)

    @property
    def postinstall(self) -> str | None:
        return self.functions.get("postinstall", None)

    @property
    def preupgrade(self) -> str | None:
        return self.functions.get("preupgrade", None)

    @property
    def postupgrade(self) -> str | None:
        return self.functions.get("postupgrade", None)

    @property
    def predeinstall(self) -> str | None:
        return self.functions.get("predeinstall", None)

    @property
    def postdeinstall(self) -> str | None:
        return self.functions.get("postdeinstall", None)

    @property
    def postosupgrade(self) -> str | None:
        return self.functions.get("postosupgrade", None)


def parse(path: str) -> VELBUILD:
    with open(path, "r") as f:
        variables, functions = bash.parse(f.read())

    return VELBUILD(variables, functions)
