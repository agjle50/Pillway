"""One patient's screen for the pharmacist: BLACK sidebar, header, and the section router.

Called by: PillwayApp.render() after the pharmacist clicks a patient tile.
Sections (all clickable, at most 2 clicks from the dashboard): Flagged messages, Possible
issues, Log, Care plan, Medication review, Check-ins, Bot settings, Custom flag words, then
the consultation record pages modelled on Pillway's own form.
Keyboard: Ctrl+1..Ctrl+8 switch sections, Esc goes back to all patients.
"""

from ...core import check_ins
from ...storage.patient_store import display_name, initials
from ..theme import (BLACK_SIDEBAR, BLACK_SIDEBAR_SELECTED, BLACK_SIDEBAR_TEXT, BORDER, GREEN, INK, LIVE_GREEN,
                     PAGE_BG, RED, TEXT_MUTED, WHITE)

DETAIL_SECTIONS = ["Flagged messages", "Possible issues", "Log", "Care plan", "Medication review",
                   "Check-ins", "Bot settings", "Custom flag words"]
CONSULT_SECTIONS = ["User account information", "Patient information", "Checklist for completeness",
                    "Diabetes assessment", "Pharmacist follow-up plan", "Resources provided",
                    "Summary for today's discussion", "Referrals", "Take home summary", "Final review & billing"]
PHARMACIST = "Pharmacist (demo)"


class PatientDetailMixin:
    # ---- navigation (method names kept from the old code; tests use them) ----------------

    def select_doctor_patient(self, patient_id):
        self.selected_patient_id = patient_id
        self.doctor_workspace_open = True
        self.dropdown = None
        if hasattr(self, "c"):
            self._bind_detail_shortcuts()
        self.render()

    def return_to_doctor_patient_list(self):
        self.doctor_workspace_open = False
        self.render()

    def select_detail_section(self, section):
        self.detail_section = section
        if section in CONSULT_SECTIONS:
            self.doctor_section = section
        self.render()

    def select_doctor_section(self, section):
        self.select_detail_section(section)

    def _bind_detail_shortcuts(self):
        for number, section in enumerate(DETAIL_SECTIONS, start=1):
            self.bind_all(f"<Control-Key-{number}>", lambda _e, s=section: self.doctor_workspace_open
                          and self.select_detail_section(s))

    # ---- drawing ----------------------------------------------------------------------

    def detail_record(self):
        return self.store.load(self.selected_patient_id)

    def draw_detail_sidebar(self):
        record = self.detail_record()
        c, sw, h = self.c, self.sw, self.h
        c.create_rectangle(0, 0, sw, h, fill=BLACK_SIDEBAR, outline=BLACK_SIDEBAR)
        self.text(self.S(24), self.S(40), "PATIENT", 10, "#9a9aa6", "bold")
        self.text(self.S(24), self.S(68), display_name(record), 18, WHITE, "bold")
        y, row = self.S(104), min(self.S(42), (h - self.S(170)) / (len(DETAIL_SECTIONS) + len(CONSULT_SECTIONS) + 2))
        open_count = sum(1 for f in record["flags"] if f["status"] == "open")
        for index, label in enumerate(DETAIL_SECTIONS + [None] + CONSULT_SECTIONS):
            if label is None:
                y += self.S(8)
                c.create_line(self.S(16), y, sw - self.S(16), y, fill="#3a3a44")
                self.text(self.S(24), y + self.S(14), "CONSULTATION RECORD", 9, "#9a9aa6", "bold")
                y += self.S(28)
                continue
            tag = f"detail_nav::{index}"
            selected = label == self.detail_section
            bg = BLACK_SIDEBAR_SELECTED if selected else BLACK_SIDEBAR
            c.create_rectangle(0, y, sw, y + row, fill=bg, outline=bg, tags=tag)
            if selected:
                c.create_rectangle(0, y, self.S(5), y + row, fill=RED, outline=RED, tags=tag)
            self.text(self.S(24), y + row / 2, label, 13 if index < len(DETAIL_SECTIONS) else 11,
                      WHITE if selected else BLACK_SIDEBAR_TEXT, "bold" if selected else "normal", tag=tag)
            if label == "Flagged messages" and open_count:
                c.create_oval(sw - self.S(52), y + row / 2 - self.S(12), sw - self.S(28), y + row / 2 + self.S(12),
                              fill=RED, outline="", tags=tag)
                self.text(sw - self.S(40), y + row / 2, str(open_count), 11, WHITE, "bold", anchor="center", tag=tag)
            self.clickable(tag, lambda s=label: self.select_detail_section(s))
            y += row
        back = "detail_back"
        c.create_rectangle(0, h - self.S(54), sw, h, fill=BLACK_SIDEBAR, outline="#3a3a44", tags=back)
        self.text(self.S(24), h - self.S(27), "‹  All patients   (Esc)", 13, WHITE, "bold", tag=back)
        self.clickable(back, self.return_to_doctor_patient_list)

    def draw_detail_header(self):
        record = self.detail_record()
        c, w = self.c, self.w
        header_h = self.S(78)
        c.create_rectangle(self.sw, 0, w, header_h, fill=WHITE, outline=WHITE)
        c.create_line(self.sw, header_h, w, header_h, fill=BORDER)
        x = self.sw + self.S(28)
        c.create_oval(x, self.S(17), x + self.S(44), self.S(61), fill="#eef2ff", outline="")
        self.text(x + self.S(22), self.S(39), initials(record), 15, "#4c5ba8", "bold", anchor="center")
        name = self.text(x + self.S(58), self.S(28), display_name(record), 20, INK, "bold")
        conditions = " · ".join(record["profile"].get("conditions", []))
        self.text(x + self.S(58), self.S(56), f"{record['profile'].get('age', '')} y  ·  {conditions}", 11, TEXT_MUTED)
        nx = self.c.bbox(name)[2] + self.S(16)
        if check_ins.is_active(record):
            c.create_oval(nx, self.S(22), nx + self.S(12), self.S(34), fill=LIVE_GREEN, outline="")
            self.text(nx + self.S(18), self.S(28), "ACTIVE now", 11, GREEN, "bold")
        consent = record["consent"]
        consent_text = (f"Consent to AI chat and pharmacist viewing: given {consent['time'][:16].replace('T', ' ')}"
                        if consent.get("accepted") else "Consent not given yet")
        self.text(w - self.S(24), self.S(28), consent_text, 10, TEXT_MUTED, anchor="e")
        self.text(w - self.S(24), self.S(54), "Ctrl+1…8 switch sections · Esc back", 10, TEXT_MUTED, anchor="e")

    def detail_box(self):
        return self.sw + self.S(20), self.S(96), self.w - self.S(20), self.h - self.S(16)

    def draw_patient_detail(self):
        x1, y1, x2, y2 = self.detail_box()
        self.c.create_rectangle(self.sw, self.S(79), self.w, self.h, fill=PAGE_BG, outline="")
        record = self.detail_record()
        router = {"Flagged messages": self.draw_flags_section, "Possible issues": self.draw_highlights_section,
                  "Log": self.draw_log_section, "Care plan": self.draw_care_plan_editor,
                  "Medication review": self.draw_medication_review, "Check-ins": self.draw_check_ins_section,
                  "Bot settings": self.draw_bot_settings, "Custom flag words": self.draw_custom_words}
        if self.detail_section in router:
            router[self.detail_section](record, x1, y1, x2, y2)
        else:
            self.draw_consult_page(record, x1, y1, x2, y2)
