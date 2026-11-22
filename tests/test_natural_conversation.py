"""Natural conversation mode: the AI writes Sarah's whole reply, with code-side safety kept.

Uses a fake Anthropic SDK (no internet, no key, no cost).
"""

import json
import time
import unittest
from types import SimpleNamespace

from tests.helpers import use_temp_settings

use_temp_settings()

from pillway.ai.brain import Brain  # noqa: E402
from pillway.core.conversation_service import ConversationService  # noqa: E402

NO_FLAG = json.dumps({"is_concern": False, "tier": None, "reason": "", "ask_next": ""})


def talk(reply, **extra):
    data = {"reply": reply, "heard_as": "", "answered": [], "asking": None, "small_talk": False,
            "finished": False, "possible_issues": [], "summary_updates": [], "medication_question": False}
    data.update(extra)
    return json.dumps(data)


class FakeSDK:
    def __init__(self, conversation, memory="Patient A: likes hockey."):
        self.calls, self.conversation, self.memory = [], list(conversation), memory
        self.messages = SimpleNamespace(create=self.create)

    def create(self, **request):
        self.calls.append(request)
        system = request["system"][0]["text"]
        if "second safety check" in system:
            text = NO_FLAG
        elif "compact memory" in system:
            text = json.dumps({"memory": self.memory})
        elif "How this conversation works" in system:
            text = self.conversation.pop(0)
        else:  # scripted fallback paragraph
            text = json.dumps({"advice": "Thanks for telling me that, Patient A.", "possible_issues": [],
                               "summary_updates": []})
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


def natural_service(sdk):
    settings = use_temp_settings(demo_mode=False)
    settings.api_key = "sk-ant-test-key-1234"
    settings.ai.conversation_style = "natural"
    brain = Brain()
    brain.client._sdk = sdk
    service = ConversationService(brain=brain)
    service.accept_consent("maria")
    service.handle_message("maria", "hi")          # scripted greeting + intake summary
    return service


class NaturalConversationTests(unittest.TestCase):
    def test_small_talk_gets_a_real_reply_and_no_canned_question(self):
        sdk = FakeSDK([talk("Oh nice, a Leafs fan! Did you watch the whole game, Patient A?", small_talk=True)])
        service = natural_service(sdk)
        record = service.handle_message("maria", "the leafs won last night!")
        last = record["messages"][-1]
        self.assertEqual(last["source"], "ai")
        self.assertEqual(last["text"], "Oh nice, a Leafs fan! Did you watch the whole game, Maria?")
        self.assertEqual(record["conversation"]["stage"], "changes")   # nothing skipped

    def test_answers_are_recorded_and_the_next_question_is_the_ais_own_words(self):
        sdk = FakeSDK([
            talk("Good to hear nothing's changed. So, how do you feel about what you eat day to day?",
                 answered=[{"id": "changes", "value": "no"}], asking="diet"),
            talk("That's a solid routine. Has a doctor ever asked you to cut back on protein?",
                 answered=[{"id": "diet", "value": "pretty well"}], asking="protein_limit"),
        ])
        service = natural_service(sdk)
        record = service.handle_message("maria", "nope nothing new")
        self.assertEqual(record["conversation"]["stage"], "questions")
        record = service.handle_message("maria", "I eat pretty well honestly")
        self.assertIn("diet", record["conversation"]["answers"])
        self.assertEqual(record["conversation"]["question_index"], 1)          # protein_limit next
        last = record["messages"][-1]
        self.assertTrue(last["text"].startswith("That's a solid routine."))
        self.assertTrue(last["quick"])                                         # chips for the question asked

    def test_a_corrected_transcript_still_triggers_the_urgent_safety_flag(self):
        sdk = FakeSDK([talk("Thanks for telling me.",
                            heard_as="the sore on my heel won't heal and my toes are numb")])
        service = natural_service(sdk)
        record = service.handle_message("maria", "the soar on my heal wont heel and my tows are num", channel="call")
        self.assertTrue(any(flag["tier"] == 1 for flag in record["flags"]))
        self.assertEqual(record["messages"][-1]["about_tier"], 1)               # urgent reply from code

    def test_unsafe_reply_falls_back_to_the_scripted_path(self):
        sdk = FakeSDK([talk("You should stop taking your metformin for a few days.")])
        service = natural_service(sdk)
        record = service.handle_message("maria", "I feel dizzy sometimes")
        self.assertNotIn("stop taking", record["messages"][-1]["text"])

    def test_memory_is_updated_in_the_background(self):
        sdk = FakeSDK([talk("Ha, love that.", small_talk=True)], memory="Patient A: big hockey fan.")
        service = natural_service(sdk)
        service.handle_message("maria", "the leafs won!")
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and not service.store.load("maria").get("memory"):
            time.sleep(0.05)
        self.assertEqual(service.store.load("maria")["memory"]["text"], "Patient A: big hockey fan.")
        prompt = next(c for c in sdk.calls if "compact memory" in c["system"][0]["text"])
        self.assertNotIn("Rossi", json.dumps(prompt))                          # de-identified

    def test_memory_is_sent_before_the_reply(self):
        sdk = FakeSDK([talk("Hi again!"), talk("Sure thing.")], memory="Patient A: granddaughter Lily, 6.")
        service = natural_service(sdk)
        service.handle_message("maria", "hello")
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and not service.store.load("maria").get("memory"):
            time.sleep(0.05)
        service.handle_message("maria", "ok")
        convo_calls = [c for c in sdk.calls if "How this conversation works" in c["system"][0]["text"]]
        self.assertIn("granddaughter Lily", convo_calls[-1]["messages"][0]["content"])


if __name__ == "__main__":
    unittest.main()
