"""The left navigation drawer with Pillway's navy background and orange active accent.

Called by: PillwayApp.render().
"""


from ..theme import BORDER_SOFT, NAVY, SIDEBAR_BG, SIDEBAR_HOVER, SIDEBAR_SELECTED, SIDEBAR_SELECTED_TEXT, \
    SIDEBAR_TEXT, WHITE
from ..navigation import NAV_ITEMS, PHARMACIST_NAV_ITEMS


class SidebarMixin:
    def draw_sidebar(self):
        if self.role == "pharmacist" and self.section == "Dashboard" and self.doctor_workspace_open:
            self.draw_detail_sidebar()  # the black sidebar inside a patient's screen
            return
        c, sw, h = self.c, self.sw, self.h
        c.create_rectangle(0, 0, sw, h, fill=SIDEBAR_BG, outline=SIDEBAR_BG)
        self.draw_icon("pills", self.S(40), self.S(48), self.S(30), WHITE, "pillway_logo", bg=SIDEBAR_BG)
        self.text(self.S(68), self.S(50), "Pillway", 31, WHITE, "bold", tag="pillway_logo")

        y = self.S(100)
        row_h = self.S(54)
        for item in (PHARMACIST_NAV_ITEMS if self.role == "pharmacist" else NAV_ITEMS):
            if item is None:
                y += self.S(8)
                c.create_line(self.S(24), y, sw - self.S(16), y, fill="#353c6a")
                y += self.S(10)
                continue
            label, icon = item
            tag = f"nav::{label.replace(' ', '_')}"
            selected = label == self.section or (label in ("Medications", "Orders", "Tasks")
                                                and self.section == "Dashboard" and self.tab == label
                                                and self.role == "patient")
            x1, x2 = self.S(12), sw - self.S(12)
            fill = SIDEBAR_SELECTED if selected else SIDEBAR_BG
            bg_tag = f"{tag}::background"
            self.rrect(x1, y + self.S(3), x2, y + row_h - self.S(3), (row_h - self.S(6)) / 2,
                       fill=fill, outline=fill, tags=(tag, bg_tag))
            colour = SIDEBAR_SELECTED_TEXT if selected else SIDEBAR_TEXT
            self.draw_icon(icon, self.S(44), y + row_h / 2, self.S(22), colour, tag, bg=fill)
            self.text(self.S(74), y + row_h / 2, label, 16, colour, "bold" if selected else "normal", tag=tag)
            self.clickable(tag, lambda l=label: self.go(l))
            if not selected:
                c.tag_bind(
                    tag, "<Enter>",
                    lambda _event, background=bg_tag: c.itemconfigure(
                        background, fill=SIDEBAR_HOVER, outline=SIDEBAR_HOVER
                    ),
                    add="+",
                )
                c.tag_bind(
                    tag, "<Leave>",
                    lambda _event, background=bg_tag: c.itemconfigure(
                        background, fill=SIDEBAR_BG, outline=SIDEBAR_BG
                    ),
                    add="+",
                )
            y += row_h
