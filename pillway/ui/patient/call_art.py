"""Artwork for the call screen, drawn with Pillow (crisp at any size, nothing stretched).

Called by: ui/patient/call.py. Everything is drawn at 4x and shrunk with high-quality
filtering, then cached. If Pillow is missing the call screen falls back to plain shapes.

- background(w, h): warm Pillway gradient with two soft light glows.
- glass(background, box): Apple-style "liquid glass" bar: the background behind it, blurred,
  frosted with white, a bright top edge, a thin light rim and a soft shadow.
- avatar(size, mouth_open): Sarah, an original illustrated character (blonde, navy top).
"""

from functools import lru_cache

try:
    from PIL import Image, ImageChops, ImageDraw, ImageFilter
except ImportError:  # pragma: no cover
    Image = None

TOP = (245, 128, 62)      # warm orange
BOTTOM = (227, 67, 42)    # Pillway red-orange (#e3432a)
NAVY = (6, 7, 37)


def available():
    return Image is not None


def _rounded_mask(size, radius, scale=4):
    w, h = size
    big = Image.new("L", (w * scale, h * scale), 0)
    ImageDraw.Draw(big).rounded_rectangle([0, 0, w * scale - 1, h * scale - 1], radius=radius * scale, fill=255)
    return big.resize((w, h), Image.LANCZOS)


@lru_cache(maxsize=8)
def background(width, height, radius=8):
    """Vertical gradient with soft glows; corners rounded to match the app's cards."""
    width, height = max(1, width), max(1, height)
    column = Image.new("RGB", (1, 256))
    for y in range(256):
        t = y / 255
        column.putpixel((0, y), tuple(round(a + (b - a) * t) for a, b in zip(TOP, BOTTOM)))
    image = column.resize((width, height), Image.BICUBIC).convert("RGBA")
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    for cx, cy, r, alpha in ((0.22, 0.18, 0.42, 60), (0.82, 0.78, 0.38, 45)):
        x, y, rr = cx * width, cy * height, r * max(width, height)
        draw.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(255, 214, 170, alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(max(width, height) * 0.08))
    image = Image.alpha_composite(image, glow)
    image.putalpha(_rounded_mask((width, height), radius))
    return image


def glass(base, box, radius):
    """A frosted-glass panel for `box` (x1, y1, x2, y2) over the `base` image. Returns (image, offset)."""
    x1, y1, x2, y2 = (round(v) for v in box)
    pad = max(8, round(radius * 0.6))            # room for the soft shadow
    w, h = x2 - x1, y2 - y1
    out = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))

    shadow = Image.new("RGBA", out.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([pad, pad + pad * 0.45, pad + w, pad + h + pad * 0.45],
                                             radius=radius, fill=(120, 30, 10, 70))
    out = Image.alpha_composite(out, shadow.filter(ImageFilter.GaussianBlur(pad * 0.55)))

    behind = base.crop((x1, y1, x2, y2)).convert("RGBA").filter(ImageFilter.GaussianBlur(14))
    frost = Image.new("RGBA", (w, h), (255, 255, 255, 58))
    panel = Image.alpha_composite(behind, frost)
    # bright top sheen fading down (the "liquid" highlight)
    sheen = Image.new("L", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        sheen.putpixel((0, y), round(90 * max(0.0, 1 - t / 0.55) ** 2))
    panel = Image.alpha_composite(panel, Image.merge("RGBA", [Image.new("L", (w, h), 255)] * 3
                                                     + [sheen.resize((w, h))]))
    mask = _rounded_mask((w, h), radius)
    panel.putalpha(mask)
    out.alpha_composite(panel, (pad, pad))

    # thin light rim, brighter on top: reads as a glass edge
    s = 4
    rim = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rim)
    rd.rounded_rectangle([1, 1, w * s - 2, h * s - 2], radius=radius * s, outline=(255, 255, 255, 150), width=int(1.4 * s))
    fade = Image.new("L", (1, h * s))
    for y in range(h * s):
        fade.putpixel((0, y), round(255 - 150 * (y / (h * s))))
    rim.putalpha(ImageChops.multiply(rim.getchannel("A"), fade.resize((w * s, h * s))))
    out.alpha_composite(rim.resize((w, h), Image.LANCZOS), (pad, pad))
    return out, (x1 - pad, y1 - pad)


def glass_circle(size, fill, alpha):
    """A small round glass button (frosted white) or a solid one (e.g. the red End button)."""
    s = 4
    big = Image.new("RGBA", (size * s, size * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    d.ellipse([0, 0, size * s - 1, size * s - 1], fill=fill + (alpha,))
    if alpha < 200:  # frosted: add a light rim and a top sheen
        d.ellipse([s, s, size * s - s - 1, size * s - s - 1], outline=(255, 255, 255, 130), width=int(1.2 * s))
        sheen = Image.new("RGBA", big.size, (0, 0, 0, 0))
        ImageDraw.Draw(sheen).ellipse([size * s * 0.2, size * s * 0.08, size * s * 0.8, size * s * 0.42],
                                      fill=(255, 255, 255, 34))
        big = Image.alpha_composite(big, sheen.filter(ImageFilter.GaussianBlur(size * s * 0.05)))
    return big.resize((size, size), Image.LANCZOS)


@lru_cache(maxsize=16)
def avatar(size, mouth_open=False):
    """Sarah: an original friendly cartoon (blonde, navy Pillway top), in a white circle."""
    s = 4
    S = size * s
    u = S / 200.0                      # draw on a 200 x 200 grid

    def box(x1, y1, x2, y2):
        return [x1 * u, y1 * u, x2 * u, y2 * u]

    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse(box(0, 0, 200, 200), fill=(255, 246, 238, 255))          # backdrop
    art = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    a = ImageDraw.Draw(art)
    hair, hair_dark, hair_light = (238, 192, 98), (214, 158, 70), (251, 222, 150)
    skin, skin_shade = (250, 213, 184), (238, 188, 156)

    a.rounded_rectangle(box(44, 70, 156, 190), radius=40 * u, fill=hair_dark)      # long hair behind
    a.ellipse(box(40, 34, 160, 150), fill=hair)
    a.rectangle(box(88, 138, 112, 166), fill=skin_shade)                            # neck
    a.ellipse(box(26, 158, 174, 260), fill=NAVY + (255,))                           # navy top
    a.polygon([(84 * u, 160 * u), (100 * u, 182 * u), (116 * u, 160 * u)], fill=(255, 255, 255, 255))
    a.ellipse(box(60, 56, 140, 150), fill=skin)                                     # face
    # hair framing the face (covers the ears), longer on her left
    a.rounded_rectangle(box(50, 70, 70, 168), radius=10 * u, fill=hair)
    a.rounded_rectangle(box(131, 70, 151, 160), radius=10 * u, fill=hair)
    # side-swept fringe from a part on her right, with a soft highlight
    a.pieslice(box(54, 38, 150, 122), 185, 300, fill=hair)
    a.polygon([(112 * u, 44 * u), (60 * u, 64 * u), (58 * u, 96 * u), (78 * u, 76 * u), (104 * u, 70 * u),
               (128 * u, 58 * u)], fill=hair)
    a.polygon([(112 * u, 44 * u), (146 * u, 62 * u), (148 * u, 92 * u), (126 * u, 64 * u)], fill=hair)
    a.line([(112 * u, 44 * u), (118 * u, 60 * u)], fill=hair_dark, width=int(2 * u))
    a.arc(box(64, 42, 128, 96), 205, 285, fill=hair_light, width=int(5 * u))
    # brows, eyes with highlights
    for x in (80, 120):
        a.arc(box(x - 11, 84, x + 11, 96), 200, 340, fill=(176, 122, 62), width=int(3.2 * u))
        a.ellipse(box(x - 6.5, 96, x + 6.5, 112), fill=(28, 34, 74))
        a.ellipse(box(x - 2.5, 98.5, x + 1.5, 102.5), fill=(255, 255, 255))
    # cheeks
    blush = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    bd = ImageDraw.Draw(blush)
    for x in (74, 126):
        bd.ellipse(box(x - 10, 114, x + 10, 126), fill=(246, 150, 140, 110))
    art = Image.alpha_composite(art, blush.filter(ImageFilter.GaussianBlur(3 * u)))
    a = ImageDraw.Draw(art)
    a.arc(box(94, 104, 106, 120), 300, 60, fill=skin_shade, width=int(2.6 * u))      # nose
    if mouth_open:
        a.chord(box(88, 120, 112, 140), 0, 180, fill=(150, 52, 60))
        a.chord(box(93, 130, 107, 140), 0, 180, fill=(232, 112, 116))
    else:
        a.arc(box(86, 112, 114, 134), 25, 155, fill=(176, 70, 72), width=int(3.4 * u))
    circle = Image.new("L", (S, S), 0)
    ImageDraw.Draw(circle).ellipse(box(0, 0, 200, 200), fill=255)
    art.putalpha(ImageChops.multiply(art.getchannel("A"), circle))
    img = Image.alpha_composite(img, art)
    return img.resize((size, size), Image.LANCZOS)
