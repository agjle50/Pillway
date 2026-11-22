"""Command-line options for `python Pillway.py ...`.

Called by: Pillway.py.
  --check-config      print the active settings and warn about anything unsafe
  --show-ai-payload   print exactly what would be sent to the AI for a sample message
  --reset-demo        restore Maria (and the other demo patients) to a fresh state
  --role patient|pharmacist   open straight into one side (run two windows side by side)
  --demo              force demo mode for this run (no AI, no internet needed)
  --rehearse          run the 5-minute stage script without the window and time each reply
  --check-ai          find out why the AI isn't working: every key found, which one is used, a live test
  --debug             print admin debug lines (mic on/off, what was heard, AI timings) in the terminal
"""

import argparse
import json

from config import ConfigError, get_settings
from config.schema import UNSAFE_WHEN


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="python Pillway.py", description="Pillway care assistant (hackathon demo)")
    parser.add_argument("--check-config", action="store_true", help="show settings and warnings, then exit")
    parser.add_argument("--show-ai-payload", action="store_true", help="show what the AI would receive, then exit")
    parser.add_argument("--reset-demo", action="store_true", help="restore the demo patients to a fresh state")
    parser.add_argument("--role", choices=["patient", "pharmacist"], help="open straight into one side")
    parser.add_argument("--demo", action="store_true", help="force demo mode (no AI) for this run")
    parser.add_argument("--check-voice", action="store_true", help="test read-aloud and the microphone, then exit")
    parser.add_argument("--rehearse", action="store_true", help="run the stage script in the terminal and time it")
    parser.add_argument("--debug", action="store_true", help="print admin debug lines in the terminal")
    parser.add_argument("--check-ai", action="store_true", help="test the AI connection and explain any problem")
    return parser.parse_args(argv)


def check_config():
    settings = get_settings()
    ai = settings.ai
    print("Pillway settings check\n" + "=" * 40)
    print(f"Settings folder : {settings.root}")
    print(f"API key         : {'found (ends ' + settings.masked_key() + ') via ' + settings.api_key_source if settings.api_key else 'none -> demo mode'}")
    print(f"Demo mode       : {ai.demo_mode}")
    from pillway.ai.client import PROVIDER_NAMES, model_for
    print(f"AI company      : {PROVIDER_NAMES[ai.provider]} (provider = \"{ai.provider}\")")
    print("Models per job  :")
    for job in ("chat", "call", "flag", "care_plan", "summary"):
        print(f"   {job:<10} {model_for(job, ai)}")
    print(f"Thresholds      : sugar low {settings.safety.blood_sugar_low}, high {settings.safety.blood_sugar_high}, "
          f"very high {settings.safety.blood_sugar_very_high} mmol/L; BP urgent {settings.safety.bp_systolic_urgent}/"
          f"{settings.safety.bp_diastolic_urgent} (PLACEHOLDERS: confirm with Pillway)")
    print(f"Pharmacist review required: {settings.pharmacist.pharmacist_review_required}")
    print(f"Estimated cost per demo run: {estimate_cost()}")
    warnings = list(settings.warnings)
    for (section, key), (bad_value, message) in UNSAFE_WHEN.items():
        if getattr(getattr(settings, section), key) == bad_value:
            warnings.append(message)
    print("\nWarnings:" if warnings else "\nNo warnings. Ready.")
    for warning in warnings:
        print(f"  ! {warning}")


def estimate_cost():
    """Very rough: about 15 chat turns, 15 flag checks, 1 care plan, 2 recaps per stage run."""
    from pillway.ai.client import model_for
    ai = get_settings().ai
    # USD per million tokens (input, output). DeepSeek: PEAK prices from api-docs.deepseek.com
    # (Nov 2026; off-peak is half). Gemini: rough estimate.
    price = {"deepseek-flash": (0.30, 1.20), "deepseek-v4-pro": (1.32, 3.96),
             "lite": (0.10, 0.40), "flash": (0.50, 3.00), "pro": (2.00, 12.00)}

    def cost(job, calls, tokens_in, tokens_out):
        model = model_for(job, ai)
        tier = next((name for name in price if name in model), "flash")
        return calls * (tokens_in * price[tier][0] + tokens_out * price[tier][1]) / 1_000_000
    total = (cost("chat", 15, 4000, 250) + cost("flag", 15, 1500, 80)
             + cost("care_plan", 1, 3000, 1200) + cost("summary", 2, 2500, 120))
    where = "api-docs.deepseek.com/quick_start/pricing" if ai.provider == "deepseek" else "ai.google.dev/pricing"
    return f"about US${total:.3f} (rough estimate at peak prices; check current prices at {where})"


def show_ai_payload():
    from pillway.ai.brain import patient_context, system_prompt
    from pillway.ai.client import AIClient
    from pillway.storage.patient_store import PatientStore, blank_record
    store = PatientStore()
    record = blank_record("maria", store.seeds()["maria"])
    sample = "Hi, it's Maria Rossi (416-555-0198). I have a sore on my foot that won't heal."
    record["messages"].append({"role": "patient", "text": sample, "time": "2026-11-22T10:00:00-05:00"})
    user = (f"<patient_data>\n{json.dumps(patient_context(record), ensure_ascii=False, indent=1)}\n</patient_data>\n\n"
            f"TASK: (the turn's task)\n\n<patient_message>\n{sample}\n</patient_message>")
    request = AIClient().build_request("chat", system_prompt(), user, record["profile"])
    print("What the AI company would receive for a sample message\n" + "=" * 56)
    print(f"Sample message typed by the patient: {sample}\n")
    from pillway.ai.client import PROVIDER_NAMES
    print(f"AI company: {PROVIDER_NAMES[get_settings().ai.provider]}   model: {request['model']}")
    print(f"system prompt: {len(request['system'])} characters of Sarah's rules (no patient data)")
    print("user message:\n" + request["contents"])
    print("\nNever sent: name, phone, email, address, health card number, date of birth.")


def check_ai():
    """Plain-English answer to "why doesn't the AI work on MY computer?" (keys, code, certificates)."""
    import sys
    import time
    from pillway.ai.client import AIClient, PROVIDER_NAMES, model_for
    from pillway.ui.patient.ai_connection import connection_hint
    settings = get_settings()
    ai = settings.ai
    name = PROVIDER_NAMES[ai.provider]
    print("Pillway AI check\n" + "=" * 40)
    print(f"Python          : {sys.version.split()[0]}  ({sys.executable})")
    print(f"Pillway folder  : {settings.root}")
    print(f"AI company      : {name}   (provider = \"{ai.provider}\" in pillway_config.toml)")
    print(f"Chat model      : {model_for('chat', ai)}")
    found = getattr(settings, "api_keys_found", [])
    print("\nAPI keys found on this computer (only the last 4 characters are shown):")
    if not found:
        print("   none. Fix: open the app > Settings > AI connection, paste your key, Save and connect.")
    for item in found:
        mark = "USED   " if item["used"] else "ignored"
        print(f"   [{mark}] …{item['ends']}  {item['kind']:<8} from {item['source']}")
    if any(not item["used"] for item in found):
        print("   Ignored keys can confuse things later: delete them if they're old.\n"
              "   (Windows: Start > 'Edit environment variables for your account'. Mac: ~/.zshrc. Or the .env file.)")
    if ai.demo_mode:
        print("\nPROBLEM: demo_mode = true, so the AI is never used. Set demo_mode = false (and don't start with --demo).")
        return
    client = AIClient()
    if not client.available:
        print(f"\nPROBLEM: {client.unavailable_reason}")
        return
    print(f"\nTesting {name} with the key ending …{settings.api_key[-4:]} …")
    started = time.monotonic()
    try:
        client._sdk.models.generate_content(model=model_for("chat", ai), contents="Reply with OK.",
                                            config={"max_output_tokens": 16})
        print(f"OK: {name} answered in {time.monotonic() - started:.1f}s. Sarah's AI works on this computer.")
    except Exception as error:
        text = str(error)
        print(f"PROBLEM: {connection_hint(text, model_for('chat', ai), ai.provider)}.\n   Details: {text[:200]}")
        if "CERTIFICATE" in text.upper() or "SSL" in text.upper():
            print("   Fix for certificate errors: python -m pip install -r requirements.txt  (installs certifi).\n"
                  "   On a Mac also double-click 'Install Certificates.command' in Applications > Python 3.x.")
        elif "401" in text:
            print("   Copy the key again from platform.deepseek.com/api_keys and paste it in Settings > AI connection.")


def reset_demo():
    from pillway.storage.patient_store import PatientStore
    PatientStore().reset_demo()
    print("Demo reset: Maria is back to a fresh, newly-enrolled state.")


def run(argv=None):
    """Handle command-line flags. Returns the chosen role, or None if the program should exit."""
    try:
        args = parse_args(argv)
        settings = get_settings()
    except ConfigError as error:
        print(error)
        return None
    if args.demo:
        settings.ai.demo_mode = True
    if args.debug:
        from pillway import debug_log
        debug_log.force(True)
    if args.check_config:
        check_config()
        return None
    if args.check_ai:
        check_ai()
        return None
    if args.show_ai_payload:
        show_ai_payload()
        return None
    if args.reset_demo:
        reset_demo()
        return None
    if args.check_voice:
        from pillway.voice.check_voice import check_voice
        check_voice()
        return None
    if args.rehearse:
        from pillway.rehearse import rehearse
        rehearse()
        return None
    return args.role or ""
