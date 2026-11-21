"""Consent screen shown once before the first chat (PHIPA and AI consent).

Called by: ui/patient/chat.py (and the Call screen) when consent hasn't been given yet.
"Agree" is stored with a timestamp in the patient record; "Not now" keeps the chat closed.
"""

from ..theme import BORDER, INK, RED, TEXT_DARK, TEXT_MUTED, WHITE


class ConsentMixin:
    def draw_consent(self, x1, y1, x2, y2):
        width = min(self.S(640), x2 - x1 - self.S(60))
        cx = (x1 + x2) / 2
        top = y1 + self.S(30)
        bottom = min(y2 - self.S(30), top + self.S(470))
        self.rrect(cx - width / 2, top, cx + width / 2, bottom, self.S(22), fill=WHITE, outline=BORDER, width=self.S(1.4))
        self.text(cx, top + self.S(46), self.t("consent.title"), 26, INK, "bold", anchor="center")
        y = top + self.S(96)
        for key in ("consent.1", "consent.2", "consent.3", "consent.4"):
            self.c.create_oval(cx - width / 2 + self.S(40), y - self.S(6), cx - width / 2 + self.S(52), y + self.S(6),
                               fill=RED, outline="")
            item = self.c.create_text(cx - width / 2 + self.S(70), y, text=self.t(key), fill=TEXT_DARK, anchor="w",
                                      font=self.font(17), width=width - self.S(110))
            y = self.c.bbox(item)[3] + self.S(26)
        if getattr(self, "consent_declined", False):
            self.c.create_text(cx, y, text=self.t("consent.declined"), fill=TEXT_MUTED, font=self.font(13),
                               width=width - self.S(80))
            y += self.S(40)
        button_w, button_h = self.S(200), self.S(56)
        by = bottom - button_h - self.S(30)
        self.rrect(cx + self.S(10), by, cx + self.S(10) + button_w, by + button_h, self.S(14), fill=RED,
                   outline="", tags="consent_yes")
        self.text(cx + self.S(10) + button_w / 2, by + button_h / 2, self.t("consent.agree"), 17, WHITE, "bold",
                  anchor="center", tag="consent_yes")
        self.clickable("consent_yes", lambda: self.give_consent(True))
        self.rrect(cx - self.S(10) - button_w, by, cx - self.S(10), by + button_h, self.S(14), fill=WHITE,
                   outline=BORDER, width=self.S(1.4), tags="consent_no")
        self.text(cx - self.S(10) - button_w / 2, by + button_h / 2, self.t("consent.not_now"), 17, INK, "bold",
                  anchor="center", tag="consent_no")
        self.clickable("consent_no", lambda: self.give_consent(False))

    def give_consent(self, accepted):
        self.consent_declined = not accepted
        if accepted:
            self.service.accept_consent(self.patient_id, True)
            self.chat_focus_requested = True
        self.render()
