"""The chat page with Sarah: message list, input box and send button.

Called by: ui/patient/check_up.py (checkup_choice('Chat')).
"""

import tkinter as tk
from tkinter import font as tkfont

from ..theme import (
    BORDER,
    INK,
    RED,
    TEXT_DARK,
    TEXT_MUTED,
    WHITE,
)
from ...storage.chat_history import format_chat_time, local_date_label, local_timestamp


class ChatMixin:
    def draw_chat_page(self, x1, y1, x2, y2):
        c = self.c
        c.create_rectangle(x1 + self.S(1), y1 + self.S(1), x2 - self.S(1), y2 - self.S(1),
                           fill="#f3f3f5", outline="")
        header_y = y1 + self.S(54)
        c.create_rectangle(x1 + self.S(12), header_y - self.S(20), x1 + self.S(48),
                           header_y + self.S(20), fill="#f3f3f5", outline="#f3f3f5", tags="chat_back")
        self.draw_icon("back", x1 + self.S(30), header_y, self.S(24), INK, "chat_back")
        self.text(x1 + self.S(62), header_y, "Chat with Juliez", 20, INK, "bold")
        self.clickable("chat_back", self.close_chat)

        date_y = y1 + self.S(112)
        self.rrect((x1 + x2) / 2 - self.S(70), date_y - self.S(18),
                   (x1 + x2) / 2 + self.S(70), date_y + self.S(18), self.S(18),
                   fill=WHITE, outline=BORDER)
        self.text((x1 + x2) / 2, date_y, local_date_label(), 10,
                  TEXT_MUTED, "bold", anchor="center")

        input_h = self.S(58)
        input_y = y2 - self.S(30) - input_h
        messages_top = date_y + self.S(32)
        viewport_h = max(self.S(60), input_y - messages_top - self.S(10))
        viewport_w = x2 - x1 - self.S(16)
        messages = self.chat_messages or [
            ("Juliez", "Hi! How can I help you today?", local_timestamp())
        ]

        self.chat_view_frame = tk.Frame(self, bg="#f3f3f5", bd=0, highlightthickness=0)
        message_canvas = tk.Canvas(self.chat_view_frame, bg="#f3f3f5",
                                   bd=0, highlightthickness=0)
        self.chat_message_canvas = message_canvas
        content = tk.Frame(message_canvas, bg="#f3f3f5", bd=0)
        content_window = message_canvas.create_window(0, 0, window=content, anchor="nw")
        auto_scroll = True

        def scroll_canvas(*args):
            nonlocal auto_scroll
            auto_scroll = False
            message_canvas.yview(*args)

        scrollbar = tk.Scrollbar(self.chat_view_frame, orient="vertical", command=scroll_canvas)
        self.chat_scrollbar = scrollbar

        def sync_scrollbar(first, last):
            scrollbar.set(first, last)
            if float(first) <= 0 and float(last) >= 1:
                scrollbar.pack_forget()
            elif not scrollbar.winfo_manager():
                scrollbar.pack(side="right", fill="y")

        message_canvas.configure(yscrollcommand=sync_scrollbar)
        message_canvas.pack(side="left", fill="both", expand=True)
        message_canvas.bind(
            "<Configure>",
            lambda event: message_canvas.itemconfigure(content_window, width=event.width),
        )
        def update_message_region(_event=None):
            bounds = message_canvas.bbox("all")
            if bounds:
                message_canvas.configure(scrollregion=bounds)
                if auto_scroll:
                    message_canvas.yview_moveto(1.0)

        content.bind("<Configure>", update_message_region)

        def scroll_by(units):
            nonlocal auto_scroll
            auto_scroll = False
            message_canvas.yview_scroll(units, "units")
            return "break"

        def scroll_messages(event):
            units = int(-event.delta / 120) or (-1 if event.delta > 0 else 1)
            return scroll_by(units)

        def bind_scroll(widget):
            widget.bind("<MouseWheel>", scroll_messages)
            widget.bind("<Button-4>", lambda _event: scroll_by(-1))
            widget.bind("<Button-5>", lambda _event: scroll_by(1))

        bind_scroll(self.chat_view_frame)
        bind_scroll(message_canvas)
        bind_scroll(content)

        bubble_width = int(viewport_w * 0.72)
        available_text_width = max(1, bubble_width - self.S(36))
        message_font = tkfont.Font(self, font=self.font(14))

        def display_line_count(message):
            count = 0
            for paragraph in message.splitlines() or [""]:
                line = ""
                for word in paragraph.split():
                    candidate = f"{line} {word}".strip()
                    if line and message_font.measure(candidate) > available_text_width:
                        count += 1
                        line = ""
                    while message_font.measure(word) > available_text_width:
                        split = len(word)
                        while split > 1 and message_font.measure(word[:split]) > available_text_width:
                            split -= 1
                        count += 1
                        word = word[split:]
                    line = f"{line} {word}".strip()
                count += 1 if line or not paragraph else 0
            return max(1, count)

        for sender, message, timestamp in messages:
            line_count = display_line_count(message)
            bubble_height = int(self.S(58 + line_count * 20))
            alert_message = sender == "You" and self.medical_robot.has_alert_keyword(message)
            bubble_bg = "#fde8e8" if alert_message else "#e7e8ee" if sender == "You" else WHITE
            row = tk.Frame(content, bg="#f3f3f5")
            row.pack(fill="x", pady=(0, self.S(14)))
            bind_scroll(row)
            bubble = tk.Frame(row, bg=bubble_bg, width=bubble_width, height=bubble_height,
                              highlightthickness=0)
            bubble.pack(side="right" if sender == "You" else "left",
                        padx=self.S(12), anchor="e" if sender == "You" else "w")
            bubble.pack_propagate(False)
            bind_scroll(bubble)

            header = tk.Frame(bubble, bg=bubble_bg)
            header.pack(fill="x", padx=self.S(14), pady=(self.S(9), self.S(5)))
            bind_scroll(header)
            sender_label = tk.Label(header, text=sender, bg=bubble_bg, fg=RED if alert_message else INK,
                                    font=self.font(14, "bold"))
            sender_label.pack(side="left")
            bind_scroll(sender_label)
            if sender != "You":
                copy_button = tk.Button(
                    header, text="Copy", command=lambda body=message: self.copy_chat_message(body),
                    bg=bubble_bg, fg=TEXT_MUTED, activebackground=bubble_bg,
                    relief="flat", bd=0, padx=self.S(5), cursor="hand2",
                    font=self.font(10))
                copy_button.pack(side="right")
                bind_scroll(copy_button)
            time_label = tk.Label(header, text=format_chat_time(timestamp),
                                  bg=bubble_bg, fg=TEXT_MUTED,
                                  font=self.font(12))
            time_label.pack(side="right", padx=(0, self.S(8)))
            bind_scroll(time_label)

            body = tk.Text(
                bubble, height=line_count, wrap="word", bd=0, highlightthickness=0,
                padx=0, pady=0, bg=bubble_bg, fg=RED if alert_message else TEXT_DARK,
                font=self.font(14),
                selectbackground="#c7d2fe", cursor="xterm",
            )
            body.insert("1.0", message)
            body.configure(state="disabled")
            body.pack(fill="both", expand=True, padx=self.S(14), pady=(0, self.S(12)))
            body.bind("<Control-c>", lambda event, text=message: self.copy_chat_selection(event, text))
            body.bind("<Control-C>", lambda event, text=message: self.copy_chat_selection(event, text))
            bind_scroll(body)

        self.c.create_window(x1 + self.S(8), messages_top, window=self.chat_view_frame,
                             width=viewport_w, height=viewport_h, anchor="nw")
        self.after_idle(lambda: message_canvas.yview_moveto(1.0)
                        if message_canvas.winfo_exists() and auto_scroll else None)

        self.rrect(x1 + self.S(28), input_y, x2 - self.S(28), input_y + input_h,
                   self.S(16), fill=WHITE, outline=BORDER, width=self.S(1.2))
        entry = tk.Entry(self, relief="flat", bd=0, font=self.font(14), fg=TEXT_DARK,
                         insertbackground=INK)
        entry.insert(0, self.chat_draft or self.chat_placeholder)
        if not self.chat_draft:
            entry.configure(fg=TEXT_MUTED)
        entry.bind("<FocusIn>", self.chat_focus_in)
        entry.bind("<FocusOut>", self.chat_focus_out)
        entry.bind("<Return>", self.send_chat_message)
        self.chat_entry = entry
        c.create_window(x1 + self.S(52), input_y + input_h / 2,
                        width=max(20, x2 - x1 - self.S(160)), height=self.S(34),
                        window=entry, anchor="w")
        send_x = x2 - self.S(58)
        c.create_oval(send_x - self.S(21), input_y + input_h / 2 - self.S(21),
                      send_x + self.S(21), input_y + input_h / 2 + self.S(21),
                      fill=RED, outline="", tags="chat_send")
        self.draw_icon("send", send_x, input_y + input_h / 2, self.S(20), WHITE,
                       "chat_send", bg=RED)
        self.clickable("chat_send", self.send_chat_message)
