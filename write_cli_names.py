import json

from vbuild.cli import commands

with open("vbuild/cli/__names__.py", "w") as f:
    _ = f.write("names = ")
    json.dump(list(commands.keys()), f)
