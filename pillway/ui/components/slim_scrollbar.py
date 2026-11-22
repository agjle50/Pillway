"""A slim, modern scroll bar (rounded grey handle) used by every scrollable area.

Called by: ui/components/scroll_area.py (make_scroll).
BUG FIX: the old native scroll bar was packed AFTER a canvas that already took the full
width, so it got 0 px and never showed. This one is packed first and always has room.
Drag the handle, click above/below it to jump a page; it hides itself when nothing scrolls.
"""

import tkinter as tk

THUMB = "#c4c5cf"
THUMB_HOVER = "#8f90a3"


class SlimScrollbar(tk.Canvas):
    def __init__(self, master, command, width=12, bg="#ffffff"):
        super().__init__(master, width=width, bg=bg, highlightthickness=0, bd=0, cursor="arrow")
        self.command = command
        self.first, self.last = 0.0, 1.0
        self.hover = False
        self._drag_offset = None
        self.bind("<Configure>", lambda _e: self._draw())
        self.bind("<Enter>", lambda _e: self._set_hover(True))
        self.bind("<Leave>", lambda _e: self._set_hover(False))
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", lambda _e: setattr(self, "_drag_offset", None))

    # the scrolled canvas calls this (yscrollcommand)
    def set(self, first, last):
        self.first, self.last = float(first), float(last)
        self._draw()

    def _set_hover(self, value):
        self.hover = value
        self._draw()

    def _thumb(self):
        height = max(1, self.winfo_height())
        top = self.first * height
        bottom = max(top + 28, self.last * height)       # never smaller than 28 px to grab
        if bottom > height:
            top, bottom = height - (bottom - top), height
        return top, bottom

    def _draw(self):
        self.delete("all")
        if self.first <= 0.0 and self.last >= 1.0:
            return                                       # everything fits: no handle
        width = max(1, self.winfo_width())
        top, bottom = self._thumb()
        pad = 3 if self.hover or self._drag_offset is not None else 4
        x1, x2 = pad, width - pad
        r = (x2 - x1) / 2
        colour = THUMB_HOVER if self.hover or self._drag_offset is not None else THUMB
        self.create_oval(x1, top + 2, x2, top + 2 + 2 * r, fill=colour, outline=colour)
        self.create_oval(x1, bottom - 2 - 2 * r, x2, bottom - 2, fill=colour, outline=colour)
        self.create_rectangle(x1, top + 2 + r, x2, bottom - 2 - r, fill=colour, outline=colour)

    def _press(self, event):
        top, bottom = self._thumb()
        if top <= event.y <= bottom:
            self._drag_offset = event.y - top
        else:
            self.command("scroll", -1 if event.y < top else 1, "pages")

    def _drag(self, event):
        if self._drag_offset is None:
            return
        height = max(1, self.winfo_height())
        self.command("moveto", max(0.0, (event.y - self._drag_offset) / height))
