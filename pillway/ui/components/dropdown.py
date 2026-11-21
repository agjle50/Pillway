"""The notifications and profile dropdown menus under the header.

Called by: PillwayApp.render() when self.dropdown is set.
"""


from ..theme import (
    BORDER,
    INK,
    RED,
    SHADOW,
    TEXT_MUTED,
    WHITE,
)


class DropdownMixin:
    def draw_dropdown(self):
        if self.dropdown == "notifications":
            items = self.notifications
            x2 = self.bell_box[0] + self.S(330)
            title = "Notifications"
        else:
            items = [("Manage profiles", "Switch between family members"),
                     ("Settings", "Account, payments, notifications"),
                     ("Sign out", "")]
            x2 = self.w - self.S(18)
            title = "Team AGILE"
        top = self.S(86)
        dw = self.S(340)
        x1 = x2 - dw
        rh = self.S(66)
        y2 = top + self.S(56) + rh * len(items)
        self.rrect(x1, top + self.S(5), x2, y2 + self.S(5), self.S(16), fill=SHADOW, outline="")
        self.rrect(x1, top, x2, y2, self.S(16), fill=WHITE, outline=BORDER, width=self.S(1.2))
        self.text(x1 + self.S(20), top + self.S(28), title, 16, INK, "bold")
        y = top + self.S(56)
        for i, (head, sub) in enumerate(items):
            tag = f"dd::{i}"
            self.c.create_line(x1 + self.S(16), y, x2 - self.S(16), y, fill=BORDER)
            self.c.create_rectangle(x1 + self.S(2), y + 1, x2 - self.S(2), y + rh - 1,
                                    fill=WHITE, outline=WHITE, tags=tag)
            if sub:
                self.text(x1 + self.S(20), y + self.S(22), head, 14, INK, "bold", tag=tag)
                self.text(x1 + self.S(20), y + self.S(46), sub, 13, TEXT_MUTED, tag=tag)
            else:
                self.text(x1 + self.S(20), y + rh / 2, head, 14, RED, "bold", tag=tag)
            if self.dropdown == "profile" and head in ("Manage profiles", "Settings"):
                self.clickable(tag, lambda h=head: self.go(h))
            else:
                self.clickable(tag, lambda: self.toggle_dropdown(None))
            y += rh
