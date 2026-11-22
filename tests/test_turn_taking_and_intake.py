"""Turn-taking on calls (Sarah never hears herself) and the first-visit questionnaire / health profile."""

import time
import unittest
from queue import Queue
from types import SimpleNamespace
from unittest.mock import Mock, patch

from tests.helpers import use_temp_settings

use_temp_settings()

from pillway.ai.brain import MEMORY_PROMPT, patient_context  # noqa: E402
from pillway.app import PillwayApp  # noqa: E402
from pillway.core import intake  # noqa: E402
from pillway.core.conversation_service import ConversationService  # noqa: E402
from pillway.core.patient_summary import intake_summary  # noqa: E402
from pillway.ui.patient import call_audio  # noqa: E402

GOOD_FORM = {"weight": "92", "weight_unit": "kg", "height": "165", "height_unit": "cm", "checks_bp": "yes",
             "systolic": "148", "diastolic": "94", "tobacco": "yes", "readiness": "thinking"}


class FakeListener:
    def __init__(self):
        self.muted = False
        self.active_engine = "whisper"

    def set_muted(self, value):
        self.muted = value


def call_app(**state):
    base = {"started": 0, "heard": [], "muted": False, "spoken": set(), "speaker_enabled": True}
    base.update(state)
    return SimpleNamespace(call_open=True, call_state=base, call_events=Queue(), call_listener=FakeListener(),
                           lang="en", _background_errors=[], _send_call_text=Mock(), _speak_new_replies=Mock(),
                           _update_call_widgets=Mock(), _tick_call=Mock(), after=Mock(return_value="job"))


class MicGateTests(unittest.TestCase):
    def test_the_mic_only_listens_on_the_patients_turn(self):
        self.assertEqual(call_audio.mic_should_listen({}), (True, "patient's turn"))
        self.assertFalse(call_audio.mic_should_listen({"muted": True})[0])
        self.assertFalse(call_audio.mic_should_listen({"sarah_speaking": True})[0])
        now = time.monotonic()
        self.assertFalse(call_audio.mic_should_listen({"deaf_until": now + 1}, now)[0])
        self.assertTrue(call_audio.mic_should_listen({"deaf_until": now - 0.1}, now)[0])

    def test_words_heard_while_sarah_talks_are_never_sent(self):
        app = call_app(sarah_speaking=True)
        app.call_events.put(("final", "how are you feeling today"))   # her own voice through the speakers
        PillwayApp._tick_call(app)
        app._send_call_text.assert_not_called()
        self.assertTrue(app.call_listener.muted)

    def test_words_heard_during_the_echo_tail_are_dropped_then_the_mic_reopens(self):
        app = call_app(deaf_until=time.monotonic() + 5)
        app.call_events.put(("final", "today"))
        PillwayApp._tick_call(app)
        app._send_call_text.assert_not_called()
        app.call_state["deaf_until"] = time.monotonic() - 0.01
        app.call_events.put(("final", "I feel fine"))
        PillwayApp._tick_call(app)
        app._send_call_text.assert_called_once_with("I feel fine")
        self.assertFalse(app.call_listener.muted)

    def test_the_mic_closes_before_sarah_starts_and_reopens_only_after_the_tail(self):
        app = call_app(heard=["half a sentence"])
        with patch("pillway.ui.patient.call_audio.speak") as speak:
            PillwayApp._speak_on_call(app, "Hello there.")
        self.assertTrue(app.call_listener.muted)                 # closed before any sound
        self.assertEqual(app.call_state["heard"], [])            # nothing half-heard leaks through
        speak.call_args.kwargs["on_done"]()
        self.assertFalse(app.call_state["sarah_speaking"])
        self.assertGreater(app.call_state["deaf_until"], time.monotonic())   # echo tail
        self.assertFalse(call_audio.apply_mic_gate(app))          # still closed during the tail

    def test_an_old_reply_finishing_cannot_reopen_the_mic_while_a_new_one_plays(self):
        app = call_app()
        with patch("pillway.ui.patient.call_audio.speak") as speak:
            PillwayApp._speak_on_call(app, "First reply.")
            first_done = speak.call_args.kwargs["on_done"]
            PillwayApp._speak_on_call(app, "Second reply.")
        first_done()   # the first one was stopped by the second: its callback is stale
        self.assertTrue(app.call_state["sarah_speaking"])
        self.assertFalse(call_audio.apply_mic_gate(app))
        self.assertTrue(app.call_listener.muted)

    def test_windows_recognizer_gets_a_longer_echo_tail(self):
        app = call_app()
        app.call_listener.active_engine = "windows"
        self.assertEqual(call_audio.echo_tail(app), call_audio.ECHO_TAIL_SECONDS_WINDOWS)


class IntakeValidationTests(unittest.TestCase):
    def test_a_complete_form_is_clean(self):
        clean, errors = intake.validate(GOOD_FORM)
        self.assertEqual(errors, {})
        self.assertEqual((clean["bp_systolic"], clean["bp_diastolic"]), (148, 94))
        self.assertEqual(clean["quit_readiness"], "thinking")

    def test_weight_and_height_are_optional_and_pounds_are_converted(self):
        clean, errors = intake.validate({**GOOD_FORM, "weight": "", "height": ""})
        self.assertEqual(errors, {})
        self.assertFalse(clean["shared_weight"])
        clean, _ = intake.validate({**GOOD_FORM, "weight": "200", "weight_unit": "lb"})
        self.assertAlmostEqual(clean["weight_kg"], 90.7, places=1)

    def test_the_yes_no_questions_are_required(self):
        _, errors = intake.validate({"checks_bp": None, "tobacco": "yes"})
        self.assertIn("checks_bp", errors)
        self.assertIn("readiness", errors)

    def test_impossible_blood_pressure_is_caught(self):
        _, errors = intake.validate({**GOOD_FORM, "systolic": "80", "diastolic": "120"})
        self.assertIn("bp", errors)
        _, errors = intake.validate({**GOOD_FORM, "systolic": "130", "diastolic": ""})
        self.assertIn("bp", errors)


class NeverPresumeTests(unittest.TestCase):
    def setUp(self):
        use_temp_settings()
        self.service = ConversationService()

    def test_a_new_account_is_asked_the_questionnaire_first(self):
        record = self.service.store.load("maria")
        self.assertTrue(intake.needed_at_boot(record))
        record, errors = self.service.submit_intake("maria", GOOD_FORM)
        self.assertEqual(errors, {})
        self.assertFalse(intake.needed_at_boot(record))

    def test_demo_numbers_are_not_read_back_before_the_patient_gives_them(self):
        record = self.service.store.load("maria")   # the seed file has 142/90, 78 kg, non-smoker
        summary = intake_summary(record, "en")
        self.assertNotIn("142/90", summary)
        self.assertNotIn("smoke", summary)
        checklist = self.service._checklist(record)
        self.assertFalse(checklist["questionnaire_done"])
        self.assertEqual(checklist["already_in_questionnaire"], {})
        self.assertEqual(self.service._facts(record), {})

    def test_skipping_weight_removes_the_old_value_and_is_marked_private(self):
        record, _ = self.service.submit_intake("maria", {**GOOD_FORM, "weight": "", "height": ""})
        self.assertNotIn("weight_kg", record["profile"])
        self.assertTrue(record["health_profile"]["not_shared"])
        self.assertNotIn("weight_kg", self.service._checklist(record)["already_in_questionnaire"])

    def test_the_profile_lists_hunches_with_reasons_and_reaches_the_ai(self):
        record, _ = self.service.submit_intake("maria", GOOD_FORM)
        areas = {a["area"]: a["why"] for a in record["health_profile"]["areas_to_explore"]}
        self.assertIn("high blood pressure", areas)
        self.assertIn("148/94", areas["high blood pressure"])
        self.assertIn("smoking", areas)
        self.assertIn("weight, eating habits and activity", areas)
        sent = patient_context(record)["health_profile"]
        self.assertEqual(sent["areas_to_explore"], record["health_profile"]["areas_to_explore"])
        self.assertIn("148/94", intake_summary(record, "en"))

    def test_ai_suggestions_are_added_without_replacing_the_rules(self):
        record, _ = self.service.submit_intake("maria", GOOD_FORM)
        intake.merge_ai_suggestions(record, [{"area": "sleep", "why": "smokers often sleep poorly", "ask_about": "sleep"},
                                             {"area": "", "why": "empty is ignored"}])
        self.assertEqual([a["area"] for a in record["health_profile"]["ai_suggestions"]], ["sleep"])
        self.assertTrue(record["health_profile"]["areas_to_explore"])

    def test_memory_keeps_medical_details_only(self):
        self.assertIn("Do NOT keep small talk", MEMORY_PROMPT)


if __name__ == "__main__":
    unittest.main()


class CheckInAndCarePlanTests(unittest.TestCase):
    def setUp(self):
        use_temp_settings()
        self.service = ConversationService()
        self.service.submit_intake("maria", GOOD_FORM)
        self.service.accept_consent("maria")

    def test_sarah_opens_the_check_in_with_the_intake_and_asks_about_changes(self):
        from pillway.ui.patient.check_in_popup import check_in_needed
        self.assertTrue(check_in_needed(self.service.store.load("maria")))
        self.assertTrue(self.service.start_check_in("maria"))
        record = self.service.store.load("maria")
        first = record["messages"][-1]["text"]
        self.assertIn("148/94", first)                 # from her questionnaire
        self.assertIn("Has anything changed", first)
        self.assertEqual(record["conversation"]["stage"], "changes")
        self.assertFalse(self.service.start_check_in("maria"))   # never twice

    def test_intake_results_decide_which_questions_matter_most(self):
        record = self.service.store.load("maria")
        priority = intake.priority_questions(record)
        self.assertIn("blood_pressure", priority)
        self.assertIn("smoking", priority)
        self.assertEqual(self.service._checklist(record)["priority_from_intake"], priority)

    def test_the_ai_can_only_pick_recommendations_from_pillways_list(self):
        from pillway.core import care_plan
        record = self.service.store.load("maria")
        ai_plan = {"smart_goals": [{"en": "Walk 15 minutes after lunch, 5 days a week, for 4 weeks.", "fr": "Marchez."}],
                   "values": [{"id": "a1c_target", "value": "7.5", "reason": "newly diagnosed, start gently"},
                              {"id": "made_up_line", "value": "9", "reason": "x"}],
                   "recommendations": ["dietitian", "buy_supplements"], "barrier_plans": []}
        plan = care_plan.build_draft(record, ai_plan, "ai")
        ids = [l["id"] for s in plan["sections"] for l in s["lines"]]
        self.assertIn("rec_dietitian", ids)
        self.assertNotIn("rec_buy_supplements", ids)
        self.assertNotIn("made_up_line", ids)
        a1c = care_plan.find_line(plan, "a1c_target")
        self.assertEqual((a1c["value"], a1c["ai"], a1c["confirmed"]), ("7.5", True, False))
        self.assertIn("rec_quit_smoking", ids)          # she's thinking about quitting (rules)
        self.assertTrue(care_plan.find_line(plan, "goal_0")["ai"])


class VoiceCutOffTests(unittest.TestCase):
    def test_a_second_reply_waits_instead_of_cutting_the_first_off(self):
        first = {"role": "sarah", "id": "r1", "text": "First reply. It has two sentences."}
        second = {"role": "sarah", "id": "r2", "text": "Second reply."}
        app = call_app()
        lines = [first]
        app.call_caption_lines = lambda: lines
        app._speak_on_call = lambda text: PillwayApp._speak_on_call(app, text)
        with patch("pillway.ui.patient.call_audio.speak") as speak:
            PillwayApp._speak_new_replies(app)
            lines.append(second)
            PillwayApp._speak_new_replies(app)        # arrives while she's still talking
            self.assertEqual(speak.call_count, 1)    # the first one is NOT interrupted
            speak.call_args.kwargs["on_done"]()       # first one finished
            PillwayApp._speak_new_replies(app)
        self.assertEqual(speak.call_count, 2)
        self.assertEqual(speak.call_args.args[0], "Second reply.")

    def test_windows_player_waits_for_the_real_end_of_a_clip(self):
        from pillway.voice.natural_voice import finished_playing
        self.assertFalse(finished_playing("stopped", 0, 4000, 0.1))      # still loading: not finished
        self.assertTrue(finished_playing("stopped", 3950, 4000, 4.0))    # reached the end
        self.assertTrue(finished_playing("stopped", 0, 4000, 7.0))       # stuck: give up
        self.assertFalse(finished_playing("playing", 1000, 4000, 1.0))

    def test_if_the_rest_cant_be_voiced_it_is_still_read_out(self):
        from pillway.voice import natural_voice, tts
        long_text = "First sentence that is long enough to stand alone here. " + "More words follow. " * 30
        said = []

        def fake_synthesize(chunk, lang):
            if said:                                  # the second part fails (e.g. a network hiccup)
                raise RuntimeError("voice service hiccup")
            said.append(chunk)
            return "first.mp3"
        with patch.object(natural_voice, "ONE_PIECE", 100), \
                patch.object(natural_voice, "available", return_value=True), \
                patch.object(natural_voice, "synthesize", side_effect=fake_synthesize), \
                patch.object(natural_voice, "play"), \
                patch.object(tts, "_speak_system", side_effect=lambda text, lang, gen: said.append(text)):
            tts._speak_natural(long_text, "en", tts._current["generation"])
        self.assertEqual(len(said), 2)
        self.assertIn("More words follow", said[1])   # the rest was read, not silently dropped


class FillerTests(unittest.TestCase):
    def test_a_slow_reply_gets_a_short_filler_once_and_then_the_reply(self):
        app = call_app()
        app.patient_id = "maria"
        app.service = SimpleNamespace(busy={"maria"})
        app.call_caption_lines = lambda: lines
        lines = []
        app._speak_on_call = lambda text: PillwayApp._speak_on_call(app, text)
        app.call_state["waiting_since"] = time.monotonic() - 2      # 2 s and still no reply
        with patch("pillway.ui.patient.call_audio.speak") as speak:
            PillwayApp._maybe_say_filler(app)
            PillwayApp._maybe_say_filler(app)                       # never twice for one reply
            self.assertEqual(speak.call_count, 1)
            self.assertIn("moment", speak.call_args.args[0])
            lines.append({"role": "sarah", "id": "r1", "text": "Here's my answer."})
            PillwayApp._speak_new_replies(app)                      # waits: filler still playing
            self.assertEqual(speak.call_count, 1)
            speak.call_args.kwargs["on_done"]()
            PillwayApp._speak_new_replies(app)
        self.assertEqual(speak.call_args.args[0], "Here's my answer.")

    def test_a_quick_reply_gets_no_filler(self):
        app = call_app()
        app.patient_id, app.service = "maria", SimpleNamespace(busy={"maria"})
        app.call_state["waiting_since"] = time.monotonic() - 0.4
        with patch("pillway.ui.patient.call_audio.speak") as speak:
            PillwayApp._maybe_say_filler(app)
        speak.assert_not_called()


class KeyLookupTests(unittest.TestCase):
    def test_the_key_saved_in_the_app_wins_and_wrong_company_keys_are_skipped(self):
        import tempfile
        from pathlib import Path
        from config import load_settings
        root = Path(tempfile.mkdtemp())
        (root / ".gitignore").write_text("pillway_config.local.toml\n")
        (root / "pillway_config.toml").write_text('[ai]\nprovider = "deepseek"\n')
        (root / "pillway_config.local.toml").write_text('[ai]\napi_key = " sk-fromtheapp1234 "\n')
        settings = load_settings(root, env={"DEEPSEEK_API_KEY": "sk-oldoldold9999"})
        self.assertEqual(settings.api_key, "sk-fromtheapp1234")        # spaces cleaned, app key wins
        self.assertTrue(any("NOT used" in w for w in settings.warnings))
        (root / "pillway_config.local.toml").write_text('[ai]\napi_key = "AIzaOLDGEMINIKEY"\n')
        settings = load_settings(root, env={"DEEPSEEK_API_KEY": "Bearer sk-rightkey5678"})
        self.assertEqual(settings.api_key, "sk-rightkey5678")          # the Gemini key is skipped
