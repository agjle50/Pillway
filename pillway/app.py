"""Core application setup and interaction state for Pillway."""

import ctypes
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

from .chat_history import ChatHistoryStore
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
from .profile_store import ProfileStore
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
        self.profile_status = ""
        self.doctor_status = ""
        self.doctor_section = "User account information"
        self.profile_store = ProfileStore()
        stored_profiles = self.profile_store.load()
        self.profiles = {profile["id"]: profile for profile in stored_profiles}
        patient_ids = [profile_id for profile_id, profile in self.profiles.items()
                       if profile["role"] == "Patient"]
        self.active_profile_id = "patient" if "patient" in patient_ids else patient_ids[0]
        self.selected_patient_id = patient_ids[0]
        self.chat_history = ChatHistoryStore(self.profiles)
        self.chat_logs = self.chat_history.load()
        self.chat_messages = self.chat_logs[self.active_profile_id]
        self.medical_robots = {
            profile_id: MedicalRobot()
            for profile_id, profile in self.profiles.items()
            if profile["role"] == "Patient"
        }
        self.prescription_flow = False
        self.prescription_stage = None
        self.prescription_photo = ""
        self.prescription_draft = ""
        self.prescription_entry = None
        self.chat_open = False
        self.call_open = False
        self.medical_robot = self.medical_robots[self.active_profile_id]
        self.chat_draft = ""
        self.chat_focus_requested = False
        self.chat_entry = None
        self.chat_view_frame = None
        self.chat_message_canvas = None
        self.chat_scrollbar = None
        self.doctor_tabs_frame = None
        self.doctor_log_frame = None
        self.profiles_view_frame = None
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
        restore_chat_focus = self.chat_focus_requested
        self.chat_focus_requested = False
        if self.prescription_entry and self.prescription_entry.winfo_exists():
            self.prescription_draft = self.prescription_entry.get()
            self.prescription_entry.destroy()
            self.prescription_entry = None
        if self.chat_entry and self.chat_entry.winfo_exists():
            restore_chat_focus = restore_chat_focus or self.focus_get() == self.chat_entry
            current_text = self.chat_entry.get()
            self.chat_draft = "" if current_text == self.chat_placeholder else current_text
            self.chat_entry.destroy()
            self.chat_entry = None
        if self.chat_view_frame and self.chat_view_frame.winfo_exists():
            self.chat_view_frame.destroy()
        self.chat_view_frame = None
        for attribute in ("doctor_tabs_frame", "doctor_log_frame", "profiles_view_frame"):
            frame = getattr(self, attribute)
            if frame and frame.winfo_exists():
                frame.destroy()
            setattr(self, attribute, None)
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
            if self.profiles[self.active_profile_id]["role"] == "Doctor":
                self.draw_doctor_dashboard()
            else:
                self.draw_dashboard()
        elif self.section == "Settings":
            self.draw_settings()
        elif self.section == "Manage profiles":
            self.draw_manage_profiles()
        else:
            self.draw_placeholder_page(self.section)
        if self.dropdown:
            self.draw_dropdown()
        if restore_chat_focus and self.chat_open and self.chat_entry:
            self.chat_entry.focus_set()
            self.chat_focus_in()
            self.chat_entry.icursor(tk.END)

    def draw_sidebar(self):
        if (
            self.section == "Dashboard"
            and self.profiles[self.active_profile_id]["role"] == "Doctor"
        ):
            self.draw_doctor_sidebar()
            return
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
        if (
            self.section == "Dashboard"
            and self.profiles[self.active_profile_id]["role"] == "Doctor"
        ):
            self.draw_doctor_header()
            return
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
        self.call_open = False
        if section == "Dashboard":
            self.select_tab(self.tab)
            return
        self.render()

    def switch_profile(self, profile_id):
        if profile_id not in self.profiles:
            raise ValueError(f"Unknown profile: {profile_id}")
        self.chat_history.save(self.chat_logs)
        self.active_profile_id = profile_id
        self.chat_messages = self.chat_logs[profile_id]
        if self.profiles[profile_id]["role"] == "Doctor":
            patients = [key for key, profile in self.profiles.items()
                        if profile["role"] == "Patient"]
            if self.selected_patient_id not in patients:
                self.selected_patient_id = patients[0]
        else:
            self.medical_robot = self.medical_robots[profile_id]
        self.chat_open = False
        self.call_open = False
        self.chat_draft = ""
        self.section = "Dashboard"
        self.dropdown = None
        self.status = ""
        self.render()

    def open_profile_chat(self):
        if self.profiles[self.active_profile_id]["role"] != "Patient":
            raise RuntimeError("The Doctor profile has no chatbot.")
        self.call_open = False
        if not self.chat_messages:
            self.chat_messages.append(("Juliez", self.medical_robot.greeting()))
            self.chat_history.save(self.chat_logs)
        self.chat_open = True
        self.dropdown = None
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
        self.call_open = False
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
            self.open_profile_chat()
            return
        if kind == "Call":
            self.call_open = True
            self.chat_open = False
            self.status = ""
            self.render()
            return
        self.status = "Opening a chat with your care assistant..."
        self.render()

    def close_call_preview(self):
        self.call_open = False
        self.render()

    def close_chat(self):
        self.chat_open = False
        self.call_open = False
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
        if self.profiles[self.active_profile_id]["role"] != "Patient":
            raise RuntimeError("The Doctor profile cannot send chatbot messages.")
        message = self.chat_entry.get().strip() if self.chat_entry else ""
        if not message or message == self.chat_placeholder:
            return
        self.chat_messages.append(("You", message))
        self.chat_messages.append(("Juliez", self.medical_robot.reply(message)))
        self.chat_history.save(self.chat_logs)
        if self.chat_entry:
            self.chat_entry.delete(0, tk.END)
        self.chat_draft = ""
        self.chat_focus_requested = True
        self.render()

    def select_doctor_patient(self, profile_id):
        profile = self.profiles.get(profile_id)
        if not profile or profile["role"] != "Patient":
            raise ValueError(f"Unknown patient profile: {profile_id}")
        self.selected_patient_id = profile_id
        self.render()

    def select_doctor_section(self, section):
        if section not in self.doctor_sections:
            raise ValueError(f"Unknown care-plan section: {section}")
        self.doctor_section = section
        self.render()

    def save_doctor_workspace(self):
        try:
            self.profile_store.save(list(self.profiles.values()))
            self.chat_history.save(self.chat_logs)
        except OSError as error:
            self.doctor_status = f"Could not save local care-plan data: {error}"
            self.render()
            return
        self.doctor_status = "Local demo profiles and chat logs saved."
        self.render()

    def add_patient_profile(self):
        name = simpledialog.askstring(
            "Add patient",
            "Enter a name for this local demo patient profile:",
            parent=self,
        )
        if name is None:
            return
        try:
            profile = ProfileStore.new_patient(name)
        except ValueError:
            self.profile_status = "Enter a patient name to add the profile."
            self.render()
            return
        self.profiles[profile["id"]] = profile
        self.profile_store.save(list(self.profiles.values()))
        self.chat_logs[profile["id"]] = []
        self.chat_history = ChatHistoryStore(self.profiles, self.chat_history.path)
        self.chat_history.save(self.chat_logs)
        self.medical_robots[profile["id"]] = MedicalRobot()
        self.selected_patient_id = profile["id"]
        self.profile_status = f"{name.strip()} added as a local demo patient."
        self.render()

    def delete_profile(self, profile_id):
        profile = self.profiles.get(profile_id)
        if not profile:
            raise ValueError(f"Unknown profile: {profile_id}")
        role_ids = [
            key for key, item in self.profiles.items() if item["role"] == profile["role"]
        ]
        if len(role_ids) <= 1:
            self.profile_status = f"The last {profile['role'].lower()} profile cannot be deleted."
            self.render()
            return
        confirmed = messagebox.askyesno(
            "Delete profile",
            f"Delete {profile['name']} and permanently remove their saved chat log?",
            parent=self,
            default=messagebox.NO,
        )
        if not confirmed:
            return

        remaining_profiles = {
            key: value for key, value in self.profiles.items() if key != profile_id
        }
        remaining_logs = {
            key: value for key, value in self.chat_logs.items() if key != profile_id
        }
        scrubbed_logs = dict(self.chat_logs)
        scrubbed_logs[profile_id] = []
        scrubbed_store = ChatHistoryStore(self.profiles, self.chat_history.path)
        try:
            scrubbed_store.save(scrubbed_logs)
        except OSError as error:
            messagebox.showerror(
                "Could not delete chat history",
                f"The profile was not deleted because its chat history could not be cleared:\n{error}",
                parent=self,
            )
            return
        self.chat_logs = scrubbed_logs
        self.chat_history = scrubbed_store
        if self.active_profile_id == profile_id:
            self.chat_messages = scrubbed_logs[profile_id]
        try:
            self.profile_store.save(list(remaining_profiles.values()))
        except OSError as error:
            self.profile_status = "The chat log was cleared, but the profile could not be deleted."
            messagebox.showerror(
                "Profile deletion incomplete",
                f"The chat log was cleared, but the profile file could not be updated:\n{error}",
                parent=self,
            )
            self.render()
            return

        self.profiles = remaining_profiles
        self.chat_logs = remaining_logs
        history_store = ChatHistoryStore(remaining_profiles, self.chat_history.path)
        self.chat_history = history_store
        self.medical_robots.pop(profile_id, None)
        self.selected_patient_id = (
            self.selected_patient_id if self.selected_patient_id in remaining_profiles
            else next(key for key, item in remaining_profiles.items() if item["role"] == "Patient")
        )
        role_ids = [key for key, item in self.profiles.items() if item["role"] == profile["role"]]
        if self.active_profile_id == profile_id:
            self.active_profile_id = role_ids[0]
            self.chat_messages = self.chat_logs[self.active_profile_id]
            if profile["role"] == "Patient":
                self.medical_robot = self.medical_robots[self.active_profile_id]
            self.section = "Dashboard"
        try:
            self.chat_history.save(self.chat_logs)
        except OSError as error:
            self.profile_status = "Profile and chat were deleted; local chat index cleanup failed."
            messagebox.showerror(
                "Chat index cleanup failed",
                f"The chat messages were cleared, but the local chat file could not be fully updated:\n{error}",
                parent=self,
            )
            self.render()
            return
        self.profile_status = f"{profile['name']} and their chat log were deleted."
        self.render()

    def delete_patient_profile(self, profile_id):
        self.delete_profile(profile_id)

    def delete_all_local_data(self):
        confirmed = messagebox.askyesno(
            "Delete all local Pillway data",
            "Permanently delete all saved profiles and chat logs from this PC? "
            "This removes the local profiles.json and chat_history.json files. "
            "Built-in demo accounts will be restored afterward.",
            parent=self,
            default=messagebox.NO,
        )
        if not confirmed:
            return

        paths = (
            self.profile_store.path,
            self.profile_store.path.with_name(self.profile_store.path.name + ".tmp"),
            self.chat_history.path,
            self.chat_history.path.with_name(self.chat_history.path.name + ".tmp"),
        )
        try:
            for path in paths:
                if path.exists():
                    path.unlink()
        except OSError as error:
            messagebox.showerror(
                "Could not delete all local data",
                f"Some files may already have been deleted. Fix the file access issue and retry:\n{error}",
                parent=self,
            )
            return

        self.profiles = {profile["id"]: profile for profile in self.profile_store.load()}
        self.chat_history = ChatHistoryStore(self.profiles, self.chat_history.path)
        self.chat_logs = self.chat_history.load()
        patient_ids = [key for key, item in self.profiles.items() if item["role"] == "Patient"]
        self.active_profile_id = patient_ids[0]
        self.selected_patient_id = patient_ids[0]
        self.chat_messages = self.chat_logs[self.active_profile_id]
        self.medical_robots = {
            key: MedicalRobot()
            for key, item in self.profiles.items()
            if item["role"] == "Patient"
        }
        self.medical_robot = self.medical_robots[self.active_profile_id]
        self.profile_status = "Saved profiles and chat logs deleted; built-in demo accounts restored."
        self.doctor_status = ""
        self.chat_open = False
        self.call_open = False
        self.chat_draft = ""
        self.dropdown = None
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
