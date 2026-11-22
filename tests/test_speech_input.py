import io
import queue
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pillway.voice.speech_input import (
    LocalSpeechInput,
    MODEL_NAME,
    audio_level,
    ensure_model,
    input_devices,
    resolve_input_device,
)


class ModelResponse(io.BytesIO):
    def __init__(self, content):
        super().__init__(content)
        self.headers = {"Content-Length": str(len(content))}


class SpeechInputTests(unittest.TestCase):
    def test_audio_level_tracks_volume_and_silence(self):
        quiet = audio_level(b"\x01\x00")
        loud = audio_level(b"\x00\x40")

        self.assertEqual(audio_level(b"\x00\x00"), 0.0)
        self.assertGreater(loud, quiet)
        self.assertLessEqual(loud, 1.0)

    def test_microphone_selection_resolves_default_name_and_device_zero(self):
        class FakePortAudioError(Exception):
            pass

        devices = [
            {"name": "USB Microphone", "max_input_channels": 1},
            {"name": "Built-in Microphone", "max_input_channels": 2},
            {"name": "Speakers", "max_input_channels": 0},
        ]
        fake_sounddevice = SimpleNamespace(
            PortAudioError=FakePortAudioError,
            default=SimpleNamespace(device=(1, 2)),
            query_devices=lambda: devices,
            check_input_settings=lambda **_options: None,
        )
        with patch.dict("sys.modules", {"sounddevice": fake_sounddevice}):
            self.assertEqual(resolve_input_device(), 1)
            self.assertEqual(resolve_input_device("0"), 0)
            self.assertEqual(resolve_input_device("USB"), 0)
            self.assertEqual(input_devices(), [(0, "USB Microphone"), (1, "Built-in Microphone")])

        self.assertEqual(LocalSpeechInput(Path("."), queue.Queue(), device=0).device, 0)

    def make_model_archive(self, entries):
        archive_bytes = io.BytesIO()
        with zipfile.ZipFile(archive_bytes, "w") as archive:
            for name, content in entries:
                archive.writestr(name, content)
        return archive_bytes.getvalue()

    def test_download_extracts_model_to_local_cache(self):
        content = self.make_model_archive((
            (f"{MODEL_NAME}/am/final.mdl", "model"),
            (f"{MODEL_NAME}/conf/mfcc.conf", "configuration"),
        ))
        with tempfile.TemporaryDirectory() as directory:
            with patch("pillway.voice.speech_input.urllib.request.urlopen",
                       return_value=ModelResponse(content)):
                model_path = ensure_model(Path(directory) / "models",
                                          threading.Event(), queue.Queue())

            self.assertTrue((model_path / "am" / "final.mdl").is_file())
            self.assertTrue((model_path / "conf" / "mfcc.conf").is_file())

    def test_model_archive_rejects_paths_outside_cache(self):
        content = self.make_model_archive((
            ("../escape.txt", "unsafe"),
            (f"{MODEL_NAME}/am/final.mdl", "model"),
            (f"{MODEL_NAME}/conf/mfcc.conf", "configuration"),
        ))
        with tempfile.TemporaryDirectory() as directory:
            model_root = Path(directory) / "models"
            with patch("pillway.voice.speech_input.urllib.request.urlopen",
                       return_value=ModelResponse(content)):
                with self.assertRaisesRegex(ValueError, "unsafe path"):
                    ensure_model(model_root, threading.Event(), queue.Queue())

            self.assertFalse((Path(directory) / "escape.txt").exists())

    def test_listener_transcribes_locally_and_stops_cleanly(self):
        events = queue.Queue()
        listener = None

        class FakeRecognizer:
            def __init__(self, _model, _sample_rate):
                pass

            def AcceptWaveform(self, _audio):
                return True

            def Result(self):
                return '{"text": "hello locally"}'

            def FinalResult(self):
                return '{"text": ""}'

        class FakeInputStream:
            def __init__(self, **options):
                self.callback = options["callback"]

            def __enter__(self):
                self.callback(b"\0\0", 1, None, None)
                listener.stop_event.set()
                return self

            def __exit__(self, *_args):
                return False

        fake_sounddevice = SimpleNamespace(RawInputStream=FakeInputStream)
        fake_vosk = SimpleNamespace(
            Model=lambda _path: object(),
            KaldiRecognizer=FakeRecognizer,
        )
        with tempfile.TemporaryDirectory() as directory:
            listener = LocalSpeechInput(Path(directory), events)
            with patch("pillway.voice.speech_input.ensure_model", return_value=Path(directory)), patch.dict(
                "sys.modules",
                {"sounddevice": fake_sounddevice, "vosk": fake_vosk},
            ):
                listener.start()
                listener.thread.join(timeout=2)

        self.assertFalse(listener.is_alive())
        self.assertIn(("final", "hello locally"), list(events.queue))

    def test_recognizer_failure_is_reported_without_escaping_audio_callback(self):
        events = queue.Queue()
        callback_errors = []

        class FakeRecognizer:
            def __init__(self, _model, _sample_rate):
                pass

            def AcceptWaveform(self, _audio):
                raise RuntimeError("Failed to process waveform")

            def FinalResult(self):
                return '{"text": ""}'

        class FakeInputStream:
            def __init__(self, **options):
                self.callback = options["callback"]

            def __enter__(self):
                try:
                    self.callback(b"\0\0", 1, None, None)
                except Exception as error:
                    callback_errors.append(error)
                listener.stop_event.set()
                return self

            def __exit__(self, *_args):
                return False

        fake_sounddevice = SimpleNamespace(RawInputStream=FakeInputStream)
        fake_vosk = SimpleNamespace(
            Model=lambda _path: object(),
            KaldiRecognizer=FakeRecognizer,
        )
        with tempfile.TemporaryDirectory() as directory:
            listener = LocalSpeechInput(Path(directory), events)
            with patch("pillway.voice.speech_input.ensure_model", return_value=Path(directory)), patch.dict(
                "sys.modules",
                {"sounddevice": fake_sounddevice, "vosk": fake_vosk},
            ):
                listener.start()
                listener.thread.join(timeout=2)

        self.assertFalse(listener.is_alive())
        self.assertEqual(callback_errors, [])
        self.assertTrue(any(
            kind == "error" and "Failed to process waveform" in value
            for kind, value in events.queue
        ))

    def test_meter_only_listener_does_not_load_transcription_model(self):
        events = queue.Queue()
        listener = None

        class FakeInputStream:
            def __init__(self, **options):
                self.callback = options["callback"]

            def __enter__(self):
                self.callback(b"\x00\x40", 1, None, None)
                listener.stop_event.set()
                return self

            def __exit__(self, *_args):
                return False

        with tempfile.TemporaryDirectory() as directory:
            listener = LocalSpeechInput(Path(directory), events, transcribe=False)
            with patch.dict(
                "sys.modules",
                {"sounddevice": SimpleNamespace(RawInputStream=FakeInputStream)},
            ), patch("pillway.voice.speech_input.ensure_model") as ensure:
                listener.start()
                listener.thread.join(timeout=2)

        self.assertFalse(listener.is_alive())
        self.assertIn(("state", "listening"), list(events.queue))
        self.assertGreater(next(value for kind, value in events.queue if kind == "level"), 0)
        ensure.assert_not_called()

    def test_muted_listener_discards_microphone_audio(self):
        events = queue.Queue()
        listener = LocalSpeechInput(Path("."), events, transcribe=False)
        listener.set_muted(True)

        class FakeInputStream:
            def __init__(self, **options):
                self.callback = options["callback"]

            def __enter__(self):
                self.callback(b"\x00\x40", 1, None, None)
                listener.stop_event.set()
                return self

            def __exit__(self, *_args):
                return False

        with patch.dict(
            "sys.modules",
            {"sounddevice": SimpleNamespace(RawInputStream=FakeInputStream)},
        ):
            listener.start()
            listener.thread.join(timeout=2)

        self.assertNotIn("level", [kind for kind, _value in events.queue])


if __name__ == "__main__":
    unittest.main()
