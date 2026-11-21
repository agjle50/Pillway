"""Local persistence for the demo patient and doctor profiles."""

import json
import os
import sys
import uuid
from pathlib import Path

from .profiles import PROFILES


class ProfileStore:
    def __init__(self, path=None):
        if path:
            self.path = Path(path)
        else:
            if sys.platform == "win32":
                base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
            else:
                base = Path.home() / ".local" / "share"
            self.path = base / "Pillway" / "profiles.json"

    def load(self):
        try:
            with self.path.open("r", encoding="utf-8") as profiles_file:
                data = json.load(profiles_file)
        except FileNotFoundError:
            return [dict(profile) for profile in PROFILES]
        except json.JSONDecodeError as error:
            raise ValueError(f"Profile file is invalid: {self.path}") from error

        if not isinstance(data, dict) or data.get("version") != 1:
            raise ValueError(f"Unsupported profile file format: {self.path}")
        profiles = data.get("profiles")
        if not isinstance(profiles, list):
            raise ValueError(f"Profile file is missing its profiles list: {self.path}")

        normalized = []
        seen_ids = set()
        for profile in profiles:
            if (
                not isinstance(profile, dict)
                or not isinstance(profile.get("id"), str)
                or not isinstance(profile.get("name"), str)
                or profile.get("role") not in ("Patient", "Doctor", "Pharmacist")
            ):
                raise ValueError(f"Invalid profile in {self.path}")
            if profile["id"] in seen_ids:
                raise ValueError(f"Duplicate profile id in {self.path}: {profile['id']}")
            seen_ids.add(profile["id"])
            role = "Pharmacist" if profile["role"] == "Doctor" else profile["role"]  # old files said Doctor
            normalized.append({
                "id": profile["id"],
                "name": profile["name"],
                "role": role,
                "record_id": profile.get("record_id", "maria" if profile["id"] == "patient" else profile["id"]),
                "description": profile.get("description", ""),
            })
        if not any(profile["role"] == "Patient" for profile in normalized):
            raise ValueError(f"Profile file has no patient account: {self.path}")
        if not any(profile["role"] == "Pharmacist" for profile in normalized):
            raise ValueError(f"Profile file has no pharmacist account: {self.path}")
        return normalized

    def save(self, profiles):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_name(self.path.name + ".tmp")
        try:
            with temporary_path.open("w", encoding="utf-8") as profiles_file:
                json.dump({"version": 1, "profiles": profiles}, profiles_file,
                          ensure_ascii=False, indent=2)
            temporary_path.replace(self.path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

    @staticmethod
    def new_patient(name):
        name = name.strip()
        if not name:
            raise ValueError("Patient name cannot be empty.")
        profile_id = uuid.uuid4().hex
        return {
            "id": profile_id,
            "name": name,
            "role": "Patient",
            "record_id": profile_id,
            "description": "Local demo patient profile.",
        }
