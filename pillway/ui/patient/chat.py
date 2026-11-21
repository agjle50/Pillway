"""The chat page with Sarah: message bubbles, red/amber flags, quick replies, read-aloud, input box.

Called by: ui/patient/dashboard.py when the chat is open (Check up -> Chat).
Concerning messages turn red (urgent) or amber (watch) WITH an icon and words, never colour alone.
Every Sarah message has "Read aloud" and "Copy". "Sarah is typing…" shows while she replies.
"""

import tkinter as tk

from config import get_settings

from ...storage.chat_history import format_chat_time, local_date_label
from ..theme import AMBER, AMBER_SOFT, BORDER, CHAT_BG, INK, RED, RED_SOFT, TEXT_DARK, TEXT_MUTED, WHITE

BUBBLE_STYLES = {1: (RED_SOFT, RED, "flag", "chat.shared_urgent"), 2: (AMBER_SOFT, AMBER, "alert", "chat.shared_watch")}


class ChatMixin:
    def draw_chat_page(self, x1, y1, x2, y2):
        record = self.record
        self.c.create_rectangle(x1 + 1, y1 + 1, x2 - 1, y2 - 1, fill=CHAT_BG, outline="")
        header_y = y1 + self.S(42)
        self.c.create_rectangle(x1 + self.S(10), header_y - self.S(22), x1 + self.S(52), header_y + self.S(22),
                                fill=CHAT_BG, outline=CHAT_BG, tags="chat_back")
        self.draw_icon("back", x1 + self.S(30), header_y, self.S(24), INK, "chat_back")
        self.clickable("chat_back", self.close_chat)
        self.text(x1 + self.S(62), header_y, self.t("chat.title"), 20, INK, "bold")
        if not record["consent"]["accepted"]:
            self.draw_consent(x1, header_y + self.S(40), x2, y2)
            return
        self._draw_progress(record, x2, header_y)
        date_y = header_y + self.S(46)
        self.text((x1 + x2) / 2, date_y, local_date_label(), 10, TEXT_MUTED, "bold", anchor="center")

        input_h = self.S(58)
        input_y = y2 - self.S(22) - input_h
        quick = self._quick_replies(record)
        quick_h = self.S(56) if quick else 0
        area = self.make_scroll(x1 + self.S(8), date_y + self.S(16), x2 - self.S(8), input_y - quick_h - self.S(8), CHAT_BG)
        self.chat_message_canvas = area
        height = self._draw_messages(area, record, x2 - x1 - self.S(16))
        self.finish_scroll(area, height, keep_bottom=True)
        if quick:
            self._draw_quick_replies(quick, x1 + self.S(28), x2 - self.S(28), input_y - quick_h)
        self._draw_input(x1, x2, input_y, input_h)

    # ---- pieces -----------------------------------------------------------------------

    def _draw_progress(self, record, x2, y):
        last = next((m for m in reversed(record["messages"]) if m["role"] == "sarah"), None)
        progress = (last or {}).get("progress", "")
        right = x2 - self.S(24)
        if progress:
            item = self.text(right, y, progress, 13, TEXT_MUTED, "bold", anchor="e")
            right = self.c.bbox(item)[0] - self.S(18)
        convo = record["conversation"]
        if convo["stage"] in ("questions", "wrap_up") and (convo["question_index"] > 0 or convo["stage"] == "wrap_up"):
            item = self.text(right, y, "‹ " + self.t("chat.back"), 13, RED, "bold", anchor="e", tag="chat_go_back")
            self.clickable("chat_go_back", self.go_back_one_question)

    def _draw_messages(self, canvas, record, width):
        size = 15 * get_settings().patient.text_size
        bubble_w = width * 0.72
        y = self.S(12)
        messages = record["messages"]
        if not messages:
            self.tx(canvas, width / 2, self.S(40), self.t("chat.empty"), 16, TEXT_MUTED, anchor="n")
        for message in messages:
            y = self._draw_bubble(canvas, message, y, width, bubble_w, size) + self.S(14)
        if self.patient_id in self.service.busy:
            self.rr(canvas, self.S(12), y, self.S(200), y + self.S(46), self.S(18), fill=WHITE, outline=BORDER)
            self.tx(canvas, self.S(30), y + self.S(23), self.t("chat.typing"), 13, TEXT_MUTED, "bold", anchor="w")
            y += self.S(60)
        return y + self.S(10)

    def _draw_bubble(self, canvas, message, y, width, bubble_w, size):
        mine = message["role"] == "patient"
        tier = message.get("tier") if mine else None
        fill, edge, icon, label_key = BUBBLE_STYLES.get(tier, ("#e7e8ee" if mine else WHITE, BORDER, None, None))
        pad = self.S(16)
        x1 = width - bubble_w - self.S(12) if mine else self.S(12)
        sender = ("You" if self.lang == "en" else "Vous") if mine else get_settings().branding.assistant_name
        head = self.tx(canvas, x1 + pad, y + pad, sender, 13, RED if tier == 1 else INK, "bold")
        self.tx(canvas, x1 + bubble_w - pad, y + pad, format_chat_time(message["time"]), 11, TEXT_MUTED, anchor="ne")
        body = self.tx(canvas, x1 + pad, self.bottom_of(canvas, head) + self.S(6), message["text"], size,
                       TEXT_DARK, width=bubble_w - 2 * pad)
        bottom = self.bottom_of(canvas, body) + self.S(10)
        if label_key:
            self.draw_icon_on(canvas, icon, x1 + pad + self.S(9), bottom + self.S(10), self.S(18), edge)
            self.tx(canvas, x1 + pad + self.S(24), bottom + self.S(10), self.t(label_key), 12, edge, "bold", anchor="w")
            bottom += self.S(28)
        if not mine:
            right = self.btn(canvas, x1 + pad, bottom, self.t("chat.read_aloud"),
                             lambda text=message["text"]: self.read_aloud(text), "ghost", size=11, height=self.S(32))
            self.btn(canvas, right + self.S(8), bottom, self.t("chat.copy"),
                     lambda text=message["text"]: self.copy_chat_message(text), "ghost", size=11, height=self.S(32))
            bottom += self.S(40)
            if message.get("source") == "offline":
                self.tx(canvas, x1 + pad, bottom, self.t("chat.offline"), 10, TEXT_MUTED)
                bottom += self.S(18)
        rect = self.rr(canvas, x1, y, x1 + bubble_w, bottom + self.S(6), self.S(18), fill=fill, outline=edge,
                       width=max(1, self.S(2 if tier else 1)))
        canvas.tag_lower(rect)
        return bottom + self.S(6)

    def draw_icon_on(self, canvas, kind, cx, cy, size, color):
        """Draw one of our vector icons on another canvas (temporarily swap the target)."""
        main = self.c
        self.c = canvas
        try:
            self.draw_icon(kind, cx, cy, size, color, None)
        finally:
            self.c = main

    def _quick_replies(self, record):
        if not get_settings().patient.quick_replies or self.patient_id in self.service.busy:
            return []
        last = record["messages"][-1] if record["messages"] else None
        return (last or {}).get("quick", []) if last and last["role"] == "sarah" else []

    def _draw_quick_replies(self, options, x1, x2, y):
        x = x1
        for index, option in enumerate(options):
            tag = f"quick::{index}"
            probe = self.c.create_text(0, -500, text=option, font=self.font(14, "bold"))
            text_w = self.c.bbox(probe)[2] - self.c.bbox(probe)[0]
            self.c.delete(probe)
            width = text_w + self.S(36)
            if x + width > x2:
                break
            self.rrect(x, y + self.S(4), x + width, y + self.S(48), self.S(22), fill=WHITE, outline=RED,
                       width=self.S(1.5), tags=tag)
            self.text(x + width / 2, y + self.S(26), option, 14, RED, "bold", anchor="center", tag=tag)
            self.clickable(tag, lambda text=option: self.send_quick_reply(text))
            x += width + self.S(10)

    def _draw_input(self, x1, x2, input_y, input_h):
        self.rrect(x1 + self.S(28), input_y, x2 - self.S(28), input_y + input_h, self.S(16), fill=WHITE,
                   outline=BORDER, width=self.S(1.2))
        entry = tk.Entry(self, relief="flat", bd=0, font=self.font(15), fg=TEXT_DARK, insertbackground=INK,
                         highlightthickness=0)
        entry.insert(0, self.chat_draft or self.chat_placeholder)
        if not self.chat_draft:
            entry.configure(fg=TEXT_MUTED)
        entry.bind("<FocusIn>", self.chat_focus_in)
        entry.bind("<FocusOut>", self.chat_focus_out)
        entry.bind("<Return>", self.send_chat_message)
        self.chat_entry = entry
        self.c.create_window(x1 + self.S(52), input_y + input_h / 2, width=max(20, x2 - x1 - self.S(220)),
                             height=self.S(34), window=entry, anchor="w")
        mid = input_y + input_h / 2
        mic_x, send_x = x2 - self.S(110), x2 - self.S(58)
        if get_settings().patient.voice_input:
            self.c.create_oval(mic_x - self.S(21), mid - self.S(21), mic_x + self.S(21), mid + self.S(21),
                               fill="#eef1f6", outline="", tags="chat_mic")
            self.draw_icon("mic", mic_x, mid, self.S(20), INK, "chat_mic", bg="#eef1f6")
            self.clickable("chat_mic", self.voice_typing)
        busy = self.patient_id in self.service.busy
        self.c.create_oval(send_x - self.S(21), mid - self.S(21), send_x + self.S(21), mid + self.S(21),
                           fill=TEXT_MUTED if busy else RED, outline="", tags="chat_send")
        self.draw_icon("send", send_x, mid, self.S(20), WHITE, "chat_send", bg=TEXT_MUTED if busy else RED)
        self.clickable("chat_send", self.send_chat_message)
        status = self.t("chat.typing") if busy else self.t("chat.saved") if self.record["messages"] else ""
        self.text(x1 + self.S(40), input_y + input_h + self.S(11), status, 10, TEXT_MUTED)
