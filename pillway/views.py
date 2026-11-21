"""Canvas views for the Pillway dashboard and secondary pages."""

import os
import tkinter as tk
from tkinter import font as tkfont

from .chat_history import format_chat_time, local_date_label, local_timestamp
from .constants import (
    BORDER,
    INK,
    NAVY,
    NAVY_DARK,
    ORANGE,
    ORDERS,
    RED,
    SETTINGS_ITEMS,
    SHADOW,
    SOFT_BLUE,
    TEXT_DARK,
    TEXT_MUTED,
    TEXT_OFF,
    TOGGLE_OFF,
    TABS,
    VIRTUAL_ASSISTANT_POPUP_TEXT,
    WHITE,
)
from .medical_guidance import CARE_PLAN_REFERENCE


class DashboardViewMixin:
    doctor_sections = (
        "User account information",
        "Patient information",
        "Medication review",
        "Checklist for completeness",
        "Diabetes assessment",
        "Pharmacist follow-up plan",
        "Resources provided",
        "Summary for today's discussion",
        "Referrals",
        "Take home summary",
        "Final review & billing",
        "Patient chat log",
    )

    def panel_box(self):
        return (self.sw + self.S(14), self.S(92), self.w - self.S(14), self.h - self.S(14))

    def draw_doctor_sidebar(self):
        c, sw, h = self.c, self.sw, self.h
        c.create_rectangle(0, 0, sw, h, fill=WHITE, outline=WHITE)
        c.create_line(sw - 1, self.S(70), sw - 1, h, fill=BORDER)
        self.text(self.S(24), self.S(91), "CARE PLAN", 10, TEXT_MUTED, "bold")
        nav_top = self.S(108)
        nav_bottom = h - self.S(166)
        row_h = min(self.S(40), max(self.S(24), (nav_bottom - nav_top) / len(self.doctor_sections)))
        for index, label in enumerate(self.doctor_sections):
            y = nav_top + index * row_h
            tag = f"doctor_section::{index}"
            selected = label == self.doctor_section
            bg = "#fff0ed" if selected else WHITE
            c.create_rectangle(0, y, sw - 2, y + row_h, fill=bg, outline=bg, tags=tag)
            if selected:
                c.create_rectangle(0, y, self.S(4), y + row_h, fill=RED, outline=RED, tags=tag)
            self.text(
                self.S(24), y + row_h / 2, label, 12,
                RED if selected else TEXT_MUTED, "bold" if selected else "normal", tag=tag,
            )
            self.clickable(tag, lambda section=label: self.select_doctor_section(section))

        notes_y = max(nav_bottom + self.S(8), h - self.S(150))
        notes_x1, notes_x2 = self.S(14), sw - self.S(14)
        self.rrect(notes_x1, notes_y, notes_x2, h - self.S(54), self.S(10),
                   fill="#f7f9fa", outline=BORDER, width=self.S(1))
        self.text(notes_x1 + self.S(12), notes_y + self.S(20), "Internal notes",
                  12, INK, "bold")
        self.c.create_text(
            notes_x1 + self.S(12), notes_y + self.S(40),
            text="No private notes saved.\nLocal demo workspace only.",
            fill=TEXT_MUTED,
            font=self.font(10),
            anchor="nw",
            width=max(1, notes_x2 - notes_x1 - self.S(24)),
        )
        manage_tag = "doctor_manage_profiles"
        manage_y = h - self.S(44)
        c.create_rectangle(0, manage_y, sw, h, fill=WHITE, outline=WHITE, tags=manage_tag)
        self.text(self.S(24), manage_y + self.S(10), "Manage profiles", 12,
                  TEXT_MUTED, "bold", tag=manage_tag)
        self.clickable(manage_tag, lambda: self.go("Manage profiles"))

    def draw_doctor_header(self):
        c, w = self.c, self.w
        header_h = self.S(68)
        c.create_rectangle(0, 0, w, header_h, fill=WHITE, outline=WHITE)
        c.create_line(0, header_h, w, header_h, fill=BORDER)
        self.text(self.S(24), header_h / 2, "pillway", 19, RED, "bold")
        self.text(self.S(105), header_h / 2, "|", 18, TEXT_MUTED)
        self.text(self.S(121), header_h / 2, "Care Plan", 17, RED, "bold")
        if self.doctor_status:
            self.text(w - self.S(402), header_h / 2, self.doctor_status,
                      10, TEXT_MUTED, anchor="e")
        patients_tag = "doctor_all_patients"
        self.rrect(w - self.S(390), self.S(9), w - self.S(290),
                   header_h - self.S(9), self.S(8), fill=WHITE,
                   outline=BORDER, width=self.S(1), tags=patients_tag)
        self.text(w - self.S(340), header_h / 2, "All patients", 11,
                  INK, "bold", anchor="center", tag=patients_tag)
        self.clickable(patients_tag, self.return_to_doctor_patient_list)
        save_tag = "doctor_save"
        self.rrect(w - self.S(240), self.S(9), w - self.S(150), header_h - self.S(9),
                   self.S(8), fill=RED, outline="", tags=save_tag)
        self.text(w - self.S(195), header_h / 2, "Save", 13, WHITE,
                  "bold", anchor="center", tag=save_tag)
        self.clickable(save_tag, self.save_doctor_workspace)
        profile_tag = "doctor_profile_menu"
        patient = self.profiles[self.selected_patient_id]
        patient_name = patient["name"]
        if len(patient_name) > 12:
            patient_name = patient_name[:11] + "…"
        self.text(w - self.S(52), header_h / 2, patient_name, 10,
                  TEXT_MUTED, anchor="e", tag=profile_tag)
        self.text(w - self.S(20), header_h / 2, "...", 16, TEXT_MUTED,
                  "bold", anchor="center", tag=profile_tag)
        self.clickable(profile_tag, lambda: self.toggle_dropdown("profile"))

    def draw_doctor_patient_picker(self):
        x1, y1, x2, y2 = self.panel_box()
        self.rrect(x1, y1, x2, y2, self.S(16), fill=WHITE, outline=BORDER,
                   width=self.S(1.2))
        title_y = y1 + self.S(42)
        self.text(x1 + self.S(30), title_y, "Your patients", 24, INK, "bold")
        self.text(x1 + self.S(30), title_y + self.S(31),
                  "Select a patient to open their care plan.", 13, TEXT_MUTED)
        add_tag = "doctor_add_patient"
        button_w, button_h = self.S(190), self.S(44)
        bx1, by1 = x2 - self.S(30) - button_w, y1 + self.S(22)
        self.rrect(bx1, by1, bx1 + button_w, by1 + button_h, self.S(10),
                   fill=ORANGE, outline="", tags=add_tag)
        self.text(bx1 + button_w / 2, by1 + button_h / 2, "Add patient profile",
                  12, WHITE, "bold", anchor="center", tag=add_tag)
        self.clickable(add_tag, self.add_patient_profile)
        if self.profile_status:
            self.text(x1 + self.S(30), title_y + self.S(57),
                      self.profile_status, 11, TEXT_MUTED)

        patients = [
            (profile_id, profile)
            for profile_id, profile in self.profiles.items()
            if profile["role"] == "Patient"
        ]
        grid_x = x1 + self.S(24)
        grid_y = y1 + self.S(112)
        grid_w = x2 - x1 - self.S(48)
        grid_h = max(self.S(100), y2 - grid_y - self.S(16))
        max_card = self.S(250)
        gap = self.S(20)
        columns = max(1, min(4, int((grid_w + gap) / (max_card + gap))))
        card_size = min(max_card, (grid_w - gap * (columns - 1)) / columns)
        rows = (len(patients) + columns - 1) // columns
        content_h = max(grid_h, rows * (card_size + gap) + gap)
        content_w = grid_w

        self.doctor_patients_frame = tk.Frame(
            self, bg=WHITE, bd=0, highlightthickness=0,
        )
        patient_canvas = tk.Canvas(
            self.doctor_patients_frame, bg=WHITE, bd=0, highlightthickness=0,
            yscrollincrement=max(1, int(self.S(24))),
        )
        patient_scrollbar = tk.Scrollbar(
            self.doctor_patients_frame, orient="vertical", command=patient_canvas.yview,
        )
        patient_canvas.configure(yscrollcommand=patient_scrollbar.set)
        patient_canvas.pack(side="left", fill="both", expand=True)
        if content_h > grid_h:
            patient_scrollbar.pack(side="right", fill="y")
        patient_canvas.configure(
            scrollregion=(0, 0, int(content_w), int(content_h)),
            width=max(1, int(content_w)),
            height=max(1, int(grid_h)),
        )
        patient_canvas.bind(
            "<MouseWheel>",
            lambda event: self._scroll_doctor_patient_grid(patient_canvas, event),
        )
        patient_canvas.bind(
            "<Button-4>", lambda _event: patient_canvas.yview_scroll(-1, "units"),
        )
        patient_canvas.bind(
            "<Button-5>", lambda _event: patient_canvas.yview_scroll(1, "units"),
        )

        avatar_fills = ("#eef2ff", "#fff0e5", "#e8f5ef", "#fcebea")
        avatar_inks = ("#4c5ba8", "#bd6b24", "#37825c", "#b54b4b")
        for index, (profile_id, profile) in enumerate(patients):
            column, row = index % columns, index // columns
            row_items = min(columns, len(patients) - row * columns)
            row_width = row_items * card_size + (row_items - 1) * gap
            row_start = max(0, (content_w - row_width) / 2)
            card_x = row_start + column * (card_size + gap)
            card_y = gap + row * (card_size + gap)
            tag = f"doctor_patient::{index}"
            patient_canvas.create_rectangle(
                card_x + self.S(3), card_y + self.S(4),
                card_x + card_size + self.S(3), card_y + card_size + self.S(4),
                fill=SHADOW, outline="", tags=tag,
            )
            patient_canvas.create_rectangle(
                card_x, card_y, card_x + card_size, card_y + card_size,
                fill=WHITE, outline=BORDER, width=max(1, int(self.S(1.2))), tags=tag,
            )
            center_x = card_x + card_size / 2
            avatar_y = card_y + self.S(48)
            avatar_radius = self.S(30)
            palette_index = index % len(avatar_fills)
            patient_canvas.create_oval(
                center_x - avatar_radius, avatar_y - avatar_radius,
                center_x + avatar_radius, avatar_y + avatar_radius,
                fill=avatar_fills[palette_index], outline="", tags=tag,
            )
            initials = "".join(
                part[0] for part in profile["name"].split()[:2]
            ).upper() or "P"
            patient_canvas.create_text(
                center_x, avatar_y, text=initials, fill=avatar_inks[palette_index],
                font=self.font(18, "bold"), anchor="center", tags=tag,
            )
            patient_canvas.create_text(
                center_x, card_y + self.S(91), text=profile["name"],
                fill=INK, font=self.font(14, "bold"), anchor="center",
                width=card_size - self.S(22), tags=tag,
            )
            patient_canvas.create_text(
                center_x, card_y + self.S(117), text="PATIENT",
                fill=TEXT_MUTED, font=self.font(9, "bold"), anchor="center", tags=tag,
            )
            patient_canvas.create_text(
                center_x, card_y + self.S(148), text="Diabetes · Hypertension",
                fill=TEXT_DARK, font=self.font(11), anchor="center",
                width=card_size - self.S(20), tags=tag,
            )
            messages = self.chat_logs.get(profile_id, [])
            message_count = len(messages)
            patient_canvas.create_text(
                center_x, card_y + self.S(172),
                text=f"{message_count} chat messages",
                fill=TEXT_MUTED, font=self.font(10), anchor="center", tags=tag,
            )
            latest_patient_message = next(
                (str(message[1]) for message in reversed(messages)
                 if len(message) >= 2 and message[0] == "You"),
                "",
            )
            if latest_patient_message:
                preview = latest_patient_message
                if len(preview) > 48:
                    preview = preview[:45].rstrip() + "..."
                preview = f"Latest: {preview}"
            else:
                preview = "No patient messages yet"
            patient_canvas.create_text(
                center_x, card_y + card_size - self.S(26), text=preview,
                fill=TEXT_MUTED, font=self.font(9), anchor="center",
                width=card_size - self.S(22), tags=tag,
            )
            patient_canvas.tag_bind(
                tag, "<Button-1>",
                lambda _event, selected=profile_id: self.select_doctor_patient(selected),
            )
            patient_canvas.tag_bind(
                tag, "<Enter>", lambda _event: patient_canvas.configure(cursor="hand2"),
            )
            patient_canvas.tag_bind(
                tag, "<Leave>", lambda _event: patient_canvas.configure(cursor=""),
            )

        self.c.create_window(
            grid_x, grid_y, window=self.doctor_patients_frame, anchor="nw",
            width=max(1, int(grid_w)), height=max(1, int(grid_h)),
        )

    @staticmethod
    def _scroll_doctor_patient_grid(canvas, event):
        units = int(-event.delta / 120) or (-1 if event.delta > 0 else 1)
        canvas.yview_scroll(units, "units")
        return "break"

    def draw_doctor_dashboard(self):
        x1, y1, x2, y2 = self.panel_box()
        self.c.create_rectangle(x1, y1, x2, y2, fill="#edf1f4", outline="")
        patients = [
            (profile_id, profile)
            for profile_id, profile in self.profiles.items()
            if profile["role"] == "Patient"
        ]
        tabs_x, tabs_y = x1 + self.S(20), y1 + self.S(10)
        tabs_w, tabs_h = x2 - x1 - self.S(40), self.S(36)
        self.doctor_tabs_frame = tk.Frame(self, bg=WHITE, bd=0, highlightthickness=0)
        tabs_canvas = tk.Canvas(
            self.doctor_tabs_frame, bg=WHITE, bd=0, highlightthickness=0,
            height=max(1, int(tabs_h - self.S(2))),
        )
        tabs_scrollbar = tk.Scrollbar(
            self.doctor_tabs_frame, orient="horizontal", command=tabs_canvas.xview,
        )
        tabs_canvas.configure(xscrollcommand=tabs_scrollbar.set)
        tabs_canvas.pack(side="top", fill="x", expand=True)
        tab_content = tk.Frame(tabs_canvas, bg=WHITE, bd=0)
        tabs_canvas.create_window((0, 0), window=tab_content, anchor="nw")
        for profile_id, profile in patients:
            active = profile_id == self.selected_patient_id
            tab = tk.Button(
                tab_content,
                text=profile["name"],
                command=lambda selected=profile_id: self.select_doctor_patient(selected),
                relief="solid",
                bd=1,
                bg=SOFT_BLUE if active else WHITE,
                fg=INK,
                activebackground=SOFT_BLUE,
                font=self.font(12, "bold" if active else "normal"),
                padx=max(10, int(self.S(14))),
                pady=max(3, int(self.S(5))),
            )
            tab.pack(side="left", padx=(0, max(4, int(self.S(8)))))
        tab_content.bind(
            "<Configure>",
            lambda _event: tabs_canvas.configure(scrollregion=tabs_canvas.bbox("all")),
        )
        tabs_canvas.bind(
            "<Configure>",
            lambda _event: self._toggle_horizontal_scrollbar(tabs_canvas, tabs_scrollbar),
        )
        self.c.create_window(
            tabs_x, tabs_y, window=self.doctor_tabs_frame, anchor="nw",
            width=max(1, int(tabs_w)), height=max(1, int(tabs_h)),
        )
        self.after_idle(lambda: self._toggle_horizontal_scrollbar(tabs_canvas, tabs_scrollbar))

        patient = self.profiles[self.selected_patient_id]
        content_x = x1 + self.S(24)
        content_w = x2 - content_x - self.S(24)
        heading_y = tabs_y + tabs_h + self.S(18)
        self.text(content_x, heading_y, self.doctor_section, 23, INK, "bold")
        subtitles = {
            "User account information": "Account details and consultation journey",
            "Patient information": "Demographics and clinical baseline",
            "Medication review": "Current therapy, adherence, and medication-related issues",
            "Checklist for completeness": "Review the consultation sections and their status",
            "Diabetes assessment": "Diabetes-specific clinical review",
            "Pharmacist follow-up plan": "Schedule and manage follow-up calls",
            "Resources provided": "Select and share relevant patient supports",
            "Summary for today's discussion": "Create a clear consultation record",
            "Referrals": "Coordinate specialty care and track outcomes",
            "Take home summary": "Review a patient-facing summary",
            "Final review & billing": "Confirm completion and billing details",
            "Patient chat log": "Read-only history from this patient's Juliez conversation",
        }
        self.text(content_x, heading_y + self.S(27), subtitles[self.doctor_section],
                  12, TEXT_MUTED)
        page_y = heading_y + self.S(54)
        page_bottom = y2 - self.S(18)

        if self.doctor_section == "User account information":
            self._draw_doctor_account_page(content_x, page_y, content_w, page_bottom, patient)
        elif self.doctor_section == "Patient information":
            self._draw_doctor_patient_page(content_x, page_y, content_w)
        elif self.doctor_section == "Medication review":
            self._draw_doctor_medication_page(content_x, page_y, content_w)
        elif self.doctor_section == "Checklist for completeness":
            self._draw_doctor_checklist_page(content_x, page_y, content_w)
        elif self.doctor_section == "Diabetes assessment":
            self._draw_doctor_diabetes_page(content_x, page_y, content_w)
        elif self.doctor_section == "Pharmacist follow-up plan":
            self._draw_doctor_empty_page(content_x, page_y, content_w, "No follow-up calls are saved.")
        elif self.doctor_section == "Resources provided":
            self._draw_doctor_resources_page(content_x, page_y, content_w)
        elif self.doctor_section == "Summary for today's discussion":
            self._draw_doctor_summary_page(content_x, page_y, content_w, patient)
        elif self.doctor_section == "Referrals":
            self._draw_doctor_empty_page(content_x, page_y, content_w, "No referrals are saved.")
        elif self.doctor_section == "Take home summary":
            self._draw_doctor_take_home_page(content_x, page_y, content_w)
        elif self.doctor_section == "Final review & billing":
            self._draw_doctor_empty_page(content_x, page_y, content_w, "No billing details are saved.")
        else:
            self._draw_doctor_chat_log(content_x, page_y, content_w, page_bottom)

    def _doctor_card(self, x, y, width, height, title):
        self.rrect(x, y, x + width, y + height, self.S(12), fill=WHITE,
                   outline=BORDER, width=self.S(1))
        self.text(x + self.S(18), y + self.S(24), title, 15, INK, "bold")

    def _doctor_field(self, x, y, width, label, value):
        self.text(x, y, label, 9, TEXT_MUTED)
        self.rrect(x, y + self.S(8), x + width, y + self.S(42), self.S(5),
                   fill=WHITE, outline=BORDER, width=self.S(1))
        self.text(x + self.S(9), y + self.S(25), value, 11, TEXT_DARK)

    def _draw_doctor_account_page(self, x, y, width, bottom, patient):
        details_h = min(self.S(286), max(self.S(210), (bottom - y) * 0.57))
        self._doctor_card(x, y, width, details_h, "User account information")
        labels = (
            ("Name", patient["name"]),
            ("Date of birth", "Not provided"),
            ("Sex", "Not provided"),
            ("Health card", "Not provided"),
            ("Phone", "Not provided"),
            ("Email", "Not provided"),
            ("Address", "Not provided"),
            ("Preferred language", "Not provided"),
            ("Pharmacy / prescriber", "Not provided"),
        )
        gap = self.S(22)
        col_w = (width - self.S(36) - gap * 2) / 3
        field_y = y + self.S(55)
        row_gap = self.S(57)
        for index, (label, value) in enumerate(labels):
            row, col = divmod(index, 3)
            self._doctor_field(
                x + self.S(18) + col * (col_w + gap),
                field_y + row * row_gap,
                col_w,
                label,
                value,
            )

        journey_y = y + details_h + self.S(16)
        journey_h = max(self.S(132), bottom - journey_y)
        self._doctor_card(x, journey_y, width, journey_h, "Consultation journey")
        labels = (
            "Request\nsubmitted", "Pre-assessment\ncompleted", "Consultation\ncall",
            "Care plan\nprovided", "Follow-up\nbooked",
        )
        start = x + self.S(42)
        span = width - self.S(84)
        line_y = journey_y + self.S(70)
        self.c.create_line(start, line_y, start + span, line_y, fill=BORDER, width=self.S(3))
        for index, label in enumerate(labels):
            cx = start + span * index / (len(labels) - 1)
            self.c.create_oval(cx - self.S(7), line_y - self.S(7), cx + self.S(7), line_y + self.S(7),
                               fill=WHITE, outline="#aeb8c2", width=self.S(2))
            self.c.create_text(cx, line_y + self.S(25), text=label, fill=TEXT_MUTED,
                               font=self.font(9), anchor="n")
        self.text(x + self.S(18), journey_y + journey_h - self.S(16),
                  "Status not recorded in this local demo.", 9, TEXT_MUTED)

    def _draw_doctor_patient_page(self, x, y, width):
        gap = self.S(16)
        card_w = (width - gap) / 2
        card_h = self.S(260)
        self._doctor_card(x, y, card_w, card_h, "Demographics")
        self._doctor_card(x + card_w + gap, y, card_w, card_h, "Lab results")
        left_values = (
            ("Age", "Not provided"), ("Sex", "Not provided"),
            ("Height / weight", "Not provided"), ("Medical conditions", "Diabetes; hypertension"),
        )
        right_values = (
            ("A1C", "Not provided"), ("Blood pressure", "Not provided"),
            ("LDL cholesterol", "Not provided"), ("Targets", "See care-plan reference"),
        )
        for index, (label, value) in enumerate(left_values):
            self._doctor_field(x + self.S(18), y + self.S(54 + index * 48),
                               card_w - self.S(36), label, value)
        for index, (label, value) in enumerate(right_values):
            self._doctor_field(x + card_w + gap + self.S(18), y + self.S(54 + index * 48),
                               card_w - self.S(36), label, value)
        bottom_y = y + card_h + gap
        self._doctor_card(x, bottom_y, width, self.S(150), "Clinical context")
        self.c.create_text(
            x + self.S(18), bottom_y + self.S(48),
            text="The short-assessment baseline for this demo is diabetes and hypertension. "
                 "Actual measurements and personal targets have not been entered.",
            fill=TEXT_DARK, anchor="nw", width=width - self.S(36), font=self.font(12),
        )

    def _draw_doctor_medication_page(self, x, y, width):
        height = self.S(300)
        self._doctor_card(x, y, width, height, "Medication review")
        columns = ("Medication", "Dose", "Frequency", "Indication", "Prescriber", "Adherence", "Flags")
        col_w = (width - self.S(36)) / len(columns)
        for index, title in enumerate(columns):
            self.text(x + self.S(18) + index * col_w, y + self.S(62), title, 9, TEXT_MUTED, "bold")
        self.c.create_line(x + self.S(14), y + self.S(82), x + width - self.S(14),
                           y + self.S(82), fill=BORDER)
        self.c.create_text(x + self.S(22), y + self.S(112),
                           text="No medication records saved for this demo patient.",
                           fill=TEXT_MUTED, anchor="w", font=self.font(11))
        notes_y = y + height + self.S(16)
        self._doctor_card(x, notes_y, width, self.S(120), "Pharmacist comments")
        self.c.create_text(x + self.S(18), notes_y + self.S(52),
                           text="No pharmacist comments saved.", fill=TEXT_MUTED,
                           anchor="nw", font=self.font(11))

    def _draw_doctor_checklist_page(self, x, y, width):
        items = (
            "Patient information reviewed", "Medication review completed",
            "Diabetes assessment completed", "Goals discussed", "Care plan published",
            "Follow-up booked", "Resources shared", "Referrals documented",
        )
        self._doctor_card(x, y, width, self.S(92), "Consultation progress")
        self.text(x + width - self.S(22), y + self.S(25), "Status not recorded",
                  10, TEXT_MUTED, anchor="e")
        self.rrect(x + self.S(20), y + self.S(52), x + width - self.S(20), y + self.S(62),
                   self.S(5), fill="#e1e6e9", outline="")
        card_gap = self.S(14)
        card_w = (width - card_gap) / 2
        row_h = self.S(58)
        start_y = y + self.S(110)
        for index, label in enumerate(items):
            row, col = divmod(index, 2)
            bx = x + col * (card_w + card_gap)
            by = start_y + row * (row_h + self.S(10))
            self._doctor_card(bx, by, card_w, row_h, "")
            self.c.create_oval(bx + self.S(14), by + self.S(20), bx + self.S(32), by + self.S(38),
                               fill=WHITE, outline=BORDER, width=self.S(1))
            self.text(bx + self.S(44), by + row_h / 2, label, 10, TEXT_DARK)
            self.text(bx + card_w - self.S(12), by + row_h / 2, "Not recorded",
                      9, TEXT_MUTED, anchor="e")

    def _draw_doctor_diabetes_page(self, x, y, width):
        gap = self.S(16)
        card_w = (width - gap) / 2
        card_h = self.S(185)
        self._doctor_card(x, y, card_w, card_h, "Diabetes profile")
        self._doctor_card(x + card_w + gap, y, card_w, card_h, "Monitoring & A1C")
        self._doctor_field(x + self.S(18), y + self.S(58), card_w - self.S(36),
                           "Diabetes type", "Not specified")
        self._doctor_field(x + self.S(18), y + self.S(112), card_w - self.S(36),
                           "Diagnosis date", "Not provided")
        self._doctor_field(x + card_w + gap + self.S(18), y + self.S(58),
                           card_w - self.S(36), "Monitoring method", "Not provided")
        self._doctor_field(x + card_w + gap + self.S(18), y + self.S(112),
                           card_w - self.S(36), "Recent A1C", "Not provided")
        focus_y = y + card_h + gap
        self.rrect(x, focus_y, x + width, focus_y + self.S(100), self.S(10),
                   fill="#fff1ed", outline="#f4cfc5", width=self.S(1))
        self.text(x + self.S(18), focus_y + self.S(24), "Clinical focus", 13, RED, "bold")
        self.c.create_text(
            x + self.S(18), focus_y + self.S(45),
            text="Follow the patient's clinician-approved plan. No A1C or glucose values "
                 "are stored in this local demo.",
            fill=TEXT_DARK, anchor="nw", width=width - self.S(36), font=self.font(10),
        )

    def _draw_doctor_empty_page(self, x, y, width, message):
        self._doctor_card(x, y, width, self.S(185), self.doctor_section)
        cx = x + width / 2
        self.text(cx, y + self.S(98), message, 12, TEXT_MUTED, anchor="center")

    def _draw_doctor_resources_page(self, x, y, width):
        resources = (
            ("Diabetes education", "General learning resources"),
            ("Nutrition support", "Discuss with the care team"),
            ("Glucose monitoring", "Follow the prescribed monitoring plan"),
            ("Foot care", "Ask about screening and preventive care"),
        )
        gap = self.S(14)
        card_w = (width - gap) / 2
        card_h = self.S(96)
        for index, (title, description) in enumerate(resources):
            row, col = divmod(index, 2)
            bx = x + col * (card_w + gap)
            by = y + row * (card_h + gap)
            self._doctor_card(bx, by, card_w, card_h, title)
            self.c.create_text(bx + self.S(18), by + self.S(52), text=description,
                               fill=TEXT_MUTED, anchor="nw", width=card_w - self.S(36),
                               font=self.font(10))

    def _draw_doctor_summary_page(self, x, y, width, patient):
        messages = self.chat_logs.get(self.selected_patient_id, [])
        latest = next(
            (message for sender, message, _timestamp in reversed(messages) if sender == "You"),
            "",
        )
        self._doctor_card(x, y, width, self.S(118), "Reason for visit")
        self.c.create_text(
            x + self.S(18), y + self.S(50),
            text="Review diabetes and hypertension check-in.",
            fill=TEXT_DARK, anchor="nw", width=width - self.S(36), font=self.font(11),
        )
        section_y = y + self.S(132)
        gap = self.S(14)
        card_w = (width - gap) / 2
        self._doctor_card(x, section_y, card_w, self.S(150), "Key findings")
        self._doctor_card(x + card_w + gap, section_y, card_w, self.S(150), "Patient concerns")
        self.c.create_text(
            x + self.S(18), section_y + self.S(50),
            text="No clinical measurements are saved.",
            fill=TEXT_MUTED, anchor="nw", width=card_w - self.S(36), font=self.font(10),
        )
        concern = latest or f"No patient chat entries are saved for {patient['name']}."
        self.c.create_text(
            x + card_w + gap + self.S(18), section_y + self.S(50),
            text=concern, fill=TEXT_DARK, anchor="nw",
            width=card_w - self.S(36), font=self.font(10),
        )

    def _draw_doctor_take_home_page(self, x, y, width):
        card_height = self.S(390)
        self.rrect(x, y, x + width, y + card_height, self.S(12),
                   fill=WHITE, outline=BORDER, width=self.S(1))
        self.text(x + self.S(24), y + self.S(26), "pillway", 18, RED, "bold")
        self.text(x + self.S(24), y + self.S(62), "Care-plan reference",
                  20, INK, "bold")
        self.text(x + self.S(24), y + self.S(84),
                  "Shared reference only; confirm individual targets with the care team.",
                  10, TEXT_MUTED)
        row_top = y + self.S(112)
        for index, (label, description) in enumerate(CARE_PLAN_REFERENCE):
            line_y = row_top + index * self.S(49)
            self.text(x + self.S(24), line_y, label, 11, RED, "bold")
            self.c.create_text(
                x + self.S(220), line_y,
                text=description,
                fill=TEXT_DARK,
                anchor="nw",
                width=width - self.S(244),
                font=self.font(10),
            )
            if index < len(CARE_PLAN_REFERENCE) - 1:
                self.c.create_line(x + self.S(20), line_y + self.S(34),
                                   x + width - self.S(20), line_y + self.S(34), fill=BORDER)

    def _draw_doctor_chat_log(self, x, y, width, bottom):
        log_y = y + self.S(6)
        self.doctor_log_frame = tk.Frame(self, bg=WHITE, bd=0, highlightthickness=0)
        log = tk.Text(
            self.doctor_log_frame, wrap="word", bg=WHITE, fg=TEXT_DARK,
            bd=0, highlightthickness=0, font=self.font(12),
            padx=max(4, int(self.S(8))), pady=max(4, int(self.S(8))),
        )
        log_scrollbar = tk.Scrollbar(self.doctor_log_frame, command=log.yview)
        log.configure(yscrollcommand=log_scrollbar.set)
        log.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")
        messages = self.chat_logs.get(self.selected_patient_id, [])
        if messages:
            for sender, message, timestamp in messages:
                log.insert("end", f"{sender} · {format_chat_time(timestamp)}\n", "sender")
                log.insert("end", f"{message}\n\n")
        else:
            log.insert("end", "No chat history yet for this patient.")
        log.tag_configure("sender", foreground=INK, font=self.font(11, "bold"))
        log.configure(state="disabled")
        self.c.create_window(
            x, log_y, window=self.doctor_log_frame, anchor="nw",
            width=max(1, int(width)), height=max(1, int(bottom - log_y)),
        )

    @staticmethod
    def _toggle_horizontal_scrollbar(canvas, scrollbar):
        if not canvas.winfo_exists() or not scrollbar.winfo_exists():
            return
        bounds = canvas.bbox("all")
        if bounds and bounds[2] > canvas.winfo_width():
            if not scrollbar.winfo_manager():
                scrollbar.pack(side="bottom", fill="x")
        elif scrollbar.winfo_manager():
            scrollbar.pack_forget()

    def draw_dashboard(self):
        px1, py1, px2, py2 = self.panel_box()
        self.rrect(px1, py1, px2, py2, self.S(16), fill=WHITE, outline=BORDER, width=self.S(1.2))
        if self.call_open:
            self.draw_call_preview(px1, py1, px2, py2)
            return
        if self.chat_open:
            self.draw_chat_page(px1, py1, px2, py2)
            return
        if self.prescription_flow:
            self.draw_prescription_page(px1, py1, px2, py2)
            return
        pcx = (px1 + px2) / 2

        gap = self.S(150)
        for i, (name, icon) in enumerate(TABS):
            x = pcx + (i - (len(TABS) - 1) / 2) * gap
            tag = f"tab::{name}"
            sel = name == self.tab
            col = RED if sel else TEXT_MUTED
            self.c.create_rectangle(x - gap / 2 + self.S(6), py1 + self.S(8), x + gap / 2 - self.S(6),
                                    py1 + self.S(96), fill=WHITE, outline=WHITE, tags=tag)
            self.draw_icon(icon, x, py1 + self.S(40), self.S(32), col, tag)
            self.text(x, py1 + self.S(76), name, 14, col, "bold" if sel else "normal",
                      anchor="center", tag=tag)
            if sel:
                self.rrect(x - self.S(26), py1 + self.S(92), x + self.S(26), py1 + self.S(96),
                           self.S(2), fill=RED, outline="", tags=tag)
            self.clickable(tag, lambda n=name: self.select_tab(n))
        self.c.create_line(px1, py1 + self.S(98), px2, py1 + self.S(98), fill=BORDER)

        y = py1 + self.S(118)
        if self.banner and self.tab != "Medications":
            bw = min(self.S(700), px2 - px1 - self.S(60))
            bx1, bx2 = pcx - bw / 2, pcx + bw / 2
            self.rrect(bx1, y, bx2, y + self.S(56), self.S(14), fill=NAVY_DARK, outline="")
            self.text(bx1 + self.S(22), y + self.S(28), VIRTUAL_ASSISTANT_POPUP_TEXT, 14, WHITE)
            self.c.create_oval(bx2 - self.S(36), y + self.S(14), bx2 - self.S(8), y + self.S(42),
                               fill=NAVY_DARK, outline="", tags="banner_x")
            self.draw_icon("close", bx2 - self.S(22), y + self.S(28), self.S(16), WHITE, "banner_x")
            self.clickable("banner_x", self.close_banner)
            y += self.S(80)
        else:
            y += self.S(10)

        content_w = min(self.S(820), px2 - px1 - self.S(80))
        x1, x2 = pcx - content_w / 2, pcx + content_w / 2
        {"Check up": self.draw_checkup, "Medications": self.draw_medications,
         "Orders": self.draw_orders, "Tasks": self.draw_tasks}[self.tab](x1, x2, y)

    def draw_call_preview(self, x1, y1, x2, y2):
        phone_w = min(self.S(360), x2 - x1 - self.S(36))
        phone_h = min(self.S(640), y2 - y1 - self.S(36))
        phone_h = max(self.S(300), phone_h)
        px = (x1 + x2 - phone_w) / 2
        py = (y1 + y2 - phone_h) / 2
        self.rrect(px, py, px + phone_w, py + phone_h, self.S(30),
                   fill="#111832", outline="#303955", width=self.S(2))
        inset = self.S(10)
        sx1, sy1 = px + inset, py + inset
        sx2, sy2 = px + phone_w - inset, py + phone_h - inset
        self.rrect(sx1, sy1, sx2, sy2, self.S(24), fill="#171f3b", outline="")
        cx = (sx1 + sx2) / 2
        self.rrect(cx - self.S(42), sy1 + self.S(9), cx + self.S(42), sy1 + self.S(15),
                   self.S(3), fill="#303955", outline="")
        self.text(cx, sy1 + self.S(38), "CALL PREVIEW", 10, "#c8cede", "bold",
                  anchor="center")

        avatar_y = sy1 + self.S(112)
        avatar_r = self.S(46)
        self.c.create_oval(cx - avatar_r, avatar_y - avatar_r,
                           cx + avatar_r, avatar_y + avatar_r,
                           fill=RED, outline="")
        self.text(cx, avatar_y, "P", 32, WHITE, "bold", anchor="center")
        self.text(cx, avatar_y + self.S(68), "Pillway care team", 19, WHITE, "bold",
                  anchor="center")
        self.text(cx, avatar_y + self.S(96), "Local speech preview · no call placed",
                  10, "#c8cede", anchor="center")

        status_y = avatar_y + self.S(145)
        self.text(cx, status_y, self.call_status, 9,
                  RED if self.call_mic_state == "error" else "#c8cede",
                  anchor="center", tag="call_status")
        self.text(
            cx, status_y + self.S(54),
            self.call_transcript[-180:] or "Your on-device transcript will appear here.",
            9, "#f3f5fa", anchor="n", tag="call_transcript",
        )
        self.c.itemconfigure("call_status", width=phone_w - self.S(44))
        self.c.itemconfigure("call_transcript", width=phone_w - self.S(44))

        controls_y = sy2 - self.S(106)
        mic_x = cx - self.S(58)
        mic_tag = "call_mic_control"
        self.c.create_oval(
            mic_x - self.S(25), controls_y - self.S(25),
            mic_x + self.S(25), controls_y + self.S(25),
            fill=RED if self.call_mic_state == "listening" else "#303955",
            outline="", tags=(mic_tag, "call_mic_button"),
        )
        self.draw_icon("mic", mic_x, controls_y, self.S(22), "#c8cede",
                       mic_tag, bg="#303955")
        self.c.create_line(mic_x - self.S(14), controls_y + self.S(14),
                           mic_x + self.S(14), controls_y - self.S(14),
                           fill=RED, width=self.S(2),
                           tags=(mic_tag, "call_mic_slash"))
        self.text(mic_x, controls_y + self.S(39),
                  "Stop mic" if self.call_mic_state in (
                      "preparing", "downloading", "listening", "stopping",
                  ) else "Start mic",
                  9, "#c8cede", anchor="center", tag="call_mic_label")
        self.clickable(mic_tag, self.toggle_call_microphone)

        end_x = cx + self.S(58)
        end_tag = "end_call_preview"
        self.c.create_oval(end_x - self.S(25), controls_y - self.S(25),
                           end_x + self.S(25), controls_y + self.S(25),
                           fill=RED, outline="", tags=end_tag)
        self.draw_icon("phone", end_x, controls_y, self.S(23), WHITE, end_tag, bg=RED)
        self.clickable(end_tag, self.close_call_preview)
        self.text(end_x, controls_y + self.S(39), "End preview", 9, "#c8cede",
                  anchor="center", tag=end_tag)

        self.text(cx, sy2 - self.S(16), "On-device only · audio is not saved or uploaded.",
                  9, "#c8cede", anchor="center")
        self._update_call_preview()

    def draw_checkup(self, x1, x2, y):
        self.text((x1 + x2) / 2, y + self.S(14), "How would you like to check in?", 20, INK,
                  "bold", anchor="center")
        y += self.S(48)
        bars = [("Call", "phone", "Open a phone preview (not connected)"),
                ("Chat", "chat", "Message your care assistant, any time")]
        bh = self.S(104)
        for i, (title, icon, sub) in enumerate(bars):
            off = (1 - self.anim) * self.S(70) * (i + 1)
            by = y + i * (bh + self.S(22)) + off
            tag = f"bar::{title}"
            self.rrect(x1, by + self.S(4), x2, by + bh + self.S(4), self.S(20),
                       fill=SHADOW, outline="", tags=tag)
            self.rrect(x1, by, x2, by + bh, self.S(20), fill=WHITE,
                       outline=BORDER, width=self.S(1.2), tags=tag)
            cx, cy, r = x1 + self.S(56), by + bh / 2, self.S(30)
            self.c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=RED, outline="", tags=tag)
            self.draw_icon(icon, cx, cy, self.S(28), WHITE, tag, bg=RED)
            self.text(x1 + self.S(106), cy - self.S(14), title, 26, INK, "bold", tag=tag)
            self.text(x1 + self.S(106), cy + self.S(20), sub, 14, TEXT_MUTED, tag=tag)
            self.draw_icon("chev_right", x2 - self.S(34), cy, self.S(24), TEXT_MUTED, tag)
            self.clickable(tag, lambda t=title: self.checkup_choice(t))
        if self.status and self.anim >= 1:
            self.text((x1 + x2) / 2, y + 2 * bh + self.S(60),
                      self.status, 14, TEXT_MUTED, anchor="center")

    def draw_medications(self, x1, x2, y):
        if not self.prescriptions:
            cx = (x1 + x2) / 2
            bottom = self.h - self.S(30)
            cy = (y + bottom) / 2
            self.text(cx, cy - self.S(38), "Let's add your first prescription!", 20,
                      TEXT_DARK, anchor="center")
            bw, bh = min(self.S(440), x2 - x1), self.S(62)
            bx1, bx2 = cx - bw / 2, cx + bw / 2
            by1, by2 = cy, cy + bh
            self.rrect(bx1, by1, bx2, by2, self.S(14), fill=RED, outline="", tags="addrx")
            self.draw_icon("plus", cx - self.S(52), (by1 + by2) / 2, self.S(20), WHITE, "addrx")
            self.text(cx - self.S(34), (by1 + by2) / 2, "Add prescription", 18,
                      WHITE, "bold", tag="addrx")
            self.clickable("addrx", self.add_prescription)
        else:
            self.list_header(x1, x2, y, "Your medications")
            y += self.S(40)
            for name in self.prescriptions:
                self.text(x1 + self.S(6), y + self.S(30), name, 20, INK)
                self.text(x1 + self.S(6), y + self.S(55),
                          "Prescription added today", 13, TEXT_MUTED)
                y += self.S(76)
                self.c.create_line(x1, y, x2, y, fill=BORDER)

    def draw_chat_page(self, x1, y1, x2, y2):
        c = self.c
        c.create_rectangle(x1 + self.S(1), y1 + self.S(1), x2 - self.S(1), y2 - self.S(1),
                           fill="#f3f3f5", outline="")
        header_y = y1 + self.S(54)
        c.create_rectangle(x1 + self.S(12), header_y - self.S(20), x1 + self.S(48),
                           header_y + self.S(20), fill="#f3f3f5", outline="#f3f3f5", tags="chat_back")
        self.draw_icon("back", x1 + self.S(30), header_y, self.S(24), INK, "chat_back")
        self.text(x1 + self.S(62), header_y, "Chat with Juliez", 20, INK, "bold")
        self.clickable("chat_back", self.close_chat)

        date_y = y1 + self.S(112)
        self.rrect((x1 + x2) / 2 - self.S(70), date_y - self.S(18),
                   (x1 + x2) / 2 + self.S(70), date_y + self.S(18), self.S(18),
                   fill=WHITE, outline=BORDER)
        self.text((x1 + x2) / 2, date_y, local_date_label(), 10,
                  TEXT_MUTED, "bold", anchor="center")

        input_h = self.S(58)
        input_y = y2 - self.S(30) - input_h
        messages_top = date_y + self.S(32)
        viewport_h = max(self.S(60), input_y - messages_top - self.S(10))
        viewport_w = x2 - x1 - self.S(16)
        messages = self.chat_messages or [
            ("Juliez", "Hi! How can I help you today?", local_timestamp())
        ]

        self.chat_view_frame = tk.Frame(self, bg="#f3f3f5", bd=0, highlightthickness=0)
        message_canvas = tk.Canvas(self.chat_view_frame, bg="#f3f3f5",
                                   bd=0, highlightthickness=0)
        self.chat_message_canvas = message_canvas
        content = tk.Frame(message_canvas, bg="#f3f3f5", bd=0)
        content_window = message_canvas.create_window(0, 0, window=content, anchor="nw")
        auto_scroll = True

        def scroll_canvas(*args):
            nonlocal auto_scroll
            auto_scroll = False
            message_canvas.yview(*args)

        scrollbar = tk.Scrollbar(self.chat_view_frame, orient="vertical", command=scroll_canvas)
        self.chat_scrollbar = scrollbar

        def sync_scrollbar(first, last):
            scrollbar.set(first, last)
            if float(first) <= 0 and float(last) >= 1:
                scrollbar.pack_forget()
            elif not scrollbar.winfo_manager():
                scrollbar.pack(side="right", fill="y")

        message_canvas.configure(yscrollcommand=sync_scrollbar)
        message_canvas.pack(side="left", fill="both", expand=True)
        message_canvas.bind(
            "<Configure>",
            lambda event: message_canvas.itemconfigure(content_window, width=event.width),
        )
        def update_message_region(_event=None):
            bounds = message_canvas.bbox("all")
            if bounds:
                message_canvas.configure(scrollregion=bounds)
                if auto_scroll:
                    message_canvas.yview_moveto(1.0)

        content.bind("<Configure>", update_message_region)

        def scroll_by(units):
            nonlocal auto_scroll
            auto_scroll = False
            message_canvas.yview_scroll(units, "units")
            return "break"

        def scroll_messages(event):
            units = int(-event.delta / 120) or (-1 if event.delta > 0 else 1)
            return scroll_by(units)

        def bind_scroll(widget):
            widget.bind("<MouseWheel>", scroll_messages)
            widget.bind("<Button-4>", lambda _event: scroll_by(-1))
            widget.bind("<Button-5>", lambda _event: scroll_by(1))

        bind_scroll(self.chat_view_frame)
        bind_scroll(message_canvas)
        bind_scroll(content)

        bubble_width = int(viewport_w * 0.72)
        available_text_width = max(1, bubble_width - self.S(36))
        message_font = tkfont.Font(self, font=self.font(14))

        def display_line_count(message):
            count = 0
            for paragraph in message.splitlines() or [""]:
                line = ""
                for word in paragraph.split():
                    candidate = f"{line} {word}".strip()
                    if line and message_font.measure(candidate) > available_text_width:
                        count += 1
                        line = ""
                    while message_font.measure(word) > available_text_width:
                        split = len(word)
                        while split > 1 and message_font.measure(word[:split]) > available_text_width:
                            split -= 1
                        count += 1
                        word = word[split:]
                    line = f"{line} {word}".strip()
                count += 1 if line or not paragraph else 0
            return max(1, count)

        for sender, message, timestamp in messages:
            line_count = display_line_count(message)
            bubble_height = int(self.S(58 + line_count * 20))
            alert_message = sender == "You" and self.medical_robot.has_alert_keyword(message)
            bubble_bg = "#fde8e8" if alert_message else "#e7e8ee" if sender == "You" else WHITE
            row = tk.Frame(content, bg="#f3f3f5")
            row.pack(fill="x", pady=(0, self.S(14)))
            bind_scroll(row)
            bubble = tk.Frame(row, bg=bubble_bg, width=bubble_width, height=bubble_height,
                              highlightthickness=0)
            bubble.pack(side="right" if sender == "You" else "left",
                        padx=self.S(12), anchor="e" if sender == "You" else "w")
            bubble.pack_propagate(False)
            bind_scroll(bubble)

            header = tk.Frame(bubble, bg=bubble_bg)
            header.pack(fill="x", padx=self.S(14), pady=(self.S(9), self.S(5)))
            bind_scroll(header)
            sender_label = tk.Label(header, text=sender, bg=bubble_bg, fg=RED if alert_message else INK,
                                    font=self.font(14, "bold"))
            sender_label.pack(side="left")
            bind_scroll(sender_label)
            if sender != "You":
                copy_button = tk.Button(
                    header, text="Copy", command=lambda body=message: self.copy_chat_message(body),
                    bg=bubble_bg, fg=TEXT_MUTED, activebackground=bubble_bg,
                    relief="flat", bd=0, padx=self.S(5), cursor="hand2",
                    font=self.font(10))
                copy_button.pack(side="right")
                bind_scroll(copy_button)
            time_label = tk.Label(header, text=format_chat_time(timestamp),
                                  bg=bubble_bg, fg=TEXT_MUTED,
                                  font=self.font(12))
            time_label.pack(side="right", padx=(0, self.S(8)))
            bind_scroll(time_label)

            body = tk.Text(
                bubble, height=line_count, wrap="word", bd=0, highlightthickness=0,
                padx=0, pady=0, bg=bubble_bg, fg=RED if alert_message else TEXT_DARK,
                font=self.font(14),
                selectbackground="#c7d2fe", cursor="xterm",
            )
            body.insert("1.0", message)
            body.configure(state="disabled")
            body.pack(fill="both", expand=True, padx=self.S(14), pady=(0, self.S(12)))
            body.bind("<Control-c>", lambda event, text=message: self.copy_chat_selection(event, text))
            body.bind("<Control-C>", lambda event, text=message: self.copy_chat_selection(event, text))
            bind_scroll(body)

        self.c.create_window(x1 + self.S(8), messages_top, window=self.chat_view_frame,
                             width=viewport_w, height=viewport_h, anchor="nw")
        self.after_idle(lambda: message_canvas.yview_moveto(1.0)
                        if message_canvas.winfo_exists() and auto_scroll else None)

        self.rrect(x1 + self.S(28), input_y, x2 - self.S(28), input_y + input_h,
                   self.S(16), fill=WHITE, outline=BORDER, width=self.S(1.2))
        entry = tk.Entry(self, relief="flat", bd=0, font=self.font(14), fg=TEXT_DARK,
                         insertbackground=INK)
        entry.insert(0, self.chat_draft or self.chat_placeholder)
        if not self.chat_draft:
            entry.configure(fg=TEXT_MUTED)
        entry.bind("<FocusIn>", self.chat_focus_in)
        entry.bind("<FocusOut>", self.chat_focus_out)
        entry.bind("<Return>", self.send_chat_message)
        self.chat_entry = entry
        c.create_window(x1 + self.S(52), input_y + input_h / 2,
                        width=max(20, x2 - x1 - self.S(160)), height=self.S(34),
                        window=entry, anchor="w")
        send_x = x2 - self.S(58)
        c.create_oval(send_x - self.S(21), input_y + input_h / 2 - self.S(21),
                      send_x + self.S(21), input_y + input_h / 2 + self.S(21),
                      fill=RED, outline="", tags="chat_send")
        self.draw_icon("send", send_x, input_y + input_h / 2, self.S(20), WHITE,
                       "chat_send", bg=RED)
        self.clickable("chat_send", self.send_chat_message)

    def draw_prescription_page(self, x1, y1, x2, y2):
        c = self.c
        left, right = x1 + self.S(32), x2 - self.S(32)
        top = y1 + self.S(42)
        self.text(left, top, "How would you like to add your prescription?",
                  26, "#3d3d3d", "bold")
        close_x = right - self.S(8)
        self.draw_icon("close", close_x, top, self.S(24), INK, "prescription_close")
        self.clickable("prescription_close", self.close_prescription_flow)

        if self.prescription_stage is None:
            self.text(left, top + self.S(42), "Please select your preferred option:",
                      24, "#3d3d3d")
            card1_y = top + self.S(88)
            self._prescription_option_card(
                left, right, card1_y, self.S(114), "Transfer", "transfer",
                "Have prescriptions at a different pharmacy? Request to transfer",
                "some or all prescriptions and deliver them to your doorstep."
            )
            card2_y = card1_y + self.S(132)
            self._prescription_option_card(
                left, right, card2_y, self.S(198), "Upload Photo", "upload",
                "Have a written prescription? Upload a photo to have it filled",
                "and delivered."
            )
            self.c.create_line(left, card2_y + self.S(114), right, card2_y + self.S(114),
                               fill=BORDER, dash=(3, 3))
            self.text(left + self.S(20), card2_y + self.S(150),
                      "Note:", 17, "#3d3d3d", "bold")
            self.text(left + self.S(61), card2_y + self.S(150),
                      "We need to contact your prescriber to verify the information",
                      16, "#3d3d3d")
            self.text(left + self.S(20), card2_y + self.S(174),
                      "before we can fill the prescription; this may take some time.",
                      16, "#3d3d3d")
            footer_y = card2_y + self.S(224)
            self.c.create_line(left, footer_y, right, footer_y, fill=BORDER)
            self.draw_icon("phone", left + self.S(24), footer_y + self.S(38),
                           self.S(24), "#222222", "schedule_call")
            self.text(left + self.S(54), footer_y + self.S(38),
                      "Prefer to transfer over the phone?", 17, "#3d3d3d")
            self.text(left + self.S(386), footer_y + self.S(38),
                      "Schedule a call", 17, RED, "bold", tag="schedule_call")
            self.text(left + self.S(518), footer_y + self.S(38),
                      "to have a team", 17, "#3d3d3d")
            self.text(left + self.S(54), footer_y + self.S(62),
                      "member complete the steps.", 17, "#3d3d3d")
            self.clickable("schedule_call", lambda: self.set_prescription_status(
                "A team member can help you transfer your prescription by phone."
            ))
            return

        method = self.prescription_stage
        self.text(left, top + self.S(52), f"{method} a prescription", 20, RED, "bold")
        self.text(left, top + self.S(90), "Medication name", 16, TEXT_MUTED)
        entry = tk.Entry(self, relief="flat", bd=0, font=self.font(16), fg=TEXT_DARK,
                         insertbackground=INK)
        entry.insert(0, self.prescription_draft)
        self.prescription_entry = entry
        self.rrect(left, top + self.S(108), right, top + self.S(150),
                   self.S(8), fill="", outline=BORDER, width=self.S(1))
        c.create_window(left + self.S(8), top + self.S(128),
                        width=right - left - self.S(16), height=self.S(40),
                        window=entry, anchor="w")

        action_y = top + self.S(174)
        if method == "Upload Photo":
            selected = os.path.basename(self.prescription_photo) if self.prescription_photo else "Choose a photo"
            self.rrect(left, action_y, left + self.S(240), action_y + self.S(46),
                       self.S(8), fill=WHITE, outline=RED, width=self.S(1.2), tags="choose_photo")
            self.text(left + self.S(120), action_y + self.S(23), selected, 15, RED,
                      "bold", anchor="center", tag="choose_photo")
            self.clickable("choose_photo", self.choose_prescription_photo)
            action_y += self.S(64)

        bx1, bx2 = left, left + self.S(220)
        self.rrect(bx1, action_y, bx2, action_y + self.S(48),
                   self.S(9), fill=RED, outline="", tags="save_prescription")
        self.text((bx1 + bx2) / 2, action_y + self.S(24), "Add prescription",
                  16, WHITE, "bold", anchor="center", tag="save_prescription")
        self.clickable("save_prescription", self.save_prescription)
        if self.status:
            self.text(left, action_y + self.S(70), self.status, 14, TEXT_MUTED)

    def _prescription_option_card(self, x1, x2, y, height, title, icon, line1, line2):
        tag = f"prescription::{icon}"
        self.rrect(x1, y, x2, y + height, self.S(13), fill=WHITE,
                   outline=RED, width=self.S(1.2), tags=tag)
        self.draw_icon(icon, x1 + self.S(35), y + self.S(34), self.S(24), RED, tag)
        self.text(x1 + self.S(70), y + self.S(31), title, 22, RED, "bold", tag=tag)
        self.text(x1 + self.S(70), y + self.S(58), line1, 17, "#4a4a4a", tag=tag)
        self.text(x1 + self.S(70), y + self.S(81), line2, 17, "#4a4a4a", tag=tag)
        self.clickable(tag, lambda selected=title: self.choose_prescription_method(selected))

    def draw_orders(self, x1, x2, y):
        self.list_header(x1, x2, y, "Recent orders")
        y += self.S(40)
        colours = {"Processing": ("#fff4e5", "#b26a00"), "Shipped": (SOFT_BLUE, NAVY),
                   "Delivered": ("#e8f6ee", "#1e7a46")}
        for title, sub, status in ORDERS:
            self.text(x1 + self.S(6), y + self.S(38), title, 30, INK, "normal")
            self.text(x1 + self.S(6), y + self.S(72), sub, 14, TEXT_MUTED)
            bg, fg = colours[status]
            pw = self.S(120)
            self.rrect(x2 - pw, y + self.S(34), x2, y + self.S(66), self.S(16), fill=bg, outline="")
            self.text(x2 - pw / 2, y + self.S(50), status, 13, fg, "bold", anchor="center")
            y += self.S(98)
            self.c.create_line(x1, y, x2, y, fill=BORDER)

    def draw_tasks(self, x1, x2, y):
        self.draw_icon("bulb", x1 + self.S(14), y + self.S(14), self.S(22), INK, None)
        self.text(x1 + self.S(34), y + self.S(14), "Daily care plan", 18, INK, "bold")
        self.c.create_line(x1, y + self.S(36), x2, y + self.S(36), fill=BORDER)
        y += self.S(36)
        for i, (time, ampm, label, on) in enumerate(self.tasks):
            col = INK if on else TEXT_OFF
            t = self.text(x1 + self.S(6), y + self.S(44), time, 46, col, "normal",
                          tag=f"task_time::{i}")
            tx2 = self.c.bbox(t)[2]
            self.text(tx2 + self.S(4), y + self.S(54), ampm, 20, col,
                      tag=f"task_ampm::{i}")
            self.text(x1 + self.S(8), y + self.S(84), label, 14,
                      TEXT_MUTED if on else TEXT_OFF, tag=f"task_label::{i}")
            self.toggle(x2 - self.S(84), y + self.S(50), on,
                        f"toggle::{i}", lambda k=i: self.flip_task(k))
            y += self.S(106)
            self.c.create_line(x1, y, x2, y, fill=BORDER)

    def list_header(self, x1, x2, y, title):
        self.text(x1, y + self.S(16), title, 18, INK, "bold")
        self.c.create_line(x1, y + self.S(38), x2, y + self.S(38), fill=BORDER)

    def toggle(self, x, cy, on, tag, func):
        w, h = self.S(84), self.S(48)
        track_tag = f"{tag}::track"
        knob_tag = f"{tag}::knob"
        self.rrect(x, cy - h / 2, x + w, cy + h / 2, h / 2,
                   fill=RED if on else TOGGLE_OFF, outline="", tags=(tag, track_tag))
        r = h / 2 - self.S(3)
        kx = x + w - h / 2 if on else x + h / 2
        self.c.create_oval(kx - r, cy - r + self.S(1.5), kx + r, cy + r + self.S(1.5),
                           fill="#c4c9d4", outline="", tags=(tag, knob_tag))
        self.c.create_oval(kx - r, cy - r, kx + r, cy + r,
                           fill=WHITE, outline="", tags=(tag, knob_tag))
        self.clickable(tag, func)

    def draw_dropdown(self):
        if self.dropdown == "notifications":
            items = self.notifications
            x2 = self.bell_box[0] + self.S(330)
            title = "Notifications"
        else:
            items = [("Manage profiles", "Switch between family members"),
                     ("Settings", "Account, payments, notifications"),
                     ("Sign out", "")]
            x2 = self.w - self.S(18)
            title = "Team AGILE"
        top = self.S(86)
        dw = self.S(340)
        x1 = x2 - dw
        rh = self.S(66)
        y2 = top + self.S(56) + rh * len(items)
        self.rrect(x1, top + self.S(5), x2, y2 + self.S(5), self.S(16), fill=SHADOW, outline="")
        self.rrect(x1, top, x2, y2, self.S(16), fill=WHITE, outline=BORDER, width=self.S(1.2))
        self.text(x1 + self.S(20), top + self.S(28), title, 16, INK, "bold")
        y = top + self.S(56)
        for i, (head, sub) in enumerate(items):
            tag = f"dd::{i}"
            self.c.create_line(x1 + self.S(16), y, x2 - self.S(16), y, fill=BORDER)
            self.c.create_rectangle(x1 + self.S(2), y + 1, x2 - self.S(2), y + rh - 1,
                                    fill=WHITE, outline=WHITE, tags=tag)
            if sub:
                self.text(x1 + self.S(20), y + self.S(22), head, 14, INK, "bold", tag=tag)
                self.text(x1 + self.S(20), y + self.S(46), sub, 13, TEXT_MUTED, tag=tag)
            else:
                self.text(x1 + self.S(20), y + rh / 2, head, 14, RED, "bold", tag=tag)
            if self.dropdown == "profile" and head in ("Manage profiles", "Settings"):
                self.clickable(tag, lambda h=head: self.go(h))
            else:
                self.clickable(tag, lambda: self.toggle_dropdown(None))
            y += rh


class SettingsViewMixin:
    def page_title(self, title):
        y = self.S(120)
        self.c.create_rectangle(self.sw + self.S(18), y - self.S(20), self.sw + self.S(56),
                                y + self.S(20), fill=WHITE, outline=WHITE, tags="back")
        self.draw_icon("back", self.sw + self.S(36), y, self.S(26), INK, "back")
        self.clickable("back", lambda: self.go("Dashboard"))
        self.text(self.sw + self.S(70), y, title, 22, INK)
        self.c.create_line(self.sw, y + self.S(36), self.w, y + self.S(36), fill=BORDER)
        return y + self.S(36)

    def draw_settings(self):
        y = self.page_title("Settings")
        x1 = self.sw + self.S(20)
        x2 = x1 + min(self.S(520), self.w - x1 - self.S(20))
        row = self.S(70)
        for label, icon in SETTINGS_ITEMS:
            tag = f"set::{label}"
            self.c.create_rectangle(x1, y, x2, y + row, fill=WHITE, outline=WHITE, tags=tag)
            self.draw_icon(icon, x1 + self.S(16), y + row / 2, self.S(26), INK, tag)
            self.text(x1 + self.S(46), y + row / 2, label, 17, INK, tag=tag)
            self.draw_icon("chev_right", x2 - self.S(20), y + row / 2, self.S(16), TEXT_MUTED, tag)
            self.c.create_line(x1, y + row, x2, y + row, fill=BORDER)
            self.clickable(tag, lambda: None)
            y += row

    def draw_manage_profiles(self):
        y = self.page_title("Manage profiles")
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
        self.text(x1, y + self.S(64),
                  "Choose an account. Each patient keeps a separate chat history.",
                  16, TEXT_MUTED)
        self.text(x1, y + self.S(86),
                  "These demo profiles do not sign in to real patient or doctor accounts.",
                  14, TEXT_MUTED)
        self.text(x1, y + self.S(108),
                  "Chat history is stored locally without encryption and stays separate by profile.",
                  14, TEXT_MUTED)
        if self.profile_status:
            self.text(x1, y + self.S(130), self.profile_status, 13, RED)
        y += self.S(151)
        list_y = y
        list_w = x2 - x1
        list_h = max(self.S(80), self.h - list_y - self.S(20))
        self.profiles_view_frame = tk.Frame(self, bg=WHITE, bd=0, highlightthickness=0)
        profile_canvas = tk.Canvas(
            self.profiles_view_frame, bg=WHITE, bd=0, highlightthickness=0,
        )
        profile_scrollbar = tk.Scrollbar(
            self.profiles_view_frame, orient="vertical", command=profile_canvas.yview,
        )
        profile_canvas.configure(yscrollcommand=profile_scrollbar.set)
        profile_canvas.pack(side="left", fill="both", expand=True)
        profile_scrollbar.pack(side="right", fill="y")
        role_counts = {}
        for profile in self.profiles.values():
            role_counts[profile["role"]] = role_counts.get(profile["role"], 0) + 1
        for index, profile in enumerate(self.profiles.values()):
            profile_id = profile["id"]
            tag = f"profile::{index}"
            active = profile_id == self.active_profile_id
            row_h = self.S(120)
            row_y = index * (row_h + self.S(14))
            profile_canvas.create_rectangle(
                2, row_y, list_w - 4, row_y + row_h,
                fill=WHITE, outline=RED if active else BORDER,
                width=max(1, int(self.S(1.3))), tags=tag,
            )
            profile_canvas.create_text(
                self.S(24), row_y + self.S(27), text=profile["name"],
                fill=INK, anchor="w", font=self.font(18, "bold"), tags=tag,
            )
            profile_canvas.create_text(
                self.S(24), row_y + self.S(54), text=profile["description"],
                fill=TEXT_MUTED, anchor="w", font=self.font(13), tags=tag,
            )
            if active:
                count = len(self.chat_logs.get(profile_id, []))
                profile_canvas.create_text(
                    self.S(24), row_y + self.S(86),
                    text=f"{count} chat messages saved on this device",
                    fill=TEXT_MUTED, anchor="w", font=self.font(12), tags=tag,
                )
            button_text = "Active account" if active else "Switch account"
            profile_canvas.create_text(
                list_w - self.S(171), row_y + row_h / 2, text=button_text,
                fill=RED if not active else TEXT_MUTED, anchor="center",
                font=self.font(13, "bold"), tags=tag,
            )
            delete_tag = f"profile_delete::{index}"
            can_delete = role_counts[profile["role"]] > 1
            delete_label = "Delete" if can_delete else "Required"
            delete_color = RED if can_delete else TEXT_MUTED
            delete_x1 = list_w - self.S(78)
            delete_y1 = row_y + self.S(39)
            profile_canvas.create_rectangle(
                delete_x1, delete_y1, list_w - self.S(14), row_y + self.S(81),
                fill=WHITE, outline=BORDER, width=max(1, int(self.S(1))),
                tags=delete_tag,
            )
            profile_canvas.create_text(
                (delete_x1 + list_w - self.S(14)) / 2, row_y + self.S(60),
                text=delete_label, fill=delete_color, anchor="center",
                font=self.font(10, "bold"), tags=delete_tag,
            )
            if can_delete:
                profile_canvas.tag_bind(
                    delete_tag, "<Button-1>",
                    lambda _event, selected=profile_id: self.delete_profile(selected),
                )
                profile_canvas.tag_bind(delete_tag, "<Enter>",
                                        lambda _event: profile_canvas.configure(cursor="hand2"))
                profile_canvas.tag_bind(delete_tag, "<Leave>",
                                        lambda _event: profile_canvas.configure(cursor=""))
            profile_canvas.tag_bind(
                tag, "<Button-1>", lambda _event, selected=profile_id: self.switch_profile(selected),
            )
            profile_canvas.tag_bind(tag, "<Enter>", lambda _event: profile_canvas.configure(cursor="hand2"))
            profile_canvas.tag_bind(tag, "<Leave>", lambda _event: profile_canvas.configure(cursor=""))
        content_h = max(1, int(len(self.profiles) * (self.S(120) + self.S(14))))
        profile_canvas.configure(
            scrollregion=(0, 0, int(list_w), content_h),
            width=max(1, int(list_w)),
            height=max(1, int(list_h)),
        )
        self.c.create_window(
            x1, list_y, window=self.profiles_view_frame, anchor="nw",
            width=max(1, int(list_w)), height=max(1, int(list_h)),
        )

    def draw_placeholder_page(self, title):
        y = self.page_title(title)
        cx = (self.sw + self.w) / 2
        cy = (y + self.h) / 2
        msg = "Payments are made here." if title == "Payments" else f"{title} will appear here."
        self.text(cx, cy, msg, 16, TEXT_MUTED, anchor="center")
