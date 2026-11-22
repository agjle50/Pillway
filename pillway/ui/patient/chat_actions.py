"""What happens when the patient opens the chat, types, taps a quick reply, or sends.

Called by: ui/patient/chat.py buttons and key bindings.
The message is handed to core/conversation_service.py in a BACKGROUND thread, so the
window never freezes; "Sarah is typing…" shows until the reply is saved.
"""

import queue
import tkinter as tk

from config import get_settings

from ...storage.paths import data_folder
from ...voice.speech_input import LocalSpeechInput, resolve_input_device
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
        self.flash_light(self.t("chat.read_aloud") + "…")
        speak(text, self.lang, on_error=lambda message: self._background_errors.append(message))

    def voice_typing(self):
        if self.voice_listener:
            if self.voice_typing_active:
                self.voice_typing_active = False
                self.voice_listener.stop()
                self.voice_typing_status = self.t("chat.voice_finishing")
                self.c.itemconfigure("chat_voice_status", text=self.voice_typing_status)
                self.chat_focus_requested = True
                self.render()
            return

        try:
            input_device = resolve_input_device(get_settings().call.microphone_device)
        except (RuntimeError, ValueError, OSError) as error:
            self.voice_typing_status = self.t("chat.voice_error").format(error=str(error))
            self.c.itemconfigure("chat_voice_status", text=self.voice_typing_status)
            return
        self.voice_events = queue.Queue()
        self.voice_listener = LocalSpeechInput(
            data_folder() / "models",
            self.voice_events,
            device=input_device,
            transcribe=True,
        )
        self.voice_typing_active = True
        self.voice_typing_had_text = False
        self.voice_typing_error = False
        self.voice_typing_status = self.t("chat.voice_preparing")
        self.chat_focus_requested = True
        self.render()
        self.voice_listener.start()
        self._voice_typing_job = self.after(100, self._poll_voice_typing)

    def _poll_voice_typing(self):
        self._voice_typing_job = None
        listener = self.voice_listener
        events = self.voice_events
        if not listener or not events:
            return

        should_render = False
        while True:
            try:
                event, value = events.get_nowait()
            except queue.Empty:
                break
            if event == "final" and value:
                self._insert_voice_text(value)
                self.voice_typing_had_text = True
            elif event == "state" and value == "listening":
                self.voice_typing_status = self.t("chat.voice_listening")
            elif event == "status":
                self.voice_typing_status = value
            elif event == "error":
                error = str(value)
                if len(error) > 100:
                    error = error[:97].rstrip() + "..."
                self.voice_typing_status = self.t("chat.voice_error").format(error=error)
                self.voice_typing_active = False
                self.voice_typing_error = True
                listener.stop()
                should_render = True

        if not listener.is_alive() and events.empty():
            self.voice_listener = None
            self.voice_events = None
            self.voice_typing_active = False
            if not self.voice_typing_error:
                status_key = "chat.voice_added" if self.voice_typing_had_text else "chat.voice_stopped"
                self.voice_typing_status = self.t(status_key)
            self.voice_typing_error = False
            should_render = True

        if should_render:
            self.chat_focus_requested = True
            self.render()
        else:
            self.c.itemconfigure("chat_voice_status", text=self.voice_typing_status)
        if self.voice_listener:
            self._voice_typing_job = self.after(100, self._poll_voice_typing)

    def _insert_voice_text(self, text):
        entry = self.chat_entry
        if entry and entry.winfo_exists():
            if entry.get() == self.chat_placeholder:
                entry.delete(0, tk.END)
                entry.configure(fg=TEXT_DARK)
            current = entry.get()
            index = entry.index(tk.INSERT)
            before, after = current[:index], current[index:]
            inserted = ("" if not before or before[-1].isspace() else " ") + text
            if after and not after[0].isspace():
                inserted += " "
            entry.insert(index, inserted)
            entry.icursor(index + len(inserted))
            entry.focus_set()
            self.chat_draft = entry.get()
            return
        draft = "" if self.chat_draft == self.chat_placeholder else self.chat_draft
        self.chat_draft = f"{draft.rstrip()} {text}".strip()

    def _stop_voice_typing(self):
        listener = self.voice_listener
        if listener:
            listener.stop()
        if self._voice_typing_job:
            self.after_cancel(self._voice_typing_job)
        self._voice_typing_job = None
        self.voice_listener = None
        self.voice_events = None
        self.voice_typing_active = False
        self.voice_typing_status = ""
        self.voice_typing_had_text = False
        self.voice_typing_error = False

    def copy_chat_message(self, message):
        self.clipboard_clear()
        self.clipboard_append(message)
        self.flash_light("Copied" if self.lang == "en" else "Copié")

    def copy_chat_selection(self, event, fallback):
        try:
            selected = event.widget.get("sel.first", "sel.last")
        except tk.TclError:
            selected = fallback
        self.copy_chat_message(selected)
        return "break"
