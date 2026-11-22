"""Local per-profile chat history persistence."""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path


def local_timestamp():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def format_chat_time(timestamp, now=None):
    if not timestamp:
        return "Time unavailable"
    message_time = datetime.fromisoformat(timestamp).astimezone()
    local_now = (now or datetime.now().astimezone()).astimezone()
    clock = message_time.strftime("%I:%M %p").lstrip("0")
    if message_time.date() == local_now.date():
        return clock
    if message_time.date() == local_now.date() - timedelta(days=1):
        return f"Yesterday, {clock}"
    return f"{message_time.strftime('%b %d')}, {clock}"


def local_date_label(now=None):
    return (now or datetime.now().astimezone()).astimezone().strftime("%A, %B %d, %Y")


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
                timestamp = message.get("timestamp")
                if timestamp is not None and not isinstance(timestamp, str):
                    raise ValueError(f"Invalid timestamp in profile {profile_id!r} chat log")
                if timestamp:
                    try:
                        datetime.fromisoformat(timestamp)
                    except ValueError as error:
                        raise ValueError(
                            f"Invalid timestamp in profile {profile_id!r} chat log"
                        ) from error
                sender = message["sender"]
                logs[profile_id].append((sender, message["message"], timestamp or None))
        return logs

    def save(self, logs):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_name(self.path.name + ".tmp")
        data = {
            "version": 1,
            "chats": {},
        }
        for profile_id in self.profile_ids:
            serialized_messages = []
            for entry in logs[profile_id]:
                if len(entry) == 2:
                    sender, message = entry
                    timestamp = None
                elif len(entry) == 3:
                    sender, message, timestamp = entry
                else:
                    raise ValueError(f"Invalid chat entry for profile {profile_id!r}")
                if not isinstance(sender, str) or not isinstance(message, str):
                    raise ValueError(f"Invalid chat entry for profile {profile_id!r}")
                if timestamp is not None and not isinstance(timestamp, str):
                    raise ValueError(f"Invalid timestamp for profile {profile_id!r}")
                if timestamp:
                    try:
                        datetime.fromisoformat(timestamp)
                    except ValueError as error:
                        raise ValueError(
                            f"Invalid timestamp for profile {profile_id!r}"
                        ) from error
                serialized_messages.append({
                    "sender": sender,
                    "message": message,
                    "timestamp": timestamp,
                })
            data["chats"][profile_id] = serialized_messages
        try:
            with temporary_path.open("w", encoding="utf-8") as history_file:
                json.dump(data, history_file, ensure_ascii=False, indent=2)
            temporary_path.replace(self.path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()
