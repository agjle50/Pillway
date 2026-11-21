"""The pharmacist's consultation workspace frame: white sidebar, header and navigation actions.

Called by: PillwayApp.render() when the pharmacist opens a patient.
"""


from ..theme import (
    BORDER,
    INK,
    RED,
    TEXT_MUTED,
    WHITE,
)


class WorkspaceShellMixin:
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
    def select_doctor_patient(self, profile_id):
        profile = self.profiles.get(profile_id)
        if not profile or profile["role"] != "Patient":
            raise ValueError(f"Unknown patient profile: {profile_id}")
        self.selected_patient_id = profile_id
        self.doctor_workspace_open = True
        self.render()
    def return_to_doctor_patient_list(self):
        self.doctor_workspace_open = False
        self.render()
    def select_doctor_section(self, section):
        if section not in self.doctor_sections:
            raise ValueError(f"Unknown care-plan section: {section}")
        self.doctor_section = section
        self.render()
    def save_doctor_workspace(self):
        try:
            self.profile_store.save(list(self.profiles.values()))
            self.chat_history.save(self.chat_logs)
        except OSError as error:
            self.doctor_status = f"Could not save local care-plan data: {error}"
            self.render()
            return
        self.doctor_status = "Local demo profiles and chat logs saved."
        self.render()
