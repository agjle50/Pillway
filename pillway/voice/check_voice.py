"""`python Pillway.py --check-voice`: tests read-aloud and the microphone, and says what's wrong.

Plain-language output for the team. Run it on the laptop you'll present from.
Steps: 1) read-aloud speaks a sentence, 2) list microphones, 3) listen 4 s and show the
loudness, 4) check the offline speech model, 5) check Windows' built-in recognizer.
"""

import queue
import sys
import time


def _ok(message):
    print(f"  OK    {message}")


def _bad(message, fix=""):
    print(f"  PROBLEM  {message}")
    if fix:
        print(f"           Fix: {fix}")


def check_voice():
    from config import get_settings
    from ..storage.paths import data_folder
    from . import speech_input, tts, windows_speech

    settings = get_settings().call
    print(f"\nPillway voice check  (computer: {sys.platform}, speech engine: {settings.speech_to_text_engine})\n")

    print("1. Read aloud")
    command = tts.system_command("Hello, this is the Pillway read aloud test.", "en")
    result = {}
    if command:
        _ok(f"uses the computer's own voice ({command[0][0]})")
    else:
        print("  ...   no built-in voice command found, trying pyttsx3")
    tts.speak("Hello, this is the Pillway read aloud test.", "en",
              on_error=lambda message: result.setdefault("error", message),
              on_done=lambda: result.setdefault("done", True))
    deadline = time.monotonic() + 25
    while "done" not in result and time.monotonic() < deadline:
        time.sleep(0.1)
    if "error" in result:
        _bad(result["error"], "On Windows, make sure Windows PowerShell isn't blocked by your school/work admin.")
    elif "done" in result:
        _ok("finished speaking. Did you HEAR it? If not, check the volume and the output device.")
    else:
        _bad("speech didn't finish within 25 seconds")

    print("\n2. Microphones")
    try:
        devices = speech_input.input_devices()
        if devices:
            for index, name in devices:
                _ok(f"[{index}] {name}")
        else:
            _bad("no microphone found", "plug one in or check Settings > Sound > Input")
        device = speech_input.resolve_input_device(settings.microphone_device)
        _ok(f"the app will use microphone [{device}]")
    except Exception as error:
        device = None
        _bad(str(error), "python -m pip install -r requirements.txt (inside your venv)")

    print("\n3. Listening for 4 seconds: say something now...")
    if device is not None:
        events = queue.Queue()
        listener = speech_input.LocalSpeechInput(data_folder() / "models", events, device=device, transcribe=False)
        listener.start()
        time.sleep(4)
        listener.stop()
        listener.thread.join(timeout=3)
        levels, errors = [], []
        while not events.empty():
            kind, value = events.get()
            if kind == "level":
                levels.append(value)
            elif kind == "error":
                errors.append(value)
        if errors:
            _bad(errors[0])
        elif not levels:
            _bad("no sound arrived from the microphone")
        elif max(levels) == 0:
            _bad("the microphone sent pure silence", speech_input.MIC_BLOCKED_HINT)
        elif max(levels) < 0.03:
            _bad(f"very quiet (peak {max(levels):.2f})", "speak closer, or raise the input volume in Sound settings")
        else:
            _ok(f"heard you (peak loudness {max(levels):.2f})")

    print("\n4. Offline speech model (Vosk)")
    try:
        import vosk  # noqa: F401
        model = data_folder() / "models" / speech_input.MODEL_NAME
        if model.exists():
            _ok(f"installed at {model}")
        else:
            print("  ...   not downloaded yet: it downloads (~40 MB) the first time you use the mic.")
            print("        Do that tonight on home Wi-Fi so it works at the venue without internet.")
    except Exception as error:
        _bad(f"Vosk isn't installed ({error})", "python -m pip install -r requirements.txt")

    print("\n5. Windows built-in speech recognition (backup)")
    if windows_speech.available():
        _ok("available as a backup if the offline model can't be used")
    else:
        print("  ...   not on Windows, skipped")
    print("\nDone. Send a screenshot of this to your developer if anything says PROBLEM.\n")
