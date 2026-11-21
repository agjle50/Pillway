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
        self.draw_icon("bulb", x1 + self.S(14), y + self.S(14), self.S(22), INK, None)
        self.text(x1 + self.S(34), y + self.S(14), "Daily care plan", 18, INK, "bold")
        self.c.create_line(x1, y + self.S(36), x2, y + self.S(36), fill=BORDER)
        y += self.S(36)
        for i, (time, ampm, label, on) in enumerate(self.tasks):
            col = INK if on else TEXT_OFF
            t = self.text(x1 + self.S(6), y + self.S(44), time, 46, col, "normal",
                          tag=f"task_time::{i}")
            tx2 = self.c.bbox(t)[2]
            self.text(tx2 + self.S(4), y + self.S(54), ampm, 20, col,
                      tag=f"task_ampm::{i}")
            self.text(x1 + self.S(8), y + self.S(84), label, 14,
                      TEXT_MUTED if on else TEXT_OFF, tag=f"task_label::{i}")
            self.toggle(x2 - self.S(84), y + self.S(50), on,
                        f"toggle::{i}", lambda k=i: self.flip_task(k))
            y += self.S(106)
            self.c.create_line(x1, y, x2, y, fill=BORDER)
    def flip_task(self, i):
        self.tasks[i][3] = not self.tasks[i][3]
        is_on = self.tasks[i][3]
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
            self.c.itemconfigure(track_tag, fill=self._blend_color(
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
                self.c.itemconfigure(track_tag, fill=target_color)

        animate_toggle()
