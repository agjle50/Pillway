"""Tests for the read-aloud / speech-to-text fixes (run anywhere, no speakers or mic needed)."""

import queue
import sys
import threading
import unittest
from unittest.mock import patch

from tests.helpers import use_temp_settings

use_temp_settings()

from pillway.voice import speech_input, tts, windows_speech  # noqa: E402


class WindowsSpeechParsingTests(unittest.TestCase):
    def test_lines_become_app_events(self):
        self.assertEqual(windows_speech.parse_line("READY\r\n"), ("state", "listening"))
        self.assertEqual(windows_speech.parse_line("L:50"), ("level", 0.5))
        self.assertEqual(windows_speech.parse_line("L:250"), ("level", 1.0))
        self.assertEqual(windows_speech.parse_line("T: my feet hurt "), ("final", "my feet hurt"))
        self.assertEqual(windows_speech.parse_line("E:no mic")[0], "error")
        self.assertIsNone(windows_speech.parse_line("T:   "))
        self.assertIsNone(windows_speech.parse_line("random noise"))


class ReadAloudTests(unittest.TestCase):
    def _speak_and_wait(self, engines):
        done, errors = threading.Event(), []
        with patch.object(tts, "ENGINES", engines):
            tts.speak("Hello", "en", on_error=errors.append, on_done=done.set)
            self.assertTrue(done.wait(2))
        return errors

    def test_system_voice_is_tried_before_pyttsx3(self):
        calls = []

        def system(text, lang, generation):
            calls.append("system")

        def pyttsx3(text, lang, generation):
            calls.append("pyttsx3")
        self.assertEqual(self._speak_and_wait((system, pyttsx3)), [])
        self.assertEqual(calls, ["system"])

    def test_falls_back_then_reports_a_friendly_error(self):
        def broken(text, lang, generation):
            raise RuntimeError("nope")
        errors = self._speak_and_wait((broken, broken))
        self.assertEqual(len(errors), 1)
        self.assertIn(tts.UNAVAILABLE, errors[0])

    def test_windows_command_passes_text_safely_in_the_environment(self):
        with patch.object(sys, "platform", "win32"), \
                patch("pillway.voice.tts.shutil.which", return_value="powershell.exe"):
            args, env = tts.system_command("Bonjour; Remove-Item C:\\ -Recurse", "fr")
        self.assertNotIn("Bonjour", " ".join(args))       # text is never part of the command
        self.assertEqual(env["PILLWAY_TTS_TEXT"], "Bonjour; Remove-Item C:\\ -Recurse")
        self.assertEqual(env["PILLWAY_TTS_LANG"], "fr")


class SpeechFallbackTests(unittest.TestCase):
    def test_windows_backup_is_used_when_vosk_is_missing(self):
        events = queue.Queue()
        listener = speech_input.LocalSpeechInput("/nowhere", events, transcribe=True)
        used = []
        with patch.dict(sys.modules, {"vosk": None}), \
                patch.object(speech_input.LocalSpeechInput, "_engine", return_value="auto"), \
                patch.object(windows_speech, "available", return_value=True), \
                patch.object(windows_speech, "run", side_effect=lambda l: used.append(l)):
            listener._run()
        self.assertEqual(used, [listener])

    def test_without_backup_a_clear_error_is_shown(self):
        events = queue.Queue()
        listener = speech_input.LocalSpeechInput("/nowhere", events, transcribe=True)
        with patch.dict(sys.modules, {"vosk": None}), \
                patch.object(windows_speech, "available", return_value=False):
            listener._run()
        kind, message = events.get_nowait()
        self.assertEqual(kind, "error")
        self.assertIn("requirements.txt", message)

    def test_missing_sound_library_is_a_friendly_error_not_a_crash(self):
        with patch.dict(sys.modules, {"sounddevice": None}):
            with self.assertRaises(RuntimeError):
                speech_input.resolve_input_device("")


if __name__ == "__main__":
    unittest.main()
