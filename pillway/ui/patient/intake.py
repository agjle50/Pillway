"""The first-visit health questionnaire screen (Pillway's intake sheet), in Pillway's card style.

Called by: ui/patient/dashboard.py. It opens by itself the first time an account with no chat
history signs in, from the Tasks tab ("Complete your health questionnaire"), and when a brand-new
patient tries to start a chat or call before doing it.
Logic (checking, saving, the health profile) lives in core/intake.py; this file only draws.

Layout: title + subtitle, a privacy note, then two columns of white cards:
  left  = Weight and height (optional) and Blood pressure
  right = Tobacco
and the buttons "Do this later" / "Save and continue" at the bottom right.
"""

import tkinter as tk

from ... import debug_log
from ...core import intake
from ..theme import (BORDER, INK, NAVY, RED, RED_SOFT, RED_TEXT, SOFT_BLUE, SURFACE_HIGH, TEXT_DARK,
                     TEXT_MUTED, WHITE)

FIELDS = ("weight", "height", "systolic", "diastolic")


class IntakeMixin:
    # ---- when to show it ---------------------------------------------------------------------

    def intake_should_show(self):
        if self.role != "patient" or not self.record:
            return False
        if getattr(self, "intake_open", False):
            return True
        return intake.needed_at_boot(self.record) and not getattr(self, "intake_later", False)

    def open_intake(self):
        self.intake_open = True
        self.intake_errors = {}
        self._intake_prefill()
        debug_log.log("intake", "questionnaire opened", patient=self.patient_id)
        self.render()

    def intake_gate(self):
        """True (and the questionnaire opens) if a brand-new patient must do it before chatting."""
        record = self.store.load(self.patient_id)
        if intake.needed_at_boot(record):
            self.chat_open = self.call_open = False
            self.flash(self.tr("Please finish your health questionnaire first."))
            self.open_intake()
            return True
        return False

    # ---- form state --------------------------------------------------------------------------

    def _intake_state(self):
        if not hasattr(self, "intake_form") or self.intake_form is None:
            self.intake_form = {"weight_unit": "kg", "height_unit": "cm", "checks_bp": None,
                                "tobacco": None, "readiness": None, "conditions": self._conditions_on_file()}
            self.intake_vars = {name: tk.StringVar(master=self) for name in FIELDS}
            self.intake_errors = {}
        return self.intake_form

    def _conditions_on_file(self):
        """Pre-tick what the pharmacy already has on file (the patient can change it)."""
        text = " ".join((self.record or {}).get("profile", {}).get("conditions", [])).lower()
        picked = []
        if "type 2" in text:
            picked.append("type2")
        if "gestational" in text:
            picked.append("gestational")
        if "blood pressure" in text or "hypertension" in text:
            picked.append("hypertension")
        return picked

    def _toggle_condition(self, key):
        picked = self._intake_state()["conditions"]
        if key == "unsure":
            picked[:] = [] if "unsure" in picked else ["unsure"]
        else:
            if "unsure" in picked:
                picked.remove("unsure")
            picked.remove(key) if key in picked else picked.append(key)
        self.intake_errors.pop("conditions", None)
        self.render()

    def _intake_prefill(self):
        """Editing a finished questionnaire: start from the saved answers."""
        self.intake_form = None
        form = self._intake_state()
        answers = (self.record or {}).get("intake", {}).get("answers") if intake.is_done(self.record or {}) else None
        if not answers:
            return
        if answers.get("weight_kg"):
            self.intake_vars["weight"].set(f"{answers['weight_kg']:g}")
        if answers.get("height_cm"):
            self.intake_vars["height"].set(str(answers["height_cm"]))
        if "checks_bp_regularly" in answers:
            form["checks_bp"] = "yes" if answers["checks_bp_regularly"] else "no"
        if answers.get("bp_systolic"):
            self.intake_vars["systolic"].set(str(answers["bp_systolic"]))
            self.intake_vars["diastolic"].set(str(answers["bp_diastolic"]))
        if "smoker" in answers:
            form["tobacco"] = "yes" if answers["smoker"] else "no"
        if answers.get("conditions"):
            form["conditions"] = list(answers["conditions"])
        form["readiness"] = answers.get("quit_readiness")

    def _intake_choose(self, key, value):
        self._intake_state()[key] = value
        self.intake_errors.pop({"checks_bp": "checks_bp", "tobacco": "tobacco",
                                "readiness": "readiness"}.get(key, ""), None)
        self.render()

    # ---- drawing -----------------------------------------------------------------------------

    def draw_intake(self, px1, py1, px2, py2):
        form = self._intake_state()
        errors = self.intake_errors
        x1, x2 = px1 + self.S(44), px2 - self.S(44)
        y = py1 + self.S(30)
        self.text(x1, y + self.S(14), "Your health questionnaire", 26, INK, "bold")
        self.text(x1, y + self.S(48), "About 3 minutes. Your answers help Sarah ask you the right questions "
                                      "instead of guessing.", 14, TEXT_MUTED)
        y += self.S(76)

        # privacy note
        note_h = self.S(66)
        self.rrect(x1, y, x2, y + note_h, self.S(10), fill=SOFT_BLUE, outline=SOFT_BLUE)
        self.draw_icon("lock", x1 + self.S(30), y + note_h / 2, self.S(22), NAVY, None, bg=SOFT_BLUE)
        self.c.create_text(
            x1 + self.S(56), y + note_h / 2, anchor="w", fill=INK, width=x2 - x1 - self.S(80),
            font=self.font(13),
            text=self.tr("Your privacy: Sarah doesn't save everything you tell her. She only keeps the medical "
                         "details that matter for your care, and shares them only with your Pillway pharmacist "
                         "and care team. In an emergency, call 911."))
        y += note_h + self.S(18)

        gap = self.S(22)
        mid = (x1 + x2) / 2
        left = (x1, mid - gap / 2)
        right = (mid + gap / 2, x2)
        bottom_limit = py2 - self.S(96)

        # left column: weight/height card, then blood pressure card
        ly = self._intake_card(left, y, "Weight and height", self._draw_weight_height)
        ly = self._intake_card(left, ly + gap, "Blood pressure", self._draw_blood_pressure)
        # right column: conditions, then tobacco
        ry = self._intake_card(right, y, "Your conditions", self._draw_conditions)
        ry = self._intake_card(right, ry + gap, "Tobacco", self._draw_tobacco)
        content_bottom = max(ly, ry)

        # buttons
        by = max(content_bottom + self.S(20), min(bottom_limit, py2 - self.S(84)))
        bh, bw = self.S(52), self.S(220)
        if errors:
            self.text(x1, by + bh / 2, "Please check the answers marked in red.", 14, RED_TEXT, "bold")
        save_x1 = x2 - bw
        self.rrect(save_x1, by, x2, by + bh, self.S(8), fill=RED, outline=RED, tags="intake_save")
        self.text((save_x1 + x2) / 2, by + bh / 2, "Save and continue", 16, WHITE, "bold", anchor="center",
                  tag="intake_save")
        self.clickable("intake_save", self.submit_intake)
        later_x2 = save_x1 - self.S(14)
        self.rrect(later_x2 - bw, by, later_x2, by + bh, self.S(8), fill=WHITE, outline=BORDER,
                   width=self.S(1.4), tags="intake_later")
        self.text(later_x2 - bw / 2, by + bh / 2, "Do this later", 16, INK, "bold", anchor="center",
                  tag="intake_later")
        self.clickable("intake_later", self.intake_do_later)

    def _intake_card(self, column, top, title, body):
        """A white Pillway card with a title; body(x1, x2, y) draws inside and returns its bottom."""
        x1, x2 = column
        pad = self.S(22)
        marker = self.c.create_line(0, 0, 0, 0, state="hidden")   # everything after it is the card's body
        self.text(x1 + pad, top + self.S(30), title, 18, INK, "bold")
        bottom = body(x1 + pad, x2 - pad, top + self.S(58)) + pad
        card = self.rrect(x1, top, x2, bottom, self.S(10), fill=WHITE, outline=BORDER, width=self.S(1.2))
        self.c.tag_lower(card, marker)   # behind its own body, but still above the page sheet
        self.c.delete(marker)
        return bottom

    def _wrapped(self, x1, x2, y, text, size=14, color=TEXT_DARK, weight="normal"):
        item = self.c.create_text(x1, y, text=self.tr(text), anchor="nw", fill=color, width=x2 - x1,
                                  font=self.font(size, weight))
        return self.c.bbox(item)[3]

    def _field_label(self, x, y, text):
        self.text(x, y, text, 12, TEXT_DARK, "bold")

    def _entry(self, name, x, y, width):
        """A Pillway input box (thin border) holding a tk.Entry; returns its bottom."""
        h = self.S(42)
        error = name in self.intake_errors or (name in ("systolic", "diastolic") and "bp" in self.intake_errors)
        self.rrect(x, y, x + width, y + h, self.S(6), fill=WHITE, outline=RED if error else BORDER,
                   width=self.S(1.6 if error else 1.2))
        entry = tk.Entry(self, textvariable=self.intake_vars[name], relief="flat", bd=0, font=self.font(15),
                         fg=TEXT_DARK, insertbackground=INK, highlightthickness=0, bg=WHITE, justify="left")
        entry.bind("<Return>", lambda _e: self.submit_intake())
        self.c.create_window(x + self.S(12), y + h / 2, anchor="w", width=max(20, width - self.S(24)),
                             height=self.S(28), window=entry)
        self.embedded_frames.append(entry)
        return y + h

    def _chips(self, x, y, options, selected, on_pick, tag, pad=40, gap=10):
        """Pill chips like Pillway's status pills: grey, or soft red with red text when chosen."""
        h = self.S(38)
        for value, label in options:
            probe = self.c.create_text(0, -500, text=self.tr(label), font=self.font(14, "bold"))
            width = self.c.bbox(probe)[2] - self.c.bbox(probe)[0] + self.S(pad)
            self.c.delete(probe)
            chosen = value == selected
            chip = f"{tag}::{value}"
            self.rrect(x, y, x + width, y + h, h / 2, fill=RED_SOFT if chosen else SURFACE_HIGH,
                       outline=RED if chosen else SURFACE_HIGH, width=self.S(1.4), tags=chip)
            self.text(x + width / 2, y + h / 2, label, 14, RED_TEXT if chosen else INK, "bold", anchor="center",
                      tag=chip)
            self.clickable(chip, lambda v=value: on_pick(v))
            x += width + self.S(gap)
        return y + h

    def _error(self, key, x, y, width=None):
        message = self.intake_errors.get(key)
        if not message:
            return y
        width = width or self.S(470)
        item = self.c.create_text(x, y + self.S(6), text=self.tr(message), anchor="nw", fill=RED_TEXT,
                                  width=width, font=self.font(12, "bold"))
        return self.c.bbox(item)[3] + self.S(4)

    def _draw_weight_height(self, x1, x2, y):
        form = self.intake_form
        y = self._wrapped(x1, x2, y, intake.SHEET[1], 13, TEXT_MUTED) + self.S(14)
        col_w = (x2 - x1 - self.S(16)) / 2
        for index, (name, label, units) in enumerate((("weight", "Weight", ("kg", "lb")),
                                                      ("height", "Height", ("cm", "in")))):
            cx = x1 + index * (col_w + self.S(16))
            self._field_label(cx, y, label)
            entry_w = col_w - self.S(112)
            self._entry(name, cx, y + self.S(14), entry_w)
            unit_key = f"{name}_unit"
            self._chips(cx + entry_w + self.S(8), y + self.S(16), [(u, u) for u in units], form[unit_key],
                        lambda v, k=unit_key: self._intake_choose(k, v), f"intake_{unit_key}", pad=20, gap=4)
            self._error(name, cx, y + self.S(56), col_w)
        y += self.S(56)
        if "weight" in self.intake_errors or "height" in self.intake_errors:
            y += self.S(36)
        self.text(x1, y + self.S(14), "Optional: leave these blank if you'd rather not say.", 12, TEXT_MUTED)
        return y + self.S(26)

    def _draw_blood_pressure(self, x1, x2, y):
        form = self.intake_form
        y = self._wrapped(x1, x2, y, intake.SHEET[4], 15, INK, "bold") + self.S(10)
        y = self._chips(x1, y, (("yes", "Yes"), ("no", "No")), form["checks_bp"],
                        lambda v: self._intake_choose("checks_bp", v), "intake_bp")
        y = self._error("checks_bp", x1, y, x2 - x1)
        if form["checks_bp"] == "yes":
            y += self.S(14)
            y = self._wrapped(x1, x2, y, intake.SHEET[5], 13, TEXT_MUTED) + self.S(10)
            box_w = self.S(120)
            self._field_label(x1, y, "Systolic (top)")
            self._entry("systolic", x1, y + self.S(14), box_w)
            self.text(x1 + box_w + self.S(14), y + self.S(35), "/", 22, TEXT_MUTED, anchor="center")
            dx = x1 + box_w + self.S(28)
            self._field_label(dx, y, "Diastolic (bottom)")
            self._entry("diastolic", dx, y + self.S(14), box_w)
            self.text(dx + box_w + self.S(10), y + self.S(35), "mmHg", 13, TEXT_MUTED)
            y = self._error("bp", x1, y + self.S(60), x2 - x1)
        return y

    def _draw_conditions(self, x1, x2, y):
        """Pillway's program covers diabetes and high blood pressure: which is the patient managing?"""
        y = self._wrapped(x1, x2, y, "Which of these are you managing? Choose all that apply.", 15, INK, "bold")
        y += self.S(10)
        picked = self.intake_form["conditions"]
        x, row_h = x1, self.S(46)
        for key, (label_en, _fr) in intake.CONDITIONS.items():
            probe = self.c.create_text(0, -500, text=self.tr(label_en), font=self.font(14, "bold"))
            width = self.c.bbox(probe)[2] - self.c.bbox(probe)[0] + self.S(40)
            self.c.delete(probe)
            if x + width > x2 and x > x1:
                x, y = x1, y + row_h
            self._chips(x, y, ((key, label_en),), key if key in picked else None,
                        lambda _v, k=key: self._toggle_condition(k), f"intake_cond_{key}")
            x += width + self.S(10)
        return self._error("conditions", x1, y + self.S(40), x2 - x1)

    def _draw_tobacco(self, x1, x2, y):
        form = self.intake_form
        y = self._wrapped(x1, x2, y, intake.SHEET[7], 15, INK, "bold") + self.S(10)
        y = self._chips(x1, y, (("yes", "Yes"), ("no", "No")), form["tobacco"],
                        lambda v: self._intake_choose("tobacco", v), "intake_tobacco")
        y = self._error("tobacco", x1, y, x2 - x1)
        if form["tobacco"] == "yes":
            y += self.S(16)
            y = self._wrapped(x1, x2, y, intake.SHEET[8], 13, TEXT_MUTED) + self.S(10)
            for value, label in intake.READINESS.items():
                y = self._radio_row(x1, x2, y, value, label, form["readiness"] == value) + self.S(8)
            y = self._error("readiness", x1, y, x2 - x1)
        return y

    def _radio_row(self, x1, x2, y, value, label, chosen):
        tag = f"intake_ready::{value}"
        text_item = self.c.create_text(x1 + self.S(48), y + self.S(14), text=self.tr(label), anchor="nw",
                                       fill=INK, width=x2 - x1 - self.S(64), font=self.font(14),
                                       tags=tag)
        bottom = self.c.bbox(text_item)[3] + self.S(14)
        box = self.rrect(x1, y, x2, bottom, self.S(8), fill=RED_SOFT if chosen else WHITE,
                         outline=RED if chosen else BORDER, width=self.S(1.4 if chosen else 1.2), tags=tag)
        self.c.tag_lower(box, text_item)
        r, cy = self.S(9), y + (bottom - y) / 2
        self.circle(self.c, x1 + self.S(24) - r, cy - r, x1 + self.S(24) + r, cy + r, fill=WHITE,
                    outline=RED if chosen else BORDER, width=self.S(2), tags=tag)
        if chosen:
            dot = self.S(5)
            self.circle(self.c, x1 + self.S(24) - dot, cy - dot, x1 + self.S(24) + dot, cy + dot, fill=RED,
                        tags=tag)
        self.clickable(tag, lambda: self._intake_choose("readiness", value))
        return bottom

    # ---- the Tasks tab row ---------------------------------------------------------------------

    def draw_intake_task(self, x1, x2, y):
        """'Complete your health questionnaire' at the top of Tasks (or 'completed' + Edit)."""
        entry = intake.task_entry(self.record, self.lang)
        h = self.S(76)
        done = entry["done"]
        self.rrect(x1, y, x2, y + h, self.S(10), fill=WHITE if done else RED_SOFT,
                   outline=BORDER if done else RED, width=self.S(1.2))
        r, cy = self.S(17), y + h / 2
        self.circle(self.c, x1 + self.S(34) - r, cy - r, x1 + self.S(34) + r, cy + r,
                    fill=SOFT_BLUE if done else RED)
        self.draw_icon("check" if done else "clipboard", x1 + self.S(34), cy, self.S(18),
                       NAVY if done else WHITE, None, bg=SOFT_BLUE if done else RED)
        self.text(x1 + self.S(66), cy - self.S(11), entry["label"], 16, INK, "bold")
        self.text(x1 + self.S(66), cy + self.S(14),
                  "Sarah uses it to ask about what matters to you." if not done
                  else "You can update your answers any time.", 13, TEXT_MUTED)
        bw, bh = self.S(150), self.S(42)
        bx2 = x2 - self.S(18)
        tag = "intake_task_open"
        self.rrect(bx2 - bw, cy - bh / 2, bx2, cy + bh / 2, self.S(8), fill=WHITE if done else RED,
                   outline=BORDER if done else RED, width=self.S(1.2), tags=tag)
        self.text(bx2 - bw / 2, cy, "Edit answers" if done else "Start", 14, INK if done else WHITE, "bold",
                  anchor="center", tag=tag)
        self.clickable(tag, self.open_intake)
        return y + h + self.S(8)

    # ---- actions -----------------------------------------------------------------------------

    def intake_do_later(self):
        self.intake_open = False
        self.intake_later = True
        self.intake_errors = {}
        debug_log.log("intake", "questionnaire put off for later", patient=self.patient_id)
        self.render()

    def submit_intake(self):
        form = dict(self._intake_state())
        form.update({name: var.get() for name, var in self.intake_vars.items()})
        record, errors = self.service.submit_intake(self.patient_id, form, self.lang)
        self.intake_errors = errors
        if errors:
            self.render()
            return
        self.record = record
        self.intake_open = False
        self.intake_form = None
        self.flash(self.tr("Thanks! Sarah has set up your health profile."))
        patient_id = self.patient_id
        self.run_in_background(lambda: self.service.refine_health_profile(patient_id),
                               "Your answers are saved.")
        self.render()
