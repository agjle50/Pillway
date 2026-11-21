"""Check up -> Call: talk to Sarah by voice, designed like the iPhone call screen.

Called by: ui/patient/dashboard.py when self.call_open is True.
Big name and timer, a GREEN ring that moves with the patient's voice (grey when muted or
silent), big round mute / hold-to-talk / end buttons, and large captions. Concerning
sentences show in red with a flag. Microphone and session logic: ui/patient/call_audio.py.
"""

from config import get_settings

from ..theme import RED, WHITE

CALL_BG, CALL_PANEL, CALL_GREY, CALL_GREEN = "#1c1c1e", "#2c2c2e", "#8e8e93", "#34c759"


class CallMixin:
    def draw_call_preview(self, x1, y1, x2, y2):
        if not self.call_state:
            self._begin_call()
        state = self.call_state
        self.rrect(x1, y1, x2, y2, self.S(16), fill=CALL_BG, outline=CALL_BG)
        if not self.record["consent"]["accepted"]:
            self.draw_consent(x1, y1, x2, y2)
            return
        cx = (x1 + x2) / 2
        self.text(cx, y1 + self.S(58), self.t("call.title"), 34, WHITE, anchor="center")
        self.text(cx, y1 + self.S(96), self.t("call.subtitle"), 14, CALL_GREY, anchor="center")
        self.text(cx, y1 + self.S(124), self._call_clock(), 16, CALL_GREY, anchor="center", tag="call_timer")

        avatar_y, radius = y1 + self.S(225), self.S(64)
        ring = radius + self.S(10) + state.get("level", 0) * self.S(40)
        live = state.get("level", 0) > 0.05 and not state.get("muted")
        self.c.create_oval(cx - ring, avatar_y - ring, cx + ring, avatar_y + ring, fill="",
                           outline=CALL_GREEN if live else "#3a3a3c", width=self.S(8), tags="call_ring")
        self.c.create_oval(cx - radius, avatar_y - radius, cx + radius, avatar_y + radius, fill="#636366", outline="")
        self.text(cx, avatar_y, "S", 48, WHITE, "bold", anchor="center")

        self._draw_captions(cx, avatar_y + self.S(100), min(self.S(760), x2 - x1 - self.S(60)), y2 - self.S(240))
        self.text(cx, y2 - self.S(200), state.get("status", ""), 13, RED if state.get("error") else CALL_GREY,
                  anchor="center", tag="call_status")
        self._draw_call_controls(cx, y2 - self.S(110))
        if state.get("mic_missing"):
            self._draw_no_mic_help(x1, x2, y2)

    def _draw_captions(self, cx, top, width, bottom):
        """Large captions: the last two lines of the call, trimmed so they never cover the buttons."""
        y = top
        for message in self.call_caption_lines()[-2:]:
            mine = message["role"] == "patient"
            colour = RED if message.get("tier") == 1 else "#ffcc00" if message.get("tier") == 2 else (
                "#d1d1d6" if mine else WHITE)
            prefix = ("You: " if self.lang == "en" else "Vous : ") if mine else "Sarah: "
            if message.get("tier"):
                prefix = "⚑ " + prefix
            text = " ".join(message["text"].split())
            room = max(60, int((bottom - y) / self.S(24)) * 60)
            if len(text) > room:
                text = text[:room].rsplit(" ", 1)[0] + "…"
            item = self.c.create_text(cx, y, text=prefix + text, fill=colour, anchor="n", justify="center",
                                      font=self.font(15, "bold" if message.get("tier") else "normal"), width=width)
            y = self.c.bbox(item)[3] + self.S(12)
            if y > bottom:
                break

    def _draw_call_controls(self, cx, cy):
        state = self.call_state
        spacing, small, big = self.S(150), self.S(38), self.S(54)
        # mute
        muted = state.get("muted")
        self.c.create_oval(cx - spacing - small, cy - small, cx - spacing + small, cy + small,
                           fill=WHITE if muted else CALL_PANEL, outline="", tags="call_mute")
        self.draw_icon("mic", cx - spacing, cy, self.S(26), CALL_BG if muted else WHITE, "call_mute",
                       bg=WHITE if muted else CALL_PANEL)
        if muted:
            self.c.create_line(cx - spacing - self.S(16), cy + self.S(16), cx - spacing + self.S(16), cy - self.S(16),
                               fill=CALL_BG, width=self.S(3), tags="call_mute")
        self.text(cx - spacing, cy + small + self.S(18), self.t("call.mute"), 13, WHITE, anchor="center")
        self.clickable("call_mute", self.toggle_call_mute)
        # hold to talk (or "say demo line" when there is no microphone)
        talk_tag = "call_talk"
        holding = state.get("holding")
        self.c.create_oval(cx - big, cy - big, cx + big, cy + big, fill=CALL_GREEN if holding else "#30d158",
                           outline=WHITE if holding else "", width=self.S(3), tags=talk_tag)
        self.draw_icon("mic", cx, cy, self.S(34), WHITE, talk_tag, bg=CALL_GREEN)
        label = self.t("call.demo_line") if state.get("use_demo") else self.t("call.hold")
        self.text(cx, cy + big + self.S(18), label, 13, WHITE, "bold", anchor="center")
        if state.get("use_demo"):
            self.clickable(talk_tag, self.say_demo_line)
        else:
            self.c.tag_bind(talk_tag, "<ButtonPress-1>", lambda _e: self.start_talking())
            self.c.tag_bind(talk_tag, "<ButtonRelease-1>", lambda _e: self.stop_talking())
            self.c.tag_bind(talk_tag, "<Enter>", lambda _e: self.c.configure(cursor="hand2"))
            self.c.tag_bind(talk_tag, "<Leave>", lambda _e: self.c.configure(cursor=""))
        # end call
        self.c.create_oval(cx + spacing - small, cy - small, cx + spacing + small, cy + small, fill="#ff3b30",
                           outline="", tags="end_call_preview")
        self.draw_icon("phone", cx + spacing, cy, self.S(26), WHITE, "end_call_preview", bg="#ff3b30")
        self.text(cx + spacing, cy + small + self.S(18), self.t("call.end"), 13, WHITE, anchor="center")
        self.clickable("end_call_preview", self.close_call_preview)

    def _draw_no_mic_help(self, x1, x2, y2):
        width = min(self.S(700), x2 - x1 - self.S(40))
        cx = (x1 + x2) / 2
        top = y2 - self.S(300)
        item = self.c.create_text(cx, top, text=self.t("call.no_mic"), fill="#ffcc00", font=self.font(12),
                                  width=width, justify="center", anchor="s")
        box = self.c.bbox(item)
        tag = "call_switch_chat"
        self.rrect(cx - self.S(90), box[1] - self.S(52), cx + self.S(90), box[1] - self.S(10), self.S(20),
                   fill=WHITE, outline="", tags=tag)
        self.text(cx, box[1] - self.S(31), self.t("call.switch_chat"), 13, CALL_BG, "bold", anchor="center", tag=tag)
        self.clickable(tag, self.switch_call_to_chat)

    def _call_clock(self):
        seconds = int(self.call_elapsed())
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    def call_caption_lines(self):
        session = self.call_state.get("session_id")
        return [m for m in self.record["messages"] if m.get("session_id") == session and m.get("channel") == "call"]

    def uses_demo_call(self):
        settings = get_settings()
        return settings.ai.demo_mode or settings.call.speech_to_text_engine == "none"
