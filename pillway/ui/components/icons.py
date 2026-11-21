"""Canvas-drawn vector icons used across the application."""

import math

from .. import theme
from ..theme import WHITE


class IconMixin:
    def draw_icon(self, kind, cx, cy, size, color, tag, bg=WHITE):
        """Draw an icon on a 24x24 grid centred on (cx, cy)."""
        c = self.c
        u = size / 24
        lw = max(1.0, 1.9 * u)
        tags = (tag, f"{tag}_icon") if tag else None

        def P(*xy):
            return [cx + (v - 12) * u if i % 2 == 0 else cy + (v - 12) * u
                    for i, v in enumerate(xy)]

        def line(*xy, width=lw, smooth=False):
            c.create_line(*P(*xy), fill=color, width=width, capstyle="round",
                          joinstyle="round", smooth=smooth, tags=tags)

        def oval(x1, y1, x2, y2, fill="", width=lw):
            c.create_oval(*P(x1, y1, x2, y2), outline=color, fill=fill, width=width, tags=tags)

        def rect(x1, y1, x2, y2, r=0, fill=""):
            a = P(x1, y1, x2, y2)
            if r:
                self.rrect(*a, r * u, outline=color, fill=fill, width=lw, tags=tags)
            else:
                c.create_rectangle(*a, outline=color, fill=fill, width=lw, tags=tags)

        if kind == "grid":
            for x, y in ((3, 3), (14, 3), (3, 14), (14, 14)):
                rect(x, y, x + 7, y + 7, 1.5)
        elif kind == "gear":
            for k in range(8):
                a = k * math.pi / 4
                line(12 + 7 * math.cos(a), 12 + 7 * math.sin(a),
                     12 + 10 * math.cos(a), 12 + 10 * math.sin(a), width=lw * 1.8)
            oval(5, 5, 19, 19, fill=bg)
            oval(9.5, 9.5, 14.5, 14.5)
        elif kind == "person":
            oval(8, 3, 16, 11)
            c.create_arc(*P(4, 13, 20, 29), start=0, extent=180, style="arc",
                         outline=color, width=lw, tags=tags)
        elif kind == "pills":
            line(7, 17, 17, 7, width=8 * u)
            c.create_line(*P(7, 17, 17, 7), fill=bg, width=max(1, 8 * u - 2 * lw),
                          capstyle="round", tags=tags)
            line(9.5, 9.5, 14.5, 14.5)
        elif kind == "rx":
            rect(4, 5, 20, 19, 2)
            c.create_text(cx, cy, text="Rx", fill=color,
                          font=(theme.FONT, -max(1, round(7 * u)), "bold"), tags=tags)
        elif kind == "stethoscope":
            line(7, 3, 7, 10, 12, 15, 17, 10, 17, 3, smooth=True)
            line(12, 15, 12, 19, 16, 20, 18, 17, smooth=True)
            oval(16.5, 13, 20.5, 17)
        elif kind == "order":
            rect(5, 3, 19, 21, 2)
            line(8.5, 8, 15.5, 8)
            line(8.5, 12, 15.5, 12)
            line(8.5, 16, 13, 16)
        elif kind == "task":
            rect(4, 4, 20, 20, 3)
            line(8, 12, 11, 15, 16.5, 9)
        elif kind == "phone":
            c.create_polygon(*P(6, 3, 9.5, 3, 11, 8, 8.5, 10, 14, 15.5, 16, 13, 21, 14.5, 21, 18,
                                18, 21, 11, 19, 5, 13, 3, 6),
                             smooth=True, outline=color, fill="", width=lw, tags=tags)
        elif kind == "bulb":
            c.create_arc(*P(6, 2, 18, 14), start=-40, extent=260, style="arc",
                         outline=color, width=lw, tags=tags)
            line(9, 13, 9, 17, 15, 17, 15, 13)
            line(10, 20, 14, 20)
        elif kind == "question":
            c.create_text(cx, cy, text="?", fill=color,
                          font=(theme.FONT, -max(1, round(20 * u)), "bold"), tags=tags)
        elif kind == "bell":
            line(6, 17, 7, 9.5, 12, 4.5, 17, 9.5, 18, 17, smooth=True)
            line(4.5, 17, 19.5, 17)
            c.create_arc(*P(9.5, 17, 14.5, 22), start=180, extent=180, style="arc",
                         outline=color, width=lw, tags=tags)
        elif kind == "card":
            rect(3, 6, 21, 18, 2.5)
            line(3, 10.5, 21, 10.5, width=lw * 1.5)
            line(6, 14.5, 10, 14.5)
        elif kind == "heart":
            c.create_polygon(*P(12, 20.5, 4, 12.5, 3, 8.5, 5, 5, 9, 4, 12, 7, 15, 4, 19, 5, 21, 8.5,
                                20, 12.5, 12, 20.5),
                             smooth=True, outline=color, fill="", width=lw, tags=tags)
            line(5.5, 12, 9, 12, 10.5, 9.5, 13, 14.5, 14.5, 12, 18.5, 12)
        elif kind == "box":
            c.create_polygon(*P(12, 3, 20, 7, 20, 17, 12, 21, 4, 17, 4, 7), outline=color,
                             fill="", width=lw, joinstyle="round", tags=tags)
            line(4, 7, 12, 11, 20, 7)
            line(12, 11, 12, 21)
        elif kind == "lock":
            rect(5, 11, 19, 21, 2.5)
            c.create_arc(*P(8, 4, 16, 14), start=0, extent=180, style="arc",
                         outline=color, width=lw, tags=tags)
            line(8, 9, 8, 11)
            line(16, 9, 16, 11)
        elif kind == "tag":
            oval(3, 3, 21, 21)
            line(9, 15, 15, 9)
            oval(8, 8, 10, 10, fill=color, width=1)
            oval(14, 14, 16, 16, fill=color, width=1)
        elif kind == "ticket":
            c.create_polygon(*P(3, 10, 10, 3, 21, 14, 14, 21), outline=color, fill="",
                             width=lw, joinstyle="round", tags=tags)
            line(8.5, 11.5, 12.5, 15.5)
        elif kind == "doc":
            rect(5, 3, 17, 21, 2)
            line(8, 8, 14, 8)
            line(8, 12, 12, 12)
            oval(14, 13, 20, 19, fill=bg)
            line(17, 15, 17, 17)
        elif kind == "chat":
            rect(3, 4, 21, 16, 4)
            c.create_polygon(*P(7, 15.5, 6.5, 21, 12, 15.5), fill=color, outline=color, tags=tags)
        elif kind == "mic":
            rect(9, 3, 15, 14, 3)
            c.create_arc(*P(6, 7, 18, 17), start=180, extent=180, style="arc",
                         outline=color, width=lw, tags=tags)
            line(12, 17, 12, 21)
            line(9, 21, 15, 21)
        elif kind == "send":
            c.create_polygon(*P(4, 4, 21, 12, 4, 20, 7, 12), fill=color, outline=color,
                             joinstyle="round", tags=tags)
        elif kind == "plus":
            line(12, 4, 12, 20, width=lw * 1.3)
            line(4, 12, 20, 12, width=lw * 1.3)
        elif kind == "transfer":
            line(4, 8, 20, 8)
            line(16, 4, 20, 8, 16, 12)
            line(20, 16, 4, 16)
            line(8, 12, 4, 16, 8, 20)
        elif kind == "upload":
            rect(4, 5, 20, 20, 2)
            line(12, 15, 12, 3)
            line(8, 7, 12, 3, 16, 7)
            line(6, 16, 10, 12, 13, 15, 16, 12, 19, 16)
        elif kind == "close":
            line(6, 6, 18, 18)
            line(18, 6, 6, 18)
        elif kind == "chev_right":
            line(9, 5, 16, 12, 9, 19)
        elif kind == "chev_down":
            line(5, 9, 12, 16, 19, 9)
        elif kind == "clipboard":
            rect(5, 4, 19, 21, 2)
            rect(9, 2.5, 15, 6, 1, fill=bg)
            line(8.5, 10, 15.5, 10)
            line(8.5, 13.5, 15.5, 13.5)
            line(8.5, 17, 13, 17)
        elif kind == "flag":
            line(6, 21, 6, 3)
            c.create_polygon(*P(6, 3.5, 18, 3.5, 15, 7.5, 18, 11.5, 6, 11.5), fill=color, outline=color, tags=tags)
        elif kind == "speaker":
            c.create_polygon(*P(4, 9, 8, 9, 13, 5, 13, 19, 8, 15, 4, 15), fill="", outline=color, width=lw, tags=tags)
            c.create_arc(*P(11, 8, 17, 16), start=-60, extent=120, style="arc", outline=color, width=lw, tags=tags)
            c.create_arc(*P(11, 5, 21, 19), start=-60, extent=120, style="arc", outline=color, width=lw, tags=tags)
        elif kind == "check":
            line(5, 12.5, 10, 17.5, 19, 7)
        elif kind == "alert":
            c.create_polygon(*P(12, 3, 22, 20, 2, 20), fill="", outline=color, width=lw, tags=tags)
            line(12, 9, 12, 14)
            oval(11.3, 16.3, 12.7, 17.7, fill=color)
        elif kind == "undo":
            c.create_arc(*P(5, 6, 20, 20), start=-90, extent=270, style="arc", outline=color, width=lw, tags=tags)
            line(5, 7, 8.5, 12.5, 12, 9)
        elif kind == "back":
            line(15, 4, 7, 12, 15, 20)
