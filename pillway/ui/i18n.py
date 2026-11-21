"""English/French labels for the patient screens. Use self.t("tab.tasks") in any screen.

Called by: patient screens. Strings live in data/french_strings.json (never in code).
"""

from ..core.content import load


def translate(key, lang):
    entry = load("french_strings")["strings"].get(key)
    if not entry:
        return key
    return entry.get(lang) or entry["en"]


class I18nMixin:
    def t(self, key):
        return translate(key, getattr(self, "lang", "en"))
