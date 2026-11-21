"""Loads the editable content files in data/ (questions, advice, care plan template, check-ins).

Called by: most of pillway/core and pillway/ai. Files are read once and cached;
call clear_cache() after editing a file while the app runs (tests do this).
"""

import json

from config import get_settings

_cache = {}

FILES = {
    "questions": lambda s: s.safety.questions_file,
    "advice": lambda s: "data/advice.json",
    "care_plan_template": lambda s: "data/care_plan_template.json",
    "check_in_messages": lambda s: s.check_ins.check_in_messages_file,
    "french_strings": lambda s: s.french.french_strings_file,
}


def load(name):
    if name not in _cache:
        settings = get_settings()
        path = settings.path(FILES[name](settings))
        _cache[name] = json.loads(path.read_text(encoding="utf-8"))
    return _cache[name]


def clear_cache():
    _cache.clear()


def advice(key, lang, **values):
    """Fetch an advice sentence like advice('protein.target', 'en', weight=78)."""
    node = load("advice")
    for part in key.split("."):
        node = node[part]
    text = node.get(lang) or node["en"]
    return text.format_map(_KeepMissing(values))


class _KeepMissing(dict):
    """Leaves unknown {placeholders} as they are instead of crashing."""

    def __missing__(self, key):
        return "{" + key + "}"
