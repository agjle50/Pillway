"""The "Necessary check-in" popup on the patient dashboard.

Called by: ui/patient/dashboard.py (drawn on top of the dashboard).
When: the patient has done the intake questionnaire but not yet the check-in that leads to their
care plan. Clicking "Start check-in" opens the chat, where Sarah speaks first: she says back what
the questionnaire told her, asks if anything has changed, then asks the important questions
(chosen from the questionnaire results) with follow-ups. "Later" hides it until the next sign-in.
"""

from ... import debug_log
from ...core import intake
from ..theme import BORDER, INK, RED, RED_SOFT, RED_TEXT, SHADOW, TEXT_DARK, TEXT_MUTED, WHITE


def check_in_needed(record):
    """Intake done, but the first check-in (and so the care plan) isn't finished yet."""
    if not record or not intake.is_done(record):
        return False
    return record.get("care_plan") is None and record["conversation"]["stage"] != "done"


class CheckInPopupMixin:
    def check_in_popup_should_show(self):
        return (self.role == "patient" and not self.chat_open and not self.call_open
                and not getattr(self, "check_in_popup_dismissed", False)
                and not getattr(self, "intake_open", False)
                and check_in_needed(self.record))

    def draw_check_in_popup(self, px1, py1, px2, py2):
        width, height = min(self.S(560), px2 - px1 - self.S(60)), self.S(300)
        cx, cy = (px1 + px2) / 2, (py1 + py2) / 2
        x1, y1, x2, y2 = cx - width / 2, cy - height / 2, cx + width / 2, cy + height / 2
        # a soft shadow, then the white Pillway card
        self.rrect(x1 + self.S(2), y1 + self.S(6), x2 + self.S(2), y2 + self.S(6), self.S(12), fill=SHADOW,
                   tags="checkin_popup")
        self.rrect(x1, y1, x2, y2, self.S(12), fill=WHITE, outline=BORDER, width=self.S(1.4), tags="checkin_popup")
        pill_w = self.S(190)
        self.rrect(x1 + self.S(28), y1 + self.S(26), x1 + self.S(28) + pill_w, y1 + self.S(56), self.S(15),
                   fill=RED_SOFT, outline=RED_SOFT, tags="checkin_popup")
        self.text(x1 + self.S(28) + pill_w / 2, y1 + self.S(41), "Necessary check-in", 13, RED_TEXT, "bold",
                  anchor="center", tag="checkin_popup")
        self.text(x1 + self.S(28), y1 + self.S(92), "Time for your check-in with Sarah", 22, INK, "bold",
                  tag="checkin_popup")
        self.c.create_text(
            x1 + self.S(28), y1 + self.S(116), anchor="nw", width=width - self.S(56), fill=TEXT_DARK,
            font=self.font(14), tags="checkin_popup",
            text=self.tr("About 5 minutes. Sarah will check what changed since your questionnaire, ask a few "
                         "questions about your health, your goals and your main concerns, then draft your care "
                         "plan for your pharmacist to review."))
        bh, bw = self.S(50), self.S(200)
        by = y2 - self.S(28) - bh
        self.rrect(x2 - self.S(28) - bw, by, x2 - self.S(28), by + bh, self.S(8), fill=RED, outline=RED,
                   tags=("checkin_popup", "checkin_start"))
        self.text(x2 - self.S(28) - bw / 2, by + bh / 2, "Start check-in", 16, WHITE, "bold", anchor="center",
                  tag=("checkin_popup", "checkin_start"))
        self.clickable("checkin_start", self.start_necessary_check_in)
        lx2 = x2 - self.S(28) - bw - self.S(12)
        self.rrect(lx2 - self.S(120), by, lx2, by + bh, self.S(8), fill=WHITE, outline=BORDER, width=self.S(1.4),
                   tags=("checkin_popup", "checkin_later"))
        self.text(lx2 - self.S(60), by + bh / 2, "Later", 16, INK, "bold", anchor="center",
                  tag=("checkin_popup", "checkin_later"))
        self.clickable("checkin_later", self.dismiss_check_in_popup)
        self.text(x1 + self.S(28), by + bh / 2, "Urgent? Call 911.", 12, TEXT_MUTED, tag="checkin_popup")

    def start_necessary_check_in(self):
        debug_log.log("checkin", "patient clicked Start check-in", patient=self.patient_id)
        self.check_in_popup_dismissed = True
        self.open_profile_chat()

    def dismiss_check_in_popup(self):
        debug_log.log("checkin", "check-in popup put off", patient=self.patient_id)
        self.check_in_popup_dismissed = True
        self.render()
