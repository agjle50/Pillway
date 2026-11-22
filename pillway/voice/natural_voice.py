"""Sarah's natural-sounding voice: a Microsoft neural voice via the free `edge-tts` package.

Called by: voice/tts.py (tried first; if anything fails, the computer's own voice is used).
Why: the voices built into Windows sound robotic. Neural voices have natural rhythm,
pitch movement and breathing pauses. Tuned (see [call] in pillway_config.toml) to the
team's reference sample: upbeat, fairly quick, short phrases.

How it works (plain words):
1. speech_text() rewrites the reply the way a person would SAY it ("142/90" -> "142 over 90").
2. The text is split into sentences. Sentence 1 is voiced and starts playing while the
   next ones are prepared, so Sarah starts talking quickly.
3. Audio is played with the computer's own player (Windows MCI, `afplay` on Mac,
   `ffplay`/`mpg123` on Linux) and can be stopped at any moment.
Voiced sentences are cached on disk, so repeated lines are instant and work offline.
"""

import asyncio
import hashlib
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from config import get_settings

from ..storage.paths import data_folder


def available():
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        return False
    return get_settings().call.natural_voice


# ---- 1. say it like a person ---------------------------------------------------------------

_UNITS = {
    "en": [(r"(\d)\s?mmol/L", r"\1 millimoles per litre"), (r"(\d)\s?mg\b", r"\1 milligrams"),
           (r"(\d)\s?kg\b", r"\1 kilograms"), (r"(\d)\s?g/kg\b", r"\1 grams per kilogram"),
           (r"(\d)\s?g\b", r"\1 grams"), (r"(\d{2,3})/(\d{2,3})", r"\1 over \2"),
           (r"\be\.g\.", "for example"), (r"\bi\.e\.", "that is"), (r"&", " and "), (r"\bvs\.?", "versus"),
           (r"\bDr\.", "Doctor"), (r"(\d)\s?%", r"\1 percent")],
    "fr": [(r"(\d)\s?mmol/L", r"\1 millimoles par litre"), (r"(\d)\s?mg\b", r"\1 milligrammes"),
           (r"(\d)\s?kg\b", r"\1 kilogrammes"), (r"(\d)\s?g/kg\b", r"\1 grammes par kilogramme"),
           (r"(\d)\s?g\b", r"\1 grammes"), (r"(\d{2,3})/(\d{2,3})", r"\1 sur \2"),
           (r"\bp\. ?ex\.", "par exemple"), (r"&", " et "), (r"(\d)\s?%", r"\1 pour cent")],
}


def speech_text(text, lang="en"):
    """Rewrite a written reply into what a person would actually say out loud."""
    text = re.sub(r":?\s*\n\s*[•▪►\-*]\s*", ". ", text)       # each bullet becomes its own sentence
    text = re.sub(r"[⚑•▪►✓✔→*#_`>]", " ", text)
    text = re.sub(r"(\d)\s?[–-]\s?(\d)", r"\1 to \2" if lang != "fr" else r"\1 à \2", text)
    text = re.sub(r"\(([^)]*)\)", r", \1,", text)          # brackets become a little pause
    text = re.sub(r"https?://\S+", "", text)
    for pattern, replacement in _UNITS.get(lang, _UNITS["en"]):
        text = re.sub(pattern, replacement, text)
    text = re.sub(r"\s*\n\s*\n\s*", ". ", text)               # paragraphs -> sentence breaks
    text = re.sub(r"\s*\n\s*", ", ", text)
    text = re.sub(r"\.{2,}|…", ".", text)
    text = re.sub(r"\s+([,.!?])", r"\1", text)
    text = re.sub(r"([,.!?])\1+", r"\1", text)
    text = re.sub(r"\.,|,\.", ".", text)
    text = re.sub(r":\s*,|,\s*:", ":", text)
    text = re.sub(r"(^|[.!?]\s+)([a-zà-ÿ])", lambda m: m.group(1) + m.group(2).upper(), text)
    return re.sub(r"\s{2,}", " ", text).strip(" ,")


ONE_PIECE = 420      # replies up to this many characters are voiced in one go (no gaps at all)


def sentences(text):
    """Split into spoken chunks, as FEW as possible: every join can be heard as a small pause.

    A normal reply is one chunk. A long one becomes two: the first sentence (so she starts
    talking quickly) and everything else (prepared while the first is playing).
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= ONE_PIECE:
        return [text]
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]
    first = parts[0]
    for part in parts[1:]:
        if len(first) >= 60:
            break
        first += " " + part
    rest = text[len(first):].strip()
    return [first, rest] if rest else [first]


# ---- 2. voice it ---------------------------------------------------------------------------

def _voice(lang):
    settings = get_settings().call
    return settings.natural_voice_fr if lang == "fr" else settings.natural_voice_en


def synthesize(text, lang):
    """Return the path of an MP3 of `text` (from the cache when possible)."""
    import edge_tts
    settings = get_settings().call
    voice, rate, pitch = _voice(lang), settings.natural_voice_rate, settings.natural_voice_pitch
    folder = data_folder() / "voice_cache"
    folder.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(f"{voice}|{rate}|{pitch}|{text}".encode()).hexdigest()[:24]
    path = folder / f"{key}.mp3"
    if path.exists() and path.stat().st_size > 0:
        return path
    partial = path.with_suffix(".part")

    async def run():
        await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(str(partial))
    asyncio.run(asyncio.wait_for(run(), timeout=20))
    if not partial.exists() or partial.stat().st_size == 0:
        raise RuntimeError("The natural voice returned no audio.")
    partial.replace(path)
    return path


# ---- 3. play it (stoppable) ----------------------------------------------------------------

_counter = [0]


def _play_windows(path, should_stop, on_playing=None):
    import ctypes
    winmm = ctypes.windll.winmm
    buffer = ctypes.create_unicode_buffer(64)
    _counter[0] += 1
    alias = f"pillway{_counter[0]}"

    def mci(command):
        error = winmm.mciSendStringW(command, buffer, 64, 0)
        if error:
            raise RuntimeError(f"Windows audio error {error}")
        return buffer.value
    mci(f'open "{path}" type mpegvideo alias {alias}')
    try:
        mci(f"play {alias}")
        if on_playing:
            on_playing(True)              # sound is starting now: her mouth may move
        time.sleep(0.05)
        while not should_stop():
            if mci(f"status {alias} mode") != "playing":
                break
            time.sleep(0.04)
    finally:
        if on_playing:
            on_playing(False)
        try:
            mci(f"close {alias}")
        except RuntimeError:
            pass


def _play_process(path, should_stop, on_playing=None):
    if sys.platform == "darwin" and shutil.which("afplay"):
        args = ["afplay", str(path)]
    elif shutil.which("ffplay"):
        args = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)]
    elif shutil.which("mpg123"):
        args = ["mpg123", "-q", str(path)]
    else:
        raise RuntimeError("No audio player found for the natural voice.")
    process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
    if on_playing:
        on_playing(True)
    try:
        while process.poll() is None:
            if should_stop():
                process.kill()
                break
            time.sleep(0.04)
    finally:
        if on_playing:
            on_playing(False)


def play(path, should_stop, on_playing=None):
    (_play_windows if sys.platform == "win32" else _play_process)(Path(path), should_stop, on_playing)


def speak(text, lang, should_stop, on_playing=None):
    """Voice and play `text`, sentence by sentence. Raises if the natural voice can't be used."""
    chunks = sentences(speech_text(text, lang))
    if not chunks:
        return
    first = synthesize(chunks[0], lang)            # fail fast (no internet -> fallback voice)
    ready = queue.Queue()
    ready.put(first)

    def prepare_rest():
        for chunk in chunks[1:]:
            if should_stop():
                break
            try:
                ready.put(synthesize(chunk, lang))
            except Exception as error:  # keep going with what we have
                ready.put(error)
                return
        ready.put(None)
    if len(chunks) > 1:
        threading.Thread(target=prepare_rest, daemon=True).start()
    else:
        ready.put(None)
    while not should_stop():
        item = ready.get()
        if item is None:
            return
        if isinstance(item, Exception):  # part of it was already spoken: stop quietly, don't repeat
            print(f"[natural voice] {type(item).__name__}: {item}")
            return
        play(item, should_stop, on_playing)
