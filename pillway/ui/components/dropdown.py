"""The notifications and account menus under the header.

Called by: the header profile and notification controls.
The account menu is a compact popover; notifications use a native Tk menu.
"""

import tkinter as tk

from ...storage.patient_store import display_name
from ..patient.manage_profiles import profile_completion
from ..theme import BORDER, INK, RED, TEXT_DARK, TEXT_MUTED, WHITE


class DropdownMixin:
    def dropdown_items(self):
        if self.dropdown == "notifications":
            if self.role == "pharmacist":
                items = [
                    (f"New patient ticket: {display_name(record)}",
                     f"{request['reason']} · {request['time'][11:16]}",
                     lambda pid=record["id"]: self.select_doctor_patient(pid))
                    for record in self.store.all()
                    for request in record["pharmacist_requests"]
                    if request["status"] == "open"
                ]
                items.extend(
                    (f"Urgent: {display_name(record)}", f"{flag['topic']} · {flag['time'][11:16]}",
                     lambda pid=record["id"]: self.select_doctor_patient(pid))
                    for record in self.store.all()
                    for flag in record["flags"]
                    if flag["status"] == "open" and flag["tier"] == 1
                )
                return "Notifications", items or [("No notifications", "You're all caught up.", None)]
            return "Notifications", [(head, sub, None) for head, sub in self.notifications] or [
                ("No notifications yet", "New updates will appear here.", None)]
        items = [("Manage profiles", "Switch between demo accounts", lambda: self.go("Manage profiles")),
                 ("Settings", "Account, payments, notifications", lambda: self.go("Settings"))]
        if self.role == "pharmacist":
            items.append(("Reset demo", "Restore Maria to a fresh state", self.reset_demo))
        items.append(("Sign out", "", self.sign_out))
        return ("Pharmacist" if self.role == "pharmacist" else display_name(self.record or {"id": "Patient"})), items

    def show_menu(self, which):
        """Open the account popover or the native notifications menu."""
        if which == "profile":
            self._show_profile_menu()
            return
        self.dropdown = which
        title, items = self.dropdown_items()
        self.dropdown = None
        menu = tk.Menu(self, tearoff=0, font=self.font(13), bg=WHITE, fg=INK,
                       activebackground="#eef1f6", activeforeground=INK,
                       disabledforeground=TEXT_MUTED, relief="flat", bd=1)
        menu.add_command(label=title, state="disabled")
        menu.add_separator()
        for head, sub, action in items:
            label = f"{head}  \u00b7  {sub}" if sub and which == "notifications" else head
            menu.add_command(label=label, command=lambda a=action: self._dropdown_choose(a))
            if head == "Sign out":
                menu.entryconfigure("end", foreground=RED, activeforeground=RED)
        self.dropdown_menu = menu
        anchor_x, anchor_y = self.bell_box if which == "notifications" else self.profile_box
        x = self.winfo_rootx() + int(anchor_x)
        y = self.winfo_rooty() + int(anchor_y) + int(self.S(8))
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _show_profile_menu(self):
        self._close_profile_menu()
        self.dropdown = None
        width, height = int(self.S(390)), int(self.S(430))
        patient_id = self.patient_id if self.role == "patient" else self.selected_patient_id
        record = self.store.load(patient_id)
        progress = profile_completion(record)
        name = display_name(record)

        x = self.winfo_screenwidth() - width - int(self.S(14))
        y = self.winfo_rooty() + int(self.profile_box[1]) + int(self.S(8))
        x = max(0, min(x, self.winfo_screenwidth() - width))
        y = max(0, min(y, self.winfo_screenheight() - height))

        shadow = tk.Toplevel(self)
        self.dropdown_shadow = shadow
        shadow.overrideredirect(True)
        shadow.configure(bg="#323342")
        try:
            shadow.attributes("-alpha", 0.18)
        except tk.TclError:
            pass
        shadow.geometry(f"{width}x1+{x + int(self.S(6))}+{y + int(self.S(7))}")

        window = tk.Toplevel(self)
        self.dropdown_window = window
        window.overrideredirect(True)
        window.configure(bg=WHITE, bd=1, highlightthickness=1, highlightbackground=BORDER)
        window.geometry(f"{width}x1+{x}+{y}")
        top = tk.Frame(window, bg=WHITE, padx=self.S(18), pady=self.S(14))
        top.pack(fill="x")
        title_row = tk.Frame(top, bg=WHITE)
        title_row.pack(fill="x")
        tk.Label(title_row, text="Profile progress", bg=WHITE, fg=TEXT_DARK,
                 font=self.font(12, "bold")).pack(side="left")
        tk.Label(title_row, text=f"{progress}%", bg=WHITE, fg=TEXT_DARK,
                 font=self.font(12, "bold")).pack(side="right")
        bar = tk.Canvas(top, height=max(5, int(self.S(7))), bg="#e1e2e8",
                        highlightthickness=0, bd=0)
        bar.pack(fill="x", pady=(self.S(8), self.S(2)))
        bar.update_idletasks()
        bar.create_rectangle(0, 0, bar.winfo_width() * progress / 100,
                             max(5, int(self.S(7))), fill=INK, outline="")
        self._profile_menu_separator(window)
        self._profile_menu_button(window, "Settings", lambda: self.go("Settings"))
        self._profile_menu_separator(window)

        profile_row = tk.Frame(window, bg=WHITE, padx=self.S(20), pady=self.S(16))
        profile_row.pack(fill="x")
        initials = "".join(part[:1] for part in name.split()[:2]).upper() or "?"
        badge = tk.Label(profile_row, text=initials, bg="#26263f", fg=WHITE,
                         font=self.font(12, "bold"), width=3, height=1)
        badge.pack(side="left", padx=(0, self.S(14)))
        tk.Label(profile_row, text=name, bg=WHITE, fg=INK,
                 font=self.font(13), anchor="w").pack(side="left", fill="x", expand=True)
        tk.Frame(window, bg=WHITE).pack(fill="both", expand=True)
        self._profile_menu_separator(window)
        self._profile_menu_button(window, "Manage profiles", lambda: self.go("Manage profiles"))
        if self.role == "pharmacist":
            self._profile_menu_separator(window)
            self._profile_menu_button(window, "Reset demo", self.reset_demo)
        self._profile_menu_separator(window)
        self._profile_menu_button(window, "Log out", self.sign_out, color=RED)

        window.bind("<Escape>", lambda _event: self._close_profile_menu())
        self._dropdown_opened_by_click = True
        self.after_idle(lambda: setattr(self, "_dropdown_opened_by_click", False))
        shadow.lift()
        window.lift()
        self.after(10, lambda: self._animate_profile_menu(window, shadow, x, y, width, height, 1))

    def _animate_profile_menu(self, window, shadow, x, y, width, height, visible_height):
        if not window.winfo_exists() or not shadow.winfo_exists():
            return
        visible_height = min(height, visible_height + max(20, int(self.S(40))))
        window.geometry(f"{width}x{visible_height}+{x}+{y}")
        shadow.geometry(
            f"{width}x{visible_height}+{x + int(self.S(6))}+{y + int(self.S(7))}"
        )
        shadow.lift()
        window.lift()
        if visible_height < height:
            self.after(
                10,
                lambda: self._animate_profile_menu(
                    window, shadow, x, y, width, height, visible_height
                ),
            )

    def _profile_menu_separator(self, parent):
        tk.Frame(parent, bg=BORDER, height=max(1, int(self.S(1)))).pack(fill="x")

    def _profile_menu_button(self, parent, label, action, color=INK):
        button = tk.Button(
            parent, text=label, command=lambda: self._dropdown_choose(action),
            bg=WHITE, fg=color, activebackground="#f5f6f8", activeforeground=color,
            relief="flat", bd=0, anchor="w", font=self.font(11), padx=self.S(20),
            pady=self.S(13), cursor="hand2",
        )
        button.pack(fill="x")

    def _close_profile_menu(self):
        window = getattr(self, "dropdown_window", None)
        shadow = getattr(self, "dropdown_shadow", None)
        self.dropdown_window = None
        self.dropdown_shadow = None
        if window and window.winfo_exists():
            window.destroy()
        if shadow and shadow.winfo_exists():
            shadow.destroy()

    def draw_dropdown(self):
        """Kept for old callers: menus are now native pop-ups (see show_menu)."""
        self.dropdown = None

    def _dropdown_choose(self, action):
        self._close_profile_menu()
        self.dropdown = None
        if action:
            action()
        else:
            self.render()

    def close_dropdown_on_outside_click(self, event=None):
        """Close the account panel when a click lands outside it."""
        if getattr(self, "_dropdown_opened_by_click", False):
            self._dropdown_opened_by_click = False
            return
        window = getattr(self, "dropdown_window", None)
        if not window or not window.winfo_exists() or event is None:
            return
        widget_path = str(event.widget)
        window_path = str(window)
        if widget_path != window_path and not widget_path.startswith(window_path + "."):
            self._close_profile_menu()

    def reset_demo(self):
        self.store.reset_demo()
        self.flash("Demo reset: Maria is back to a fresh state.")
