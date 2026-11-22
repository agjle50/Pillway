"""Check up -> Call: hands-free voice conversation with Sarah in a bright Pillway call view.

Called by: ui/patient/dashboard.py when self.call_open is True.
The live sine waveform and input level respond to microphone volume. Microphone
and session logic: ui/patient/call_audio.py. The mic stays live until muted or the call ends.
"""

import math

from config import get_settings

from ...storage.patient_store import display_name, initials
from ..theme import HOVER, INK, ORANGE, RED, WHITE

CALL_BG = "#f27032"
CALL_HALO = "#f68442"
CALL_PANEL = "#d9572b"
CALL_GREY = "#fff1e8"
CALL_RED = "#d93636"


class CallMixin:
    def draw_call_preview(self, x1, y1, x2, y2):
        self.rrect(x1, y1, x2, y2, self.S(28), fill=CALL_BG, outline=CALL_BG)
        if not self.record["consent"]["accepted"]:
            self.draw_consent(x1, y1, x2, y2)
            return
        if not self.call_state:
            self._begin_call()
        state = self.call_state
        cx = (x1 + x2) / 2
        heading = "APPEL PILLWAY" if self.lang == "fr" else "PILLWAY CALL"
        self.text(cx, y1 + self.S(42), heading, 12, CALL_GREY, "bold", anchor="center")
        self.text(x2 - self.S(30), y1 + self.S(42), self._call_clock(), 14, WHITE,
                  "bold", anchor="e", tag="call_timer")

        avatar_y = y1 + min(self.S(245), (y2 - y1) * 0.32)
        radius = min(self.S(62), (y2 - y1) * 0.13)
        state["wave_center"] = (cx, avatar_y)
        state["wave_radius"] = radius
        self.c.create_oval(
            cx - radius - self.S(24), avatar_y - radius - self.S(24),
            cx + radius + self.S(24), avatar_y + radius + self.S(24),
            fill=CALL_HALO, outline="", tags="call_avatar_halo",
        )
        self.c.create_oval(
            cx - radius, avatar_y - radius, cx + radius, avatar_y + radius,
            fill="#fffaf6", outline=WHITE, width=self.S(5), tags="call_avatar",
        )
        self.text(cx, avatar_y, initials(self.record), 29, INK, "bold",
                  anchor="center", tag="call_avatar_initials")
        self._draw_call_wave()
        name_y = avatar_y + radius + self.S(34)
        self.text(cx, name_y, display_name(self.record), 25, WHITE, "bold", anchor="center")
        subtitle = "Sarah est avec vous" if self.lang == "fr" else "Sarah is here with you"
        self.text(cx, name_y + self.S(30), subtitle, 13, CALL_GREY, anchor="center")

        caption_top = name_y + self.S(64)
        caption_bottom = y2 - self.S(
            286 if state.get("mic_missing") or state.get("speech_disabled") else 226
        )
        self._draw_captions(
            cx, caption_top, min(self.S(700), x2 - x1 - self.S(60)), caption_bottom
        )
        self._draw_call_controls(cx, y2 - self.S(132), x1, x2)
        meter_width = min(self.S(148), x2 - x1 - self.S(80))
        meter_x1 = cx - meter_width / 2
        meter_y = y2 - self.S(32)
        self.text(cx, meter_y - self.S(17), self._call_meter_status(), 11, WHITE,
                  anchor="center", tag="call_meter_status")
        self.c.create_line(
            meter_x1, meter_y, meter_x1 + meter_width, meter_y,
            fill="#f9aa7c", width=self.S(5), capstyle="round", tags="call_meter_track",
        )
        self.c.create_line(
            meter_x1, meter_y, meter_x1, meter_y,
            fill=WHITE, width=self.S(5), capstyle="round", tags="call_meter_fill",
        )
        if state.get("mic_missing") or state.get("speech_disabled"):
            self._draw_no_mic_help(x1, x2, y2)

    def _draw_call_wave(self):
        state = self.call_state
        cx, cy = state["wave_center"]
        radius = state["wave_radius"]
        level = 0.0 if state.get("muted") else state.get("level", 0.0)
        phase = self.call_elapsed() * 2.8
        count = 72
        for index in range(count):
            angle = 2 * math.pi * index / count
            pulse = (math.sin(angle * 7 - phase) + 1) / 2
            inner = radius + self.S(16)
            outer = inner + self.S(2 + 4 * pulse + level * (9 + 34 * pulse))
            coords = (
                cx + math.cos(angle) * inner,
                cy + math.sin(angle) * inner,
                cx + math.cos(angle) * outer,
                cy + math.sin(angle) * outer,
            )
            tag = f"call_wave_{index}"
            if self.c.find_withtag(tag):
                self.c.coords(tag, *coords)
            else:
                self.c.create_line(
                    *coords, fill=WHITE, width=self.S(2.5), capstyle="round", tags=("call_wave", tag),
                )
        avatar_radius = radius + self.S(4) * level
        self.c.coords(
            "call_avatar", cx - avatar_radius, cy - avatar_radius,
            cx + avatar_radius, cy + avatar_radius,
        )
        halo_radius = avatar_radius + self.S(24)
        self.c.coords(
            "call_avatar_halo", cx - halo_radius, cy - halo_radius,
            cx + halo_radius, cy + halo_radius,
        )
        self.c.coords("call_avatar_initials", cx, cy)

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

    def _draw_call_controls(self, cx, cy, x1, x2):
        state = self.call_state
        spacing = min(self.S(108), (x2 - x1) / 3.2)
        small = min(self.S(34), (x2 - x1) / 12)
        muted = state.get("muted")
        self._draw_call_control("call_mute", cx - spacing, cy, small, "mic",
                                WHITE if muted else CALL_PANEL, CALL_BG if muted else WHITE,
                                self.toggle_call_mute)
        if muted:
            self.c.create_line(cx - spacing - self.S(16), cy + self.S(16), cx - spacing + self.S(16), cy - self.S(16),
                               fill=CALL_BG, width=self.S(3), tags="call_mute")
        mic_label = self.t("call.unmute") if muted else self.t("call.mute")
        self.text(cx - spacing, cy + small + self.S(17), mic_label, 12, WHITE, anchor="center")

        speaker_on = state.get("speaker_enabled", False)
        self._draw_call_control("call_speaker", cx, cy, small, "speaker",
                                CALL_PANEL, WHITE, self.toggle_call_speaker)
        if not speaker_on:
            self.c.create_line(
                cx - self.S(17), cy + self.S(17), cx + self.S(17), cy - self.S(17),
                fill=WHITE, width=self.S(3), tags="call_speaker",
            )
        speaker_label = self.t("call.speaker") if speaker_on else self.t("call.speaker_off")
        self.text(cx, cy + small + self.S(17), speaker_label, 12, WHITE, anchor="center")
        self._draw_call_control("end_call_preview", cx + spacing, cy, small, "phone",
                                CALL_RED, WHITE, self.close_call_preview)
        self.text(cx + spacing, cy + small + self.S(17), self.t("call.end"), 12, WHITE, anchor="center")

    def _draw_call_control(self, tag, cx, cy, radius, icon, fill, icon_color, action):
        shadow_tag = f"{tag}::shadow"
        background_tag = f"{tag}::background"
        self.c.create_oval(
            cx - radius + self.S(1), cy - radius + self.S(3),
            cx + radius + self.S(1), cy + radius + self.S(3),
            fill="#d95e35", outline="", tags=shadow_tag,
        )
        self.c.create_oval(
            cx - radius, cy - radius, cx + radius, cy + radius,
            fill=fill, outline="", tags=(tag, background_tag),
        )
        self.draw_icon(icon, cx, cy, self.S(24), icon_color, tag, bg=fill)
        self.clickable(tag, action)
        self.c.tag_bind(
            tag, "<Enter>",
            lambda *_: (
                self.c.itemconfigure(background_tag, fill=HOVER),
                self.c.itemconfigure(f"{tag}_icon", fill=ORANGE),
            ),
            add="+",
        )
        self.c.tag_bind(
            tag, "<Leave>",
            lambda *_: (
                self.c.itemconfigure(background_tag, fill=fill),
                self.c.itemconfigure(f"{tag}_icon", fill=icon_color),
            ),
            add="+",
        )

    def _draw_no_mic_help(self, x1, x2, y2):
        width = min(self.S(700), x2 - x1 - self.S(40))
        cx = (x1 + x2) / 2
        top = y2 - self.S(224)
        message = self.t("call.speech_disabled") if self.call_state.get("speech_disabled") else self.t("call.no_mic")
        item = self.c.create_text(cx, top, text=message, fill=WHITE, font=self.font(11),
                                  width=width, justify="center", anchor="s")
        box = self.c.bbox(item)
        tag = "call_switch_chat"
        self.rrect(cx - self.S(90), box[1] - self.S(52), cx + self.S(90), box[1] - self.S(10), self.S(20),
                   fill=WHITE, outline="#fff4e8", tags=tag)
        self.text(cx, box[1] - self.S(31), self.t("call.switch_chat"), 13, CALL_BG, "bold", anchor="center", tag=tag)
        self.clickable(tag, self.switch_call_to_chat)

    def _call_clock(self):
        seconds = int(self.call_elapsed())
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    def call_caption_lines(self):
        session = self.call_state.get("session_id")
        return [m for m in self.record["messages"] if m.get("session_id") == session and m.get("channel") == "call"]

    def speech_recognition_disabled(self):
        settings = get_settings()
        return settings.call.speech_to_text_engine == "none"

    def _call_meter_status(self):
        state = self.call_state
        if state.get("muted"):
            return "Microphone muted" if self.lang == "en" else "Microphone en sourdine"
        if not state.get("meter_available"):
            return "Microphone unavailable" if self.lang == "en" else "Microphone indisponible"
        level = state.get("level", 0.0)
        if level <= 0.025:
            return "No voice detected" if self.lang == "en" else "Aucune voix détectée"
        return (f"Input detected · {round(level * 100)}%" if self.lang == "en"
                else f"Entrée détectée · {round(level * 100)}%")
