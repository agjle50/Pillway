"""The account and notifications menus, and the shared in-window menu (popover)."""

import tkinter as tk

from ...storage.patient_store import display_name
from ..patient.manage_profiles import profile_completion
from ..theme import BORDER, BORDER_SOFT, HOVER, INK, NAVY, RED, TEXT_DARK, TEXT_MUTED, WHITE


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
        """Open the account menu or the notifications menu (both inside the app window)."""
        if which == "profile":
            self._show_profile_menu()
            self._popover_kind = which
            return
        self.dropdown = which
        title, items = self.dropdown_items()
        self.dropdown = None
        width = int(self.S(360))
        anchor_x, anchor_y = self.bell_box
        menu_items = [(head, action, TEXT_MUTED if action is None else INK, sub) for head, sub, action in items]
        self._show_branded_menu(self.winfo_rootx() + int(anchor_x + self.S(44)) - width,
                                self.winfo_rooty() + int(anchor_y + self.S(8)), menu_items, title=title, width=width)
        self._popover_kind = which

    @staticmethod
    def _notification_time(value):
        value = str(value or "")
        return value[11:16] if len(value) >= 16 else value

    # ---- the shared popover ---------------------------------------------------------------

    def _open_popover(self, x, y, width):
        """Create an empty menu panel at screen point (x, y), kept inside the app window.

        BUG FIX: menus used to be separate windows (Toplevel / tk.Menu), so they could hang
        outside the app and showed up as extra windows. This is a frame INSIDE the window.
        """
        self._close_branded_menu()
        frame = tk.Frame(self, bg=WHITE, bd=0, highlightthickness=1, highlightbackground=BORDER)
        frame._pillway_anchor = (x - self.winfo_rootx(), y - self.winfo_rooty(), int(width))
        self._branded_menu_window = frame
        self.dropdown_window = frame
        if not getattr(self, "_popover_bindings", False):
            self.bind_all("<Button-1>", self._close_branded_menu_on_outside, add="+")
            self.bind_all("<Escape>", lambda _e: self._close_branded_menu(), add="+")
            self._popover_bindings = True
        # The click that opened the menu must not also count as a click "outside" it.
        # BUG FIX: this used after_idle(), but placing the menu runs update_idletasks(),
        # which fired that reset immediately, so the same click closed the menu again.
        self._popover_opened_now = True
        self.after(250, lambda: setattr(self, "_popover_opened_now", False))
        return frame

    def _place_popover(self, frame):
        """Place the finished panel, clamped so it never goes past the window's edges."""
        lx, ly, width = frame._pillway_anchor
        frame.update_idletasks()
        height = frame.winfo_reqheight()
        win_w, win_h = max(self.winfo_width(), width + 16), max(self.winfo_height(), 200)
        lx = max(8, min(lx, win_w - width - 8))
        if ly + height > win_h - 8:
            ly = max(8, win_h - height - 8)
        frame.place(x=lx, y=ly, width=width)
        frame.lift()

    def lift_popover(self):
        """Keep an open menu above widgets that were rebuilt by a redraw."""
        frame = getattr(self, "_branded_menu_window", None)
        if frame is not None and frame.winfo_exists():
            frame.lift()

    def _menu_row(self, parent, label, action, color=INK, sub="", badge=None, selected=False):
        """One menu row: grey on hover, runs `action` when clicked (disabled if action is None)."""
        row = tk.Frame(parent, bg=WHITE, padx=self.S(16), pady=self.S(11), cursor="hand2" if action else "arrow")
        row.pack(fill="x")
        parts = [row]
        if badge:
            tile = tk.Label(row, text=badge, bg=NAVY, fg=WHITE, font=self.font(12, "bold"),
                            width=3, padx=self.S(2), pady=self.S(3))
            tile.pack(side="left", padx=(0, self.S(12)))
        text_box = tk.Frame(row, bg=WHITE)
        text_box.pack(side="left", fill="x", expand=True)
        parts.append(text_box)
        main = tk.Label(text_box, text=self.tr(label), bg=WHITE, fg=color, anchor="w", justify="left",
                        font=self.font(14, "bold" if selected else "normal"))
        main.pack(fill="x")
        parts.append(main)
        if sub:
            detail = tk.Label(text_box, text=self.tr(sub), bg=WHITE, fg=TEXT_MUTED, anchor="w", justify="left",
                              font=self.font(12), wraplength=max(120, int(self.S(280))))
            detail.pack(fill="x")
            parts.append(detail)
        if selected:
            mark = tk.Label(row, text="\u2713", bg=WHITE, fg=RED, font=self.font(14, "bold"))
            mark.pack(side="right")
            parts.append(mark)
        if action is None:
            return row

        def shade(colour):
            for part in parts:
                part.configure(bg=colour)
        for part in parts:
            part.bind("<Enter>", lambda _e: shade(HOVER), add="+")
            part.bind("<Leave>", lambda _e: shade(WHITE), add="+")
            part.bind("<Button-1>", lambda _e: self._dropdown_choose(action), add="+")
        return row

    def _menu_separator(self, parent):
        tk.Frame(parent, bg=BORDER_SOFT, height=max(1, int(self.S(1)))).pack(fill="x")

    def _show_branded_menu(self, x, y, items, title=None, width=None, row_height=None):
        """A simple list menu at screen point (x, y). items: (label, action, colour[, subtitle])."""
        frame = self._open_popover(x, y, width or self.S(260))
        if title:
            tk.Label(frame, text=self.tr(title), bg=WHITE, fg=TEXT_DARK, font=self.font(14, "bold"), anchor="w",
                     padx=self.S(16), pady=self.S(10)).pack(fill="x")
            self._menu_separator(frame)
        for label, action, color, *rest in items:
            self._menu_row(frame, label, action, color, sub=rest[0] if rest else "")
        self._place_popover(frame)

    def _show_profile_menu(self):
        """Account menu: profile progress, Settings, EVERY account (click to switch), Manage, Log out."""
        width = int(self.S(330))
        x = self.winfo_rootx() + int(self.w - self.S(14)) - width
        y = self.winfo_rooty() + int(self.profile_box[1] + self.S(8))
        frame = self._open_popover(x, y, width)

        patient_id = self.patient_id if self.role == "patient" else self.selected_patient_id
        progress = profile_completion(self.store.load(patient_id))
        top = tk.Frame(frame, bg=WHITE, padx=self.S(16), pady=self.S(14))
        top.pack(fill="x")
        title_row = tk.Frame(top, bg=WHITE)
        title_row.pack(fill="x")
        tk.Label(title_row, text=self.tr("Profile progress"), bg=WHITE, fg=TEXT_DARK,
                 font=self.font(13, "bold")).pack(side="left")
        tk.Label(title_row, text=f"{progress}%", bg=WHITE, fg=TEXT_DARK,
                 font=self.font(13, "bold")).pack(side="right")
        bar_h = max(6, int(self.S(7)))
        bar = tk.Canvas(top, height=bar_h, bg="#e1e2e8", highlightthickness=0, bd=0)
        bar.pack(fill="x", pady=(self.S(8), 0))

        def draw_bar(event):
            # BUG FIX: the bar used to be drawn before it had a width (0 px), so it never filled.
            bar.delete("fill")
            bar.create_rectangle(0, 0, event.width * progress / 100, bar_h, fill=NAVY, outline="", tags="fill")
        bar.bind("<Configure>", draw_bar)

        self._menu_separator(frame)
        self._menu_row(frame, "Settings", lambda: self.go("Settings"))
        self._menu_separator(frame)
        for role, heading in (("Patient", "Patient accounts"), ("Pharmacist", "Pharmacist accounts")):
            profiles = [p for p in self.profiles.values() if p["role"] == role]
            if not profiles:
                continue
            tk.Label(frame, text=self.tr(heading), bg=WHITE, fg=TEXT_MUTED, font=self.font(12, "bold"),
                     anchor="w", padx=self.S(16), pady=self.S(6)).pack(fill="x")
            for profile in profiles:
                name = profile.get("name", "Account")
                badge = "".join(part[:1] for part in name.split()[:2]).upper() or "?"
                current = profile["id"] == self.active_profile_id and (
                    (role == "Patient") == (self.role == "patient"))
                action = None if current else (lambda pid=profile["id"]: self.switch_profile(pid))
                self._menu_row(frame, name, action, INK, badge=badge, selected=current)
        self._menu_separator(frame)
        self._menu_row(frame, "Manage profiles", lambda: self.go("Manage profiles"))
        if self.role == "pharmacist":
            self._menu_row(frame, "Reset demo", self.reset_demo)
        self._menu_separator(frame)
        self._menu_row(frame, "Log out", self.sign_out, color=RED)
        self._place_popover(frame)

    def _close_branded_menu(self):
        frame = getattr(self, "_branded_menu_window", None)
        self._branded_menu_window = None
        self.dropdown_window = None
        self._popover_kind = None
        if frame is not None and frame.winfo_exists():
            frame.destroy()

    _close_profile_menu = _close_branded_menu

    def _close_branded_menu_on_outside(self, event=None):
        frame = getattr(self, "_branded_menu_window", None)
        if frame is None or getattr(self, "_popover_opened_now", False) or event is None:
            return
        try:
            if not frame.winfo_exists():
                return
            widget_path, frame_path = str(event.widget), str(frame)
        except Exception:
            return
        if widget_path != frame_path and not widget_path.startswith(frame_path + "."):
            self.after_idle(self._close_branded_menu)

    def draw_dropdown(self):
        """Kept for old callers: menus are popovers now (see show_menu)."""
        self.dropdown = None

    def _dropdown_choose(self, action):
        self._close_branded_menu()
        self.dropdown = None
        if action:
            action()
        else:
            self.render()

    def close_dropdown_on_outside_click(self, event=None):
        """Old canvas binding; the popover handles outside clicks itself."""

    def reset_demo(self):
        self.store.reset_demo()
        self.flash("Demo reset: Maria is back to a fresh state.")
