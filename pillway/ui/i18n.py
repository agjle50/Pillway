"""English/French labels for the patient screens. Use self.t("tab.tasks") in any screen.

Called by: patient screens. Strings live in data/french_strings.json (never in code).
"""

from ..core.content import load


def translate(key, lang):
    entry = load("french_strings")["strings"].get(key)
    if not entry:
        return key
    return entry.get(lang) or entry["en"]


_FRENCH_UI = None


def french_ui():
    """English -> French for every label on the patient screens (data/french_ui.json)."""
    global _FRENCH_UI
    if _FRENCH_UI is None:
        import json
        from pathlib import Path
        path = Path(__file__).resolve().parents[2] / "data" / "french_ui.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        _FRENCH_UI = {"exact": data.get("exact", {}), "prefixes": data.get("prefixes", {})}
    return _FRENCH_UI


def to_french(text):
    if not isinstance(text, str) or not text.strip():
        return text
    table = french_ui()
    if text in table["exact"]:
        return table["exact"][text]
    stripped = text.strip()
    if stripped in table["exact"]:
        return text.replace(stripped, table["exact"][stripped])
    for english, french in table["prefixes"].items():  # e.g. "Urgent: numb feet"
        if text.startswith(english):
            return french + to_french(text[len(english):])
    return text


class I18nMixin:
    def t(self, key):
        text = translate(key, getattr(self, "lang", "en"))
        return self.tr(text) if text == key else text

    def translate_screen(self, widget=None):
        """After a redraw in French: translate any text that was drawn without self.tr()."""
        import tkinter as tk
        widget = widget or self
        for child in widget.winfo_children():
            try:
                if isinstance(child, tk.Canvas):
                    for item in child.find_all():
                        if child.type(item) == "text":
                            text = child.itemcget(item, "text")
                            french = to_french(text)
                            if french != text:
                                child.itemconfigure(item, text=french)
                elif isinstance(child, (tk.Label, tk.Button, tk.Checkbutton, tk.Radiobutton)):
                    text = child.cget("text")
                    french = to_french(text)
                    if french != text:
                        child.configure(text=french)
            except Exception:
                pass
            self.translate_screen(child)

    def tr(self, text):
        """Translate any on-screen English text when the patient has chosen French.

        Every text drawing helper calls this, so the whole patient side switches language.
        The pharmacist side stays in English (the toggle belongs to the patient).
        """
        if getattr(self, "lang", "en") != "fr" or getattr(self, "role", None) == "pharmacist":
            return text
        return to_french(text)
