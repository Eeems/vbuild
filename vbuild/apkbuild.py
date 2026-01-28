import shlex

from typing import TypeVar
from typing import Callable

from . import bash

F = TypeVar("F", bound=Callable[["APKBUILD", str | None], str | None])


def string_property(func: F) -> property:  # pyright: ignore[reportInvalidTypeVarUse]
    name = func.__name__

    def wrapper(self: "APKBUILD") -> str | None:
        value = self.variables.get(name, None)
        assert value is None or isinstance(value, str)
        return func(self, value)

    return property(wrapper)


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
            lines.append(f"{name}() {{{value}}}")

        return "\n".join(lines)

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
    def upstream_author(self, value: str | None) -> str | None:
        return value

    @string_property
    def category(self, value: str | None) -> str | None:
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
