"""The patient flow (section 4), stage script (section 9), French, persistence and live view tests."""

import json
import subprocess
import sys
import unittest

from tests.helpers import use_temp_settings

use_temp_settings()

from config import get_settings  # noqa: E402
from config.loader import ROOT  # noqa: E402
from pillway.core import care_plan  # noqa: E402
from pillway.core.conversation_service import ConversationService  # noqa: E402
from pillway.core.output_guard import check_reply  # noqa: E402
from pillway.core.tasks import is_medication_task  # noqa: E402
from pillway.storage.patient_store import PatientStore  # noqa: E402

STAGE_SCRIPT = ["hi", "I've been feeling dizzy and my doctor started me on a new pill", "I'm not sure what to eat",
                "No", "I have a sore on my foot that won't heal and my toes feel numb", "right heel, 2 weeks, bigger"]


MARIA_INTAKE = {"weight": "78", "weight_unit": "kg", "height": "162", "height_unit": "cm", "checks_bp": "yes",
                "systolic": "142", "diastolic": "90", "tobacco": "no"}


def fresh_service():
    use_temp_settings()
    service = ConversationService()
    service.accept_consent("maria")
    return service


def sarah_texts(record):
    return [m["text"] for m in record["messages"] if m["role"] == "sarah"]


class StageScriptTests(unittest.TestCase):
    def test_full_stage_script(self):
        service = fresh_service()
        service.submit_intake("maria", MARIA_INTAKE)
        for text in STAGE_SCRIPT:
            record = service.handle_message("maria", text)
        replies = sarah_texts(record)
        self.assertIn("142/90", replies[0])
        self.assertIn("Has anything changed", replies[0])
        self.assertIn("Ramipril", replies[1])
        self.assertIn("I've let your pharmacist know", replies[1])
        self.assertIn("limit protein", replies[2])
        self.assertIn("62 to 78 g", replies[3])
        self.assertIn("Where on your foot", replies[4])
        self.assertIn("A pharmacist will contact you soon", replies[4])
        foot = [f for f in record["flags"] if f["tier"] == 1]
        self.assertEqual(len(foot), 1)
        self.assertTrue(foot[0]["details"])
        self.assertEqual([m for m in record["messages"] if m["role"] == "patient"][4]["tier"], 1)
        self.assertTrue(record["possible_issues"])
        for reply in replies:
            self.assertEqual(check_reply(reply, allow_short=True), [], reply)

    def test_one_question_at_a_time(self):
        service = fresh_service()
        for text in ["hi", "no changes", "I eat pretty well", "no", "my feet look fine", "none", "142/90"]:
            record = service.handle_message("maria", text)
            self.assertLessEqual(sarah_texts(record)[-1].count("?"), 1, sarah_texts(record)[-1])

    def test_protein_rule_limits_and_unsure(self):
        for answer, expected in (("Yes, because of my kidneys", "won't suggest a protein amount"),
                                 ("I'm not sure", "won't suggest a protein amount")):
            service = fresh_service()
            for text in ["hi", "no changes", "I'm not sure what to eat", answer]:
                record = service.handle_message("maria", text)
            self.assertIn(expected, sarah_texts(record)[-1])
            self.assertNotIn(" g of protein a day", sarah_texts(record)[-1])
            self.assertTrue(record["pharmacist_requests"])

    def test_protein_question_comes_first_if_patient_asks_about_protein(self):
        service = fresh_service()
        for text in ["hi", "no changes", "How much protein should I eat?"]:
            record = service.handle_message("maria", text)
        self.assertIn("limit protein", sarah_texts(record)[-1])

    def test_wrap_up_care_plan_and_tasks(self):
        service = fresh_service()
        service.submit_intake("maria", MARIA_INTAKE)
        get_settings().patient.max_questions_per_check_in = 3
        for text in ["hi", "no", "I'm not sure what to eat", "no", "my feet look fine", "What to eat",
                     "Eat better", "no"]:
            record = service.handle_message("maria", text)
        self.assertIn("care plan draft is ready", sarah_texts(record)[-1])
        plan = record["care_plan"]
        self.assertEqual(plan["status"], "draft")
        ids = [s["id"] for s in plan["sections"]]
        self.assertEqual(ids, ["smart_goals", "targets", "recommended", "every_day", "medications", "resources"])
        all_ids = {line["id"] for s in plan["sections"] for line in s["lines"]}
        self.assertIn("rec_eye_exam", all_ids)        # retinopathy: a Pillway care plan topic
        self.assertIn("salt_daily", all_ids)          # she has high blood pressure
        self.assertTrue({"res_diabetes", "res_pressure"} <= all_ids)
        # suggested values are filled in but wait for the pharmacist
        a1c = care_plan.find_line(plan, "a1c_target")
        self.assertEqual(a1c["value"], "7.0")
        self.assertTrue(a1c["suggested"] and not a1c["confirmed"] and a1c["reason"])
        self.assertIn(a1c, care_plan.to_check(plan))
        # protein only because she said no doctor limit, computed from her questionnaire weight
        self.assertEqual(care_plan.find_line(plan, "protein")["value"], "")
        self.assertEqual(plan["protein_target"], "62-78")
        # only what her answers support: she wasn't asked about alcohol, she doesn't smoke
        with self.assertRaises(KeyError):
            care_plan.find_line(plan, "alcohol")
        recs = {line["id"] for line in next(s for s in plan["sections"] if s["id"] == "recommended")["lines"]}
        self.assertTrue({"rec_coaching", "rec_labs", "rec_dietitian", "rec_lifestylerx"} <= recs)
        self.assertNotIn("rec_quit_smoking", recs)
        goals = next(s for s in plan["sections"] if s["id"] == "smart_goals")["lines"]
        self.assertTrue(goals and any("week" in g["en"] for g in goals))   # SMART: measurable + timed
        meds = next(s for s in plan["sections"] if s["id"] == "medications")
        self.assertFalse(any(line["ai"] for line in meds["lines"]))
        self.assertTrue(record["tasks"])
        self.assertFalse(any(is_medication_task(t["label_en"]) for t in record["tasks"]))
        text = care_plan.to_text(record)
        self.assertLess(text.index("CARE PLAN"), text.index("PLAN DE SOINS"))


class CarePlanEditTests(unittest.TestCase):
    def test_edit_history_undo_and_approve(self):
        service = fresh_service()
        service.submit_intake("maria", MARIA_INTAKE)
        get_settings().patient.max_questions_per_check_in = 1
        for text in ["hi", "no", "I eat pretty well", "no", "nothing", "my sugar", "walk more", "no"]:
            service.handle_message("maria", text)

        def edit(record):
            care_plan.set_value(record, "a1c_target", "6.5", "Pharmacist demo")
            care_plan.edit_text(record, "bp_daily", "en", "Check your blood pressure every morning.", "Pharmacist demo")
            care_plan.undo_last(record, "Pharmacist demo")
            care_plan.approve(record, "Pharmacist demo")
        record = service.store.update("maria", edit)
        plan = record["care_plan"]
        self.assertEqual(care_plan.find_line(plan, "a1c_target")["value"], "6.5")
        self.assertTrue(care_plan.find_line(plan, "a1c_target")["confirmed"])
        self.assertNotIn("every morning", care_plan.find_line(plan, "bp_daily")["en"])
        self.assertEqual(plan["status"], "approved")
        self.assertEqual(care_plan.to_check(plan), [])      # approving accepted the rest (logged)
        self.assertTrue(any(e["action"] == "accept_suggestions" for e in record["care_plan_history"]))

    def test_foot_sore_reaches_the_pharmacist_and_shapes_the_plan(self):
        service = fresh_service()
        service.submit_intake("maria", MARIA_INTAKE)
        get_settings().patient.max_questions_per_check_in = 3
        for text in ["hi", "no", "I eat pretty well", "no", "I have a sore on my foot that won't heal",
                     "right heel, 2 weeks", "my feet", "heal my foot", "no"]:
            record = service.handle_message("maria", text)
        self.assertTrue(any(f["tier"] == 1 for f in record["flags"]))   # reached the pharmacist at once
        feet = care_plan.find_line(record["care_plan"], "feet_daily")
        self.assertIn("following up on the sore", feet["en"])


class FrenchTests(unittest.TestCase):
    def test_french_conversation_follows_same_rules(self):
        service = fresh_service()
        service.set_language("maria", "fr")
        for text in ["bonjour", "Aucun changement", "Je ne sais pas quoi manger", "Non",
                     "Quelle dose d'insuline dois-je prendre?"]:
            record = service.handle_message("maria", text)
        replies = sarah_texts(record)
        self.assertIn("Y a-t-il eu des changements", replies[0])
        self.assertIn("62 à 78 g", replies[3])
        self.assertIn("excellente question pour votre pharmacien", replies[4])
        for reply in replies:
            self.assertEqual(check_reply(reply, "fr", allow_short=True), [], reply)


class PersistenceTests(unittest.TestCase):
    def test_nothing_is_lost_after_restart(self):
        settings = use_temp_settings()
        service = ConversationService()
        service.accept_consent("maria")
        for text in STAGE_SCRIPT[:4]:
            service.handle_message("maria", text)
        before = service.store.load("maria")
        # a brand-new process reads the same folder (like restarting the app)
        script = ("import json,sys; sys.path.insert(0, %r);"
                  "from config import load_settings, set_settings; s=load_settings(); s.storage.data_folder=%r; set_settings(s);"
                  "from pillway.storage.patient_store import PatientStore; print(json.dumps(PatientStore().load('maria')))"
                  % (str(ROOT), settings.storage.data_folder))
        output = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, cwd=ROOT, check=True)
        after = json.loads(output.stdout)
        self.assertEqual(after["messages"], before["messages"])
        self.assertEqual(after["conversation"], before["conversation"])
        self.assertEqual(after["consent"], before["consent"])

    def test_two_windows_share_one_source_of_truth(self):
        use_temp_settings()
        patient_side, pharmacist_side = PatientStore(), PatientStore()
        stamp = pharmacist_side.stamp()
        ConversationService(store=patient_side).handle_message("maria", "I have a foot ulcer")
        self.assertNotEqual(stamp, pharmacist_side.stamp())
        open_flags = [f for f in pharmacist_side.load("maria")["flags"] if f["status"] == "open"]
        self.assertEqual(len(open_flags), 1)

    def test_reset_demo_restores_maria(self):
        service = fresh_service()
        service.handle_message("maria", "hi")
        service.store.reset_demo()
        record = service.store.load("maria")
        self.assertEqual(record["messages"], [])
        self.assertFalse(record["consent"]["accepted"])


if __name__ == "__main__":
    unittest.main()
