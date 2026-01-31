import podman
import docker

from contextlib import contextmanager
from collections.abc import Generator
from typing import cast


@contextmanager
def from_env() -> Generator[podman.PodmanClient, None, None]:
    for engine in [podman, docker]:
        client = cast(podman.PodmanClient, engine.from_env())  # pyright: ignore[reportAny]
        if not client.ping():
            client.close()
            continue

        try:
            yield client
            break
        finally:
            client.close()

    else:
        raise Exception("Unable to connect to docker or podman")
