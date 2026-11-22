"""The main window: creates the canvas, holds UI state, scales and routes drawing to screens.

Called by: Pillway.py (python Pillway.py).
Each screen lives in its own file under pillway/ui/ and is mixed into PillwayApp below.
To add a screen: write a mixin in pillway/ui/..., add it to the class list, and route to it in render().
No business rules live here: those are in pillway/core.
"""

import ctypes
import sys
import tkinter as tk
from tkinter import messagebox  # noqa: F401  (tests patch pillway.app.messagebox)

from config import get_settings

from .core.conversation_service import ConversationService
from .core.medical_robot import MedicalRobot
from .storage import app_state
from .storage.chat_history import ChatHistoryStore
from .storage.patient_store import PatientStore
from .storage.profile_store import ProfileStore
from .ui.canvas_helpers import CanvasHelpersMixin
from .ui.components.buttons import ButtonsMixin
from .ui.components.dropdown import DropdownMixin
from .ui.components.icons import IconMixin
from .ui.components.scroll_area import ScrollAreaMixin
from .ui.i18n import I18nMixin
from .ui.live_sync import LiveSyncMixin
from .ui.login import LoginMixin
from .ui.patient.call import CallMixin
from .ui.patient.call_audio import CallAudioMixin
from .ui.patient.care_plan import PatientCarePlanMixin
from .ui.patient.chat import ChatMixin
from .ui.patient.chat_actions import ChatActionsMixin
from .ui.patient.check_up import CheckUpMixin
from .ui.patient.consent import ConsentMixin
from .ui.patient.dashboard import PatientDashboardMixin
from .ui.patient.manage_profiles import ManageProfilesMixin
from .ui.patient.medications import MedicationsMixin
from .ui.patient.orders import OrdersMixin
from .ui.patient.prescription import PrescriptionMixin
from .ui.patient.settings import SettingsMixin
from .ui.patient.tasks import TasksMixin
from .ui.pharmacist.bot_settings import BotSettingsMixin
from .ui.pharmacist.care_plan_editor import CarePlanEditorMixin
from .ui.pharmacist.check_ins import CheckInsMixin
from .ui.pharmacist.consult_pages import ConsultPagesMixin
from .ui.pharmacist.consult_pages_more import ConsultPagesMoreMixin
from .ui.pharmacist.dashboard import PharmacistDashboardMixin
from .ui.pharmacist.flags import FlagsMixin
from .ui.pharmacist.highlights import HighlightsMixin
from .ui.pharmacist.log import LogMixin
from .ui.pharmacist.medication_review import MedicationReviewMixin
from .ui.pharmacist.patient_detail import PatientDetailMixin
from .ui.pharmacist.workspace_router import WorkspaceRouterMixin
from .ui.profile_actions import ProfileActionsMixin
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
    # sign-in and live updates
    LoginMixin, LiveSyncMixin,
    # patient screens
    PatientDashboardMixin, CheckUpMixin, CallMixin, CallAudioMixin, ChatMixin, ChatActionsMixin, ConsentMixin,
    MedicationsMixin, PrescriptionMixin, OrdersMixin, TasksMixin, PatientCarePlanMixin, SettingsMixin,
    ManageProfilesMixin, ProfileActionsMixin,
    # pharmacist screens
    PharmacistDashboardMixin, PatientDetailMixin, FlagsMixin, HighlightsMixin, LogMixin,
    CarePlanEditorMixin, MedicationReviewMixin, CheckInsMixin, BotSettingsMixin,
    WorkspaceRouterMixin, ConsultPagesMixin, ConsultPagesMoreMixin,
    # shared shell and components
    SidebarMixin, HeaderMixin, DropdownMixin, ScrollAreaMixin, ButtonsMixin, IconMixin,
    I18nMixin, CanvasHelpersMixin,
    tk.Tk,
):
    def __init__(self, start_role=""):
        enable_high_dpi()
        super().__init__()
        settings = get_settings()
        self.title(settings.branding.app_name)
        self.geometry("1500x900")
        self.minsize(900, 560)
        self.configure(bg=WHITE)
        self.protocol("WM_DELETE_WINDOW", self.close_application)
        pick_font(self)

        self.c = tk.Canvas(self, bg=WHITE, highlightthickness=0, bd=0)
        self.c.pack(fill="both", expand=True)
        self._click_targets = []
        self.c.bind("<Button-1>", self._dispatch_expanded_click, add="+")
        self.c.bind("<Button-1>", self.close_dropdown_on_outside_click, add="+")
        self.bind_all("<Button-1>", self._sound_on_native_button_click, add="+")

        # shared data (one source of truth for both roles)
        self.store = PatientStore()
        self.service = ConversationService(store=self.store)
        self.role = None                  # None = sign-in screen, "patient" or "pharmacist"
        self.lang = settings.patient.default_language
        self.patient_id = "maria"         # the patient record shown on the patient side
        self.record = None                # cached copy of that record (refreshed by live sync)

        # UI state
        self.section = "Dashboard"
        self.tab = "Check up"
        self.banner = True
        self.dropdown = None              # None | "notifications" | "profile"
        self.dropdown_frame = None
        self.anim = 1.0                   # 0 -> 1 slide-in for the Check up bars
        self._checkup_animation_job = None
        self._checkup_animation_started = None
        self.status = ""                  # small message under Check up bars
        self.toast = ""                   # short confirmation message ("Saved", "Resolved")
        self.prescriptions = []
        self.notifications = []
        self.profile_status = ""
        self.doctor_status = ""
        self.doctor_section = "User account information"
        self.detail_section = "Flagged messages"
        self.doctor_workspace_open = False
        prefs = app_state.load()
        if "microphone_device" in prefs:
            settings.call.microphone_device = str(prefs["microphone_device"])
        self.dash_filter, self.dash_sort, self.dash_view = prefs["filter"], prefs["sort"], prefs["view"]
        if "review_required" in prefs:  # the pharmacist's switch on the care plan screen
            settings.pharmacist.pharmacist_review_required = prefs["review_required"]
        self.recently_moved = {}
        self.expanded_flags = set()
        self.consent_declined = False
        self.task_ids = []
        self._last_order = []
        self._dropdown_opened_by_click = False
        self.bell_box = (0, 0)
        self.profile_box = (0, 0)
        self.show_resolved = False
        self.show_history = False

        # accounts (Manage profiles) and the older per-profile chat log (kept for compatibility)
        self.profile_store = ProfileStore()
        self.profiles = {profile["id"]: profile for profile in self.profile_store.load()}
        patient_ids = [pid for pid, p in self.profiles.items() if p["role"] == "Patient"]
        self.active_profile_id = "patient" if "patient" in patient_ids else patient_ids[0]
        self.selected_patient_id = "maria"
        self.chat_history = ChatHistoryStore(self.profiles)
        self.chat_logs = self.chat_history.load()
        self.chat_messages = self.chat_logs[self.active_profile_id]
        self.medical_robots = {pid: MedicalRobot() for pid in patient_ids}
        self.medical_robot = self.medical_robots[self.active_profile_id]

        self.prescription_flow = False
        self.prescription_stage = None
        self.prescription_photo = ""
        self.prescription_draft = ""
        self.prescription_entry = None
        self.chat_open = False
        self.call_open = False
        self.call_state = {}
        self.call_listener = None
        self.call_events = None
        self._call_poll_job = None
        self.microphone_test_listener = None
        self.microphone_test_events = None
        self.microphone_test_active = False
        self.microphone_test_level = 0.0
        self.microphone_test_status = ""
        self.microphone_test_error = False
        self._mic_test_job = None
        self.chat_draft = ""
        self.chat_focus_requested = False
        self.chat_entry = None
        self.voice_listener = None
        self.voice_events = None
        self.voice_typing_active = False
        self.voice_typing_status = ""
        self.voice_typing_had_text = False
        self.voice_typing_error = False
        self._voice_typing_job = None
        self.chat_view_frame = None
        self.chat_message_canvas = None
        self.chat_scrollbar = None
        self.embedded_frames = []
        self.doctor_tabs_frame = None
        self.doctor_log_frame = None
        self.doctor_patients_frame = None
        self.profiles_view_frame = None
        self.tasks = []
        self._task_toggle_jobs = {}

        self._job = None
        self.c.bind("<Configure>", self._schedule_render)
        self.bind_all("<Escape>", lambda _e: self.on_escape())
        self.start_live_sync()
        if start_role in ("patient", "pharmacist"):
            self.after(50, lambda: self.sign_in(start_role))
        else:
            self.after(50, self.render)

    def _schedule_render(self, _event=None):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(10, self.render)

    # ---- drawing ------------------------------------------------------------------

    def _clear_embedded_widgets(self):
        """Embedded Tk widgets sit above the canvas, so they are rebuilt on every render."""
        if self.prescription_entry and self.prescription_entry.winfo_exists():
            self.prescription_draft = self.prescription_entry.get()
            self.prescription_entry.destroy()
            self.prescription_entry = None
        if self.chat_entry and self.chat_entry.winfo_exists():
            current = self.chat_entry.get()
            self.chat_draft = "" if current == self.t("chat.placeholder") else current
            self.chat_entry.destroy()
            self.chat_entry = None
        for attribute in ("chat_view_frame", "doctor_tabs_frame", "doctor_log_frame", "profiles_view_frame",
                          "doctor_patients_frame", "dropdown_frame"):
            frame = getattr(self, attribute)
            if frame and frame.winfo_exists():
                frame.destroy()
            setattr(self, attribute, None)
        for frame in self.embedded_frames:
            if frame.winfo_exists():
                frame.destroy()
        self.embedded_frames = []
        self.chat_message_canvas = None
        self.chat_scrollbar = None

    def render(self):
        self._job = None
        if not self.chat_open and self.voice_listener:
            self._stop_voice_typing()
        if self.section != "Microphone" and self.microphone_test_listener:
            self._stop_microphone_test()
        self._click_targets = []
        for job in self._task_toggle_jobs.values():
            self.after_cancel(job)
        self._task_toggle_jobs.clear()
        restore_chat_focus = self.chat_focus_requested or (
            self.chat_entry is not None and self.chat_entry.winfo_exists() and self.focus_get() == self.chat_entry)
        self.chat_focus_requested = False
        self._clear_embedded_widgets()
        self.c.delete("all")
        w, h = max(self.c.winfo_width(), 1), max(self.c.winfo_height(), 1)
        self.w, self.h = w, h
        self.s = min(w / BASE_W, h / BASE_H)
        self.sw = self.S(300)  # sidebar width
        if self.role is None:
            self.draw_login()
            return
        self.refresh_record()
        self.draw_sidebar()
        self.draw_header()
        if self.section == "Dashboard":
            if self.role == "pharmacist":
                if self.doctor_workspace_open:
                    self.draw_patient_detail()
                else:
                    self.draw_pharmacist_dashboard()
            else:
                self.draw_dashboard()
        elif self.section == "Settings":
            self.draw_settings()
        elif self.section == "Manage profiles":
            self.draw_manage_profiles()
        elif self.section == "Microphone":
            self.draw_microphone_settings()
        elif self.section in ("See a doctor", "Contact us", "Account tour", "FAQ"):
            self.draw_placeholder_page(self.section)
        else:
            self.draw_placeholder_page(self.section)
        if self.toast:
            self.draw_toast()
        if self.dropdown:
            self.draw_dropdown()
        if restore_chat_focus and self.chat_open and self.chat_entry:
            self.chat_entry.focus_set()
            self.chat_focus_in()
            self.chat_entry.icursor(tk.END)

    # ---- navigation -----------------------------------------------------------------

    def go(self, section):
        self._cancel_checkup_animation()
        self._stop_call_input()
        self.dropdown = None
        self.chat_open = False
        self.call_open = False
        if section in ("Medications", "Orders", "Tasks", "Care plan") and self.role == "patient":
            self.section = "Dashboard"
            self.select_tab(section)
            return
        self.section = section
        if section == "Dashboard":
            if self.role == "patient":
                self.select_tab(self.tab)
                return
            self.doctor_workspace_open = False
        self.render()

    def toggle_dropdown(self, which):
        self.dropdown = None if which is None or self.dropdown == which else which
        self.render()

    def on_escape(self):
        if self.dropdown:
            self.toggle_dropdown(None)
        elif self.role == "pharmacist" and self.doctor_workspace_open:
            self.return_to_doctor_patient_list()
        elif self.chat_open or self.call_open:
            self.close_chat()

    def flash(self, message):
        """Show a short confirmation (instant feedback on every click)."""
        self.toast = message
        self.render()
        self.after(1800, self._clear_toast)

    def _clear_toast(self):
        if self.toast:
            self.toast = ""
            self.render()

    def close_application(self):
        listener = self.call_listener
        voice_listener = self.voice_listener
        microphone_test_listener = self.microphone_test_listener
        self._stop_call_input()
        self._stop_voice_typing()
        self._stop_microphone_test()
        if listener and listener.is_alive():
            listener.thread.join(timeout=1)
        if voice_listener and voice_listener.is_alive():
            voice_listener.thread.join(timeout=1)
        if microphone_test_listener and microphone_test_listener.is_alive():
            microphone_test_listener.thread.join(timeout=1)
        self._cancel_checkup_animation()
        for job in self._task_toggle_jobs.values():
            self.after_cancel(job)
        self._task_toggle_jobs.clear()
        self.destroy()
