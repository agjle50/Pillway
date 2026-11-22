"""The ONLY file that talks to the AI company's API (Google Gemini, via the google-genai package).

Called by: ai/brain.py. Everything else goes through the brain, so demo mode and the real
API are interchangeable.
- The model for each job (chat, call, flag, memory, care_plan, summary) comes from pillway_config.toml.
- Every outgoing message is de-identified here as a last safety net (core/deidentify.py).
- Replies are requested as JSON; timeouts, a retry, plain-English errors; never prints or logs the key.
- Runs in a background thread (the UI never calls this directly).
"""

import re
import time

from config import get_settings

from ..core.deidentify import redact_text
from .parsers import InvalidAIOutput, parse

OK, UNAVAILABLE = "ok", "unavailable"
FAST_JOBS = ("flag", "memory", "call")   # think as little as possible (calls need speed)
CALL_TIMEOUT_SECONDS = 10   # a voice call can't wait long: fall back to the guide lines quickly
RATE_LIMIT_WORDS = ("429", "resource_exhausted", "quota", "rate limit", "too many requests")
KEY_LIKE = re.compile(r"AIza[0-9A-Za-z_\-]{10,}")


class AIClient:
    def __init__(self):
        self.settings = get_settings()
        self.last_payload = None
        self.timings = []
        self.last_error = ""        # plain-English reason for the last failure (shown in the terminal)
        self._cool_until = {}       # model -> time when Google's "too many requests" pause ends
        self.unavailable_reason = ""
        self._sdk = None
        if self.settings.ai.demo_mode:
            self.unavailable_reason = "Demo mode is on (scripted replies, no AI)."
        elif not self.settings.api_key:
            self.unavailable_reason = "No Gemini API key found, so the app is using demo mode."
        else:
            try:
                from google import genai
                timeout_ms = self.settings.ai.timeout_seconds * 1000
                self._sdk = genai.Client(api_key=self.settings.api_key, http_options={"timeout": timeout_ms})
            except ImportError:
                self.unavailable_reason = "The 'google-genai' package isn't installed (pip install -r requirements.txt)."

    @property
    def available(self):
        return self._sdk is not None

    def build_request(self, job, system_text, user_text, profile=None):
        """The exact request that would be sent (used by --show-ai-payload too)."""
        ai = self.settings.ai
        if ai.deidentify_before_ai:
            user_text = redact_text(user_text, profile or {})
        model = getattr(ai, f"{job}_model")
        # "minimal" thinking is only offered on Flash-Lite; everything else uses the configured level.
        thinking = "minimal" if job in FAST_JOBS and "lite" in model else ai.thinking_level
        return {"model": model, "system": system_text, "contents": user_text,
                "max_output_tokens": ai.max_tokens, "thinking_level": thinking,
                "timeout_seconds": min(ai.timeout_seconds, CALL_TIMEOUT_SECONDS) if job == "call" else None}

    def complete(self, job, system_text, user_text, schema, profile=None):
        """Ask the AI and return (clean_json, status). status is "ok" or "unavailable"."""
        if not self.available:
            return None, UNAVAILABLE
        request = self.build_request(job, system_text, user_text, profile)
        self.last_payload = request
        model = request["model"]
        if time.monotonic() < self._cool_until.get(model, 0):
            return None, UNAVAILABLE   # still inside Google's rate-limit pause: use the backup at once
        for attempt in range(self.settings.ai.retries + 1):
            started = time.monotonic()
            try:
                data = parse(self._send(request), schema)
                self._log_timing(job, started, "ok")
                return data, OK
            except InvalidAIOutput as problem:  # retry once with a firm reminder
                self._log_timing(job, started, f"invalid JSON ({problem})")
                request = dict(request, contents=request["contents"] +
                               "\n\nReply with ONE valid JSON object only, exactly in the shape described.")
            except Exception as error:  # network, timeout, rate limit, server error
                text = KEY_LIKE.sub("[key hidden]", str(error))[:300]
                if any(word in text.lower() for word in RATE_LIMIT_WORDS):
                    wait = _retry_seconds(text)
                    self._cool_until[model] = time.monotonic() + wait
                    self._report(job, started, f"Gemini free-tier limit reached for {model}; "
                                               f"using backup lines for {wait}s. ({text[:120]})")
                    break   # retrying straight away only makes the wait longer
                self._report(job, started, f"{type(error).__name__}: {text[:160]}")
                if attempt >= self.settings.ai.retries or job == "call":
                    break
                time.sleep(0.6)
        return None, UNAVAILABLE

    def _report(self, job, started, reason):
        """Always say why the AI failed (in the terminal), never showing the key."""
        self.last_error = reason
        self._log_timing(job, started, "error")
        print(f"[AI] {job} failed after {round(time.monotonic() - started, 1)}s: {reason}")

    def _send(self, request):
        config = {"system_instruction": request["system"], "max_output_tokens": request["max_output_tokens"],
                  "response_mime_type": "application/json",
                  "thinking_config": {"thinking_level": request["thinking_level"]}}
        if request.get("timeout_seconds"):
            config["http_options"] = {"timeout": int(request["timeout_seconds"] * 1000)}
        try:
            response = self._sdk.models.generate_content(model=request["model"], contents=request["contents"],
                                                         config=config)
        except Exception as error:
            message = str(error).lower()
            if "http_options" in message and "http_options" in config:
                config.pop("http_options")      # an older google-genai: use the normal timeout instead
            elif "thinking" in message:
                config.pop("thinking_config")   # an older model without thinking levels: ask again without
            else:
                raise
            response = self._sdk.models.generate_content(model=request["model"], contents=request["contents"],
                                                         config=config)
        return response.text or ""

    def _log_timing(self, job, started, outcome):
        seconds = round(time.monotonic() - started, 2)
        self.timings.append({"job": job, "seconds": seconds, "outcome": outcome})
        if self.settings.dev.dev_mode:
            print(f"[AI] {job}: {seconds}s ({outcome})")


def _retry_seconds(text):
    """Google often says how long to wait ("retry in 12.3s"); otherwise pause 20 seconds."""
    match = re.search(r"retry(?:_delay)?[^0-9]{0,20}([0-9]+(?:\.[0-9]+)?)\s*s", text, re.IGNORECASE)
    return min(60, max(5, round(float(match.group(1))))) if match else 20
