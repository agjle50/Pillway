"""Safe JSON file reading and writing (atomic save + lock), shared by every store.

Called by: storage/patient_store.py, storage/app_state.py.
Why: data must never disappear. We write to a temporary file and then swap it in,
so a crash mid-save can never leave a half-written file.
"""

import json
import os
from pathlib import Path

from .file_lock import FileLock


def read_json(path, default=None):
    path = Path(path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as error:
        backup = path.with_suffix(path.suffix + ".broken")
        path.replace(backup)
        raise ValueError(f"{path.name} was damaged; it was moved to {backup.name}.") from error


def write_json(path, data):
    """Atomic write: temp file then replace. Caller should hold the lock."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=1)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def update_json(path, change, default):
    """Lock, re-read the latest version from disk, apply change(data), save. Returns the new data."""
    with FileLock(path):
        data = read_json(path, default)
        result = change(data)
        if result is not None:
            data = result
        write_json(path, data)
        return data


def modified_time(path):
    try:
        return Path(path).stat().st_mtime_ns
    except FileNotFoundError:
        return 0
