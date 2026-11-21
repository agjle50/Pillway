"""A tiny cross-platform file lock, so two Pillway windows never write the same file at once.

Called by: storage/json_store.py.
How: create "<file>.lock" exclusively; other writers wait. A lock older than a few
seconds is treated as left over from a crash and removed.
"""

import os
import time
from pathlib import Path

STALE_AFTER_SECONDS = 5.0


class FileLock:
    def __init__(self, path, timeout=5.0):
        self.lock_path = Path(str(path) + ".lock")
        self.timeout = timeout
        self._fd = None

    def __enter__(self):
        deadline = time.monotonic() + self.timeout
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                self._fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                return self
            except FileExistsError:
                self._remove_if_stale()
                if time.monotonic() > deadline:
                    raise TimeoutError(f"Another Pillway window is busy saving {self.lock_path.stem}. Try again.")
                time.sleep(0.02)

    def _remove_if_stale(self):
        try:
            if time.time() - self.lock_path.stat().st_mtime > STALE_AFTER_SECONDS:
                self.lock_path.unlink()
        except FileNotFoundError:
            pass

    def __exit__(self, *_):
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
        try:
            self.lock_path.unlink()
        except FileNotFoundError:
            pass
