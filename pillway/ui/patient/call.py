"""Check up -> Call screen and its microphone handling.

Called by: ui/patient/check_up.py (checkup_choice('Call')).
"""

import queue

from ..theme import (
    RED,
    WHITE,
)
from ...voice.speech_input import LocalSpeechInput


class CallMixin:
    def draw_call_preview(self, x1, y1, x2, y2):
        phone_w = min(self.S(360), x2 - x1 - self.S(36))
        phone_h = min(self.S(640), y2 - y1 - self.S(36))
        phone_h = max(self.S(300), phone_h)
        px = (x1 + x2 - phone_w) / 2
        py = (y1 + y2 - phone_h) / 2
        self.rrect(px, py, px + phone_w, py + phone_h, self.S(30),
                   fill="#111832", outline="#303955", width=self.S(2))
        inset = self.S(10)
        sx1, sy1 = px + inset, py + inset
        sx2, sy2 = px + phone_w - inset, py + phone_h - inset
        self.rrect(sx1, sy1, sx2, sy2, self.S(24), fill="#171f3b", outline="")
        cx = (sx1 + sx2) / 2
        self.rrect(cx - self.S(42), sy1 + self.S(9), cx + self.S(42), sy1 + self.S(15),
                   self.S(3), fill="#303955", outline="")
        self.text(cx, sy1 + self.S(38), "CALL PREVIEW", 10, "#c8cede", "bold",
                  anchor="center")

        avatar_y = sy1 + self.S(112)
        avatar_r = self.S(46)
        self.c.create_oval(cx - avatar_r, avatar_y - avatar_r,
                           cx + avatar_r, avatar_y + avatar_r,
                           fill=RED, outline="")
        self.text(cx, avatar_y, "P", 32, WHITE, "bold", anchor="center")
        self.text(cx, avatar_y + self.S(68), "Pillway care team", 19, WHITE, "bold",
                  anchor="center")
        self.text(cx, avatar_y + self.S(96), "Local speech preview · no call placed",
                  10, "#c8cede", anchor="center")

        status_y = avatar_y + self.S(145)
        self.text(cx, status_y, self.call_status, 9,
                  RED if self.call_mic_state == "error" else "#c8cede",
                  anchor="center", tag="call_status")
        self.text(
            cx, status_y + self.S(54),
            self.call_transcript[-180:] or "Your on-device transcript will appear here.",
            9, "#f3f5fa", anchor="n", tag="call_transcript",
        )
        self.c.itemconfigure("call_status", width=phone_w - self.S(44))
        self.c.itemconfigure("call_transcript", width=phone_w - self.S(44))

        controls_y = sy2 - self.S(106)
        mic_x = cx - self.S(58)
        mic_tag = "call_mic_control"
        self.c.create_oval(
            mic_x - self.S(25), controls_y - self.S(25),
            mic_x + self.S(25), controls_y + self.S(25),
            fill=RED if self.call_mic_state == "listening" else "#303955",
            outline="", tags=(mic_tag, "call_mic_button"),
        )
        self.draw_icon("mic", mic_x, controls_y, self.S(22), "#c8cede",
                       mic_tag, bg="#303955")
        self.c.create_line(mic_x - self.S(14), controls_y + self.S(14),
                           mic_x + self.S(14), controls_y - self.S(14),
                           fill=RED, width=self.S(2),
                           tags=(mic_tag, "call_mic_slash"))
        self.text(mic_x, controls_y + self.S(39),
                  "Stop mic" if self.call_mic_state in (
                      "preparing", "downloading", "listening", "stopping",
                  ) else "Start mic",
                  9, "#c8cede", anchor="center", tag="call_mic_label")
        self.clickable(mic_tag, self.toggle_call_microphone)

        end_x = cx + self.S(58)
        end_tag = "end_call_preview"
        self.c.create_oval(end_x - self.S(25), controls_y - self.S(25),
                           end_x + self.S(25), controls_y + self.S(25),
                           fill=RED, outline="", tags=end_tag)
        self.draw_icon("phone", end_x, controls_y, self.S(23), WHITE, end_tag, bg=RED)
        self.clickable(end_tag, self.close_call_preview)
        self.text(end_x, controls_y + self.S(39), "End preview", 9, "#c8cede",
                  anchor="center", tag=end_tag)

        self.text(cx, sy2 - self.S(16), "On-device only · audio is not saved or uploaded.",
                  9, "#c8cede", anchor="center")
        self._update_call_preview()
    def close_call_preview(self):
        self._stop_call_input()
        self.call_open = False
        self.call_transcript = ""
        self.call_status = "Microphone off."
        self.render()
    def toggle_call_microphone(self):
        if self.call_mic_state == "stopping":
            return
        if self.call_listener and self.call_listener.is_alive():
            self.call_listener.stop()
            self.call_mic_state = "stopping"
            self.call_status = "Stopping microphone..."
            self._update_call_preview()
            return

        self.call_mic_state = "preparing"
        self.call_status = "Preparing on-device speech recognition..."
        self.call_transcript = ""
        self.call_partial = ""
        self.call_events = queue.Queue()
        model_root = self.chat_history.path.parent / "models"
        self.call_listener = LocalSpeechInput(model_root, self.call_events)
        self.call_listener.start()
        self._update_call_preview()
        self._poll_call_events()
    def _poll_call_events(self):
        self._call_poll_job = None
        if not self.call_open or self.call_events is None:
            return
        while True:
            try:
                event, value = self.call_events.get_nowait()
            except queue.Empty:
                break
            if event == "state":
                if value == "preparing":
                    self.call_mic_state = "preparing"
                    self.call_status = "Preparing on-device speech recognition..."
                elif value == "listening":
                    self.call_mic_state = "listening"
                    self.call_status = "Listening; speech is processed on this device."
                elif value == "stopped":
                    self.call_mic_state = "off"
                    self.call_status = "Microphone off."
                    self.call_listener = None
            elif event == "status":
                self.call_status = value
                if value.startswith("Downloading offline model"):
                    self.call_mic_state = "downloading"
            elif event == "partial":
                self.call_partial = value
            elif event == "final":
                self.call_transcript = " ".join(
                    part for part in (self.call_transcript, value) if part
                )
                self.call_partial = ""
            elif event == "error":
                self.call_mic_state = "error"
                self.call_status = f"Microphone error: {value}"
                self.call_listener = None
        self._update_call_preview()
        if self.call_listener is not None:
            self._call_poll_job = self.after(75, self._poll_call_events)
    def _update_call_preview(self):
        listening = self.call_mic_state == "listening"
        active = self.call_mic_state in ("preparing", "downloading", "listening", "stopping")
        button_text = "Stop mic" if active else "Start mic"
        self.c.itemconfigure("call_mic_label", text=button_text)
        self.c.itemconfigure("call_mic_button", fill=RED if listening else "#303955")
        self.c.itemconfigure(
            "call_mic_slash", state="hidden" if listening else "normal",
        )
        self.c.itemconfigure(
            "call_status",
            text=self.call_status,
            fill=RED if self.call_mic_state == "error" else "#c8cede",
        )
        transcript = " ".join(part for part in (self.call_transcript, self.call_partial) if part)
        self.c.itemconfigure(
            "call_transcript",
            text=transcript[-180:] if transcript else "Your on-device transcript will appear here.",
        )
    def _stop_call_input(self):
        if self.call_listener:
            self.call_listener.stop()
        if self._call_poll_job:
            self.after_cancel(self._call_poll_job)
            self._call_poll_job = None
        self.call_listener = None
        self.call_events = None
        self.call_mic_state = "off"
        self.call_partial = ""
