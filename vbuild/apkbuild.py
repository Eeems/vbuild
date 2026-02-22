import shlex
import string

from enum import Enum
from typing import Callable
from collections.abc import Generator

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


def string_property(func: Callable[..., str | None]) -> property:
    name = func.__name__

    def wrapper(self: "APKBUILD") -> str | None:
        value = self.variables.get(name, None)
        assert value is None or isinstance(value, str)
        return func(self, value)

    return property(wrapper)


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
            if not in_quote:
                in_quote = True
                quoted_value += "'"

            if token == "'":
                token = "\\'"

            quoted_value += token
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


class APKBUILD:
    def __init__(self, variables: bash.Variables, functions: bash.Functions) -> None:
        self.variables: bash.Variables = variables
        self.functions: bash.Functions = functions

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

        for name, value in self.functions.items():
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

    @string_property
    def arch(self, value: str | None) -> str | None:
        return value

    @string_property
    def depends(self, value: str | None) -> str | None:
        return value

    @string_property
    def depends_dev(self, value: str | None) -> str | None:
        return value

    @string_property
    def depends_doc(self, value: str | None) -> str | None:
        return value

    @string_property
    def depends_openrc(self, value: str | None) -> str | None:
        return value

    @string_property
    def depends_libs(self, value: str | None) -> str | None:
        return value

    @string_property
    def depends_static(self, value: str | None) -> str | None:
        return value

    @string_property
    def checkdepends(self, value: str | None) -> str | None:
        return value

    @string_property
    def giturl(self, value: str | None) -> str | None:
        return value

    @string_property
    def install(self, value: str | None) -> str | None:
        return value

    @string_property
    def install_if(self, value: str | None) -> str | None:
        return value

    @string_property
    def license(self, value: str | None) -> str | None:
        return value

    @string_property
    def makedepends(self, value: str | None) -> str | None:
        return value

    @string_property
    def makedepends_build(self, value: str | None) -> str | None:
        return value

    @string_property
    def makedepends_host(self, value: str | None) -> str | None:
        return value

    @string_property
    def sha256sums(self, value: str | None) -> str | None:
        return value

    @string_property
    def sha512sums(self, value: str | None) -> str | None:
        return value

    @string_property
    def options(self, value: str | None) -> str | None:
        return value

    @string_property
    def pkgdesc(self, value: str | None) -> str | None:
        return value

    @string_property
    def pkggroups(self, value: str | None) -> str | None:
        return value

    @string_property
    def pkgname(self, value: str | None) -> str | None:
        return value

    @string_property
    def pkgrel(self, value: str | None) -> str | None:
        return value

    @string_property
    def pkgusers(self, value: str | None) -> str | None:
        return value

    @string_property
    def pkgver(self, value: str | None) -> str | None:
        return value

    @string_property
    def provides(self, value: str | None) -> str | None:
        return value

    @string_property
    def provider_priority(self, value: str | None) -> str | None:
        return value

    @string_property
    def replaces(self, value: str | None) -> str | None:
        return value

    @string_property
    def replaces_priority(self, value: str | None) -> str | None:
        return value

    @string_property
    def source(self, value: str | None) -> str | None:
        return value

    @string_property
    def subpackages(self, value: str | None) -> str | None:
        return value

    @string_property
    def triggers(self, value: str | None) -> str | None:
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
