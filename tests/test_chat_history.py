import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from pillway.storage.chat_history import ChatHistoryStore, format_chat_time, local_timestamp


class ChatHistoryStoreTests(unittest.TestCase):
    def test_profiles_keep_separate_histories_across_reload(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "chat_history.json"
            store = ChatHistoryStore(("patient", "doctor"), path)
            logs = store.load()
            timestamp = local_timestamp()
            self.assertIsNotNone(datetime.fromisoformat(timestamp).utcoffset())
            logs["patient"].append(("Sarah", "Patient-only message", timestamp))
            logs["doctor"].append(("Doctor workspace", "Doctor-only message"))
            store.save(logs)

            restored = ChatHistoryStore(("patient", "doctor"), path).load()

        self.assertEqual(restored["patient"], [("Sarah", "Patient-only message", timestamp)])
        self.assertEqual(restored["doctor"], [("Doctor workspace", "Doctor-only message", None)])

    def test_legacy_sarah_sender_is_migrated_without_changing_message_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "chat_history.json"
            path.write_text(
                '{"version": 1, "chats": {"patient": [{"sender": "Sarah", '
                '"message": "Sarah said hello"}]}}',
                encoding="utf-8",
            )

            restored = ChatHistoryStore(("patient",), path).load()

        self.assertEqual(restored["patient"], [("Sarah", "Sarah said hello", None)])

    def test_chat_time_uses_local_device_date(self):
        now = datetime.now().astimezone().replace(hour=12, minute=0, second=0, microsecond=0)
        yesterday = now.replace(hour=9) - timedelta(days=1)

        self.assertEqual(
            format_chat_time(yesterday.isoformat(), now=now),
            f"Yesterday, {yesterday.strftime('%I:%M %p').lstrip('0')}",
        )
        self.assertEqual(format_chat_time(None, now=now), "Time unavailable")


if __name__ == "__main__":
    unittest.main()
