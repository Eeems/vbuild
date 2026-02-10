import os
import sys
import subprocess

from collections.abc import Generator
from collections.abc import Iterator

from . import containers

SETUP_CONTAINER = [
    "set -e",
    "apk add --no-cache alpine-sdk",
    "if [ -d /work-src ];then",
    "  cp -r /work-src/packages /work/",
    "  cp -r /work-src/keys /work/",
    "fi",
    'mkdir -p /work/dist/"$CARCH"',
    "cp /root/.abuild/vbuild.rsa.pub /etc/apk/keys/",
]


def abuild(
    directory: str,
    action: str = "all",
) -> int:
    directory = os.path.abspath(directory)
    distfiles = os.path.join(directory, ".distfiles")
    os.makedirs(distfiles, exist_ok=True)
    filepath = os.path.join(directory, "APKBUILD")
    if not os.path.exists(filepath):
        raise FileNotFoundError(filepath)

    abuilddir = os.path.expanduser("~/.config/vbuild")
    key_path = os.path.join(abuilddir, "vbuild.rsa")
    os.makedirs(abuilddir, exist_ok=True)
    if not os.path.exists(key_path):
        _ = subprocess.check_call(["openssl", "genrsa", "-out", key_path])
        _ = subprocess.check_call(
            ["openssl", "rsa", "-in", key_path, "-pubout", "-out", f"{key_path}.pub"]
        )
        os.chmod(key_path, 0o600)

    conf_path = os.path.join(abuilddir, "abuild.conf")
    if not os.path.exists(conf_path):
        with open(conf_path, "w") as f:
            _ = f.write("PACKAGER_PRIVKEY=/root/.abuild/vbuild.rsa")

    with containers.from_env() as client:
        container = client.containers.run(  # pyright: ignore[reportUnknownMemberType]
            "alpine:3",
            [
                "sh",
                "-c",
                "\n".join(
                    SETUP_CONTAINER
                    + [
                        f"REPODEST=/work/dist abuild -C /work -d -r -F {action}",
                    ]
                ),
            ],
            detach=True,
            remove=True,
            volumes={
                directory: {"bind": "/work"},
                distfiles: {"bind": "/var/cache/distfiles"},
                abuilddir: {"bind": "/root/.abuild"},
            },
            environment={
                "CARCH": os.environ.get("CARCH", "noarch"),
                "SOURCE_DATE_EPOCH": "0",
            },
        )
        assert not isinstance(container, Generator)
        assert not isinstance(container, Iterator)
        logs = container.logs(stream=True)  # pyright: ignore[reportUnknownMemberType]
        assert isinstance(logs, Generator)
        for x in logs:
            print(x.decode(), file=sys.stderr, end="")

        return container.wait()  # pyright: ignore[reportUnknownMemberType]
