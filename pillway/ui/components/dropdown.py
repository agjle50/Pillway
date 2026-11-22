"""The notifications and account menus under the header."""

import tkinter as tk

from ...storage.patient_store import display_name
from ..patient.manage_profiles import profile_completion
from ..theme import BORDER, BORDER_SOFT, HOVER, INK, PAGE_BG, RED, SHADOW, TEXT_DARK, TEXT_MUTED, WHITE


class DropdownMixin:
    def dropdown_items(self):
        if self.dropdown == "notifications":
            if self.role == "pharmacist":
                items = [
                    (display_name(record), DropdownMixin._notification_time(request.get("time")),
                     lambda pid=record["id"]: self.select_doctor_patient(pid))
                    for record in self.store.all()
                    for request in record["pharmacist_requests"]
                    if request["status"] == "open"
                ]
                items.extend(
                    (display_name(record), DropdownMixin._notification_time(flag.get("time")),
                     lambda pid=record["id"]: self.select_doctor_patient(pid))
                    for record in self.store.all()
                    for flag in record["flags"]
                    if flag["status"] == "open" and flag["tier"] == 1
                )
                return "Notifications", items or [("No notifications", "You're all caught up.", None)]
            items = []
            for notification in self.notifications:
                if len(notification) >= 2:
                    items.append(
                        (str(notification[0]), DropdownMixin._notification_time(notification[1]), None)
                    )
            return "Notifications", items or [("No notifications yet", "New updates will appear here.", None)]
        items = [("Manage profiles", "Switch between demo accounts", lambda: self.go("Manage profiles")),
                 ("Settings", "Account, payments, notifications", lambda: self.go("Settings"))]
        if self.role == "pharmacist":
            items.append(("Reset demo", "Restore Maria to a fresh state", self.reset_demo))
        items.append(("Sign out", "", self.sign_out))
        return ("Pharmacist" if self.role == "pharmacist" else display_name(self.record or {"id": "Patient"})), items

    def show_menu(self, which):
        """Open the account or branded notifications popover."""
        if which == "profile":
            self._show_profile_menu()
            return
        self.dropdown = which
        title, items = self.dropdown_items()
        self.dropdown = None
        anchor_x, anchor_y = self.bell_box
        width = int(self.S(340))
        x = self.winfo_rootx() + int(anchor_x) - width + int(self.S(28))
        y = self.winfo_rooty() + int(anchor_y) + int(self.S(8))
        menu_items = [
            (head, action, TEXT_MUTED if action is None else INK, sub)
            for head, sub, action in items
        ]
        self._show_branded_menu(x, y, menu_items, title=title, width=width)

    @staticmethod
    def _notification_time(value):
        value = str(value or "")
        return value[11:16] if len(value) >= 16 else value

    def _show_branded_menu(self, x, y, items, title=None, width=None, row_height=None):
        self._close_branded_menu()
        self._close_profile_menu()
        width = int(width or self.S(280))
        row_height = int(row_height or self.S(48))
        title_height = int(self.S(46)) if title else 0
        content_height = title_height + row_height * len(items) + self.S(12)
        height = min(int(content_height), self.winfo_screenheight() - int(self.S(28)))
        x = max(0, min(int(x), self.winfo_screenwidth() - width))
        y = max(0, min(int(y), self.winfo_screenheight() - height))

        shadow = tk.Toplevel(self)
        self._branded_menu_shadow = shadow
        shadow.overrideredirect(True)
        shadow.configure(bg=SHADOW)
        try:
            shadow.attributes("-alpha", 0.1)
        except tk.TclError:
            pass
        shadow.geometry(f"{width}x{height}+{x + self.S(3):.0f}+{y + self.S(4):.0f}")

        window = tk.Toplevel(self)
        self._branded_menu_window = window
        window.overrideredirect(True)
        window.configure(bg=PAGE_BG)
        window.geometry(f"{width}x{height}+{x}+{y}")
        panel = tk.Canvas(window, width=width, height=height, bg=PAGE_BG,
                          bd=0, highlightthickness=0)
        panel.pack(fill="both", expand=True)
        radius, inset = self.S(14), self.S(4)
        panel.create_polygon(
            inset + radius, inset, width - inset - radius, inset,
            width - inset, inset, width - inset, inset + radius,
            width - inset, height - inset - radius, width - inset, height - inset,
            width - inset - radius, height - inset, inset + radius, height - inset,
            inset, height - inset, inset, height - inset - radius,
            inset, inset + radius, inset, inset,
            smooth=True, fill=WHITE, outline=BORDER_SOFT, width=1,
        )
        body = tk.Frame(panel, bg=WHITE, padx=self.S(6), pady=self.S(6))
        panel.create_window(inset, inset, window=body, anchor="nw",
                            width=width - inset * 2, height=height - inset * 2)
        if title:
            tk.Label(body, text=title, bg=WHITE, fg=TEXT_DARK,
                     font=self.font(12, "bold"), anchor="w",
                     padx=self.S(12)).pack(fill="x", ipady=self.S(8))
            tk.Frame(body, bg=BORDER_SOFT, height=1).pack(fill="x")
        for label, action, color, *subtitles in items:
            display = label if not subtitles or not subtitles[0] else f"{label}    {subtitles[0]}"
            button = tk.Button(
                body, text=display, command=lambda selected=action: self._dropdown_choose(selected),
                bg=WHITE, fg=color, activebackground=HOVER, activeforeground=color,
                relief="flat", bd=0, anchor="w", justify="left",
                font=self.font(11), padx=self.S(12), pady=self.S(10),
                cursor="hand2" if action else "arrow",
                state="normal" if action else "disabled",
            )
            button.pack(fill="x")
            button.bind("<Enter>", lambda _event, b=button: b.configure(bg=HOVER), add="+")
            button.bind("<Leave>", lambda _event, b=button: b.configure(bg=WHITE), add="+")
        window.bind("<Escape>", lambda _event: self._close_branded_menu())
        shadow.lift()
        window.lift()
        if not getattr(self, "_branded_menu_click_binding", None):
            self._branded_menu_click_binding = self.bind_all(
                "<Button-1>", self._close_branded_menu_on_outside, add="+"
            )

    def _close_branded_menu(self):
        for name in ("_branded_menu_window", "_branded_menu_shadow"):
            window = getattr(self, name, None)
            setattr(self, name, None)
            if window and window.winfo_exists():
                window.destroy()

    def _close_branded_menu_on_outside(self, event=None):
        window = getattr(self, "_branded_menu_window", None)
        if not window or not window.winfo_exists() or event is None:
            return
        path = str(event.widget)
        if path != str(window) and not path.startswith(str(window) + "."):
            self._close_branded_menu()

    def _show_profile_menu(self):
        self._close_branded_menu()
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
        shadow.configure(bg=SHADOW)
        try:
            shadow.attributes("-alpha", 0.1)
        except tk.TclError:
            pass
        shadow.geometry(f"{width}x1+{x + int(self.S(3))}+{y + int(self.S(4))}")

        window = tk.Toplevel(self)
        self.dropdown_window = window
        window.overrideredirect(True)
        window.configure(bg=PAGE_BG, bd=0, highlightthickness=0)
        window.geometry(f"{width}x1+{x}+{y}")
        panel = tk.Canvas(window, bg=PAGE_BG, bd=0, highlightthickness=0)
        panel.pack(fill="both", expand=True)
        inset, radius = self.S(4), self.S(16)
        shape = panel.create_polygon(
            inset + radius, inset, width - inset - radius, inset,
            width - inset, inset, width - inset, inset + radius,
            width - inset, height - inset - radius, width - inset, height - inset,
            width - inset - radius, height - inset, inset + radius, height - inset,
            inset, height - inset, inset, height - inset - radius,
            inset, inset + radius, inset, inset,
            smooth=True, fill=WHITE, outline=BORDER_SOFT, width=1,
        )
        body = tk.Frame(panel, bg=WHITE, padx=self.S(6), pady=self.S(6))
        body_window = panel.create_window(
            inset, inset, window=body, anchor="nw",
            width=width - inset * 2, height=height - inset * 2,
        )

        def resize(event):
            panel.coords(
                shape,
                inset + radius, inset, event.width - inset - radius, inset,
                event.width - inset, inset, event.width - inset, inset + radius,
                event.width - inset, height - inset - radius, event.width - inset, height - inset,
                event.width - inset - radius, height - inset, inset + radius, height - inset,
                inset, height - inset, inset, height - inset - radius,
                inset, inset + radius, inset, inset,
            )
            panel.itemconfigure(body_window, width=event.width - inset * 2)

        panel.bind("<Configure>", resize, add="+")
        top = tk.Frame(body, bg=WHITE, padx=self.S(14), pady=self.S(10))
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
        self._profile_menu_separator(body)
        self._profile_menu_button(body, "Settings", lambda: self.go("Settings"))
        self._profile_menu_separator(body)

        profile_row = tk.Frame(body, bg=WHITE, padx=self.S(16), pady=self.S(12))
        profile_row.pack(fill="x")
        initials = "".join(part[:1] for part in name.split()[:2]).upper() or "?"
        badge = tk.Label(profile_row, text=initials, bg="#26263f", fg=WHITE,
                         font=self.font(12, "bold"), width=3, height=1)
        badge.pack(side="left", padx=(0, self.S(14)))
        tk.Label(profile_row, text=name, bg=WHITE, fg=INK,
                 font=self.font(13), anchor="w").pack(side="left", fill="x", expand=True)
        tk.Frame(body, bg=WHITE).pack(fill="both", expand=True)
        self._profile_menu_separator(body)
        self._profile_menu_button(body, "Manage profiles", lambda: self.go("Manage profiles"))
        if self.role == "pharmacist":
            self._profile_menu_separator(body)
            self._profile_menu_button(body, "Reset demo", self.reset_demo)
        self._profile_menu_separator(body)
        self._profile_menu_button(body, "Log out", self.sign_out, color=RED)

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
            f"{width}x{visible_height}+{x + int(self.S(3))}+{y + int(self.S(4))}"
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
            bg=WHITE, fg=color, activebackground=HOVER, activeforeground=color,
            relief="flat", bd=0, anchor="w", font=self.font(11), padx=self.S(20),
            pady=self.S(13), cursor="hand2",
        )
        button.pack(fill="x")
        button.bind("<Enter>", lambda _event: button.configure(bg=HOVER), add="+")
        button.bind("<Leave>", lambda _event: button.configure(bg=WHITE), add="+")

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
        self._close_branded_menu()
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
