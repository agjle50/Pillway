"""Settings page and the generic page title / placeholder page.

Called by: PillwayApp.render() for Settings and any section without its own screen.
"""


from ..theme import (
    RED,
    BORDER,
    INK,
    TEXT_MUTED,
    WHITE,
)
from ..navigation import SETTINGS_ITEMS


class SettingsMixin:
    def page_title(self, title):
        y = self.S(120)
        self.c.create_rectangle(self.sw + self.S(18), y - self.S(20), self.sw + self.S(56),
                                y + self.S(20), fill=WHITE, outline=WHITE, tags="back")
        self.draw_icon("back", self.sw + self.S(36), y, self.S(26), INK, "back")
        self.clickable("back", lambda: self.go("Dashboard"))
        self.text(self.sw + self.S(70), y, title, 22, INK)
        self.c.create_line(self.sw, y + self.S(36), self.w, y + self.S(36), fill=BORDER)
        return y + self.S(36)

    def draw_settings(self):
        y = self.page_title("Settings")
        x1 = self.sw + self.S(20)
        x2 = x1 + min(self.S(520), self.w - x1 - self.S(20))
        row = self.S(70)
        for label, icon in SETTINGS_ITEMS:
            tag = f"set::{label}"
            self.c.create_rectangle(x1, y, x2, y + row, fill=WHITE, outline=WHITE, tags=tag)
            self.draw_icon(icon, x1 + self.S(16), y + row / 2, self.S(26), INK, tag)
            self.text(x1 + self.S(46), y + row / 2, label, 17, INK, tag=tag)
            self.draw_icon("chev_right", x2 - self.S(20), y + row / 2, self.S(16), TEXT_MUTED, tag)
            self.c.create_line(x1, y + row, x2, y + row, fill=BORDER)
            self.clickable(tag, lambda name=label: self.go(name))  # was a dead click
            y += row
        if self.role == "pharmacist":
            tag = "set::reset_demo"
            self.rrect(x1, y + self.S(24), x1 + self.S(220), y + self.S(74), self.S(12), fill=RED, outline="", tags=tag)
            self.text(x1 + self.S(110), y + self.S(49), "Reset demo", 15, WHITE, "bold", anchor="center", tag=tag)
            self.text(x1 + self.S(240), y + self.S(49), "Restores Maria to a fresh, newly-enrolled state.", 12, TEXT_MUTED)
            self.clickable(tag, self.reset_demo)

    def draw_placeholder_page(self, title):
        """Any page without content yet: its title and a friendly "Coming soon" (never a dead click)."""
        y = self.page_title(title)
        cx = (self.sw + self.w) / 2
        cy = (y + self.h) / 2
        self.draw_icon("bulb", cx, cy - self.S(60), self.S(44), TEXT_MUTED, None)
        self.text(cx, cy, "Coming soon", 22, INK, "bold", anchor="center")
        message = "Payments are made here." if title == "Payments" else f"{title} isn't part of this demo yet."
        self.text(cx, cy + self.S(36), message, 15, TEXT_MUTED, anchor="center")
