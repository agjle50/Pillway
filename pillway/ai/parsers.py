"""Turns the AI's text answer into checked JSON. Unknown fields are thrown away.

Called by: ai/client.py (every structured AI job).
Why: the app acts on these fields (flags, care plan, summary), so a bad or injected
field must never get through. Anything that doesn't fit the schema is rejected and retried once.
"""

import json
import re

# field: (type, required, allowed sub-fields for lists of dicts)
SCHEMAS = {
    "reply": {
        "advice": (str, True, None),
        "possible_issues": (list, False, ("issue", "reason")),
        "summary_updates": (list, False, ("type", "value")),
        "medication_question": (bool, False, None),
        "needs_pharmacist": (bool, False, None),
    },
    "converse": {
        "reply": (str, True, None),
        "heard_as": (str, False, None),
        "answered": (list, False, ("id", "value")),
        "asking": ((str, type(None)), False, None),
        "small_talk": (bool, False, None),
        "finished": (bool, False, None),
        "possible_issues": (list, False, ("issue", "reason")),
        "summary_updates": (list, False, ("type", "value")),
        "medication_question": (bool, False, None),
    },
    "memory": {
        "memory": (str, True, None),
    },
    "flag": {
        "is_concern": (bool, True, None),
        "tier": ((int, type(None)), False, None),
        "reason": (str, False, None),
        "ask_next": (str, False, None),
    },
    "care_plan": {
        "sections": (dict, True, None),
        "barrier_plans": (list, False, ("barrier_en", "plan_en", "barrier_fr", "plan_fr")),
    },
    "summary": {
        "recap": (list, True, None),
    },
}

UPDATE_TYPES = {"symptom", "medication", "reading", "condition", "lifestyle"}


class InvalidAIOutput(ValueError):
    pass


def extract_json(text):
    """Find the first {...} block in the reply (the AI sometimes adds ```json fences)."""
    if not text:
        raise InvalidAIOutput("empty reply")
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise InvalidAIOutput("no JSON object found")
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as error:
        raise InvalidAIOutput(f"bad JSON: {error}") from None


def validate(data, schema_name):
    """Return a cleaned dict with only the allowed fields, or raise InvalidAIOutput."""
    schema = SCHEMAS[schema_name]
    if not isinstance(data, dict):
        raise InvalidAIOutput("reply is not a JSON object")
    clean = {}
    for field, (kind, required, subfields) in schema.items():
        if field not in data:
            if required:
                raise InvalidAIOutput(f"missing field {field}")
            continue
        value = data[field]
        if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
            raise InvalidAIOutput(f"field {field} has the wrong type")
        if subfields and isinstance(value, list):
            value = [{k: str(item.get(k, ""))[:400] for k in subfields} for item in value if isinstance(item, dict)][:8]
        clean[field] = value
    if schema_name == "flag":
        if clean.get("tier") not in (1, 2, 3, None):
            raise InvalidAIOutput("tier must be 1, 2, 3 or null")
        if not clean["is_concern"]:
            clean["tier"] = None
    if schema_name == "reply":
        clean["summary_updates"] = [u for u in clean.get("summary_updates", []) if u["type"] in UPDATE_TYPES]
        clean["advice"] = clean["advice"].strip()[:1200]
    if schema_name == "converse":
        clean["summary_updates"] = [u for u in clean.get("summary_updates", []) if u["type"] in UPDATE_TYPES]
        clean["reply"] = clean["reply"].strip()[:1500]
        clean["heard_as"] = clean.get("heard_as", "").strip()[:600]
        clean["answered"] = [a for a in clean.get("answered", []) if a["id"].strip()][:6]
    if schema_name == "memory":
        clean["memory"] = clean["memory"].strip()[:2000]
    if schema_name == "summary":
        clean["recap"] = [str(line)[:200] for line in clean["recap"]][:3]
    return clean


def parse(text, schema_name):
    return validate(extract_json(text), schema_name)
