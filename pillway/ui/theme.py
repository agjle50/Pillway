"""Colours, fonts and sizes for the whole UI (the one theme file).

Read by: every screen file. Brand colours come from [branding] in pillway_config.toml,
so Pillway can re-skin the app without touching code.
Change a colour here only if it is NOT a brand colour (brand colours live in the config).
"""

from config import get_settings

_brand = get_settings().branding

# Brand colours (from the config file)
NAVY = _brand.navy
NAVY_DARK = _brand.navy_dark
RED = _brand.red
TEXT_DARK = _brand.text_dark
TEXT_MUTED = _brand.text_muted
BORDER = _brand.border

# Supporting colours
RED_DARK = "#d93636"
RED_TEXT = "#c42b2b"       # brand red, deepened for small text on white (5.9:1 contrast)
TEXT_SUBTLE = "#5d6880"    # timestamps and hints (still 5.6:1 on white)
BORDER_SOFT = "#e3e7ee"    # dividers inside cards
NAV_SELECTED = "#1d2570"   # selected row in the pharmacist's dark sidebar
# Pillway surfaces: a cool blue-grey canvas behind white cards.
SURFACE = "#e9edf6"
SURFACE_HIGH = "#f3f5fa"
TONAL = "#dfe3f6"          # selected item in the side menu (navy text on it: 13:1)
ORANGE = "#f28c28"
HOVER = "#f1f3f7"
SIDEBAR_BG = "#080c38"
SIDEBAR_HOVER = "#151b55"
SIDEBAR_SELECTED = "#ffffff"
SIDEBAR_TEXT = "#f4f5ff"
SIDEBAR_SELECTED_TEXT = "#ef3f3f"
AMBER = "#b26a00"
AMBER_SOFT = "#fff4e5"
GREEN = "#1e7a46"
GREEN_SOFT = "#e8f6ee"
LIVE_GREEN = "#22c55e"
RED_SOFT = "#fde8e8"
TEXT_OFF = "#8a93a6"
WHITE = "#ffffff"
SOFT_BLUE = "#eef2ff"
INK = "#101a3c"
NAV_TEXT = "#edf0ff"
NAV_ICON = "#c3cbef"
DIVIDER = "#2a3170"
SHADOW = "#e1e5ed"
TOGGLE_OFF = "#d5dae4"
CHAT_BG = "#ffffff"
PAGE_BG = "#f5f6fa"
BLACK_SIDEBAR = "#0b0b0f"
BLACK_SIDEBAR_SELECTED = "#26262e"
BLACK_SIDEBAR_TEXT = "#e9e9ef"
FOCUS = "#2563eb"

# Fonts: the first one installed on this computer wins (Windows, Mac, then Linux).
FONT_CHOICES = ("Century Gothic", "Arial Rounded MT Bold", "Segoe UI", "SF Pro Text",
                "SF Pro", "Helvetica Neue", "Arial", "DejaVu Sans")
FONT = FONT_CHOICES[0]

# The design canvas size. Everything is drawn at this size and scaled to the window.
BASE_W, BASE_H = 1500, 900
# Smallest text size in base pixels (nothing smaller is drawn: readability).
MIN_TEXT = 12
# Smallest tap target in base pixels (accessibility: at least 44 px).
MIN_TAP = 44


def pick_font(root):
    """Choose the first installed font from FONT_CHOICES. Needs a Tk window to exist."""
    global FONT
    try:
        from tkinter import font as tkfont
        installed = {name.lower() for name in tkfont.families(root)}
    except Exception:
        return FONT
    for choice in FONT_CHOICES:
        if choice.lower() in installed:
            FONT = choice
            return FONT
    FONT = "TkDefaultFont"
    return FONT
