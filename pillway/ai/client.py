"""The ONLY file that talks to the AI company's API (Anthropic).

Called by: ai/brain.py. Everything else goes through the brain, so demo mode and the real
API are interchangeable.
- The model for each job (chat, flag, care_plan, summary) comes from pillway_config.toml.
- Every outgoing message is de-identified here as a last safety net (core/deidentify.py).
- Timeouts, retries and plain-English errors; never prints or logs the API key.
- Runs in a background thread (the UI never calls this directly).
"""

import time

from config import get_settings

from ..core.deidentify import redact_text
from .parsers import InvalidAIOutput, parse

OK, UNAVAILABLE = "ok", "unavailable"


class AIClient:
    def __init__(self):
        self.settings = get_settings()
        self.last_payload = None
        self.timings = []
        self.unavailable_reason = ""
        self._sdk = None
        if self.settings.ai.demo_mode:
            self.unavailable_reason = "Demo mode is on (scripted replies, no AI)."
        elif not self.settings.api_key:
            self.unavailable_reason = "No API key found, so the app is using demo mode."
        else:
            try:
                import anthropic
                self._sdk = anthropic.Anthropic(api_key=self.settings.api_key,
                                                timeout=self.settings.ai.timeout_seconds, max_retries=0)
            except ImportError:
                self.unavailable_reason = "The 'anthropic' package isn't installed (pip install -r requirements.txt)."

    @property
    def available(self):
        return self._sdk is not None

    def build_request(self, job, system_text, user_text, profile=None):
        """The exact request that would be sent (used by --show-ai-payload too)."""
        ai = self.settings.ai
        if ai.deidentify_before_ai:
            user_text = redact_text(user_text, profile or {})
        system = [{"type": "text", "text": system_text}]
        if ai.prompt_caching:
            system[0]["cache_control"] = {"type": "ephemeral"}
        return {"model": getattr(ai, f"{job}_model"), "max_tokens": ai.max_tokens,
                "temperature": ai.temperature, "system": system,
                "messages": [{"role": "user", "content": user_text}]}

    def complete(self, job, system_text, user_text, schema, profile=None):
        """Ask the AI and return (clean_json, status). status is "ok" or "unavailable"."""
        if not self.available:
            return None, UNAVAILABLE
        request = self.build_request(job, system_text, user_text, profile)
        self.last_payload = request
        for attempt in range(self.settings.ai.retries + 1):
            started = time.monotonic()
            try:
                text = self._send(request)
                data = parse(text, schema)
                self._log_timing(job, started, "ok")
                return data, OK
            except InvalidAIOutput as problem:
                self._log_timing(job, started, f"invalid JSON ({problem})")
                request = dict(request, messages=request["messages"] + [
                    {"role": "assistant", "content": "{"},
                ]) if attempt == 0 else request
            except Exception as error:  # network, timeout, rate limit, server error
                self._log_timing(job, started, f"error: {type(error).__name__}")
                if attempt >= self.settings.ai.retries:
                    break
                time.sleep(0.6)
        return None, UNAVAILABLE

    def _send(self, request):
        try:
            response = self._sdk.messages.create(**request)
        except Exception as error:
            if "temperature" in str(error).lower():
                request = {k: v for k, v in request.items() if k != "temperature"}
                response = self._sdk.messages.create(**request)
            else:
                raise
        text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
        if request["messages"][-1]["role"] == "assistant":
            text = request["messages"][-1]["content"] + text
        return text

    def _log_timing(self, job, started, outcome):
        seconds = round(time.monotonic() - started, 2)
        self.timings.append({"job": job, "seconds": seconds, "outcome": outcome})
        if self.settings.dev.dev_mode:
            print(f"[AI] {job}: {seconds}s ({outcome})")
