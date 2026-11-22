"""Log: every chat and call, newest first, each labelled CHAT or CALL with date, time (and duration).

Called by: ui/pharmacist/patient_detail.py ("Log" section).
Flagged messages show in red (urgent) or amber (watch) with a word label. It updates live
while the patient is chatting (live sync redraws within about a second).
"""

from ...storage.chat_history import format_chat_time
from ..theme import AMBER, BORDER, INK, RED, RED_TEXT, TEXT_DARK, TEXT_MUTED, WHITE


def group_by_session(record):
    """Return [(session, [messages])] newest session first. Messages without a session go in 'Earlier'."""
    sessions = {s["id"]: s for s in record.get("sessions", [])}
    groups, order = {}, []
    for message in record["messages"]:
        key = message.get("session_id") or "none"
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(message)
    result = []
    for key in reversed(order):
        session = sessions.get(key) or {"kind": "CHAT", "start": groups[key][0]["time"], "duration_s": None}
        result.append((session, groups[key]))
    return result


class LogMixin:
    def draw_log_section(self, record, x1, y1, x2, y2):
        canvas = self.make_scroll(x1, y1, x2, y2, "#edf1f4")
        width = x2 - x1 - self.S(30)
        consent = "Patient consented to pharmacist viewing" if record["consent"].get("accepted") else "No consent recorded"
        y = self.section_title(canvas, 0, self.S(4), "Log", f"Chats and calls, newest first. {consent}. Updates live.")
        groups = group_by_session(record)
        if not groups:
            self.tx(canvas, 0, y, "No chats or calls yet.", 14, TEXT_MUTED)
        for session, messages in groups:
            top = y
            kind = session.get("kind", "CHAT")
            self.chip(canvas, self.S(18), y + self.S(14), kind, "#ffffff", RED if kind == "CALL" else INK, 12)
            when = session["start"][:16].replace("T", " ")
            duration = session.get("duration_s")
            extra = f"  ·  duration {duration // 60}:{duration % 60:02d}" if duration else (
                "  ·  in progress" if kind == "CALL" and not session.get("end") else "")
            self.tx(canvas, self.S(100), y + self.S(25), f"{when}{extra}", 13, TEXT_MUTED, "bold", anchor="w")
            y += self.S(52)
            for message in messages:
                mine = message["role"] == "patient"
                tier = message.get("tier") if mine else None
                colour = RED_TEXT if tier == 1 else AMBER if tier == 2 else (INK if mine else TEXT_DARK)
                who = "Patient" if mine else "Sarah"
                tag = {1: "  [URGENT FLAG]", 2: "  [WATCH FLAG]"}.get(tier, "")
                head = self.tx(canvas, self.S(18), y, f"{who} · {format_chat_time(message['time'])}{tag}", 11, colour, "bold")
                body = self.tx(canvas, self.S(18), self.bottom_of(canvas, head) + self.S(2), message["text"], 13,
                               colour, "bold" if tier else "normal", width=width - self.S(36))
                y = self.bottom_of(canvas, body) + self.S(10)
            box = self.rr(canvas, 0, top, width, y + self.S(6), self.S(12), fill=WHITE, outline=BORDER)
            canvas.tag_lower(box)
            y += self.S(20)
        self.finish_scroll(canvas, y + self.S(20))
