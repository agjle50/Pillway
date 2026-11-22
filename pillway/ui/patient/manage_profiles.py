"""Profile editor and account switching page."""

import tkinter as tk
from tkinter import filedialog, messagebox

from ..theme import (
    BORDER,
    BORDER_SOFT,
    HOVER,
    INK,
    PAGE_BG,
    RED,
    SHADOW,
    TEXT_MUTED,
    WHITE,
)

PROFILE_FIELDS = (
    ("Personal information", (
        ("First name*", "first_name", "entry"),
        ("Last name*", "last_name", "entry"),
        ("Date of birth*", "date_of_birth", "entry"),
        ("Phone number*", "phone", "entry"),
        ("Sex at birth*", "sex", "sex"),
        ("Relationship", "relationship", "relationship"),
        ("Email", "email", "entry"),
    )),
    ("Health card", (
        ("Health card number (optional)", "health_card", "entry"),
    )),
    ("Insurance", (
        ("Cardholder name", "insurance_cardholder", "entry"),
        ("Insurance provider", "insurance_provider", "entry"),
        ("Carrier number", "insurance_carrier_number", "entry"),
        ("Contract/group number", "insurance_group_number", "entry"),
        ("Member ID/certificate number", "insurance_member_number", "entry"),
    )),
    ("Delivery address", (
        ("Street number and name*", "street_address", "entry"),
        ("Province*", "province", "province"),
        ("City*", "city", "entry"),
        ("Postal code*", "postal_code", "entry"),
        ("Unit or apartment number", "apartment", "entry"),
        ("Entry or buzzer code", "buzzer_code", "entry"),
        ("Delivery instructions", "delivery_instructions", "entry"),
    )),
)

PHOTO_FIELDS = ("insurance_card_front", "insurance_card_back")
COMPLETION_FIELDS = tuple(
    field for _, fields in PROFILE_FIELDS for _, field, _ in fields
) + PHOTO_FIELDS
PROFILE_PAGES = PROFILE_FIELDS + (("Insurance card photos", ()),)


def profile_form_values(profile):
    address = str(profile.get("address") or "")
    parts = [part.strip() for part in address.split(",") if part.strip()]
    street = profile.get("street_address") or (parts[0] if parts else "")
    city = profile.get("city") or ""
    province = profile.get("province") or ""
    if len(parts) > 1 and not city:
        location = parts[-1].split()
        if location and len(location[-1]) == 2 and location[-1].isalpha():
            province = province or location.pop().upper()
        city = " ".join(location)
    province = {
        "AB": "Alberta", "BC": "British Columbia", "MB": "Manitoba",
        "NB": "New Brunswick", "NL": "Newfoundland and Labrador",
        "NS": "Nova Scotia", "NT": "Northwest Territories", "NU": "Nunavut",
        "ON": "Ontario", "PE": "Prince Edward Island", "QC": "Quebec",
        "SK": "Saskatchewan", "YT": "Yukon",
    }.get(str(province).upper(), province)

    values = {
        key: str(profile.get(key) or "")
        for _, fields in PROFILE_FIELDS
        for _, key, _ in fields
    }
    values.update(
        street_address=str(street),
        city=str(city),
        province=str(province),
        insurance_card_front=str(profile.get("insurance_card_front") or ""),
        insurance_card_back=str(profile.get("insurance_card_back") or ""),
    )
    return values


def format_profile_address(values):
    street = values.get("street_address", "").strip()
    city = values.get("city", "").strip()
    province = values.get("province", "").strip()
    postal_code = values.get("postal_code", "").strip()
    location = " ".join(part for part in (city, province, postal_code) if part)
    return ", ".join(part for part in (street, location) if part)


def profile_completion(record):
    values = profile_form_values(record.get("profile", {}))
    completed = sum(bool(values.get(field, "").strip()) for field in COMPLETION_FIELDS)
    return round(completed * 100 / len(COMPLETION_FIELDS))


class ManageProfilesMixin:
    def draw_manage_profiles(self):
        y = self.page_title("Manage Profiles")
        x1, x2 = self.sw + self.S(32), self.w - self.S(32)
        button_w, button_h = self.S(190), self.S(42)
        bx1, by1 = x2 - button_w, y + self.S(10)
        self.rrect(bx1, by1, x2, by1 + button_h, self.S(10), fill=RED,
                   outline="", tags="add_patient_profile")
        self.text((bx1 + x2) / 2, by1 + button_h / 2, "Add patient profile",
                  13, WHITE, "bold", anchor="center", tag="add_patient_profile")
        self.clickable("add_patient_profile", self.add_patient_profile)
        delete_x1 = bx1 - button_w - self.S(10)
        self.rrect(delete_x1, by1, bx1 - self.S(10), by1 + button_h, self.S(10),
                   fill=WHITE, outline=BORDER, width=self.S(1), tags="delete_all_local_data")
        self.text((delete_x1 + bx1 - self.S(10)) / 2, by1 + button_h / 2,
                  "Delete saved data", 12, RED, "bold", anchor="center",
                  tag="delete_all_local_data")
        self.clickable("delete_all_local_data", self.delete_all_local_data)
        if self.profile_status:
            self.text(x1, y + self.S(130), self.profile_status, 13, RED)
        y += self.S(151)
        list_y = y
        list_w = x2 - x1
        list_h = max(self.S(80), self.h - list_y - self.S(20))
        outer = tk.Frame(self, bg=PAGE_BG, bd=0, highlightthickness=0)
        self.profiles_view_frame = outer
        canvas = tk.Canvas(outer, bg=PAGE_BG, bd=0, highlightthickness=0)
        scrollbar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        body = tk.Frame(canvas, bg=PAGE_BG, padx=max(10, int(self.S(4))))
        body_window = canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>", lambda *_: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(body_window, width=event.width))
        role_labels = (("Patient", "Patient profiles"), ("Pharmacist", "Pharmacist profiles"))
        for role, label in role_labels:
            profiles = [profile for profile in self.profiles.values() if profile["role"] == role]
            if not profiles:
                continue
            tk.Label(body, text=label, bg=PAGE_BG, fg=INK,
                     font=self.font(18, "bold"), anchor="w").pack(
                         fill="x", pady=(self.S(12), self.S(8)))
            for profile in profiles:
                self._draw_profile_card(body, profile)
        self._bind_profile_scroll(body, canvas)
        canvas.configure(height=max(1, int(list_h)))
        self.c.create_window(
            x1, list_y, window=outer, anchor="nw",
            width=max(1, int(list_w)), height=max(1, int(list_h)),
        )

    def _draw_profile_card(self, parent, profile):
        height = max(1, int(self.S(156)))
        card = tk.Canvas(parent, bg=PAGE_BG, bd=0, highlightthickness=0, height=height)
        card.pack(fill="x", pady=(0, self.S(10)))
        content = tk.Frame(card, bg=WHITE, padx=self.S(16), pady=self.S(12))
        window = card.create_window(self.S(14), self.S(10), window=content, anchor="nw")

        def rounded(width, item_height, offset=0):
            radius = self.S(16)
            top = self.S(3) + offset
            left, right = self.S(4), width - self.S(4)
            bottom = item_height - self.S(4) + offset
            return [
                left + radius, top, right - radius, top, right, top, right, top + radius,
                right, bottom - radius, right, bottom, right - radius, bottom,
                left + radius, bottom, left, bottom, left, bottom - radius, left, top + radius,
                left, top,
            ]

        shadow = card.create_polygon(
            *rounded(800, height, self.S(3)), smooth=True, fill=SHADOW, outline=""
        )
        surface = card.create_polygon(
            *rounded(800, height), smooth=True, fill=WHITE, outline=BORDER_SOFT, width=1
        )
        card.tag_lower(shadow)
        card.tag_lower(surface)

        def resize(event):
            card.coords(shadow, *rounded(event.width, height, self.S(3)))
            card.coords(surface, *rounded(event.width, height))
            card.itemconfigure(window, width=max(1, event.width - self.S(28)))

        card.bind("<Configure>", resize, add="+")
        details = tk.Frame(content, bg=WHITE)
        details.pack(fill="x")
        tk.Label(details, text=profile["name"], bg=WHITE, fg=INK,
                 font=self.font(16, "bold"), anchor="w").pack(side="left")
        if profile["id"] == self.active_profile_id:
            tk.Label(details, text="Current profile", bg="#f5f6f8", fg=TEXT_MUTED,
                     font=self.font(10, "bold"), padx=self.S(9), pady=self.S(4)).pack(side="right")
        tk.Label(content, text=profile.get("description", ""), bg=WHITE, fg=TEXT_MUTED,
                 font=self.font(11), anchor="w", wraplength=max(200, int(self.S(700)))).pack(
                     fill="x", pady=(self.S(5), self.S(12)))
        actions = tk.Frame(content, bg=WHITE)
        actions.pack(fill="x")
        tk.Button(
            actions, text="Switch profile",
            command=lambda selected=profile["id"]: self.switch_profile(selected),
            state="disabled" if profile["id"] == self.active_profile_id else "normal",
            bg="#fff0ed", fg=RED, activebackground="#ffe5df",
            relief="flat", bd=0, font=self.font(11, "bold"), cursor="hand2",
            padx=self.S(14), pady=self.S(8),
        ).pack(side="right")
        menu_button = tk.Button(
            actions, text="⋯", command=lambda selected=profile["id"]:
            self._show_profile_actions(selected, menu_button),
            bg=WHITE, fg=INK, activebackground="#f5f6f8",
            relief="flat", bd=0, highlightthickness=1,
            highlightbackground=BORDER_SOFT, font=self.font(18, "bold"), cursor="hand2",
            padx=self.S(10), pady=self.S(3),
        )
        menu_button.pack(side="right", padx=(0, self.S(8)))

        def set_hover(active):
            color = HOVER if active else WHITE
            card.itemconfigure(surface, fill=color)
            self._set_profile_card_color(content, color)

        def switch_from_card(_event=None):
            if profile["id"] != self.active_profile_id:
                self.switch_profile(profile["id"])
            return "break"

        def bind_card(widget):
            if isinstance(widget, tk.Button):
                widget.bind("<Enter>", lambda *_: set_hover(True), add="+")
                widget.bind("<Leave>", lambda *_: set_hover(False), add="+")
                return
            widget.bind("<Enter>", lambda *_: set_hover(True), add="+")
            widget.bind("<Leave>", lambda *_: set_hover(False), add="+")
            widget.bind("<Button-1>", switch_from_card, add="+")
            for child in widget.winfo_children():
                bind_card(child)

        bind_card(card)
        card.bind("<Enter>", lambda *_: set_hover(True), add="+")
        card.bind("<Leave>", lambda *_: set_hover(False), add="+")

    def _set_profile_card_color(self, widget, color):
        try:
            widget.configure(bg=color)
        except tk.TclError:
            return
        for child in widget.winfo_children():
            if not isinstance(child, tk.Button):
                self._set_profile_card_color(child, color)

    def _show_profile_actions(self, profile_id, button):
        profile = self.profiles[profile_id]
        role_count = sum(item["role"] == profile["role"] for item in self.profiles.values())
        items = []
        if profile["role"] == "Patient":
            items.append(
                ("Edit profile", lambda: self.edit_profile(profile_id), INK)
            )
        items.append(
            ("Switch profile",
             lambda: self.switch_profile(profile_id)
             if profile_id != self.active_profile_id else None,
             INK if profile_id != self.active_profile_id else TEXT_MUTED)
        )
        items.append(
            ("Delete profile",
             lambda: self.delete_profile(profile_id) if role_count > 1 else None,
             RED if role_count > 1 else TEXT_MUTED)
        )
        width = int(self.S(220))
        x = button.winfo_rootx() + button.winfo_width() - width
        y = button.winfo_rooty() + button.winfo_height()
        self._show_branded_menu(x, y, items, width=width, row_height=int(self.S(46)))

    def edit_profile(self, profile_id):
        if profile_id not in self.profiles:
            raise ValueError(f"Unknown profile: {profile_id}")
        if self.profiles[profile_id]["role"] != "Patient":
            raise ValueError("Only patient profiles have editable health information.")
        self.profile_edit_record_id = self.profiles[profile_id].get("record_id") or profile_id
        self.profile_page_index = 0
        self.profile_status = ""
        self.section = "Edit profile"
        self.render()

    def draw_profile_editor(self):
        profile_id = getattr(self, "profile_edit_record_id", None)
        if not profile_id:
            self.section = "Manage profiles"
            self.render()
            return
        record = self.store.load(profile_id)
        y = self.page_title("Edit Profile")
        x1, x2 = self.sw + self.S(32), self.w - self.S(32)
        back_x, back_y = x1, y + self.S(8)
        self.rrect(back_x, back_y, back_x + self.S(130), back_y + self.S(40),
                   self.S(9), fill=WHITE, outline=BORDER, tags="profiles_back")
        self.text(back_x + self.S(65), back_y + self.S(20), "Back to profiles",
                  11, INK, "bold", anchor="center", tag="profiles_back")
        self.clickable("profiles_back", lambda: self.go("Manage profiles"))

        panel_y = back_y + self.S(54)
        panel_h = max(self.S(300), self.h - panel_y - self.S(20))
        panel = tk.Frame(self, bg=WHITE, bd=0, highlightthickness=1, highlightbackground=BORDER)
        self.profiles_view_frame = panel
        panel.pack_propagate(False)
        panel_body = tk.Frame(panel, bg=WHITE, padx=self.S(26), pady=self.S(20))
        panel_body.pack(fill="both", expand=True)
        heading = tk.Frame(panel_body, bg=WHITE)
        heading.pack(fill="x", pady=(0, self.S(16)))
        tk.Label(heading, text=record.get("profile", {}).get("first_name", "Patient"),
                 bg=WHITE, fg=INK, font=self.font(19, "bold"), anchor="w").pack(side="left")
        tk.Label(heading, text="Swipe left or right to move between sections",
                 bg=WHITE, fg=TEXT_MUTED, font=self.font(11), anchor="e").pack(side="right")

        values = self._profile_variables(record)
        page_index = min(max(getattr(self, "profile_page_index", 0), 0), len(PROFILE_PAGES) - 1)
        self.profile_page_index = page_index
        title, fields = PROFILE_PAGES[page_index]
        page = tk.Frame(panel_body, bg=WHITE, bd=0, highlightthickness=1,
                        highlightbackground=BORDER, padx=self.S(22), pady=self.S(18))
        page.pack(fill="both", expand=True)
        tk.Label(page, text=title, bg=WHITE, fg=INK,
                 font=self.font(17, "bold"), anchor="w").pack(fill="x", pady=(0, self.S(5)))
        tk.Label(page, text=f"Section {page_index + 1} of {len(PROFILE_PAGES)}",
                 bg=WHITE, fg=TEXT_MUTED, font=self.font(10), anchor="w").pack(
                     fill="x", pady=(0, self.S(12)))
        if fields:
            grid = tk.Frame(page, bg=WHITE)
            grid.pack(fill="x", anchor="n")
            for column in range(2):
                grid.grid_columnconfigure(column, weight=1, uniform="profile_field")
            for index, (label, key, kind) in enumerate(fields):
                cell = tk.Frame(grid, bg=WHITE)
                cell.grid(
                    row=index // 2, column=index % 2, sticky="ew",
                    padx=(0, self.S(10)) if index % 2 == 0 else (self.S(10), 0),
                    pady=(0, self.S(10)),
                )
                self._profile_field(cell, label, values[key], kind)
        else:
            self._draw_insurance_uploads(page, values)

        controls = tk.Frame(panel_body, bg=WHITE)
        controls.pack(fill="x", pady=(self.S(14), 0))
        tk.Button(
            controls, text="Previous", command=lambda: self._set_profile_page(page_index - 1),
            state="normal" if page_index else "disabled",
            bg=HOVER, fg=INK, relief="flat", bd=0,
            font=self.font(11), cursor="hand2", padx=self.S(12), pady=self.S(7),
        ).pack(side="left")
        dots = tk.Frame(controls, bg=WHITE)
        dots.pack(side="left", expand=True)
        for index in range(len(PROFILE_PAGES)):
            tk.Button(
                dots, text="●" if index == page_index else "○",
                command=lambda selected=index: self._set_profile_page(selected),
                bg=WHITE, fg=RED if index == page_index else TEXT_MUTED,
                activebackground=WHITE, relief="flat", bd=0,
                font=self.font(12), cursor="hand2", padx=self.S(3),
            ).pack(side="left")
        selector = tk.Button(
            controls, text=f"{title}  v",
            command=lambda: self._show_profile_page_menu(selector),
            bg=WHITE, fg=INK, activebackground=HOVER, activeforeground=INK,
            relief="flat", bd=0, font=self.font(10), cursor="hand2",
            padx=self.S(10), pady=self.S(8),
        )
        selector.pack(side="left", padx=self.S(8))
        if page_index == len(PROFILE_PAGES) - 1:
            tk.Button(
                controls, text="Save changes", command=self.save_profile_details,
                bg=RED, fg=WHITE, activebackground=RED, activeforeground=WHITE,
                relief="flat", bd=0, font=self.font(11, "bold"), cursor="hand2",
                padx=self.S(14), pady=self.S(8),
            ).pack(side="right")
        else:
            tk.Button(
                controls, text="Next", command=lambda: self._set_profile_page(page_index + 1),
                bg=RED, fg=WHITE, activebackground=RED, activeforeground=WHITE,
                relief="flat", bd=0, font=self.font(11, "bold"), cursor="hand2",
                padx=self.S(14), pady=self.S(8),
            ).pack(side="right")
        self.c.create_window(
            x1, panel_y, window=panel, anchor="nw",
            width=max(1, int(x2 - x1)), height=max(1, int(panel_h)),
        )
        self._bind_profile_swipe(panel)

    def _show_profile_page_menu(self, button):
        x = button.winfo_rootx()
        y = button.winfo_rooty() + button.winfo_height()
        items = [
            (title, lambda selected=index: self._set_profile_page(selected), INK)
            for index, (title, _fields) in enumerate(PROFILE_PAGES)
        ]
        self._show_branded_menu(
            x, y, items, width=max(int(self.S(220)), button.winfo_width()),
            row_height=int(self.S(42)),
        )

    def _profile_variables(self, record):
        profile = record.get("profile", {})
        record_id = record["id"]
        draft_map = getattr(self, "profile_edit_vars", None)
        if draft_map is None:
            self.profile_edit_vars = {}
            draft_map = self.profile_edit_vars
        variables = draft_map.get(record_id)
        if variables is None:
            variables = {
                key: tk.StringVar(master=self, value=value)
                for key, value in profile_form_values(profile).items()
            }
            draft_map[record_id] = variables
        self._profile_record_id = record_id
        return variables

    def _set_profile_page(self, page_index):
        self.profile_page_index = min(max(page_index, 0), len(PROFILE_PAGES) - 1)
        self.render()

    def _bind_profile_swipe(self, widget):
        widget.bind("<ButtonPress-1>", self._profile_swipe_start, add="+")
        widget.bind("<ButtonRelease-1>", self._profile_swipe_end, add="+")
        for child in widget.winfo_children():
            self._bind_profile_swipe(child)

    def _profile_swipe_start(self, event):
        self._profile_swipe_origin = (event.x_root, event.y_root)

    def _profile_swipe_end(self, event):
        origin = getattr(self, "_profile_swipe_origin", None)
        self._profile_swipe_origin = None
        if not origin:
            return
        dx, dy = event.x_root - origin[0], event.y_root - origin[1]
        if abs(dx) < self.S(60) or abs(dx) < abs(dy) * 1.3:
            return
        page = self.profile_page_index + (1 if dx < 0 else -1)
        if 0 <= page < len(PROFILE_PAGES):
            self._set_profile_page(page)
            return "break"

    def _profile_field(self, parent, label, variable, kind):
        row = tk.Frame(parent, bg=WHITE)
        row.pack(fill="x", pady=(0, self.S(9)))
        tk.Label(row, text=label, bg=WHITE, fg=TEXT_MUTED,
                 font=self.font(12), anchor="w").pack(fill="x", pady=(0, self.S(5)))
        if kind == "sex":
            choices = ("", "Female", "Male", "Intersex", "Prefer not to say")
        elif kind == "relationship":
            choices = ("", "Self", "Partner", "Parent", "Child", "Other")
        elif kind == "province":
            choices = (
                "", "Alberta", "British Columbia", "Manitoba", "New Brunswick",
                "Newfoundland and Labrador", "Northwest Territories", "Nova Scotia",
                "Nunavut", "Ontario", "Prince Edward Island", "Quebec", "Saskatchewan",
                "Yukon",
            )
        else:
            choices = ()
        field_height = max(1, int(self.S(46)))
        field = tk.Canvas(
            row, bg=WHITE, height=field_height, bd=0, highlightthickness=0,
            cursor="hand2" if choices else "xterm",
        )
        field.pack(fill="x")

        def rounded(width, height):
            radius = self.S(9)
            return [
                radius, 1, width - radius, 1, width - 1, 1, width - 1, radius,
                width - 1, height - radius, width - 1, height - 1,
                width - radius, height - 1, radius, height - 1,
                1, height - 1, 1, height - radius, 1, radius, 1, 1,
            ]

        shape = field.create_polygon(
            *rounded(500, field_height), smooth=True, fill=WHITE,
            outline=BORDER_SOFT, width=1,
        )
        if choices:
            value = tk.Label(
                field, text=variable.get() or "Select...", bg=WHITE,
                fg=INK if variable.get() else TEXT_MUTED,
                font=self.font(13), anchor="w", cursor="hand2",
            )
            variable.trace_add(
                "write",
                lambda *_args, label_widget=value, source=variable: label_widget.configure(
                    text=source.get() or "Select...",
                    fg=INK if source.get() else TEXT_MUTED,
                ),
            )
            value_window = field.create_window(
                self.S(14), field_height / 2, window=value,
                anchor="w", width=max(1, int(self.S(200))), height=field_height - self.S(8),
            )
            arrow = field.create_text(
                0, field_height / 2, text="v", fill=TEXT_MUTED,
                font=self.font(11, "bold"), anchor="e",
            )

            def open_choices(_event=None):
                x = field.winfo_rootx()
                y = field.winfo_rooty() + field.winfo_height()
                menu_items = []
                for choice in choices:
                    label_text = choice or "Select..."
                    menu_items.append(
                        (label_text, lambda selected=choice: variable.set(selected), INK)
                    )
                self._show_branded_menu(
                    x, y, menu_items, width=field.winfo_width(),
                    row_height=int(self.S(40)),
                )
                return "break"

            value.bind("<Button-1>", open_choices, add="+")
            field.bind("<Button-1>", open_choices, add="+")

            def resize(event):
                field.coords(shape, *rounded(event.width, field_height))
                field.coords(arrow, event.width - self.S(14), field_height / 2)
                field.itemconfigure(value_window, width=max(1, event.width - self.S(48)))

            field.bind("<Configure>", resize, add="+")
        else:
            widget = tk.Entry(
                row, textvariable=variable, bg=WHITE, fg=INK, insertbackground=INK,
                relief="flat", bd=0, highlightthickness=0, font=self.font(13),
            )
            entry_window = field.create_window(
                self.S(14), field_height / 2, window=widget, anchor="w",
                width=max(1, int(self.S(200))), height=field_height - self.S(8),
            )

            def resize(event):
                field.coords(shape, *rounded(event.width, field_height))
                field.itemconfigure(entry_window, width=max(1, event.width - self.S(28)))

            field.bind("<Configure>", resize, add="+")

    def _draw_insurance_uploads(self, parent, variables):
        section = tk.Frame(
            parent, bg=WHITE, bd=0, highlightthickness=1,
            highlightbackground=BORDER, padx=self.S(18), pady=self.S(14),
        )
        section.pack(fill="x", pady=(0, self.S(14)))
        tk.Label(section, text="Insurance card photos", bg=WHITE, fg=INK,
                 font=self.font(15, "bold"), anchor="w").pack(fill="x", pady=(0, self.S(6)))
        tk.Label(section, text="Add the front and back of the card if available.",
                 bg=WHITE, fg=TEXT_MUTED, font=self.font(10), anchor="w").pack(fill="x", pady=(0, self.S(10)))
        for label, key in (("Front", "insurance_card_front"), ("Back", "insurance_card_back")):
            row = tk.Frame(section, bg=WHITE)
            row.pack(fill="x", pady=(0, self.S(7)))
            value = variables[key]
            name = tk.Label(row, textvariable=value, bg=WHITE, fg=TEXT_MUTED,
                            font=self.font(9), anchor="w")
            name.pack(side="left", fill="x", expand=True)
            tk.Button(
                row, text=f"Choose {label.lower()} photo",
                command=lambda field=key: self._choose_insurance_photo(field),
                bg=WHITE, fg=INK, activebackground="#eef1f6", relief="solid",
                bd=1, highlightthickness=0, font=self.font(10), cursor="hand2",
            ).pack(side="right")

    def _choose_insurance_photo(self, field):
        path = filedialog.askopenfilename(
            parent=self, title="Choose insurance card photo",
            filetypes=(("Images", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All files", "*.*")),
        )
        if path:
            self.profile_edit_vars[self._profile_record_id][field].set(path)

    def save_profile_details(self):
        record_id = self._profile_record_id
        variables = self.profile_edit_vars[record_id]
        values = {key: value.get().strip() for key, value in variables.items()}
        values["address"] = format_profile_address(values)

        def update(record):
            record["profile"].update(values)
            return record

        try:
            self.store.update(record_id, update)
        except (OSError, ValueError) as error:
            messagebox.showerror("Could not save profile", str(error), parent=self)
            return
        self.profile_edit_vars.pop(record_id, None)
        if record_id == self.patient_id:
            self.refresh_record()
        self.profile_status = "Profile changes saved."
        self.section = "Manage profiles"
        self.render()

    def _bind_profile_scroll(self, widget, canvas):
        widget.bind("<MouseWheel>", lambda event: canvas.yview_scroll(int(-event.delta / 120), "units"), add="+")
        for child in widget.winfo_children():
            self._bind_profile_scroll(child, canvas)
