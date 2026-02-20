import podman
import docker

from contextlib import contextmanager
from collections.abc import Generator
from typing import cast


@contextmanager
def from_env() -> Generator[podman.PodmanClient, None, None]:
    errors:list[Exception] = []
    for engine in [podman, docker]:
        client: podman.PodmanClient | None = None
        try:
            client = cast(podman.PodmanClient, engine.from_env())  # pyright: ignore[reportAny]
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
