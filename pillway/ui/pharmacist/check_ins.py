"""Check-ins: status, missed days, the weekly summary, and this patient's editable check-in message.

Called by: ui/pharmacist/patient_detail.py ("Check-ins" section).
One topic per week, like Pillway's follow-up calls (Fibre week, Foot-care week...).
"""

from tkinter import simpledialog

from config import get_settings

from ...core import check_ins
from ...core.content import load
from ...storage import audit_log
from ..theme import AMBER, BORDER, GREEN, INK, TEXT_DARK, TEXT_MUTED, WHITE
from .patient_detail import PHARMACIST


class CheckInsMixin:
    def draw_check_ins_section(self, record, x1, y1, x2, y2):
        canvas = self.make_scroll(x1, y1, x2, y2, "#edf1f4")
        width = x2 - x1 - self.S(30)
        y = self.section_title(canvas, 0, self.S(4), "Check-ins",
                               "Daily reminders and a weekly summary. Reminders are never about medication.")
        days = check_ins.days_since_check_in(record)
        missed = check_ins.missed_check_ins(record)
        rows = [("Status", check_ins.status(record), GREEN),
                ("Last check-in", "never" if days is None else f"{days} day(s) ago", AMBER if missed else TEXT_DARK),
                ("Missed check-ins", f"yes (more than {get_settings().safety.missed_check_in_days} days)" if missed else "no",
                 AMBER if missed else TEXT_DARK),
                ("Topic this week", check_ins.topic_for(record)["en"], INK),
                ("Daily reminder time", get_settings().check_ins.daily_check_in_time, TEXT_DARK),
                ("Reminders allowed by patient", "yes" if record["reminders_consent"]["accepted"] else "not yet (CASL)", TEXT_DARK),
                ("Weekly summary", check_ins.weekly_summary(record, "en"), TEXT_DARK)]
        top = y
        for label, value, colour in rows:
            self.tx(canvas, self.S(18), y + self.S(14), label, 12, TEXT_MUTED, "bold")
            item = self.tx(canvas, self.S(260), y + self.S(14), value, 13, colour, "bold", width=width - self.S(290))
            y = max(self.bottom_of(canvas, item), y + self.S(30)) + self.S(6)
        box = self.rr(canvas, 0, top, width, y + self.S(10), self.S(12), fill=WHITE, outline=BORDER)
        canvas.tag_lower(box)
        y += self.S(30)
        self.tx(canvas, 0, y, "Today's check-in message (English / French)", 14, INK, "bold")
        y += self.S(30)
        for lang in ("en", "fr"):
            item = self.tx(canvas, self.S(18), y, check_ins.daily_message(record, lang), 13, TEXT_DARK, width=width - self.S(200))
            self.btn(canvas, width - self.S(160), y - self.S(4), f"Edit {lang.upper()}",
                     lambda lg=lang: self.edit_check_in_message(record["id"], lg), "ghost", size=11, height=self.S(32))
            y = max(self.bottom_of(canvas, item), y + self.S(34)) + self.S(12)
        topics = ", ".join(topic["en"] for topic in load("check_in_messages")["weekly_topics"])
        self.tx(canvas, 0, y + self.S(10), f"Weekly topics available: {topics}. Step and watch data: Phase 2.", 11, TEXT_MUTED,
                width=width)
        self.finish_scroll(canvas, y + self.S(60))

    def edit_check_in_message(self, patient_id, lang):
        current = check_ins.daily_message(self.store.load(patient_id), lang)
        text = simpledialog.askstring("Check-in message", "Message for this patient:", initialvalue=current, parent=self)
        if text and text.strip():
            self.store.update(patient_id, lambda r: r["check_in_messages"].update({f"daily_{lang}": text.strip()}))
            audit_log.record("check_in_message_edited", patient_id, by=PHARMACIST, lang=lang)
            self.flash("Check-in message saved")
