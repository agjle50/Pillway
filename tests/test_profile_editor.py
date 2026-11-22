import json
import unittest
from pathlib import Path
from unittest.mock import Mock

from pillway.ui.patient.manage_profiles import (
    COMPLETION_FIELDS,
    format_profile_address,
    profile_completion,
    profile_form_values,
)
from pillway.ui.pharmacist.consult_pages import ConsultPagesMixin


class ProfileEditorTests(unittest.TestCase):
    def test_completion_tracks_every_profile_editor_field(self):
        complete = {field: "filled" for field in COMPLETION_FIELDS}
        self.assertEqual(profile_completion({"profile": complete}), 100)
        self.assertEqual(profile_completion({"profile": {"first_name": "Alex", "last_name": "Lee"}}), 9)

    def test_seeded_maria_template_is_nearly_complete(self):
        seed_path = Path(__file__).parent.parent / "data" / "seed_patients.json"
        seed = json.loads(seed_path.read_text(encoding="utf-8"))["patients"]["maria"]
        self.assertGreaterEqual(profile_completion(seed), 90)
        self.assertLess(profile_completion(seed), 100)

    def test_seed_address_is_split_for_editing_and_reassembled(self):
        values = profile_form_values({
            "first_name": "Maria",
            "address": "12 Example St, Brampton ON",
        })
        self.assertEqual(values["street_address"], "12 Example St")
        self.assertEqual(values["city"], "Brampton")
        self.assertEqual(values["province"], "Ontario")
        self.assertEqual(format_profile_address(values), "12 Example St, Brampton Ontario")


class DoctorPatientDetailsTests(unittest.TestCase):
    def setUp(self):
        self.page = ConsultPagesMixin()
        self.page.S = lambda value: value
        self.page.font = Mock(return_value=("font",))
        self.page.text = Mock()
        self.page.c = Mock()
        self.page._doctor_card = Mock()
        self.page._doctor_field = Mock()

    def test_account_notes_use_values_from_the_patient_record(self):
        patient = {
            "name": "Maria Rossi",
            "profile": {
                "date_of_birth": "1968-03-14",
                "sex": "Female",
                "health_card": "1234-567-890-AB",
                "phone": "(416) 555-0198",
                "email": "maria.demo@example.com",
                "address": "12 Example St, Brampton ON",
                "language": "en",
                "pharmacy": "Pillway",
                "prescriber": "Dr. A. Chen",
            },
        }

        self.page._draw_doctor_account_page(0, 0, 600, 1000, patient)

        fields = {(item.args[3], item.args[4]) for item in self.page._doctor_field.call_args_list}
        self.assertIn(("Date of birth", "1968-03-14"), fields)
        self.assertIn(("Phone", "(416) 555-0198"), fields)
        self.assertIn(("Address", "12 Example St, Brampton ON"), fields)
        self.assertIn(("Pharmacy / prescriber", "Pillway / Dr. A. Chen"), fields)
        self.assertNotIn(("Date of birth", "Not provided"), fields)

    def test_clinical_notes_use_recorded_demographics_and_measurements(self):
        patient = {"profile": {
            "age": 58, "sex": "Female", "height_cm": 162, "weight_kg": 78,
            "conditions": ["Type 2 diabetes", "High blood pressure"],
            "last_a1c": "7.4%", "last_bp": "142/90",
        }}

        self.page._draw_doctor_patient_page(0, 0, 1000, patient)

        fields = {(item.args[3], item.args[4]) for item in self.page._doctor_field.call_args_list}
        self.assertIn(("Age", "58"), fields)
        self.assertIn(("Height / weight", "162 cm / 78 kg"), fields)
        self.assertIn(("A1C", "7.4%"), fields)
        self.assertIn(("Blood pressure", "142/90"), fields)


if __name__ == "__main__":
    unittest.main()
