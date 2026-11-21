"""Auto-generates daily tasks from the care plan, in the Alarm-style Tasks layout.

Called by: core/conversation_service.py after the care plan draft is made.
Rules: NO medication reminders, ever (medication stays with the pharmacy). Tasks only ring
after the patient allows reminders (CASL), and every task can be switched off. No duplicates.
"""

from ..storage.patient_store import new_id
from .answer_parsing import activity_bucket

MEDICATION_WORDS = ("medication", "medicine", "pill", "tablet", "dose", "insulin", "metformin", "refill", "médicament")

TASK_IDEAS = [
    # (time, am/pm, label_en, label_fr, condition)
    ("7:30", "AM", "Log your blood sugar before breakfast", "Notez votre glycémie avant le déjeuner", "diabetes"),
    ("8:00", "AM", "Check your blood pressure", "Mesurez votre tension artérielle", "blood pressure"),
    ("12:00", "PM", "Add a high-fibre food to lunch", "Ajoutez un aliment riche en fibres au dîner", "diabetes"),
    ("6:30", "PM", "{walk}", "{walk_fr}", "always"),
    ("9:00", "PM", "Check your feet", "Vérifiez vos pieds", "diabetes"),
]


def is_medication_task(label):
    return any(word in label.lower() for word in MEDICATION_WORDS)


def generate(record):
    """Return the task list for this patient (does not save)."""
    conditions = " ".join(record["profile"].get("conditions", [])).lower()
    activity = record["conversation"]["answers"].get("activity", {}).get("value", "")
    bucket = activity_bucket(activity) if activity else "low"
    walk_en, walk_fr = {"low": ("Walk 10 minutes after dinner", "Marchez 10 minutes après le souper"),
                        "medium": ("Walk 20 minutes", "Marchez 20 minutes"),
                        "high": ("Walk 30 minutes + 5 minutes of strength", "Marchez 30 minutes + 5 minutes de renforcement")}[bucket]
    tasks, seen = [], set()
    for time, ampm, label_en, label_fr, condition in TASK_IDEAS:
        if condition == "diabetes" and "diabetes" not in conditions:
            continue
        if condition == "blood pressure" and "blood pressure" not in conditions and "hypertension" not in conditions:
            continue
        label_en = label_en.format(walk=walk_en)
        label_fr = label_fr.format(walk_fr=walk_fr)
        if is_medication_task(label_en) or label_en in seen:
            continue
        seen.add(label_en)
        tasks.append({"id": new_id("task"), "time": time, "ampm": ampm, "label_en": label_en,
                      "label_fr": label_fr, "on": True, "source": "care_plan"})
    return tasks


def merge(existing, new):
    """Add new tasks without duplicating labels the patient already has."""
    labels = {task["label_en"] for task in existing}
    return existing + [task for task in new if task["label_en"] not in labels]
