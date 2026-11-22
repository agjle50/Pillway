"""Drawing helpers shared by every screen: scaling, fonts, rounded rectangles, clickable areas.

Called by: pillway/app.py (mixed into PillwayApp); used by every ui/ file as self.S(), self.text(), ....
"""


from .theme import (
    BORDER,
    INK,
)
from . import theme


from .components import smooth

SMOOTH_OPTIONS = {"fill", "outline", "width", "tags", "state"}

class CanvasHelpersMixin:
    def S(self, v):
        return v * self.s

    def font(self, size, weight="normal", slant="roman"):
        size = max(size, theme.MIN_TEXT)  # accessibility: no text smaller than MIN_TEXT
        return (theme.FONT, -max(1, round(size * self.s)), weight, slant)

    def rrect(self, x1, y1, x2, y2, r, **kw):
        return self.round_box(self.c, x1, y1, x2, y2, r, **kw)

    def round_box(self, canvas, x1, y1, x2, y2, r, **kw):
        """Rounded box on any canvas: crisp anti-aliased image when possible (see smooth.py).

        House style: corners are at most RADIUS (8 px). Only shapes asked to be fully round
        (radius = half the height, e.g. toggle switches) keep their pill shape.
        """
        short = min(abs(x2 - x1), abs(y2 - y1))
        if r < short / 2 - 0.5:
            r = min(r, self.S(theme.RADIUS))
        if smooth.available() and set(kw) <= SMOOTH_OPTIONS:
            try:
                return smooth.shape(canvas, "rect", x1, y1, x2, y2, r, **kw)
            except Exception as error:  # never break a screen over a rounded corner
                print(f"[smooth] {type(error).__name__}: {error}")
        r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return canvas.create_polygon(pts, smooth=True, **kw)

    def circle(self, canvas, x1, y1, x2, y2, **kw):
        """Crisp anti-aliased circle/ellipse on any canvas (falls back to a plain oval)."""
        if smooth.available() and set(kw) <= SMOOTH_OPTIONS:
            try:
                return smooth.shape(canvas, "oval", x1, y1, x2, y2, **kw)
            except Exception as error:
                print(f"[smooth] {type(error).__name__}: {error}")
        return canvas.create_oval(x1, y1, x2, y2, **kw)

    def _hover_shade(self, tag, bg_tag, normal, hover, canvas=None, outline=False):
        """Change the background shape bg_tag to `hover` while the pointer is over `tag`."""
        canvas = canvas or self.c
        kw = (lambda colour: {"fill": colour, "outline": colour}) if outline else (lambda colour: {"fill": colour})
        canvas.tag_bind(tag, "<Enter>", lambda _e: self.recolor(bg_tag, canvas=canvas, **kw(hover)), add="+")
        canvas.tag_bind(tag, "<Leave>", lambda _e: self.recolor(bg_tag, canvas=canvas, **kw(normal)), add="+")

    def recolor(self, tag, fill=None, outline=None, canvas=None):
        """Recolour shapes after drawing (works for crisp image shapes and plain items)."""
        smooth.recolor(canvas or self.c, tag, fill=fill, outline=outline)

    def _unused_old_rrect(self, x1, y1, x2, y2, r, **kw):
        r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return self.c.create_polygon(pts, smooth=True, **kw)

    def clickable(self, tag, func):
        bounds = self.c.bbox(tag)
        if bounds:
            padding = max(4, round(self.S(8)))
            x1, y1, x2, y2 = bounds
            self._click_targets.append((
                x1 - padding, y1 - padding, x2 + padding, y2 + padding,
                bounds, func,
            ))
        self.c.tag_bind(tag, "<Button-1>", lambda _event: self._invoke_clickable(func))
        self.c.tag_bind(tag, "<Enter>", lambda e: self.c.configure(cursor="hand2"))
        self.c.tag_bind(tag, "<Leave>", lambda e: self.c.configure(cursor=""))

    def _invoke_clickable(self, func):
        self._play_click_sound()
        func()
        return "break"

    def _play_click_sound(self):
        self.bell()

    def _sound_on_native_button_click(self, event):
        if event.widget.winfo_class() in ("Button", "TButton"):
            self._play_click_sound()

    def _dispatch_expanded_click(self, event):
        candidates = []
        for x1, y1, x2, y2, bounds, func in self._click_targets:
            bx1, by1, bx2, by2 = bounds
            inside = x1 <= event.x <= x2 and y1 <= event.y <= y2
            inside_original = bx1 <= event.x <= bx2 and by1 <= event.y <= by2
            if inside and not inside_original:
                area = (x2 - x1) * (y2 - y1)
                candidates.append((area, func))
        if candidates:
            _, func = min(candidates, key=lambda candidate: candidate[0])
            return self._invoke_clickable(func)

    def text(self, x, y, txt, size, color, weight="normal", anchor="w", tag=None, slant="roman"):
        txt = self.tr(txt)
        return self.c.create_text(x, y, text=txt, fill=color, anchor=anchor,
                                  font=self.font(size, weight, slant), tags=tag)

    def _blend_color(self, start, end, amount):
        start_rgb = self.winfo_rgb(start)
        end_rgb = self.winfo_rgb(end)
        channels = [
            round(first + (last - first) * amount) // 257
            for first, last in zip(start_rgb, end_rgb)
        ]
        return "#{:02x}{:02x}{:02x}".format(*channels)

    def list_header(self, x1, x2, y, title):
        self.text(x1, y + self.S(16), title, 18, INK, "bold")
        self.c.create_line(x1, y + self.S(38), x2, y + self.S(38), fill=BORDER)

    @staticmethod
    def _toggle_horizontal_scrollbar(canvas, scrollbar):
        if not canvas.winfo_exists() or not scrollbar.winfo_exists():
            return
        bounds = canvas.bbox("all")
        if bounds and bounds[2] > canvas.winfo_width():
            if not scrollbar.winfo_manager():
                scrollbar.pack(side="bottom", fill="x")
        elif scrollbar.winfo_manager():
            scrollbar.pack_forget()
