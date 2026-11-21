"""The pharmacist's grid of patient tiles.

Called by: PillwayApp.render() for the pharmacist Dashboard.
"""

import tkinter as tk

from ..theme import (
    BORDER,
    INK,
    ORANGE,
    SHADOW,
    TEXT_DARK,
    TEXT_MUTED,
    WHITE,
)


class PatientPickerMixin:
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
