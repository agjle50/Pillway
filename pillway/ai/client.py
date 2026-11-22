"""The ONLY file that talks to the AI company's API: DeepSeek (default) or Google Gemini.

Called by: ai/brain.py. Everything else goes through the brain, so demo mode and the real
API are interchangeable.
- Which company: `provider = "deepseek"` or `"gemini"` in pillway_config.toml. That one line is
  enough: if a job's model name belongs to the other company, that company's default model for
  the job is used instead (PROVIDER_MODELS below).
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
CARE_PLAN_TIMEOUT_SECONDS = 60   # the care plan is written once, after the chat: it may take longer
THINKING_TOKENS = 6000      # when a model "thinks", its thinking counts toward max_tokens: leave room
RATE_LIMIT_WORDS = ("429", "resource_exhausted", "quota", "rate limit", "too many requests")
KEY_LIKE = re.compile(r"AIza[0-9A-Za-z_\-]{10,}|sk-[0-9A-Za-z]{10,}")

# Default model per job for each company. A job uses the model from pillway_config.toml when that
# model belongs to the chosen provider; otherwise the default below (so switching is one line).
PROVIDER_MODELS = {
    "deepseek": {"chat": "deepseek-flash", "call": "deepseek-flash", "flag": "deepseek-flash",
                 "memory": "deepseek-flash", "summary": "deepseek-flash", "care_plan": "deepseek-v4-pro"},
    "gemini": {"chat": "gemini-3.8-flash", "call": "gemini-3.5-flash-lite", "flag": "gemini-3.5-flash-lite",
               "memory": "gemini-3.5-flash-lite", "summary": "gemini-3.8-flash", "care_plan": "gemini-3.8-flash"},
}
PROVIDER_NAMES = {"deepseek": "DeepSeek", "gemini": "Gemini"}


def model_for(job, ai):
    """The model a job uses: the configured one if it belongs to the provider, else its default."""
    configured = getattr(ai, f"{job}_model", "") or ""
    if configured.lower().startswith(ai.provider):
        return configured
    return PROVIDER_MODELS[ai.provider][job]


def key_problem(provider, key):
    """A plain-English problem if the saved key clearly belongs to the other company."""
    if provider == "deepseek" and key.startswith("AIza"):
        return "Your saved key is a Google Gemini key. DeepSeek needs a DeepSeek key (it starts with sk-)."
    if provider == "gemini" and key.startswith("sk-"):
        return "Your saved key looks like a DeepSeek key. Gemini needs a Google key (it starts with AIza)."
    return ""


class AIClient:
    def __init__(self):
        self.settings = get_settings()
        self.last_payload = None
        self.timings = []
        self.last_error = ""        # plain-English reason for the last failure (shown in the terminal)
        self._cool_until = {}       # model -> time when the AI company's "too many requests" pause ends
        self.unavailable_reason = ""
        self._sdk = None
        if self.settings.ai.demo_mode:
            self.unavailable_reason = "Demo mode is on (scripted replies, no AI)."
        elif not self.settings.api_key:
            name = PROVIDER_NAMES[self.settings.ai.provider]
            self.unavailable_reason = f"No {name} API key found, so the app is using demo mode."
        elif key_problem(self.settings.ai.provider, self.settings.api_key):
            self.unavailable_reason = key_problem(self.settings.ai.provider, self.settings.api_key)
        elif self.settings.ai.provider == "deepseek":
            from .deepseek import DeepSeekClient
            self._sdk = DeepSeekClient(self.settings.api_key, self.settings.ai.timeout_seconds)
        else:
            try:
                from google import genai
                timeout_ms = self.settings.ai.timeout_seconds * 1000
                self._sdk = genai.Client(api_key=self.settings.api_key, http_options={"timeout": timeout_ms})
            except ImportError:
                self.unavailable_reason = "The 'google-genai' package isn't installed (pip install google-genai)."

    @property
    def available(self):
        return self._sdk is not None

    def build_request(self, job, system_text, user_text, profile=None):
        """The exact request that would be sent (used by --show-ai-payload too)."""
        ai = self.settings.ai
        if ai.deidentify_before_ai:
            user_text = redact_text(user_text, profile or {})
        model = model_for(job, ai)
        if ai.provider == "deepseek":
            # DeepSeek thinks by default (slow). Only the care plan may think; everything else is "off".
            thinking = ai.care_plan_thinking if job == "care_plan" else (
                "off" if job in FAST_JOBS else ai.thinking_level)
        else:
            # "minimal" thinking is only offered on Flash-Lite; everything else uses the configured level.
            thinking = "minimal" if job in FAST_JOBS and "lite" in model else (
                "low" if ai.thinking_level == "off" else ai.thinking_level)
        timeout = (min(ai.timeout_seconds, CALL_TIMEOUT_SECONDS) if job == "call" else
                   max(ai.timeout_seconds, CARE_PLAN_TIMEOUT_SECONDS) if job == "care_plan" else None)
        max_tokens = ai.max_tokens + (THINKING_TOKENS if thinking not in ("off", "minimal") else 0)
        return {"model": model, "system": system_text, "contents": user_text,
                "max_output_tokens": max_tokens, "thinking_level": thinking, "timeout_seconds": timeout}

    def complete(self, job, system_text, user_text, schema, profile=None):
        """Ask the AI and return (clean_json, status). status is "ok" or "unavailable"."""
        if not self.available:
            return None, UNAVAILABLE
        request = self.build_request(job, system_text, user_text, profile)
        self.last_payload = request
        model = request["model"]
        if time.monotonic() < self._cool_until.get(model, 0):
            from .. import debug_log
            debug_log.log("ai", f"{job} skipped: rate-limit pause, using backup lines", model=model)
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
                    self._report(job, started, f"{PROVIDER_NAMES.get(self.settings.ai.provider, 'AI')} rate limit "
                                               f"reached for {model}; "
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
        outcome = f"{PROVIDER_NAMES.get(self.settings.ai.provider, '')} {outcome}".strip()
        from .. import debug_log
        debug_log.log("ai", f"{job} reply", seconds=seconds, outcome=outcome)


def _retry_seconds(text):
    """The error often says how long to wait ("retry in 12.3s"); otherwise pause 20 seconds."""
    match = re.search(r"retry(?:_delay)?[^0-9]{0,20}([0-9]+(?:\.[0-9]+)?)\s*s", text, re.IGNORECASE)
    return min(60, max(5, round(float(match.group(1))))) if match else 20
