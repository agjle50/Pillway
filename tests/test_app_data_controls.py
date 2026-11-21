import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    import tkinter  # noqa: F401
    from pillway.app import PillwayApp
except ImportError:  # no window toolkit on this computer (e.g. a server): skip these UI tests
    raise unittest.SkipTest("tkinter is not installed")
from pillway.storage.chat_history import ChatHistoryStore
from pillway.core.medical_robot import MedicalRobot
from pillway.storage.profile_store import ProfileStore


class AppDataControlTests(unittest.TestCase):
    def test_selecting_a_doctor_patient_opens_the_care_plan_workspace(self):
        app = SimpleNamespace(
            profiles={"patient": {"id": "patient", "role": "Patient"}},
            selected_patient_id="patient",
            doctor_workspace_open=False,
            render=Mock(),
        )

        PillwayApp.select_doctor_patient(app, "patient")

        self.assertTrue(app.doctor_workspace_open)
        app.render.assert_called_once_with()

    def test_returning_to_patient_list_closes_the_care_plan_workspace(self):
        app = SimpleNamespace(
            doctor_workspace_open=True,
            render=Mock(),
        )

        PillwayApp.return_to_doctor_patient_list(app)

        self.assertFalse(app.doctor_workspace_open)
        app.render.assert_called_once_with()

    def test_call_choice_opens_a_preview_without_claiming_to_connect(self):
        app = SimpleNamespace(
            call_open=False,
            chat_open=True,
            status="Connecting...",
            render=Mock(),
            _cancel_checkup_animation=Mock(),
            _stop_call_input=Mock(),
        )

        PillwayApp.checkup_choice(app, "Call")

        self.assertTrue(app.call_open)
        self.assertFalse(app.chat_open)
        self.assertEqual(app.status, "")
        app.render.assert_called_once_with()
        PillwayApp.close_call_preview(app)
        self.assertFalse(app.call_open)

    def make_app(self, directory):
        profile_store = ProfileStore(Path(directory) / "profiles.json")
        profiles = {profile["id"]: profile for profile in profile_store.load()}
        patient = ProfileStore.new_patient("Alex")
        profiles[patient["id"]] = patient
        profile_store.save(list(profiles.values()))

        chat_history = ChatHistoryStore(profiles, Path(directory) / "chat_history.json")
        chat_logs = chat_history.load()
        chat_logs[patient["id"]].append(("You", "Private message"))
        chat_history.save(chat_logs)
        patient_ids = [key for key, profile in profiles.items() if profile["role"] == "Patient"]
        return SimpleNamespace(
            profiles=profiles,
            profile_store=profile_store,
            chat_history=chat_history,
            chat_logs=chat_logs,
            medical_robots={key: MedicalRobot() for key in patient_ids},
            selected_patient_id=patient["id"],
            active_profile_id=patient["id"],
            chat_messages=chat_logs[patient["id"]],
            medical_robot=MedicalRobot(),
            section="Dashboard",
            profile_status="",
            doctor_status="",
            chat_open=True,
            render=lambda: None,
        ), patient["id"]

    def test_deleting_profile_removes_saved_chat_and_switches_active_patient(self):
        with tempfile.TemporaryDirectory() as directory:
            app, deleted_id = self.make_app(directory)
            with patch("pillway.app.messagebox.askyesno", return_value=True), patch(
                "pillway.app.messagebox.showerror"
            ):
                PillwayApp.delete_profile(app, deleted_id)

            self.assertNotIn(deleted_id, app.profiles)
            self.assertNotIn(deleted_id, app.chat_logs)
            self.assertEqual(app.active_profile_id, "patient")
            self.assertEqual(app.selected_patient_id, "patient")
            saved_profiles = app.profile_store.load()
            self.assertNotIn(deleted_id, {profile["id"] for profile in saved_profiles})
            saved_history = ChatHistoryStore(
                {profile["id"]: profile for profile in saved_profiles},
                app.chat_history.path,
            ).load()
            self.assertNotIn(deleted_id, saved_history)
            self.assertNotIn("Private message", app.chat_history.path.read_text(encoding="utf-8"))

    def test_delete_all_removes_local_files_and_restores_empty_demo_state(self):
        with tempfile.TemporaryDirectory() as directory:
            app, _ = self.make_app(directory)
            profile_path = app.profile_store.path
            history_path = app.chat_history.path
            profile_tmp = profile_path.with_name(profile_path.name + ".tmp")
            history_tmp = history_path.with_name(history_path.name + ".tmp")
            profile_tmp.write_text("temporary", encoding="utf-8")
            history_tmp.write_text("temporary", encoding="utf-8")
            with patch("pillway.app.messagebox.askyesno", return_value=True), patch(
                "pillway.app.messagebox.showerror"
            ):
                PillwayApp.delete_all_local_data(app)

            self.assertFalse(profile_path.exists())
            self.assertFalse(history_path.exists())
            self.assertFalse(profile_tmp.exists())
            self.assertFalse(history_tmp.exists())
            self.assertEqual(app.chat_logs[app.active_profile_id], [])
            self.assertIn("restored", app.profile_status)


if __name__ == "__main__":
    unittest.main()
