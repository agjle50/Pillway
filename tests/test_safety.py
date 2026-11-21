"""SAFETY TESTS (section 6.4). These must always pass before a demo."""

import unittest

from tests.helpers import use_temp_settings

use_temp_settings()

from pillway.core.flagging import AI_OK, AI_UNAVAILABLE, apply_flag, decide  # noqa: E402
from pillway.core.safety_rules import check_message, load_buzzwords  # noqa: E402
from pillway.storage.patient_store import blank_record, new_id, now_iso  # noqa: E402

NOT_CONCERN = {"is_concern": False, "tier": None, "reason": "Patient says the foot does not hurt.", "ask_next": ""}


class Layer1Tests(unittest.TestCase):
    def test_every_tier1_phrase_triggers_tier1(self):
        for rule in load_buzzwords()["tier1"]:
            for phrase in rule["phrases"]:
                with self.subTest(phrase=phrase):
                    self.assertEqual(check_message(f"Today I noticed {phrase}.").tier, 1)

    def test_demo_foot_message_is_urgent(self):
        result = check_message("I have a sore on my foot that won't heal and my toes feel numb")
        self.assertEqual(result.tier, 1)
        self.assertIn("Where on your foot", result.ask_next)

    def test_cant_feel_toes_is_flagged(self):
        self.assertEqual(check_message("I can't feel my toes").tier, 1)

    def test_curly_quotes_and_plurals_are_normalised(self):
        self.assertEqual(check_message("I can’t feel my toes").tier, 1)
        self.assertEqual(check_message("I have foot sores").tier, 1)

    def test_negation_is_marked_for_ai_not_dropped(self):
        result = check_message("my foot doesn't hurt")
        self.assertIsNone(result.tier)
        self.assertTrue(result.needs_ai_check)
        self.assertTrue(check_message("no vomiting today").needs_ai_check)

    def test_weight_loss_only_with_without_trying_or_unexplained(self):
        self.assertIsNone(check_message("I'm losing weight on my new diet").tier)
        self.assertEqual(check_message("I'm losing weight without trying").tier, 2)
        self.assertEqual(check_message("unexplained weight loss").tier, 2)

    def test_ethnicity_age_and_weight_never_alert(self):
        for text in ("I'm South Asian", "I am Black and in my 50s", "I'm Indigenous", "I'm over 40",
                     "I'm overweight", "my mom has diabetes", "I'm Latino and 62"):
            with self.subTest(text=text):
                result = check_message(text)
                self.assertFalse(result.is_alert)
                self.assertIsNone(decide(result, None, AI_OK)["final_tier"])

    def test_slow_healing_on_feet_is_tier1(self):
        self.assertEqual(check_message("my cuts won't heal").tier, 2)
        self.assertEqual(check_message("the cut on my heel won't heal").tier, 1)

    def test_numeric_thresholds(self):
        self.assertEqual(check_message("my sugar was 2.8 this morning").tier, 1)
        self.assertEqual(check_message("blood sugar 15.2 after lunch").tier, 2)
        self.assertEqual(check_message("glucose 22 mmol").tier, 1)
        self.assertIsNone(check_message("my sugar was 6.4 before breakfast").tier)
        self.assertEqual(check_message("BP was 185/112").tier, 1)
        self.assertEqual(check_message("blood pressure 162/95").tier, 2)
        self.assertIsNone(check_message("blood pressure 142/90").tier)

    def test_pharmacist_custom_words(self):
        self.assertEqual(check_message("my ankle is puffy", extra_words=["puffy"]).tier, 2)


class Layer2CombinationTests(unittest.TestCase):
    def test_foot_doesnt_hurt_resolved_by_layer2(self):
        layer1 = check_message("my foot doesn't hurt")
        self.assertIsNone(decide(layer1, NOT_CONCERN, AI_OK)["final_tier"])

    def test_negation_without_ai_is_not_silent(self):
        decision = decide(check_message("my foot doesn't hurt"), None, AI_UNAVAILABLE)
        self.assertEqual(decision["final_tier"], 2)
        self.assertIn("AI context unavailable", decision["reason"])

    def test_tier1_still_appears_when_ai_is_down(self):
        decision = decide(check_message("I have a foot ulcer"), None, AI_UNAVAILABLE)
        self.assertEqual(decision["final_tier"], 1)
        self.assertIn("AI context unavailable", decision["reason"])

    def test_ai_cannot_downgrade_tier1(self):
        layer1 = check_message("I've been vomiting all night")
        self.assertEqual(decide(layer1, NOT_CONCERN, AI_OK)["final_tier"], 1)
        layer2 = {"is_concern": True, "tier": 2, "reason": "mild", "ask_next": ""}
        self.assertEqual(decide(layer1, layer2, AI_OK)["final_tier"], 1)

    def test_ai_can_add_a_flag_the_word_list_missed(self):
        layer1 = check_message("my big toe has gone a weird purple colour")
        layer2 = {"is_concern": True, "tier": 1, "reason": "Colour change in toe may mean poor blood flow.", "ask_next": "Since when?"}
        decision = decide(layer1, layer2, AI_OK)
        self.assertEqual(decision["final_tier"], 1)

    def test_flags_are_grouped_and_badge_counts_open_only(self):
        record = blank_record("maria")
        for text in ("I have a foot ulcer", "the ulcer is bigger"):
            message = {"id": new_id("msg"), "text": text, "time": now_iso()}
            record["messages"].append(message)
            layer1 = check_message(text)
            apply_flag(record, message, decide(layer1, None, AI_OK), layer1, None)
        self.assertEqual(len(record["flags"]), 1)
        self.assertEqual(len(record["flags"][0]["occurrences"]), 1)


if __name__ == "__main__":
    unittest.main()
