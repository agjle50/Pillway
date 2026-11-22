"""Check up -> Call: a hands-free voice call with Sarah.

Called by: ui/patient/dashboard.py when self.call_open is True.
Layout (top to bottom): "Pillway call" + timer; Sarah's illustrated avatar (her mouth moves
while she speaks); her name; live captions; an Apple-style frosted "liquid glass" bar with
Mute / Speaker / End. Bottom-right, well inside the margin: YOUR microphone orb, whose bars
grow with how loudly you speak. If no voice is heard for a while (or there's no microphone),
a small Pillway card appears top-right saying you may be muted or the mic isn't working.
Artwork: ui/patient/call_art.py. Microphone and session logic: ui/patient/call_audio.py.
"""

import math
import time

from config import get_settings

from ...storage.patient_store import initials
from ..theme import BORDER, INK, NAVY, RED, RED_SOFT, TEXT_DARK, WHITE
from . import call_art

CALL_BG = "#f0703a"         # plain-shapes fallback (no Pillow)
CALL_GREY = "#fff1e8"
CALL_RED = "#e5383b"
SILENCE_SECONDS = 8         # show "we can't hear you" after this long without a voice
BAR_COUNT = 64


class CallMixin:
    # ---- artwork (cached PhotoImages) ------------------------------------------------------

    def _call_photo(self, key, make):
        cache = self.__dict__.setdefault("_call_photo_cache", {})
        if key not in cache:
            from PIL import ImageTk
            if len(cache) > 40:
                cache.clear()
            cache[key] = ImageTk.PhotoImage(make(), master=self)
        return cache[key]

    def _art_ok(self):
        import os
        return call_art.available() and not os.environ.get("PILLWAY_PLAIN_SHAPES")

    # ---- the screen ----------------------------------------------------------------------

    def draw_call_preview(self, x1, y1, x2, y2):
        w, h = round(x2 - x1), round(y2 - y1)
        art = self._art_ok()
        if art:
            self.c.create_image(round(x1), round(y1), anchor="nw",
                                image=self._call_photo(("bg", w, h), lambda: call_art.background(w, h)))
        else:
            self.rrect(x1, y1, x2, y2, self.S(8), fill=CALL_BG, outline=CALL_BG)
        if not self.record["consent"]["accepted"]:
            self.draw_consent(x1, y1, x2, y2)
            return
        if not self.call_state:
            self._begin_call()
        state = self.call_state
        cx = (x1 + x2) / 2
        self.text(cx, y1 + self.S(36), "Appel Pillway" if self.lang == "fr" else "Pillway call", 14, WHITE, "bold",
                  anchor="center")
        self.text(x2 - self.S(28), y1 + self.S(36), self._call_clock(), 16, WHITE, "bold", anchor="e",
                  tag="call_timer")

        # Sarah
        size = round(min(self.S(170), h * 0.25))
        avatar_y = y1 + self.S(70) + size / 2
        if art:
            closed = self._call_photo(("avatar", size, False), lambda: call_art.avatar(size, False))
            opened = self._call_photo(("avatar", size, True), lambda: call_art.avatar(size, True))
            state["avatar_images"] = (closed, opened)
            self.c.create_image(round(cx), round(avatar_y), image=closed, tags="call_avatar")
        else:
            r = size / 2
            self.circle(self.c, cx - r, avatar_y - r, cx + r, avatar_y + r, fill="#fff6ee")
            self.text(cx, avatar_y, "S", 40, INK, "bold", anchor="center")
        name = get_settings().branding.assistant_name
        name_y = avatar_y + size / 2 + self.S(30)
        self.text(cx, name_y, name, 28, WHITE, "bold", anchor="center")
        self.text(cx, name_y + self.S(30), self._call_status_line(), 14, CALL_GREY, anchor="center",
                  tag="call_status_line")

        # glass control bar
        bar_w = min(self.S(500), w - self.S(260))
        bar_h = self.S(104)
        bar_box = (cx - bar_w / 2, y2 - self.S(40) - bar_h, cx + bar_w / 2, y2 - self.S(40))
        if art:
            local = tuple(round(v - o) for v, o in zip(bar_box, (x1, y1, x1, y1)))
            radius = bar_h / 2
            pad = max(8, round(radius * 0.6))  # call_art.glass adds this much room for the shadow
            photo = self._call_photo(("glass", w, h, local),
                                     lambda: call_art.glass(call_art.background(w, h), local, radius)[0])
            self.c.create_image(round(x1 + local[0] - pad), round(y1 + local[1] - pad), anchor="nw", image=photo)
        else:
            self.rrect(*bar_box, bar_h / 2, fill="#f59a6c", outline="#fbc2a2", width=self.S(1.5))

        # captions sit between the name and the glass bar
        caption_top = name_y + self.S(66)
        self._draw_captions(cx, caption_top, min(self.S(680), w - self.S(120)), bar_box[1] - self.S(20))
        self._draw_call_controls(cx, (bar_box[1] + bar_box[3]) / 2 - self.S(10), x1, x2)

        # your microphone orb, bottom-right with a generous margin
        orb_r = self.S(40)
        reach = orb_r + self.S(46)
        ox, oy = x2 - self.S(40) - reach, y2 - self.S(40) - reach
        state["orb"] = (ox, oy, orb_r)
        self.circle(self.c, ox - orb_r, oy - orb_r, ox + orb_r, oy + orb_r, fill=WHITE, tags="call_orb")
        self.text(ox, oy, initials(self.record), 20, NAVY, "bold", anchor="center", tag="call_orb")
        if state.get("muted"):
            br = self.S(15)
            bx, by = ox + orb_r * 0.72, oy + orb_r * 0.72
            self.circle(self.c, bx - br, by - br, bx + br, by + br, fill=CALL_RED, outline=WHITE,
                        width=self.S(2), tags="call_orb")
            self.draw_icon("mic", bx, by, self.S(15), WHITE, "call_orb_mic", bg=CALL_RED)
            self.c.create_line(bx - self.S(7), by + self.S(7), bx + self.S(7), by - self.S(7), fill=WHITE,
                               width=self.S(2), tags="call_orb")
        self._draw_call_wave()

        self._draw_silence_popup(x2, y1)
        self._update_silence_popup()

    # ---- your voice meter -----------------------------------------------------------------

    def _draw_call_wave(self):
        """The bars around YOUR orb: longer when you speak louder (Sarah has no ring)."""
        state = self.call_state
        if "orb" not in state:  # the call screen hasn't been laid out yet
            return
        ox, oy, r = state["orb"]
        level = 0.0 if state.get("muted") else state.get("level", 0.0)
        smooth = state.get("level_smooth", 0.0)
        smooth = smooth + (level - smooth) * (0.55 if level > smooth else 0.18)  # fast up, slow down
        state["level_smooth"] = smooth
        phase = self.call_elapsed() * 3.1
        inner = r + self.S(7)
        for index in range(BAR_COUNT):
            angle = 2 * math.pi * index / BAR_COUNT - math.pi / 2
            ripple = 0.55 + 0.45 * math.sin(index * 0.83 + phase) * math.sin(index * 0.27 - phase * 0.6)
            length = self.S(3) + smooth * self.S(42) * max(0.15, ripple)
            coords = (ox + math.cos(angle) * inner, oy + math.sin(angle) * inner,
                      ox + math.cos(angle) * (inner + length), oy + math.sin(angle) * (inner + length))
            tag = f"call_bar_{index}"
            if self.c.find_withtag(tag):
                self.c.coords(tag, *coords)
            else:
                self.c.create_line(*coords, fill=WHITE, width=max(1, self.S(2.6)), capstyle="round",
                                   tags=("call_bars", tag))
        # Sarah's mouth moves while she is speaking
        images = state.get("avatar_images")
        if images:
            # lip-sync: only while sound is actually playing, with a slightly irregular rhythm
            t = self.call_elapsed()
            talking = state.get("sarah_audio") and (math.sin(t * 13.0) + 0.6 * math.sin(t * 7.3)) > 0.15
            self.c.itemconfigure("call_avatar", image=images[1 if talking else 0])
        self.c.itemconfigure("call_status_line", text=self._call_status_line())

    def _call_status_line(self):
        state = self.call_state or {}
        fr = self.lang == "fr"
        if state.get("sarah_audio"):
            return "Sarah parle…" if fr else "Speaking…"
        if state.get("muted"):
            return "Votre micro est coupé" if fr else "Your mic is muted"
        if self.patient_id in self.service.busy:
            return "Sarah réfléchit…" if fr else "Sarah is thinking…"
        return "Sarah vous écoute" if fr else "Listening"

    # ---- "we can't hear you" card -----------------------------------------------------------

    def _draw_silence_popup(self, right, top):
        state = self.call_state
        width, height = self.S(330), self.S(118)
        x2, y1 = right - self.S(24), top + self.S(62)
        x1, y2 = x2 - width, y1 + height
        tag = "call_popup"
        self.rrect(x1 + self.S(1), y1 + self.S(3), x2 + self.S(1), y2 + self.S(3), self.S(8), fill="#c9542f",
                   tags=tag)
        self.rrect(x1, y1, x2, y2, self.S(8), fill=WHITE, outline=BORDER, tags=tag)
        r = self.S(17)
        icx, icy = x1 + self.S(30), y1 + self.S(32)
        self.circle(self.c, icx - r, icy - r, icx + r, icy + r, fill=RED_SOFT, tags=tag)
        self.draw_icon("mic", icx, icy, self.S(18), RED, "call_popup", bg=RED_SOFT)
        self.c.create_line(icx - self.S(8), icy + self.S(8), icx + self.S(8), icy - self.S(8), fill=RED,
                           width=self.S(2), tags=tag)
        self.text(x1 + self.S(58), y1 + self.S(28), "", 15, INK, "bold", tag=(tag, "call_popup_title"))
        self.c.create_text(x1 + self.S(58), y1 + self.S(46), text="", anchor="nw", fill=TEXT_DARK,
                           width=width - self.S(74), font=self.font(13), tags=(tag, "call_popup_body"))
        link = "call_popup_link"
        self.text(x1 + self.S(58), y2 - self.S(18), self.t("call.switch_chat"), 13, RED, "bold",
                  tag=(tag, link))
        self.clickable(link, self.switch_call_to_chat)
        self.c.itemconfigure(tag, state="hidden")
        state["popup_shown"] = None

    def _update_silence_popup(self):
        state = self.call_state
        now = time.monotonic()
        if state.get("level", 0) > 0.05 or state.get("sarah_speaking") or self.patient_id in self.service.busy:
            state["last_voice"] = now
        quiet_for = now - state.setdefault("last_voice", now)
        fr = self.lang == "fr"
        if state.get("mic_missing") or state.get("speech_disabled"):
            kind = "missing"
        elif state.get("muted") and quiet_for > SILENCE_SECONDS:
            kind = "muted"
        elif quiet_for > SILENCE_SECONDS:
            kind = "silent"
        else:
            kind = None
        if kind == state.get("popup_shown"):
            return
        state["popup_shown"] = kind
        if kind is None:
            self.c.itemconfigure("call_popup", state="hidden")
            return
        title, body = {
            "missing": (("Micro introuvable", "Vérifiez que votre micro est branché et autorisé, ou passez au clavardage.")
                        if fr else ("No microphone found",
                                    "Check that your mic is plugged in and allowed, or switch to chat.")),
            "muted": (("Votre micro est coupé", "Touchez Activer le micro pour parler à Sarah.")
                      if fr else ("You're on mute", "Tap Unmute to talk to Sarah.")),
            "silent": (("On ne vous entend pas", "Votre micro est peut-être coupé ou ne fonctionne pas.")
                       if fr else ("We can't hear you", "You may be muted, or your microphone isn't working.")),
        }[kind]
        self.c.itemconfigure("call_popup", state="normal")
        self.c.itemconfigure("call_popup_title", text=title)
        self.c.itemconfigure("call_popup_body", text=body)

    # ---- captions and controls ------------------------------------------------------------

    def _draw_captions(self, cx, top, width, bottom):
        """The last two lines of the call, trimmed so they never run into the glass bar."""
        y = top
        for message in self.call_caption_lines()[-2:]:
            mine = message["role"] == "patient"
            colour = "#ffe1d6" if mine else WHITE
            if message.get("tier") == 1:
                colour = "#fff3b0"
            prefix = ("Vous : " if self.lang == "fr" else "You: ") if mine else ""
            if message.get("tier"):
                prefix = "⚑ " + prefix
            # show the AI's corrected reading of what speech recognition heard, when there is one
            text = " ".join((message.get("heard_as") or message["text"]).split())
            room = max(60, int((bottom - y) / self.S(26)) * 62)
            if len(text) > room:
                text = text[:room].rsplit(" ", 1)[0] + "…"
            item = self.c.create_text(cx, y, text=prefix + text, fill=colour, anchor="n", justify="center",
                                      font=self.font(15 if mine else 18, "bold" if message.get("tier") else "normal"),
                                      width=width)
            y = self.c.bbox(item)[3] + self.S(14)
            if y > bottom:
                break

    def _draw_call_controls(self, cx, cy, x1, x2):
        state = self.call_state
        spacing = self.S(118)
        muted = state.get("muted")
        speaker_on = state.get("speaker_enabled", False)
        self._draw_call_control("call_mute", cx - spacing, cy, "mic", solid=muted, action=self.toggle_call_mute,
                                crossed=muted)
        self.text(cx - spacing, cy + self.S(44), self.t("call.unmute") if muted else self.t("call.mute"), 13,
                  WHITE, anchor="center")
        self._draw_call_control("call_speaker", cx, cy, "speaker", solid=False, action=self.toggle_call_speaker,
                                crossed=not speaker_on)
        self.text(cx, cy + self.S(44), self.t("call.speaker") if speaker_on else self.t("call.speaker_off"), 13,
                  WHITE, anchor="center")
        self._draw_call_control("end_call_preview", cx + spacing, cy, "phone", solid=False, red=True,
                                action=self.close_call_preview)
        self.text(cx + spacing, cy + self.S(44), self.t("call.end").capitalize(), 13, WHITE, anchor="center")

    def _draw_call_control(self, tag, cx, cy, icon, solid=False, red=False, action=None, crossed=False):
        """A round button on the glass bar: frosted glass, solid white (on), or red (End)."""
        size = round(self.S(60))
        icon_colour = "#e05a2c" if solid else WHITE
        if self._art_ok():
            fill, alpha, hover_alpha = ((230, 56, 59), 255, 255) if red else (
                ((255, 255, 255), 255, 235) if solid else ((255, 255, 255), 55, 95))
            normal = self._call_photo(("btn", size, fill, alpha), lambda: call_art.glass_circle(size, fill, alpha))
            hover = self._call_photo(("btn", size, fill, hover_alpha, "h"),
                                     lambda: call_art.glass_circle(size, fill, hover_alpha))
            self.c.create_image(round(cx), round(cy), image=normal, tags=(tag, f"{tag}::bg"))
            self.c.tag_bind(tag, "<Enter>", lambda _e: self.c.itemconfigure(f"{tag}::bg", image=hover), add="+")
            self.c.tag_bind(tag, "<Leave>", lambda _e: self.c.itemconfigure(f"{tag}::bg", image=normal), add="+")
            bg = "#e6383b" if red else ("#ffffff" if solid else "#f49166")
        else:
            r = size / 2
            bg = CALL_RED if red else (WHITE if solid else "#f59a6c")
            self.circle(self.c, cx - r, cy - r, cx + r, cy + r, fill=bg, tags=tag)
        self.draw_icon(icon, cx, cy, self.S(24), icon_colour, tag, bg=bg)
        if crossed:
            self.c.create_line(cx - self.S(13), cy + self.S(13), cx + self.S(13), cy - self.S(13),
                               fill=icon_colour, width=self.S(2.6), capstyle="round", tags=tag)
        self.clickable(tag, action)

    def _draw_no_mic_help(self, x1, x2, y2):
        """Kept for old callers: the 'no microphone' message is now the corner card."""

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
