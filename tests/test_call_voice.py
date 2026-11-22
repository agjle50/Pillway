"""Tests for the call redesign's voice pieces (no microphone, speakers or internet needed)."""

import unittest

from tests.helpers import use_temp_settings

use_temp_settings()

from pillway.voice import natural_voice, whisper_input  # noqa: E402


class SpokenTextTests(unittest.TestCase):
    def test_numbers_and_units_are_said_like_a_person(self):
        said = natural_voice.speech_text("Your reading was 142/90 and you take Metformin 500 mg.")
        self.assertIn("142 over 90", said)
        self.assertIn("500 milligrams", said)
        self.assertIn("142 sur 90", natural_voice.speech_text("Votre tension : 142/90.", "fr"))

    def test_bullets_become_separate_short_sentences(self):
        said = natural_voice.speech_text("Here's what I noted:\n• Dizziness\n• A new pill")
        self.assertEqual(natural_voice.sentences(said)[0], "Here's what I noted.")
        self.assertNotIn("•", said)

    def test_ranges_and_symbols(self):
        said = natural_voice.speech_text("Aim for 0.8–1.0 g/kg, e.g. eggs & beans.")
        self.assertIn("0.8 to 1.0 grams per kilogram", said)
        self.assertIn("for example eggs and beans", said.lower())


class SegmenterTests(unittest.TestCase):
    def block(self):
        return b"\x01\x00" * whisper_input.BLOCK

    def test_a_sentence_is_sent_after_a_short_pause(self):
        seg = whisper_input.Segmenter()
        for _ in range(10):
            self.assertIsNone(seg.feed(self.block(), 0.01))      # room noise
        for _ in range(12):
            self.assertIsNone(seg.feed(self.block(), 0.30))      # speaking
        results = [seg.feed(self.block(), 0.01) for _ in range(10)]  # pause
        finished = [r for r in results if r]
        self.assertEqual(len(finished), 1)
        self.assertGreater(len(finished[0]), 12 * whisper_input.BLOCK * 2)

    def test_a_click_is_ignored(self):
        seg = whisper_input.Segmenter()
        for _ in range(10):
            seg.feed(self.block(), 0.01)
        seg.feed(self.block(), 0.4)                               # one loud click
        results = [seg.feed(self.block(), 0.01) for _ in range(12)]
        self.assertFalse(any(results))

    def test_noise_words_are_dropped(self):
        class Seg:
            def __init__(self, text):
                self.text, self.no_speech_prob = text, 0.1

        class Model:
            def __init__(self, text):
                self.text = text

            def transcribe(self, audio, **options):
                self.options = options
                return [Seg(self.text)], None
        raw = b"\x00\x00" * 1600
        self.assertEqual(whisper_input.transcribe(Model(" Thank you."), raw, "en"), "")
        model = Model(" My heel is sore.")
        self.assertEqual(whisper_input.transcribe(model, raw, "en"), "My heel is sore.")
        self.assertIn("Metformin", model.options["initial_prompt"])


if __name__ == "__main__":
    unittest.main()
