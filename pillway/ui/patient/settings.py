"""Settings page and the generic page title / placeholder page.

Called by: PillwayApp.render() for Settings and any section without its own screen.
"""

import queue
from textwrap import shorten

from config import get_settings

from ...storage import app_state
from ...storage.paths import data_folder
from ...voice.speech_input import LocalSpeechInput, input_devices, resolve_input_device
from ..theme import (RED_TEXT, 
    RED,
    BORDER,
    INK,
    TEXT_MUTED,
    WHITE,
)
from ..navigation import SETTINGS_ITEMS


class SettingsMixin:
    def page_title(self, title, back_to="Dashboard"):
        y = self.S(120)
        self.c.create_rectangle(self.sw + self.S(18), y - self.S(20), self.sw + self.S(56),
                                y + self.S(20), fill=WHITE, outline=WHITE, tags="back")
        self.draw_icon("back", self.sw + self.S(36), y, self.S(26), INK, "back")
        self.clickable("back", lambda: self.go(back_to))
        self.text(self.sw + self.S(70), y, title, 22, INK, tag="page_title")
        self.c.create_line(self.sw + self.S(14), y + self.S(36), self.w - self.S(14), y + self.S(36), fill=BORDER)
        return y + self.S(36)

    def draw_settings(self):
        y = self.page_title("Settings")
        x1 = self.sw + self.S(20)
        x2 = x1 + min(self.S(520), self.w - x1 - self.S(20))
        row = self.S(70)
        for label, icon in SETTINGS_ITEMS:
            tag = f"set::{label.replace(' ', '_')}"
            background_tag = f"{tag}::background"
            self.c.create_rectangle(
                x1, y, x2, y + row, fill=WHITE, outline=WHITE, tags=(tag, background_tag),
            )
            self.draw_icon(icon, x1 + self.S(16), y + row / 2, self.S(26), INK, tag)
            self.text(x1 + self.S(46), y + row / 2, label, 17, INK, tag=tag)
            self.draw_icon("chev_right", x2 - self.S(20), y + row / 2, self.S(16), TEXT_MUTED, tag)
            self.c.create_line(x1, y + row, x2, y + row, fill=BORDER)
            self.clickable(tag, lambda name=label: self.go(name))  # was a dead click
            self.c.tag_bind(
                tag, "<Enter>",
                lambda _event, bg=background_tag: self.c.itemconfigure(bg, fill="#f1f3f7"),
                add="+",
            )
            self.c.tag_bind(
                tag, "<Leave>",
                lambda _event, bg=background_tag: self.c.itemconfigure(bg, fill=WHITE),
                add="+",
            )
            y += row
        if self.role == "pharmacist":
            tag = "set::reset_demo"
            self.rrect(x1, y + self.S(24), x1 + self.S(220), y + self.S(74), self.S(12), fill=RED, outline="", tags=tag)
            self.text(x1 + self.S(110), y + self.S(49), "Reset demo", 15, WHITE, "bold", anchor="center", tag=tag)
            self.text(x1 + self.S(240), y + self.S(49), "Restores Maria to a fresh, newly-enrolled state.", 12, TEXT_MUTED)
            self.clickable(tag, self.reset_demo)

    def draw_microphone_settings(self):
        y = self.page_title("Microphone", back_to="Settings")
        x1, x2 = self.sw + self.S(24), self.w - self.S(24)
        self.text(x1, y + self.S(24), "Choose the input used for voice calls and chat dictation.", 14, TEXT_MUTED)
        y += self.S(48)
        y = self._draw_microphone_test(x1, x2, y)

        try:
            devices = input_devices()
        except RuntimeError as error:
            self.text(x1, y, str(error), 14, RED_TEXT)
            return

        settings = get_settings().call
        try:
            selected = resolve_input_device(settings.microphone_device)
            selection_error = ""
        except (RuntimeError, ValueError, OSError) as error:
            selected = None
            selection_error = f"Current microphone selection is unavailable: {error}"
        try:
            default_index = resolve_input_device()
        except (RuntimeError, ValueError, OSError):
            default_index = None
        if selection_error:
            self.c.create_text(
                x1, y, text=selection_error, fill=RED, font=self.font(12),
                anchor="nw", width=x2 - x1,
            )
            y += self.S(30)

        default_name = next((name for index, name in devices if index == default_index), "Unavailable")
        default_is_selected = not settings.microphone_device and default_index is not None
        y = self._draw_microphone_row(
            x1, x2, y, f"System default — {default_name}", default_is_selected, "mic_device_default",
            lambda: self.set_microphone_device(None),
        )
        for index, name in devices:
            y = self._draw_microphone_row(
                x1, x2, y, f"{index}: {name}", selected == index, f"mic_device_{index}",
                lambda device=index: self.set_microphone_device(device),
            )
        if not devices:
            self.text(x1, y + self.S(12), "No compatible microphone inputs were found.", 14, RED_TEXT)
            y += self.S(38)
        self.c.create_text(
            x1, y + self.S(18),
            text=("The test measures volume only; it does not save audio. If the level stays at zero, "
                  "check your operating system's microphone permissions for desktop apps."),
            fill=TEXT_MUTED, font=self.font(12), anchor="nw", width=x2 - x1,
        )

    def _draw_microphone_test(self, x1, x2, y):
        height = self.S(104)
        self.rrect(x1, y, x2, y + height, self.S(12), fill=WHITE, outline=BORDER)
        self.text(x1 + self.S(16), y + self.S(20), "Test microphone", 14, INK, "bold")
        track_x1, track_x2 = x1 + self.S(16), x2 - self.S(184)
        track_y = y + self.S(54)
        self.c.create_rectangle(
            track_x1, track_y, track_x2, track_y + self.S(12),
            fill="#3a3a3c", outline="#555558", tags="mic_test_track",
        )
        fill_x2 = track_x1 + (track_x2 - track_x1) * self.microphone_test_level
        self.c.create_rectangle(
            track_x1, track_y, fill_x2, track_y + self.S(12),
            fill=self._blend_color("#ff3b30", "#34c759", self.microphone_test_level),
            outline="", tags="mic_test_fill",
        )
        self.c.create_text(
            track_x1, y + self.S(82), text=self.microphone_test_status,
            fill=RED if self.microphone_test_error else TEXT_MUTED,
            font=self.font(11), anchor="w", width=track_x2 - track_x1, tags="mic_test_status",
        )
        tag = "mic_test_toggle"
        button_x1, button_x2 = x2 - self.S(164), x2 - self.S(16)
        self.rrect(
            button_x1, y + self.S(34), button_x2, y + self.S(78), self.S(12),
            fill=RED if self.microphone_test_active else "#eef1f6", outline="", tags=tag,
        )
        self.text(
            (button_x1 + button_x2) / 2, y + self.S(56),
            "Stop test" if self.microphone_test_active else "Start test", 13,
            WHITE if self.microphone_test_active else INK, "bold", anchor="center", tag=tag,
        )
        self.clickable(tag, self.toggle_microphone_test)
        return y + height + self.S(14)

    def toggle_microphone_test(self):
        if self.microphone_test_listener:
            if self.microphone_test_active:
                self.microphone_test_active = False
                self.microphone_test_listener.stop()
                self.microphone_test_status = "Stopping microphone test..."
                self.render()
            return

        try:
            device = resolve_input_device(get_settings().call.microphone_device)
        except (RuntimeError, ValueError, OSError) as error:
            self.microphone_test_error = True
            self.microphone_test_status = str(error)
            self.render()
            return
        self.microphone_test_events = queue.Queue()
        self.microphone_test_listener = LocalSpeechInput(
            data_folder() / "models", self.microphone_test_events, device=device, transcribe=False,
        )
        self.microphone_test_active = True
        self.microphone_test_error = False
        self.microphone_test_level = 0.0
        self.microphone_test_status = "Listening — speak to test the selected input."
        self.render()
        self.microphone_test_listener.start()
        self._mic_test_job = self.after(75, self._poll_microphone_test)

    def _stop_microphone_test(self):
        if self.microphone_test_listener:
            self.microphone_test_listener.stop()
        if self._mic_test_job:
            self.after_cancel(self._mic_test_job)
        self._mic_test_job = None
        self.microphone_test_listener = None
        self.microphone_test_events = None
        self.microphone_test_active = False
        self.microphone_test_level = 0.0
        self.microphone_test_status = ""
        self.microphone_test_error = False

    def _poll_microphone_test(self):
        self._mic_test_job = None
        listener = self.microphone_test_listener
        events = self.microphone_test_events
        if not listener or not events:
            return
        while True:
            try:
                event, value = events.get_nowait()
            except queue.Empty:
                break
            if event == "level":
                self.microphone_test_level = value
                if value > 0.025:
                    self.microphone_test_status = f"Input detected · {round(value * 100)}%"
            elif event == "state" and value == "listening":
                self.microphone_test_status = "Listening — speak to test the selected input."
            elif event == "status":
                self.microphone_test_status = value
            elif event == "error":
                self.microphone_test_error = True
                self.microphone_test_active = False
                self.microphone_test_status = f"Microphone test failed: {value}"

        track = self.c.coords("mic_test_track")
        if track:
            self.c.coords("mic_test_fill", track[0], track[1],
                          track[0] + (track[2] - track[0]) * self.microphone_test_level, track[3])
            self.c.itemconfigure(
                "mic_test_fill",
                fill=self._blend_color("#ff3b30", "#34c759", self.microphone_test_level),
            )
        self.c.itemconfigure(
            "mic_test_status", text=self.microphone_test_status,
            fill=RED if self.microphone_test_error else TEXT_MUTED,
        )

        if not listener.is_alive() and events.empty():
            self.microphone_test_listener = None
            self.microphone_test_events = None
            self.microphone_test_active = False
            if not self.microphone_test_error:
                self.microphone_test_status = "Microphone test stopped."
            self.render()
        elif self.microphone_test_listener:
            self._mic_test_job = self.after(75, self._poll_microphone_test)

    def _draw_microphone_row(self, x1, x2, y, label, selected, tag, action):
        row_height = self.S(48)
        self.c.create_rectangle(
            x1, y, x2, y + row_height, fill="#eef1f6" if selected else WHITE,
            outline=BORDER, tags=(tag,),
        )
        self.c.create_text(
            x1 + self.S(14), y + row_height / 2, text=shorten(label, width=86, placeholder="…"), fill=INK,
            font=self.font(13), anchor="w", width=max(1, x2 - x1 - self.S(70)),
            tags=(tag,),
        )
        if selected:
            self.draw_icon("check", x2 - self.S(22), y + row_height / 2, self.S(18), RED, tag)
        self.clickable(tag, action)
        return y + row_height + self.S(6)

    def set_microphone_device(self, device):
        value = "" if device is None else str(device)
        self._stop_microphone_test()
        try:
            app_state.save(microphone_device=value)
        except OSError as error:
            self.flash(f"Could not save microphone selection: {error}")
            return
        get_settings().call.microphone_device = value
        self.flash("Microphone saved.")

    def draw_placeholder_page(self, title):
        """Show a dedicated destination for sidebar links that are not full workflows yet."""
        y = self.page_title(title)
        cx = (self.sw + self.w) / 2
        coming_soon = {
            "See a doctor": "Doctor appointments are coming soon.",
            "Contact us": "Contact options are coming soon.",
            "Account tour": "The guided account tour is coming soon.",
        }
        if title == "FAQ":
            self._draw_faq_page(y)
            return

        card_width = min(self.S(620), self.w - self.sw - self.S(80))
        card_height = self.S(270)
        card_top = max(y + self.S(45), (y + self.h - card_height) / 2)
        card_bottom = card_top + card_height
        self.rrect(
            cx - card_width / 2, card_top, cx + card_width / 2, card_bottom,
            self.S(18), fill=WHITE, outline=BORDER, width=self.S(1.2),
        )
        self.draw_icon("bulb", cx, card_top + self.S(62), self.S(42), TEXT_MUTED, None)
        self.text(cx, card_top + self.S(120), "Coming soon", 22, INK, "bold", anchor="center")
        self.text(
            cx, card_top + self.S(164), coming_soon.get(
                title, f"{title} isn't part of this demo yet.",
            ), 15, TEXT_MUTED, anchor="center",
        )

    def _draw_faq_page(self, y):
        x1 = self.sw + self.S(36)
        x2 = self.w - self.S(36)
        questions = (
            ("What can Juliez help me with?",
             "Juliez can help you review your check-in and care-plan information. It is not a doctor."),
            ("Who can see my check-in?",
             "Your care team may review your check-in and any request you send to them."),
            ("What if I need medical help now?",
             "For an emergency, call your local emergency number. For non-urgent concerns, contact your care team."),
        )
        y += self.S(30)
        for question, answer in questions:
            question_item = self.c.create_text(
                x1, y, text=question, fill=INK, font=self.font(17, "bold"),
                anchor="nw", width=x2 - x1,
            )
            y = self.c.bbox(question_item)[3] + self.S(8)
            answer_item = self.c.create_text(
                x1, y, text=answer, fill=TEXT_MUTED, font=self.font(14),
                anchor="nw", width=x2 - x1,
            )
            y = self.c.bbox(answer_item)[3] + self.S(24)
