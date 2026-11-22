"""Sarah's brain: one interface for the real AI and demo mode, with automatic fallback.

Called by: core/conversation_service.py and the pharmacist screens (recaps).
Every method returns (data, source): source is "ai", "demo" (demo mode on / no key) or
"offline" (the AI failed mid-demo, so demo mode answered and the UI shows a small note).
This file builds the de-identified context; ai/client.py sends it.
"""

import json
from functools import lru_cache
from pathlib import Path

from config import get_settings

from ..core.deidentify import redact_text, restore_name, safe_profile
from ..core.medical_guidance import CARE_PLAN_REFERENCE, MEDICAL_KEYWORDS
from .client import OK, AIClient
from .demo_mode import DemoBrain

PROMPTS = Path(__file__).parent / "prompts"


@lru_cache(maxsize=1)
def _examples():
    return "\n\n".join(path.read_text(encoding="utf-8") for path in sorted((PROMPTS / "examples").glob("*.md")))


def system_prompt(lang="en"):
    settings = get_settings()
    legacy = "\n".join(f"- {branch['topic']}: {branch['response']}" for branch in MEDICAL_KEYWORDS)
    legacy += "\n" + "\n".join(f"- {label}: {text}" for label, text in CARE_PLAN_REFERENCE)
    text = (PROMPTS / "system_prompt.md").read_text(encoding="utf-8").format(
        assistant=settings.branding.assistant_name, pharmacy=settings.branding.pharmacy_name,
        language="French (Canada)" if lang == "fr" else "English", legacy_guidance=legacy)
    return text + "\n\n# Worked examples\n\n" + _examples()


def conversation_system_prompt(lang="en"):
    """Natural mode: the same persona and hard rules, but Sarah writes the whole reply."""
    full = system_prompt(lang)
    head = full.split("# Your job in each turn")[0]
    tail = full.split("# Existing Sarah guidance", 1)[1] if "# Existing Sarah guidance" in full else ""
    job = (PROMPTS / "conversation.md").read_text(encoding="utf-8").replace("{{", "{").replace("}}", "}")
    return head + job + "\n\n# Existing Sarah guidance" + tail


MEMORY_PROMPT = """You keep a compact memory for a pharmacy care assistant, so she remembers each patient
like a person would. You get the current memory and the latest exchange. Return an updated memory.

Keep (most important first): health facts and readings with dates, new symptoms and how they
changed, medicines mentioned, worries, what they found hard, goals, what was already covered in the
check-in, open questions for the pharmacist, and personal details they shared in small talk (family,
hobbies, plans, mood) that a caring person would remember. Drop greetings and filler. Merge, don't
repeat. Never invent anything. Use "Patient A" for the patient. At most 200 words, short lines.

Answer ONLY with JSON: {"memory": "the updated memory"}"""


def patient_context(record, limit=8):
    """Only the facts the AI needs, de-identified. Shown by --show-ai-payload."""
    profile = record["profile"]
    meds = [{k: m.get(k) for k in ("name", "dose", "frequency", "indication")} for m in record["medications"]]
    session_id = record["conversation"].get("session_id")
    current_session = next(
        (session for session in record.get("sessions", []) if session.get("id") == session_id),
        None,
    )
    current_messages = (
        [message for message in record["messages"] if message.get("session_id") == session_id]
        if session_id else [
            message for message in record["messages"] if not message.get("session_id")
        ][-limit:]
    )
    recent = [{"from": "patient" if m["role"] == "patient" else "assistant",
               "text": redact_text(m["text"], profile)} for m in current_messages[-limit:]]
    patient_turns = [message for message in current_messages if message.get("role") == "patient"]

    previous_interaction = None
    previous_session = (current_session or {}).get("previous_interaction")
    if previous_session:
        previous_messages = [
            message for message in record["messages"]
            if message.get("session_id") == previous_session.get("session_id")
        ][-limit:]
        previous_interaction = {
            "kind": previous_session.get("kind", "CHAT"),
            "last_contact": previous_session.get("at", ""),
            "topic": redact_text(previous_session.get("topic", ""), profile),
            "messages": [
                {"from": "patient" if message["role"] == "patient" else "assistant",
                 "text": redact_text(message["text"], profile)}
                for message in previous_messages
            ],
        }
    answers = {qid: a.get("value") for qid, a in record["conversation"]["answers"].items()}
    return {
        "patient": safe_profile(profile),
        "medications": meds,
        "changes_reported": [u["text"] for u in record.get("summary_updates", [])][-6:],
        "answers_so_far": answers,
        "pharmacist_settings": record["bot_settings"],
        "recent_messages": recent,
        "session_opening": len(patient_turns) == 1,
        "memory": (record.get("memory") or {}).get("text", ""),
        "previous_interaction": previous_interaction,
    }


class Brain:
    def __init__(self):
        self.client = AIClient()
        self.demo = DemoBrain()

    @property
    def live(self):
        return self.client.available

    def status_note(self):
        return "" if self.live else self.client.unavailable_reason

    def _ask(self, job, system, record, task, message, schema):
        payload = json.dumps(patient_context(record), ensure_ascii=False, indent=1)
        user = (f"<patient_data>\n{payload}\n</patient_data>\n\nTASK: {task}\n\n"
                f"<patient_message>\n{redact_text(message, record['profile'])}\n</patient_message>")
        return self.client.complete(job, system, user, schema, profile=record["profile"])

    def converse(self, record, text, channel, checklist, facts):
        """Natural mode: Sarah's whole reply, written freely. Returns (data, status)."""
        if not self.live:
            return None, "unavailable"
        context = patient_context(record, limit=14)
        context.update(channel=channel, checklist=checklist, facts=facts)
        payload = json.dumps(context, ensure_ascii=False, indent=1)
        user = (f"<patient_data>\n{payload}\n</patient_data>\n\n"
                f"TASK: Reply to the patient's latest message as {get_settings().branding.assistant_name}.\n\n"
                f"<patient_message>\n{redact_text(text, record['profile'])}\n</patient_message>")
        job = "call" if channel == "call" else "chat"
        data, status = self.client.complete(job, conversation_system_prompt(record["language"]), user, "converse",
                                            profile=record["profile"],
                                            temperature=get_settings().ai.conversation_temperature)
        if status == OK:
            data["reply"] = restore_name(data["reply"], record["profile"])
            data["heard_as"] = restore_name(data.get("heard_as", ""), record["profile"])
        return data, status

    def update_memory(self, record, exchange):
        """Fold the latest exchange into the patient's compact memory. Returns the new text or None."""
        if not self.live:
            return None
        current = (record.get("memory") or {}).get("text", "") or "(empty: first conversation)"
        lines = "\n".join(f"{who}: {redact_text(said, record['profile'])}" for who, said in exchange)
        user = f"<current_memory>\n{current}\n</current_memory>\n\n<latest_exchange>\n{lines}\n</latest_exchange>"
        data, status = self.client.complete("memory", MEMORY_PROMPT, user, "memory", profile=record["profile"],
                                            temperature=0.2)
        return data["memory"] if status == OK else None

    def flag_check(self, record, text, layer1):
        if not get_settings().ai.ai_safety_layer_enabled:
            return None, "disabled"
        if self.live:
            system = (PROMPTS / "flag_check.md").read_text(encoding="utf-8")
            data, status = self._ask("flag", system, record, "Check the latest patient message for safety.", text, "flag")
            if status == OK:
                return data, "ok"
            return None, "unavailable"
        return self.demo.flag_check(record, text, layer1), "ok"

    def reply(self, record, plan, text, task, layer1=None):
        if self.live and plan.get("ai_role"):
            data, status = self._ask("chat", system_prompt(record["language"]), record, task, text, "reply")
            if status == OK:
                data["advice"] = restore_name(data["advice"], record["profile"])
                return data, "ai"
            return self.demo.reply(record, plan, text, layer1), "offline"
        return self.demo.reply(record, plan, text, layer1), "demo"

    def care_plan_lifestyle(self, record):
        if self.live:
            system = (PROMPTS / "care_plan.md").read_text(encoding="utf-8")
            task = "Write the lifestyle lines. Readiness: " + str((record.get("care_plan") or {}).get("readiness", "not set"))
            data, status = self._ask("care_plan", system, record, task, "(no new message)", "care_plan")
            if status == OK:
                return data, "ai"
            return self.demo.care_plan_lifestyle(record), "offline"
        return self.demo.care_plan_lifestyle(record), "demo"

    def recap(self, record):
        if self.live:
            system = (PROMPTS / "summary.md").read_text(encoding="utf-8")
            data, status = self._ask("summary", system, record, "Write the 3-line recap.", "(no new message)", "summary")
            if status == OK:
                return [restore_name(line, record["profile"]) for line in data["recap"]], "ai"
        return self.demo.recap(record), "demo"
