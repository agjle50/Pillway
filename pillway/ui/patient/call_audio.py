"""The Call screen's behavior: microphone input, waveform level, transcript and call lifecycle.

Called by: ui/patient/call.py buttons.
- Speech-to-text is OFFLINE (Vosk, see voice/speech_input.py), chosen in [call] of the config.
- The microphone listens hands-free while unmuted; the patient can mute it at any time.
- Every sentence goes through the SAME flow and two-layer flagging as the chat (channel "call").
- Sarah's replies can be spoken (voice/tts.py) and are shown as captions.
- On "end", the call is saved as a CALL session with its duration for the pharmacist's log.
- If speech input is disabled or no microphone is available, the screen offers a switch to chat.

Turn-taking (so Sarah never "hears" herself through the speakers and answers her own words):
the microphone is only open when ALL of these are true, checked every tick by _apply_mic_gate():
  * the patient hasn't pressed Mute,
  * Sarah isn't talking (from the moment her reply is handed to the voice until it ends), and
  * a short "echo tail" has passed since she stopped (speakers and rooms ring on for a moment,
    and some recognizers report a sentence a second late).
Anything the recognizer reports while the mic is closed is thrown away, never sent to Sarah.
With `debug_logs = true` every open/close and every heard sentence is printed in the terminal.
"""

import queue
import time

from config import get_settings

from ... import debug_log
from ...storage.paths import data_folder
from ...voice.speech_input import LocalSpeechInput, resolve_input_device
from ...voice.tts import speak, stop as stop_speaking


# Seconds the mic stays closed after Sarah stops talking. Windows' recognizer reports sentences
# late (after it decides you stopped talking), so it needs a longer tail than Whisper/Vosk.
ECHO_TAIL_SECONDS = 0.8
ECHO_TAIL_SECONDS_WINDOWS = 1.6


def mic_should_listen(state, now=None):
    """(open?, reason). The one rule for whether the patient's microphone is listening."""
    now = time.monotonic() if now is None else now
    if state.get("muted"):
        return False, "patient pressed mute"
    if state.get("sarah_speaking"):
        return False, "Sarah is talking"
    if now < state.get("deaf_until", 0.0):
        return False, "echo tail after Sarah spoke"
    return True, "patient's turn"


def echo_tail(app):
    listener = getattr(app, "call_listener", None)
    engine = getattr(listener, "active_engine", "") if listener else ""
    return ECHO_TAIL_SECONDS_WINDOWS if engine == "windows" else ECHO_TAIL_SECONDS


def apply_mic_gate(app):
    """Open or close the call microphone to match mic_should_listen(); logs every change."""
    state = app.call_state
    is_open, reason = mic_should_listen(state)
    listener = getattr(app, "call_listener", None)
    if listener is not None and hasattr(listener, "set_muted"):
        listener.set_muted(not is_open)
    if state.get("mic_open") != is_open:
        state["mic_open"] = is_open
        if not is_open:
            state["level"] = 0.0
        debug_log.log("call", f"mic {'ON ' if is_open else 'OFF'}", reason=reason)
    return is_open


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
        debug_log.log("call", "call started", patient=self.patient_id, session=self.call_state["session_id"],
                      mic="ok" if meter_available else f"missing: {microphone_message}",
                      transcribe=transcribe, speaker=self.call_state["speaker_enabled"])
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
        self.call_state["mic_open"] = True   # a new listener starts unmuted
        debug_log.log("call", "listener started", engine=get_settings().call.speech_to_text_engine,
                      device=self.call_listener.device, language=self.lang)

    def _tick_call(self):
        """Runs every 75 ms during a call: reads mic events, moves the meter, speaks new replies."""
        self._call_poll_job = None
        if not self.call_open or not self.call_state:
            return
        state = self.call_state
        redraw = False
        mic_open = apply_mic_gate(self)
        while self.call_events is not None:
            try:
                event, value = self.call_events.get_nowait()
            except queue.Empty:
                break
            if event in ("level", "partial", "final") and not mic_open:
                # captured while Sarah was talking (or muted): her own voice, never the patient's turn
                if event == "final" and value:
                    debug_log.log("call", "heard (DROPPED)", why=mic_should_listen(state)[1],
                                  text=debug_log.snippet(value))
                continue
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
                debug_log.log("speech", "status", text=debug_log.snippet(value))
            elif event == "state":
                debug_log.log("speech", f"recognizer {value}")
            elif event == "final" and value and not state["muted"]:
                debug_log.log("call", "heard (used)", text=debug_log.snippet(value))
                state["heard"].append(value)
            elif event == "error":
                debug_log.log("speech", "ERROR", text=debug_log.snippet(value))
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
        """Say every new reply, in order, never cutting one off (BUG FIX: starting a second reply used
        to stop the first after its first sentence). Replies that arrive while Sarah is talking wait
        in a queue and are said when she finishes; several at once are said as one piece."""
        new = []
        for message in self.call_caption_lines():
            if message["role"] == "sarah" and message["id"] not in self.call_state["spoken"]:
                self.call_state["spoken"].add(message["id"])
                debug_log.log("call", "Sarah replied", source=message.get("source"),
                              speaker="on" if self.call_state.get("speaker_enabled") else "off",
                              text=debug_log.snippet(message["text"]))
                new.append(message["text"])
        queue = self.call_state.setdefault("voice_queue", [])
        if new and self.call_state.get("speaker_enabled"):
            queue.extend(new)
        if queue and not self.call_state.get("sarah_speaking"):
            text = "\n\n".join(queue)
            queue.clear()
            self._speak_on_call(text)

    def _speak_on_call(self, text):
        """Speak Sarah's reply with the microphone CLOSED, so she never hears (and answers) herself.

        Each reply gets a numbered token. BUG FIX: when a second reply started, stopping the
        first one ran the first one's "done" callback, which switched the mic back on while the
        second reply was still playing through the speakers. Now a callback only counts if it
        belongs to the reply that is currently speaking.
        """
        state = self.call_state
        token = state.get("speak_token", 0) + 1
        state["speak_token"] = token
        # "speaking" = a reply is on its way or playing (mic closed, silence card waits);
        # "audio" = sound is ACTUALLY coming out (only then does her mouth move).
        state["sarah_speaking"] = True
        if state.get("heard"):
            debug_log.log("call", "heard (DROPPED)", why="Sarah started talking",
                          text=debug_log.snippet(" ".join(state["heard"])))
            state["heard"] = []
        apply_mic_gate(self)          # close the mic NOW, before any sound comes out
        tail = echo_tail(self)
        started = time.monotonic()
        debug_log.log("voice", "speaking", reply=token, words=len(text.split()))

        def playing(value):
            if state.get("speak_token") == token:
                state["sarah_audio"] = value
                debug_log.log("voice", "sound " + ("playing" if value else "paused"), reply=token)

        def done():
            if state.get("speak_token") != token:
                debug_log.log("voice", "old reply finished (ignored)", reply=token)
                return
            state["sarah_audio"] = False
            state["deaf_until"] = time.monotonic() + tail
            state["sarah_speaking"] = False
            # the tick reopens the mic once the echo tail has passed (unless the patient muted)
            debug_log.log("voice", "finished", reply=token, seconds=round(time.monotonic() - started, 1),
                          mic_back_in=f"{tail}s")

        def failed(message):
            debug_log.log("voice", "ERROR", text=debug_log.snippet(message))
            self._background_errors.append(message)

        speak(text, self.lang, on_done=done, on_playing=playing, on_error=failed)

    def _send_call_text(self, text):
        debug_log.log("call", "sent to Sarah", text=debug_log.snippet(text))
        patient_id = self.patient_id
        self.service.busy.add(patient_id)
        self.run_in_background(lambda: self.service.handle_message(patient_id, text, "call"))

    def toggle_call_mute(self):
        self.call_state["muted"] = not self.call_state.get("muted")
        self.call_state["level"] = 0.0
        debug_log.log("call", "patient pressed " + ("Mute" if self.call_state["muted"] else "Unmute"))
        apply_mic_gate(self)
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
        self.call_state["voice_queue"] = []
        debug_log.log("call", "speaker " + ("on" if self.call_state["speaker_enabled"] else "off"))
        if not self.call_state["speaker_enabled"]:
            stop_speaking()
        self.render()

    def switch_call_to_chat(self):
        self.close_call_preview()
        self.open_profile_chat()

    def close_call_preview(self):
        state = getattr(self, "call_state", None) or {}
        self._stop_call_input()
        if state.get("started"):
            debug_log.log("call", "call ended", seconds=int(time.monotonic() - state["started"]))
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
