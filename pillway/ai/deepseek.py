"""Talks to DeepSeek's API (https://api-docs.deepseek.com). Standard library only: nothing to install.

Called by: ai/client.py when `provider = "deepseek"` in pillway_config.toml.
It offers the same small interface the Gemini SDK had (`.models.generate_content(...)` returning
an object with `.text`), so the rest of the app, the tests and the offline fallback don't change.

What the DeepSeek docs say, and how we follow it (plain words):
  * One endpoint: POST https://api.deepseek.com/chat/completions, key sent as
    "Authorization: Bearer <key>". Request/response look like OpenAI's chat API.
  * Models: "deepseek-flash" (fast, cheap) and "deepseek-v4-pro" (stronger, slower, dearer).
  * JSON Output: we send response_format {"type": "json_object"}. The docs require the word
    "json" in the prompt (all of Sarah's prompts say "Answer ONLY with JSON"; we add a line
    if one ever doesn't), and warn the reply can come back BLANK: we treat blank as a bad
    reply so the client retries once and then uses the offline backup.
  * Thinking mode is ON by default and makes replies slower. Chats, calls and safety checks
    turn it off ({"thinking": {"type": "disabled"}}); the care plan may think a little
    ({"thinking": {"type": "enabled"}} + reasoning_effort "low"/"high").
  * Errors: 401 wrong key, 402 no balance left, 422/400 bad request, 429 too many requests,
    500/503 server busy. We raise them with the code in the message so the client can react
    (429 -> short pause, then backup lines).
"""

import json
import ssl
import urllib.error
import urllib.request
from types import SimpleNamespace

BASE_URL = "https://api.deepseek.com"
ENDPOINT = "/chat/completions"
MODELS = ("deepseek-flash", "deepseek-v4-pro")
ERRORS = {
    400: "the request was not in the right format",
    401: "the API key was rejected (check you copied all of it)",
    402: "the DeepSeek account has no balance left (top up at platform.deepseek.com)",
    422: "a setting in the request is not valid (check the model name)",
    429: "too many requests right now (rate limit)",
    500: "DeepSeek had a server problem",
    502: "DeepSeek (or the network on the way) had a gateway error",
    503: "DeepSeek is overloaded right now",
    504: "DeepSeek took too long to answer (gateway timeout)",
}


def _ssl_context():
    """Use certifi's certificates when available (python.org Python on Mac often lacks them).

    If SSL_CERT_FILE is set (company networks, proxies), Python's normal lookup honours it instead.
    """
    import os
    if os.environ.get("SSL_CERT_FILE"):
        return ssl.create_default_context()
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def build_body(model, system_text, user_text, max_tokens, thinking="off", json_mode=True):
    """The JSON body DeepSeek receives (kept separate so tests and --show-ai-payload can see it)."""
    if json_mode and "json" not in (system_text + user_text).lower():
        system_text += "\n\nAnswer with one json object."
    body = {"model": model,
            "messages": [{"role": "system", "content": system_text}, {"role": "user", "content": user_text}],
            "max_tokens": int(max_tokens), "stream": False}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    if thinking in (None, "off", "minimal"):
        body["thinking"] = {"type": "disabled"}
    else:
        body["thinking"] = {"type": "enabled"}
        body["reasoning_effort"] = "low" if thinking == "low" else "high"
    return body


def read_reply(data):
    """The answer text from DeepSeek's response JSON. Raises ValueError if there's nothing usable."""
    choice = (data.get("choices") or [{}])[0]
    text = ((choice.get("message") or {}).get("content") or "").strip()
    reason = choice.get("finish_reason")
    if reason == "length":
        raise ValueError("the reply was cut off (max_tokens too small)")
    if reason in ("content_filter", "insufficient_system_resource"):
        raise ValueError(f"DeepSeek stopped early ({reason})")
    return text   # may be "" (blank JSON reply, see the docs): the parser treats that as a bad reply


class DeepSeekClient:
    """Drop-in for the old Gemini SDK object: client.models.generate_content(model, contents, config)."""

    def __init__(self, api_key, timeout_seconds=20, base_url=BASE_URL):
        self._key = api_key
        self.timeout = timeout_seconds
        self.base_url = base_url.rstrip("/")
        self.models = SimpleNamespace(generate_content=self.generate_content)

    def generate_content(self, model, contents, config):
        system = config.get("system_instruction") or ""
        thinking = (config.get("thinking_config") or {}).get("thinking_level", "off")
        timeout = ((config.get("http_options") or {}).get("timeout") or self.timeout * 1000) / 1000
        json_mode = config.get("response_mime_type") == "application/json"
        body = build_body(model, system, contents, config.get("max_output_tokens", 1024), thinking, json_mode)
        return SimpleNamespace(text=read_reply(self.post(body, timeout)))

    def post(self, body, timeout):
        request = urllib.request.Request(
            self.base_url + ENDPOINT, data=json.dumps(body).encode("utf-8"), method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json",
                     "Authorization": f"Bearer {self._key}"})
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=_ssl_context()) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = ""
            try:
                detail = json.loads(error.read().decode("utf-8", "replace")).get("error", {}).get("message", "")
            except Exception:
                pass
            meaning = ERRORS.get(error.code, "unexpected error")
            raise RuntimeError(f"{error.code} {meaning}" + (f": {detail[:160]}" if detail else "")) from None
        except urllib.error.URLError as error:
            raise ConnectionError(f"couldn't reach DeepSeek ({error.reason})") from None

    def __repr__(self):   # never show the key, even in a debugger or error report
        return "DeepSeekClient(key=…%s)" % (self._key[-4:] if self._key else "none")
