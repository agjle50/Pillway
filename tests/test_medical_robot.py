import unittest
from datetime import datetime

from pillway.medical_robot import MedicalRobot
from pillway.medical_guidance import MEDICAL_KEYWORDS


class MedicalRobotTests(unittest.TestCase):
    def setUp(self):
        self.robot = MedicalRobot()

    def test_greeting_is_warm_and_asks_how_patient_feels(self):
        greeting = self.robot.greeting(datetime(2026, 1, 1, 9))
        self.assertIn("Good morning", greeting)
        self.assertIn("Sarah", greeting)
        self.assertIn("How are you feeling", greeting)

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

    def test_medication_question_says_not_to_change_dose(self):
        reply = self.robot.reply("Should I stop my medication?")
        self.assertIn("don't stop or change a dose", reply.lower())

    def test_follow_up_responses_use_the_prior_topic_and_vary(self):
        first = self.robot.reply("My blood pressure is high")
        second = self.robot.reply("BP is still high")
        reading = self.robot.reply("145/90")
        self.assertNotEqual(first, second)
        self.assertIn("recent reading", first)
        self.assertIn("symptoms", second)
        self.assertIn("145/90", reading)

    def test_wellness_answer_is_acknowledged(self):
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
