"""Switching, adding and deleting profiles, and deleting all local data.

Called by: Manage profiles page, pharmacist patient list.
"""

from tkinter import messagebox, simpledialog

from ..core.medical_robot import MedicalRobot
from ..storage.chat_history import ChatHistoryStore
from ..storage.profile_store import ProfileStore


class ProfileActionsMixin:
    def switch_profile(self, profile_id):
        if profile_id not in self.profiles:
            raise ValueError(f"Unknown profile: {profile_id}")
        self._cancel_checkup_animation()
        self._stop_call_input()
        self.chat_history.save(self.chat_logs)
        self.active_profile_id = profile_id
        self.chat_messages = self.chat_logs.get(profile_id, [])
        if self.profiles[profile_id]["role"] == "Patient":
            self.medical_robot = self.medical_robots.setdefault(profile_id, MedicalRobot())
        self.chat_draft = ""
        self.status = ""
        # switching account = signing in as that role (pharmacist or that patient)
        self.sign_in("pharmacist" if self.profiles[profile_id]["role"] == "Pharmacist" else "patient")

    def add_patient_profile(self):
        name = simpledialog.askstring(
            "Add patient",
            "Enter a name for this local demo patient profile:",
            parent=self,
        )
        if name is None:
            return
        try:
            profile = ProfileStore.new_patient(name)
        except ValueError:
            self.profile_status = "Enter a patient name to add the profile."
            self.render()
            return
        self.profiles[profile["id"]] = profile
        self.profile_store.save(list(self.profiles.values()))
        self.chat_logs[profile["id"]] = []
        self.chat_history = ChatHistoryStore(self.profiles, self.chat_history.path)
        self.chat_history.save(self.chat_logs)
        self.medical_robots[profile["id"]] = MedicalRobot()
        first, _, last = name.strip().partition(" ")
        self.store.update(profile["id"], lambda r: r["profile"].update(first_name=first, last_name=last))
        self.selected_patient_id = profile["id"]
        self.profile_status = f"{name.strip()} added as a local demo patient."
        self.render()

    def delete_profile(self, profile_id):
        profile = self.profiles.get(profile_id)
        if not profile:
            raise ValueError(f"Unknown profile: {profile_id}")
        role_ids = [
            key for key, item in self.profiles.items() if item["role"] == profile["role"]
        ]
        if len(role_ids) <= 1:
            self.profile_status = f"The last {profile['role'].lower()} profile cannot be deleted."
            self.render()
            return
        confirmed = messagebox.askyesno(
            "Delete profile",
            f"Delete {profile['name']} and permanently remove their saved chat log?",
            parent=self,
            default=messagebox.NO,
        )
        if not confirmed:
            return

        remaining_profiles = {
            key: value for key, value in self.profiles.items() if key != profile_id
        }
        remaining_logs = {
            key: value for key, value in self.chat_logs.items() if key != profile_id
        }
        scrubbed_logs = dict(self.chat_logs)
        scrubbed_logs[profile_id] = []
        scrubbed_store = ChatHistoryStore(self.profiles, self.chat_history.path)
        try:
            scrubbed_store.save(scrubbed_logs)
        except OSError as error:
            messagebox.showerror(
                "Could not delete chat history",
                f"The profile was not deleted because its chat history could not be cleared:\n{error}",
                parent=self,
            )
            return
        self.chat_logs = scrubbed_logs
        self.chat_history = scrubbed_store
        if self.active_profile_id == profile_id:
            self.chat_messages = scrubbed_logs[profile_id]
        try:
            self.profile_store.save(list(remaining_profiles.values()))
        except OSError as error:
            self.profile_status = "The chat log was cleared, but the profile could not be deleted."
            messagebox.showerror(
                "Profile deletion incomplete",
                f"The chat log was cleared, but the profile file could not be updated:\n{error}",
                parent=self,
            )
            self.render()
            return

        self.profiles = remaining_profiles
        self.chat_logs = remaining_logs
        history_store = ChatHistoryStore(remaining_profiles, self.chat_history.path)
        self.chat_history = history_store
        self.medical_robots.pop(profile_id, None)
        self.selected_patient_id = (
            self.selected_patient_id if self.selected_patient_id in remaining_profiles
            else next(key for key, item in remaining_profiles.items() if item["role"] == "Patient")
        )
        role_ids = [key for key, item in self.profiles.items() if item["role"] == profile["role"]]
        if self.active_profile_id == profile_id:
            self.active_profile_id = role_ids[0]
            self.chat_messages = self.chat_logs[self.active_profile_id]
            if profile["role"] == "Patient":
                self.medical_robot = self.medical_robots[self.active_profile_id]
            self.section = "Dashboard"
        try:
            self.chat_history.save(self.chat_logs)
        except OSError as error:
            self.profile_status = "Profile and chat were deleted; local chat index cleanup failed."
            messagebox.showerror(
                "Chat index cleanup failed",
                f"The chat messages were cleared, but the local chat file could not be fully updated:\n{error}",
                parent=self,
            )
            self.render()
            return
        self.profile_status = f"{profile['name']} and their chat log were deleted."
        self.render()

    def delete_patient_profile(self, profile_id):
        self.delete_profile(profile_id)

    def delete_all_local_data(self):
        confirmed = messagebox.askyesno(
            "Delete all local Pillway data",
            "Permanently delete all saved profiles and chat logs from this PC? "
            "This removes the local profiles.json and chat_history.json files. "
            "Built-in demo accounts will be restored afterward.",
            parent=self,
            default=messagebox.NO,
        )
        if not confirmed:
            return

        paths = (
            self.profile_store.path,
            self.profile_store.path.with_name(self.profile_store.path.name + ".tmp"),
            self.chat_history.path,
            self.chat_history.path.with_name(self.chat_history.path.name + ".tmp"),
        )
        try:
            for path in paths:
                if path.exists():
                    path.unlink()
        except OSError as error:
            messagebox.showerror(
                "Could not delete all local data",
                f"Some files may already have been deleted. Fix the file access issue and retry:\n{error}",
                parent=self,
            )
            return

        self.profiles = {profile["id"]: profile for profile in self.profile_store.load()}
        self.chat_history = ChatHistoryStore(self.profiles, self.chat_history.path)
        self.chat_logs = self.chat_history.load()
        patient_ids = [key for key, item in self.profiles.items() if item["role"] == "Patient"]
        self.active_profile_id = patient_ids[0]
        self.selected_patient_id = patient_ids[0]
        self.doctor_workspace_open = False
        self.chat_messages = self.chat_logs[self.active_profile_id]
        self.medical_robots = {
            key: MedicalRobot()
            for key, item in self.profiles.items()
            if item["role"] == "Patient"
        }
        self.medical_robot = self.medical_robots[self.active_profile_id]
        if hasattr(self, "store"):
            self.store.reset_demo()
        self.profile_status = "Saved profiles and chat logs deleted; built-in demo accounts restored."
        self.doctor_status = ""
        self.chat_open = False
        self.call_open = False
        self.chat_draft = ""
        self.dropdown = None
        self.render()
