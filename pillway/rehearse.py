"""Rehearse the 5-minute stage script without opening the window, and measure reply times.

Called by: `python Pillway.py --rehearse` (add --demo to force demo mode).
Uses a TEMPORARY data folder, so your real demo data is never touched.
Prints every message, which flags were raised, the care plan status, and timings.
Run it 3 times in demo mode and 3 times in live AI mode before the pitch.
"""

import tempfile
import time

from config import get_settings

STAGE_SCRIPT = [
    "hi",
    "I've been feeling dizzy and my doctor started me on a new pill",
    "I'm not sure what to eat",
    "No",
    "I have a sore on my foot that won't heal and my toes feel numb",
    "On my right heel, about two weeks, and it's getting bigger",
    "my sugar was 7.8 before breakfast at 8 am",
    "142/90 at 8 am",
    "30 to 90",
    "None",
    "Cost of healthy food",
    "Walk more",
    "no",
]


def rehearse():
    settings = get_settings()
    settings.storage.data_folder = tempfile.mkdtemp(prefix="pillway-rehearsal-")
    from .core.conversation_service import ConversationService
    service = ConversationService()
    mode = "LIVE AI (" + settings.ai.chat_model + ")" if service.brain.live else "DEMO MODE (" + service.brain.status_note() + ")"
    print(f"Rehearsing the stage script in {mode}\n" + "=" * 70)
    service.accept_consent("maria")
    timings = []
    for text in STAGE_SCRIPT:
        started = time.monotonic()
        record = service.handle_message("maria", text)
        seconds = time.monotonic() - started
        timings.append(seconds)
        patient = [m for m in record["messages"] if m["role"] == "patient"][-1]
        sarah = [m for m in record["messages"] if m["role"] == "sarah"][-1]
        flag = {1: "  [RED: URGENT]", 2: "  [AMBER: WATCH]"}.get(patient.get("tier"), "")
        print(f"\nMARIA: {text}{flag}")
        print(f"SARAH ({sarah['source']}, {seconds:.1f}s): {sarah['text']}")
    print("\n" + "=" * 70)
    print("Flags:", [(f["tier"], f["topic"]) for f in record["flags"]])
    print("Care plan:", (record["care_plan"] or {}).get("status"), "| tasks:", len(record["tasks"]))
    print(f"Reply time: average {sum(timings) / len(timings):.1f}s, slowest {max(timings):.1f}s")
    ok = (any(f["tier"] == 1 for f in record["flags"]) and record["care_plan"] is not None
          and "62 to 78" in " ".join(m["text"] for m in record["messages"]))
    print("RESULT:", "PASS - the stage script works" if ok else "CHECK - something differs from the script")
    return ok
