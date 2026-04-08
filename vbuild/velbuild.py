import os
from collections.abc import Generator
from inspect import cleandoc
from typing import override

from . import bash
from .apkbuild import (
    APKBUILD,
    APKBUILD_AUTOMATIC_VARIABLES,
    ErrorType,
    put_variables,
    quoted_string,
    string_property,
)

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
            if (
                value is None
                or name in bash.DEFAULT_VARIABLE_NAMES
                or name == "sha512sums"
            ):
                continue

            if (
                name in APKBUILD_AUTOMATIC_VARIABLES.keys()
                and value == APKBUILD_AUTOMATIC_VARIABLES[name]
            ):
                continue

            if name in ("upstream_author", "category"):
                name = f"_{name}"

            if isinstance(value, str):
                lines.append(f"{name}={quoted_string(value)}")

            elif isinstance(value, list):
                lines.append(f"{name}=(")
                for x in value:
                    if x is not None:
                        lines.append(f"  {quoted_string(x)}")

                lines.append(")")

            elif isinstance(value, dict):  # pyright: ignore[reportUnnecessaryIsInstance]
                lines.append(f"{name}=(")
                for k, v in value.items():
                    lines.append(f"  [{k}]={quoted_string(v)}")

                lines.append(")")

        subpackages = self.subpackages
        subpackage_map: dict[str, str] = {}
        if subpackages:
            value = self.variables["subpackages"]
            assert isinstance(value, str)
            for spec in value.split():
                parts = spec.split(":", 1)
                subpackage_map[parts[0]] = parts[0] if len(parts) == 1 else parts[1]

        if self.install.strip():  # pyright: ignore[reportAny]
            lines.append(f"install={quoted_string(self.install)}")  # pyright: ignore[reportAny]

        tab = " " * 4
        for name, value in self.functions.items():
            if name in INSTALL_FUNCTION_NAMES or name in subpackage_map.values():
                continue

            if name == "package" and self.postosupgrade is not None:
                fn_name = INSTALL_FUNCTION_NAME_MAP["postosupgrade"]
                value += f'{tab}install -Dm755 "$startdir"/"$pkgname".{fn_name} '  # noqa: PLW2901
                value += (
                    '"$pkgdir"/home/root/.vellum/hooks/post-os-upgrade/"$pkgname";\n'  # noqa: PLW2901
                )

            lines.append(f"{name}() {{{value}}}")

        if subpackages:
            for name, value in subpackages.items():
                lines.append(f"{subpackage_map[name]}() {{{value}}}")

        if "sha512sums" in self.variables:
            value = self.variables["sha512sums"]
            assert isinstance(value, str)
            lines.append(f"sha512sums={quoted_string(value)}")

        return "\n".join(lines)

    def save(self, path: str):
        with open(os.path.join(path, "APKBUILD"), "w") as f:
            _ = f.write(self.text + "\n")

        for name, _ in INSTALL_FUNCTION_NAME_MAP.items():
            src = getattr(self, name)  # pyright: ignore[reportAny]
            if src is None:
                continue

            with open(
                os.path.join(path, f"{self.pkgname}.{INSTALL_FUNCTION_NAME_MAP[name]}"),  # pyright: ignore[reportAny]
                "w",
            ) as f:
                _ = f.write(f"#!/bin/sh\n{src}")

        for name, body in super().subpackages.items():
            _, sub_funcs = bash.parse(body, APKBUILD_AUTOMATIC_VARIABLES)
            for lifecycle_name, lifecycle_file in INSTALL_FUNCTION_NAME_MAP.items():
                if lifecycle_name not in sub_funcs:
                    continue

                src = cleandoc(sub_funcs[lifecycle_name])
                with open(
                    os.path.join(path, f"{name}.{lifecycle_file}"),
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

        if self.sha256sums is not None:  # pyright: ignore[reportAny]
            yield ErrorType.Error, "sha256sums is not supported by vbuild"

    @APKBUILD.subpackages.getter
    def subpackages(self) -> dict[str, str]:
        subpackages = super().subpackages
        tab = " " * 4
        for name, body in subpackages.items():
            context = put_variables(self.variables)
            sub_vars, _ = bash.parse(context + body, APKBUILD_AUTOMATIC_VARIABLES)
            expected_vars, sub_funcs = bash.parse(body, APKBUILD_AUTOMATIC_VARIABLES)

            sub_vars["install"] = ""
            for lifecycle_name in INSTALL_FUNCTION_NAMES:
                if lifecycle_name in sub_funcs and lifecycle_name != "postosupgrade":
                    sub_vars["install"] += (
                        f"\n{name}.{INSTALL_FUNCTION_NAME_MAP[lifecycle_name]}"
                    )

            if sub_vars["install"]:
                sub_vars["install"] += "\n"
                expected_vars["install"] = ""

            subpackages[name] = ""
            for var_name in expected_vars.keys():
                if (
                    var_name in bash.DEFAULT_VARIABLE_NAMES
                    or var_name in APKBUILD_AUTOMATIC_VARIABLES
                ):
                    continue

                var_value = sub_vars[var_name]
                if var_value is None:
                    continue

                if isinstance(var_value, str):
                    subpackages[name] += (
                        f"\n{tab}{var_name}={quoted_string(var_value)};"
                    )

                elif isinstance(var_value, list):
                    joined = " ".join(v for v in var_value if v is not None)
                    subpackages[name] += f"\n{tab}{var_name}={quoted_string(joined)};"

            if "package" in sub_funcs:
                subpackages[name] += "\n" + sub_funcs["package"]

            if "postosupgrade" in sub_funcs:
                fn_name = INSTALL_FUNCTION_NAME_MAP["postosupgrade"]
                subpackages[name] += (
                    f'\n{tab}install -Dm755 "$startdir"/{name}.{fn_name} '
                )
                subpackages[name] += (
                    f'"$pkgdir"/home/root/.vellum/hooks/post-os-upgrade/{name};\n'
                )

        return subpackages

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
        variables, functions = bash.parse(f.read(), APKBUILD_AUTOMATIC_VARIABLES)

    return VELBUILD(variables, functions)
