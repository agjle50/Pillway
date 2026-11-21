"""On-device speech transcription for the call preview."""

import json
from array import array
import shutil
import tempfile
import threading
import urllib.request
import zipfile
from pathlib import Path


MODEL_NAME = "vosk-model-small-en-us-0.15"
MODEL_URL = f"https://alphacephei.com/vosk/models/{MODEL_NAME}.zip"
MAX_MODEL_BYTES = 100_000_000
MAX_EXTRACTED_BYTES = 500_000_000


def ensure_model(model_root, stop_event, events):
    if stop_event.is_set():
        raise InterruptedError("Speech model download cancelled.")
    model_root = Path(model_root)
    model_path = model_root / MODEL_NAME
    if model_path.exists():
        if (model_path / "am").is_dir() and (model_path / "conf").is_dir():
            return model_path
        raise ValueError(f"The offline speech model folder is incomplete: {model_path}")

    model_root.mkdir(parents=True, exist_ok=True)
    temporary_archive = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix="vosk-model-", suffix=".zip", dir=model_root, delete=False,
        ) as archive_file:
            temporary_archive = Path(archive_file.name)
            with urllib.request.urlopen(MODEL_URL, timeout=30) as response:
                content_length = response.headers.get("Content-Length")
                expected_bytes = int(content_length) if content_length else None
                if expected_bytes and expected_bytes > MAX_MODEL_BYTES:
                    raise ValueError("The offline speech model download is unexpectedly large.")
                downloaded = 0
                reported_percent = -10
                while True:
                    if stop_event.is_set():
                        raise InterruptedError("Speech model download cancelled.")
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    downloaded += len(chunk)
                    if downloaded > MAX_MODEL_BYTES:
                        raise ValueError("The offline speech model download exceeded its size limit.")
                    archive_file.write(chunk)
                    if expected_bytes:
                        percent = min(100, downloaded * 100 // expected_bytes)
                        if percent >= reported_percent + 10:
                            events.put(("status", f"Downloading offline model: {percent}%"))
                            reported_percent = percent
        if expected_bytes and downloaded != expected_bytes:
            raise ValueError("The offline speech model download was incomplete.")

        if stop_event.is_set():
            raise InterruptedError("Speech model download cancelled.")
        with tempfile.TemporaryDirectory(prefix="vosk-extract-", dir=model_root) as staging:
            staging_path = Path(staging)
            with zipfile.ZipFile(temporary_archive) as archive:
                staging_root = staging_path.resolve()
                members = archive.infolist()
                if sum(member.file_size for member in members) > MAX_EXTRACTED_BYTES:
                    raise ValueError("The offline speech model archive expands beyond its size limit.")
                for member in members:
                    destination = (staging_path / member.filename).resolve()
                    if destination != staging_root and staging_root not in destination.parents:
                        raise ValueError("The speech model archive contains an unsafe path.")
                archive.extractall(staging_path)
            extracted_model = staging_path / MODEL_NAME
            if not (extracted_model / "am").is_dir() or not (extracted_model / "conf").is_dir():
                raise ValueError("The downloaded file is not a valid offline speech model.")
            if stop_event.is_set():
                raise InterruptedError("Speech model installation cancelled.")
            shutil.move(str(extracted_model), str(model_path))
        return model_path
    finally:
        if temporary_archive and temporary_archive.exists():
            temporary_archive.unlink()


def audio_level(raw_bytes):
    """0.0 (silent) to 1.0 (loud) from 16-bit audio, for the green voice meter."""
    samples = array("h", bytes(raw_bytes)[: len(raw_bytes) - len(raw_bytes) % 2])
    if not samples:
        return 0.0
    rms = (sum(value * value for value in samples) / len(samples)) ** 0.5
    return min(1.0, rms / 6000)


class LocalSpeechInput:
    def __init__(self, model_root, events, device=None):
        self.device = device or None
        self.model_root = Path(model_root)
        self.events = events
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()

    def is_alive(self):
        return self.thread.is_alive()

    def _run(self):
        try:
            import sounddevice
            from vosk import KaldiRecognizer, Model
        except ImportError as error:
            self.events.put((
                "error",
                f"{error}. Install the local speech dependencies with "
                "'python -m pip install -r requirements.txt'.",
            ))
            return

        try:
            self.events.put(("state", "preparing"))
            model_path = ensure_model(self.model_root, self.stop_event, self.events)
            if self.stop_event.is_set():
                self.events.put(("state", "stopped"))
                return

            model = Model(str(model_path))
            recognizer = KaldiRecognizer(model, 16000)

            def on_audio(indata, _frames, _time_info, status):
                self.events.put(("level", audio_level(indata)))
                if status:
                    self.events.put(("status", f"Microphone status: {status}"))
                if recognizer.AcceptWaveform(bytes(indata)):
                    phrase = json.loads(recognizer.Result()).get("text", "").strip()
                    if phrase:
                        self.events.put(("final", phrase))
                else:
                    partial = json.loads(recognizer.PartialResult()).get("partial", "").strip()
                    if partial:
                        self.events.put(("partial", partial))

            with sounddevice.RawInputStream(
                samplerate=16000,
                blocksize=1600,
                device=self.device,
                dtype="int16",
                channels=1,
                callback=on_audio,
            ):
                self.events.put(("state", "listening"))
                while not self.stop_event.wait(0.1):
                    pass
                phrase = json.loads(recognizer.FinalResult()).get("text", "").strip()
                if phrase:
                    self.events.put(("final", phrase))
            self.events.put(("state", "stopped"))
        except InterruptedError:
            self.events.put(("state", "stopped"))
        except Exception as error:
            self.events.put(("error", f"{type(error).__name__}: {error}"))
