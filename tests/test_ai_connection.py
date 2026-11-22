"""Settings > AI connection: the key is saved only to the gitignored local file."""

import tempfile
import unittest
from pathlib import Path

from tests.helpers import use_temp_settings

use_temp_settings()

try:
    from pillway.ui.patient.ai_connection import KEY_PATTERN, save_key_to_local_file
except ImportError:  # no tkinter on this computer
    raise unittest.SkipTest("tkinter is not installed")

KEY = "sk-ant-api03-" + "a" * 40


class SaveKeyTests(unittest.TestCase):
    def test_creates_the_local_file_with_an_ai_section(self):
        with tempfile.TemporaryDirectory() as folder:
            path = save_key_to_local_file(Path(folder), KEY)
            self.assertEqual(path.name, "pillway_config.local.toml")
            self.assertIn(f'[ai]\napi_key = "{KEY}"', path.read_text())

    def test_replaces_an_old_key_and_keeps_other_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "pillway_config.local.toml"
            path.write_text('[ai]\napi_key = "old"\nchat_model = "claude-haiku-5-5"\n')
            save_key_to_local_file(Path(folder), KEY)
            text = path.read_text()
            self.assertIn(KEY, text)
            self.assertNotIn('"old"', text)
            self.assertIn('chat_model = "claude-haiku-5-5"', text)

    def test_only_real_looking_keys_are_accepted(self):
        self.assertTrue(KEY_PATTERN.match(KEY))
        for bad in ("", "hello", "sk-ant-short", "sk-proj-" + "a" * 40):
            self.assertFalse(KEY_PATTERN.match(bad))

    def test_the_local_file_is_gitignored(self):
        root = Path(__file__).resolve().parents[1]
        self.assertIn("pillway_config.local.toml", (root / ".gitignore").read_text())


if __name__ == "__main__":
    unittest.main()
