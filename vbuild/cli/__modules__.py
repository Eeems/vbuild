import os
import argparse
import importlib
from glob import glob
from typing import Callable
from types import ModuleType

CommandCallable = Callable[[argparse.Namespace], int]
modules: dict[str, ModuleType] = {}
commands: dict[str, CommandCallable] = {}

names: list[str] = []
if "__compiled__" in globals():
    from .__names__ import names

else:
    __dirname__ = os.path.dirname(__file__)
    modulename = os.path.basename(os.path.dirname(__dirname__))
    for file in sorted(glob(os.path.join(__dirname__, "*.py"))):
        if os.path.basename(file).startswith("__") or file.endswith("__.py"):
            continue

        names.append(os.path.splitext(os.path.basename(file))[0])


for name in names:
    module = importlib.import_module(f"vbuild.cli.{name}", "vbuild")
    modules[name] = module
    assert hasattr(module, "register"), f"Missing register method: {name}"
    assert hasattr(module, "command"), f"Missing command method: {name}"
    commands[name] = module.command  # pyright: ignore[reportAny]
