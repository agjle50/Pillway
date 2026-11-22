"""Reusable buttons: the bevelled header button and the iOS-style toggle switch.

Called by: header, Tasks screen, settings screens.
"""


from ..theme import BORDER, HOVER, INK, RADIUS, RED, TOGGLE_OFF, WHITE


class ButtonsMixin:
    def beveled_button(self, x1, y1, x2, y2, icon, tag, func):
        """Pillway's outlined square icon button (bell, card): no highlight, grey fill on hover."""
        bg_tag = f"{tag}::background"
        self.rrect(x1, y1, x2, y2, self.S(RADIUS), fill=WHITE, outline=BORDER, width=self.S(1.2),
                   tags=(tag, bg_tag))
        self.draw_icon(icon, (x1 + x2) / 2, (y1 + y2) / 2, self.S(22), INK, tag)
        self.clickable(tag, func)
        self._hover_shade(tag, bg_tag, WHITE, HOVER)

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
