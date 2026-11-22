"""Care plan tab (patient side): Pillway's format, English first then French.

Called by: ui/patient/dashboard.py when the "Care plan" tab is selected.
Shows "Draft, waiting for your pharmacist's approval" until a pharmacist approves it.
Medical targets the pharmacist hasn't set yet are highlighted "to be set by your pharmacist".
"""

from tkinter import filedialog

from ...core import care_plan as plan_logic
from ...core.content import load
from ..theme import RED_TEXT, AMBER, AMBER_SOFT, BORDER, GREEN, GREEN_SOFT, INK, RED, TEXT_DARK, TEXT_MUTED

STATUS_STYLE = {"draft": ("careplan.draft", AMBER_SOFT, AMBER), "changes_requested": ("careplan.changes", AMBER_SOFT, AMBER),
                "approved": ("careplan.approved", GREEN_SOFT, GREEN),
                "published_without_review": ("careplan.unreviewed", "#eef1f6", TEXT_DARK)}


class PatientCarePlanMixin:
    def draw_patient_care_plan(self, x1, x2, y, bottom):
        plan = (self.record or {}).get("care_plan")
        if not plan:
            self.text((x1 + x2) / 2, (y + bottom) / 2, self.t("careplan.empty"), 18, TEXT_MUTED, anchor="center")
            return
        canvas = self.make_scroll(x1, y, x2, bottom)
        width = x2 - x1 - self.S(24)
        key, bg, fg = STATUS_STYLE.get(plan["status"], STATUS_STYLE["draft"])
        self.rr(canvas, 0, 0, width, self.S(50), self.S(12), fill=bg, outline=fg)
        self.tx(canvas, self.S(18), self.S(25), self.t(key), 15, fg, "bold", anchor="w")
        self.btn(canvas, width - self.S(170), self.S(6), "Save as text" if self.lang == "en" else "Enregistrer",
                 self.export_care_plan, "ghost", size=11, min_w=self.S(160))
        cy = self.S(74)
        # simple: only the patient's own language on screen ("Save as text" still has English + French)
        cy = self._draw_plan_language(canvas, plan, self.lang if self.lang in ("en", "fr") else "en", cy, width)
        cy += self.S(30)
        self.finish_scroll(canvas, cy)

    def _draw_plan_language(self, canvas, plan, lang, y, width):
        template = load("care_plan_template")
        self.tx(canvas, 0, y, template["care_plan_title"][lang], 24, RED_TEXT, "bold")
        y += self.S(44)
        if plan["goals"]:
            item = self.tx(canvas, 0, y, template["goals_title"][lang], 14, INK, "bold", width=width)
            y = self.bottom_of(canvas, item) + self.S(6)
            for goal in plan["goals"]:
                item = self.tx(canvas, self.S(18), y, "• " + goal, 14, TEXT_DARK, width=width - self.S(18))
                y = self.bottom_of(canvas, item) + self.S(4)
            y += self.S(12)
        for section in plan["sections"]:
            canvas.create_line(0, y, width, y, fill=BORDER)
            y += self.S(12)
            self.tx(canvas, 0, y, section[lang], 17, INK, "bold")
            y += self.S(32)
            for line in plan_logic.visible_lines(section):
                text = plan_logic.render_line(line, lang, plan)
                if line.get("suggested") and not line.get("confirmed"):
                    text += (" (votre pharmacien va confirmer)" if lang == "fr" else " (your pharmacist will confirm)")
                missing = plan_logic.BLANK in text
                if missing:
                    text = text.replace(plan_logic.BLANK, f"[{self.t('careplan.blank')}]")
                item = self.tx(canvas, self.S(18), y, "• " + text, 14, AMBER if missing else TEXT_DARK,
                               "bold" if missing else "normal", width=width - self.S(18))
                if missing:
                    box = canvas.bbox(item)
                    highlight = self.rr(canvas, box[0] - 4, box[1] - 2, box[2] + 4, box[3] + 2, 6, fill="#fff7d6", outline="")
                    canvas.tag_lower(highlight)
                y = self.bottom_of(canvas, item) + self.S(6)
            y += self.S(8)
        if plan["barriers"]:
            canvas.create_line(0, y, width, y, fill=BORDER)
            y += self.S(12)
            item = self.tx(canvas, 0, y, template["barriers_title"][lang], 15, INK, "bold", width=width)
            y = self.bottom_of(canvas, item) + self.S(8)
            for barrier in plan["barriers"]:
                item = self.tx(canvas, self.S(18), y, f"• {barrier.get('barrier_' + lang, '')}: {barrier.get('plan_' + lang, '')}",
                               14, TEXT_DARK, width=width - self.S(18))
                y = self.bottom_of(canvas, item) + self.S(6)
        return y

    def export_care_plan(self):
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".txt", initialfile="care_plan.txt",
                                            filetypes=[("Text file", "*.txt")])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(plan_logic.to_text(self.store.load(self.patient_id)))
        self.flash("Care plan saved" if self.lang == "en" else "Plan de soins enregistré")


