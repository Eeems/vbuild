import os
import shlex
import subprocess
import sys
from collections.abc import (
    Generator,
    Iterator,
)
from hashlib import sha256
from typing import (
    Any,
    cast,
)

from . import containers

KEY_NAME = os.environ.get("VBUILD_KEY_NAME", "vbuild")

SETUP_CONTAINER = [
    f"cp /root/.abuild/{KEY_NAME}.rsa.pub /etc/apk/keys/",
    'mkdir -p /dist/"$CARCH" /work/src',
]
TEARDOWN_CONTAINER_DOCKER: list[str] = [
    f"chown -R {os.getuid()}:{os.getgid()} /dist/.",
]
TEARDOWN_CONTAINER_PODMAN: list[str] = []

has_pulled = False


def abuild(
    directory: str,
    action: str = "all",
) -> int:
    directory = os.path.abspath(directory)
    distfiles = os.path.join(
        os.path.expanduser("~/.cache/vbuild/distfiles"),
        sha256(directory.encode()).hexdigest(),
    )
    os.makedirs(distfiles, exist_ok=True)
    filepath = os.path.join(directory, "APKBUILD")
    if not os.path.exists(filepath):
        raise FileNotFoundError(filepath)

    abuilddir = os.path.expanduser("~/.config/vbuild")
    key_path = os.path.join(abuilddir, f"{KEY_NAME}.rsa")
    os.makedirs(abuilddir, exist_ok=True)
    if not os.path.exists(key_path):
        _ = subprocess.check_call(["openssl", "genrsa", "-out", key_path])
        _ = subprocess.check_call(
            ["openssl", "rsa", "-in", key_path, "-pubout", "-out", f"{key_path}.pub"]
        )
        os.chmod(key_path, 0o600)

    conf_path = os.path.join(abuilddir, "abuild.conf")
    lines: list[str] = [f"PACKAGER_PRIVKEY=/root/.abuild/{KEY_NAME}.rsa\n"]
    if os.path.exists(conf_path):
        with open(conf_path) as f:
            for line in f.readlines():
                if not line.startswith("PACKAGER_PRIVKEY="):
                    lines.append(line)

    with open(conf_path, "w") as f:
        _ = f.truncate()
        f.writelines(lines)

    with containers.from_env() as client:
        runtime = containers.runtime()
        assert runtime is not None
        print(f"Container driver: {runtime}", file=sys.stderr)

        global has_pulled
        if not has_pulled:
            logs = containers.pull(client, "ghcr.io/eeems/vbuild-builder", "main")
            for x in logs:
                if isinstance(x, bytes):
                    x = x.decode()  # noqa: PLW2901

                x = x.strip()  # noqa: PLW2901
                if x:
                    print(x, file=sys.stderr)

            has_pulled = True

        distdir = os.path.realpath(
            os.environ.get("REPODEST", None) or os.path.join(directory, "dist")
        )
        os.makedirs(distdir, exist_ok=True)
        os.makedirs(os.path.join(directory, "src"), exist_ok=True)
        run_kwargs: dict[str, Any] = {  # pyright: ignore[reportExplicitAny]
            "detach": True,
            "volumes": {
                distdir: {"bind": "/dist", "mode": "rw"},
                distfiles: {"bind": "/var/cache/distfiles", "mode": "rw"},
                abuilddir: {"bind": "/root/.abuild", "mode": "ro"},
            },
            "environment": {
                "CARCH": os.environ.get("CARCH", "noarch"),
                "SOURCE_DATE_EPOCH": os.environ.get("SOURCE_DATE_EPOCH", "0"),
                "REPODEST": "/dist",
            },
        }
        teardown = []
        match runtime:
            case "podman":
                run_kwargs["volumes"][directory] = {"bind": "/work", "mode": "Z"}
                socket_uri = cast(str, client.info()["host"]["remoteSocket"]["path"])  # pyright: ignore[reportUnknownMemberType]
                print(f"Socket: {socket_uri}")
                socket = socket_uri.split("://", 1)[1]
                run_kwargs["volumes"][socket] = {
                    "bind": "/run/podman/podman.sock",
                    "mode": "rw",
                }
                teardown = TEARDOWN_CONTAINER_PODMAN

            case "docker":
                run_kwargs["volumes"][directory] = {"bind": "/work", "mode": "Z"}
                run_kwargs["volumes"]["/var/run/docker.sock"] = {
                    "bind": "/var/run/docker.sock",
                    "mode": "rw",
                }
                teardown = TEARDOWN_CONTAINER_DOCKER

        container = client.containers.run(  # pyright: ignore[reportUnknownMemberType]
            "ghcr.io/eeems/vbuild-builder:main",
            [
                "sh",
                "-ec",
                "\n".join(
                    [
                        *SETUP_CONTAINER,
                        f"abuild -C /work -d -F -r {shlex.quote(action)}",
                        *teardown,
                    ]
                ),
            ],
            **run_kwargs,  # pyright: ignore[reportAny]
        )
        assert not isinstance(container, Generator)
        assert not isinstance(container, Iterator)
        try:
            logs = container.logs(stream=True)  # pyright: ignore[reportUnknownMemberType]
            for x in logs:
                if isinstance(x, bytes):
                    x = x.decode()  # noqa: PLW2901

                assert isinstance(x, str)
                x = x.strip()  # noqa: PLW2901
                if x:
                    print(x, file=sys.stderr)

            ret = container.wait()  # pyright: ignore[reportUnknownMemberType]
            if isinstance(ret, dict):
                ret = ret.get("StatusCode")  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

            assert isinstance(ret, int)
            return ret

        finally:
            if container.status == "running":  # pyright: ignore[reportUnknownMemberType]
                try:
                    container.stop()  # pyright: ignore[reportUnknownMemberType]

                except Exception:  # noqa: S110
                    pass

            container.remove()  # pyright: ignore[reportUnknownMemberType]
