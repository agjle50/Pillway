"""Chooses which consultation-record page to draw (the pages modelled on Pillway's own form).

Called by: ui/pharmacist/patient_detail.py for the sections under "CONSULTATION RECORD".
"""

from ...storage.patient_store import display_name


from ..theme import (
    BORDER,
    INK,
    TEXT_DARK,
    TEXT_MUTED,
    WHITE,
)


class WorkspaceRouterMixin:
    def draw_consult_page(self, record, x1, y1, x2, y2):
        """Draw one consultation-record page (modelled on Pillway's own care-plan form)."""
        patient = {"name": display_name(record)}
        content_x, content_w = x1 + self.S(10), x2 - x1 - self.S(20)
        heading_y = y1 + self.S(16)
        self.text(content_x, heading_y, self.doctor_section, 23, INK, "bold")
        subtitles = {
            "User account information": "Account details and consultation journey",
            "Patient information": "Demographics and clinical baseline",
            "Checklist for completeness": "Review the consultation sections and their status",
            "Diabetes assessment": "Diabetes-specific clinical review",
            "Pharmacist follow-up plan": "Schedule and manage follow-up calls",
            "Resources provided": "Select and share relevant patient supports",
            "Summary for today's discussion": "Create a clear consultation record",
            "Referrals": "Coordinate specialty care and track outcomes",
            "Take home summary": "Review a patient-facing summary",
            "Final review & billing": "Confirm completion and billing details",
        }
        self.text(content_x, heading_y + self.S(27), subtitles.get(self.doctor_section, "") +
                  "   (Phase 2: these pages are a static mock-up of Pillway's form)", 12, TEXT_MUTED)
        page_y = heading_y + self.S(54)
        page_bottom = y2 - self.S(18)
        section = self.doctor_section
        if section == "User account information":
            self._draw_doctor_account_page(content_x, page_y, content_w, page_bottom, patient)
        elif section == "Patient information":
            self._draw_doctor_patient_page(content_x, page_y, content_w)
        elif section == "Checklist for completeness":
            self._draw_doctor_checklist_page(content_x, page_y, content_w)
        elif section == "Diabetes assessment":
            self._draw_doctor_diabetes_page(content_x, page_y, content_w)
        elif section == "Resources provided":
            self._draw_doctor_resources_page(content_x, page_y, content_w)
        elif section == "Summary for today's discussion":
            self._draw_doctor_summary_page(content_x, page_y, content_w, patient)
        elif section == "Take home summary":
            self._draw_doctor_take_home_page(content_x, page_y, content_w)
        else:
            empty = {"Pharmacist follow-up plan": "No follow-up calls are saved.",
                     "Referrals": "No referrals are saved."}.get(section, "No billing details are saved.")
            self._draw_doctor_empty_page(content_x, page_y, content_w, empty)

    def _doctor_card(self, x, y, width, height, title):
        self.rrect(x, y, x + width, y + height, self.S(12), fill=WHITE,
                   outline=BORDER, width=self.S(1))
        self.text(x + self.S(18), y + self.S(24), title, 15, INK, "bold")

    def _doctor_field(self, x, y, width, label, value):
        self.text(x, y, label, 9, TEXT_MUTED)
        self.rrect(x, y + self.S(8), x + width, y + self.S(42), self.S(5),
                   fill=WHITE, outline=BORDER, width=self.S(1))
        self.text(x + self.S(9), y + self.S(25), value, 11, TEXT_DARK)
