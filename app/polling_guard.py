from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import fcntl


class PollingAlreadyRunningError(RuntimeError):
    """Raised when another polling process already holds the runtime lock."""


@contextmanager
def hold_polling_lock(lock_path: str) -> Iterator[None]:
    path = Path(lock_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise PollingAlreadyRunningError(
                f"another polling process is already running (lock: {path})"
            ) from exc

        handle.seek(0)
        handle.truncate()
        handle.write(f"{os.getpid()}\n")
        handle.flush()

        try:
            yield
        finally:
            handle.seek(0)
            handle.truncate()
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
