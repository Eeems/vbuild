import shlex

from . import bash

from .apkbuild import APKBUILD

INSTALL_FUNCTION_NAMES = [
    "preinstall",
    "postinstall",
    "preupgrade",
    "postupgrade",
    "predeinstall",
    "postdeinstall",
    "postosupgrade",
]


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

        for name, value in self.functions.items():
            if name not in INSTALL_FUNCTION_NAMES:
                lines.append(f"{name}() {{{value}}}")

        return "\n".join(lines)

    @property
    def preinstall(self) -> str:
        return self.functions["preinstall"]

    @property
    def postinstall(self) -> str:
        return self.functions["postinstall"]

    @property
    def preupgrade(self) -> str:
        return self.functions["preupgrade"]

    @property
    def postupgrade(self) -> str:
        return self.functions["postupgrade"]

    @property
    def predeinstall(self) -> str:
        return self.functions["predeinstall"]

    @property
    def postdeinstall(self) -> str:
        return self.functions["postdeinstall"]

    @property
    def postosupgrade(self) -> str:
        return self.functions["postosupgrade"]


def parse(path: str) -> VELBUILD:
    with open(path, "r") as f:
        variables, functions = bash.parse(f.read())

    return VELBUILD(variables, functions)
