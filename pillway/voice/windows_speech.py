"""Backup speech-to-text that uses Windows' own built-in recognizer (System.Speech).

Called by: voice/speech_input.py when the offline Vosk model can't be used on Windows
(not installed, download failed, no internet), or when the config says engine = "windows".

How it works (plain words): we start a small hidden PowerShell program that listens to
the default microphone with Windows' recognizer and prints one line per event:
  READY          the microphone is open
  L:<0-100>      how loud the voice is (drives the green meter)
  T:<text>       a sentence it understood
  E:<message>    something went wrong
Python reads those lines and turns them into the same events Vosk produces, so the
rest of the app doesn't know or care which engine is running.
Nothing is sent over the internet.
"""

import base64
import shutil
import subprocess
import sys

SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
function Say($line) { [Console]::Out.WriteLine($line); [Console]::Out.Flush() }
try {
  Add-Type -AssemblyName System.Speech
  $all = [System.Speech.Recognition.SpeechRecognitionEngine]::InstalledRecognizers()
  $ri = $all | Where-Object { $_.Culture.Name -like 'en*' } | Select-Object -First 1
  if (-not $ri) { $ri = $all | Select-Object -First 1 }
  if (-not $ri) { throw 'No Windows speech recognizer is installed (Settings > Time & language > Speech).' }
  $e = New-Object System.Speech.Recognition.SpeechRecognitionEngine($ri)
  $e.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))
  $e.SetInputToDefaultAudioDevice()
} catch { Say ('E:' + $_.Exception.Message); exit 2 }
$null = Register-ObjectEvent -InputObject $e -EventName SpeechRecognized -SourceIdentifier pwRec
$null = Register-ObjectEvent -InputObject $e -EventName AudioLevelUpdated -SourceIdentifier pwLvl
$e.RecognizeAsync([System.Speech.Recognition.RecognizeMode]::Multiple)
Say 'READY'
while ($true) {
  $ev = Wait-Event -Timeout 1
  if ($ev) {
    if ($ev.SourceIdentifier -eq 'pwRec') {
      $t = $ev.SourceEventArgs.Result.Text
      if ($t) { Say ('T:' + $t) }
    } else { Say ('L:' + $ev.SourceEventArgs.AudioLevel) }
    Remove-Event -EventIdentifier $ev.EventIdentifier
  }
}
"""


def available():
    return sys.platform == "win32" and bool(shutil.which("powershell") or shutil.which("pwsh"))


def parse_line(line):
    """One printed line -> one app event (or None). Kept separate so it can be tested anywhere."""
    line = line.strip()
    if line == "READY":
        return ("state", "listening")
    if line.startswith("L:"):
        try:
            return ("level", max(0.0, min(1.0, float(line[2:]) / 100)))
        except ValueError:
            return None
    if line.startswith("T:") and line[2:].strip():
        return ("final", line[2:].strip())
    if line.startswith("E:"):
        return ("error", "Windows speech recognition: " + line[2:].strip())
    return None


def start_process():
    exe = shutil.which("powershell") or shutil.which("pwsh")
    encoded = base64.b64encode(SCRIPT.encode("utf-16-le")).decode("ascii")
    return subprocess.Popen(
        [exe, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def run(listener):
    """Listen until listener.stop_event is set. Posts events to listener.events."""
    import threading

    events, stop_event, muted = listener.events, listener.stop_event, listener.muted_event
    events.put(("status", "Using Windows speech recognition…"))
    process = start_process()
    saw_error = []

    def reader():
        for raw in process.stdout:
            event = parse_line(raw)
            if not event or stop_event.is_set():
                continue
            if muted.is_set() and event[0] in ("final", "level"):
                continue
            if event[0] == "final" and not listener.transcribe:
                continue
            if event[0] == "error":
                saw_error.append(True)
            events.put(event)

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    while not stop_event.wait(0.1):
        if process.poll() is not None:
            break
    if process.poll() is None:
        process.kill()
    thread.join(timeout=1)
    if not stop_event.is_set() and not saw_error and process.returncode not in (0, None):
        events.put(("error", "Windows speech recognition stopped unexpectedly."))
    events.put(("state", "stopped"))
