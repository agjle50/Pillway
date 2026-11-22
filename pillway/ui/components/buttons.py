"""Reusable buttons: the bevelled header button and the iOS-style toggle switch.

Called by: header, Tasks screen, settings screens.
"""


from ..theme import (
    INK,
    ORANGE,
    HOVER,
    SURFACE_HIGH,
    RED,
    SHADOW,
    BORDER_SOFT,
    TOGGLE_OFF,
    WHITE,
)


class ButtonsMixin:
    def beveled_button(self, x1, y1, x2, y2, icon, tag, func):
        """A softly raised circular icon button with a warm hover accent."""
        self.c.create_oval(
            x1 + self.S(1), y1 + self.S(3), x2 + self.S(1), y2 + self.S(3),
            fill=SHADOW, outline="", tags=f"{tag}::shadow",
        )
        self.c.create_oval(
            x1, y1, x2, y2, fill=SURFACE_HIGH, outline=BORDER_SOFT,
            width=max(1, self.S(1)), tags=(tag, f"{tag}::background"),
        )
        self.draw_icon(icon, (x1 + x2) / 2, (y1 + y2) / 2, self.S(24), INK, tag, bg=SURFACE_HIGH)
        self.clickable(tag, func)
        self.c.tag_bind(
            tag, "<Enter>",
            lambda *_: (
                self.c.itemconfigure(f"{tag}::background", fill=HOVER),
                self.c.itemconfigure(f"{tag}_icon", fill=ORANGE),
            ),
            add="+",
        )
        self.c.tag_bind(
            tag, "<Leave>",
            lambda *_: (
                self.c.itemconfigure(f"{tag}::background", fill=SURFACE_HIGH),
                self.c.itemconfigure(f"{tag}_icon", fill=INK),
            ),
            add="+",
        )

    def toggle(self, x, cy, on, tag, func):
        w, h = self.S(84), self.S(48)
        track_tag = f"{tag}::track"
        knob_tag = f"{tag}::knob"
        self.rrect(x, cy - h / 2, x + w, cy + h / 2, h / 2,
                   fill=RED if on else TOGGLE_OFF, outline="", tags=(tag, track_tag))
        r = h / 2 - self.S(3)
        kx = x + w - h / 2 if on else x + h / 2
        self.c.create_oval(kx - r, cy - r + self.S(1.5), kx + r, cy + r + self.S(1.5),
                           fill="#c4c9d4", outline="", tags=(tag, knob_tag))
        self.c.create_oval(kx - r, cy - r, kx + r, cy + r,
                           fill=WHITE, outline="", tags=(tag, knob_tag))
        self.clickable(tag, func)
