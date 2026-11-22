"""Check up tab: the two slide-in bars (Call and Chat).

Called by: ui/patient/dashboard.py.
"""

import time

from ..theme import (
    BORDER,
    INK,
    RED,
    SHADOW,
    TEXT_MUTED,
    WHITE,
)


class CheckUpMixin:
    def draw_checkup(self, x1, x2, y):
        self.text((x1 + x2) / 2, y + self.S(14), self.t("checkup.title"), 20, INK,
                  "bold", anchor="center")
        y += self.S(48)
        bars = [("Call", "phone", self.t("checkup.call_sub"), self.t("checkup.call")),
                ("Chat", "chat", self.t("checkup.chat_sub"), self.t("checkup.chat"))]
        bh = self.S(104)
        for i, (title, icon, sub, label) in enumerate(bars):
            off = (1 - self.anim) * self.S(70) * (i + 1)
            by = y + i * (bh + self.S(22)) + off
            tag = "bar::" + "_".join(title.split())
            self.rrect(x1, by + self.S(4), x2, by + bh + self.S(4), self.S(20),
                       fill=SHADOW, outline="", tags=tag)
            self.rrect(x1, by, x2, by + bh, self.S(20), fill=WHITE,
                       outline=BORDER, width=self.S(1.2), tags=tag)
            cx, cy, r = x1 + self.S(56), by + bh / 2, self.S(30)
            self.c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=RED, outline="", tags=tag)
            self.draw_icon(icon, cx, cy, self.S(28), WHITE, tag, bg=RED)
            self.text(x1 + self.S(106), cy - self.S(14), label, 26, INK, "bold", tag=tag)
            self.text(x1 + self.S(106), cy + self.S(20), sub, 14, TEXT_MUTED, tag=tag)
            self.draw_icon("chev_right", x2 - self.S(34), cy, self.S(24), TEXT_MUTED, tag)
            self.clickable(tag, lambda t=title: self.checkup_choice(t))
        if self.status and self.anim >= 1:
            self.text((x1 + x2) / 2, y + 2 * bh + self.S(60),
                      self.status, 14, TEXT_MUTED, anchor="center")

    def checkup_choice(self, kind):
        if kind == "Chat":
            self.open_profile_chat()
            return
        if kind == "Call":
            self._cancel_checkup_animation()
            self._stop_call_input()
            self.call_state = {}          # the call screen sets itself up on first draw
            self.call_open = True
            self.chat_open = False
            self.status = ""
            self.render()
            return
        self.status = "Opening a chat with your care assistant..."
        self.render()

    def _cancel_checkup_animation(self):
        if self._checkup_animation_job:
            self.after_cancel(self._checkup_animation_job)
            self._checkup_animation_job = None
        self._checkup_animation_started = None
        self.anim = 1.0

    def _animate(self):
        self._checkup_animation_job = None
        if (
            self._checkup_animation_started is None
            or self.tab != "Check up"
            or self.section != "Dashboard"
            or self.chat_open
            or self.call_open
        ):
            self._checkup_animation_started = None
            self.anim = 1.0
            return
        previous = self.anim
        elapsed = time.monotonic() - self._checkup_animation_started
        progress = min(1.0, elapsed / 0.36)
        self.anim = 1 - (1 - progress) ** 3
        delta = self.anim - previous
        for index, title in enumerate(("Call", "Chat")):
            self.c.move("bar::" + "_".join(title.split()), 0, -delta * self.S(70) * (index + 1))
        if progress < 1.0:
            self._checkup_animation_job = self.after(16, self._animate)
        else:
            self.anim = 1.0
            self._checkup_animation_started = None
