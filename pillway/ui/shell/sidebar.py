"""The left side menu for the patient side (Google-style light drawer with a pill highlight).

Called by: PillwayApp.render().
"""


from ..theme import BORDER_SOFT, NAVY, SURFACE, TEXT_DARK, TONAL
from ..navigation import NAV_ITEMS, PHARMACIST_NAV_ITEMS


class SidebarMixin:
    def draw_sidebar(self):
        if self.role == "pharmacist" and self.section == "Dashboard" and self.doctor_workspace_open:
            self.draw_detail_sidebar()  # the black sidebar inside a patient's screen
            return
        c, sw, h = self.c, self.sw, self.h
        c.create_rectangle(0, 0, sw, h, fill=SURFACE, outline=SURFACE)
        self.text(self.S(36), self.S(50), "Pillway", 32, NAVY, "bold")

        y = self.S(100)
        row_h = self.S(54)
        for item in (PHARMACIST_NAV_ITEMS if self.role == "pharmacist" else NAV_ITEMS):
            if item is None:
                y += self.S(8)
                c.create_line(self.S(24), y, sw - self.S(16), y, fill=BORDER_SOFT)
                y += self.S(10)
                continue
            label, icon = item
            tag = f"nav::{label.replace(' ', '_')}"
            selected = label == self.section or (label in ("Medications", "Orders", "Tasks")
                                                and self.section == "Dashboard" and self.tab == label
                                                and self.role == "patient")
            x1, x2 = self.S(12), sw - self.S(12)
            fill = TONAL if selected else SURFACE
            self.rrect(x1, y + self.S(3), x2, y + row_h - self.S(3), (row_h - self.S(6)) / 2,
                       fill=fill, outline=fill, tags=tag)
            colour = NAVY if selected else TEXT_DARK
            self.draw_icon(icon, self.S(44), y + row_h / 2, self.S(22), colour, tag, bg=fill)
            self.text(self.S(74), y + row_h / 2, label, 16, colour, "bold" if selected else "normal", tag=tag)
            self.clickable(tag, lambda l=label: self.go(l))
            y += row_h
