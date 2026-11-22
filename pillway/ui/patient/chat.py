"""The chat page with Sarah: message bubbles, red/amber flags, quick replies, read-aloud, input box.

Called by: ui/patient/dashboard.py when the chat is open (Check up -> Chat).
Concerning messages turn red (urgent) or amber (watch) WITH an icon and words, never colour alone.
Every Sarah message has "Read aloud" and "Copy". "Sarah is typing…" shows while she replies.
"""

import tkinter as tk

from config import get_settings

from ...storage.chat_history import format_chat_time, local_date_label
from ..theme import (AMBER, AMBER_SOFT, BORDER, CHAT_BG, INK, NAV_ICON, NAVY, RED, RED_SOFT, RED_TEXT, TEXT_DARK,
                     SURFACE_HIGH, TEXT_MUTED, TEXT_SUBTLE, WHITE)

# Flag labels under a patient's message: (label background, label colour, icon, words). Never colour alone.
FLAG_LABELS = {1: (RED_SOFT, RED_TEXT, "flag", "chat.shared_urgent"), 2: (AMBER_SOFT, AMBER, "alert", "chat.shared_watch")}
SOFT_BUTTON = "#e9ecf5"     # mic button and similar quiet controls


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
        self._chat_toast_x, self._chat_toast_y = (x1 + x2) / 2, header_y + self.S(23)  # where toasts show
        self.text((x1 + x2) / 2, date_y, local_date_label(), 10, TEXT_MUTED, "bold", anchor="center")

        input_h = self.S(64)
        input_y = y2 - self.S(22) - input_h
        quick = self._quick_replies(record)
        quick_layout = self._layout_quick_replies(quick, x1 + self.S(28), x2 - self.S(28))
        quick_h = (quick_layout[-1][2] + self.S(60)) if quick_layout else 0
        area = self.make_scroll(x1 + self.S(8), date_y + self.S(16), x2 - self.S(8), input_y - quick_h - self.S(8), CHAT_BG)
        self.chat_message_canvas = area
        height = self._draw_messages(area, record, x2 - x1 - self.S(16))
        self.finish_scroll(area, height, keep_bottom=True)
        if quick_layout:
            self._draw_quick_replies(quick_layout, input_y - quick_h)
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
            item = self.text(right, y, "‹ " + self.t("chat.back"), 14, RED_TEXT, "bold", anchor="e", tag="chat_go_back")
            self.clickable("chat_go_back", self.go_back_one_question)

    def _draw_messages(self, canvas, record, width):
        size = 17 * get_settings().patient.text_size
        bubble_w = min(width * 0.74, self.S(680))  # keeps lines short enough to read comfortably
        y = self.S(16)
        messages = record["messages"]
        if not messages:
            self.tx(canvas, width / 2, self.S(48), self.t("chat.empty"), 17, TEXT_MUTED, anchor="n")
        previous = None
        for message in messages:
            same_sender = previous is not None and previous["role"] == message["role"]
            y = self._draw_bubble(canvas, message, y, width, bubble_w, size, show_avatar=not same_sender)
            y += self.S(10 if same_sender else 20)
            previous = message
        if self.patient_id in self.service.busy:
            self._draw_avatar(canvas, self.S(30), y + self.S(24))
            self.rr(canvas, self.S(58), y, self.S(58) + self.S(250), y + self.S(48), self.S(24),
                    fill=SURFACE_HIGH, outline=SURFACE_HIGH)
            self.tx(canvas, self.S(80), y + self.S(24), self.t("chat.typing"), 15, TEXT_MUTED, anchor="w")
            y += self.S(64)
        return y + self.S(10)

    def _draw_avatar(self, canvas, cx, cy):
        r = self.S(18)
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=RED, outline="")
        name = get_settings().branding.assistant_name
        self.tx(canvas, cx, cy, name[:1].upper(), 15, WHITE, "bold", anchor="center")

    def _draw_bubble(self, canvas, message, y, width, bubble_w, size, show_avatar=True):
        """Patient messages: solid navy on the right. Sarah's: white cards on the left with her initial."""
        mine = message["role"] == "patient"
        pad = self.S(18)
        text = message["text"].strip()
        # Fit the bubble to its words (short replies get short bubbles), within the max width.
        probe = canvas.create_text(0, -2000, text=text, font=self.font(size), width=bubble_w - 2 * pad, anchor="nw")
        box = canvas.bbox(probe)
        canvas.delete(probe)
        natural = (box[2] - box[0]) + 2 * pad if box else bubble_w
        flagged = mine and message.get("tier") in FLAG_LABELS
        smallest = self.S(380) if flagged else self.S(150) if mine else self.S(300)  # room for the flag label/buttons
        bubble_w = min(bubble_w, max(natural, smallest))
        if mine:
            x1 = width - bubble_w - self.S(12)
            fill, ink, meta, outline = NAVY, WHITE, NAV_ICON, NAVY
        else:
            x1 = self.S(58)
            fill, ink, meta, outline = SURFACE_HIGH, TEXT_DARK, TEXT_SUBTLE, SURFACE_HIGH
            if show_avatar:
                self._draw_avatar(canvas, self.S(30), y + self.S(22))
        inner_w = bubble_w - 2 * pad
        top = y + pad
        if not mine and show_avatar:
            self.tx(canvas, x1 + pad, top, get_settings().branding.assistant_name, 14, INK, "bold")
        self.tx(canvas, x1 + bubble_w - pad, top, format_chat_time(message["time"]), 12, meta, anchor="ne")
        if not mine and show_avatar:
            top += self.S(26)
        else:
            top += self.S(22)
        body = self.tx(canvas, x1 + pad, top, text, size, ink, width=inner_w)
        bottom = self.bottom_of(canvas, body) + self.S(14)
        tier = message.get("tier") if mine else None
        if tier in FLAG_LABELS:
            soft, strong, icon, key = FLAG_LABELS[tier]
            label = self.tx(canvas, x1 + pad + self.S(34), bottom + self.S(17), self.t(key), 14, strong, "bold",
                            anchor="w")
            lx2 = canvas.bbox(label)[2] + self.S(14)
            pill = self.rr(canvas, x1 + pad, bottom, lx2, bottom + self.S(34), self.S(17), fill=soft, outline="")
            canvas.tag_lower(pill)
            self.draw_icon_on(canvas, icon, x1 + pad + self.S(18), bottom + self.S(17), self.S(18), strong)
            bottom += self.S(46)
        if not mine:
            right = self.btn(canvas, x1 + pad, bottom, self.t("chat.read_aloud"),
                             lambda text=text: self.read_aloud(text), "white", size=14, height=self.S(40))
            self.btn(canvas, right + self.S(10), bottom, self.t("chat.copy"),
                     lambda text=text: self.copy_chat_message(text), "white", size=14, height=self.S(40))
            bottom += self.S(52)
            if message.get("source") == "offline":
                item = self.tx(canvas, x1 + pad, bottom, self.t("chat.offline"), 13, TEXT_MUTED, width=inner_w)
                bottom = self.bottom_of(canvas, item) + self.S(10)
        rect = self.rr(canvas, x1, y, x1 + bubble_w, bottom + self.S(4), self.S(24), fill=fill, outline=outline,
                       width=max(1, self.S(1)))
        canvas.tag_lower(rect)
        return bottom + self.S(4)

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

    def _layout_quick_replies(self, options, x1, x2):
        """Place the reply chips in rows (wrapping instead of dropping the ones that don't fit)."""
        placed, x, row, gap = [], x1, 0, self.S(10)
        for index, option in enumerate(options):
            probe = self.c.create_text(0, -500, text=option, font=self.font(15, "bold"))
            width = self.c.bbox(probe)[2] - self.c.bbox(probe)[0] + self.S(40)
            self.c.delete(probe)
            if x + width > x2 and x > x1:
                x, row = x1, row + 1
            placed.append((index, option, row * self.S(58), x, min(width, x2 - x1)))
            x += width + gap
        return placed

    def _draw_quick_replies(self, layout, y):
        for index, option, dy, x, width in layout:
            tag = f"quick::{index}"
            top = y + dy + self.S(4)
            self.rrect(x, top, x + width, top + self.S(48), self.S(8), fill=WHITE, outline=NAVY,
                       width=self.S(1.6), tags=tag)
            self.text(x + width / 2, top + self.S(24), option, 15, NAVY, "bold", anchor="center", tag=tag)
            self.clickable(tag, lambda text=option: self.send_quick_reply(text))

    def _draw_input(self, x1, x2, input_y, input_h):
        left, right = x1 + self.S(28), x2 - self.S(28)
        # Google-style search-bar message box: tinted pill, navy outline while typing
        self.rrect(left, input_y, right, input_y + input_h, self.S(8), fill=SURFACE_HIGH, outline=BORDER,
                   width=self.S(2), tags="chat_input_box")
        entry = tk.Entry(self, relief="flat", bd=0, font=self.font(17), fg=TEXT_DARK, insertbackground=INK,
                         highlightthickness=0, bg=SURFACE_HIGH)
        entry.insert(0, self.chat_draft or self.chat_placeholder)
        if not self.chat_draft:
            entry.configure(fg=TEXT_MUTED)
        entry.bind("<FocusIn>", lambda e: (self.recolor("chat_input_box", outline=NAVY),
                                           self.chat_focus_in(e)))
        entry.bind("<FocusOut>", lambda e: (self.recolor("chat_input_box", outline=BORDER),
                                            self.chat_focus_out(e)))
        entry.bind("<Return>", self.send_chat_message)
        self.chat_entry = entry
        self.c.create_window(left + self.S(28), input_y + input_h / 2, width=max(20, right - left - self.S(160)),
                             height=self.S(36), window=entry, anchor="w")
        mid = input_y + input_h / 2
        r = self.S(23)
        mic_x, send_x = right - self.S(88), right - self.S(34)
        if get_settings().patient.voice_input:
            voice_active = getattr(self, "voice_typing_active", False)
            mic_bg = RED if voice_active else WHITE
            self.c.create_oval(mic_x - r, mid - r, mic_x + r, mid + r, fill=mic_bg, outline="", tags="chat_mic")
            self.draw_icon("mic", mic_x, mid, self.S(20), WHITE if voice_active else NAVY, "chat_mic", bg=mic_bg)
            self.clickable("chat_mic", self.voice_typing)
        busy = self.patient_id in self.service.busy
        send_bg = TEXT_SUBTLE if busy else RED
        self.c.create_oval(send_x - r, mid - r, send_x + r, mid + r, fill=send_bg, outline="", tags="chat_send")
        self.draw_icon("send", send_x, mid, self.S(20), WHITE, "chat_send", bg=send_bg)
        self.clickable("chat_send", self.send_chat_message)
        status = (
            getattr(self, "voice_typing_status", "")
            or (self.t("chat.typing") if busy else self.t("chat.saved") if self.record["messages"] else "")
        )
        self.text(left + self.S(24), input_y + input_h + self.S(13), status, 13, TEXT_MUTED,
                  tag="chat_voice_status")
