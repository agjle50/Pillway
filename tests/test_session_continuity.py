import json
import unittest

from tests.helpers import use_temp_settings

use_temp_settings()

from pillway.ai.brain import Brain, patient_context  # noqa: E402
from pillway.core.conversation_service import ConversationService  # noqa: E402
from pillway.storage.patient_store import PatientStore, now_iso  # noqa: E402


class SessionContinuityTests(unittest.TestCase):
    def setUp(self):
        use_temp_settings()
        self.store = PatientStore()
        self.service = ConversationService(store=self.store, brain=Brain())
        self.service.accept_consent("maria")

    def _returning_session(self, language="en"):
        self.store.update("maria", lambda record: record.update(language=language))
        first_id = self.service.start_session("maria", "CHAT")

        def add_prior_message(record):
            record["messages"].append({
                "id": "prior-message",
                "role": "patient",
                "text": "Maria Rossi here, call (416) 555-0198 or maria.demo@example.com. "
                        "My foot has been sore for two weeks",
                "time": now_iso(),
                "session_id": first_id,
                "channel": "chat",
            })

        self.store.update("maria", add_prior_message)
        self.service.end_session("maria", first_id)
        return self.service.start_session("maria", "CHAT")

    def test_first_session_has_no_assumed_history(self):
        session_id = self.service.start_session("maria", "CHAT")
        record = self.store.load("maria")

        self.assertNotIn("previous_interaction", record["sessions"][-1])
        self.assertFalse(any(
            "welcome back" in message["text"].lower()
            for message in record["messages"]
            if message.get("session_id") == session_id
        ))

    def test_returning_session_offers_recap_or_a_new_concern(self):
        session_id = self._returning_session()
        record = self.store.load("maria")
        greeting = next(
            message["text"] for message in record["messages"]
            if message.get("session_id") == session_id
        )

        self.assertIn("quick recap", greeting)
        self.assertIn("something new", greeting)
        self.assertIn("don't need to remember", greeting)
        self.assertEqual(record["conversation"]["stage"], "done")

    def test_recap_request_uses_previous_topic(self):
        self._returning_session()
        record = self.service.handle_message("maria", "Can you remind me what we talked about last time?")

        self.assertIn("foot has been sore", record["messages"][-1]["text"])
        self.assertIn("something new", record["messages"][-1]["text"])

    def test_returning_session_and_recap_are_localized_in_french(self):
        session_id = self._returning_session("fr")
        record = self.store.load("maria")
        greeting = next(
            message["text"] for message in record["messages"]
            if message.get("session_id") == session_id
        )
        self.assertIn("Bonjour", greeting)
        self.assertIn("nouveau sujet", greeting)

        record = self.service.handle_message("maria", "Peux-tu me rappeler ce dont on a parlé la dernière fois?")
        self.assertIn("La dernière fois", record["messages"][-1]["text"])
        self.assertIn("nouveau sujet", record["messages"][-1]["text"])

    def test_ai_context_separates_and_redacts_historical_messages(self):
        self._returning_session()
        record = self.store.load("maria")
        context = patient_context(record)
        previous = json.dumps(context["previous_interaction"])

        self.assertTrue(all(message["from"] == "assistant" for message in context["recent_messages"]))
        self.assertIn("foot has been sore", previous)
        for identifier in ("Maria", "Rossi", "(416) 555-0198", "maria.demo@example.com"):
            self.assertNotIn(identifier, previous)


if __name__ == "__main__":
    unittest.main()
