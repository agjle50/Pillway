"""Orders tab: recent orders with status pills.

Called by: ui/patient/dashboard.py.
"""


from ..theme import (
    BORDER,
    INK,
    NAVY,
    SOFT_BLUE,
    TEXT_MUTED,
)
from ..sample_content import ORDERS


class OrdersMixin:
    def draw_orders(self, x1, x2, y):
        self.list_header(x1, x2, y, "Recent orders")
        y += self.S(40)
        colours = {"Processing": ("#fff4e5", "#b26a00"), "Shipped": (SOFT_BLUE, NAVY),
                   "Delivered": ("#e8f6ee", "#1e7a46")}
        for title, sub, status in ORDERS:
            self.text(x1 + self.S(6), y + self.S(38), title, 30, INK, "normal")
            self.text(x1 + self.S(6), y + self.S(72), sub, 14, TEXT_MUTED)
            bg, fg = colours[status]
            pw = self.S(120)
            self.rrect(x2 - pw, y + self.S(34), x2, y + self.S(66), self.S(16), fill=bg, outline="")
            self.text(x2 - pw / 2, y + self.S(50), status, 13, fg, "bold", anchor="center")
            y += self.S(98)
            self.c.create_line(x1, y, x2, y, fill=BORDER)
