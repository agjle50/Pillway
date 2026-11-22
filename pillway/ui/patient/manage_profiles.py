"""Manage profiles page: switch, add and delete demo profiles.

Called by: PillwayApp.render() for the 'Manage profiles' section.
"""

import tkinter as tk

from ..theme import (RED_TEXT, 
    BORDER,
    INK,
    RED,
    TEXT_MUTED,
    WHITE,
)


class ManageProfilesMixin:
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
            self.text(x1, y + self.S(130), self.profile_status, 13, RED_TEXT)
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
                record_id = profile.get("record_id") or profile_id
                count = len(self.store.load(record_id)["messages"]) if profile["role"] == "Patient" else 0
                profile_canvas.create_text(
                    self.S(24), row_y + self.S(86),
                    text=f"{count} chat messages saved on this device",
                    fill=TEXT_MUTED, anchor="w", font=self.font(12), tags=tag,
                )
            switch_tag = f"profile_switch::{index}"
            switch_x1, switch_x2 = list_w - self.S(244), list_w - self.S(104)
            profile_canvas.create_rectangle(
                switch_x1, row_y + self.S(38), switch_x2, row_y + self.S(82),
                fill="#fff0ed" if not active else "#f5f6f8",
                outline=BORDER, width=max(1, int(self.S(1))), tags=switch_tag,
            )
            profile_canvas.create_text(
                (switch_x1 + switch_x2) / 2, row_y + row_h / 2,
                text="Active account" if active else "Switch account",
                fill=RED if not active else TEXT_MUTED, anchor="center",
                font=self.font(12, "bold"), tags=switch_tag,
            )
            if not active:
                self.bind_click(
                    profile_canvas, switch_tag,
                    lambda selected=profile_id: self.switch_profile(selected),
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
                self.bind_click(
                    profile_canvas, delete_tag,
                    lambda selected=profile_id: self.delete_profile(selected),
                )
            self.bind_click(
                profile_canvas, tag,
                lambda selected=profile_id: self.switch_profile(selected),
            )
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
