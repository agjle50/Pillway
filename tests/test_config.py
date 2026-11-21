"""Tests for config/: defaults, validation messages, API key lookup and the key safety net."""

import tempfile
import unittest
from pathlib import Path

from config import ConfigError, load_settings
from config.loader import ROOT

FAKE_KEY = "sk-ant-" + "x" * 30 + "ABCD"


class ConfigTests(unittest.TestCase):
    def make_root(self, shared="", local=None, dotenv=None, gitignore="pillway_config.local.toml\n"):
        folder = Path(tempfile.mkdtemp())
        (folder / "pillway_config.toml").write_text(shared, encoding="utf-8")
        if local is not None:
            (folder / "pillway_config.local.toml").write_text(local, encoding="utf-8")
        if dotenv is not None:
            (folder / ".env").write_text(dotenv, encoding="utf-8")
        (folder / ".gitignore").write_text(gitignore, encoding="utf-8")
        return folder

    def test_real_repo_config_loads(self):
        settings = load_settings(ROOT, env={})
        self.assertEqual(settings.ai.flag_model, "claude-haiku-5-5")
        self.assertTrue(settings.ai.deidentify_before_ai)

    def test_defaults_when_file_is_empty(self):
        settings = load_settings(self.make_root(), env={})
        self.assertEqual(settings.ai.chat_model, "claude-opus-5-5")
        self.assertEqual(settings.branding.assistant_name, "Sarah")

    def test_typo_gives_plain_english_error_naming_the_setting(self):
        root = self.make_root('[safety]\nblood_sugar_high = "lots"\n')
        with self.assertRaises(ConfigError) as caught:
            load_settings(root, env={})
        self.assertIn("`blood_sugar_high` must be a number", str(caught.exception))

    def test_local_file_overrides_shared_file(self):
        root = self.make_root('[ai]\nchat_model = "claude-opus-5-5"\n',
                              local='[ai]\nchat_model = "claude-haiku-5-5"\n')
        self.assertEqual(load_settings(root, env={}).ai.chat_model, "claude-haiku-5-5")

    def test_key_lookup_order(self):
        root = self.make_root(local=f'[ai]\napi_key = "{FAKE_KEY}"\n',
                              dotenv="ANTHROPIC_API_KEY=from-dotenv\n")
        self.assertEqual(load_settings(root, env={"ANTHROPIC_API_KEY": "from-env"}).api_key, "from-env")
        self.assertEqual(load_settings(root, env={}).api_key, FAKE_KEY)
        (root / "pillway_config.local.toml").write_text("", encoding="utf-8")
        self.assertEqual(load_settings(root, env={}).api_key, "from-dotenv")

    def test_no_key_means_empty_key(self):
        settings = load_settings(self.make_root(), env={})
        self.assertEqual(settings.api_key, "")
        self.assertEqual(settings.masked_key(), "(none)")

    def test_key_is_masked_in_repr(self):
        settings = load_settings(self.make_root(local=f'[ai]\napi_key = "{FAKE_KEY}"\n'), env={})
        self.assertNotIn(FAKE_KEY, repr(settings))
        self.assertIn("ABCD", settings.masked_key())

    def test_key_in_shared_file_refuses_to_start(self):
        root = self.make_root(f'# {FAKE_KEY}\n')
        with self.assertRaises(ConfigError) as caught:
            load_settings(root, env={})
        self.assertIn("Remove your API key from this file", str(caught.exception))

    def test_missing_gitignore_entry_warns(self):
        settings = load_settings(self.make_root(gitignore=""), env={})
        self.assertTrue(any(".gitignore" in warning for warning in settings.warnings))

    def test_choice_setting_lists_allowed_values(self):
        root = self.make_root('[patient]\ndefault_language = "es"\n')
        with self.assertRaises(ConfigError) as caught:
            load_settings(root, env={})
        self.assertIn('"en", "fr"', str(caught.exception))


if __name__ == "__main__":
    unittest.main()
