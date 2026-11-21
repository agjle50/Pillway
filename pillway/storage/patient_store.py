"""The ONE source of truth for each patient: profile, messages, flags, care plan, tasks, settings.

Called by: the chat flow (core/conversation_service.py), pharmacist screens and tests.
Each patient is one JSON file in <data folder>/patients/. Every change goes through
update(), which locks the file, re-reads the latest version from disk, applies the
change and saves. So a patient window and a pharmacist window (even two separate
processes) always see the same status, within about a second.
"""

import copy
import json
import uuid
from datetime import datetime

from config import get_settings

from .json_store import modified_time, read_json, update_json
from .paths import data_folder

RECORD_VERSION = 1


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def new_id(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def blank_record(patient_id, seed=None):
    """A fresh patient record. `seed` comes from data/seed_patients.json."""
    seed = copy.deepcopy(seed or {})
    language_default = get_settings().patient.default_language
    profile = seed.get("profile", {"first_name": patient_id.title(), "last_name": "", "conditions": []})
    return {
        "id": patient_id, "version": RECORD_VERSION,
        "profile": profile,
        "medications": seed.get("medications", []),
        "language": profile.get("language", language_default),
        "consent": {"accepted": False, "time": None},
        "reminders_consent": {"accepted": get_settings().check_ins.reminders_opt_in_default, "time": None},
        "summary_updates": [],
        "conversation": {"stage": "consent", "question_index": 0, "answers": {}, "asked": [],
                         "pending_flag_followup": None, "session_id": None},
        "messages": [], "sessions": [], "flags": [], "possible_issues": [],
        "pharmacist_requests": [], "care_plan": None, "care_plan_history": [],
        "tasks": [], "check_ins": seed.get("check_ins", {"last_check_in": None, "watching": True}),
        "bot_settings": {"simpler_language": False, "french_default": False, "avoid_weight_talk": False,
                         "ask_feet_every_check_in": True, "instructions": "", "question_ids": None},
        "custom_flag_words": [], "check_in_messages": {},
        "last_patient_activity": None, "created": now_iso(),
    }


class PatientStore:
    def __init__(self, folder=None):
        self.folder = (folder or data_folder()) / "patients"
        self.folder.mkdir(parents=True, exist_ok=True)
        self._seeds = None

    # ---- seeds ---------------------------------------------------------

    def seeds(self):
        if self._seeds is None:
            path = get_settings().path(get_settings().demo.seed_patients_file)
            self._seeds = json.loads(path.read_text(encoding="utf-8"))["patients"]
        return self._seeds

    def path(self, patient_id):
        safe = "".join(ch for ch in patient_id if ch.isalnum() or ch in "-_")
        return self.folder / f"{safe}.json"

    # ---- reading -------------------------------------------------------

    def load(self, patient_id):
        """Return the record, creating it from the seed file the first time."""
        record = read_json(self.path(patient_id))
        if record is None:
            record = self.update(patient_id, lambda data: data)
        return record

    def ids(self):
        visible = list(get_settings().demo.visible_patients)
        on_disk = sorted(path.stem for path in self.folder.glob("*.json"))
        extra = [pid for pid in on_disk if pid not in visible and pid not in self.seeds()]
        return visible + extra

    def all(self):
        return [self.load(pid) for pid in self.ids()]

    def stamp(self):
        """Changes whenever any patient file changes (used to refresh other windows)."""
        return tuple(modified_time(self.path(pid)) for pid in self.ids())

    # ---- writing -------------------------------------------------------

    def update(self, patient_id, change):
        """Apply change(record) safely. change may edit in place or return a new record."""
        default = blank_record(patient_id, self.seeds().get(patient_id))
        return update_json(self.path(patient_id), change, default)

    def reset(self, patient_id):
        """Restore one patient to a fresh seeded state (used by 'Reset demo')."""
        fresh = blank_record(patient_id, self.seeds().get(patient_id))
        return update_json(self.path(patient_id), lambda _old: fresh, fresh)

    def reset_demo(self):
        for patient_id in set(self.ids()) | set(self.seeds()):
            if patient_id in self.seeds():
                self.reset(patient_id)


def display_name(record):
    profile = record.get("profile", {})
    return f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip() or record["id"]


def initials(record):
    profile = record.get("profile", {})
    return ((profile.get("first_name") or "?")[:1] + (profile.get("last_name") or "")[:1]).upper()
