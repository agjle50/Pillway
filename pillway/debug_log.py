"""Admin debug log: short, timestamped lines in the terminal that ran `python Pillway.py`.

Called by: the call screen, the speech engines, read-aloud, the AI client and the intake
questionnaire. It never touches the window, so it is safe from any thread.

Turn it on or off with `debug_logs` under [dev] in pillway_config.toml, or force it on for
one run with `python Pillway.py --debug`. Lines look like:

    14:02:31.207 [call    ] mic OFF (Sarah is talking)
    14:02:33.948 [call    ] heard (dropped: Sarah was talking) "okay so how are you"

Privacy: lines can contain short snippets of what was heard/said (cut to 80 characters) so
you can debug speech problems. They are printed only, never saved or sent anywhere.
"""

import sys
import threading
import time

_forced = {"on": None}          # set by --debug; None means "use the config"
_lock = threading.Lock()
MAX_TEXT = 80


def force(on=True):
    _forced["on"] = bool(on)


def enabled():
    if _forced["on"] is not None:
        return _forced["on"]
    try:
        from config import get_settings
        return bool(get_settings().dev.debug_logs)
    except Exception:
        return False


def snippet(text):
    """Text shortened for the log, on one line, in quotes."""
    text = " ".join(str(text or "").split())
    if len(text) > MAX_TEXT:
        text = text[:MAX_TEXT - 1] + "…"
    return f'"{text}"'


def log(area, message, **details):
    """Print one debug line, e.g. log("call", "mic OFF", reason="Sarah is talking")."""
    if not enabled():
        return
    now = time.time()
    stamp = time.strftime("%H:%M:%S", time.localtime(now)) + f".{int(now % 1 * 1000):03d}"
    extra = " ".join(f"{key}={value}" for key, value in details.items() if value is not None)
    line = f"{stamp} [{area:<8}] {message}" + (f"  ({extra})" if extra else "")
    with _lock:
        try:
            print(line, file=sys.stderr, flush=True)
        except Exception:  # a closed terminal must never crash the app
            pass
