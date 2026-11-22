"""Consultation record pages modelled on Pillway's real care-plan form (account, patient, meds, checklist, diabetes).

Called by: ui/pharmacist/workspace_router.py.
"""


from ..theme import (
    BORDER,
    RED,
    TEXT_DARK,
    TEXT_MUTED,
    WHITE,
)


class ConsultPagesMixin:
    @staticmethod
    def _patient_value(value, fallback="Not on file"):
        if isinstance(value, (list, tuple)):
            value = ", ".join(str(item) for item in value if item)
        return str(value).strip() if value is not None and str(value).strip() else fallback

    def _draw_doctor_account_page(self, x, y, width, bottom, patient):
        profile = patient["profile"]
        details_h = min(self.S(286), max(self.S(210), (bottom - y) * 0.57))
        self._doctor_card(x, y, width, details_h, "User account information")
        labels = (
            ("Name", patient["name"]),
            ("Date of birth", self._patient_value(profile.get("date_of_birth"))),
            ("Sex", self._patient_value(profile.get("sex"))),
            ("Health card", self._patient_value(profile.get("health_card"))),
            ("Phone", self._patient_value(profile.get("phone"))),
            ("Email", self._patient_value(profile.get("email"))),
            ("Address", self._patient_value(profile.get("address"))),
            ("Preferred language", self._patient_value(profile.get("language"))),
            ("Pharmacy / prescriber", self._patient_value(
                " / ".join(value for value in (profile.get("pharmacy"), profile.get("prescriber")) if value)
            )),
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

    def _draw_doctor_patient_page(self, x, y, width, patient):
        profile = patient["profile"]
        gap = self.S(16)
        card_w = (width - gap) / 2
        card_h = self.S(260)
        self._doctor_card(x, y, card_w, card_h, "Demographics")
        self._doctor_card(x + card_w + gap, y, card_w, card_h, "Lab results")
        height_weight = " / ".join(
            value for value in (
                f"{profile['height_cm']} cm" if profile.get("height_cm") else "",
                f"{profile['weight_kg']} kg" if profile.get("weight_kg") else "",
            ) if value
        )
        left_values = (
            ("Age", self._patient_value(profile.get("age"), "Not on file")),
            ("Sex", self._patient_value(profile.get("sex"))),
            ("Height / weight", self._patient_value(height_weight)),
            ("Medical conditions", self._patient_value(profile.get("conditions"))),
        )
        right_values = (
            ("A1C", self._patient_value(profile.get("last_a1c"))),
            ("Blood pressure", self._patient_value(profile.get("last_bp"))),
            ("LDL cholesterol", self._patient_value(profile.get("last_ldl"))),
            ("Targets", self._patient_value(profile.get("targets"))),
        )
        for index, (label, value) in enumerate(left_values):
            self._doctor_field(x + self.S(18), y + self.S(54 + index * 48),
                               card_w - self.S(36), label, value)
        for index, (label, value) in enumerate(right_values):
            self._doctor_field(x + card_w + gap + self.S(18), y + self.S(54 + index * 48),
                               card_w - self.S(36), label, value)
        bottom_y = y + card_h + gap
        self._doctor_card(x, bottom_y, width, self.S(150), "Clinical context")
        context = "Medical conditions: " + self._patient_value(profile.get("conditions"))
        allergies = self._patient_value(profile.get("allergies"))
        if allergies != "Not on file":
            context += "\nAllergies: " + allergies
        self.c.create_text(
            x + self.S(18), bottom_y + self.S(48),
            text=context,
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

    def _draw_doctor_diabetes_page(self, x, y, width, patient):
        profile = patient["profile"]
        gap = self.S(16)
        card_w = (width - gap) / 2
        card_h = self.S(185)
        self._doctor_card(x, y, card_w, card_h, "Diabetes profile")
        self._doctor_card(x + card_w + gap, y, card_w, card_h, "Monitoring & A1C")
        self._doctor_field(x + self.S(18), y + self.S(58), card_w - self.S(36),
                           "Diabetes type", self._patient_value(profile.get("diabetes_type")))
        self._doctor_field(x + self.S(18), y + self.S(112), card_w - self.S(36),
                           "Diagnosis date", self._patient_value(profile.get("diagnosis_date")))
        self._doctor_field(x + card_w + gap + self.S(18), y + self.S(58),
                           card_w - self.S(36), "Monitoring method", self._patient_value(profile.get("monitoring")))
        self._doctor_field(x + card_w + gap + self.S(18), y + self.S(112),
                           card_w - self.S(36), "Recent A1C", self._patient_value(profile.get("last_a1c")))
        focus_y = y + card_h + gap
        self.rrect(x, focus_y, x + width, focus_y + self.S(100), self.S(10),
                   fill="#fff1ed", outline="#f4cfc5", width=self.S(1))
        self.text(x + self.S(18), focus_y + self.S(24), "Clinical focus", 13, RED, "bold")
        self.c.create_text(
            x + self.S(18), focus_y + self.S(45),
            text="Conditions: " + self._patient_value(profile.get("conditions")) +
                 "\nAllergies: " + self._patient_value(profile.get("allergies")),
            fill=TEXT_DARK, anchor="nw", width=width - self.S(36), font=self.font(10),
        )
