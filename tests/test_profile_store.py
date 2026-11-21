import tempfile
import unittest
from pathlib import Path

from pillway.profile_store import ProfileStore


class ProfileStoreTests(unittest.TestCase):
    def test_new_patient_profiles_persist_with_existing_accounts(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProfileStore(Path(directory) / "profiles.json")
            profiles = store.load()
            patient = ProfileStore.new_patient("Alex")
            profiles.append(patient)
            store.save(profiles)

            restored = store.load()

        self.assertIn(patient, restored)
        self.assertEqual(len([profile for profile in restored if profile["role"] == "Patient"]), 2)

    def test_new_patient_rejects_empty_name(self):
        with self.assertRaises(ValueError):
            ProfileStore.new_patient("  ")


if __name__ == "__main__":
    unittest.main()
