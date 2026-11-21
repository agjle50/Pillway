"""Bot settings for one patient (how Sarah responds) and the pharmacist's custom flag words.

Called by: ui/pharmacist/patient_detail.py ("Bot settings" and "Custom flag words" sections).
Toggles are saved to the patient's record and used in Sarah's instructions on the next message.
The question list can be trimmed per patient; deeper customisation is Phase 2.
"""

from tkinter import simpledialog

from ...core.content import load
from ...storage import audit_log
from ..theme import BORDER, INK, TEXT_DARK, TEXT_MUTED, WHITE
from .patient_detail import PHARMACIST

TOGGLES = [("simpler_language", "Simpler language", "Shorter sentences and very common words."),
           ("french_default", "French by default", "Start conversations in French."),
           ("avoid_weight_talk", "Avoid weight talk", "Sarah won't mention weight or BMI (the protein maths still uses weight)."),
           ("ask_feet_every_check_in", "Ask about feet every check-in", "The foot question is always included.")]


class BotSettingsMixin:
    def draw_bot_settings(self, record, x1, y1, x2, y2):
        canvas = self.make_scroll(x1, y1, x2, y2, "#edf1f4")
        width = x2 - x1 - self.S(30)
        y = self.section_title(canvas, 0, self.S(4), "Bot settings for this patient",
                               "How Sarah responds to this patient. Saved immediately; used from the next message.")
        settings = record["bot_settings"]
        for key, label, hint in TOGGLES:
            on = settings.get(key)
            self.btn(canvas, 0, y, ("☑ " if on else "☐ ") + label, lambda k=key: self.toggle_bot_setting(record["id"], k),
                     "dark" if on else "ghost", size=13, min_w=self.S(330))
            self.tx(canvas, self.S(350), y + self.S(19), hint, 12, TEXT_MUTED, anchor="w")
            y += self.S(50)
        y += self.S(10)
        self.tx(canvas, 0, y, "Extra instructions for Sarah (free text)", 14, INK, "bold")
        y += self.S(28)
        item = self.tx(canvas, self.S(14), y + self.S(12), settings.get("instructions") or "(none)", 13, TEXT_DARK,
                       width=width - self.S(180))
        box_bottom = max(self.bottom_of(canvas, item) + self.S(12), y + self.S(46))
        box = self.rr(canvas, 0, y, width - self.S(160), box_bottom, self.S(10), fill=WHITE, outline=BORDER)
        canvas.tag_lower(box)
        self.btn(canvas, width - self.S(150), y + self.S(4), "Edit", lambda: self.edit_bot_instructions(record["id"]), "ghost")
        y = box_bottom + self.S(24)
        self.tx(canvas, 0, y, "Questions Sarah asks this patient (tap to include or skip)", 14, INK, "bold")
        y += self.S(30)
        chosen = settings.get("question_ids")
        for question in load("questions")["questions"]:
            included = chosen is None or question["id"] in chosen
            self.btn(canvas, 0, y, ("☑ " if included else "☐ ") + (question["en"][:66] + ("…" if len(question["en"]) > 66 else "")),
                     lambda q=question["id"]: self.toggle_question(record["id"], q), "dark" if included else "ghost",
                     size=11, height=self.S(34))
            y += self.S(40)
        self.tx(canvas, 0, y + self.S(10), "Phase 2: reorder questions, write new ones, per-patient tone presets.", 11, TEXT_MUTED)
        self.finish_scroll(canvas, y + self.S(60))

    def draw_custom_words(self, record, x1, y1, x2, y2):
        canvas = self.make_scroll(x1, y1, x2, y2, "#edf1f4")
        y = self.section_title(canvas, 0, self.S(4), "Custom flag words",
                               "Extra words to watch for with this patient. A match becomes a WATCH flag (Tier 2).")
        self.btn(canvas, 0, y, "+ Add a word or phrase", lambda: self.add_custom_word(record["id"]), "primary")
        y += self.S(56)
        if not record["custom_flag_words"]:
            self.tx(canvas, 0, y, "No custom words yet. The standard list (data/buzzwords.json) always applies.", 13, TEXT_MUTED)
            y += self.S(30)
        for word in record["custom_flag_words"]:
            right = self.chip(canvas, 0, y + self.S(6), word, INK, WHITE, 12)
            self.btn(canvas, right + self.S(10), y, "Remove", lambda w=word: self.remove_custom_word(record["id"], w),
                     "danger", size=11, height=self.S(32))
            y += self.S(44)
        self.finish_scroll(canvas, y + self.S(40))

    # ---- actions ------------------------------------------------------------------------

    def toggle_bot_setting(self, patient_id, key):
        def change(record):
            record["bot_settings"][key] = not record["bot_settings"].get(key)
            if key == "french_default" and record["bot_settings"][key]:
                record["language"] = "fr"
        self.store.update(patient_id, change)
        audit_log.record("bot_setting_changed", patient_id, by=PHARMACIST, setting=key)
        self.flash("Saved")

    def edit_bot_instructions(self, patient_id):
        current = self.store.load(patient_id)["bot_settings"].get("instructions", "")
        text = simpledialog.askstring("Instructions for Sarah", "Extra instructions:", initialvalue=current, parent=self)
        if text is not None:
            self.store.update(patient_id, lambda r: r["bot_settings"].update(instructions=text.strip()[:500]))
            audit_log.record("bot_instructions_changed", patient_id, by=PHARMACIST)
            self.flash("Saved")

    def toggle_question(self, patient_id, question_id):
        all_ids = [q["id"] for q in load("questions")["questions"]]

        def change(record):
            chosen = record["bot_settings"].get("question_ids") or list(all_ids)
            chosen = [q for q in chosen if q != question_id] if question_id in chosen else chosen + [question_id]
            record["bot_settings"]["question_ids"] = [q for q in all_ids if q in chosen]
        self.store.update(patient_id, change)
        self.flash("Question list saved")

    def add_custom_word(self, patient_id):
        word = simpledialog.askstring("Custom flag word", "Word or phrase to watch for:", parent=self)
        if word and word.strip():
            self.store.update(patient_id, lambda r: r["custom_flag_words"].append(word.strip().lower()))
            audit_log.record("custom_word_added", patient_id, by=PHARMACIST, word=word.strip().lower())
            self.flash("Word added")

    def remove_custom_word(self, patient_id, word):
        self.store.update(patient_id, lambda r: r.update(custom_flag_words=[w for w in r["custom_flag_words"] if w != word]))
        self.flash("Word removed")
