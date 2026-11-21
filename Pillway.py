"""Pillway desktop UI mockup.

Everything is drawn as vectors on a single tkinter Canvas and redrawn on every
resize, so the whole interface scales cleanly to any window size.
"""
import math
import ctypes
import sys
import tkinter as tk


def enable_high_dpi():
    """Keep every Tk canvas primitive at the screen's physical resolution."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass

# ---------------------------------------------------------------- colours ----
NAVY = "#0a0f42"
NAVY_DARK = "#080c38"
RED = "#ef3f3f"
RED_DARK = "#d93636"
TEXT_DARK = "#4a566f"
TEXT_MUTED = "#768197"
TEXT_OFF = "#b4bccb"
BORDER = "#dde2ea"
WHITE = "#ffffff"
SOFT_BLUE = "#eef2ff"
INK = "#101a3c"
NAV_TEXT = "#edf0ff"
NAV_ICON = "#9da9dc"
DIVIDER = "#9098b8"
SHADOW = "#e8ebf2"
TOGGLE_OFF = "#d5dae4"

FONT = "Segoe UI"
BASE_W, BASE_H = 1500, 900  # design size; everything scales from this

# Easy-to-find placeholder copy for the first-launch banner.
VIRTUAL_ASSISTANT_POPUP_TEXT = (
    "Get a virtual assistant doctor to help you discover your condition today, live."
)

# None = divider line in the sidebar
NAV_ITEMS = [
    ("Dashboard", "grid"),
    ("Settings", "gear"),
    ("Manage profiles", "person"),
    None,
    ("Medications", "pills"),
    ("Prescription", "rx"),
    ("See a doctor", "stethoscope"),
    ("Orders", "order"),
    ("Tasks", "task"),
    None,
    ("Contact us", "phone"),
    ("Account tour", "bulb"),
    ("FAQ", "question"),
]

# Top selection bar (like the tab bar in the iOS Clock app, moved to the top)
TABS = [
    ("Check up", "heart"),
    ("Medications", "pills"),
    ("Orders", "box"),
    ("Tasks", "task"),
]

SETTINGS_ITEMS = [
    ("Profile settings", "person"),
    ("Account settings", "lock"),
    ("Payment method", "card"),
    ("Promotions", "tag"),
    ("Referral code", "ticket"),
    ("Notifications", "bell"),
    ("Account tour", "bulb"),
    ("Info and legal", "doc"),
]

NOTIFICATIONS = [
    ("Weekly check-in is ready", "Foot-care week. Takes 2 minutes."),
    ("Reminder", "Check your blood sugar at 8:00 AM."),
    ("Order shipped", "Order #1057 is on its way."),
]

ORDERS = [
    ("Order #1063", "Glucose sensors  ·  Processing", "Processing"),
    ("Order #1057", "Test strips  ·  Shipped Nov 20", "Shipped"),
    ("Order #1042", "Monthly refill  ·  Delivered Nov 18", "Delivered"),
]


class PillwayApp(tk.Tk):
    def __init__(self):
        enable_high_dpi()
        super().__init__()
        self.title("Pillway")
        self.geometry("1500x900")
        self.minsize(900, 560)
        self.configure(bg=WHITE)

        self.c = tk.Canvas(self, bg=WHITE, highlightthickness=0, bd=0)
        self.c.pack(fill="both", expand=True)

        # UI state
        self.section = "Dashboard"
        self.tab = "Check up"
        self.banner = True
        self.dropdown = None          # None | "notifications" | "profile"
        self.anim = 1.0               # 0 -> 1 slide-in for the Check up bars
        self.status = ""              # small message under Check up bars
        self.prescriptions = []
        self.tasks = [                # alarm-style reminders
            ["8:00", "AM", "Check blood sugar", True],
            ["9:00", "AM", "Foot check", True],
            ["12:30", "PM", "15-minute walk", False],
            ["7:00", "PM", "Log dinner", False],
        ]

        self._job = None
        self.c.bind("<Configure>", self._schedule_render)
        self.after(50, lambda: self.select_tab("Check up"))

    # ------------------------------------------------------------ helpers ---
    def _schedule_render(self, _event=None):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(10, self.render)

    def S(self, v):
        return v * self.s

    def font(self, size, weight="normal", slant="roman"):
        return (FONT, -max(1, round(size * self.s)), weight, slant)

    def rrect(self, x1, y1, x2, y2, r, **kw):
        r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return self.c.create_polygon(pts, smooth=True, **kw)

    def clickable(self, tag, func):
        self.c.tag_bind(tag, "<Button-1>", lambda e: func())
        self.c.tag_bind(tag, "<Enter>", lambda e: self.c.configure(cursor="hand2"))
        self.c.tag_bind(tag, "<Leave>", lambda e: self.c.configure(cursor=""))

    def text(self, x, y, txt, size, color, weight="normal", anchor="w", tag=None, slant="roman"):
        return self.c.create_text(x, y, text=txt, fill=color, anchor=anchor,
                                  font=self.font(size, weight, slant), tags=tag)

    # ------------------------------------------------------------- render ---
    def render(self):
        self._job = None
        c = self.c
        c.delete("all")
        w, h = max(c.winfo_width(), 1), max(c.winfo_height(), 1)
        self.w, self.h = w, h
        self.s = min(w / BASE_W, h / BASE_H)
        self.sw = self.S(300)  # sidebar width

        self.draw_sidebar()
        self.draw_header()
        if self.section == "Dashboard":
            self.draw_dashboard()
        elif self.section == "Settings":
            self.draw_settings()
        else:
            self.draw_placeholder_page(self.section)
        if self.dropdown:
            self.draw_dropdown()

    # ------------------------------------------------------------ sidebar ---
    def draw_sidebar(self):
        c, s, sw, h = self.c, self.s, self.sw, self.h
        c.create_rectangle(0, 0, sw, h, fill=NAVY, outline=NAVY)
        c.create_rectangle(0, 0, sw, self.S(100), fill=NAVY_DARK, outline=NAVY_DARK)
        self.text(sw / 2, self.S(50), "Pillway", 38, WHITE, "bold", anchor="center")
        c.create_line(0, self.S(100), sw, self.S(100), fill=DIVIDER)

        y = self.S(104)
        row_h = self.S(60)
        for item in NAV_ITEMS:
            if item is None:
                y += self.S(6)
                c.create_line(0, y, sw, y, fill=DIVIDER)
                y += self.S(8)
                continue
            label, icon = item
            tag = f"nav::{label}"
            selected = label == self.section
            bg = WHITE if selected else NAVY
            fg = RED if selected else NAV_TEXT
            ic = RED if selected else NAV_ICON
            c.create_rectangle(0, y, sw, y + row_h, fill=bg, outline=bg, tags=tag)
            self.draw_icon(icon, self.S(32), y + row_h / 2, self.S(26), ic, tag, bg=bg)
            self.text(self.S(62), y + row_h / 2, label, 16, fg,
                      "bold" if selected else "normal", tag=tag)
            self.clickable(tag, lambda l=label: self.go(l))
            y += row_h

    # ------------------------------------------------------------- header ---
    def draw_header(self):
        c, w = self.c, self.w
        top = self.S(18)
        size = self.S(54)

        if self.section == "Dashboard":
            self.text(self.sw + self.S(28), top + size / 2, "Dashboard", 28, TEXT_DARK, "bold")

        # profile (circle avatar + name + chevron), right aligned
        cy = top + size / 2
        self.draw_icon("chev_down", w - self.S(34), cy, self.S(22), INK, "profile")
        name = self.text(w - self.S(54), cy, "Team AGILE", 17, INK, "bold", anchor="e", tag="profile")
        nx1 = c.bbox(name)[0]
        r = self.S(27)
        ax = nx1 - self.S(14) - r
        c.create_oval(ax - r, cy - r, ax + r, cy + r, fill="#080b32", outline="#080b32", tags="profile")
        self.text(ax, cy, "T A", 16, WHITE, "bold", anchor="center", tag="profile")
        self.clickable("profile", lambda: self.toggle_dropdown("profile"))

        # credit card (payments) and bell (notifications): beveled rectangles
        card_x2 = ax - r - self.S(24)
        self.beveled_button(card_x2 - size, top, card_x2, top + size, "card", "payments",
                            lambda: self.go("Payments"))
        bell_x2 = card_x2 - size - self.S(14)
        self.beveled_button(bell_x2 - size, top, bell_x2, top + size, "bell", "bell",
                            lambda: self.toggle_dropdown("notifications"))
        # unread dot
        d = self.S(7)
        c.create_oval(bell_x2 - d * 1.6, top - d * 0.4, bell_x2 + d * 0.4, top + d * 1.6,
                      fill=RED, outline=WHITE, width=self.S(2), tags="bell")
        self.bell_box = (bell_x2 - size, top + size)
        self.profile_box = (ax - r, top + size)

    def beveled_button(self, x1, y1, x2, y2, icon, tag, func):
        rad = self.S(14)
        # bevel: soft shadow underneath, light top highlight inside
        self.rrect(x1, y1 + self.S(3), x2, y2 + self.S(3), rad, fill=SHADOW, outline="", tags=tag)
        self.rrect(x1, y1, x2, y2, rad, fill=WHITE, outline="#d7dbe5", width=self.S(1.5), tags=tag)
        self.c.create_line(x1 + rad, y1 + self.S(2.5), x2 - rad, y1 + self.S(2.5),
                           fill="#f7f8fb", width=self.S(2), tags=tag)
        self.draw_icon(icon, (x1 + x2) / 2, (y1 + y2) / 2, self.S(26), INK, tag)
        self.clickable(tag, func)

    # ----------------------------------------------------------- dashboard ---
    def panel_box(self):
        return (self.sw + self.S(14), self.S(92), self.w - self.S(14), self.h - self.S(14))

    def draw_dashboard(self):
        px1, py1, px2, py2 = self.panel_box()
        self.rrect(px1, py1, px2, py2, self.S(16), fill=WHITE, outline=BORDER, width=self.S(1.2))
        pcx = (px1 + px2) / 2

        # selection bar with icons, at the top of the screen
        gap = self.S(150)
        for i, (name, icon) in enumerate(TABS):
            x = pcx + (i - (len(TABS) - 1) / 2) * gap
            tag = f"tab::{name}"
            sel = name == self.tab
            col = RED if sel else TEXT_MUTED
            self.c.create_rectangle(x - gap / 2 + self.S(6), py1 + self.S(8), x + gap / 2 - self.S(6),
                                    py1 + self.S(96), fill=WHITE, outline=WHITE, tags=tag)
            self.draw_icon(icon, x, py1 + self.S(40), self.S(32), col, tag)
            self.text(x, py1 + self.S(76), name, 14, col, "bold" if sel else "normal",
                      anchor="center", tag=tag)
            if sel:
                self.rrect(x - self.S(26), py1 + self.S(92), x + self.S(26), py1 + self.S(96),
                           self.S(2), fill=RED, outline="", tags=tag)
            self.clickable(tag, lambda n=name: self.select_tab(n))
        self.c.create_line(px1, py1 + self.S(98), px2, py1 + self.S(98), fill=BORDER)

        y = py1 + self.S(118)
        if self.banner:
            bw = min(self.S(700), px2 - px1 - self.S(60))
            bx1, bx2 = pcx - bw / 2, pcx + bw / 2
            self.rrect(bx1, y, bx2, y + self.S(56), self.S(14), fill=NAVY_DARK, outline="")
            self.text(bx1 + self.S(22), y + self.S(28), VIRTUAL_ASSISTANT_POPUP_TEXT, 14, WHITE)
            self.c.create_oval(bx2 - self.S(36), y + self.S(14), bx2 - self.S(8), y + self.S(42),
                               fill=NAVY_DARK, outline="", tags="banner_x")
            self.draw_icon("close", bx2 - self.S(22), y + self.S(28), self.S(16), WHITE, "banner_x")
            self.clickable("banner_x", self.close_banner)
            y += self.S(80)
        else:
            y += self.S(10)

        content_w = min(self.S(820), px2 - px1 - self.S(80))
        x1, x2 = pcx - content_w / 2, pcx + content_w / 2
        {"Check up": self.draw_checkup, "Medications": self.draw_medications,
         "Orders": self.draw_orders, "Tasks": self.draw_tasks}[self.tab](x1, x2, y)

    def draw_checkup(self, x1, x2, y):
        self.text((x1 + x2) / 2, y + self.S(14), "How would you like to check in?", 20, INK,
                  "bold", anchor="center")
        y += self.S(48)
        bars = [("Call", "phone", "Talk to a Pillway pharmacist now"),
                ("Chat", "chat", "Message your care assistant, any time")]
        bh = self.S(104)
        for i, (title, icon, sub) in enumerate(bars):
            off = (1 - self.anim) * self.S(70) * (i + 1)
            by = y + i * (bh + self.S(22)) + off
            tag = f"bar::{title}"
            self.rrect(x1, by + self.S(4), x2, by + bh + self.S(4), self.S(20), fill=SHADOW, outline="", tags=tag)
            self.rrect(x1, by, x2, by + bh, self.S(20), fill=WHITE, outline=BORDER, width=self.S(1.2), tags=tag)
            cx, cy, r = x1 + self.S(56), by + bh / 2, self.S(30)
            self.c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=RED, outline="", tags=tag)
            self.draw_icon(icon, cx, cy, self.S(28), WHITE, tag, bg=RED)
            self.text(x1 + self.S(106), cy - self.S(14), title, 26, INK, "bold", tag=tag)
            self.text(x1 + self.S(106), cy + self.S(20), sub, 14, TEXT_MUTED, tag=tag)
            self.draw_icon("chev_right", x2 - self.S(34), cy, self.S(24), TEXT_MUTED, tag)
            self.clickable(tag, lambda t=title: self.checkup_choice(t))
        if self.status and self.anim >= 1:
            self.text((x1 + x2) / 2, y + 2 * bh + self.S(60), self.status, 14, TEXT_MUTED, anchor="center")

    def draw_medications(self, x1, x2, y):
        cw = min(self.S(580), x2 - x1)
        cx1 = (x1 + x2) / 2 - cw / 2
        cx2 = cx1 + cw
        ch = self.S(140)
        self.rrect(cx1, y + self.S(5), cx2, y + ch + self.S(5), self.S(22), fill=SHADOW, outline="")
        self.rrect(cx1, y, cx2, y + ch, self.S(22), fill=WHITE, outline=BORDER, width=self.S(1.2))
        self.text(cx1 + self.S(28), y + self.S(40), "Hi! I'm Sarah. How can I help you today?",
                  16, TEXT_MUTED, slant="italic")
        # add prescription button
        bx1, by1 = cx1 + self.S(18), y + ch - self.S(58)
        bx2, by2 = bx1 + self.S(176), y + ch - self.S(18)
        self.rrect(bx1, by1, bx2, by2, self.S(10), fill=RED, outline="", tags="addrx")
        self.draw_icon("plus", bx1 + self.S(22), (by1 + by2) / 2, self.S(18), WHITE, "addrx")
        self.text(bx1 + self.S(40), (by1 + by2) / 2, "Add prescription", 14, WHITE, "bold", tag="addrx")
        self.clickable("addrx", self.add_prescription)
        # mic + send
        my = (by1 + by2) / 2
        self.draw_icon("mic", cx2 - self.S(92), my, self.S(26), RED, "mic")
        r = self.S(20)
        sx = cx2 - self.S(42)
        self.c.create_oval(sx - r, my - r, sx + r, my + r, fill=RED, outline="", tags="send")
        self.draw_icon("send", sx + self.S(1), my, self.S(20), WHITE, "send", bg=RED)

        y += ch + self.S(40)
        if not self.prescriptions:
            self.text((x1 + x2) / 2, y + self.S(10), "Let's add your first prescription!", 15,
                      TEXT_MUTED, anchor="center")
        else:
            self.list_header(x1, x2, y, "Your prescriptions")
            y += self.S(40)
            for name in self.prescriptions:
                self.text(x1 + self.S(6), y + self.S(36), name, 26, INK)
                self.text(x1 + self.S(6), y + self.S(66), "Added today", 13, TEXT_MUTED)
                y += self.S(90)
                self.c.create_line(x1, y, x2, y, fill=BORDER)

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

    def draw_tasks(self, x1, x2, y):
        # Looks like the iOS Alarm list: big times, labels, toggles
        self.draw_icon("bulb", x1 + self.S(14), y + self.S(14), self.S(22), INK, None)
        self.text(x1 + self.S(34), y + self.S(14), "Daily care plan", 18, INK, "bold")
        self.c.create_line(x1, y + self.S(36), x2, y + self.S(36), fill=BORDER)
        y += self.S(36)
        for i, (time, ampm, label, on) in enumerate(self.tasks):
            col = INK if on else TEXT_OFF
            t = self.text(x1 + self.S(6), y + self.S(44), time, 46, col, "normal")
            tx2 = self.c.bbox(t)[2]
            self.text(tx2 + self.S(4), y + self.S(54), ampm, 20, col)
            self.text(x1 + self.S(8), y + self.S(84), label, 14, TEXT_MUTED if on else TEXT_OFF)
            self.toggle(x2 - self.S(70), y + self.S(50), on, f"toggle::{i}", lambda k=i: self.flip_task(k))
            y += self.S(106)
            self.c.create_line(x1, y, x2, y, fill=BORDER)

    def list_header(self, x1, x2, y, title):
        self.text(x1, y + self.S(16), title, 18, INK, "bold")
        self.c.create_line(x1, y + self.S(38), x2, y + self.S(38), fill=BORDER)

    def toggle(self, x, cy, on, tag, func):
        w, h = self.S(68), self.S(40)
        self.rrect(x, cy - h / 2, x + w, cy + h / 2, h / 2, fill=RED if on else TOGGLE_OFF,
                   outline="", tags=tag)
        r = h / 2 - self.S(3)
        kx = x + w - h / 2 if on else x + h / 2
        self.c.create_oval(kx - r, cy - r + self.S(1.5), kx + r, cy + r + self.S(1.5),
                           fill="#c4c9d4", outline="", tags=tag)
        self.c.create_oval(kx - r, cy - r, kx + r, cy + r, fill=WHITE, outline="", tags=tag)
        self.clickable(tag, func)

    # ------------------------------------------------------------ settings ---
    def page_title(self, title):
        y = self.S(120)
        self.c.create_rectangle(self.sw + self.S(18), y - self.S(20), self.sw + self.S(56),
                                y + self.S(20), fill=WHITE, outline=WHITE, tags="back")
        self.draw_icon("back", self.sw + self.S(36), y, self.S(26), INK, "back")
        self.clickable("back", lambda: self.go("Dashboard"))
        self.text(self.sw + self.S(70), y, title, 22, INK)
        self.c.create_line(self.sw, y + self.S(36), self.w, y + self.S(36), fill=BORDER)
        return y + self.S(36)

    def draw_settings(self):
        y = self.page_title("Settings")
        x1 = self.sw + self.S(20)
        x2 = x1 + min(self.S(520), self.w - x1 - self.S(20))
        row = self.S(70)
        for label, icon in SETTINGS_ITEMS:
            tag = f"set::{label}"
            self.c.create_rectangle(x1, y, x2, y + row, fill=WHITE, outline=WHITE, tags=tag)
            self.draw_icon(icon, x1 + self.S(16), y + row / 2, self.S(26), INK, tag)
            self.text(x1 + self.S(46), y + row / 2, label, 17, INK, tag=tag)
            self.draw_icon("chev_right", x2 - self.S(20), y + row / 2, self.S(16), TEXT_MUTED, tag)
            self.c.create_line(x1, y + row, x2, y + row, fill=BORDER)
            self.clickable(tag, lambda: None)  # sections have no UI inside yet
            y += row

    def draw_placeholder_page(self, title):
        y = self.page_title(title)
        cx = (self.sw + self.w) / 2
        cy = (y + self.h) / 2
        msg = "Payments are made here." if title == "Payments" else f"{title} will appear here."
        self.text(cx, cy, msg, 16, TEXT_MUTED, anchor="center")

    # ------------------------------------------------------------ dropdown ---
    def draw_dropdown(self):
        if self.dropdown == "notifications":
            items = NOTIFICATIONS
            x2 = self.bell_box[0] + self.S(330)
            title = "Notifications"
        else:
            items = [("Manage profiles", "Switch between family members"),
                     ("Settings", "Account, payments, notifications"),
                     ("Sign out", "")]
            x2 = self.w - self.S(18)
            title = "Team AGILE"
        top = self.S(86)
        dw = self.S(340)
        x1 = x2 - dw
        rh = self.S(66)
        y2 = top + self.S(56) + rh * len(items)
        self.rrect(x1, top + self.S(5), x2, y2 + self.S(5), self.S(16), fill=SHADOW, outline="")
        self.rrect(x1, top, x2, y2, self.S(16), fill=WHITE, outline=BORDER, width=self.S(1.2))
        self.text(x1 + self.S(20), top + self.S(28), title, 16, INK, "bold")
        y = top + self.S(56)
        for head, sub in items:
            tag = f"dd::{head}"
            self.c.create_line(x1 + self.S(16), y, x2 - self.S(16), y, fill=BORDER)
            self.c.create_rectangle(x1 + self.S(2), y + 1, x2 - self.S(2), y + rh - 1,
                                    fill=WHITE, outline=WHITE, tags=tag)
            if sub:
                self.text(x1 + self.S(20), y + self.S(22), head, 14, INK, "bold", tag=tag)
                self.text(x1 + self.S(20), y + self.S(46), sub, 13, TEXT_MUTED, tag=tag)
            else:
                self.text(x1 + self.S(20), y + rh / 2, head, 14, RED, "bold", tag=tag)
            if self.dropdown == "profile" and head in ("Manage profiles", "Settings"):
                self.clickable(tag, lambda h=head: self.go(h))
            else:
                self.clickable(tag, lambda: self.toggle_dropdown(None))
            y += rh

    # ------------------------------------------------------------- actions ---
    def go(self, section):
        self.section = section
        self.dropdown = None
        if section == "Dashboard":
            self.select_tab(self.tab)
            return
        self.render()

    def toggle_dropdown(self, which):
        self.dropdown = None if which is None or self.dropdown == which else which
        self.render()

    def close_banner(self):
        self.banner = False
        self.render()

    def select_tab(self, name):
        self.tab = name
        self.dropdown = None
        self.status = ""
        if name == "Check up":
            self.anim = 0.0
            self._animate()
        else:
            self.anim = 1.0
            self.render()

    def _animate(self):
        self.anim = min(1.0, self.anim + 0.1)
        eased = 1 - (1 - self.anim) ** 3
        keep = self.anim
        self.anim = eased
        self.render()
        self.anim = keep
        if keep < 1.0 and self.tab == "Check up" and self.section == "Dashboard":
            self.after(16, self._animate)
        else:
            self.anim = 1.0
            self.render()

    def checkup_choice(self, kind):
        self.status = ("Connecting you to a pharmacist..." if kind == "Call"
                       else "Opening a chat with your care assistant...")
        self.render()

    def flip_task(self, i):
        self.tasks[i][3] = not self.tasks[i][3]
        self.render()

    def add_prescription(self):
        dialog = tk.Toplevel(self)
        dialog.title("Add prescription")
        dialog.geometry("460x250")
        dialog.resizable(False, False)
        dialog.configure(bg=WHITE)
        dialog.transient(self)
        dialog.grab_set()
        tk.Label(dialog, text="Add prescription", bg=WHITE, fg=TEXT_DARK,
                 font=(FONT, 18, "bold")).pack(pady=(24, 12))
        tk.Label(dialog, text="Medication name", bg=WHITE, fg=TEXT_MUTED,
                 font=(FONT, 13)).pack(anchor="w", padx=32)
        entry = tk.Entry(dialog, font=(FONT, 13), width=38)
        entry.pack(pady=(4, 18), padx=32)
        entry.focus_set()

        def save(_e=None):
            if entry.get().strip():
                self.prescriptions.append(entry.get().strip())
                dialog.destroy()
                self.render()

        entry.bind("<Return>", save)
        tk.Button(dialog, text="Add prescription", command=save, bg=RED, fg=WHITE,
                  activebackground=RED_DARK, activeforeground=WHITE, bd=0,
                  font=(FONT, 13, "bold"), width=24, height=2, cursor="hand2").pack()

    # --------------------------------------------------------------- icons ---
    def draw_icon(self, kind, cx, cy, size, color, tag, bg=WHITE):
        """Vector icons drawn on a 24x24 grid centred on (cx, cy)."""
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
            c.create_text(cx, cy, text="Rx", fill=color, font=(FONT, -max(1, round(7 * u)), "bold"), tags=tags)
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
            c.create_text(cx, cy, text="?", fill=color, font=(FONT, -max(1, round(20 * u)), "bold"), tags=tags)
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
        elif kind == "close":
            line(6, 6, 18, 18)
            line(18, 6, 6, 18)
        elif kind == "chev_right":
            line(9, 5, 16, 12, 9, 19)
        elif kind == "chev_down":
            line(5, 9, 12, 16, 19, 9)
        elif kind == "back":
            line(15, 4, 7, 12, 15, 20)


if __name__ == "__main__":
    app = PillwayApp()
    app.mainloop()
