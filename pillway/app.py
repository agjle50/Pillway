"""Core application setup and interaction state for Pillway."""

import ctypes
import sys
import tkinter as tk
from tkinter import filedialog

from .constants import (
    BASE_H,
    BASE_W,
    BORDER,
    DIVIDER,
    FONT,
    INK,
    NAV_ITEMS,
    NAV_ICON,
    NAV_TEXT,
    NAVY,
    NAVY_DARK,
    NOTIFICATIONS,
    RED,
    SHADOW,
    TEXT_DARK,
    TEXT_MUTED,
    WHITE,
)
from .icons import IconMixin
from .medical_robot import MedicalRobot
from .views import DashboardViewMixin, SettingsViewMixin


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


class PillwayApp(DashboardViewMixin, SettingsViewMixin, IconMixin, tk.Tk):
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
        self.notifications = list(NOTIFICATIONS)
        self.prescription_flow = False
        self.prescription_stage = None
        self.prescription_photo = ""
        self.prescription_draft = ""
        self.prescription_entry = None
        self.chat_open = False
        self.chat_messages = []
        self.medical_robot = MedicalRobot()
        self.chat_draft = ""
        self.chat_entry = None
        self.chat_view_frame = None
        self.chat_message_canvas = None
        self.chat_scrollbar = None
        self.chat_placeholder = "TYPE YOUR MESSAGE..."
        self.tasks = [                # alarm-style reminders
            ["8:00", "AM", "Check blood sugar", True],
            ["9:00", "AM", "Foot check", True],
            ["12:30", "PM", "15-minute walk", False],
            ["7:00", "PM", "Log dinner", False],
        ]

        self._job = None
        self.c.bind("<Configure>", self._schedule_render)
        self.after(50, lambda: self.select_tab("Check up"))

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

    def render(self):
        self._job = None
        c = self.c
        if self.prescription_entry and self.prescription_entry.winfo_exists():
            self.prescription_draft = self.prescription_entry.get()
            self.prescription_entry.destroy()
            self.prescription_entry = None
        if self.chat_entry and self.chat_entry.winfo_exists():
            current_text = self.chat_entry.get()
            self.chat_draft = "" if current_text == self.chat_placeholder else current_text
            self.chat_entry.destroy()
            self.chat_entry = None
        if self.chat_view_frame and self.chat_view_frame.winfo_exists():
            self.chat_view_frame.destroy()
        self.chat_view_frame = None
        self.chat_message_canvas = None
        self.chat_scrollbar = None
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

    def go(self, section):
        self.section = section
        self.dropdown = None
        self.chat_open = False
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
        self.chat_open = False
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
        if kind == "Chat":
            if not self.chat_messages:
                self.chat_messages.append(("Sarah", self.medical_robot.greeting()))
            self.chat_open = True
            self.dropdown = None
            self.render()
            return
        self.status = ("Connecting you to a pharmacist..." if kind == "Call"
                       else "Opening a chat with your care assistant...")
        self.render()

    def close_chat(self):
        self.chat_open = False
        self.chat_draft = ""
        self.render()

    def chat_focus_in(self, _event=None):
        if self.chat_entry and self.chat_entry.get() == self.chat_placeholder:
            self.chat_entry.delete(0, tk.END)
            self.chat_entry.configure(fg=TEXT_DARK)

    def chat_focus_out(self, _event=None):
        if self.chat_entry and not self.chat_entry.get():
            self.chat_entry.insert(0, self.chat_placeholder)
            self.chat_entry.configure(fg=TEXT_MUTED)

    def send_chat_message(self, _event=None):
        message = self.chat_entry.get().strip() if self.chat_entry else ""
        if not message or message == self.chat_placeholder:
            return
        self.chat_messages.append(("You", message))
        self.chat_messages.append(("Sarah", self.medical_robot.reply(message)))
        if self.chat_entry:
            self.chat_entry.delete(0, tk.END)
        self.chat_draft = ""
        self.render()

    def copy_chat_message(self, message):
        self.clipboard_clear()
        self.clipboard_append(message)

    def copy_chat_selection(self, event, fallback):
        try:
            selected = event.widget.get("sel.first", "sel.last")
        except tk.TclError:
            selected = fallback
        self.copy_chat_message(selected)
        return "break"

    def flip_task(self, i):
        self.tasks[i][3] = not self.tasks[i][3]
        self.render()

    def add_prescription(self):
        self.prescription_flow = True
        self.prescription_stage = None
        self.prescription_photo = ""
        self.prescription_draft = ""
        self.status = ""
        self.render()

    def close_prescription_flow(self):
        self.prescription_flow = False
        self.prescription_stage = None
        self.prescription_draft = ""
        self.status = ""
        self.render()

    def choose_prescription_method(self, method):
        self.prescription_stage = method
        self.prescription_draft = ""
        self.status = ""
        self.render()

    def choose_prescription_photo(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Choose prescription photo",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")]
        )
        if path:
            self.prescription_photo = path
            self.render()

    def save_prescription(self, _event=None):
        medication = self.prescription_entry.get().strip() if self.prescription_entry else ""
        if not medication:
            self.status = "Enter the medication name to continue."
            self.render()
            return
        if self.prescription_stage == "Upload Photo" and not self.prescription_photo:
            self.status = "Choose a photo of your prescription to continue."
            self.render()
            return
        self.prescriptions.append(medication)
        self.notifications.insert(
            0, ("New medication prescribed", f"{medication} has been added to your medications.")
        )
        self.prescription_flow = False
        self.prescription_stage = None
        self.prescription_draft = ""
        self.prescription_photo = ""
        self.status = ""
        self.render()

    def set_prescription_status(self, message):
        self.status = message
        self.render()
