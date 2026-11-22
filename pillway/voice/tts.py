"""Read-aloud (text-to-speech) with a safe fallback chain. Never crashes the app.

Called by: the "Read aloud" button on the assistant's messages and the Call screen.

Order (most reliable first):
  1. The computer's own voice, run as a separate program:
       Windows -> PowerShell + System.Speech (built into Windows, no install)
       Mac     -> the `say` command
       Linux   -> `espeak` if installed
  2. pyttsx3 (Python library), only if step 1 isn't available.
  3. A friendly "read-aloud isn't available on this computer" message.

Why this order: pyttsx3 often freezes silently on Windows and Mac when it runs in a
background thread (and we must run speech in the background so the window doesn't
freeze). A frozen pyttsx3 never raises an error, so the fallback never got a turn.
A separate program can't freeze the app and can be stopped at any time.

Only one thing is spoken at a time: starting a new message stops the old one.
"""

import os
import shutil
import subprocess
import sys
import threading

from config import get_settings

UNAVAILABLE = "Read-aloud isn't available on this computer."

_lock = threading.Lock()
_current = {"process": None, "generation": 0}

# Text is passed in an environment variable, not on the command line or stdin, so
# accents (French) survive and nothing in the text can be run as a command.
_WINDOWS_SCRIPT = (
    "Add-Type -AssemblyName System.Speech; "
    "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
    "if ($env:PILLWAY_TTS_LANG -eq 'fr') { "
    "  $v = $s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -like 'fr*' } | Select-Object -First 1; "
    "  if ($v) { $s.SelectVoice($v.VoiceInfo.Name) } } "
    "$s.Rate = [int]$env:PILLWAY_TTS_RATE; "
    "$s.Speak($env:PILLWAY_TTS_TEXT)"
)


def _windows_rate(words_per_minute):
    # System.Speech uses -10..10, where 0 is about 180 words per minute.
    return max(-10, min(10, round((int(words_per_minute) - 180) / 20)))


def system_command(text, lang):
    """The command + environment for the computer's own voice, or None if there isn't one."""
    rate = get_settings().call.sarah_speech_rate
    env = dict(os.environ)
    if sys.platform == "win32":
        exe = shutil.which("powershell") or shutil.which("pwsh")
        if not exe:
            return None
        env.update(PILLWAY_TTS_TEXT=text, PILLWAY_TTS_LANG=lang, PILLWAY_TTS_RATE=str(_windows_rate(rate)))
        return [exe, "-NoProfile", "-NonInteractive", "-Command", _WINDOWS_SCRIPT], env
    if sys.platform == "darwin" and shutil.which("say"):
        voice = ["-v", "Amelie"] if lang == "fr" else []
        return ["say", "-r", str(rate), *voice, "--", text], env
    if shutil.which("espeak"):
        return ["espeak", "-v", "fr" if lang == "fr" else "en", "-s", str(rate), "--", text], env
    return None


def _speak_system(text, lang, generation):
    command = system_command(text, lang)
    if not command:
        raise RuntimeError(UNAVAILABLE)
    args, env = command
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # no black console window on Windows
    process = subprocess.Popen(args, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.PIPE, creationflags=flags)
    with _lock:
        if generation != _current["generation"]:  # a newer message started meanwhile
            process.kill()
            return
        _current["process"] = process
    try:
        _out, err = process.communicate(timeout=180)
    except subprocess.TimeoutExpired:
        process.kill()
        raise RuntimeError("Read-aloud took too long and was stopped.")
    finally:
        with _lock:
            if _current["process"] is process:
                _current["process"] = None
    stopped_by_us = generation != _current["generation"]
    if process.returncode not in (0, None) and not stopped_by_us:
        raise RuntimeError((err or b"").decode(errors="replace").strip()[:200] or UNAVAILABLE)


def _speak_pyttsx3(text, lang, _generation):
    import pyttsx3
    engine = pyttsx3.init()
    settings = get_settings().call
    engine.setProperty("rate", settings.sarah_speech_rate)
    if settings.sarah_voice or lang == "fr":
        for voice in engine.getProperty("voices"):
            name = f"{voice.name} {voice.id}".lower()
            if (settings.sarah_voice and settings.sarah_voice.lower() in name) or (lang == "fr" and "fr" in name):
                engine.setProperty("voice", voice.id)
                break
    engine.say(text)
    engine.runAndWait()


ENGINES = (_speak_system, _speak_pyttsx3)


def stop():
    """Stop whatever is being read aloud right now."""
    with _lock:
        _current["generation"] += 1
        process, _current["process"] = _current["process"], None
    if process and process.poll() is None:
        process.kill()


def speak(text, lang="en", on_error=None, on_done=None):
    """Speak in the background (stops anything already speaking).

    on_done() is called when speech ends; on_error(message) if nothing could speak.
    Both are called from the background thread: the UI must hand them to its own loop.
    """
    stop()
    with _lock:
        generation = _current["generation"]

    def run():
        last_error = UNAVAILABLE
        try:
            for engine in ENGINES:
                try:
                    engine(text, lang, generation)
                    return
                except Exception as error:  # try the next engine
                    last_error = str(error) or UNAVAILABLE
                    print(f"[read-aloud] {engine.__name__} failed: {type(error).__name__}: {error}")
            if on_error:
                on_error(UNAVAILABLE if last_error == UNAVAILABLE else f"{UNAVAILABLE} ({last_error})")
        finally:
            if on_done:
                on_done()
    threading.Thread(target=run, daemon=True).start()
