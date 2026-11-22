"""Tests for the DeepSeek connector (no internet, no key, no cost: urlopen is faked)."""

import io
import json
import unittest
import urllib.error
from unittest.mock import patch

from tests.helpers import use_temp_settings

use_temp_settings()

from pillway.ai import deepseek  # noqa: E402
from pillway.ai.client import AIClient, key_problem  # noqa: E402


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def answer(content, finish="stop"):
    return FakeResponse(json.dumps({"choices": [{"message": {"content": content}, "finish_reason": finish}]}).encode())


class DeepSeekRequestTests(unittest.TestCase):
    def test_body_follows_the_docs(self):
        body = deepseek.build_body("deepseek-flash", "Answer ONLY with JSON", "hi", 500, "off")
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertEqual(body["thinking"], {"type": "disabled"})        # fast: no thinking
        self.assertEqual(body["messages"][0]["role"], "system")
        care = deepseek.build_body("deepseek-v4-pro", "Answer ONLY with JSON", "plan", 2000, "low")
        self.assertEqual((care["thinking"], care["reasoning_effort"]), ({"type": "enabled"}, "low"))

    def test_the_word_json_is_always_in_the_prompt(self):
        body = deepseek.build_body("deepseek-flash", "Be kind.", "hello", 100)
        self.assertIn("json", body["messages"][0]["content"].lower())

    def test_request_goes_to_the_documented_endpoint_with_a_bearer_key(self):
        sent = {}

        def fake_urlopen(request, timeout, context):
            sent.update(url=request.full_url, auth=request.get_header("Authorization"),
                        body=json.loads(request.data))
            return answer('{"reply": "Hi"}')
        client = deepseek.DeepSeekClient("sk-test", 5)
        with patch("urllib.request.urlopen", fake_urlopen):
            reply = client.models.generate_content(model="deepseek-flash", contents="hi",
                                                   config={"system_instruction": "Answer with JSON",
                                                           "response_mime_type": "application/json"})
        self.assertEqual(reply.text, '{"reply": "Hi"}')
        self.assertEqual(sent["url"], "https://api.deepseek.com/chat/completions")
        self.assertEqual(sent["auth"], "Bearer sk-test")
        self.assertNotIn("sk-test", repr(client).replace("…test", ""))

    def test_errors_are_explained_and_429_is_a_rate_limit(self):
        def fail(code):
            def fake_urlopen(request, timeout, context):
                raise urllib.error.HTTPError(request.full_url, code, "x", {}, io.BytesIO(b'{"error":{"message":"m"}}'))
            return fake_urlopen
        client = deepseek.DeepSeekClient("sk-test", 5)
        for code, words in ((401, "rejected"), (402, "no balance"), (429, "rate limit")):
            with patch("urllib.request.urlopen", fail(code)), self.assertRaises(RuntimeError) as caught:
                client.post({}, 5)
            self.assertIn(str(code), str(caught.exception))
            self.assertIn(words, str(caught.exception))

    def test_blank_or_cut_off_replies_are_not_trusted(self):
        self.assertEqual(deepseek.read_reply(json.loads(answer("   ").getvalue())), "")
        with self.assertRaises(ValueError):
            deepseek.read_reply(json.loads(answer('{"re', "length").getvalue()))


class ProviderTests(unittest.TestCase):
    def test_a_gemini_key_is_caught_before_any_call(self):
        settings = use_temp_settings(demo_mode=False)
        settings.ai.provider, settings.api_key = "deepseek", "AIza" + "x" * 35
        client = AIClient()
        self.assertFalse(client.available)
        self.assertIn("DeepSeek key", client.unavailable_reason)
        self.assertEqual(key_problem("deepseek", "sk-abc"), "")

    def test_deepseek_is_used_by_default_with_thinking_off_for_chats(self):
        settings = use_temp_settings(demo_mode=False)
        settings.api_key = "sk-" + "a" * 32
        client = AIClient()
        self.assertIsInstance(client._sdk, deepseek.DeepSeekClient)
        self.assertEqual(client.build_request("chat", "s", "u")["thinking_level"], "off")
        self.assertEqual(client.build_request("flag", "s", "u")["model"], "deepseek-flash")
        self.assertEqual(client.build_request("care_plan", "s", "u")["model"], "deepseek-v4-pro")


if __name__ == "__main__":
    unittest.main()


class LiveCarePlanTests(unittest.TestCase):
    def test_the_ai_care_plan_request_is_built_and_used(self):
        """BUG FIX: building the AI's care plan request crashed whenever the live AI was on."""
        from types import SimpleNamespace
        from pillway.ai.brain import Brain
        from pillway.core.conversation_service import ConversationService
        settings = use_temp_settings(demo_mode=False)
        settings.api_key = "sk-" + "a" * 32
        brain = Brain()
        sent = []

        def generate_content(model, contents, config):
            sent.append(contents)
            return SimpleNamespace(text=json.dumps({"smart_goals": [{"en": "Walk 10 minutes after lunch, 5 days a "
                                                                         "week, for 4 weeks.", "fr": "Marchez."}],
                                                    "values": [{"id": "a1c_target", "value": "7.0", "reason": "r"}],
                                                    "recommendations": ["dietitian"], "barrier_plans": []}))
        brain.client._sdk = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
        service = ConversationService(brain=brain)
        service.submit_intake("maria", {"weight": "78", "height": "162", "checks_bp": "yes", "systolic": "142",
                                        "diastolic": "90", "tobacco": "no"})
        record = service.make_care_plan("maria")
        self.assertEqual(record["care_plan"]["source"], "ai")
        self.assertIn("plan_so_far", sent[-1])


class GuidelineRangeTests(unittest.TestCase):
    def test_ai_values_outside_pillways_guideline_are_ignored(self):
        from pillway.core.care_plan import ai_value_ok
        self.assertTrue(ai_value_ok("fibre", "30"))
        self.assertFalse(ai_value_ok("fibre", "25"))           # seen live: below Pillway's 30-50 g
        self.assertFalse(ai_value_ok("alcohol", "5"))
        self.assertTrue(ai_value_ok("bp_target", "130/80"))
        self.assertFalse(ai_value_ok("bp_target", "150/95"))
        self.assertFalse(ai_value_ok("made_up", "1"))

    def test_thinking_gets_room_and_time(self):
        settings = use_temp_settings(demo_mode=False)
        settings.api_key = "sk-" + "a" * 32
        settings.ai.care_plan_thinking = "low"
        request = AIClient().build_request("care_plan", "s", "u")
        self.assertGreater(request["max_output_tokens"], settings.ai.max_tokens)
        self.assertGreaterEqual(request["timeout_seconds"], 60)
