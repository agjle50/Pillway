"""The navy left sidebar for the patient side.

Called by: PillwayApp.render().
"""


from ..theme import (
    DIVIDER,
    NAV_ICON,
    NAV_TEXT,
    NAVY,
    NAVY_DARK,
    RED,
    WHITE,
)
from ..navigation import NAV_ITEMS, PHARMACIST_NAV_ITEMS


class SidebarMixin:
    def draw_sidebar(self):
        if self.role == "pharmacist" and self.section == "Dashboard" and self.doctor_workspace_open:
            self.draw_detail_sidebar()  # the black sidebar inside a patient's screen
            return
        c, sw, h = self.c, self.sw, self.h
        c.create_rectangle(0, 0, sw, h, fill=NAVY, outline=NAVY)
        c.create_rectangle(0, 0, sw, self.S(100), fill=NAVY_DARK, outline=NAVY_DARK)
        self.text(sw / 2, self.S(50), "Pillway", 38, WHITE, "bold", anchor="center")
        c.create_line(0, self.S(100), sw, self.S(100), fill=DIVIDER)

        y = self.S(104)
        row_h = self.S(60)
        for item in (PHARMACIST_NAV_ITEMS if self.role == "pharmacist" else NAV_ITEMS):
            if item is None:
                y += self.S(6)
                c.create_line(0, y, sw, y, fill=DIVIDER)
                y += self.S(8)
                continue
            label, icon = item
            tag = f"nav::{label}"
            selected = label == self.section or (label in ("Medications", "Orders", "Tasks")
                                                and self.section == "Dashboard" and self.tab == label
                                                and self.role == "patient")
            bg = WHITE if selected else NAVY
            fg = RED if selected else NAV_TEXT
            ic = RED if selected else NAV_ICON
            c.create_rectangle(0, y, sw, y + row_h, fill=bg, outline=bg, tags=tag)
            self.draw_icon(icon, self.S(32), y + row_h / 2, self.S(26), ic, tag, bg=bg)
            self.text(self.S(62), y + row_h / 2, label, 16, fg,
                      "bold" if selected else "normal", tag=tag)
            self.clickable(tag, lambda l=label: self.go(l))
            y += row_h
