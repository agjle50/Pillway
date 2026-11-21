"""Flagged messages, shown like comments in Google Docs.

Called by: ui/pharmacist/patient_detail.py ("Flagged messages" section).
Each card: the exact patient message, time, tier colour + words (never colour alone), where it
came from (chat or call), matched words, the one-line AI reason, what Sarah asked next and
the patient's extra details. Actions: Resolve (records who/when, can be reopened), Add note,
"Right flag" / "Wrong flag" feedback. A 3-line recap sits on top so the patient never has to
repeat themselves. Repeat flags on the same topic are grouped (no alert fatigue).
"""

from tkinter import simpledialog

from ...storage import audit_log
from ...storage.patient_store import now_iso
from ..theme import AMBER, AMBER_SOFT, BORDER, GREEN, INK, RED, RED_SOFT, TEXT_DARK, TEXT_MUTED, WHITE
from .patient_detail import PHARMACIST

TIER_STYLE = {1: ("URGENT", RED, RED_SOFT), 2: ("WATCH", AMBER, AMBER_SOFT)}


class FlagsMixin:
    def draw_flags_section(self, record, x1, y1, x2, y2):
        canvas = self.make_scroll(x1, y1, x2, y2, "#edf1f4")
        width = x2 - x1 - self.S(30)
        y = self.section_title(canvas, 0, self.S(4), "Flagged messages",
                               "Like comments in Google Docs. Resolve a card when it's handled. The red badge counts open cards.")
        newest_first = sorted((f for f in record["flags"] if f["status"] == "open"),
                              key=lambda f: f.get("updated") or f["time"], reverse=True)
        open_flags = sorted(newest_first, key=lambda f: f["tier"])  # urgent first, newest first inside
        if open_flags or any(q["status"] == "open" for q in record["pharmacist_requests"]):
            y = self._draw_recap(canvas, record, y, width)
        for request in [q for q in record["pharmacist_requests"] if q["status"] == "open"]:
            y = self._draw_request_card(canvas, record, request, y, width) + self.S(12)
        if not open_flags:
            self.rr(canvas, 0, y, width, y + self.S(60), self.S(12), fill="#e8f6ee", outline=GREEN)
            self.tx(canvas, self.S(20), y + self.S(30), "All clear: no open flags for this patient.", 14, GREEN, "bold", anchor="w")
            y += self.S(76)
        for flag in open_flags:
            y = self._draw_flag_card(canvas, record, flag, y, width) + self.S(14)
        resolved = [f for f in record["flags"] if f["status"] == "resolved"]
        if resolved:
            label = ("▾ " if self.show_resolved else "▸ ") + f"Resolved ({len(resolved)})"
            self.btn(canvas, 0, y, label, self.toggle_resolved, "ghost", size=12)
            y += self.S(52)
            if self.show_resolved:
                for flag in reversed(resolved):
                    y = self._draw_resolved_card(canvas, record, flag, y, width) + self.S(10)
        self.finish_scroll(canvas, y + self.S(20))

    def _draw_recap(self, canvas, record, y, width):
        lines = self.service.brain.demo.recap(record)  # instant, built from the saved flags
        top = y
        self.tx(canvas, self.S(18), y + self.S(14), "3-LINE RECAP", 10, TEXT_MUTED, "bold")
        y += self.S(36)
        for line in lines[:3]:
            item = self.tx(canvas, self.S(18), y, line, 13, INK, width=width - self.S(36))
            y = self.bottom_of(canvas, item) + self.S(6)
        box = self.rr(canvas, 0, top, width, y + self.S(10), self.S(12), fill=WHITE, outline=INK, width=self.S(1.5))
        canvas.tag_lower(box)
        return y + self.S(24)

    def _draw_request_card(self, canvas, record, request, y, width):
        top = y
        self.draw_icon_on(canvas, "phone", self.S(30), y + self.S(26), self.S(22), AMBER)
        self.tx(canvas, self.S(54), y + self.S(14), "Patient request", 13, AMBER, "bold")
        self.tx(canvas, width - self.S(16), y + self.S(14), request["time"][:16].replace("T", " "), 11, TEXT_MUTED, anchor="ne")
        item = self.tx(canvas, self.S(54), y + self.S(40), request["reason"], 14, TEXT_DARK, width=width - self.S(80))
        y = self.bottom_of(canvas, item) + self.S(10)
        self.btn(canvas, self.S(54), y, "Mark as done", lambda: self.complete_request(record["id"], request["id"]), "green", size=11)
        y += self.S(50)
        box = self.rr(canvas, 0, top, width, y, self.S(12), fill=AMBER_SOFT, outline=AMBER)
        canvas.tag_lower(box)
        return y

    def _draw_flag_card(self, canvas, record, flag, y, width):
        label, colour, soft = TIER_STYLE.get(flag["tier"], TIER_STYLE[2])
        top, left = y, self.S(22)
        self.draw_icon_on(canvas, "flag" if flag["tier"] == 1 else "alert", left + self.S(10), y + self.S(26), self.S(22), colour)
        x = self.chip(canvas, left + self.S(30), y + self.S(15), label, WHITE, colour, 10)
        x = self.chip(canvas, x + self.S(8), y + self.S(15), f"from {flag['source']}", INK, "#eef1f6", 10)
        x = self.chip(canvas, x + self.S(8), y + self.S(15), flag["topic"], colour, WHITE, 10)
        if flag.get("ai_status") in ("unavailable", "pending"):
            self.chip(canvas, x + self.S(8), y + self.S(15),
                      "AI context unavailable" if flag["ai_status"] == "unavailable" else "AI checking…", TEXT_MUTED, "#eef1f6", 10)
        self.tx(canvas, width - self.S(16), y + self.S(18), flag["time"][:16].replace("T", " "), 11, TEXT_MUTED, anchor="ne")
        y += self.S(50)
        item = self.tx(canvas, left, y, f"“{flag['text']}”", 16, INK, "bold", width=width - left * 2)
        y = self.bottom_of(canvas, item) + self.S(8)
        for occurrence in flag.get("occurrences", []):
            item = self.tx(canvas, left, y, f"Again at {occurrence['time'][11:16]}: “{occurrence['text']}”", 12,
                           TEXT_DARK, width=width - left * 2)
            y = self.bottom_of(canvas, item) + self.S(4)
        if flag.get("ask_next"):
            item = self.tx(canvas, left, y, f"Sarah asked: {flag['ask_next']}", 12, TEXT_MUTED, width=width - left * 2)
            y = self.bottom_of(canvas, item) + self.S(4)
        for detail in flag.get("details", []):
            item = self.tx(canvas, left, y, f"Patient added: “{detail['text']}”", 13, TEXT_DARK, "bold", width=width - left * 2)
            y = self.bottom_of(canvas, item) + self.S(4)
        if flag["matched_words"] or flag.get("readings"):
            words = ", ".join(flag["matched_words"] + [f"{r['kind']} {r['value']}" for r in flag.get("readings", [])])
            item = self.tx(canvas, left, y + self.S(4), f"Matched: {words}", 12, colour, width=width - left * 2)
            y = self.bottom_of(canvas, item) + self.S(4)
        item = self.tx(canvas, left, y + self.S(2), f"AI reason: {flag['ai_reason']}", 13, TEXT_DARK, width=width - left * 2)
        y = self.bottom_of(canvas, item) + self.S(8)
        if flag["id"] in getattr(self, "expanded_flags", set()) and flag.get("context"):
            for line in flag["context"]:
                item = self.tx(canvas, left + self.S(12), y, f"… {line}", 11, TEXT_MUTED, width=width - left * 3)
                y = self.bottom_of(canvas, item) + self.S(3)
        for note in flag["notes"]:
            item = self.tx(canvas, left, y, f"Note by {note['by']} at {note['time'][11:16]}: {note['text']}", 12, INK,
                           width=width - left * 2)
            y = self.bottom_of(canvas, item) + self.S(4)
        y += self.S(6)
        fid, pid = flag["id"], record["id"]
        x = self.btn(canvas, left, y, "✓ Resolve", lambda: self.resolve_flag(pid, fid), "green", size=12)
        x = self.btn(canvas, x + self.S(10), y, "Add note", lambda: self.add_flag_note(pid, fid), "ghost", size=12)
        x = self.btn(canvas, x + self.S(10), y, "Right flag" + (" ✓" if flag["feedback"] == "up" else ""),
                     lambda: self.flag_feedback(pid, fid, "up"), "dark" if flag["feedback"] == "up" else "ghost", size=12)
        x = self.btn(canvas, x + self.S(10), y, "Wrong flag" + (" ✓" if flag["feedback"] == "down" else ""),
                     lambda: self.flag_feedback(pid, fid, "down"), "dark" if flag["feedback"] == "down" else "ghost", size=12)
        if flag.get("context"):
            self.btn(canvas, x + self.S(10), y, "Hide context" if fid in getattr(self, "expanded_flags", set())
                     else "Show context", lambda: self.toggle_flag_context(fid), "ghost", size=12)
        y += self.S(52)
        box = self.rr(canvas, 0, top, width, y, self.S(14), fill=WHITE, outline=BORDER)
        bar = canvas.create_rectangle(0, top + self.S(8), self.S(7), y - self.S(8), fill=colour, outline="")
        canvas.tag_lower(bar)
        canvas.tag_lower(box)
        return y

    def _draw_resolved_card(self, canvas, record, flag, y, width):
        label = TIER_STYLE.get(flag["tier"], TIER_STYLE[2])[0]
        item = self.tx(canvas, self.S(18), y + self.S(12),
                       f"{label} · {flag['topic']} · “{flag['text'][:70]}”  —  resolved by {flag['resolved_by']} "
                       f"at {(flag['resolved_at'] or '')[:16].replace('T', ' ')}", 12, TEXT_MUTED, width=width - self.S(150))
        bottom = self.bottom_of(canvas, item) + self.S(10)
        self.btn(canvas, width - self.S(120), y + self.S(6), "Reopen", lambda: self.reopen_flag(record["id"], flag["id"]),
                 "ghost", size=11, height=self.S(32))
        bottom = max(bottom, y + self.S(46))
        box = self.rr(canvas, 0, y, width, bottom, self.S(10), fill="#f7f8fa", outline=BORDER)
        canvas.tag_lower(box)
        return bottom

    # ---- actions (each one updates the shared record and the audit log) ----------------

    def _update_flag(self, patient_id, flag_id, change, event, **details):
        def apply(record):
            for flag in record["flags"]:
                if flag["id"] == flag_id:
                    change(flag)
        self.store.update(patient_id, apply)
        audit_log.record(event, patient_id, flag_id=flag_id, by=PHARMACIST, **details)

    def resolve_flag(self, patient_id, flag_id):
        self._update_flag(patient_id, flag_id, lambda f: f.update(status="resolved", resolved_by=PHARMACIST,
                                                                  resolved_at=now_iso()), "flag_resolved")
        self.flash("Flag resolved")

    def reopen_flag(self, patient_id, flag_id):
        self._update_flag(patient_id, flag_id, lambda f: f.update(status="open", resolved_by=None, resolved_at=None),
                          "flag_reopened")
        self.flash("Flag reopened")

    def add_flag_note(self, patient_id, flag_id):
        text = simpledialog.askstring("Add a note", "Note or reply for this flag:", parent=self)
        if text and text.strip():
            self._update_flag(patient_id, flag_id, lambda f: f["notes"].append(
                {"by": PHARMACIST, "time": now_iso(), "text": text.strip()}), "flag_note")
            self.flash("Note saved")

    def flag_feedback(self, patient_id, flag_id, value):
        self._update_flag(patient_id, flag_id, lambda f: f.update(feedback=value), "flag_feedback", value=value)
        self.flash("Thanks: feedback saved")

    def toggle_flag_context(self, flag_id):
        expanded = getattr(self, "expanded_flags", set())
        expanded ^= {flag_id}
        self.expanded_flags = expanded
        self.render()

    def toggle_resolved(self):
        self.show_resolved = not self.show_resolved
        self.render()

    def complete_request(self, patient_id, request_id):
        def apply(record):
            for request in record["pharmacist_requests"]:
                if request["id"] == request_id:
                    request.update(status="done", done_by=PHARMACIST, done_at=now_iso())
        self.store.update(patient_id, apply)
        audit_log.record("request_done", patient_id, request_id=request_id, by=PHARMACIST)
        self.flash("Request marked as done")
