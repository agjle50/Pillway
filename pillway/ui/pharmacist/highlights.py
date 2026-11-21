"""Possible issues: every "you may have…, because…" statement Sarah made, with her reasoning.

Called by: ui/pharmacist/patient_detail.py ("Possible issues" section).
Kept separate from the chat log so the pharmacist can review them in one place.
"""

from ..theme import AMBER, BORDER, INK, TEXT_DARK, TEXT_MUTED, WHITE


class HighlightsMixin:
    def draw_highlights_section(self, record, x1, y1, x2, y2):
        canvas = self.make_scroll(x1, y1, x2, y2, "#edf1f4")
        width = x2 - x1 - self.S(30)
        y = self.section_title(canvas, 0, self.S(4), "Possible issues",
                               "Every \"you may have…, because…\" statement Sarah made. Sarah never diagnoses; you decide.")
        issues = list(reversed(record.get("possible_issues", [])))
        if not issues:
            self.tx(canvas, 0, y, "Sarah hasn't raised any possible issues for this patient.", 14, TEXT_MUTED)
            y += self.S(40)
        messages = {m["id"]: m for m in record["messages"]}
        for issue in issues:
            top = y
            self.chip(canvas, self.S(18), y + self.S(14), "AI DRAFT · possible issue", AMBER, "#fff4e5", 10)
            self.tx(canvas, width - self.S(16), y + self.S(16), issue["time"][:16].replace("T", " "), 11, TEXT_MUTED, anchor="ne")
            item = self.tx(canvas, self.S(18), y + self.S(48), f"May have: {issue['issue']}", 16, INK, "bold", width=width - self.S(36))
            y = self.bottom_of(canvas, item) + self.S(6)
            item = self.tx(canvas, self.S(18), y, f"Because: {issue['reason']}", 13, TEXT_DARK, width=width - self.S(36))
            y = self.bottom_of(canvas, item) + self.S(6)
            source = messages.get(issue.get("message_id"))
            if source:
                item = self.tx(canvas, self.S(18), y, f"Patient said: “{source['text']}”", 12, TEXT_MUTED, width=width - self.S(36))
                y = self.bottom_of(canvas, item) + self.S(6)
            y += self.S(10)
            box = self.rr(canvas, 0, top, width, y, self.S(12), fill=WHITE, outline=BORDER)
            canvas.tag_lower(box)
            y += self.S(12)
        self.finish_scroll(canvas, y + self.S(20))
