"""Care plan edit history: who changed which line, when, before and after, with undo.

Called by: core/care_plan.py (record_edit, undo_last) and the pharmacist care plan editor.
"""

from .patient_store import now_iso


def record_edit(record, who, line_id, before, after, action="edit"):
    entry = {"time": now_iso(), "by": who, "line_id": line_id,
             "before": before, "after": after, "action": action, "undone": False}
    record.setdefault("care_plan_history", []).append(entry)
    return entry


def last_undoable(record):
    for entry in reversed(record.get("care_plan_history", [])):
        if entry["action"] == "edit" and not entry["undone"]:
            return entry
    return None
