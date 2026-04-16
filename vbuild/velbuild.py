import os
from collections.abc import Generator
from inspect import cleandoc
from typing import (
    cast,
    override,
)

from . import bash
from .apkbuild import (
    APKBUILD,
    APKBUILD_AUTOMATIC_VARIABLES,
    ErrorType,
    put_variables,
    quoted_string,
    string_array_property,
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

        if "options" not in self.variables:
            self.variables["options"] = ""

        if self.systemdunits and "!fhs" not in self.options:
            self.options = list([*self.options, "!fhs"])

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

        if self.install.strip():  # pyright: ignore[reportAny]
            lines.append(f"install={quoted_string(self.install)}")  # pyright: ignore[reportAny]

        tab = " " * 4
        subpackage_map = self._subpackages
        subpackage_functions = subpackage_map.values()
        if "package" not in self.functions:
            self.functions["package"] = "\n"

        for name, value in self.functions.items():
            if name in INSTALL_FUNCTION_NAMES or name in subpackage_functions:
                continue

            if name == "package" and self.postosupgrade is not None:
                fn_name = INSTALL_FUNCTION_NAME_MAP["postosupgrade"]
                value += f'{tab}install -Dm755 "$startdir"/"$pkgname".{fn_name} '  # noqa: PLW2901
                value += (
                    '"$pkgdir"/home/root/.vellum/hooks/post-os-upgrade/"$pkgname";\n'  # noqa: PLW2901
                )

            if name == "package":
                for unit in self.systemdunits:  # pyright: ignore[reportAny]
                    unit_name = os.path.basename(unit)
                    value += f'{tab}install -Dm644 "$srcdir/{unit}" "$pkgdir/home/root/.vellum/share/{self.pkgname}/{unit_name}";\n'

            lines.append(f"{name}() {{{value}}}")

        for name, value in self.subpackages.items():
            lines.append(f"{subpackage_map[name]}() {{{value}}}")

        if "sha512sums" in self.variables:
            value = self.variables["sha512sums"]
            assert isinstance(value, str)
            lines.append(f"sha512sums={quoted_string(value)}")

        return "\n".join(lines)

    def save(self, path: str):
        assert isinstance(self.pkgname, str)  # pyright: ignore[reportAny]
        with open(os.path.join(path, "APKBUILD"), "w") as f:
            _ = f.write(self.text + "\n")

        for name, _ in INSTALL_FUNCTION_NAME_MAP.items():
            src = getattr(self, name)  # pyright: ignore[reportAny]

            footer = self._getfooter(self.pkgname, name, self.systemdunits)
            if src is None and footer is None:
                continue

            header = "#!/bin/sh"
            for lifecyclename in sorted(INSTALL_FUNCTION_NAMES):
                if (
                    lifecyclename != name
                    and lifecyclename in (src or "")
                    and getattr(self, lifecyclename) is not None
                ):
                    header += self._lifecycle_header_script(self.pkgname, lifecyclename)

            with open(
                os.path.join(path, f"{self.pkgname}.{INSTALL_FUNCTION_NAME_MAP[name]}"),
                "w",
            ) as f:
                _ = f.write("\n".join([header, src or "", footer or ""]))

        for name, body in super().subpackages.items():
            sub_vars, sub_funcs = bash.parse(body, APKBUILD_AUTOMATIC_VARIABLES)
            systemdunits = [
                x for x in cast(str, sub_vars.get("systemdunits", "")).split() if x
            ]
            for lifecycle_name, lifecycle_file in INSTALL_FUNCTION_NAME_MAP.items():
                footer = self._getfooter(name, lifecycle_name, systemdunits)
                if lifecycle_name not in sub_funcs and footer is None:
                    continue

                src = cleandoc(sub_funcs.get(lifecycle_name, "")) or ""
                header = "#!/bin/sh"
                for lifecyclename in sorted(INSTALL_FUNCTION_NAMES):
                    if (
                        lifecyclename != lifecycle_name
                        and lifecyclename in src
                        and lifecyclename in sub_funcs
                    ):
                        header += self._lifecycle_header_script(name, lifecyclename)

                with open(
                    os.path.join(path, f"{name}.{lifecycle_file}"),
                    "w",
                ) as f:
                    _ = f.write("\n".join([header, src, footer or ""]))

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
            systemdunits = [
                x for x in cast(str, expected_vars.get("systemdunits", "")).split() if x
            ]
            install: list[str] = []
            for lifecycle_name in INSTALL_FUNCTION_NAMES:
                if lifecycle_name in sub_funcs and lifecycle_name != "postosupgrade":
                    install.append(
                        f"{name}.{INSTALL_FUNCTION_NAME_MAP[lifecycle_name]}"
                    )

            if systemdunits:
                for lifecycle_name in ("postinstall", "postupgrade", "predeinstall"):
                    install.append(
                        f"{self.pkgname}.{INSTALL_FUNCTION_NAME_MAP[lifecycle_name]}"  # pyright: ignore[reportAny]
                    )

            if install:
                sub_vars["install"] = f"\n{'\n'.join(sorted(set(install)))}\n"
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

            if "postosupgrade" in sub_funcs or systemdunits:
                fn_name = INSTALL_FUNCTION_NAME_MAP["postosupgrade"]
                subpackages[name] += (
                    f'\n{tab}install -Dm755 "$startdir"/{name}.{fn_name} '
                    + f'"$subpkgdir"/home/root/.vellum/hooks/post-os-upgrade/{name};'
                )

            for unit in systemdunits:
                unit_name = os.path.basename(unit)
                subpackages[name] += (
                    f'\n{tab}install -Dm644 "$srcdir/{unit}" '
                    + f'"$subpkgdir/home/root/.vellum/share/{name}/{unit_name}";'
                )

            subpackages[name] += "\n"

        return subpackages

    @APKBUILD.install.getter
    def install(self) -> str:
        data: list[str] = []
        for name in INSTALL_FUNCTION_NAMES:
            if name in self.functions and name != "postosupgrade":
                data.append(f"{self.pkgname}.{INSTALL_FUNCTION_NAME_MAP[name]}")  # pyright: ignore[reportAny]

        if self.systemdunits:  # pyright: ignore[reportAny]
            for name in ("postinstall", "postupgrade", "predeinstall"):
                data.append(f"{self.pkgname}.{INSTALL_FUNCTION_NAME_MAP[name]}")  # pyright: ignore[reportAny]

        return f"\n{'\n'.join(sorted(set(data)))}\n"

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

    @string_array_property
    def systemdunits(self, value: list[str] | None) -> list[str]:
        return value or []

    def _getsrc(self, name: str) -> str | None:
        src = self.functions.get(name, None)
        if src is None:
            return None

        return cleandoc(src)

    def _getfooter(
        self,
        pkgname: str,
        name: str,
        systemdunits: list[str],
    ) -> str | None:
        if (
            name
            not in (
                "postinstall",
                "postupgrade",
                "postosupgrade",
                "predeinstall",
            )
            or not systemdunits
        ):
            return None

        tab = " " * 4
        lines = [
            'if [ "$SKIP_SYSTEMD_HANDLING" != "1" ]; then',
        ]
        if name != "postosupgrade":
            lines.append(f"{tab}/home/root/.vellum/bin/mount-rw")

        for unit in systemdunits:
            unit_name = os.path.basename(unit)
            if name in ("postinstall", "postupgrade", "postosupgrade"):
                lines.append(
                    f'{tab}cp "$pkgdir"/home/root/.vellum/share/{pkgname}/{unit} /etc/systemd/system/'
                )

            if name == "predeinstall":
                lines.extend(
                    [
                        f"{tab}systemctl disable --now {unit_name}",
                        f"{tab}rm -f /etc/systemd/system/{unit_name}",
                    ]
                )

        lines.append(f"{tab}systemctl daemon-reload")
        for unit in systemdunits:
            unit_name = os.path.basename(unit)
            if name == "postinstall":
                lines.append(f"{tab}systemctl enable --now {unit_name}")

            if name == "postupgrade":
                lines.extend(
                    [
                        f"{tab}if systemctl is-enabled --quiet {unit_name} && systemctl is-active --quiet {unit_name}; then",
                        f"{tab * 2}systemctl try-reload-or-restart {unit_name}",
                        f"{tab}fi",
                    ]
                )

            if name == "postosupgrade":
                lines.append(f"{tab}systemctl enable --now {unit_name}")

        if name != "postosupgrade":
            lines.append(f"{tab}/home/root/.vellum/bin/mount-restore")

        lines.append("fi")
        return "\n".join([*lines])

    def _lifecycle_header_script(self, pkgname: str, name: str) -> str:
        tab = " " * 4
        header = f"\n{name}() {{\n"
        if name == "postosupgrade":
            header += f"{tab}SKIP_SYSTEMD_HANDLING=1 /home/root/.vellum/hooks/post-os-upgrade/{pkgname}"

        else:
            assert isinstance(self.pkgver, str)  # pyright: ignore[reportAny]
            assert isinstance(self.pkgrel, str)  # pyright: ignore[reportAny]
            lifecycle = INSTALL_FUNCTION_NAME_MAP[name]
            header += (
                f"{tab}db=/home/root/.vellum/lib/apk/db/scripts.tar.gz;\n"
                + f"{tab}tar tf $db \\\n"
                + f"{tab}| grep -E '^{pkgname}-{self.pkgver}-r{self.pkgrel}\\..+\\.{lifecycle}$' \\\n"
                + f"{tab}| xargs tar xOf $db \\\n"
                + f"{tab}| SKIP_SYSTEMD_HANDLING=1 bash /dev/stdin"
            )

        return header + ' "$@";\n}'


def parse(path: str) -> VELBUILD:
    with open(path, "r") as f:
        variables, functions = bash.parse(f.read(), APKBUILD_AUTOMATIC_VARIABLES)

    return VELBUILD(variables, functions)
