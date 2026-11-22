"""Scrollable areas and small drawing helpers that work on ANY canvas (not just the main one).

Called by: pharmacist screens (flags, care plan editor, log...), patient care plan, tasks.
Why: long lists need scrolling, so they are drawn on a canvas inside a scrollable frame.
Helpers: make_scroll(), finish_scroll(), rr() rounded box, tx() text, btn() button, chip(), draw_toast().
Buttons are at least 44 px tall at normal size (easy to tap) and show a hand cursor.
"""

import tkinter as tk

from ..theme import BORDER, FOCUS, INK, RED, RED_DARK, SHADOW, TEXT_DARK, TEXT_MUTED, WHITE

BUTTON_STYLES = {
    "primary": (RED, WHITE, RED),
    "outline": (WHITE, RED, RED),
    "ghost": (WHITE, INK, BORDER),
    "dark": (INK, WHITE, INK),
    "danger": (WHITE, RED_DARK, RED_DARK),
    "green": ("#1e7a46", WHITE, "#1e7a46"),
}


class ScrollAreaMixin:
    def make_scroll(self, x1, y1, x2, y2, bg=WHITE):
        """Create a scrollable canvas in the box. Draw on the returned canvas, then call finish_scroll()."""
        frame = tk.Frame(self, bg=bg, bd=0, highlightthickness=0)
        canvas = tk.Canvas(frame, bg=bg, bd=0, highlightthickness=0, yscrollincrement=max(1, int(self.S(20))))
        bar = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=bar.set, width=max(1, int(x2 - x1)), height=max(1, int(y2 - y1)))
        canvas.pack(side="left", fill="both", expand=True)
        canvas._bar = bar
        canvas._box = (x1, y1, x2, y2)

        def wheel(event):
            step = int(-event.delta / 120) or (-1 if event.delta > 0 else 1)
            canvas.yview_scroll(step, "units")
            return "break"
        canvas.bind("<MouseWheel>", wheel)
        canvas.bind("<Button-4>", lambda _e: canvas.yview_scroll(-1, "units"))
        canvas.bind("<Button-5>", lambda _e: canvas.yview_scroll(1, "units"))
        self.c.create_window(x1, y1, window=frame, anchor="nw", width=max(1, int(x2 - x1)), height=max(1, int(y2 - y1)))
        self.embedded_frames.append(frame)
        return canvas

    def finish_scroll(self, canvas, content_height, keep_bottom=False):
        x1, y1, x2, y2 = canvas._box
        height = max(content_height, y2 - y1)
        canvas.configure(scrollregion=(0, 0, int(x2 - x1), int(height)))
        if content_height > y2 - y1 + 2:
            canvas._bar.pack(side="right", fill="y")
        if keep_bottom:
            self.after_idle(lambda: canvas.winfo_exists() and canvas.yview_moveto(1.0))

    # ---- drawing on any canvas ------------------------------------------------------------

    def rr(self, canvas, x1, y1, x2, y2, r, **kw):
        r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return canvas.create_polygon(pts, smooth=True, **kw)

    def tx(self, canvas, x, y, text, size, color=TEXT_DARK, weight="normal", anchor="nw", width=None, tag=None):
        options = {"text": text, "fill": color, "anchor": anchor, "font": self.font(size, weight)}
        if width:
            options["width"] = max(1, width)
        if tag:
            options["tags"] = tag
        return canvas.create_text(x, y, **options)

    def bottom_of(self, canvas, item):
        box = canvas.bbox(item)
        return box[3] if box else 0

    def btn(self, canvas, x1, y1, label, func, kind="ghost", tag=None, size=12, min_w=0, height=None):
        """Draw a button starting at (x1, y1). Returns its right edge x."""
        fill, ink, outline = BUTTON_STYLES[kind]
        tag = tag or f"btn::{id(func)}::{label}::{x1:.0f}::{y1:.0f}"
        height = height or self.S(38)
        probe = canvas.create_text(0, -1000, text=label, font=self.font(size, "bold"))
        box = canvas.bbox(probe)
        canvas.delete(probe)
        width = max(min_w, (box[2] - box[0]) + self.S(28) if box else self.S(100))
        self.rr(canvas, x1, y1, x1 + width, y1 + height, self.S(9), fill=fill, outline=outline,
                width=max(1, self.S(1.3)), tags=tag)
        canvas.create_text(x1 + width / 2, y1 + height / 2, text=label, fill=ink, font=self.font(size, "bold"), tags=tag)
        self.bind_click(canvas, tag, func)
        return x1 + width

    def bind_click(self, canvas, tag, func):
        canvas.tag_bind(tag, "<Button-1>", lambda _e: self._invoke_clickable(func))
        canvas.tag_bind(tag, "<Enter>", lambda _e: canvas.configure(cursor="hand2"))
        canvas.tag_bind(tag, "<Leave>", lambda _e: canvas.configure(cursor=""))

    def chip(self, canvas, x, y, label, fg=TEXT_DARK, bg="#eef1f6", size=10):
        """A small rounded label. Returns its right edge x."""
        probe = canvas.create_text(0, -1000, text=label, font=self.font(size, "bold"))
        box = canvas.bbox(probe)
        canvas.delete(probe)
        width = (box[2] - box[0]) + self.S(16) if box else self.S(60)
        self.rr(canvas, x, y, x + width, y + self.S(22), self.S(11), fill=bg, outline="")
        canvas.create_text(x + width / 2, y + self.S(11), text=label, fill=fg, font=self.font(size, "bold"))
        return x + width

    def draw_toast(self):
        """Short confirmation at the bottom centre ("Saved", "Flag resolved")."""
        cx, y = (self.sw + self.w) / 2, self.h - self.S(46)
        item = self.c.create_text(cx, y, text=self.toast, fill=WHITE, font=self.font(13, "bold"))
        box = self.c.bbox(item)
        pad = self.S(16)
        self.rrect(box[0] - pad, box[1] - self.S(8), box[2] + pad, box[3] + self.S(8), self.S(14),
                   fill=INK, outline=SHADOW)
        self.c.tag_raise(item)

    def focus_ring(self, canvas, x1, y1, x2, y2):
        return self.rr(canvas, x1 - 3, y1 - 3, x2 + 3, y2 + 3, self.S(10), fill="", outline=FOCUS, width=2)

    def section_title(self, canvas, x, y, title, subtitle=""):
        self.tx(canvas, x, y, title, 20, INK, "bold")
        if subtitle:
            self.tx(canvas, x, y + self.S(32), subtitle, 12, TEXT_MUTED)
        return y + self.S(64 if subtitle else 40)
