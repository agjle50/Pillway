"""Settings > AI connection: connect Sarah to the AI (DeepSeek by default, or Gemini) by pasting a key.

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

# What a key looks like for each company. DeepSeek keys start with "sk-", Google keys with "AIza".
KEY_PATTERNS = {"deepseek": re.compile(r"^sk-[0-9A-Za-z]{20,}$"),
                "gemini": re.compile(r"^AIza[0-9A-Za-z_\-]{30,}$")}
KEY_PATTERN = KEY_PATTERNS["gemini"]   # kept for older code and tests
KEY_HELP = {"deepseek": ("DeepSeek API key", "Create one at platform.deepseek.com/api_keys. It starts with sk-.",
                         "DeepSeek API use is pay-as-you-go: top up your balance at platform.deepseek.com."),
            "gemini": ("Gemini API key", "Create one at aistudio.google.com/apikey (Get API key). It starts with AIza.",
                       "Gemini API use is free up to Google's limits, then billed by Google.")}


def connection_hint(text, model, provider):
    """Turn a failed test call into a plain-English reason."""
    low = text.lower()
    if "401" in text or "api_key_invalid" in low or "api key not valid" in low:
        return "the key was rejected; check you copied all of it"
    if "402" in text:
        return "the DeepSeek account has no balance left; top up at platform.deepseek.com"
    if "422" in text or "404" in text or "not_found" in low or "model" in low and "400" in text:
        return f"the model '{model}' isn't available for this key"
    if "403" in text or "permission" in low:
        return f"this key isn't allowed to use {'DeepSeek' if provider == 'deepseek' else 'Gemini'}"
    if "429" in text or "resource_exhausted" in low:
        return "too many requests; wait a minute" + (" or add billing" if provider == "gemini" else "")
    if "connect" in low or "timed out" in low or "reach" in low:
        return "no internet connection"
    return text[:120]


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
        from ...ai.client import PROVIDER_NAMES, model_for
        provider = settings.ai.provider
        label, help_text, billing = KEY_HELP[provider]
        title = (f"Connected: Sarah is using {PROVIDER_NAMES[provider]} ({model_for('chat', settings.ai)})" if live else
                 "Not connected: Sarah is in demo mode (scripted replies)")
        self.text(x1 + self.S(20), top + self.S(28), title, 16, ink, "bold")
        detail = (f"Natural conversation is {'on' if settings.ai.conversation_style == 'natural' else 'off'}. "
                  f"Key …{settings.api_key[-4:]} from {settings.api_key_source}." if live else
                  self.service.brain.status_note() or f"Paste a {label} below to connect.")
        self.text(x1 + self.S(20), top + self.S(58), detail, 13, TEXT_DARK)

        # key field
        y = top + self.S(116)
        self.text(x1, y, label, 15, INK, "bold")
        self.text(x1, y + self.S(26), help_text, 13, TEXT_MUTED)
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
                  + billing))

    def save_ai_key(self):
        key = (self.ai_key_entry.get() if getattr(self, "ai_key_entry", None) else "").strip()
        provider = get_settings().ai.provider
        if not KEY_PATTERNS[provider].match(key):
            start = "sk-" if provider == "deepseek" else "AIza"
            self.ai_connection_status = f"✕ That doesn't look like a {KEY_HELP[provider][0]} (it should start with {start})."
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
        from ...ai.client import PROVIDER_NAMES, model_for
        settings = get_settings()
        provider, model = settings.ai.provider, model_for("chat", settings.ai)

        def work():
            try:
                client._sdk.models.generate_content(model=model, contents="Reply with OK.",
                                                    config={"max_output_tokens": 16})
                result = (f"✓ Connected. {PROVIDER_NAMES[provider]} ({model}) answered. "
                          "Sarah will now have real conversations.")
            except Exception as error:  # wrong key, no internet, no balance, model not available...
                result = f"✕ Not connected: {connection_hint(str(error), model, provider)}."
            self.ai_connection_status = result   # the app redraws when background work finishes
        self.run_in_background(work)
