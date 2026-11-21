"""Chooses which consultation page to draw for the selected section.

Called by: PillwayApp.render() via draw_doctor_dashboard().
"""

import tkinter as tk

from ..theme import (
    BORDER,
    INK,
    SOFT_BLUE,
    TEXT_DARK,
    TEXT_MUTED,
    WHITE,
)


class WorkspaceRouterMixin:
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
