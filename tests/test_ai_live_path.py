"""Tests the LIVE AI path with a fake Anthropic SDK (no internet, no key, no cost).

Checks: a good AI reply is used; broken JSON is retried; a failed call falls back to demo
mode ("offline") without crashing; an unsafe AI reply is replaced by the safe fallback; the
AI can raise a flag but not clear a Tier 1; and nothing identifying is sent.
"""

import json
import unittest
from types import SimpleNamespace

from tests.helpers import use_temp_settings

use_temp_settings()

from pillway.ai.brain import Brain  # noqa: E402
from pillway.core.conversation_service import ConversationService  # noqa: E402


class FakeSDK:
    """Answers like the Anthropic SDK. `script` is a list of replies or exceptions, by job keyword."""

    def __init__(self, chat=None, flag=None, care_plan=None, fail=False):
        self.calls = []
        self.replies = {"chat": chat, "flag": flag, "care_plan": care_plan}
        self.fail = fail
        self.messages = SimpleNamespace(create=self.create)

    def create(self, **request):
        self.calls.append(request)
        if self.fail:
            raise TimeoutError("network down")
        system = request["system"][0]["text"]
        job = "flag" if "second safety check" in system else "care_plan" if "lifestyle parts" in system else "chat"
        reply = self.replies[job]
        text = reply.pop(0) if isinstance(reply, list) else reply
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


def live_service(sdk):
    settings = use_temp_settings(demo_mode=False)
    settings.api_key = "sk-ant-test-key-1234"
    brain = Brain()
    brain.client._sdk = sdk
    service = ConversationService(brain=brain)
    service.accept_consent("maria")
    return service


GOOD_CHAT = json.dumps({"advice": "Lovely, Patient A. Keeping meals regular helps your blood sugar.",
                        "possible_issues": [], "summary_updates": [], "medication_question": False,
                        "needs_pharmacist": False})
NO_FLAG = json.dumps({"is_concern": False, "tier": None, "reason": "", "ask_next": ""})


class LiveAIPathTests(unittest.TestCase):
    def test_good_ai_reply_is_used_and_name_restored(self):
        sdk = FakeSDK(chat=GOOD_CHAT, flag=NO_FLAG)
        service = live_service(sdk)
        for text in ["hi", "no changes", "I eat pretty well"]:
            record = service.handle_message("maria", text)
        last = record["messages"][-1]
        self.assertEqual(last["source"], "ai")
        self.assertIn("Lovely, Maria.", last["text"])
        self.assertIn("limit protein", last["text"])  # the app still adds the protein question
        sent = json.dumps(sdk.calls)
        for identifier in ("Rossi", "555-0198", "maria.demo@example.com", "1234-567-890-AB"):
            self.assertNotIn(identifier, sent)

    def test_broken_json_is_retried(self):
        sdk = FakeSDK(chat=["not json at all", GOOD_CHAT[1:]], flag=NO_FLAG)
        service = live_service(sdk)
        for text in ["hi", "no changes", "I eat pretty well"]:
            record = service.handle_message("maria", text)
        self.assertEqual(record["messages"][-1]["source"], "ai")

    def test_network_failure_falls_back_to_offline_demo(self):
        service = live_service(FakeSDK(fail=True))
        for text in ["hi", "no changes", "I eat pretty well"]:
            record = service.handle_message("maria", text)
        self.assertEqual(record["messages"][-1]["source"], "offline")
        record = service.handle_message("maria", "my foot doesn't hurt")
        self.assertTrue(record["flags"])  # negated danger word + AI down = amber check, never silent

    def test_unsafe_ai_reply_is_replaced(self):
        bad = json.dumps({"advice": "You should stop taking your metformin until the dizziness passes.",
                          "possible_issues": [], "summary_updates": []})
        service = live_service(FakeSDK(chat=bad, flag=NO_FLAG))
        for text in ["hi", "no changes", "I eat pretty well"]:
            record = service.handle_message("maria", text)
        last = record["messages"][-1]["text"]
        self.assertNotIn("stop taking", last)
        self.assertIn("great question for your pharmacist", last)

    def test_ai_cannot_clear_urgent_foot_flag(self):
        service = live_service(FakeSDK(chat=GOOD_CHAT, flag=NO_FLAG))
        service.handle_message("maria", "hi")
        record = service.handle_message("maria", "I have a sore on my foot that won't heal")
        self.assertEqual(record["flags"][-1]["tier"], 1)

    def test_ai_flag_catches_what_words_miss(self):
        raise_flag = json.dumps({"is_concern": True, "tier": 1, "reason": "Toe colour change.", "ask_next": "Since when?"})
        service = live_service(FakeSDK(chat=GOOD_CHAT, flag=[NO_FLAG, raise_flag]))
        service.handle_message("maria", "hi")
        record = service.handle_message("maria", "my big toe went a strange dark colour")
        self.assertEqual(record["flags"][-1]["tier"], 1)
        self.assertEqual(record["flags"][-1]["ai_reason"], "Toe colour change.")
        self.assertIn("A pharmacist will contact you soon", record["messages"][-1]["text"])
        self.assertEqual([m for m in record["messages"] if m["role"] == "patient"][-1]["tier"], 1)


if __name__ == "__main__":
    unittest.main()
