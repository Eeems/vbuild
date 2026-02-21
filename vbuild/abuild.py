import os
import sys
import shlex
import subprocess

from collections.abc import Generator
from collections.abc import Iterator

from . import containers

SETUP_CONTAINER = [
    "set -e",
    'mkdir -p /work/dist/"$CARCH"',
    "ls -l /root/.abuild/",
    "cp /root/.abuild/vbuild.rsa.pub /etc/apk/keys/",
]

has_pulled = False

def abuild(
    directory: str,
    action: str = "all",
) -> int:
    directory = os.path.abspath(directory)
    distfiles = os.path.expanduser("~/.cache/vbuild/distfiles")
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
        global has_pulled
        if not has_pulled:
            logs = containers.pull(client, "ghcr.io/eeems/vbuild-builder", "main")
            for x in logs:
                if isinstance(x, bytes):
                    x = x.decode()

                x = x.strip()
                if x:
                    print(x, file=sys.stderr)

            has_pulled = True

        container = client.containers.run(  # pyright: ignore[reportUnknownMemberType]
            "ghcr.io/eeems/vbuild-builder:main",
            [
                "sh",
                "-c",
                "\n".join(
                    SETUP_CONTAINER
                    + [
                        shlex.join(
                            [
                                "abuild",
                                "-C",
                                "/work",
                                "-d",
                                "-r",
                                "-F",
                                action,
                            ]
                        ),
                    ]
                ),
            ],
            detach=True,
            volumes={
                directory: {"bind": "/work"},
                distfiles: {"bind": "/var/cache/distfiles"},
                abuilddir: {"bind": "/root/.abuild"},
            },
            environment={
                "CARCH": os.environ.get("CARCH", "noarch"),
                "SOURCE_DATE_EPOCH": "0",
                "REPODEST": "/work/dist",
            },
        )
        assert not isinstance(container, Generator)
        assert not isinstance(container, Iterator)
        try:
            logs = container.logs(stream=True)  # pyright: ignore[reportUnknownMemberType]
            for x in logs:
                if isinstance(x, bytes):
                    x = x.decode()

                assert isinstance(x, str)
                x = x.strip()
                if x:
                    print(x, file=sys.stderr)

            return container.wait()  # pyright: ignore[reportUnknownMemberType]

        finally:
            if container.status == "running":  # pyright: ignore[reportUnknownMemberType]
                try:
                    container.stop()  # pyright: ignore[reportUnknownMemberType]

                except Exception:
                    pass

            container.remove()  # pyright: ignore[reportUnknownMemberType]
