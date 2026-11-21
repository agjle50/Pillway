"""Local per-profile chat history persistence."""

import json
import os
import sys
from pathlib import Path


class ChatHistoryStore:
    def __init__(self, profile_ids, path=None):
        self.profile_ids = tuple(profile_ids)
        self.path = Path(path) if path else self._default_path()

    @staticmethod
    def _default_path():
        if sys.platform == "win32":
            base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        else:
            base = Path.home() / ".local" / "share"
        return base / "Pillway" / "chat_history.json"

    def load(self):
        logs = {profile_id: [] for profile_id in self.profile_ids}
        try:
            with self.path.open("r", encoding="utf-8") as history_file:
                data = json.load(history_file)
        except FileNotFoundError:
            return logs
        except json.JSONDecodeError as error:
            raise ValueError(f"Chat history file is invalid: {self.path}") from error

        if not isinstance(data, dict) or data.get("version") != 1:
            raise ValueError(f"Unsupported chat history format: {self.path}")
        saved_logs = data.get("chats")
        if not isinstance(saved_logs, dict):
            raise ValueError(f"Chat history is missing account logs: {self.path}")
        for profile_id in self.profile_ids:
            messages = saved_logs.get(profile_id, [])
            if not isinstance(messages, list):
                raise ValueError(f"Invalid chat log for profile {profile_id!r}")
            for message in messages:
                if (
                    not isinstance(message, dict)
                    or not isinstance(message.get("sender"), str)
                    or not isinstance(message.get("message"), str)
                ):
                    raise ValueError(f"Invalid message in profile {profile_id!r} chat log")
                sender = "Juliez" if message["sender"] == "Sarah" else message["sender"]
                logs[profile_id].append((sender, message["message"]))
        return logs

    def save(self, logs):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_name(self.path.name + ".tmp")
        data = {
            "version": 1,
            "chats": {
                profile_id: [
                    {"sender": sender, "message": message}
                    for sender, message in logs[profile_id]
                ]
                for profile_id in self.profile_ids
            },
        }
        try:
            with temporary_path.open("w", encoding="utf-8") as history_file:
                json.dump(data, history_file, ensure_ascii=False, indent=2)
            temporary_path.replace(self.path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()
