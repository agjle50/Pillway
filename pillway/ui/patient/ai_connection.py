"""Settings > AI connection: connect Sarah to Google Gemini by pasting a Gemini API key.

Called by: PillwayApp.render() for the "AI connection" section (patient and pharmacist).
- Shows whether Sarah is LIVE (real AI conversation) or in DEMO MODE (scripted backup).
- The key is typed into a hidden field (shown as dots) and saved ONLY to
  pillway_config.local.toml, which .gitignore keeps off GitHub. It is never printed or logged.
- "Test connection" sends one tiny request to check the key works.
"""

import re
import tkinter as tk

from config import get_settings
from config.loader import LOCAL_FILE

from ..theme import BORDER, GREEN, GREEN_SOFT, INK, RED, RED_SOFT, TEXT_DARK, TEXT_MUTED, WHITE

KEY_PATTERN = re.compile(r"^AIza[0-9A-Za-z_\-]{30,}$")   # Google API keys start with "AIza"


def save_key_to_local_file(root, key):
    """Write api_key into pillway_config.local.toml (creating it if needed), keeping other settings."""
    path = root / LOCAL_FILE
    line = f'api_key = "{key}"'
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if re.search(r'(?m)^\s*api_key\s*=.*$', text):
        text = re.sub(r'(?m)^\s*api_key\s*=.*$', line, text, count=1)
    elif re.search(r"(?m)^\[ai\]\s*$", text):
        text = re.sub(r"(?m)^\[ai\]\s*$", "[ai]\n" + line, text, count=1)
    else:
        text = (text.rstrip() + "\n\n" if text.strip() else
                "# Your personal settings. This file is in .gitignore: never commit it.\n\n") + "[ai]\n" + line + "\n"
    path.write_text(text, encoding="utf-8")
    return path


class AIConnectionMixin:
    def draw_ai_connection(self):
        y = self.page_title("AI connection", back_to="Settings")
        settings = get_settings()
        x1 = self.sw + self.S(36)
        x2 = min(self.w - self.S(36), x1 + self.S(720))
        live = self.service.brain.live
        status = getattr(self, "ai_connection_status", "")

        # status card
        top = y + self.S(24)
        fill, ink = (GREEN_SOFT, GREEN) if live else (RED_SOFT, RED)
        self.rrect(x1, top, x2, top + self.S(84), self.S(8), fill=fill, outline=fill)
        title = (f"Connected: Sarah is using {settings.ai.chat_model}" if live else
                 "Not connected: Sarah is in demo mode (scripted replies)")
        self.text(x1 + self.S(20), top + self.S(28), title, 16, ink, "bold")
        detail = (f"Natural conversation is {'on' if settings.ai.conversation_style == 'natural' else 'off'}. "
                  f"Key …{settings.api_key[-4:]} from {settings.api_key_source}." if live else
                  self.service.brain.status_note() or "Paste a Gemini API key below to connect.")
        self.text(x1 + self.S(20), top + self.S(58), detail, 13, TEXT_DARK)

        # key field
        y = top + self.S(116)
        self.text(x1, y, "Gemini API key", 15, INK, "bold")
        self.text(x1, y + self.S(26), "Create one at aistudio.google.com/apikey (Get API key). It starts with AIza.",
                  13, TEXT_MUTED)
        field_y = y + self.S(50)
        entry = tk.Entry(self, show="•", font=self.font(15), relief="flat", bd=0, bg=WHITE, fg=INK,
                         highlightthickness=1, highlightbackground=BORDER, highlightcolor=INK,
                         insertbackground=INK)
        self.c.create_window(x1, field_y, window=entry, anchor="nw", width=int(x2 - x1), height=int(self.S(46)))
        self.embedded_frames.append(entry)
        self.ai_key_entry = entry

        by = field_y + self.S(66)
        right = self.btn(self.c, x1, by, "Save and connect", self.save_ai_key, kind="primary", size=14,
                         height=self.S(44))
        self.btn(self.c, right + self.S(12), by, "Test connection", self.test_ai_connection, kind="outline",
                 size=14, height=self.S(44))
        if status:
            colour = GREEN if status.startswith("✓") else RED if status.startswith("✕") else TEXT_DARK
            self.c.create_text(x1, by + self.S(66), text=status, anchor="nw", fill=colour, font=self.font(14),
                               width=int(x2 - x1))
        self.c.create_text(
            x1, by + self.S(112), anchor="nw", width=int(x2 - x1), fill=TEXT_MUTED, font=self.font(12),
            text=("The key is saved only in pillway_config.local.toml on this computer. That file is never "
                  "uploaded to GitHub. Never paste your key into chat, email or the shared config file. "
                  "Gemini API use is free up to Google's limits, then billed by Google."))

    def save_ai_key(self):
        key = (self.ai_key_entry.get() if getattr(self, "ai_key_entry", None) else "").strip()
        if not KEY_PATTERN.match(key):
            self.ai_connection_status = "✕ That doesn't look like a Gemini API key (it should start with AIza)."
            self.render()
            return
        settings = get_settings()
        try:
            save_key_to_local_file(settings.root, key)
        except OSError as error:
            self.ai_connection_status = f"✕ Couldn't save the key: {error}"
            self.render()
            return
        settings.api_key, settings.api_key_source = key, LOCAL_FILE
        settings.ai.demo_mode = False
        self._reconnect_ai()
        self.ai_connection_status = "Saved. Testing the connection…"
        self.render()
        self.test_ai_connection()

    def _reconnect_ai(self):
        from ...ai.client import AIClient
        self.service.brain.client = AIClient()

    def test_ai_connection(self):
        client = self.service.brain.client
        if not client.available:
            self.ai_connection_status = "✕ " + (client.unavailable_reason or "No API key yet.")
            self.render()
            return
        self.ai_connection_status = "Testing…"
        self.render()
        model = get_settings().ai.chat_model

        def work():
            try:
                client._sdk.models.generate_content(model=model, contents="Reply with OK.",
                                                    config={"max_output_tokens": 16})
                result = f"✓ Connected. Gemini ({model}) answered. Sarah will now have real conversations."
            except Exception as error:  # wrong key, no internet, quota, model not available...
                text = str(error)
                hint = ("the key was rejected; check you copied all of it" if "API_KEY_INVALID" in text
                        or "API key not valid" in text else
                        f"the model '{model}' isn't available for this key" if "404" in text or "NOT_FOUND" in text
                        else "this key isn't allowed to use Gemini" if "403" in text or "PERMISSION" in text
                        else "the free limit was reached; wait a minute or add billing" if "429" in text
                        or "RESOURCE_EXHAUSTED" in text
                        else "no internet connection" if "connect" in text.lower() or "timed out" in text.lower()
                        else text[:120])
                result = f"✕ Not connected: {hint}."
            self.ai_connection_status = result   # the app redraws when background work finishes
        self.run_in_background(work)
