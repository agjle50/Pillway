"""The 'Add prescription' flow (Transfer or Upload photo).

Called by: ui/patient/medications.py.
"""

import os
import tkinter as tk
from tkinter import filedialog

from ..theme import (
    BORDER,
    INK,
    RED,
    TEXT_DARK,
    TEXT_MUTED,
    WHITE,
)


class PrescriptionMixin:
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
    def add_prescription(self):
        self.prescription_flow = True
        self.prescription_stage = None
        self.prescription_photo = ""
        self.prescription_draft = ""
        self.status = ""
        self.render()
    def close_prescription_flow(self):
        self.prescription_flow = False
        self.prescription_stage = None
        self.prescription_draft = ""
        self.status = ""
        self.render()
    def choose_prescription_method(self, method):
        self.prescription_stage = method
        self.prescription_draft = ""
        self.status = ""
        self.render()
    def choose_prescription_photo(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Choose prescription photo",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")]
        )
        if path:
            self.prescription_photo = path
            self.render()
    def save_prescription(self, _event=None):
        medication = self.prescription_entry.get().strip() if self.prescription_entry else ""
        if not medication:
            self.status = "Enter the medication name to continue."
            self.render()
            return
        if self.prescription_stage == "Upload Photo" and not self.prescription_photo:
            self.status = "Choose a photo of your prescription to continue."
            self.render()
            return
        self.prescriptions.append(medication)
        self.notifications.insert(
            0, ("New medication prescribed", f"{medication} has been added to your medications.")
        )
        self.prescription_flow = False
        self.prescription_stage = None
        self.prescription_draft = ""
        self.prescription_photo = ""
        self.status = ""
        self.render()
    def set_prescription_status(self, message):
        self.status = message
        self.render()
