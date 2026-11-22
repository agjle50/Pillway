"""The Call screen's behavior: microphone input, waveform level, transcript and call lifecycle.

Called by: ui/patient/call.py buttons.
- Speech-to-text is OFFLINE (Vosk, see voice/speech_input.py), chosen in [call] of the config.
- The microphone listens hands-free while unmuted; the patient can mute it at any time.
- Every sentence goes through the SAME flow and two-layer flagging as the chat (channel "call").
- Sarah's replies can be spoken (voice/tts.py) and are shown as captions.
- On "end", the call is saved as a CALL session with its duration for the pharmacist's log.
- If speech input is disabled or no microphone is available, the screen offers a switch to chat.
"""

import queue
import time

from config import get_settings

from ...storage.paths import data_folder
from ...voice.speech_input import LocalSpeechInput, resolve_input_device
from ...voice.tts import speak, stop as stop_speaking


def microphone_status():
    try:
        resolve_input_device(get_settings().call.microphone_device)
    except (RuntimeError, ValueError, OSError) as error:
        return False, str(error)
    return True, ""


class CallAudioMixin:
    def _begin_call(self):
        meter_available, microphone_message = microphone_status()
        transcribe = not self.speech_recognition_disabled()
        self.call_state = {"started": time.monotonic(), "level": 0.0, "muted": False,
                           "heard": [], "spoken": set(),
                           "speaker_enabled": get_settings().patient.read_aloud,
                           "speech_disabled": not transcribe,
                           "meter_available": meter_available, "mic_missing": not meter_available,
                           "status": (
                               ("Getting the microphone ready…" if self.lang == "en"
                                else "Préparation du microphone…")
                               if meter_available else
                               (f"{microphone_message} Switch to chat to continue."
                                if self.lang == "en" else
                                f"{microphone_message} Passez au clavardage pour continuer.")
                           )}
        pending_ends = getattr(self, "_pending_session_ends", {})
        for pending_patient, pending_session in list(pending_ends):
            if pending_patient == self.patient_id:
                pending_ends.pop((pending_patient, pending_session), None)
        self.call_state["session_id"] = self.service.start_session(self.patient_id, "CALL")
        self.record = self.store.load(self.patient_id)
        if meter_available:
            self._start_listener(transcribe=transcribe)
        self._tick_call()

    def call_elapsed(self):
        return time.monotonic() - self.call_state.get("started", time.monotonic())

    def _start_listener(self, transcribe=True):
        self.call_events = queue.Queue()
        self.call_listener = LocalSpeechInput(data_folder() / "models", self.call_events,
                                              device=resolve_input_device(get_settings().call.microphone_device),
                                              transcribe=transcribe)
        self.call_listener.language = self.lang
        self.call_listener.start()

    def _tick_call(self):
        """Runs every 75 ms during a call: reads mic events, moves the meter, speaks new replies."""
        self._call_poll_job = None
        if not self.call_open or not self.call_state:
            return
        state = self.call_state
        redraw = False
        while self.call_events is not None:
            try:
                event, value = self.call_events.get_nowait()
            except queue.Empty:
                break
            if event == "level":
                sensitivity = get_settings().call.voice_meter_sensitivity
                state["level"] = 0.0 if state["muted"] else min(1.0, value * sensitivity)
            elif event == "state" and value == "listening":
                state["status"] = (
                    ("Listening. Speak naturally; mute the microphone whenever you like."
                     if self.lang == "en" else
                     "Écoute active. Parlez normalement; vous pouvez couper le micro à tout moment.")
                    if not self.speech_recognition_disabled() else
                    ("Speech recognition is disabled. Switch to chat to continue."
                     if self.lang == "en" else
                     "La reconnaissance vocale est désactivée. Passez au clavardage pour continuer.")
                )
            elif event == "status":
                state["status"] = value
            elif event == "final" and value and not state["muted"]:
                state["heard"].append(value)
            elif event == "error":
                error = str(value)
                if len(error) > 110:
                    error = error[:107].rstrip() + "..."
                state.update(
                    mic_missing=True, meter_available=False, level=0.0,
                    error=True,
                    status=(f"Microphone unavailable: {error}" if self.lang == "en"
                            else f"Microphone indisponible : {error}"),
                )
                redraw = True
        if state["heard"]:
            self._send_call_text(" ".join(state["heard"]))
            state["heard"] = []
        self._speak_new_replies()
        if redraw:
            self.render()
        else:
            self._update_call_widgets()
        self._call_poll_job = self.after(75, self._tick_call)

    def _update_call_widgets(self):
        """Animate your voice meter, Sarah's mouth, the 'can't hear you' card and the timer."""
        self._draw_call_wave()
        self._update_silence_popup()
        self.c.itemconfigure("call_timer", text=self._call_clock())

    def _speak_new_replies(self):
        for message in self.call_caption_lines():
            if message["role"] == "sarah" and message["id"] not in self.call_state["spoken"]:
                self.call_state["spoken"].add(message["id"])
                if self.call_state.get("speaker_enabled"):
                    self._speak_on_call(message["text"])

    def _speak_on_call(self, text):
        """Speak Sarah's reply, with the microphone paused so it doesn't 'hear' her own voice."""
        listener = getattr(self, "call_listener", None)
        if listener:
            listener.set_muted(True)
        state = self.call_state
        state["sarah_speaking"] = True   # her avatar's mouth moves; the silence card waits

        def done():
            state["sarah_speaking"] = False
            # back on (unless the patient pressed mute themselves meanwhile)
            if listener and not state.get("muted"):
                listener.set_muted(False)

        speak(text, self.lang, on_done=done,
              on_error=lambda message: self._background_errors.append(message))

    def _send_call_text(self, text):
        patient_id = self.patient_id
        self.service.busy.add(patient_id)
        self.run_in_background(lambda: self.service.handle_message(patient_id, text, "call"))

    def toggle_call_mute(self):
        self.call_state["muted"] = not self.call_state.get("muted")
        self.call_state["level"] = 0.0
        listener = getattr(self, "call_listener", None)
        if listener:
            listener.set_muted(self.call_state["muted"])
        if self.call_state["muted"] and getattr(self, "call_events", None):
            queued = []
            while True:
                try:
                    event = self.call_events.get_nowait()
                except queue.Empty:
                    break
                if event[0] not in ("final", "partial", "level"):
                    queued.append(event)
            for event in queued:
                self.call_events.put(event)
        self.render()

    def toggle_call_speaker(self):
        self.call_state["speaker_enabled"] = not self.call_state.get("speaker_enabled", False)
        if not self.call_state["speaker_enabled"]:
            stop_speaking()
        self.render()

    def switch_call_to_chat(self):
        self.close_call_preview()
        self.open_profile_chat()

    def close_call_preview(self):
        state = getattr(self, "call_state", None) or {}
        self._stop_call_input()
        if state.get("session_id") and hasattr(self, "service"):
            self.end_session_when_idle(
                self.patient_id, state["session_id"],
                int(time.monotonic() - state["started"]),
            )
        self.call_state = {}
        self.call_open = False
        self.render()

    def _stop_call_input(self):
        if getattr(self, "call_listener", None):
            stop_speaking()
            self.call_listener.stop()
        if getattr(self, "_call_poll_job", None):
            self.after_cancel(self._call_poll_job)
        self._call_poll_job = None
        self.call_listener = None
        self.call_events = None
