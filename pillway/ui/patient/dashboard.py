"""The patient dashboard panel with the top icon tab bar (Check up, Medications, Orders, Tasks).

Called by: PillwayApp.render() for the Dashboard section.
"""

import time

from ..theme import (
    BORDER,
    NAVY_DARK,
    RED,
    RADIUS,
    RED_TEXT,
    TEXT_DARK,
    TEXT_MUTED,
    WHITE,
)
from ..navigation import TABS


class PatientDashboardMixin:
    def panel_box(self):
        return (self.sw + self.S(14), self.S(92), self.w - self.S(14), self.h - self.S(14))

    def draw_sheet(self, x1, y1, x2, y2):
        """The white content panel with a thin border (Pillway's card style)."""
        self.c.create_rectangle(x1, y1, x2, y2, fill=WHITE, outline=BORDER)

    def draw_chat_fab(self):
        """Round red chat button in the bottom-right corner: opens the chat with Sarah."""
        px1, py1, px2, py2 = self.panel_box()
        r = self.S(30)
        cx, cy = px2 - self.S(14) - r, py2 - self.S(14) - r
        self.circle(self.c, cx - r + self.S(1), cy - r + self.S(3), cx + r + self.S(1), cy + r + self.S(3),
                    fill="#d9d9de", tags="chat_fab")
        self.circle(self.c, cx - r, cy - r, cx + r, cy + r, fill=RED, tags=("chat_fab", "chat_fab::bg"))
        self.draw_icon("chat", cx, cy, self.S(26), WHITE, "chat_fab", bg=RED)
        self.clickable("chat_fab", lambda: self.checkup_choice("Chat"))
        self._hover_shade("chat_fab", "chat_fab::bg", RED, "#c7361f")

    def draw_dashboard(self):
        px1, py1, px2, py2 = self.panel_box()
        self.draw_sheet(px1, py1, px2, py2)
        if self.intake_should_show():
            self.draw_intake(px1, py1, px2, py2)
            return
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

        # text tabs, centred, the selected one in red with a red underline (Pillway's style)
        labels = [(name, self.t(label_key)) for name, _icon, label_key in TABS]
        widths = []
        for _name, label in labels:
            probe = self.c.create_text(0, -500, text=label, font=self.font(17))
            widths.append(self.c.bbox(probe)[2] - self.c.bbox(probe)[0])
            self.c.delete(probe)
        gap = self.S(26)
        x = pcx - (sum(widths) + gap * (len(widths) - 1)) / 2
        ty = py1 + self.S(30)
        for (name, label), width in zip(labels, widths):
            tag = "tab::" + "_".join(name.split())
            sel = name == self.tab
            col = RED if sel else TEXT_DARK
            self.c.create_rectangle(x - self.S(8), py1 + self.S(6), x + width + self.S(8), py1 + self.S(54),
                                    fill=WHITE, outline=WHITE, tags=tag)
            self.text(x + width / 2, ty, label, 17, col, anchor="center", tag=tag)
            if sel:
                self.c.create_rectangle(x - self.S(8), py1 + self.S(50), x + width + self.S(8), py1 + self.S(53),
                                        fill=RED, outline=RED, tags=tag)
            self.clickable(tag, lambda n=name: self.select_tab(n))
            x += width + gap

        y = py1 + self.S(78)
        if self.banner and self.tab == "Check up":
            bw = min(self.S(700), px2 - px1 - self.S(60))
            bx1, bx2 = pcx - bw / 2, pcx + bw / 2
            self.rrect(bx1, y, bx2, y + self.S(56), self.S(RADIUS), fill=NAVY_DARK, outline="")
            self.c.create_text(bx1 + self.S(22), y + self.S(28), text=self.t("banner"), fill=WHITE, anchor="w",
                               font=self.font(13), width=max(1, bw - self.S(70)))
            self.c.create_oval(bx2 - self.S(36), y + self.S(14), bx2 - self.S(8), y + self.S(42),
                               fill=NAVY_DARK, outline="", tags="banner_x")
            self.draw_icon("close", bx2 - self.S(22), y + self.S(28), self.S(16), WHITE, "banner_x")
            self.clickable("banner_x", self.close_banner)
            y += self.S(80)
        else:
            y += self.S(10)

        content_w = min(self.S(820), px2 - px1 - self.S(80))
        x1, x2 = pcx - content_w / 2, pcx + content_w / 2
        if self.tab == "Care plan":
            self.draw_patient_care_plan(px1 + self.S(30), px2 - self.S(30), y, py2 - self.S(16))
        else:
            {"Check up": self.draw_checkup, "Medications": self.draw_medications,
             "Orders": self.draw_orders, "Tasks": self.draw_tasks}[self.tab](x1, x2, y)
        if self.tab != "Check up":
            self.draw_chat_fab()
        if self.check_in_popup_should_show():
            self.draw_check_in_popup(px1, py1, px2, py2)

    def select_tab(self, name):
        self._cancel_checkup_animation()
        if getattr(self, "intake_open", False):
            self.intake_open = False
        if self.call_open:
            self.close_call_preview()
        elif self.chat_open:
            self._end_chat_session()
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
