import podman
import docker

from contextlib import contextmanager
from typing import ContextManager
from typing import cast


@contextmanager
def client() -> ContextManager[podman.PodmanClient]:
    for engine in [podman, docker]:
        client = engine.from_env()  # pyright: ignore[reportAny]
        if not client.ping():  # pyright: ignore[reportAny]
            client.close()  # pyright: ignore[reportAny]
            continue

        try:
            yield cast(podman.PodmanClient, client)
            return
        finally:
            client.close()  # pyright: ignore[reportAny]

    raise Exception("Unable to connect to docker or podman")
