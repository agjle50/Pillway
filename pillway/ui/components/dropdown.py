"""The notifications and profile dropdown menus under the header.

Called by: PillwayApp.render() when self.dropdown is set.
BUG FIX: both menus are now native pop-up menus (tk.Menu). They always appear above
the chat and lists, always show their text, and close on Esc or a click elsewhere.
"""

import tkinter as tk

from ...storage.patient_store import display_name
from ..theme import BORDER, INK, RED, TEXT_MUTED, WHITE


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
        """Open the profile or notifications menu as a native pop-up menu.

        BUG FIX (white empty box you couldn't close): the old menu was a small drawing
        canvas placed over the page. On some Windows setups it showed up blank and
        swallowed clicks, so it couldn't be closed. A native Tk menu is drawn by Windows
        or macOS itself: it always shows its text, sits above everything (including the
        chat and lists), and closes when you click anywhere else or press Esc.
        """
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

    def draw_dropdown(self):
        """Kept for old callers: menus are now native pop-ups (see show_menu)."""
        self.dropdown = None

    def _dropdown_choose(self, action):
        self.dropdown = None
        if action:
            action()
        else:
            self.render()

    def close_dropdown_on_outside_click(self, _event=None):
        """Native menus close themselves; nothing to do (kept so old bindings still work)."""

    def reset_demo(self):
        self.store.reset_demo()
        self.flash("Demo reset: Maria is back to a fresh state.")
