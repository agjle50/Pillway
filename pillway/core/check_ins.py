"""Check-in status for the pharmacist dashboard (ACTIVE / WATCHING / missed) and daily/weekly messages.

Called by: pharmacist dashboard and check-ins screen, patient Check up screen.
ACTIVE   = the patient sent a message in the last few minutes (config: active_window_seconds).
WATCHING = on daily/weekly check-ins but not chatting right now.
Missed   = no check-in for N days (config: missed_check_in_days); these jump to the top.
"""

from datetime import datetime, timedelta

from config import get_settings

from .content import load


def _parse(iso):
    return datetime.fromisoformat(iso) if iso else None


def is_active(record, now=None):
    now = now or datetime.now().astimezone()
    last = _parse(record.get("last_patient_activity"))
    return bool(last and (now - last).total_seconds() <= get_settings().pharmacist.active_window_seconds)


def days_since_check_in(record, now=None):
    now = now or datetime.now().astimezone()
    last = _parse(record.get("last_patient_activity")) or _parse(record["check_ins"].get("last_check_in"))
    if not last:
        return None
    return (now - last).days


def missed_check_ins(record, now=None):
    days = days_since_check_in(record, now)
    return days is not None and days >= get_settings().safety.missed_check_in_days


def status(record, now=None):
    if is_active(record, now):
        return "ACTIVE"
    return "WATCHING" if record["check_ins"].get("watching", True) else "INACTIVE"


def topic_for(record):
    topics = load("check_in_messages")["weekly_topics"]
    wanted = (record["check_ins"].get("topic_week") or "").lower()
    for topic in topics:
        if topic["en"].lower().startswith(wanted.split()[0] if wanted else "~"):
            return topic
    return topics[0]


def daily_message(record, lang):
    """Today's check-in message (the pharmacist can override it per patient)."""
    topic = topic_for(record)
    override = record.get("check_in_messages", {}).get(f"daily_{lang}")
    text = override or topic.get(f"daily_{lang}") or topic["daily_en"]
    return text.format(first_name=record["profile"].get("first_name", ""))


def weekly_summary(record, lang, now=None):
    now = now or datetime.now().astimezone()
    week_ago = now - timedelta(days=7)
    days = {m["time"][:10] for m in record["messages"]
            if m["role"] == "patient" and _parse(m["time"]) and _parse(m["time"]) >= week_ago}
    tasks_on = sum(1 for task in record.get("tasks", []) if task.get("on"))
    topic = topic_for(record)
    template = load("check_in_messages")[f"weekly_summary_{lang}"]
    return template.format(check_ins=len(days), tasks_done=tasks_on, topic=topic.get(lang, topic["en"]))
