"""Medication review: the patient's medication list, with "Add medication" inside this section.

Called by: ui/pharmacist/patient_detail.py ("Medication review" section).
The pharmacist adds or edits medicines (name, dose, how often, notes, common side effects).
These feed Sarah's side-effect awareness ("dizziness can be a common side effect of…"),
but Sarah still never gives medication advice.
"""

from tkinter import simpledialog

from ...storage import audit_log
from ...storage.patient_store import new_id
from ..theme import BORDER, INK, TEXT_DARK, TEXT_MUTED, WHITE
from .patient_detail import PHARMACIST

FIELDS = [("name", "Medication name"), ("dose", "Dose (e.g. 500 mg)"), ("frequency", "How often"),
          ("indication", "What it's for"), ("notes", "Notes")]


class MedicationReviewMixin:
    def draw_medication_review(self, record, x1, y1, x2, y2):
        canvas = self.make_scroll(x1, y1, x2, y2, "#edf1f4")
        width = x2 - x1 - self.S(30)
        y = self.section_title(canvas, 0, self.S(4), "Medication review",
                               "Entered by the pharmacist. Sarah uses this list only to notice common side effects.")
        self.btn(canvas, width - self.S(200), self.S(8), "+ Add medication", lambda: self.add_medication(record["id"]),
                 "primary", min_w=self.S(190))
        columns = [("Medication", 0), ("Dose", 0.22), ("How often", 0.36), ("For", 0.56), ("Common side effects", 0.72)]
        top = y
        for title, frac in columns:
            self.tx(canvas, self.S(18) + frac * (width - self.S(160)), y + self.S(14), title, 11, TEXT_MUTED, "bold")
        y += self.S(44)
        canvas.create_line(self.S(10), y, width - self.S(10), y, fill=BORDER)
        if not record["medications"]:
            self.tx(canvas, self.S(18), y + self.S(14), "No medications on file yet.", 13, TEXT_MUTED)
            y += self.S(50)
        for med in record["medications"]:
            values = [med.get("name", ""), med.get("dose", ""), med.get("frequency", ""), med.get("indication", ""),
                      ", ".join(med.get("common_side_effects", []))]
            bottom = y
            for (title, frac), value in zip(columns, values):
                item = self.tx(canvas, self.S(18) + frac * (width - self.S(160)), y + self.S(14), value, 13,
                               INK if title == "Medication" else TEXT_DARK, "bold" if title == "Medication" else "normal",
                               width=(width - self.S(160)) * 0.2)
                bottom = max(bottom, self.bottom_of(canvas, item))
            if med.get("notes"):
                item = self.tx(canvas, self.S(18), bottom + self.S(4), f"Notes: {med['notes']}", 11, TEXT_MUTED,
                               width=width - self.S(200))
                bottom = self.bottom_of(canvas, item)
            x = self.btn(canvas, width - self.S(150), y + self.S(8), "Edit", lambda m=med["id"]: self.edit_medication(record["id"], m),
                         "ghost", size=11, height=self.S(32))
            self.btn(canvas, x + self.S(6), y + self.S(8), "Remove", lambda m=med["id"]: self.remove_medication(record["id"], m),
                     "danger", size=11, height=self.S(32))
            y = max(bottom, y + self.S(44)) + self.S(12)
            canvas.create_line(self.S(10), y, width - self.S(10), y, fill=BORDER)
        box = self.rr(canvas, 0, top, width, y + self.S(10), self.S(12), fill=WHITE, outline=BORDER)
        canvas.tag_lower(box)
        self.finish_scroll(canvas, y + self.S(40))

    def _ask_medication(self, current=None):
        current = current or {}
        values = {}
        for key, label in FIELDS:
            answer = simpledialog.askstring("Medication", label + ":", initialvalue=current.get(key, ""), parent=self)
            if answer is None:
                return None
            values[key] = answer.strip()
        effects = simpledialog.askstring("Medication", "Common side effects (comma separated):",
                                         initialvalue=", ".join(current.get("common_side_effects", [])), parent=self)
        values["common_side_effects"] = [e.strip() for e in (effects or "").split(",") if e.strip()]
        return values if values["name"] else None

    def add_medication(self, patient_id):
        values = self._ask_medication()
        if values:
            self.store.update(patient_id, lambda r: r["medications"].append({"id": new_id("med"), **values}))
            audit_log.record("medication_added", patient_id, by=PHARMACIST, name=values["name"])
            self.flash("Medication added")

    def edit_medication(self, patient_id, med_id):
        current = next(m for m in self.store.load(patient_id)["medications"] if m["id"] == med_id)
        values = self._ask_medication(current)
        if values:
            def change(record):
                for med in record["medications"]:
                    if med["id"] == med_id:
                        med.update(values)
            self.store.update(patient_id, change)
            audit_log.record("medication_edited", patient_id, by=PHARMACIST, name=values["name"])
            self.flash("Medication updated")

    def remove_medication(self, patient_id, med_id):
        self.store.update(patient_id, lambda r: r.update(medications=[m for m in r["medications"] if m["id"] != med_id]))
        audit_log.record("medication_removed", patient_id, by=PHARMACIST, med_id=med_id)
        self.flash("Medication removed")
