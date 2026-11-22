"""Free Gemini tier: a "429 too many requests" answer must fall back to the guide lines at once,
pause that model for a little while (no hammering), and never print the key."""

import io
import time
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace

from tests.helpers import use_temp_settings

use_temp_settings()

from pillway.ai.client import AIClient, _retry_seconds  # noqa: E402
from pillway.ai.parsers import InvalidAIOutput  # noqa: E402,F401


class RateLimitedSDK:
    def __init__(self):
        self.calls = 0
        self.models = SimpleNamespace(generate_content=self.generate_content)

    def generate_content(self, model, contents, config):
        self.calls += 1
        raise RuntimeError("429 RESOURCE_EXHAUSTED. key=AIzaSyFAKEFAKEFAKEFAKE1234 Please retry in 7.5s.")


def live_client(sdk):
    settings = use_temp_settings(demo_mode=False)
    settings.api_key = "AIza-test-key-1234"
    client = AIClient()
    client._sdk = sdk
    return client


class RateLimitTests(unittest.TestCase):
    def test_rate_limit_fails_fast_once_then_pauses_the_model(self):
        sdk = RateLimitedSDK()
        client = live_client(sdk)
        out = io.StringIO()
        with redirect_stdout(out):
            started = time.monotonic()
            first = client.complete("chat", "system", "hello", "reply")
            second = client.complete("chat", "system", "hello again", "reply")
        self.assertEqual(first, (None, "unavailable"))
        self.assertEqual(second, (None, "unavailable"))
        self.assertEqual(sdk.calls, 1)                    # no instant retry, no second request in the pause
        self.assertLess(time.monotonic() - started, 0.5)  # the patient isn't kept waiting
        self.assertIn("free-tier limit", out.getvalue())
        self.assertNotIn("AIzaSyFAKE", out.getvalue())    # the key is never printed
        self.assertNotIn("AIzaSyFAKE", client.last_error)

    def test_retry_delay_is_read_from_google_message(self):
        self.assertEqual(_retry_seconds("Please retry in 7.5s."), 8)
        self.assertEqual(_retry_seconds("no hint here"), 20)

    def test_calls_use_a_short_timeout(self):
        client = live_client(RateLimitedSDK())
        self.assertEqual(client.build_request("call", "s", "u")["timeout_seconds"], 10)
        self.assertIsNone(client.build_request("chat", "s", "u")["timeout_seconds"])


if __name__ == "__main__":
    unittest.main()
