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

# Supporting colours (matched to Pillway's site: navy sidebar, white cards, red-orange accent)
RED_DARK = "#c7361f"
RED_TEXT = "#c7361f"       # the accent red, deepened for small text on white (4.9:1 contrast)
TEXT_SUBTLE = "#65667b"    # timestamps and hints (5.3:1 on white)
BORDER_SOFT = "#ececef"    # dividers inside cards
NAV_SELECTED = "#1b1d4a"   # selected row in the pharmacist's dark patient sidebar
SURFACE = "#ffffff"        # window background (Pillway's pages are white)
SURFACE_HIGH = "#f5f5f7"   # quiet fills: assistant bubbles, message box
TONAL = "#f0f0f3"
ORANGE = "#e3432a"
HOVER = "#eeeef1"          # grey shown under the pointer (buttons, menu rows)
SIDEBAR_BG = "#060725"
SIDEBAR_HOVER = "#14163f"
SIDEBAR_SELECTED = "#ffffff"
SIDEBAR_TEXT = "#ffffff"
SIDEBAR_SELECTED_TEXT = "#e3432a"
SIDEBAR_DIVIDER = "#3a3b5c"
AMBER = "#9a5b00"
AMBER_SOFT = "#fff4e5"
GREEN = "#1e7a46"
GREEN_SOFT = "#e8f6ee"
LIVE_GREEN = "#22c55e"
RED_SOFT = "#fdecea"
TEXT_OFF = "#8a8b9c"
WHITE = "#ffffff"
SOFT_BLUE = "#eef0f8"
INK = "#09173a"            # names and strong text
NAV_TEXT = "#ffffff"
NAV_ICON = "#e6e6ee"
DIVIDER = "#3a3b5c"
SHADOW = "#e6e6ea"
TOGGLE_OFF = "#d5d6de"
CHAT_BG = "#ffffff"
PAGE_BG = "#ffffff"
BLACK_SIDEBAR = "#060725"
BLACK_SIDEBAR_SELECTED = "#1b1d4a"
BLACK_SIDEBAR_TEXT = "#ffffff"
FOCUS = "#2563eb"
RADIUS = 8                 # corner radius for buttons, inputs and cards (base pixels)

# Fonts: the first one installed on this computer wins (Windows, Mac, then Linux).
# "Pillway Sans" is the bundled font (Montserrat, renamed; see pillway/assets/fonts). It is
# loaded into this app only (not installed on the computer) by load_bundled_fonts().
FONT_CHOICES = ("Pillway Sans", "Montserrat", "Century Gothic", "Segoe UI", "SF Pro Text",
                "SF Pro", "Helvetica Neue", "Arial", "DejaVu Sans")
FONT = FONT_CHOICES[0]

# The design canvas size. Everything is drawn at this size and scaled to the window.
BASE_W, BASE_H = 1500, 900
# Smallest text size in base pixels (nothing smaller is drawn: readability).
MIN_TEXT = 12
# Smallest tap target in base pixels (accessibility: at least 44 px).
MIN_TAP = 44


def load_bundled_fonts():
    """Make the bundled font usable by this app (Windows: private to this process).

    Call before the Tk window is created. On Mac/Linux the font falls back to the system's.
    """
    import sys
    from pathlib import Path
    folder = Path(__file__).resolve().parent.parent / "assets" / "fonts"
    if sys.platform != "win32":
        return
    try:
        import ctypes
        for path in folder.glob("*.ttf"):
            ctypes.windll.gdi32.AddFontResourceExW(str(path), 0x10, 0)  # 0x10 = FR_PRIVATE
    except Exception:
        pass


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
