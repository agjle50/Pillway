import io
import queue
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pillway.voice.speech_input import LocalSpeechInput, MODEL_NAME, ensure_model


class ModelResponse(io.BytesIO):
    def __init__(self, content):
        super().__init__(content)
        self.headers = {"Content-Length": str(len(content))}


class SpeechInputTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
