"""Append-only audit log: every flag decision and every pharmacist action, one JSON line each.

Called by: core/flagging.py (flag decisions), pharmacist actions (resolve, approve, edits).
Why: this is our responsible-AI proof. Nothing here is ever edited or deleted by the app.
The log never contains names or contact details, only the patient id.
"""

import json
from datetime import datetime

from .file_lock import FileLock
from .paths import data_folder


def log_path():
    return data_folder() / "audit_log.jsonl"


def record(event, patient_id, **details):
    entry = {"time": datetime.now().astimezone().isoformat(timespec="seconds"),
             "event": event, "patient_id": patient_id, **details}
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(path):
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def read(patient_id=None, limit=500):
    try:
        lines = log_path().read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    entries = [json.loads(line) for line in lines if line.strip()]
    if patient_id:
        entries = [entry for entry in entries if entry.get("patient_id") == patient_id]
    return entries[-limit:]
