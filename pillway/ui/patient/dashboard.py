"""The patient dashboard panel with the top icon tab bar (Check up, Medications, Orders, Tasks).

Called by: PillwayApp.render() for the Dashboard section.
"""

import time

from ..theme import (
    BORDER,
    NAVY_DARK,
    RED,
    TEXT_MUTED,
    WHITE,
)
from ..navigation import TABS
from ..sample_content import BANNER_TEXT as VIRTUAL_ASSISTANT_POPUP_TEXT


class PatientDashboardMixin:
    def panel_box(self):
        return (self.sw + self.S(14), self.S(92), self.w - self.S(14), self.h - self.S(14))
    def draw_dashboard(self):
        px1, py1, px2, py2 = self.panel_box()
        self.rrect(px1, py1, px2, py2, self.S(16), fill=WHITE, outline=BORDER, width=self.S(1.2))
        if self.call_open:
            self.draw_call_preview(px1, py1, px2, py2)
            return
        if self.chat_open:
            self.draw_chat_page(px1, py1, px2, py2)
            return
        if self.prescription_flow:
            self.draw_prescription_page(px1, py1, px2, py2)
            return
        pcx = (px1 + px2) / 2

        gap = self.S(150)
        for i, (name, icon) in enumerate(TABS):
            x = pcx + (i - (len(TABS) - 1) / 2) * gap
            tag = f"tab::{name}"
            sel = name == self.tab
            col = RED if sel else TEXT_MUTED
            self.c.create_rectangle(x - gap / 2 + self.S(6), py1 + self.S(8), x + gap / 2 - self.S(6),
                                    py1 + self.S(96), fill=WHITE, outline=WHITE, tags=tag)
            self.draw_icon(icon, x, py1 + self.S(40), self.S(32), col, tag)
            self.text(x, py1 + self.S(76), name, 14, col, "bold" if sel else "normal",
                      anchor="center", tag=tag)
            if sel:
                self.rrect(x - self.S(26), py1 + self.S(92), x + self.S(26), py1 + self.S(96),
                           self.S(2), fill=RED, outline="", tags=tag)
            self.clickable(tag, lambda n=name: self.select_tab(n))
        self.c.create_line(px1, py1 + self.S(98), px2, py1 + self.S(98), fill=BORDER)

        y = py1 + self.S(118)
        if self.banner and self.tab != "Medications":
            bw = min(self.S(700), px2 - px1 - self.S(60))
            bx1, bx2 = pcx - bw / 2, pcx + bw / 2
            self.rrect(bx1, y, bx2, y + self.S(56), self.S(14), fill=NAVY_DARK, outline="")
            self.text(bx1 + self.S(22), y + self.S(28), VIRTUAL_ASSISTANT_POPUP_TEXT, 14, WHITE)
            self.c.create_oval(bx2 - self.S(36), y + self.S(14), bx2 - self.S(8), y + self.S(42),
                               fill=NAVY_DARK, outline="", tags="banner_x")
            self.draw_icon("close", bx2 - self.S(22), y + self.S(28), self.S(16), WHITE, "banner_x")
            self.clickable("banner_x", self.close_banner)
            y += self.S(80)
        else:
            y += self.S(10)

        content_w = min(self.S(820), px2 - px1 - self.S(80))
        x1, x2 = pcx - content_w / 2, pcx + content_w / 2
        {"Check up": self.draw_checkup, "Medications": self.draw_medications,
         "Orders": self.draw_orders, "Tasks": self.draw_tasks}[self.tab](x1, x2, y)
    def select_tab(self, name):
        self._cancel_checkup_animation()
        self._stop_call_input()
        self.tab = name
        self.chat_open = False
        self.call_open = False
        self.dropdown = None
        self.status = ""
        if name == "Check up":
            self.anim = 0.0
            self.render()
            self._checkup_animation_started = time.monotonic()
            self._animate()
        else:
            self.anim = 1.0
            self.render()
    def close_banner(self):
        self.banner = False
        self.render()
