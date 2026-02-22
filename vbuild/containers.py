import podman
import docker
import json
import os

from contextlib import contextmanager
from collections.abc import Generator
from typing import cast
from typing import Any


def parse_progress(x: dict[str, Any]) -> str:  # pyright: ignore[reportExplicitAny]
    d = x.get("progressDetail", {})  # pyright: ignore[reportAny]
    progress: float | str | None = None
    if "current" in d:
        progress = d["current"] / d.get("total", 3)  # pyright: ignore[reportAny]
        progress = f" {progress:.1%}"

    progress = progress or ""
    status = x.get("status", "")  # pyright: ignore[reportAny]
    identifier: str = x.get("id", "")  # pyright: ignore[reportAny]
    if identifier:
        identifier = " " + identifier

    return f"{status}{identifier}{progress}"


def pull(
    client: podman.PodmanClient | docker.DockerClient, repository: str, tag: str
) -> Generator[str, None, None]:
    if isinstance(client, podman.PodmanClient):
        yield f"Pulling from {repository} {tag}"
        logs = client.images.pull(repository, tag, stream=True)  # pyright: ignore[reportUnknownMemberType]

    else:
        logs = client.api.pull(repository, tag, stream=True, decode=True)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    assert isinstance(logs, Generator), f"Not a generator: {logs}"
    for x in logs:  # pyright: ignore[reportUnknownVariableType]
        yield parse_progress(
            json.loads(x) if isinstance(client, podman.PodmanClient) else x
        )  # pyright: ignore[reportArgumentType, reportUnknownArgumentType]


@contextmanager
def from_env() -> Generator[podman.PodmanClient, None, None]:
    errors: list[Exception] = []
    match os.environ.get("VBUILD_DRIVER", None):
        case "podman":
            drivers = [podman]

        case "docker":
            drivers = [docker]

        case _:
            drivers = [podman, docker]

    for driver in drivers:
        client: podman.PodmanClient | None = None
        try:
            client = cast(podman.PodmanClient, driver.from_env())  # pyright: ignore[reportAny]
            if not client.ping():
                client.close()
                continue

            errors = []

        except Exception as e:
            errors.append(e)
            if client is not None:
                client.close()

            continue

        try:
            yield client
            break

        finally:
            client.close()

    else:
        raise ExceptionGroup("Unable to connect to docker or podman", errors)
