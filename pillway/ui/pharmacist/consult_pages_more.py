"""More consultation record pages (resources, summary, take-home summary, chat log, empty pages).

Called by: ui/pharmacist/workspace_router.py.
"""

import tkinter as tk

from ..theme import (
    BORDER,
    INK,
    RED,
    TEXT_DARK,
    TEXT_MUTED,
    WHITE,
)
from ...core.medical_guidance import CARE_PLAN_REFERENCE
from ...storage.chat_history import format_chat_time


class ConsultPagesMoreMixin:
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
