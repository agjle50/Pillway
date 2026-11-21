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
        if not self.prescriptions:
            cx = (x1 + x2) / 2
            bottom = self.h - self.S(30)
            cy = (y + bottom) / 2
            self.text(cx, cy - self.S(38), "Let's add your first prescription!", 20,
                      TEXT_DARK, anchor="center")
            bw, bh = min(self.S(440), x2 - x1), self.S(62)
            bx1, bx2 = cx - bw / 2, cx + bw / 2
            by1, by2 = cy, cy + bh
            self.rrect(bx1, by1, bx2, by2, self.S(14), fill=RED, outline="", tags="addrx")
            self.draw_icon("plus", cx - self.S(52), (by1 + by2) / 2, self.S(20), WHITE, "addrx")
            self.text(cx - self.S(34), (by1 + by2) / 2, "Add prescription", 18,
                      WHITE, "bold", tag="addrx")
            self.clickable("addrx", self.add_prescription)
        else:
            self.list_header(x1, x2, y, "Your medications")
            y += self.S(40)
            for name in self.prescriptions:
                self.text(x1 + self.S(6), y + self.S(30), name, 20, INK)
                self.text(x1 + self.S(6), y + self.S(55),
                          "Prescription added today", 13, TEXT_MUTED)
                y += self.S(76)
                self.c.create_line(x1, y, x2, y, fill=BORDER)
