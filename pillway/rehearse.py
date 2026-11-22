"""Rehearse the 5-minute stage script without opening the window, and measure reply times.

Called by: `python Pillway.py --rehearse` (add --demo to force demo mode).
Uses a TEMPORARY data folder, so your real demo data is never touched.
Prints every message, which flags were raised, the care plan status, and timings.
Run it 3 times in demo mode and 3 times in live AI mode before the pitch.
"""

import tempfile
import time

from config import get_settings

# Maria's intake questionnaire (filled in on the first screen before the check-in)
MARIA_INTAKE = {"weight": "78", "weight_unit": "kg", "height": "162", "height_unit": "cm", "checks_bp": "yes",
                "systolic": "142", "diastolic": "90", "tobacco": "no"}

# Sarah speaks first (the "Necessary check-in" popup), so the script starts with Maria's answer to
# "Has anything changed?".
STAGE_SCRIPT = [
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
    "What I should eat",
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
    service.submit_intake("maria", MARIA_INTAKE)
    service.accept_consent("maria")
    service.start_check_in("maria")
    opener = [m for m in service.store.load("maria")["messages"] if m["role"] == "sarah"][-1]
    print(f"\nSARAH (opens the check-in): {opener['text']}")
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
    # Live AI is adaptive (it may ask in a different order than the script), so finish politely.
    for _ in range(3):
        if record["care_plan"] is not None:
            break
        record = service.handle_message("maria", "No, that's everything, thank you")
        sarah = [m for m in record["messages"] if m["role"] == "sarah"][-1]
        print(f"\nMARIA: No, that's everything, thank you\nSARAH ({sarah['source']}): {sarah['text']}")
    print("\n" + "=" * 70)
    print("Flags:", [(f["tier"], f["topic"]) for f in record["flags"]])
    print("Care plan:", (record["care_plan"] or {}).get("status"), "| tasks:", len(record["tasks"]))
    if record["care_plan"]:
        from .core import care_plan as plan_logic
        for line in plan_logic.to_check(record["care_plan"]):
            print(f"   to check: {plan_logic.render_line(line, 'en', record['care_plan'])}   <- {line['reason']}")
    print(f"Reply time: average {sum(timings) / len(timings):.1f}s, slowest {max(timings):.1f}s")
    ok = (any(f["tier"] == 1 for f in record["flags"]) and record["care_plan"] is not None
          and "62 to 78" in " ".join(m["text"] for m in record["messages"]))
    print("RESULT:", "PASS - the stage script works" if ok else "CHECK - something differs from the script")
    return ok
