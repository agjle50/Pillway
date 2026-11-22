"""Accurate on-device speech-to-text with Whisper (the `faster-whisper` package).

Called by: voice/speech_input.py, first choice when installed ("auto" or "whisper").
Why: the small Vosk model often mishears people. Whisper understands natural speech and
accents much better, still runs entirely on this computer (no audio leaves it), and is
primed with the words this app expects (medications, symptoms) so they come out right.

How it works (plain words):
1. The microphone streams audio in 0.1-second blocks; each block's loudness feeds the meter.
2. A simple voice detector notices when you START talking (louder than the room's
   background noise) and when you STOP (about 0.8 s of quiet).
3. That whole sentence is handed to Whisper in a background thread; the text comes back
   as a "final" event, exactly like the other engines, so the rest of the app is unchanged.
The model (about 140 MB for "base") downloads once into the app's data folder.
"""

import queue
import threading
import time

from .speech_input import MIC_BLOCKED_HINT, audio_level

RATE = 16000
BLOCK = 1600                       # 0.1 s
END_SILENCE = 0.8                  # seconds of quiet that end a sentence
MAX_UTTERANCE = 20.0               # seconds; longer speech is cut and sent in pieces
PRE_ROLL = 3                       # blocks kept from just before speech started

# Words Whisper should expect. Priming like this fixes most "completely wrong" medical words.
PROMPT = {
    "en": ("A friendly check-in call with a pharmacy care assistant about diabetes and blood pressure. "
           "Words: Metformin, Ramipril, insulin, blood sugar, mmol, A1C, blood pressure, dizzy, numbness, "
           "tingling, sore on my foot, heel, toes, pharmacist, protein, walking, yes, no."),
    "fr": ("Un appel de suivi avec une assistante de soins de la pharmacie, au sujet du diabète et de la "
           "tension artérielle. Mots : Metformine, Ramipril, insuline, glycémie, mmol, pression, étourdi, "
           "engourdissement, picotements, plaie au pied, talon, orteils, pharmacien, protéines, oui, non."),
}
# Whisper sometimes "hears" these in silence or noise; never send them as the patient's words.
HALLUCINATIONS = {"", "you", "thank you", "thank you.", "thanks for watching", "thanks for watching!",
                  "bye", "bye.", "merci", "merci.", "sous-titrage", "sous-titres réalisés par"}


def available():
    try:
        import faster_whisper  # noqa: F401
        import numpy  # noqa: F401
    except ImportError:
        return False
    return True


def load_model(model_root, events):
    from config import get_settings
    from faster_whisper import WhisperModel
    size = get_settings().call.whisper_model
    events.put(("status", "Getting speech recognition ready…"))
    folder = model_root / "whisper"
    folder.mkdir(parents=True, exist_ok=True)
    return WhisperModel(size, device="cpu", compute_type="int8", download_root=str(folder))


def transcribe(model, raw, lang):
    """Raw 16-bit audio -> cleaned text (or "" if it was noise)."""
    import numpy as np
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    segments, _info = model.transcribe(
        audio, language="fr" if lang == "fr" else "en", beam_size=5, vad_filter=False,
        condition_on_previous_text=False, initial_prompt=PROMPT.get(lang, PROMPT["en"]),
        no_speech_threshold=0.6, temperature=0.0)
    parts = [seg.text.strip() for seg in segments if getattr(seg, "no_speech_prob", 0) < 0.6]
    text = " ".join(part for part in parts if part).strip()
    return "" if text.lower().strip(" .!") in {h.strip(" .!") for h in HALLUCINATIONS} else text


class Segmenter:
    """Finds the start and end of each spoken sentence from block loudness (no extra libraries)."""

    def __init__(self):
        self.noise = 0.01
        self.speaking = False
        self.quiet_blocks = 0
        self.loud_blocks = 0
        self.buffer = []
        self.history = []

    def feed(self, raw, level):
        """Feed one block. Returns the finished sentence's audio (bytes) or None."""
        threshold = max(0.035, self.noise * 2.8)
        if not self.speaking:
            self.history = (self.history + [raw])[-PRE_ROLL:]
            if level > threshold:
                self.speaking, self.quiet_blocks, self.loud_blocks = True, 0, 1
                self.buffer = list(self.history)
            else:
                self.noise = self.noise * 0.95 + level * 0.05   # learn the room's background noise
            return None
        self.buffer.append(raw)
        if level >= threshold:
            self.loud_blocks += 1
        self.quiet_blocks = self.quiet_blocks + 1 if level < threshold * 0.8 else 0
        too_long = len(self.buffer) * BLOCK / RATE >= MAX_UTTERANCE
        if self.quiet_blocks * BLOCK / RATE >= END_SILENCE or too_long:
            audio, self.buffer, self.history = b"".join(self.buffer), [], []
            spoken = self.loud_blocks
            self.speaking, self.quiet_blocks, self.loud_blocks = False, 0, 0
            return audio if spoken >= 3 else None              # ignore clicks and coughs (< 0.3 s)
        return None

    def reset(self):
        self.speaking, self.quiet_blocks, self.loud_blocks, self.buffer, self.history = False, 0, 0, [], []


def run(listener, model=None):
    """Listen until listener.stop_event is set; post events to listener.events."""
    import sounddevice

    events, stop, muted = listener.events, listener.stop_event, listener.muted_event
    events.put(("state", "preparing"))
    if model is None:
        model = load_model(listener.model_root, events)
    lang = getattr(listener, "language", "en")
    blocks = queue.Queue(maxsize=200)
    sentences = queue.Queue()
    segmenter = Segmenter()
    silent = {"blocks": 0, "warned": False}

    def on_audio(indata, _frames, _time, _status):
        if not stop.is_set():
            try:
                blocks.put_nowait(bytes(indata))
            except queue.Full:
                pass

    def worker():
        while not stop.is_set() or not sentences.empty():
            try:
                audio = sentences.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                text = transcribe(model, audio, lang)
            except Exception as error:
                events.put(("error", f"Speech recognition failed: {type(error).__name__}: {error}"))
                stop.set()
                return
            if text:
                events.put(("final", text))
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    with sounddevice.RawInputStream(samplerate=RATE, blocksize=BLOCK, device=listener.device, dtype="int16",
                                    channels=1, callback=on_audio):
        events.put(("state", "listening"))
        while not stop.is_set():
            try:
                raw = blocks.get(timeout=0.1)
            except queue.Empty:
                continue
            if muted.is_set():
                segmenter.reset()
                continue
            level = audio_level(raw)
            events.put(("level", level))
            silent["blocks"] = silent["blocks"] + 1 if not any(raw) else 0
            if silent["blocks"] == 40 and not silent["warned"]:
                silent["warned"] = True
                events.put(("status", MIC_BLOCKED_HINT))
            if listener.transcribe:
                finished = segmenter.feed(raw, level)
                if finished:
                    sentences.put(finished)
    deadline = time.monotonic() + 3
    while thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.05)
    events.put(("state", "stopped"))
