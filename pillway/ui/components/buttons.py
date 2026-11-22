"""Reusable buttons: the bevelled header button and the iOS-style toggle switch.

Called by: header, Tasks screen, settings screens.
"""


from ..theme import (
    INK,
    SURFACE_HIGH,
    RED,
    SHADOW,
    TOGGLE_OFF,
    WHITE,
)


class ButtonsMixin:
    def beveled_button(self, x1, y1, x2, y2, icon, tag, func):
        """A round icon button (Google style: flat circle, no bevel or shadow)."""
        self.c.create_oval(x1, y1, x2, y2, fill=SURFACE_HIGH, outline="", tags=tag)
        self.draw_icon(icon, (x1 + x2) / 2, (y1 + y2) / 2, self.S(24), INK, tag, bg=SURFACE_HIGH)
        self.clickable(tag, func)

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
