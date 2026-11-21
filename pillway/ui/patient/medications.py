"""Medications tab: the patient's medication list.

Called by: ui/patient/dashboard.py.
"""


from ..theme import (
    BORDER,
    INK,
    RED,
    TEXT_DARK,
    TEXT_MUTED,
    WHITE,
)


class MedicationsMixin:
    def draw_medications(self, x1, x2, y):
        """The pharmacy's list (entered by the pharmacist) plus prescriptions the patient added."""
        meds = (self.record or {}).get("medications", [])
        if not self.prescriptions and not meds:
            cx = (x1 + x2) / 2
            bottom = self.h - self.S(30)
            cy = (y + bottom) / 2
            self.text(cx, cy - self.S(38), "Let's add your first prescription!", 20,
                      TEXT_DARK, anchor="center")
            self._add_prescription_button(cx, cy, min(self.S(440), x2 - x1))
            return
        self.list_header(x1, x2, y, self.t("meds.on_file"))
        y += self.S(40)
        for med in meds:
            self.text(x1 + self.S(6), y + self.S(30), f"{med['name']} {med.get('dose', '')}".strip(), 20, INK)
            self.text(x1 + self.S(6), y + self.S(55), f"{med.get('frequency', '')}  ·  {med.get('indication', '')}",
                      13, TEXT_MUTED)
            y += self.S(76)
            self.c.create_line(x1, y, x2, y, fill=BORDER)
        for name in self.prescriptions:
            self.text(x1 + self.S(6), y + self.S(30), name, 20, INK)
            self.text(x1 + self.S(6), y + self.S(55), "Prescription added today", 13, TEXT_MUTED)
            y += self.S(76)
            self.c.create_line(x1, y, x2, y, fill=BORDER)
        self._add_prescription_button((x1 + x2) / 2, y + self.S(24), min(self.S(360), x2 - x1))

    def _add_prescription_button(self, cx, top, width):
        bh = self.S(62)
        self.rrect(cx - width / 2, top, cx + width / 2, top + bh, self.S(14), fill=RED, outline="", tags="addrx")
        self.draw_icon("plus", cx - self.S(52), top + bh / 2, self.S(20), WHITE, "addrx")
        self.text(cx - self.S(34), top + bh / 2, self.t("meds.add"), 18, WHITE, "bold", tag="addrx")
        self.clickable("addrx", self.add_prescription)
