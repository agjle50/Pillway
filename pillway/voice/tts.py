"""Read-aloud (text-to-speech) with a safe fallback chain. Never crashes the app.

Called by: the "Read aloud" button on Sarah's messages and the Call screen.
Order: pyttsx3 (offline) -> the system command (`say` on Mac, PowerShell SAPI on Windows,
`espeak` on Linux) -> a friendly "read-aloud isn't available on this computer" message.
Speech runs in a background thread so the window never freezes.
"""

import shutil
import subprocess
import sys
import threading

from config import get_settings

UNAVAILABLE = "Read-aloud isn't available on this computer."


def _speak_pyttsx3(text, lang):
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


def _speak_system(text, lang):
    if sys.platform == "darwin" and shutil.which("say"):
        voice = ["-v", "Amelie"] if lang == "fr" else []
        subprocess.run(["say", *voice, text], check=True, timeout=120)
    elif sys.platform == "win32":
        script = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                  "$s.Speak([Console]::In.ReadToEnd())")
        subprocess.run(["powershell", "-NoProfile", "-Command", script], input=text, text=True, check=True, timeout=120)
    elif shutil.which("espeak"):
        subprocess.run(["espeak", "-v", "fr" if lang == "fr" else "en", text], check=True, timeout=120)
    else:
        raise RuntimeError(UNAVAILABLE)


def speak(text, lang="en", on_error=None, on_done=None):
    """Speak in the background. on_error(message) is called (from the thread) if nothing works."""

    def run():
        for engine in (_speak_pyttsx3, _speak_system):
            try:
                engine(text, lang)
                if on_done:
                    on_done()
                return
            except Exception:
                continue
        if on_error:
            on_error(UNAVAILABLE)
    threading.Thread(target=run, daemon=True).start()
