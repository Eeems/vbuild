import os
from collections.abc import (
    Callable,
    Generator,
)
from inspect import cleandoc
from typing import (
    cast,
    override,
)
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import (
    HTTPErrorProcessor,
    Request,
    build_opener,
)

from . import (
    bash,
    containers,
)
from .apkbuild import (
    APKBUILD,
    APKBUILD_AUTOMATIC_VARIABLES,
    APKBUILD_VARIABLES,
    ErrorType,
    Property,
    is_type,
    put_variables,
    quoted_string,
    typed_property,
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
VELBUILD_VARIABLE_MAP = {
    "upstream_author": "_upstream_author",
    "category": "_category",
    "readmeurl": "_readmeurl",
    "donateurl": "_donateurl",
    "changelogurl": "_changelogurl",
    "status": "_status",
    "systemdunits": "_systemdunits",
}

INSTALL_FUNCTION_NAMES = set(INSTALL_FUNCTION_NAME_MAP.keys())


class NonRaisingHTTPErrorProcessor(HTTPErrorProcessor):
    http_response = https_response = lambda self, request, response: response  # pyright: ignore[reportUnannotatedClassAttribute]


class URLValidationError(Exception):
    pass


def string_array_property_always(
    func: Callable[..., list[str]],
) -> Property[list[str]]:
    name = func.__name__

    def fget(self: "APKBUILD") -> list[str]:
        value = self.variables.get(name, None)
        assert is_type(value, str | None), f"Cannot get {name}, value is not valid"
        if value is None:
            return func(self, [])

        assert isinstance(value, str)
        return func(self, value.split())

    def fset(self: "APKBUILD", value: list[str]) -> None:
        assert is_type(value, list[str]), f"Cannot set {name}, value is not valid"
        self.variables[name] = f"\n{'\n'.join(value)}\n"

    def fdel(self: "APKBUILD") -> None:
        del self.variables[name]

    return Property[list[str]](fget, fset, fdel, func.__doc__)


class VELBUILD(APKBUILD):
    @APKBUILD.text.getter
    def text(self) -> str:
        lines: list[str] = []
        variables = self.variables.copy()
        for name, value in variables.items():
            if (
                value is None
                or name in bash.DEFAULT_VARIABLE_NAMES
                or name in ("sha512sums", "triggers")
            ):
                continue

            if (
                name in APKBUILD_AUTOMATIC_VARIABLES
                and value == APKBUILD_AUTOMATIC_VARIABLES[name]
            ):
                continue

            if name in VELBUILD_VARIABLE_MAP:
                name = VELBUILD_VARIABLE_MAP[name]  # noqa: PLW2901

            if name in ("systemdunits", "image", "options"):
                continue

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

        options = set(self.options)
        if self.image is not None:
            options |= {"!strip"}

        lines.append(f"options={quoted_string(f'\n{"\n".join(sorted(options))}\n')}")
        if self.install.strip():
            lines.append(f"install={quoted_string(self.install)}")

        triggers: list[str] = []
        if self.triggers:
            triggers.append(f"{self.pkgname}.trigger={':'.join(self.triggers)}")

        subpackage_map = self._subpackages
        for sub_name, sub_func_name in subpackage_map.items():
            sub_vars, sub_funcs = bash.parse(
                self.functions[sub_func_name], APKBUILD_AUTOMATIC_VARIABLES
            )
            if "trigger" not in sub_funcs or "triggers" not in sub_vars:
                continue

            triggers.append(
                f"{sub_name}.trigger={':'.join(x for x in cast(str, sub_vars['triggers']).split() if x)}"
            )

        if triggers:
            lines.append(f"triggers={quoted_string(f'\n{"\n".join(triggers)}\n')}")

        functions = self.functions.copy()
        if "package" not in functions:
            functions["package"] = "\n"

        runtime = containers.runtime()
        assert runtime is not None
        match runtime:
            case "podman":
                runtime += " --remote"

            case "docker":
                pass

        tab = " " * 4
        subpackage_functions = subpackage_map.values()
        for name, value in functions.items():
            if (
                name in INSTALL_FUNCTION_NAMES
                or name in subpackage_functions
                or name == "trigger"
            ):
                continue

            if name == "image":
                continue

            elif name == "build" and self.image is not None:
                keys = sorted(
                    set(APKBUILD_VARIABLES + list(variables.keys()))
                    - bash.DEFAULT_VARIABLE_NAMES
                )
                value = (  # noqa: PLW2901
                    f"\n{tab}set -e\n"
                    + f"{tab}image() {{{self.image}{tab}}}\n"
                    + f"{tab}image=$(image)\n"
                    + f"{tab}unset -f image\n"
                    + f"{tab}set +e\n"
                    + (
                        f" \\\n{tab}".join(
                            f'{tab}{x}="${VELBUILD_VARIABLE_MAP.get(x, x)}"'
                            for x in keys
                        )
                    )
                    + " \\\n"
                    + f"{tab * 2}{runtime} run \\\n"
                    + f"{tab * 2}--rm \\\n"
                    + f"{tab * 2}--volume=$VBUILD_WORKDIR:/work \\\n"
                    + f"{tab * 2}--volume=$VBUILD_DISTFILES:/var/cache/distfiles:ro \\\n"
                    + (" \\\n".join(f"{tab * 2}-e {x}" for x in keys))
                    + " \\\n"
                    + f'{tab * 2}--workdir "$builddir" \\\n'
                    + f"{tab * 2}$image \\\n"
                    + f"{tab * 2}sh $startdir/$pkgname.build\n"
                    + f"{tab}_ret=$?\n"
                    + f"{tab}if [ $_ret -ne 0 ];then\n"
                    + f"{tab}{tab}exit $_ret\n"
                    + f"{tab}fi\n"
                )

            elif name == "package":
                if self.postosupgrade is not None or self.systemdunits:
                    fn_name = INSTALL_FUNCTION_NAME_MAP["postosupgrade"]
                    value += f'{tab}install -Dm755 "$startdir"/"$pkgname".{fn_name} '  # noqa: PLW2901
                    value += (  # noqa: PLW2901
                        '"$pkgdir"/home/root/.vellum/hooks/post-os-upgrade/"$pkgname";\n'
                    )

                for unit in self.systemdunits:
                    unit_name = os.path.basename(unit)
                    value += f'{tab}install -Dm644 "$srcdir/{unit}" "$pkgdir/home/root/.vellum/share/{self.pkgname}/{unit_name}";\n'  # noqa: PLW2901

            lines.append(f"{name}() {{{value}}}")

        for name, value in self.subpackages.items():
            lines.append(f"{subpackage_map[name]}() {{{value}}}")

        if "sha512sums" in variables:
            value = variables["sha512sums"]
            assert isinstance(value, str)
            lines.append(f"sha512sums={quoted_string(value)}")

        return "\n".join(lines)

    def save(self, path: str) -> None:
        assert isinstance(self.pkgname, str)
        with open(os.path.join(path, "APKBUILD"), "w") as f:
            _ = f.write(self.text + "\n")

        for name, functionName in INSTALL_FUNCTION_NAME_MAP.items():
            src = getattr(self, name)  # pyright: ignore[reportAny]

            footer = self._getfooter(self.pkgname, name, self.systemdunits)
            if src is None and footer is None:
                continue

            header = "#!/bin/sh"
            for lifecyclename in sorted(self._lifecycle_references(name, src)):
                header += self._lifecycle_header_script(
                    self.pkgname,
                    lifecyclename,
                )

            with open(
                os.path.join(path, f"{self.pkgname}.{functionName}"),
                "w",
            ) as f:
                _ = f.write(
                    "\n".join(
                        [
                            header,
                            f'{name}() {{\n{src}\n}}\n{name} "$@"' if src else "",
                            footer or "",
                        ]
                    )
                )

        if self.trigger is not None:
            with open(
                os.path.join(path, f"{self.pkgname}.trigger"),
                "w",
            ) as f:
                _ = f.write("#!/bin/sh\n" + self.trigger)

        if self.image is not None:
            src = self.functions.get("build", None)
            if src is not None:
                script = f'#!/bin/sh\nbuild() {{\n{src}\n}}\nbuild "$@"'
                if "!strip" not in self.options:
                    script += (
                        "\n_build_ret=$?\n"
                        + "set +e\n"
                        + 'if [ "$CARCH" = "noarch" ]; then\n'
                        + "    exit $_build_ret\n"
                        + "fi\n"
                        + "STRIP=${STRIP:-${CROSS_COMPILE}strip}\n"
                        + "OBJDUMP=${OBJDUMP:-${CROSS_COMPILE}objdump}\n"
                        + 'echo "Stripping with strip=$STRIP and objdump=$OBJDUMP"\n'
                        + 'formats=$("$STRIP" --info |\n'
                        + "    sed -n 's/^\\([a-z0-9][a-z0-9._-]*\\)$/\\1/p' |\n"
                        + "    grep '^elf' |\n"
                        + "    tr '\\n' ' ')\n"
                        + 'echo "Allowed formats: $formats"\n'
                        + "export OBJDUMP formats\n"
                        + 'output=$(find "$srcdir" -type f -print0 |\n'
                        + "    xargs -0 -r sh -c '\n"
                        + "    for f do\n"
                        + '      fmt=$("$OBJDUMP" -f "$f" 2>/dev/null |\n'
                        + '        sed -n "s/.*file format \\([a-z0-9][a-z0-9._-]*\\).*/\\1/p" |\n'
                        + "        head -1)\n"
                        + '      [ -n "$fmt" ] || continue\n'
                        + '      case " $formats " in\n'
                        + '        *" $fmt "*)\n'
                        + '          printf "%s\\0" "$f"\n'
                        + "          ;;\n"
                        + "      esac\n"
                        + "    done\n"
                        + "  ' sh |\n"
                        + '    xargs -0 -r "$STRIP" --strip-unneeded 2>&1)\n'
                        + "_strip_ret=$?\n"
                        + 'if [ -n "$output" ]; then\n'
                        + '    output=$(printf "%s\\n" "$output" |\n'
                        + '        grep -v -e "Unable to recognise the format of the input file" -e "file format not recognized" -e "plugin needed to handle")\n'
                        + '    if [ -n "$output" ]; then\n'
                        + '        printf "%s\\n" "$output" >&2\n'
                        + "        exit $_strip_ret\n"
                        + "    fi\n"
                        + "fi\n"
                        + "exit $_build_ret\n"
                    )

                with open(os.path.join(path, f"{self.pkgname}.build"), "w") as f:
                    _ = f.write(script)

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
                for lifecyclename in sorted(
                    self._lifecycle_references(
                        lifecycle_name,
                        src,
                        lookup=lambda fn, s=sub_funcs: s.get(fn),
                    )
                ):
                    header += self._lifecycle_header_script(
                        name,
                        lifecyclename,
                        src=sub_funcs.get(lifecyclename),
                    )

                with open(
                    os.path.join(path, f"{name}.{lifecycle_file}"),
                    "w",
                ) as f:
                    _ = f.write(
                        "\n".join(
                            [
                                header,
                                f'{lifecycle_name}() {{\n{src}\n}}\n{lifecycle_name} "$@"',
                                footer or "",
                            ]
                        )
                    )

            if "trigger" in sub_funcs:
                with open(
                    os.path.join(path, f"{name}.trigger"),
                    "w",
                ) as f:
                    _ = f.write("#!/bin/sh\n" + cleandoc(sub_funcs["trigger"]))

    def _validate_url(self, url: str | None) -> None:
        if url is None:
            return

        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise URLValidationError(f"Unsupported URL schema: {parsed.scheme}")

        with build_opener(NonRaisingHTTPErrorProcessor).open(
            Request(  # noqa: S310
                url,
                method="HEAD",
                headers={"User-Agent": "vbuild"},
            ),
            timeout=10,
        ) as res:  # pyright: ignore[reportAny]
            if res.status >= 300 and res.status != 403:  # pyright: ignore[reportAny]
                raise URLValidationError(f"Unexpected response code: {res.status}")  # pyright: ignore[reportAny]

    @override
    def validate(self) -> Generator[tuple[ErrorType, str]]:
        if "image" in self.variables and "image" in self.functions:
            yield ErrorType.Error, "image set as both variable and function"

        if "package" not in self.functions:
            yield ErrorType.Error, "package function is not defined"

        if self.upstream_author is None:
            yield ErrorType.Error, "upstream_author is not set"

        if self.category is None:
            yield ErrorType.Error, "category is not set"

        try:
            self._validate_url(self.readmeurl)

        except (URLValidationError, URLError) as e:
            yield ErrorType.Error, f"readmeurl is not valid: {e}"

        try:
            self._validate_url(self.donateurl)

        except (URLValidationError, URLError) as e:
            yield ErrorType.Error, f"donateurl is not valid: {e}"

        try:
            self._validate_url(self.changelogurl)

        except (URLValidationError, URLError) as e:
            yield ErrorType.Error, f"changelogurl is not valid: {e}"

        try:
            self._validate_url(self.url)

        except (URLValidationError, URLError) as e:
            yield ErrorType.Error, f"url is not valid: {e}"

        if self.status not in (None, "maintained", "unmaintained", "deprecated"):
            yield (
                ErrorType.Error,
                "status is not valid, must be 'maintained', 'unmaintained', or 'deprecated'",
            )

        pkgdesc_len = len(self.pkgdesc or "")
        if pkgdesc_len >= 128:
            yield (
                ErrorType.Error,
                f"pkgdesc is too long ({pkgdesc_len} chars, must be <128)",
            )

        if not self.variables.get("maintainer"):
            yield ErrorType.Error, "maintainer is not set"

        if self.sha256sums is not None:
            yield ErrorType.Error, "sha256sums is not supported by vbuild"

        if self.trigger is not None and not self.triggers:
            yield (
                ErrorType.Error,
                "trigger function defined but triggers variable not set",
            )
        elif self.trigger is None and self.triggers:
            yield (
                ErrorType.Error,
                "triggers variable set but trigger function not defined",
            )

        for name, body in super().subpackages.items():
            sub_vars, sub_funcs = bash.parse(body, APKBUILD_AUTOMATIC_VARIABLES)
            if "package" not in sub_funcs:
                yield (
                    ErrorType.Error,
                    f"subpackage {name}: package function is not defined",
                )

            triggers = sub_vars.get("triggers")
            if isinstance(triggers, str) and bool(triggers.split()):
                if "trigger" not in sub_funcs:
                    yield (
                        ErrorType.Error,
                        f"subpackage {name}: triggers variable set but trigger function not defined",
                    )

            elif "trigger" in sub_funcs:
                yield (
                    ErrorType.Error,
                    f"subpackage {name}: trigger function defined but triggers variable not set",
                )

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
                        f"{name}.{INSTALL_FUNCTION_NAME_MAP[lifecycle_name]}"
                    )

            if install:
                sub_vars["install"] = f"\n{'\n'.join(sorted(set(install)))}\n"
                expected_vars["install"] = ""

            subpackages[name] = ""

            for var_name in expected_vars:
                if (
                    var_name in bash.DEFAULT_VARIABLE_NAMES
                    or var_name in APKBUILD_AUTOMATIC_VARIABLES
                    or var_name == "triggers"
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

    @property
    @override
    def install(self) -> str:
        data: list[str] = []
        for name in INSTALL_FUNCTION_NAMES:
            if name in self.functions and name != "postosupgrade":
                data.append(f"{self.pkgname}.{INSTALL_FUNCTION_NAME_MAP[name]}")

        if self.systemdunits:
            for name in ("postinstall", "postupgrade", "predeinstall"):
                data.append(f"{self.pkgname}.{INSTALL_FUNCTION_NAME_MAP[name]}")

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

    @property
    def trigger(self) -> str | None:
        return self._getsrc("trigger")

    @typed_property
    def category(self, value: str | None) -> str | None:
        return value

    @typed_property
    def readmeurl(self, value: str | None) -> str | None:
        return value

    @typed_property
    def donateurl(self, value: str | None) -> str | None:
        return value

    @typed_property
    def changelogurl(self, value: str | None) -> str | None:
        return value

    @typed_property
    def status(self, value: str | None) -> str | None:
        return value

    @typed_property
    def upstream_author(self, value: str | None) -> str | None:
        return value

    @string_array_property_always
    def systemdunits(self, value: list[str]) -> list[str]:
        return value

    @property
    def image(self) -> str | None:
        value = self.functions.get("image", None)
        if value is not None:
            return value

        value = self.variables.get("image", None)
        assert value is None or isinstance(value, str), f"{value} is not str | None"
        if value is not None:
            return f"\n    echo {quoted_string(value)}\n"

        return None

    @string_array_property_always
    @override
    def options(self, value: list[str]) -> list[str]:
        options = list(
            {
                *value,
                *{"!check", "!fhs", "!strip", "!tracedeps"},
            }
        )

        def handle_option(option: str) -> None:
            nonlocal options
            if option not in options:
                return

            options.remove(option)
            option = f"!{option}"
            if option in options:
                options.remove(option)

        handle_option("check")
        handle_option("fhs")
        handle_option("strip")
        handle_option("tracedeps")
        options.sort()
        return options

    @image.setter
    def image(self, value: str | None) -> None:
        assert value is None or isinstance(value, str)
        self.variables["image"] = value
        if "image" in self.functions:
            del self.functions["image"]

    @image.deleter
    def image(self) -> None:
        if "image" in self.variables:
            del self.variables["image"]

        if "image" in self.functions:
            del self.functions["image"]

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
                    f"{tab}cp /home/root/.vellum/share/{pkgname}/{unit_name} /etc/systemd/system/"
                )

            if name == "predeinstall":
                if "@." in unit_name:
                    lines.append(f"{tab}systemctl disable {unit_name}")

                else:
                    lines.append(f"{tab}systemctl disable --now {unit_name}")

                lines.append(f"{tab}rm -f /etc/systemd/system/{unit_name}")

        lines.append(f"{tab}systemctl daemon-reload")
        for unit in systemdunits:
            unit_name = os.path.basename(unit)
            if "@." in unit_name:
                continue

            if name == "postinstall":
                lines.append(f"{tab}systemctl enable --now {unit_name}")

            if name == "postupgrade":
                lines.append(f"{tab}systemctl try-reload-or-restart {unit_name}")

            if name == "postosupgrade":
                lines.append(f"{tab}systemctl enable --now {unit_name}")

        if name != "postosupgrade":
            lines.append(f"{tab}/home/root/.vellum/bin/mount-restore")

        lines.append("fi")
        return "\n".join(lines)

    def _lifecycle_header_script(
        self,
        pkgname: str,
        name: str,
        src: str | None = None,
    ) -> str:
        tab = " " * 4
        if src is None:
            src = getattr(self, name) or ""

        header = f"\n{name}() {{\n{tab}_SKIP_SYSTEMD_HANDLING=${{SKIP_SYSTEMD_HANDLING:-0}}\n{tab}export SKIP_SYSTEMD_HANDLING=1\n"
        if name == "postosupgrade":
            header += f"{tab}SKIP_SYSTEMD_HANDLING=1 /home/root/.vellum/hooks/post-os-upgrade/{pkgname}"
            header += ' "$@";\n'

        elif src:
            body = cleandoc(src)
            if body:
                for line in body.split("\n"):
                    header += f"{line}\n"

        return (
            header + f"{tab}export SKIP_SYSTEMD_HANDLING=$_SKIP_SYSTEMD_HANDLING;\n}}"
        )

    def _lifecycle_references(
        self,
        name: str,
        src: str | None = None,
        lookup: Callable[[str], str | None] | None = None,
    ) -> set[str]:
        if lookup is None:
            lookup = lambda fn: getattr(self, fn) or ""

        if src is None:
            src = lookup(name)

        assert isinstance(src, str)
        referenced: set[str] = set()
        pending: set[str] = {
            fn for fn in INSTALL_FUNCTION_NAMES if fn != name and fn in src
        }
        while pending:
            fn = pending.pop()
            if fn in referenced:
                continue

            referenced.add(fn)
            fn_src = lookup(fn)
            if not fn_src:
                continue

            for other in INSTALL_FUNCTION_NAMES:
                if (
                    other not in (fn, name)
                    and other not in referenced
                    and other in fn_src
                ):
                    pending.add(other)

        return referenced


def parse(path: str) -> VELBUILD:
    with open(path) as f:
        variables, functions = bash.parse(f.read(), APKBUILD_AUTOMATIC_VARIABLES)

    return VELBUILD(variables, functions)
