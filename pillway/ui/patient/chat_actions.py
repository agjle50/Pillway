"""What happens when the patient opens the chat, types and sends.

Called by: ui/patient/chat.py buttons and key bindings.
"""

import tkinter as tk

from ..theme import (
    TEXT_DARK,
    TEXT_MUTED,
)
from ...storage.chat_history import local_timestamp


class ChatActionsMixin:
    def open_profile_chat(self):
        if self.profiles[self.active_profile_id]["role"] != "Patient":
            raise RuntimeError("The Doctor profile has no chatbot.")
        self._cancel_checkup_animation()
        self.call_open = False
        if not self.chat_messages:
            self.chat_messages.append(("Juliez", self.medical_robot.greeting(), local_timestamp()))
            self.chat_history.save(self.chat_logs)
        self.chat_open = True
        self.dropdown = None
        self.render()
    def close_chat(self):
        self.chat_open = False
        self.call_open = False
        self.chat_draft = ""
        self.render()
    def chat_focus_in(self, _event=None):
        if self.chat_entry and self.chat_entry.get() == self.chat_placeholder:
            self.chat_entry.delete(0, tk.END)
            self.chat_entry.configure(fg=TEXT_DARK)
    def chat_focus_out(self, _event=None):
        if self.chat_entry and not self.chat_entry.get():
            self.chat_entry.insert(0, self.chat_placeholder)
            self.chat_entry.configure(fg=TEXT_MUTED)
    def send_chat_message(self, _event=None):
        if self.profiles[self.active_profile_id]["role"] != "Patient":
            raise RuntimeError("The Doctor profile cannot send chatbot messages.")
        message = self.chat_entry.get().strip() if self.chat_entry else ""
        if not message or message == self.chat_placeholder:
            return
        self.chat_messages.append(("You", message, local_timestamp()))
        self.chat_messages.append(("Juliez", self.medical_robot.reply(message), local_timestamp()))
        self.chat_history.save(self.chat_logs)
        if self.chat_entry:
            self.chat_entry.delete(0, tk.END)
        self.chat_draft = ""
        self.chat_focus_requested = True
        self.render()
    def copy_chat_message(self, message):
        self.clipboard_clear()
        self.clipboard_append(message)
    def copy_chat_selection(self, event, fallback):
        try:
            selected = event.widget.get("sel.first", "sel.last")
        except tk.TclError:
            selected = fallback
        self.copy_chat_message(selected)
        return "break"
