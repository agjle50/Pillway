"""Remembers small UI preferences between sessions (pharmacist filter, sort, compact view, language).

Called by: pharmacist dashboard and the language toggle.
"""

from config import get_settings

from .json_store import read_json, update_json
from .paths import data_folder


def _path():
    return data_folder() / "app_state.json"


def defaults():
    pharmacist = get_settings().pharmacist
    return {"filter": pharmacist.default_filter, "sort": pharmacist.default_sort,
            "view": pharmacist.default_view}


def load():
    state = defaults()
    state.update(read_json(_path(), {}) or {})
    return state


def save(**changes):
    def apply(data):
        data.update(changes)
    return update_json(_path(), apply, {})
