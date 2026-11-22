"""The notifications and profile dropdown menus under the header.

Called by: PillwayApp.render() when self.dropdown is set.
BUG FIX (Manage profiles dropdown): Tk always draws embedded widgets (the profile list,
the chat, scroll areas) ON TOP of canvas drawings, so the old dropdown was hidden behind
them on the Manage profiles page. The dropdown is now its own small canvas placed above
everything with place() + lift(). It closes on Escape, on a second click, or on any
click elsewhere on the page.
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

    def draw_dropdown(self):
        title, items = self.dropdown_items()
        width, row = self.S(340), self.S(66)
        height = self.S(56) + row * len(items) + self.S(8)
        x2 = (self.bell_box[0] + self.S(330)) if self.dropdown == "notifications" else self.w - self.S(18)
        x1, top = min(x2, self.w - self.S(10)) - width, self.S(86)
        menu = tk.Canvas(self, width=int(width), height=int(height), bg=WHITE, highlightthickness=1,
                         highlightbackground=BORDER, bd=0)
        menu.place(x=int(x1), y=int(top))
        menu.tk.call("raise", menu._w)
        self.dropdown_frame = menu
        self.tx(menu, self.S(20), self.S(18), title, 16, INK, "bold")
        y = self.S(56)
        for index, (head, sub, action) in enumerate(items):
            tag = f"dd::{index}"
            menu.create_line(self.S(16), y, width - self.S(16), y, fill=BORDER)
            menu.create_rectangle(2, y + 1, width - 2, y + row - 1, fill=WHITE, outline=WHITE, tags=tag)
            if sub:
                self.tx(menu, self.S(20), y + self.S(10), head, 14, INK, "bold", tag=tag)
                self.tx(menu, self.S(20), y + self.S(36), sub, 12, TEXT_MUTED, tag=tag, width=width - self.S(40))
            else:
                self.tx(menu, self.S(20), y + row / 2, head, 14, RED, "bold", anchor="w", tag=tag)
            self.bind_click(menu, tag, lambda a=action: self._dropdown_choose(a))
            y += row
        self._dropdown_opened_by_click = True
        self.after_idle(self._arm_dropdown_close)

    def _arm_dropdown_close(self):
        self._dropdown_opened_by_click = False

    def _dropdown_choose(self, action):
        self.dropdown = None
        if action:
            action()
        else:
            self.render()

    def close_dropdown_on_outside_click(self, _event=None):
        if self.dropdown and not getattr(self, "_dropdown_opened_by_click", False):
            self.after_idle(lambda: self.dropdown and self.toggle_dropdown(None))

    def reset_demo(self):
        self.store.reset_demo()
        self.flash("Demo reset: Maria is back to a fresh state.")
