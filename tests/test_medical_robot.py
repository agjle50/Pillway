import unittest
from datetime import datetime

from pillway.core.medical_robot import MedicalRobot
from pillway.core.medical_guidance import MEDICAL_KEYWORDS


class MedicalRobotTests(unittest.TestCase):
    def setUp(self):
        self.robot = MedicalRobot()

    def test_greeting_is_warm_and_asks_how_patient_feels(self):
        greeting = self.robot.greeting(datetime(2026, 1, 1, 9))
        self.assertIn("Good morning", greeting)
        self.assertIn("Sarah", greeting)
        self.assertIn("diabetes and hypertension", greeting)
        self.assertIn("anything changed", greeting)

    def test_short_assessment_no_change_records_summary(self):
        self.robot.greeting(datetime(2026, 1, 1, 9))
        reply = self.robot.reply("No changes")
        self.assertIn("diabetes and hypertension", reply)
        self.assertIn("no new changes", reply)

    def test_short_assessment_change_requests_details_then_summarizes(self):
        self.robot.greeting(datetime(2026, 1, 1, 9))
        prompt = self.robot.reply("Yes, something changed")
        self.assertIn("What has changed", prompt)
        summary = self.robot.reply("My sleep schedule has changed")
        self.assertIn("my sleep schedule has changed", summary.lower())
        self.assertIn("not a diagnosis", summary)

    def test_vague_check_in_uses_claude_placeholder(self):
        self.robot.greeting(datetime(2026, 1, 1, 9))
        self.assertEqual(self.robot.reply("recent"), "Prompt Claude")

    def test_blood_sugar_guidance_uses_care_plan_and_avoids_dose_changes(self):
        reply = self.robot.reply("I'm worried about my glucose")
        self.assertIn("A1C", reply)
        self.assertIn("don't change", reply)

    def test_off_topic_message_is_redirected(self):
        reply = self.robot.reply("Who won the game last night?")
        self.assertIn("blood sugar", reply)
        self.assertIn("health concern", reply)

    def test_emergency_symptom_gets_urgent_escalation(self):
        reply = self.robot.reply("I have chest pain")
        self.assertIn("emergency number now", reply)

    def test_denied_emergency_symptom_is_not_treated_as_present(self):
        self.assertFalse(self.robot._has_emergency_sign("I do not have chest pain"))

    def test_acute_keyword_escalates_without_diagnosing(self):
        reply = self.robot.reply("I've been throwing up")
        self.assertIn("emergency medical help now", reply)
        self.assertIn("can't diagnose", reply)

    def test_hyperglycemia_symptoms_prompt_clinical_assessment(self):
        reply = self.robot.reply("I'm constantly thirsty and peeing a lot")
        self.assertIn("excessive thirst", reply)
        self.assertIn("frequent urination", reply)
        self.assertIn("don't diagnose diabetes", reply)
        self.assertIn("healthcare professional", reply)

    def test_risk_history_and_age_are_acknowledged_without_diagnosis(self):
        reply = self.robot.reply("My mother has diabetes and I'm 45")
        self.assertIn("family history", reply)
        self.assertIn("age 40 or older", reply)
        self.assertIn("don't mean you have diabetes", reply)

    def test_negated_acute_symptom_does_not_escalate(self):
        reply = self.robot.reply("I don't have nausea")
        self.assertNotIn("emergency medical help now", reply)

    def test_medication_question_says_not_to_change_dose(self):
        reply = self.robot.reply("Should I stop my medication?")
        self.assertIn("don't stop or change a dose", reply.lower())

    def test_follow_up_responses_use_the_prior_topic_and_vary(self):
        first = self.robot.reply("My blood pressure is high")
        second = self.robot.reply("BP is still high")
        reading = self.robot.reply("145/90")
        self.assertNotEqual(first, second)
        self.assertIn("cuff", first)
        self.assertIn("symptoms", second)
        self.assertIn("145/90", reading)

    def test_blood_pressure_follow_up_understands_recent_and_asks_for_cuff_reading(self):
        first = self.robot.reply("My blood pressure is high")
        recent = self.robot.reply("recent")
        self.assertIn("cuff", first)
        self.assertIn("don't rely on feeling alone", first)
        self.assertIn("top and bottom numbers", recent)

    def test_blood_pressure_follow_up_responds_to_patient_suspecting_it_is_high(self):
        self.robot.reply("My blood pressure is high")
        reply = self.robot.reply("I feel like my BP is high?")
        self.assertIn("What are you feeling", reply)
        self.assertIn("cuff reading", reply)

    def test_initial_blood_pressure_reading_is_included_in_response(self):
        reply = self.robot.reply("My blood pressure is 148/92")
        self.assertIn("148/92", reply)
        self.assertIn("One reading alone", reply)

    def test_alert_keywords_are_available_for_chat_highlighting(self):
        self.assertTrue(self.robot.has_alert_keyword("I'm constantly thirsty"))
        self.assertFalse(self.robot.has_alert_keyword("I don't have nausea"))

    def test_wellness_answer_is_acknowledged(self):
        self.robot.assessment_stage = "complete"
        self.assertIn("glad", self.robot.reply("I feel fine").lower())

    def test_keyword_rules_can_be_extended(self):
        glucose_rule = MEDICAL_KEYWORDS[0]
        glucose_rule["keywords"].append("sugar tracker")
        try:
            self.assertIn("A1C", self.robot.reply("I use a sugar tracker"))
        finally:
            glucose_rule["keywords"].remove("sugar tracker")


if __name__ == "__main__":
    unittest.main()
