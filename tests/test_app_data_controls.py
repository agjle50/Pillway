import tempfile
import unittest
from pathlib import Path
from queue import Queue
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
    def test_sign_in_keeps_the_pharmacist_account_selected_in_manage_profiles(self):
        app = SimpleNamespace(
            profiles={
                "first": {"id": "first", "role": "Pharmacist"},
                "second": {"id": "second", "role": "Pharmacist"},
            },
            active_profile_id="second",
            section="Manage profiles",
            tab="Check up",
            dropdown="profile",
            chat_open=True,
            call_open=True,
            doctor_workspace_open=True,
            render=Mock(),
        )

        PillwayApp.sign_in(app, "pharmacist")

        self.assertEqual(app.active_profile_id, "second")
        self.assertEqual(app.role, "pharmacist")
        self.assertFalse(app.doctor_workspace_open)
        app.render.assert_called_once_with()

    def test_add_patient_profile_persists_a_new_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            profile_store = ProfileStore(Path(directory) / "profiles.json")
            profiles = {profile["id"]: profile for profile in profile_store.load()}
            chat_history = ChatHistoryStore(profiles, Path(directory) / "chat_history.json")
            app = SimpleNamespace(
                profiles=profiles,
                profile_store=profile_store,
                chat_history=chat_history,
                chat_logs=chat_history.load(),
                medical_robots={},
                store=Mock(),
                selected_patient_id="maria",
                profile_status="",
                render=Mock(),
            )
            with patch("pillway.ui.profile_actions.simpledialog.askstring", return_value="Alex"):
                PillwayApp.add_patient_profile(app)

            created = next(profile for profile in app.profiles.values() if profile["name"] == "Alex")
            self.assertEqual(created["role"], "Patient")
            self.assertIn(created["id"], app.chat_logs)
            self.assertIn(created["id"], {profile["id"] for profile in profile_store.load()})

    def test_pharmacist_notifications_include_open_patient_tickets(self):
        record = {
            "id": "maria",
            "profile": {"first_name": "Maria", "last_name": "Rossi"},
            "pharmacist_requests": [{
                "id": "req-1", "status": "open", "reason": "Patient asked for a callback.",
                "time": "2026-11-21T17:00:00-05:00",
            }],
            "flags": [],
        }
        app = SimpleNamespace(
            role="pharmacist",
            dropdown="notifications",
            store=SimpleNamespace(all=Mock(return_value=[record])),
            select_doctor_patient=Mock(),
        )

        title, items = PillwayApp.dropdown_items(app)
        items[0][2]()

        self.assertEqual(title, "Notifications")
        self.assertEqual(items[0][0], "Maria Rossi")
        self.assertEqual(items[0][1], "17:00")
        app.select_doctor_patient.assert_called_once_with("maria")
        self.assertTrue(PillwayApp.unread_notifications(app))

    def test_patient_notifications_start_empty(self):
        app = SimpleNamespace(
            role="patient",
            dropdown="notifications",
            notifications=[],
        )

        _title, items = PillwayApp.dropdown_items(app)

        self.assertEqual(items[0][0], "No notifications yet")

    def test_patient_notifications_show_only_patient_and_time(self):
        app = SimpleNamespace(
            role="patient",
            dropdown="notifications",
            notifications=[("Maria Rossi", "2026-11-21T17:00:00-05:00")],
        )

        _title, items = PillwayApp.dropdown_items(app)

        self.assertEqual(items, [("Maria Rossi", "17:00", None)])

    def test_clickable_runs_action_silently(self):
        class ClickHarness:
            def __init__(self):
                self.sound_count = 0

            def bell(self):
                self.sound_count += 1

            _invoke_clickable = PillwayApp._invoke_clickable

        app = ClickHarness()
        action = Mock()

        result = PillwayApp._invoke_clickable(app, action)

        self.assertEqual(app.sound_count, 0)  # never the Windows "ding"
        action.assert_called_once_with()
        self.assertEqual(result, "break")

    def test_demo_ai_still_uses_offline_transcription_when_a_mic_is_present(self):
        settings = SimpleNamespace(
            ai=SimpleNamespace(demo_mode=True),
            call=SimpleNamespace(speech_to_text_engine="vosk", microphone_device=""),
            patient=SimpleNamespace(read_aloud=True),
        )
        app = SimpleNamespace(
            patient_id="maria",
            service=SimpleNamespace(start_session=Mock(return_value="session-1")),
            store=SimpleNamespace(load=Mock(return_value={"messages": []})),
            _start_listener=Mock(),
            _tick_call=Mock(),
            lang="en",
        )
        app.speech_recognition_disabled = lambda: PillwayApp.speech_recognition_disabled(app)

        with patch("pillway.ui.patient.call.get_settings", return_value=settings), patch(
            "pillway.ui.patient.call_audio.get_settings", return_value=settings,
        ), patch(
            "pillway.ui.patient.call_audio.microphone_status",
            return_value=(True, ""),
        ):
            PillwayApp._begin_call(app)

        self.assertTrue(app.call_state["meter_available"])
        self.assertTrue(app.call_state["speaker_enabled"])
        app._start_listener.assert_called_once_with(transcribe=True)

    def test_sidebar_destinations_change_section_and_render(self):
        for section in ("See a doctor", "Contact us", "Account tour", "FAQ"):
            app = SimpleNamespace(
                role="patient",
                section="Dashboard",
                tab="Check up",
                dropdown="profile",
                chat_open=False,
                call_open=False,
                _cancel_checkup_animation=Mock(),
                _stop_call_input=Mock(),
                render=Mock(),
            )

            PillwayApp.go(app, section)

            self.assertEqual(app.section, section)
            app.render.assert_called_once_with()

    def test_call_final_utterances_send_hands_free_but_are_discarded_when_muted(self):
        for muted, expected_calls in ((False, 1), (True, 0)):
            events = Queue()
            events.put(("final", "I feel okay"))
            app = SimpleNamespace(
                call_open=True,
                call_state={"started": 0, "heard": [], "muted": muted},
                call_events=events,
                _send_call_text=Mock(),
                _speak_new_replies=Mock(),
                _update_call_widgets=Mock(),
                _tick_call=Mock(),
                after=Mock(return_value="poll-job"),
            )

            PillwayApp._tick_call(app)

            self.assertEqual(app._send_call_text.call_count, expected_calls)
            if expected_calls:
                app._send_call_text.assert_called_once_with("I feel okay")

    def test_call_controls_toggle_microphone_and_ai_speaker(self):
        app = SimpleNamespace(
            call_state={"muted": False, "speaker_enabled": True},
            render=Mock(),
        )

        PillwayApp.toggle_call_mute(app)
        PillwayApp.toggle_call_speaker(app)

        self.assertTrue(app.call_state["muted"])
        self.assertFalse(app.call_state["speaker_enabled"])
        self.assertEqual(app.render.call_count, 2)

    def test_speaker_toggle_controls_ai_voice_output(self):
        message = {"role": "sarah", "id": "reply-1", "text": "Hello."}
        app = SimpleNamespace(
            call_state={"spoken": set(), "speaker_enabled": False},
            call_caption_lines=Mock(return_value=[message]),
            lang="en",
            call_listener=None,
            _background_errors=[],
        )
        app._speak_on_call = lambda text: PillwayApp._speak_on_call(app, text)

        with patch("pillway.ui.patient.call_audio.speak") as speak:
            PillwayApp._speak_new_replies(app)
            self.assertEqual(speak.call_count, 0)
            app.call_state["speaker_enabled"] = True
            message["id"] = "reply-2"
            PillwayApp._speak_new_replies(app)

        speak.assert_called_once()
        self.assertEqual(speak.call_args.args, ("Hello.", "en"))

    def test_voice_typing_starts_local_transcription(self):
        app = SimpleNamespace(
            patient_id="maria",
            lang="en",
            voice_listener=None,
            voice_events=None,
            voice_typing_active=False,
            voice_typing_status="",
            voice_typing_had_text=False,
            voice_typing_error=False,
            chat_focus_requested=False,
            render=Mock(),
            _poll_voice_typing=Mock(),
            after=Mock(return_value="voice-poll"),
            t=lambda key: key,
        )
        settings = SimpleNamespace(call=SimpleNamespace(microphone_device=""))
        with tempfile.TemporaryDirectory() as directory, patch(
            "pillway.ui.patient.chat_actions.get_settings", return_value=settings,
        ), patch(
            "pillway.ui.patient.chat_actions.data_folder", return_value=Path(directory),
        ), patch(
            "pillway.ui.patient.chat_actions.resolve_input_device", return_value=3,
        ), patch(
            "pillway.ui.patient.chat_actions.LocalSpeechInput",
        ) as listener_factory:
            PillwayApp.voice_typing(app)

        listener_factory.assert_called_once()
        self.assertEqual(listener_factory.call_args.kwargs["device"], 3)
        self.assertTrue(listener_factory.call_args.kwargs["transcribe"])
        listener_factory.return_value.start.assert_called_once_with()
        self.assertTrue(app.voice_typing_active)
        self.assertEqual(app._voice_typing_job, "voice-poll")

    def test_voice_typing_inserts_recognized_text_without_sending(self):
        class FakeEntry:
            def __init__(self, value):
                self.value = value
                self.cursor = len(value)

            def winfo_exists(self):
                return True

            def get(self):
                return self.value

            def index(self, _index):
                return self.cursor

            def insert(self, index, value):
                self.value = self.value[:index] + value + self.value[index:]
                self.cursor = index + len(value)

            def delete(self, _start, _end):
                self.value = ""
                self.cursor = 0

            def configure(self, **_options):
                pass

            def icursor(self, index):
                self.cursor = index

            def focus_set(self):
                pass

        events = Queue()
        events.put(("final", "I have a headache."))
        app = SimpleNamespace(
            voice_listener=SimpleNamespace(is_alive=Mock(return_value=False)),
            voice_events=events,
            voice_typing_active=True,
            voice_typing_status="Listening",
            voice_typing_had_text=False,
            voice_typing_error=False,
            chat_entry=FakeEntry("I feel"),
            chat_placeholder="Type your message...",
            chat_draft="I feel",
            chat_focus_requested=False,
            c=SimpleNamespace(itemconfigure=Mock()),
            t=lambda key: {
                "chat.voice_added": "Voice text added.",
                "chat.voice_stopped": "No text recognized.",
                "chat.voice_error": "Voice typing unavailable: {error}",
            }.get(key, key),
            render=Mock(),
            after=Mock(return_value="voice-poll"),
        )
        app._insert_voice_text = lambda text: PillwayApp._insert_voice_text(app, text)

        PillwayApp._poll_voice_typing(app)

        self.assertEqual(app.chat_entry.get(), "I feel I have a headache.")
        self.assertEqual(app.chat_draft, "I feel I have a headache.")
        self.assertEqual(app.voice_typing_status, "Voice text added.")
        self.assertIsNone(app.voice_listener)
        app.render.assert_called_once_with()

    def test_microphone_selection_is_saved_as_device_index(self):
        settings = SimpleNamespace(call=SimpleNamespace(microphone_device=""))
        app = SimpleNamespace(
            _stop_microphone_test=Mock(),
            flash=Mock(),
        )

        with patch("pillway.ui.patient.settings.get_settings", return_value=settings), patch(
            "pillway.ui.patient.settings.app_state.save",
        ) as save:
            PillwayApp.set_microphone_device(app, 0)

        save.assert_called_once_with(microphone_device="0")
        self.assertEqual(settings.call.microphone_device, "0")
        app._stop_microphone_test.assert_called_once_with()
        app.flash.assert_called_once_with("Microphone saved.")

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
            patient_id="maria",
            service=SimpleNamespace(busy=set()),
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

    def test_call_choice_waits_while_a_chat_reply_is_processing(self):
        app = SimpleNamespace(
            patient_id="maria",
            service=SimpleNamespace(busy={"maria"}),
            call_open=False,
            chat_open=False,
            status="",
            render=Mock(),
            _cancel_checkup_animation=Mock(),
        )

        PillwayApp.checkup_choice(app, "Call")

        self.assertFalse(app.call_open)
        self.assertIn("wait", app.status)
        app.render.assert_called_once_with()

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
