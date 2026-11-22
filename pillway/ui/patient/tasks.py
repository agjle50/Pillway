"""Tasks tab in the Apple Alarm style: big times, labels, red toggles.

Called by: ui/patient/dashboard.py.
"""

import time

from ..theme import (
    BORDER,
    INK,
    RED,
    TEXT_MUTED,
    TEXT_OFF,
    TOGGLE_OFF,
)


class TasksMixin:
    def draw_tasks(self, x1, x2, y):
        record = self.record or {"tasks": [], "reminders_consent": {"accepted": False}}
        self.tasks = [[t["time"], t["ampm"], t.get(f"label_{self.lang}") or t["label_en"], t["on"]] for t in record["tasks"]]
        self.task_ids = [t["id"] for t in record["tasks"]]
        self.draw_icon("bulb", x1 + self.S(14), y + self.S(14), self.S(22), INK, None)
        self.text(x1 + self.S(34), y + self.S(14), self.t("tasks.title"), 18, INK, "bold")
        self.c.create_line(x1, y + self.S(36), x2, y + self.S(36), fill=BORDER)
        y += self.S(36)
        if not self.tasks:
            self.text((x1 + x2) / 2, y + self.S(80), self.t("tasks.empty"), 16, TEXT_MUTED, anchor="center")
            return
        if not record["reminders_consent"]["accepted"]:
            y = self._draw_reminder_permission(x1, x2, y + self.S(10))
        row = max(self.S(70), min(self.S(106), (self.h - self.S(30) - y) / max(1, len(self.tasks))))
        for i, (clock, ampm, label, on) in enumerate(self.tasks):
            col = INK if on else TEXT_OFF
            t = self.text(x1 + self.S(6), y + self.S(44), clock, 46, col, "normal",
                          tag=f"task_time::{i}")
            tx2 = self.c.bbox(t)[2]
            self.text(tx2 + self.S(4), y + self.S(54), ampm, 20, col,
                      tag=f"task_ampm::{i}")
            self.text(x1 + self.S(8), y + self.S(84), label, 14,
                      TEXT_MUTED if on else TEXT_OFF, tag=f"task_label::{i}")
            self.toggle(x2 - self.S(84), y + self.S(50), on,
                        f"toggle::{i}", lambda k=i: self.flip_task(k))
            y += row
            self.c.create_line(x1, y, x2, y, fill=BORDER)

    def _draw_reminder_permission(self, x1, x2, y):
        """CASL: reminders only after the patient says yes. Medication is never a reminder."""
        self.rrect(x1, y, x2, y + self.S(84), self.S(14), fill="#eef2ff", outline=BORDER)
        self.c.create_text(x1 + self.S(18), y + self.S(26), text=self.t("tasks.permission"), anchor="w", fill=INK,
                           font=self.font(13, "bold"), width=x2 - x1 - self.S(230))
        self.text(x1 + self.S(18), y + self.S(60), self.t("tasks.no_meds"), 11, TEXT_MUTED)
        bx1 = x2 - self.S(196)
        self.rrect(bx1, y + self.S(18), x2 - self.S(16), y + self.S(66), self.S(12), fill=RED, outline="", tags="allow_reminders")
        self.text((bx1 + x2 - self.S(16)) / 2, y + self.S(42), self.t("tasks.allow"), 13, "#ffffff", "bold",
                  anchor="center", tag="allow_reminders")
        self.clickable("allow_reminders", self.allow_reminders)
        return y + self.S(92)

    def allow_reminders(self):
        from ...storage.patient_store import now_iso
        self.store.update(self.patient_id, lambda r: r.update(reminders_consent={"accepted": True, "time": now_iso()}))
        self.flash("Reminders on" if self.lang == "en" else "Rappels activés")

    def flip_task(self, i):
        self.tasks[i][3] = not self.tasks[i][3]
        is_on = self.tasks[i][3]
        task_id = self.task_ids[i] if i < len(getattr(self, "task_ids", [])) else None
        if task_id:
            def change(record):
                for task in record["tasks"]:
                    if task["id"] == task_id:
                        task["on"] = is_on
            self.store.update(self.patient_id, change)
        track_tag = f"toggle::{i}::track"
        knob_tag = f"toggle::{i}::knob"
        track_items = self.c.find_withtag(track_tag)
        track_bounds = self.c.bbox(track_tag)
        knob_bounds = self.c.bbox(knob_tag)
        if not track_items or not track_bounds or not knob_bounds:
            self.render()
            return

        old_job = self._task_toggle_jobs.pop(i, None)
        if old_job:
            self.after_cancel(old_job)
        track_x1, track_y1, track_x2, track_y2 = track_bounds
        current_x = [(knob_bounds[0] + knob_bounds[2]) / 2]
        starting_x = current_x[0]
        radius = (track_y2 - track_y1) / 2
        target_x = track_x2 - radius if is_on else track_x1 + radius
        start_color = self.c.itemcget(track_items[0], "fill")
        target_color = RED if is_on else TOGGLE_OFF
        started = time.monotonic()

        def animate_toggle():
            self._task_toggle_jobs.pop(i, None)
            progress = min(1.0, (time.monotonic() - started) / 0.18)
            eased = 1 - (1 - progress) ** 3
            next_x = starting_x + (target_x - starting_x) * eased
            self.c.move(knob_tag, next_x - current_x[0], 0)
            current_x[0] = next_x
            self.recolor(track_tag, fill=self._blend_color(
                start_color, target_color, eased,
            ))
            self.c.itemconfigure(f"task_time::{i}", fill=INK if is_on else TEXT_OFF)
            self.c.itemconfigure(f"task_ampm::{i}", fill=INK if is_on else TEXT_OFF)
            self.c.itemconfigure(
                f"task_label::{i}", fill=TEXT_MUTED if is_on else TEXT_OFF,
            )
            if progress < 1:
                self._task_toggle_jobs[i] = self.after(16, animate_toggle)
            else:
                self.recolor(track_tag, fill=target_color)

        animate_toggle()
