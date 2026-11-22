"""Crisp, anti-aliased rounded boxes and circles for the Tk canvas.

Why: Tk on Windows draws shapes WITHOUT anti-aliasing, so rounded corners and circles
come out jagged ("blurry" at a glance). Here each shape is drawn by Pillow at 4x size,
shrunk to the exact pixel size with high-quality filtering, and placed as an image.
Nothing is ever stretched: every size is rendered fresh, and kept in a cache.

If Pillow isn't installed the app falls back to plain Tk shapes (still works, less crisp).
Images can't be recoloured with itemconfigure(fill=...): use recolor() instead.
"""

try:
    from PIL import Image, ImageDraw, ImageTk
except ImportError:  # pragma: no cover - depends on the computer
    Image = None

SUPERSAMPLE = 4
_cache = {}
_specs = {}  # (canvas id, item id) -> drawing spec, so shapes can be recoloured


def available():
    import os
    return Image is not None and not os.environ.get("PILLWAY_PLAIN_SHAPES")


def _rgba(colour, widget):
    if not colour:
        return None
    r, g, b = widget.winfo_rgb(colour)
    return (r // 257, g // 257, b // 257, 255)


def _render(widget, kind, width, height, radius, fill, outline, line):
    key = (kind, width, height, round(radius, 1), fill, outline, round(line, 1))
    image = _cache.get(key)
    if image is not None:
        return image
    s = SUPERSAMPLE
    big = Image.new("RGBA", (width * s, height * s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(big)
    box = [0, 0, width * s - 1, height * s - 1]
    fill_rgba, outline_rgba = _rgba(fill, widget), _rgba(outline, widget)
    line_px = max(0, round(line * s)) if outline_rgba else 0
    if kind == "oval":
        draw.ellipse(box, fill=fill_rgba, outline=outline_rgba, width=line_px)
    else:
        r = max(0, min(radius * s, (width * s) / 2, (height * s) / 2))
        draw.rounded_rectangle(box, radius=r, fill=fill_rgba, outline=outline_rgba, width=line_px)
    image = ImageTk.PhotoImage(big.resize((width, height), Image.LANCZOS), master=widget)
    if len(_cache) > 3000:
        _cache.clear()
    _cache[key] = image
    return image


def shape(canvas, kind, x1, y1, x2, y2, radius=0, fill="", outline="", width=1, tags=None, state=None):
    """Draw a crisp rounded box (kind="rect") or circle/ellipse (kind="oval"). Returns the item id."""
    left, top = round(min(x1, x2)), round(min(y1, y2))
    w, h = max(1, round(abs(x2 - x1))), max(1, round(abs(y2 - y1)))
    image = _render(canvas, kind, w, h, radius, fill or "", outline or "", float(width or 0))
    options = {"image": image, "anchor": "nw"}
    if tags:
        options["tags"] = tags
    if state:
        options["state"] = state
    item = canvas.create_image(left, top, **options)
    _specs[(str(canvas), item)] = [kind, w, h, radius, fill or "", outline or "", float(width or 0)]
    return item


def recolor(canvas, tag_or_id, fill=None, outline=None):
    """Change the colours of shapes drawn by shape() (and of ordinary canvas items)."""
    for item in canvas.find_withtag(tag_or_id):
        spec = _specs.get((str(canvas), item))
        if spec is None:
            options = {k: v for k, v in (("fill", fill), ("outline", outline)) if v is not None}
            if options:
                try:
                    canvas.itemconfigure(item, **options)
                except Exception:
                    pass
            continue
        if spec[0] != "icon" and fill is not None:
            spec[4] = fill
        if outline is not None and spec[0] != "icon":
            spec[5] = outline
        if spec[0] == "icon":  # icons: `fill` changes the icon colour (image swapped in place)
            _, paint, kind, cx, cy, size, color, bg = spec
            canvas.itemconfigure(item, image=_icon_image(canvas, paint, kind, cx, cy, size, fill or color, bg)[0])
            continue
        kind, w, h, radius, f, o, line = spec
        canvas.itemconfigure(item, image=_render(canvas, kind, w, h, radius, f, o, line))


def forget(canvas):
    """Drop remembered specs for a canvas that was cleared (canvas.delete('all'))."""
    name = str(canvas)
    for key in [k for k in _specs if k[0] == name]:
        del _specs[key]


# ---- icons ---------------------------------------------------------------------------------

def _chaikin(points, closed, rounds=3):
    """Smooth a polyline like Tk's smooth=True (corner-cutting curve)."""
    for _ in range(rounds):
        if len(points) < 3:
            return points
        out = [] if closed else [points[0]]
        seq = points + [points[0]] if closed else points
        for (x0, y0), (x1, y1) in zip(seq, seq[1:]):
            out += [(0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1), (0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1)]
        if not closed:
            out.append(points[-1])
        points = out
    return points


class IconPainter:
    """Stands in for a Tk canvas while an icon is drawn, painting onto a 4x Pillow image.

    Colours equal to the icon's background are painted as TRANSPARENT, so icons have no
    background patches: when a button turns grey on hover, the icon shows grey through.
    """
    is_painter = True

    def __init__(self, widget, left, top, width, height, bg):
        self.widget, self.left, self.top, self.k = widget, left, top, SUPERSAMPLE
        self.image = Image.new("RGBA", (width * self.k, height * self.k), (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.image)
        self.bg = bg.lower() if bg else None

    def _colour(self, colour):
        if not colour:
            return None
        if self.bg and str(colour).lower() == self.bg:
            return (0, 0, 0, 0)
        return _rgba(colour, self.widget)

    def _pts(self, coords):
        flat = [v for c in coords for v in (c if isinstance(c, (tuple, list)) else (c,))]
        return [((flat[i] - self.left) * self.k, (flat[i + 1] - self.top) * self.k) for i in range(0, len(flat) - 1, 2)]

    def _w(self, width):
        return max(1, round(float(width or 1) * self.k))

    def create_line(self, *coords, fill="black", width=1, smooth=False, capstyle=None, **_):
        pts = self._pts(coords)
        if smooth:
            pts = _chaikin(pts, closed=False)
        colour, w = self._colour(fill), self._w(width)
        self.draw.line(pts, fill=colour, width=w, joint="curve")
        if capstyle == "round" and colour:
            r = w / 2
            for x, y in (pts[0], pts[-1]):
                self.draw.ellipse([x - r, y - r, x + r, y + r], fill=colour)

    def create_oval(self, *coords, fill="", outline="black", width=1, **_):
        (x1, y1), (x2, y2) = self._pts(coords)
        self.draw.ellipse([x1, y1, x2, y2], fill=self._colour(fill), outline=self._colour(outline),
                          width=self._w(width) if outline else 0)

    def create_rectangle(self, *coords, fill="", outline="black", width=1, **_):
        (x1, y1), (x2, y2) = self._pts(coords)
        self.draw.rectangle([x1, y1, x2, y2], fill=self._colour(fill), outline=self._colour(outline),
                            width=self._w(width) if outline else 0)

    def create_arc(self, *coords, start=0, extent=90, outline="black", width=1, style="arc", **_):
        (x1, y1), (x2, y2) = self._pts(coords)
        start, extent = float(start), float(extent)
        a, b = -(start + extent), -start  # Tk: counter-clockwise; Pillow: clockwise
        self.draw.arc([x1, y1, x2, y2], a, b, fill=self._colour(outline), width=self._w(width))

    def create_polygon(self, *coords, fill="", outline="", width=1, smooth=False, **_):
        pts = self._pts(coords)
        if smooth:
            pts = _chaikin(pts, closed=True)
        if fill:
            self.draw.polygon(pts, fill=self._colour(fill))
        if outline:
            self.draw.line(pts + [pts[0]], fill=self._colour(outline), width=self._w(width), joint="curve")

    def create_round_rect(self, x1, y1, x2, y2, r, fill="", outline="", width=1, **_):
        (a, b), (c, d) = self._pts((x1, y1, x2, y2))
        self.draw.rounded_rectangle([a, b, c, d], radius=r * self.k, fill=self._colour(fill),
                                    outline=self._colour(outline), width=self._w(width) if outline else 0)

    def create_text(self, x, y, text="", fill="black", font=None, **_):
        from PIL import ImageFont
        from pathlib import Path
        size = abs(int(font[1])) if font and len(font) > 1 else 12
        bold = font and "bold" in font[2:]
        folder = Path(__file__).resolve().parents[2] / "assets" / "fonts"
        try:
            face = ImageFont.truetype(str(folder / ("PillwaySans-Bold.ttf" if bold else "PillwaySans-Regular.ttf")),
                                      max(1, size * self.k))
        except OSError:
            face = ImageFont.load_default()
        (px, py), = self._pts((x, y))
        self.draw.text((px, py), text, fill=self._colour(fill), font=face, anchor="mm")

    def finish(self, width, height):
        return self.image.resize((width, height), Image.LANCZOS)


def _icon_image(canvas, paint, kind, cx, cy, size, color, bg):
    pad = max(2, size * 0.15)
    left, top = round(cx - size / 2 - pad), round(cy - size / 2 - pad)
    width = height = max(1, round(size + 2 * pad))
    offset = (round((cx - left) * 4), round((cy - top) * 4))
    cache_key = ("icon", kind, round(size, 2), color, bg, width, offset)
    image = _cache.get(cache_key)
    if image is None:
        painter = IconPainter(canvas, left, top, width, height, bg)
        paint(painter, kind, cx, cy, size, color, bg)
        image = ImageTk.PhotoImage(painter.finish(width, height), master=canvas)
        _cache[cache_key] = image
    return image, left, top


def icon(canvas, paint, kind, cx, cy, size, color, bg, tags=None):
    """Draw icon `kind` as a crisp image centred on (cx, cy).

    paint(target, kind, cx, cy, size, color, bg) draws it using Tk-canvas-style calls.
    """
    image, left, top = _icon_image(canvas, paint, kind, cx, cy, size, color, bg)
    options = {"image": image, "anchor": "nw"}
    if tags:
        options["tags"] = tags
    item = canvas.create_image(left, top, **options)
    _specs[(str(canvas), item)] = ["icon", paint, kind, cx, cy, size, color, bg]
    return item
