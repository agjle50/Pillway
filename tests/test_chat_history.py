import tempfile
import unittest
from pathlib import Path

from pillway.chat_history import ChatHistoryStore


class ChatHistoryStoreTests(unittest.TestCase):
    def test_profiles_keep_separate_histories_across_reload(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "chat_history.json"
            store = ChatHistoryStore(("patient", "doctor"), path)
            logs = store.load()
            logs["patient"].append(("Juliez", "Patient-only message"))
            logs["doctor"].append(("Doctor workspace", "Doctor-only message"))
            store.save(logs)

            restored = ChatHistoryStore(("patient", "doctor"), path).load()

        self.assertEqual(restored["patient"], [("Juliez", "Patient-only message")])
        self.assertEqual(restored["doctor"], [("Doctor workspace", "Doctor-only message")])

    def test_legacy_sarah_sender_is_migrated_without_changing_message_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "chat_history.json"
            path.write_text(
                '{"version": 1, "chats": {"patient": [{"sender": "Sarah", '
                '"message": "Sarah said hello"}]}}',
                encoding="utf-8",
            )

            restored = ChatHistoryStore(("patient",), path).load()

        self.assertEqual(restored["patient"], [("Juliez", "Sarah said hello")])


if __name__ == "__main__":
    unittest.main()
