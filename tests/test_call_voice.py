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


class WhisperRunTests(unittest.TestCase):
    """The full listen loop with a fake microphone and a fake Whisper model."""

    def run_listener(self, loud_blocks, stop_after_quiet):
        import queue
        import sys
        import threading
        from types import SimpleNamespace
        from unittest.mock import patch

        class Stream:
            def __init__(self, callback=None, **_):
                self.callback = callback

            def __enter__(self):
                def feed():
                    loud = (b"\x00\x30" * whisper_input.BLOCK)
                    quiet = (b"\x01\x00" * whisper_input.BLOCK)
                    for _ in range(5):
                        self.callback(quiet, 0, None, None)
                    for _ in range(loud_blocks):
                        self.callback(loud, 0, None, None)
                    for _ in range(stop_after_quiet):
                        self.callback(quiet, 0, None, None)
                    time.sleep(0.3)
                    listener.stop_event.set()          # the user taps the mic to stop
                threading.Thread(target=feed, daemon=True).start()
                return self

            def __exit__(self, *a):
                return False

        class Model:
            def transcribe(self, audio, **_):
                time.sleep(0.2)                        # transcription takes a moment
                return [SimpleNamespace(text=" Can I take this with food?", no_speech_prob=0.05)], None

        import time
        listener = SimpleNamespace(events=queue.Queue(), stop_event=threading.Event(), muted_event=threading.Event(),
                                   transcribe=True, device=None, language="en")
        fake_sd = SimpleNamespace(RawInputStream=Stream)
        with patch.dict(sys.modules, {"sounddevice": fake_sd}):
            whisper_input.run(listener, model=Model())
        events = []
        while not listener.events.empty():
            events.append(listener.events.get())
        return events

    def test_stopping_right_after_speaking_keeps_the_words(self):
        events = self.run_listener(loud_blocks=12, stop_after_quiet=1)   # stopped before the 0.8 s pause
        finals = [value for kind, value in events if kind == "final"]
        self.assertEqual(finals, ["Can I take this with food?"])
        self.assertEqual(events[-1], ("state", "stopped"))               # "stopped" comes AFTER the words

    def test_a_normal_pause_sends_the_sentence_once(self):
        events = self.run_listener(loud_blocks=12, stop_after_quiet=12)
        self.assertEqual([v for k, v in events if k == "final"], ["Can I take this with food?"])
