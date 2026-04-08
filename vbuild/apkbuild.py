import shlex
import string
from collections.abc import (
    Callable,
    Generator,
)
from enum import Enum

from . import bash

APKBUILD_AUTOMATIC_VARIABLES = {
    "builddir": "$builddir",
    "pkgdir": "$pkgdir",
    "srcdir": "$srcdir",
    "startdir": "$startdir",
    "subpkgdir": "$subpkgdir",
}


class ErrorType(Enum):
    Error = 1
    Warning = 2

    @staticmethod
    def string(type: "ErrorType") -> str:
        return str(type)[10:]


class StringProperty(property):
    pass


class StringArrayProperty(property):
    pass


def string_property(func: Callable[..., str | None]) -> property:
    name = func.__name__

    def fget(self: "APKBUILD") -> str | None:
        value = self.variables.get(name, None)
        assert value is None or isinstance(value, str)
        return func(self, value)

    def fset(self: "APKBUILD", value: str | None) -> None:
        assert value is None or isinstance(value, str)
        self.variables[name] = value

    def fdel(self: "APKBUILD") -> None:
        del self.variables[name]

    return StringProperty(fget, fset, fdel, func.__doc__)


def string_array_property(func: Callable[..., list[str] | None]) -> property:
    name = func.__name__

    def fget(self: "APKBUILD") -> list[str] | None:
        value = self.variables.get(name, None)
        assert value is None or isinstance(value, str)
        return func(self, None) if value is None else func(self, value.split())

    def fset(self: "APKBUILD", value: list[str] | None):
        assert value is None or (
            isinstance(value, list)
            and (not value or not [x for x in value if not isinstance(x, str)])
        )
        self.variables[name] = None if value is None else f"\n{'\n'.join(value)}\n"

    def fdel(self: "APKBUILD") -> None:
        del self.variables[name]

    return StringArrayProperty(fget, fset, fdel, func.__doc__)


def get_token(value: str, offset: int) -> tuple[int, str]:
    size = len(value)
    if offset >= size:
        return (offset, "")

    token = value[offset]
    token_chars = string.ascii_letters + string.digits + "-_"
    if token not in token_chars:
        offset += 1
        return offset, token

    while True:
        offset += 1
        if offset >= size:
            break

        next_char = value[offset]

        if next_char not in token_chars:
            break

        token += next_char

    return offset, token


def quoted_string(value: str) -> str:
    offset = 0
    quoted_value = ""
    in_quote = False
    size = len(value)
    while True:
        if offset >= size:
            if in_quote:
                quoted_value += "'"

            break

        token = value[offset]
        offset += 1

        if token != "$":
            if token != "'":
                if not in_quote:
                    in_quote = True
                    quoted_value += "'"

                quoted_value += token
                continue

            if in_quote:
                quoted_value += "'"

            quoted_value += '"\'"'
            if in_quote:
                quoted_value += "'"

            continue

        offset, name = get_token(value, offset)
        source = "$" + name
        if name == "{":
            offset, name = get_token(value, offset)
            source += name
            offset, next_token = get_token(value, offset)
            source += next_token
            if next_token != "}" and offset < size:
                raise bash.BashSyntaxError(
                    f"Unexpected token: '{next_token}'. Expecting '}}'", value, 1
                )

        if name not in APKBUILD_AUTOMATIC_VARIABLES.keys():
            if not in_quote:
                in_quote = True
                quoted_value += "'"

            quoted_value += shlex.quote(source)[1:-1]
            continue

        if in_quote:
            in_quote = False
            quoted_value += "'"

        quoted_value += f"${name}"

    return quoted_value


def put_variables(variables: bash.Variables) -> str:
    lines: list[str] = []
    for name, value in variables.items():
        if name in bash.DEFAULT_VARIABLE_NAMES:
            continue

        if value is None:
            lines.append(f"declare -- {name}\n")

        elif isinstance(value, str):
            lines.append(f"declare -- {name}={quoted_string(value)}\n")

        elif isinstance(value, list):
            lines.append(f"{name}=(")
            for x in value:
                if x is not None:
                    lines.append(f"  {quoted_string(x)}")

            lines.append(")")

        elif isinstance(value, dict):  # pyright: ignore[reportUnnecessaryIsInstance]
            lines.append(f"declare -A {name}=(")
            for k, v in value.items():
                lines.append(f"  [{k}]={quoted_string(v)}")

            lines.append(")")

        else:
            raise ValueError(f"Unsupported type {type(value)} for variable \n{name}")

    return "\n".join(lines)


class APKBUILD:
    def __init__(self, variables: bash.Variables, functions: bash.Functions) -> None:
        self.variables: bash.Variables = variables
        self.functions: bash.Functions = functions
        for name in variables.keys():
            prop = getattr(APKBUILD, name, None)
            if not isinstance(prop, property) or prop.fset is None or prop.fget is None:
                continue

            if isinstance(prop, StringProperty) or isinstance(
                prop, StringArrayProperty
            ):
                prop.fset(self, prop.fget(self))

    @property
    def text(self) -> str:
        lines: list[str] = []

        for name, value in self.variables.items():
            if value is None or name in bash.DEFAULT_VARIABLE_NAMES:
                continue

            if (
                name in APKBUILD_AUTOMATIC_VARIABLES.keys()
                and value == APKBUILD_AUTOMATIC_VARIABLES[name]
            ):
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

        subpackages = self.subpackages
        for name, value in self.functions.items():
            if name not in subpackages.values():
                lines.append(f"{name}() {{{value}}}")

        for name, value in subpackages.items():
            lines.append(f"{name}() {{{value}}}")

        return "\n".join(lines)

    def validate(self) -> Generator[tuple[ErrorType, str]]:
        if self._upstream_author is None:  # pyright: ignore[reportAny]
            yield ErrorType.Error, "_upstream_author is not set"

        if self._category is None:  # pyright: ignore[reportAny]
            yield ErrorType.Error, "_category is not set"

        pkgdesc_len = len(self.pkgdesc)  # pyright: ignore[reportAny]
        if pkgdesc_len >= 128:
            yield (
                ErrorType.Error,
                f"pkgdesc is too long ({pkgdesc_len} chars, must be <128)",
            )

        if self.maintainer is None:  # pyright: ignore[reportAny]
            yield ErrorType.Error, "maintainer is not set"

    @string_property
    def maintainer(self, value: str | None) -> str:
        assert value is not None
        return value

    @string_array_property
    def arch(self, value: list[str] | None) -> list[str] | None:
        return value

    @string_array_property
    def depends(self, value: list[str] | None) -> list[str] | None:
        return value

    @string_array_property
    def depends_dev(self, value: list[str] | None) -> list[str] | None:
        return value

    @string_array_property
    def depends_doc(self, value: list[str] | None) -> list[str] | None:
        return value

    @string_array_property
    def depends_openrc(self, value: list[str] | None) -> list[str] | None:
        return value

    @string_array_property
    def depends_libs(self, value: list[str] | None) -> list[str] | None:
        return value

    @string_array_property
    def depends_static(self, value: list[str] | None) -> list[str] | None:
        return value

    @string_array_property
    def checkdepends(self, value: list[str] | None) -> list[str] | None:
        return value

    @string_property
    def giturl(self, value: str | None) -> str | None:
        return value

    @string_array_property
    def install(self, value: list[str] | None) -> list[str] | None:
        return value

    @string_array_property
    def install_if(self, value: list[str] | None) -> list[str] | None:
        return value

    @string_property
    def license(self, value: str | None) -> str | None:
        return value

    @string_array_property
    def makedepends(self, value: list[str] | None) -> list[str] | None:
        return value

    @string_array_property
    def makedepends_build(self, value: list[str] | None) -> list[str] | None:
        return value

    @string_array_property
    def makedepends_host(self, value: list[str] | None) -> list[str] | None:
        return value

    @string_array_property
    def sha256sums(self, value: list[str] | None) -> list[str] | None:
        return value

    @string_array_property
    def sha512sums(self, value: list[str] | None) -> list[str] | None:
        return value

    @string_array_property
    def options(self, value: list[str] | None) -> list[str] | None:
        return value

    @string_property
    def pkgdesc(self, value: str | None) -> str | None:
        return value

    @string_array_property
    def pkggroups(self, value: list[str] | None) -> list[str] | None:
        return value

    @string_property
    def pkgname(self, value: str | None) -> str | None:
        return value

    @string_property
    def pkgrel(self, value: str | None) -> str | None:
        return value

    @string_array_property
    def pkgusers(self, value: list[str] | None) -> list[str] | None:
        return value

    @string_property
    def pkgver(self, value: str | None) -> str | None:
        return value

    @string_array_property
    def provides(self, value: list[str] | None) -> list[str] | None:
        return value

    @string_property
    def provider_priority(self, value: str | None) -> str | None:
        return value

    @string_array_property
    def replaces(self, value: list[str] | None) -> list[str] | None:
        return value

    @string_array_property
    def replaces_priority(self, value: list[str] | None) -> list[str] | None:
        return value

    @string_array_property
    def source(self, value: list[str] | None) -> list[str] | None:
        return value

    @property
    def subpackages(self) -> dict[str, str]:
        value = self.variables.get("subpackages", None)
        assert value is None or isinstance(value, str)
        if value is None:
            return {}

        subpackages: dict[str, str] = {}
        for spec in value.split():
            parts = spec.split(":", 1)
            if len(parts) == 1:
                parts[1] = parts[0]

            name, fn = parts
            subpackages[name] = self.functions[fn]

        return subpackages

    @string_array_property
    def triggers(self, value: list[str] | None) -> list[str] | None:
        return value

    @string_property
    def url(self, value: str | None) -> str | None:
        return value

    @string_property
    def langdir(self, value: str | None) -> str | None:
        return value

    @string_property
    def pcprefix(self, value: str | None) -> str | None:
        return value

    @string_property
    def _upstream_author(self, value: str | None) -> str | None:
        return value

    @string_property
    def _category(self, value: str | None) -> str | None:
        return value

    @string_property
    def sonameprefix(self, value: str | None) -> str | None:
        return value

    @property
    def fetch(self) -> str | None:
        return self.functions.get("fetch", None)

    @property
    def unpack(self) -> str | None:
        return self.functions.get("unpack", None)

    @property
    def dev(self) -> str | None:
        return self.functions.get("dev", None)

    @property
    def doc(self) -> str | None:
        return self.functions.get("doc", None)

    @property
    def openrc(self) -> str | None:
        return self.functions.get("openrc", None)

    @property
    def static(self) -> str | None:
        return self.functions.get("static", None)

    @property
    def snapshot(self) -> str | None:
        return self.functions.get("snapshot", None)

    @property
    def default_prepare(self) -> str | None:
        return self.functions.get("default_prepare", None)

    @property
    def prepare(self) -> str | None:
        return self.functions.get("prepare", None)

    @property
    def build(self) -> str | None:
        return self.functions.get("build", None)

    @property
    def check(self) -> str | None:
        return self.functions.get("check", None)

    @property
    def package(self) -> str:
        return self.functions["package"]


def parse(path: str) -> APKBUILD:
    with open(path, "r") as f:
        variables, functions = bash.parse(f.read())

    return APKBUILD(variables, functions)
