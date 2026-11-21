"""What happens when the patient opens the chat, types, taps a quick reply, or sends.

Called by: ui/patient/chat.py buttons and key bindings.
The message is handed to core/conversation_service.py in a BACKGROUND thread, so the
window never freezes; "Sarah is typing…" shows until the reply is saved.
"""

import tkinter as tk

from ...voice.tts import speak
from ..theme import TEXT_DARK, TEXT_MUTED


class ChatActionsMixin:
    @property
    def chat_placeholder(self):
        return self.t("chat.placeholder")

    def open_profile_chat(self):
        if self.role != "patient":
            raise RuntimeError("Only the patient side has the chat.")
        self._cancel_checkup_animation()
        self.call_open = False
        self.chat_open = True
        self.dropdown = None
        record = self.store.load(self.patient_id)
        if not record["conversation"].get("session_id") or record["sessions"] and record["sessions"][-1]["kind"] != "CHAT":
            self.service.start_session(self.patient_id, "CHAT")
        self.chat_focus_requested = True
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

    def send_chat_message(self, _event=None, text=None):
        if self.role != "patient":
            raise RuntimeError("Only the patient can send chat messages.")
        message = text if text is not None else (self.chat_entry.get().strip() if self.chat_entry else "")
        if not message or message == self.chat_placeholder or self.patient_id in self.service.busy:
            return
        if self.chat_entry:
            self.chat_entry.delete(0, tk.END)
        self.chat_draft = ""
        self.chat_focus_requested = True
        self.service.busy.add(self.patient_id)  # show "typing" straight away
        patient_id = self.patient_id
        self.run_in_background(lambda: self.service.handle_message(patient_id, message, "chat"),
                               "Sarah couldn't reply just now. Your message is saved; please try again.")
        self.render()

    def send_quick_reply(self, text):
        self.send_chat_message(text=text)

    def go_back_one_question(self):
        self.service.back_one_question(self.patient_id)
        self.render()

    def read_aloud(self, text):
        self.flash(self.t("chat.read_aloud") + "…")
        speak(text, self.lang, on_error=lambda message: self._background_errors.append(message))

    def voice_typing(self):
        self.flash(self.t("chat.voice_soon"))

    def copy_chat_message(self, message):
        self.clipboard_clear()
        self.clipboard_append(message)
        self.flash("Copied" if self.lang == "en" else "Copié")

    def copy_chat_selection(self, event, fallback):
        try:
            selected = event.widget.get("sel.first", "sel.last")
        except tk.TclError:
            selected = fallback
        self.copy_chat_message(selected)
        return "break"
