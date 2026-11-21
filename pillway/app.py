"""The main window: creates the canvas, holds UI state, scales and routes drawing to screens.

Called by: Pillway.py (python Pillway.py).
Each screen lives in its own file under pillway/ui/ and is mixed into PillwayApp below.
To add a screen: write a mixin in pillway/ui/..., add it to the class list, and route to it in render().
"""

import ctypes
import sys
import tkinter as tk
from tkinter import messagebox  # noqa: F401  (tests patch pillway.app.messagebox)

from .core.medical_robot import MedicalRobot
from .storage.chat_history import ChatHistoryStore
from .storage.profile_store import ProfileStore
from .ui.canvas_helpers import CanvasHelpersMixin
from .ui.components.buttons import ButtonsMixin
from .ui.components.dropdown import DropdownMixin
from .ui.components.icons import IconMixin
from .ui.patient.call import CallMixin
from .ui.patient.chat import ChatMixin
from .ui.patient.chat_actions import ChatActionsMixin
from .ui.patient.check_up import CheckUpMixin
from .ui.patient.dashboard import PatientDashboardMixin
from .ui.patient.manage_profiles import ManageProfilesMixin
from .ui.patient.medications import MedicationsMixin
from .ui.patient.orders import OrdersMixin
from .ui.patient.prescription import PrescriptionMixin
from .ui.patient.settings import SettingsMixin
from .ui.patient.tasks import TasksMixin
from .ui.pharmacist.consult_pages import ConsultPagesMixin
from .ui.pharmacist.consult_pages_more import ConsultPagesMoreMixin
from .ui.pharmacist.patient_picker import PatientPickerMixin
from .ui.pharmacist.workspace_router import WorkspaceRouterMixin
from .ui.pharmacist.workspace_shell import WorkspaceShellMixin
from .ui.profile_actions import ProfileActionsMixin
from .ui.sample_content import NOTIFICATIONS
from .ui.shell.header import HeaderMixin
from .ui.shell.sidebar import SidebarMixin
from .ui.theme import BASE_H, BASE_W, WHITE, pick_font


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


class PillwayApp(
    # patient screens
    PatientDashboardMixin, CheckUpMixin, CallMixin, ChatMixin, ChatActionsMixin,
    MedicationsMixin, PrescriptionMixin, OrdersMixin, TasksMixin, SettingsMixin,
    ManageProfilesMixin, ProfileActionsMixin,
    # pharmacist screens
    PatientPickerMixin, WorkspaceShellMixin, WorkspaceRouterMixin, ConsultPagesMixin,
    ConsultPagesMoreMixin,
    # shared shell and components
    SidebarMixin, HeaderMixin, DropdownMixin, ButtonsMixin, IconMixin, CanvasHelpersMixin,
    tk.Tk,
):
    def __init__(self):
        enable_high_dpi()
        super().__init__()
        self.title("Pillway")
        self.geometry("1500x900")
        self.minsize(900, 560)
        self.configure(bg=WHITE)
        self.protocol("WM_DELETE_WINDOW", self.close_application)

        pick_font(self)
        self.c = tk.Canvas(self, bg=WHITE, highlightthickness=0, bd=0)
        self.c.pack(fill="both", expand=True)
        self._click_targets = []
        self.c.bind("<Button-1>", self._dispatch_expanded_click, add="+")

        # UI state
        self.section = "Dashboard"
        self.tab = "Check up"
        self.banner = True
        self.dropdown = None          # None | "notifications" | "profile"
        self.anim = 1.0               # 0 -> 1 slide-in for the Check up bars
        self._checkup_animation_job = None
        self._checkup_animation_started = None
        self.status = ""              # small message under Check up bars
        self.prescriptions = []
        self.notifications = list(NOTIFICATIONS)
        self.profile_status = ""
        self.doctor_status = ""
        self.doctor_section = "User account information"
        self.doctor_workspace_open = False
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
        self.call_mic_state = "off"
        self.call_status = "Mic off. First use downloads a ~40 MB offline model."
        self.call_transcript = ""
        self.call_partial = ""
        self.call_listener = None
        self.call_events = None
        self._call_poll_job = None
        self.medical_robot = self.medical_robots[self.active_profile_id]
        self.chat_draft = ""
        self.chat_focus_requested = False
        self.chat_entry = None
        self.chat_view_frame = None
        self.chat_message_canvas = None
        self.chat_scrollbar = None
        self.doctor_tabs_frame = None
        self.doctor_log_frame = None
        self.doctor_patients_frame = None
        self.profiles_view_frame = None
        self.chat_placeholder = "TYPE YOUR MESSAGE..."
        self.tasks = [                # alarm-style reminders
            ["8:00", "AM", "Check blood sugar", True],
            ["9:00", "AM", "Foot check", True],
            ["12:30", "PM", "15-minute walk", False],
            ["7:00", "PM", "Log dinner", False],
        ]
        self._task_toggle_jobs = {}

        self._job = None
        self.c.bind("<Configure>", self._schedule_render)
        self.after(50, lambda: self.select_tab("Check up"))

    def _schedule_render(self, _event=None):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(10, self.render)

    def render(self):
        self._job = None
        c = self.c
        self._click_targets = []
        for job in self._task_toggle_jobs.values():
            self.after_cancel(job)
        self._task_toggle_jobs.clear()
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
        for attribute in (
            "doctor_tabs_frame", "doctor_log_frame", "profiles_view_frame",
            "doctor_patients_frame",
        ):
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
                if self.doctor_workspace_open:
                    self.draw_doctor_dashboard()
                else:
                    self.draw_doctor_patient_picker()
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

    def go(self, section):
        self._cancel_checkup_animation()
        self._stop_call_input()
        self.section = section
        self.dropdown = None
        self.chat_open = False
        self.call_open = False
        if section == "Dashboard":
            self.select_tab(self.tab)
            return
        self.render()

    def toggle_dropdown(self, which):
        self.dropdown = None if which is None or self.dropdown == which else which
        self.render()

    def close_application(self):
        listener = self.call_listener
        self._stop_call_input()
        if listener and listener.is_alive():
            listener.thread.join(timeout=1)
        self._cancel_checkup_animation()
        for job in self._task_toggle_jobs.values():
            self.after_cancel(job)
        self._task_toggle_jobs.clear()
        self.destroy()
