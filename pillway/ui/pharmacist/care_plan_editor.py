"""Care plan editor for the pharmacist: Pillway's format, AI lines clearly labelled, one-click approve.

Called by: ui/pharmacist/patient_detail.py ("Care plan" section).
- Blank medical targets are highlighted: click "Set" to fill them (the AI never does).
- Every edit is logged (who, when, before/after) and "Undo" reverses the last one.
- Approve / Request changes, and the "Pharmacist review required" switch Pillway wants to compare.
"""

from tkinter import simpledialog

from config import get_settings

from ...core import care_plan as plan_logic
from ...core.content import load
from ...storage import app_state
from ..theme import AMBER, BORDER, GREEN, INK, RED, TEXT_DARK, TEXT_MUTED, WHITE
from .patient_detail import PHARMACIST

STATUS_TEXT = {"draft": ("AI DRAFT · waiting for your approval", AMBER), "changes_requested": ("Changes requested", AMBER),
               "approved": ("Approved", GREEN), "published_without_review": ("Sent without review (comparison mode)", TEXT_DARK)}


class CarePlanEditorMixin:
    def draw_care_plan_editor(self, record, x1, y1, x2, y2):
        canvas = self.make_scroll(x1, y1, x2, y2, "#edf1f4")
        width = x2 - x1 - self.S(30)
        plan = record.get("care_plan")
        y = self.section_title(canvas, 0, self.S(4), "Care plan", "Pillway's care plan format. English first, then French.")
        y = self._draw_review_switch(canvas, y, width)
        if not plan:
            self.tx(canvas, 0, y + self.S(10), "No care plan yet. It is drafted when the patient finishes their check-in with Sarah.",
                    14, TEXT_MUTED, width=width)
            self.finish_scroll(canvas, y + self.S(80))
            return
        y = self._draw_plan_toolbar(canvas, record, plan, y, width)
        if self.show_history:
            y = self._draw_history(canvas, record, y, width)
        y = self._draw_readiness(canvas, record, plan, y, width)
        for section in plan["sections"]:
            y = self._draw_editor_section(canvas, record, plan, section, y, width)
        self.finish_scroll(canvas, y + self.S(30))

    def _draw_review_switch(self, canvas, y, width):
        on = get_settings().pharmacist.pharmacist_review_required
        self.rr(canvas, 0, y, width, y + self.S(64), self.S(12), fill=WHITE, outline=BORDER)
        self.tx(canvas, self.S(18), y + self.S(12), "Pharmacist review required", 14, INK, "bold")
        self.tx(canvas, self.S(18), y + self.S(36), "When on, new AI care plans wait for a pharmacist's approval; when off, "
                "they go straight to the patient so Pillway can compare both.", 11, TEXT_MUTED, width=width - self.S(160))
        self.btn(canvas, width - self.S(110), y + self.S(14), "ON" if on else "OFF", self.toggle_review_required,
                 "green" if on else "ghost", min_w=self.S(90))
        return y + self.S(78)

    def _draw_plan_toolbar(self, canvas, record, plan, y, width):
        label, colour = STATUS_TEXT.get(plan["status"], STATUS_TEXT["draft"])
        blanks = plan_logic.blanks_to_fill(plan)
        self.rr(canvas, 0, y, width, y + self.S(66), self.S(12), fill=WHITE, outline=colour, width=self.S(2))
        self.tx(canvas, self.S(18), y + self.S(12), label, 15, colour, "bold")
        self.tx(canvas, self.S(18), y + self.S(38), f"{len(blanks)} medical targets still to set (highlighted)  ·  "
                f"made by {'the AI' if plan['source'] == 'ai' else 'demo mode'}  ·  edits: {len(record['care_plan_history'])}",
                11, TEXT_MUTED)
        pid = record["id"]
        x = width - self.S(16)
        for text, action, kind in (("Export", lambda: self.export_plan_for(pid), "ghost"),
                                   ("History", self.toggle_history, "dark" if self.show_history else "ghost"),
                                   ("Undo", lambda: self.undo_plan_edit(pid), "ghost"),
                                   ("Request changes", lambda: self.request_plan_changes(pid), "outline"),
                                   ("Approve", lambda: self.approve_plan(pid), "green")):
            probe = canvas.create_text(0, -500, text=text, font=self.font(12, "bold"))
            w = canvas.bbox(probe)[2] - canvas.bbox(probe)[0] + self.S(28)
            canvas.delete(probe)
            x -= w
            self.btn(canvas, x, y + self.S(14), text, action, kind, size=12)
            x -= self.S(8)
        return y + self.S(80)

    def _draw_history(self, canvas, record, y, width):
        entries = list(reversed(record["care_plan_history"]))[:12]
        top = y
        self.tx(canvas, self.S(18), y + self.S(12), "Edit history (newest first)", 13, INK, "bold")
        y += self.S(40)
        for entry in entries or [{"time": "", "by": "", "line_id": "No edits yet", "before": "", "after": "", "action": ""}]:
            text = (f"{entry['time'][11:16]}  {entry['by']}  ·  {entry['action']} {entry['line_id']}:  "
                    f"{entry['before']}  →  {entry['after']}" + ("  (undone)" if entry.get("undone") else ""))
            item = self.tx(canvas, self.S(18), y, text, 11, TEXT_DARK, width=width - self.S(36))
            y = self.bottom_of(canvas, item) + self.S(6)
        box = self.rr(canvas, 0, top, width, y + self.S(8), self.S(12), fill="#f7f8fa", outline=BORDER)
        canvas.tag_lower(box)
        return y + self.S(22)

    def _draw_readiness(self, canvas, record, plan, y, width):
        self.tx(canvas, 0, y, "Readiness for change (set by the pharmacist; the advice adapts to it)", 13, INK, "bold")
        y += self.S(28)
        short = {"motivated": "Motivated", "contemplating": "Thinking about it", "not_considering": "Not considering now",
                 "other": "Other"}
        x = 0
        options = load("care_plan_template")["readiness_options"]
        for option in options:
            selected = plan.get("readiness") == option["id"]
            x = self.btn(canvas, x, y, ("● " if selected else "○ ") + short.get(option["id"], option["id"]),
                         lambda o=option["id"]: self.set_plan_readiness(record["id"], o), "dark" if selected else "ghost",
                         size=11, height=self.S(34)) + self.S(8)
        chosen = next((o for o in options if o["id"] == plan.get("readiness")), None)
        y += self.S(42)
        if chosen:
            item = self.tx(canvas, 0, y, chosen["en"], 12, TEXT_MUTED, width=width)
            y = self.bottom_of(canvas, item) + self.S(6)
        return y + self.S(12)

    def _draw_editor_section(self, canvas, record, plan, section, y, width):
        top = y
        title = f"{section['en']}  /  {section['fr']}"
        if section["id"] == "medications":
            title += "   (filled by the pharmacist, never by the AI)"
        self.tx(canvas, self.S(18), y + self.S(14), title, 15, INK, "bold")
        y += self.S(46)
        for line in section["lines"]:
            y = self._draw_editor_line(canvas, record, plan, line, y, width)
        box = self.rr(canvas, 0, top, width, y + self.S(6), self.S(12), fill=WHITE, outline=BORDER)
        canvas.tag_lower(box)
        return y + self.S(18)

    def _draw_editor_line(self, canvas, record, plan, line, y, width):
        pid, lid = record["id"], line["id"]
        text_w = width - self.S(330)
        faded = not line["included"]
        missing = "{blank}" in line["en"] and not line.get("value") and line["included"]
        x = self.S(18)
        if line["ai"]:
            x = self.chip(canvas, x, y, "AI", WHITE, AMBER, 9) + self.S(6)
        en = self.tx(canvas, x, y + self.S(2), plan_logic.render_line(line, "en", plan), 13,
                     "#b4bccb" if faded else (RED if missing else TEXT_DARK), "bold" if missing else "normal",
                     width=text_w - (x - self.S(18)))
        fr = self.tx(canvas, x, self.bottom_of(canvas, en) + self.S(2), plan_logic.render_line(line, "fr", plan) +
                     ("   [FR needs review]" if line.get("needs_review") else ""), 11, "#b4bccb" if faded else TEXT_MUTED,
                     width=text_w - (x - self.S(18)))
        if missing:
            box = canvas.bbox(en)
            mark = self.rr(canvas, box[0] - 4, box[1] - 2, box[2] + 4, box[3] + 2, 6, fill="#fff7d6", outline="")
            canvas.tag_lower(mark)
        bx = width - self.S(300)
        if "{blank}" in line["en"]:
            bx = self.btn(canvas, bx, y, "Set" if not line.get("value") else "Change",
                          lambda: self.set_plan_value(pid, lid), "primary" if missing else "ghost", size=11, height=self.S(32))
        if line["kind"] == "optional":
            bx = self.btn(canvas, bx + self.S(6), y, "Included" if line["included"] else "Include",
                          lambda: self.toggle_plan_line(pid, lid, not line["included"]), "dark" if line["included"] else "ghost",
                          size=11, height=self.S(32))
        bx = self.btn(canvas, bx + self.S(6), y, "Edit EN", lambda: self.edit_plan_text(pid, lid, "en"), "ghost", size=11,
                      height=self.S(32))
        self.btn(canvas, bx + self.S(6), y, "Edit FR", lambda: self.edit_plan_text(pid, lid, "fr"), "ghost", size=11,
                 height=self.S(32))
        return max(self.bottom_of(canvas, fr), y + self.S(34)) + self.S(12)

    # ---- actions -----------------------------------------------------------------------

    def _plan_change(self, patient_id, change, message):
        self.store.update(patient_id, change)
        self.flash(message)

    def set_plan_value(self, patient_id, line_id):
        value = simpledialog.askstring("Set target", "Value for this target (for example 7.0):", parent=self)
        if value is not None:
            self._plan_change(patient_id, lambda r: plan_logic.set_value(r, line_id, value.strip(), PHARMACIST), "Target saved")

    def edit_plan_text(self, patient_id, line_id, lang):
        line = plan_logic.find_line(self.store.load(patient_id)["care_plan"], line_id)
        text = simpledialog.askstring("Edit line", f"Edit the {'English' if lang == 'en' else 'French'} text:",
                                      initialvalue=line[lang], parent=self)
        if text and text.strip() and text.strip() != line[lang]:
            self._plan_change(patient_id, lambda r: plan_logic.edit_text(r, line_id, lang, text.strip(), PHARMACIST),
                              "Line updated (logged)")

    def toggle_plan_line(self, patient_id, line_id, included):
        self._plan_change(patient_id, lambda r: plan_logic.set_included(r, line_id, included, PHARMACIST), "Saved")

    def set_plan_readiness(self, patient_id, option):
        self._plan_change(patient_id, lambda r: plan_logic.set_readiness(r, option, PHARMACIST), "Readiness saved")

    def undo_plan_edit(self, patient_id):
        undone = []
        self.store.update(patient_id, lambda r: undone.append(plan_logic.undo_last(r, PHARMACIST)))
        self.flash("Last edit undone" if undone and undone[0] else "Nothing to undo")

    def approve_plan(self, patient_id):
        self._plan_change(patient_id, lambda r: plan_logic.approve(r, PHARMACIST), "Care plan approved")

    def request_plan_changes(self, patient_id):
        note = simpledialog.askstring("Request changes", "What should change?", parent=self)
        if note:
            self._plan_change(patient_id, lambda r: plan_logic.request_changes(r, PHARMACIST, note), "Changes requested")

    def toggle_history(self):
        self.show_history = not self.show_history
        self.render()

    def toggle_review_required(self):
        settings = get_settings().pharmacist
        settings.pharmacist_review_required = not settings.pharmacist_review_required
        app_state.save(review_required=settings.pharmacist_review_required)
        self.flash("Review " + ("required" if settings.pharmacist_review_required else "not required") +
                   " for new care plans")

    def export_plan_for(self, patient_id):
        previous = self.patient_id
        self.patient_id = patient_id
        try:
            self.export_care_plan()
        finally:
            self.patient_id = previous
