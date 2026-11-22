"""On-device speech transcription for the call preview."""

import json
import queue
import shutil
import tempfile
import threading
import urllib.request
import zipfile
from array import array
from pathlib import Path

from .. import debug_log


MODEL_NAME = "vosk-model-small-en-us-0.15"
MODEL_URL = f"https://alphacephei.com/vosk/models/{MODEL_NAME}.zip"
MAX_MODEL_BYTES = 100_000_000
MAX_EXTRACTED_BYTES = 500_000_000
MIC_BLOCKED_HINT = (
    "The microphone is sending silence. On Windows: Settings > Privacy & security > Microphone > "
    "turn on 'Let desktop apps access your microphone'. On Mac: System Settings > Privacy & "
    "Security > Microphone > allow your terminal or VS Code."
)


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


def input_devices():
    try:
        import sounddevice
    except (ImportError, OSError) as error:
        raise RuntimeError(f"Audio input is unavailable: {error}") from error

    try:
        devices = sounddevice.query_devices()
    except sounddevice.PortAudioError as error:
        raise RuntimeError(f"Could not list microphone devices: {error}") from error

    supported = []
    for index, device in enumerate(devices):
        if device.get("max_input_channels", 0) <= 0:
            continue
        try:
            sounddevice.check_input_settings(
                device=index, channels=1, samplerate=16000, dtype="int16",
            )
        except sounddevice.PortAudioError:
            continue
        supported.append((index, device["name"]))
    return supported


def resolve_input_device(selection=None):
    try:
        import sounddevice
    except (ImportError, OSError) as error:
        raise RuntimeError(f"Audio input is unavailable: {error}") from error

    try:
        devices = sounddevice.query_devices()
    except sounddevice.PortAudioError as error:
        raise RuntimeError(f"Could not list microphone devices: {error}") from error
    if selection is None or not str(selection).strip():
        index = sounddevice.default.device[0]
        if index is None or index < 0:
            raise ValueError("No system-default microphone is selected.")
    elif str(selection).strip().isdigit():
        index = int(str(selection).strip())
    else:
        name = str(selection).strip().casefold()
        matches = [
            item for item, device in enumerate(devices)
            if device.get("max_input_channels", 0) > 0 and name in device["name"].casefold()
        ]
        if not matches:
            raise ValueError(f"No microphone matches '{selection}'. Choose a device in Settings > Microphone.")
        default = sounddevice.default.device[0]
        index = default if default in matches else matches[0]

    if index < 0 or index >= len(devices) or devices[index].get("max_input_channels", 0) <= 0:
        raise ValueError(f"Audio device {index} is not an input microphone.")
    try:
        sounddevice.check_input_settings(
            device=index, channels=1, samplerate=16000, dtype="int16",
        )
    except sounddevice.PortAudioError as error:
        raise ValueError(
            f"Microphone '{devices[index]['name']}' does not support the speech input format: {error}"
        ) from error
    return index


class LocalSpeechInput:
    def __init__(self, model_root, events, device=None, transcribe=True):
        self.device = device
        self.model_root = Path(model_root)
        self.events = events
        self.transcribe = transcribe
        self.language = "en"            # "fr" makes Whisper listen for French
        self.stop_event = threading.Event()
        self.muted_event = threading.Event()
        self.active_engine = ""         # "whisper", "vosk" or "windows" once one has started
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()

    def set_muted(self, muted):
        if muted:
            self.muted_event.set()
        else:
            self.muted_event.clear()

    def is_alive(self):
        return self.thread.is_alive()

    def _engine(self):
        from config import get_settings
        try:
            return get_settings().call.speech_to_text_engine
        except Exception:
            return "auto"

    def _use_windows_backup(self, reason):
        """Vosk couldn't start: on Windows, switch to Windows' own recognizer instead."""
        from . import windows_speech
        if self._engine() in ("auto", "windows") and windows_speech.available():
            debug_log.log("speech", "offline model unavailable; using Windows speech recognition",
                          reason=debug_log.snippet(reason))
            self.active_engine = "windows"
            windows_speech.run(self)
            return True
        return False

    def _run(self):
        engine = self._engine()
        if self.transcribe and engine in ("auto", "whisper"):
            from . import whisper_input
            if whisper_input.available():
                try:
                    self.active_engine = "whisper"
                    debug_log.log("speech", "engine: Whisper (on-device)")
                    whisper_input.run(self)
                    return
                except Exception as error:  # e.g. model download blocked: try the next engine
                    print(f"[speech] Whisper unavailable ({type(error).__name__}: {error})")
                    debug_log.log("speech", "Whisper unavailable", error=f"{type(error).__name__}: {error}")
                    if engine == "whisper":
                        self.events.put(("error", f"Whisper speech recognition failed: {error}"))
                        return
                    self.events.put(("status", "Using the backup speech recognizer…"))
            elif engine == "whisper":
                self.events.put(("error", "Whisper isn't installed. Run: python -m pip install faster-whisper"))
                return
        if engine == "windows" and self.transcribe:
            if self._use_windows_backup("engine set to windows"):
                return
        try:
            import sounddevice
            if self.transcribe:
                from vosk import KaldiRecognizer, Model
        except (ImportError, OSError) as error:
            if self.transcribe and self._use_windows_backup(error):
                return
            self.events.put((
                "error",
                f"{error}. Install the local speech dependencies with "
                "'python -m pip install -r requirements.txt'.",
            ))
            return

        try:
            self.active_engine = "vosk" if self.transcribe else "meter"
            debug_log.log("speech", f"engine: {self.active_engine}")
            self.events.put(("state", "preparing"))
            recognizer = None
            audio_chunks = queue.Queue(maxsize=20)
            recognition_failed = threading.Event()
            if self.transcribe:
                try:
                    model_path = ensure_model(self.model_root, self.stop_event, self.events)
                    if self.stop_event.is_set():
                        self.events.put(("state", "stopped"))
                        return
                    model = Model(str(model_path))
                    recognizer = KaldiRecognizer(model, 16000)
                except InterruptedError:
                    raise
                except Exception as error:  # no internet, blocked download, broken model...
                    if self._use_windows_backup(error):
                        return
                    raise RuntimeError(
                        f"Couldn't get the offline speech model ({type(error).__name__}: {error}). "
                        "Connect to the internet once so it can download (about 40 MB)."
                    ) from error
            silence = {"blocks": 0, "warned": False}

            def on_audio(indata, _frames, _time_info, status):
                if self.stop_event.is_set() or self.muted_event.is_set():
                    return
                try:
                    raw_audio = bytes(indata)
                    level = audio_level(raw_audio)
                    self.events.put(("level", level))
                    # Perfect silence (every sample is 0) for ~4 s usually means the computer
                    # is blocking the microphone, not that the room is quiet.
                    silence["blocks"] = silence["blocks"] + 1 if not any(raw_audio) else 0
                    if silence["blocks"] == 40 and not silence["warned"]:
                        silence["warned"] = True
                        self.events.put(("status", MIC_BLOCKED_HINT))
                    if status:
                        self.events.put(("status", f"Microphone status: {status}"))
                    if recognizer is not None:
                        audio_chunks.put_nowait(raw_audio)
                except queue.Full:
                    self.events.put(("error", "Speech recognition could not keep up with microphone input."))
                    recognition_failed.set()
                    self.stop_event.set()
                except Exception as error:
                    self.events.put((
                        "error",
                        f"Microphone callback failed: {type(error).__name__}: {error}",
                    ))
                    recognition_failed.set()
                    self.stop_event.set()

            with sounddevice.RawInputStream(
                samplerate=16000,
                blocksize=1600,
                device=self.device,
                dtype="int16",
                channels=1,
                callback=on_audio,
            ):
                self.events.put(("state", "listening"))
                was_muted = False
                while not recognition_failed.is_set():
                    if self.stop_event.is_set() and audio_chunks.empty():
                        break
                    if self.muted_event.is_set():
                        # Sarah is talking: forget any half-heard words so her voice can't
                        # leak into the patient's next sentence.
                        if not was_muted and recognizer is not None:
                            recognizer.Reset()
                        was_muted = True
                        while not audio_chunks.empty():
                            try:
                                audio_chunks.get_nowait()
                            except queue.Empty:
                                break
                        self.stop_event.wait(0.05)
                        continue
                    was_muted = False
                    try:
                        raw_audio = audio_chunks.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    try:
                        if recognizer and recognizer.AcceptWaveform(raw_audio):
                            phrase = json.loads(recognizer.Result()).get("text", "").strip()
                            if phrase:
                                self.events.put(("final", phrase))
                        elif recognizer:
                            partial = json.loads(recognizer.PartialResult()).get("partial", "").strip()
                            if partial:
                                self.events.put(("partial", partial))
                    except Exception as error:
                        self.events.put((
                            "error",
                            f"Speech recognition failed: {type(error).__name__}: {error}",
                        ))
                        recognition_failed.set()
                        self.stop_event.set()
                if recognizer is not None and not recognition_failed.is_set():
                    try:
                        phrase = json.loads(recognizer.FinalResult()).get("text", "").strip()
                        if phrase:
                            self.events.put(("final", phrase))
                    except Exception as error:
                        self.events.put((
                            "error",
                            f"Speech recognition failed while finishing: {type(error).__name__}: {error}",
                        ))
            self.events.put(("state", "stopped"))
        except InterruptedError:
            self.events.put(("state", "stopped"))
        except Exception as error:
            self.events.put(("error", f"{type(error).__name__}: {error}"))
