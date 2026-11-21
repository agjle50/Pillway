"""The Call screen's behaviour: microphone check, hold-to-talk, green meter, transcript, ending the call.

Called by: ui/patient/call.py buttons.
- Speech-to-text is OFFLINE (Vosk, see voice/speech_input.py), chosen in [call] of the config.
  Hold-to-talk is the default because continuous listening is unreliable in a noisy room.
- Every sentence goes through the SAME flow and two-layer flagging as the chat (channel "call").
- Sarah's replies are spoken (voice/tts.py) and shown as captions.
- On "end", the call is saved as a CALL session with its duration for the pharmacist's log.
- No microphone or demo mode: a scripted call with a simulated green meter.
"""

import queue
import random
import time

from config import get_settings

from ...storage.paths import data_folder
from ...voice.speech_input import LocalSpeechInput
from ...voice.tts import speak
from ..sample_content import DEMO_CALL_LINES


def microphone_available():
    try:
        import sounddevice
        return bool([d for d in sounddevice.query_devices() if d.get("max_input_channels", 0) > 0])
    except Exception:
        return False


class CallAudioMixin:
    def _begin_call(self):
        use_demo = self.uses_demo_call() or not microphone_available()
        self.call_state = {"started": time.monotonic(), "level": 0.0, "muted": False, "holding": False,
                           "heard": [], "use_demo": use_demo, "demo_index": 0, "spoken": set(),
                           "mic_missing": not use_demo and False,
                           "status": "Tap the green button to say the next line." if use_demo else "Getting the microphone ready…"}
        if not self.uses_demo_call() and not microphone_available():
            self.call_state["mic_missing"] = True
            self.call_state["status"] = ""
        self.call_state["session_id"] = self.service.start_session(self.patient_id, "CALL")
        self.record = self.store.load(self.patient_id)
        if not use_demo:
            self._start_listener()
        self._tick_call()

    def call_elapsed(self):
        return time.monotonic() - self.call_state.get("started", time.monotonic())

    def _start_listener(self):
        self.call_events = queue.Queue()
        self.call_listener = LocalSpeechInput(data_folder() / "models", self.call_events,
                                              device=get_settings().call.microphone_device or None)
        self.call_listener.start()

    def _tick_call(self):
        """Runs every 75 ms during a call: reads mic events, moves the meter, speaks new replies."""
        self._call_poll_job = None
        if not self.call_open or not self.call_state:
            return
        state = self.call_state
        while self.call_events is not None:
            try:
                event, value = self.call_events.get_nowait()
            except queue.Empty:
                break
            if event == "level":
                sensitivity = get_settings().call.voice_meter_sensitivity
                state["level"] = 0.0 if state["muted"] else min(1.0, value * sensitivity)
            elif event == "state" and value == "listening":
                state["status"] = "Hold the green button and speak." if self.lang == "en" else "Maintenez le bouton vert et parlez."
            elif event == "status":
                state["status"] = value
            elif event == "final" and value and (state["holding"] or state.get("release_grace", 0) > time.monotonic()
                                                 or get_settings().call.listening_mode == "continuous"):
                state["heard"].append(value)
            elif event == "error":
                state.update(mic_missing=True, use_demo=True, error=True, status="")
        if state.get("fake_until", 0) > time.monotonic():
            state["level"] = random.uniform(0.25, 0.9)
        elif state.get("use_demo"):
            state["level"] = 0.0
        if state["heard"] and not state["holding"] and state.get("release_grace", 0) < time.monotonic():
            self._send_call_text(" ".join(state["heard"]))
            state["heard"] = []
        self._speak_new_replies()
        self._update_call_widgets()
        self._call_poll_job = self.after(75, self._tick_call)

    def _update_call_widgets(self):
        """Move the ring and timer without redrawing the whole screen."""
        bbox = self.c.bbox("call_ring")
        if bbox:
            cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
            ring = self.S(74) + self.call_state["level"] * self.S(40)
            live = self.call_state["level"] > 0.05 and not self.call_state["muted"]
            self.c.coords("call_ring", cx - ring, cy - ring, cx + ring, cy + ring)
            self.c.itemconfigure("call_ring", outline="#34c759" if live else "#3a3a3c")
        self.c.itemconfigure("call_timer", text=self._call_clock())
        self.c.itemconfigure("call_status", text=self.call_state.get("status", ""))

    def _speak_new_replies(self):
        for message in self.call_caption_lines():
            if message["role"] == "sarah" and message["id"] not in self.call_state["spoken"]:
                self.call_state["spoken"].add(message["id"])
                if get_settings().patient.read_aloud:
                    speak(message["text"], self.lang)

    def _send_call_text(self, text):
        patient_id = self.patient_id
        self.service.busy.add(patient_id)
        self.run_in_background(lambda: self.service.handle_message(patient_id, text, "call"))

    def start_talking(self):
        if self.call_state.get("muted"):
            return
        self.call_state["holding"] = True
        self.render()

    def stop_talking(self):
        self.call_state["holding"] = False
        self.call_state["release_grace"] = time.monotonic() + 0.8  # let the last words arrive
        self.render()

    def say_demo_line(self):
        """Scripted call for the stage: simulated green meter, then the line is 'heard'."""
        lines = DEMO_CALL_LINES.get(self.lang) or DEMO_CALL_LINES.get("en", [])
        if not lines or self.patient_id in self.service.busy:
            return
        line = lines[self.call_state["demo_index"] % len(lines)]
        self.call_state["demo_index"] += 1
        self.call_state["fake_until"] = time.monotonic() + 1.4
        self.after(1400, lambda: self.call_open and self._send_call_text(line))

    def toggle_call_mute(self):
        self.call_state["muted"] = not self.call_state.get("muted")
        self.call_state["level"] = 0.0
        self.render()

    def switch_call_to_chat(self):
        self.close_call_preview()
        self.open_profile_chat()

    def close_call_preview(self):
        state = getattr(self, "call_state", None) or {}
        self._stop_call_input()
        if state.get("session_id") and hasattr(self, "service"):
            self.service.end_session(self.patient_id, state["session_id"], int(time.monotonic() - state["started"]))
        self.call_state = {}
        self.call_open = False
        self.render()

    def _stop_call_input(self):
        if getattr(self, "call_listener", None):
            self.call_listener.stop()
        if getattr(self, "_call_poll_job", None):
            self.after_cancel(self._call_poll_job)
        self._call_poll_job = None
        self.call_listener = None
        self.call_events = None
