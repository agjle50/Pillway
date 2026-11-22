"""The left navigation drawer, matching Pillway's site.

Called by: PillwayApp.render().
Navy background, the Pillway wordmark (a real image, rendered at exact sizes so it stays
sharp) with a small "demo" label, white full-width highlight with red text on the current
page, thin dividers between groups, and a subtle hover colour.
"""

import tkinter as tk
from pathlib import Path

from ..navigation import NAV_ITEMS, PHARMACIST_NAV_ITEMS
from ..theme import (SIDEBAR_BG, SIDEBAR_DIVIDER, SIDEBAR_HOVER, SIDEBAR_SELECTED, SIDEBAR_SELECTED_TEXT,
                     SIDEBAR_TEXT)

LOGO_FOLDER = Path(__file__).resolve().parents[2] / "assets" / "logo"
LOGO_HEIGHTS = (28, 32, 36, 40, 44, 48, 52, 56, 60)


class SidebarMixin:
    def logo_image(self, height):
        """The wordmark at the closest pre-rendered size (never stretched, so never blurry)."""
        best = min(LOGO_HEIGHTS, key=lambda h: abs(h - height))
        cache = self.__dict__.setdefault("_logo_cache", {})
        if best not in cache:
            try:
                cache[best] = tk.PhotoImage(master=self, file=str(LOGO_FOLDER / f"pillway-{best}.png"))
            except Exception:
                cache[best] = None
        return cache[best]

    def draw_logo(self, cx, cy, height, demo=True, colour="#9c9db5"):
        """Wordmark centred at (cx, cy), with a small 'demo' label to its right."""
        image = self.logo_image(height)
        if image is None:  # image missing: fall back to text
            item = self.text(cx, cy, "Pillway", 30, SIDEBAR_TEXT, "bold", anchor="center")
            right = self.c.bbox(item)[2]
            bottom = cy + self.S(12)
        else:
            self.c.create_image(cx, cy, image=image, anchor="center")
            right, bottom = cx + image.width() / 2, cy + image.height() / 2
        if demo:
            self.text(right + self.S(6), bottom - self.S(4), self.t("demo") if hasattr(self, "t") else "demo",
                      12, colour, anchor="sw")

    def draw_sidebar(self):
        if self.role == "pharmacist" and self.section == "Dashboard" and self.doctor_workspace_open:
            self.draw_detail_sidebar()  # the black sidebar inside a patient's screen
            return
        c, sw, h = self.c, self.sw, self.h
        c.create_rectangle(0, 0, sw, h, fill=SIDEBAR_BG, outline=SIDEBAR_BG)
        self.draw_logo(sw / 2 - self.S(14), self.S(42), self.S(46))
        top = self.S(82)
        c.create_line(0, top, sw, top, fill=SIDEBAR_DIVIDER)

        y = top + self.S(6)
        row_h = self.S(53)
        for item in (PHARMACIST_NAV_ITEMS if self.role == "pharmacist" else NAV_ITEMS):
            if item is None:
                y += self.S(8)
                c.create_line(0, y, sw, y, fill=SIDEBAR_DIVIDER)
                y += self.S(8)
                continue
            label, icon = item
            tag = f"nav::{label.replace(' ', '_')}"
            selected = label == self.section or (label in ("Medications", "Orders", "Tasks")
                                                and self.section == "Dashboard" and self.tab == label
                                                and self.role == "patient")
            fill = SIDEBAR_SELECTED if selected else SIDEBAR_BG
            bg_tag = f"{tag}::background"
            c.create_rectangle(0, y, sw, y + row_h, fill=fill, outline=fill, tags=(tag, bg_tag))
            colour = SIDEBAR_SELECTED_TEXT if selected else SIDEBAR_TEXT
            self.draw_icon(icon, self.S(26), y + row_h / 2, self.S(22), colour, tag, bg=fill)
            self.text(self.S(52), y + row_h / 2, self.t(label), 15, colour, tag=tag)
            self.clickable(tag, lambda l=label: self.go(l))
            if not selected:
                c.tag_bind(tag, "<Enter>", lambda _e, b=bg_tag: c.itemconfigure(b, fill=SIDEBAR_HOVER,
                                                                                 outline=SIDEBAR_HOVER), add="+")
                c.tag_bind(tag, "<Leave>", lambda _e, b=bg_tag: c.itemconfigure(b, fill=SIDEBAR_BG,
                                                                                 outline=SIDEBAR_BG), add="+")
            y += row_h
