"""Sarah's voice from DeepSeek's Text to Speech, STREAMED: she starts talking as soon as the first
audio arrives instead of waiting for the whole reply to be voiced.

Called by: voice/tts.py (first choice when `voice_engine = "deepseek"` and the language is English)
and the call screen (prepare(): start voicing a reply early, while the safety checks finish).

Why (measured on 2026-11-22): the free Microsoft voice we used took anywhere from 0.7 s to 12 s
to voice a reply, and Sarah could only start once ALL of it was ready. DeepSeek's paid voice sends
the first audio after about 1-1.7 s and keeps streaming faster than she speaks, so she can start
right away and never stalls.

How (from api-docs.deepseek.com, "Text to Speech"):
  * POST https://api.deepseek.com/v1/tools/tts with {"text", "voice_id", "format": "pcm"} and the same
    "Authorization: Bearer <key>" as the chat API. The audio is streamed in the response body:
    raw 16-bit mono PCM at 24 kHz.
  * Voices: "stella" (female, default) or "tide" (male). Languages include English, but NOT French,
    so French replies keep using the Microsoft voice.
  * If the response ends early, it failed. Price: $0.45 per 10,000 characters (about 200 replies).
Playback uses `sounddevice`, already installed for the microphone: nothing new to install.
"""

import collections
import json
import threading
import time
import urllib.request

from config import get_settings

TTS_URL = "https://api.deepseek.com/v1/tools/tts"
SAMPLE_RATE = 24000
BYTES_PER_SECOND = SAMPLE_RATE * 2
START_BUFFER = int(BYTES_PER_SECOND * 0.25)    # start playing once 0.25 s of audio has arrived
LANGUAGES = ("en",)                            # DeepSeek's voices don't speak French


def _log(message, **details):
    try:
        from .. import debug_log
        debug_log.log("voice", message, **details)
    except Exception:
        pass


def available(lang="en"):
    settings = get_settings()
    if settings.call.voice_engine != "deepseek" or lang not in LANGUAGES:
        return False
    if settings.ai.demo_mode or not settings.api_key or settings.api_key.startswith("AIza"):
        return False
    try:
        import sounddevice  # noqa: F401
    except (ImportError, OSError):
        return False
    return True


class VoiceStream:
    """Fetches one piece of speech in the background; the player reads while it is still arriving."""

    def __init__(self, text):
        self.text = text
        self.audio = bytearray()
        self.done = threading.Event()
        self.changed = threading.Condition()
        self.error = None
        self.started = time.monotonic()
        self.first_audio_after = None
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self):
        from ..ai.deepseek import _ssl_context
        settings = get_settings()
        body = json.dumps({"text": self.text, "voice_id": settings.call.deepseek_voice or "stella",
                           "format": "pcm", "filter_markdown": True}).encode("utf-8")
        request = urllib.request.Request(TTS_URL, data=body, method="POST", headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {settings.api_key}"})
        try:
            with urllib.request.urlopen(request, timeout=15, context=_ssl_context()) as response:
                while True:
                    piece = response.read1(9600) if hasattr(response, "read1") else response.read(9600)
                    if not piece:
                        break
                    with self.changed:
                        if self.first_audio_after is None:
                            self.first_audio_after = time.monotonic() - self.started
                        self.audio.extend(piece)
                        self.changed.notify_all()
        except Exception as error:   # wrong key, no balance, busy, network...
            self.error = error
        finally:
            with self.changed:
                self.done.set()
                self.changed.notify_all()

    def wait_for(self, size, timeout):
        """Wait until `size` bytes have arrived (or the stream ended). True if there is enough."""
        end = time.monotonic() + timeout
        with self.changed:
            while len(self.audio) < size and not self.done.is_set():
                left = end - time.monotonic()
                if left <= 0:
                    return False
                self.changed.wait(min(left, 0.05))
        return len(self.audio) >= size or self.done.is_set()


_streams = collections.OrderedDict()   # text -> VoiceStream (the last few, so early voicing is reused)
_lock = threading.Lock()


def prepare(text):
    """Start voicing `text` now (or return the stream already started for the same text)."""
    from .natural_voice import chunks_for
    first = None
    for chunk in chunks_for(text, "en"):
        stream = _get(chunk)
        first = first or stream
    return first


def _get(chunk):
    with _lock:
        stream = _streams.get(chunk)
        if stream is None or stream.error is not None:
            stream = _streams[chunk] = VoiceStream(chunk)
        _streams.move_to_end(chunk)
        while len(_streams) > 16:
            _streams.popitem(last=False)
        return stream


def speak(text, should_stop, on_playing=None):
    """Play `text` as it streams in. Raises (so tts.py tries the next voice) if no audio came at all."""
    import sounddevice
    from .natural_voice import chunks_for
    chunks = chunks_for(text, "en")
    if not chunks:
        return
    streams = [_get(chunk) for chunk in chunks]          # all pieces start fetching at once
    first = streams[0]
    if not first.wait_for(START_BUFFER, timeout=8) or (first.error and not first.audio):
        raise RuntimeError(f"DeepSeek voice unavailable: {first.error or 'no audio in 8 s'}")
    _log("DeepSeek voice starts", after_request=f"{time.monotonic() - first.started:.2f}s",
         first_audio=f"{first.first_audio_after or 0:.2f}s")
    played_any = False
    unfinished = None
    with sounddevice.RawOutputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16") as out:
        for index, stream in enumerate(streams):          # one output stream: no gaps between pieces
            position = 0
            while not should_stop():
                with stream.changed:
                    available_bytes = len(stream.audio) - position
                    finished = stream.done.is_set()
                if available_bytes > 0:
                    size = min(available_bytes, 4800) // 2 * 2  # 0.1 s at a time; whole samples only
                    if size == 0:
                        stream.wait_for(position + 2, 0.05)
                        continue
                    if not played_any and on_playing:
                        on_playing(True)
                    played_any = True
                    out.write(bytes(stream.audio[position:position + size]))
                    position += size
                elif finished:
                    break
                else:
                    stream.wait_for(position + 4800, 0.5)
            if should_stop():
                out.abort()
                break
            if stream.error:
                _log("DeepSeek voice stopped early", error=f"{type(stream.error).__name__}: {stream.error}")
                # never drop the rest: hand the pieces not yet spoken to the next voice
                rest = chunks[index if position == 0 else index + 1:]
                if rest:
                    from .natural_voice import Unfinished
                    unfinished = Unfinished(" ".join(rest), str(stream.error))
                break
    if on_playing:
        on_playing(False)
    if unfinished:
        raise unfinished
