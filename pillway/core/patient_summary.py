"""The patient summary: the intake summary Sarah reads back, and the changes the patient reports.

Called by: core/conversation_flow.py (step 2 summary, step 3 changes) and ai/demo_mode.py.
Only valid, relevant health information becomes an update (new symptoms, new or changed
medicines, new readings, new conditions, lifestyle changes). Small talk is ignored.
"""

import re

from .answer_parsing import bp_reading, has_phrase
from .content import advice, load
from .safety_rules import check_message
from .text_normalize import normalize, words

NEW_MEDICATION = ("new pill", "new pills", "new medication", "new medicine", "new prescription", "started me on",
                  "started taking", "put me on", "new drug", "nouveau médicament", "nouvelle pilule")
CONDITION = re.compile(r"\b(?:diagnosed with|told me i have|found out i have|diagnostiqué(?:e)? (?:avec|d'un|d'une))\s+([\w\s'-]{3,40})", re.I)
LIFESTYLE = {"stopped smoking": "stopped smoking", "quit smoking": "stopped smoking",
             "started walking": "started walking", "new diet": "started a new diet", "joined a gym": "joined a gym",
             "arrêté de fumer": "stopped smoking"}
SYMPTOM_WORDS = {"dizzy": "dizziness", "dizziness": "dizziness", "lightheaded": "lightheadedness",
                 "cough": "cough", "headache": "headache", "tired": "tiredness", "nauseous": "nausea",
                 "étourdi": "dizziness", "étourdie": "dizziness", "étourdissements": "dizziness"}


def _join(items, lang):
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + f" {advice('intake_bits.and', lang)} " + items[-1]


def intake_summary(record, lang):
    """Step 2: the hard-coded summary of what the short intake questionnaire told us."""
    profile = record["profile"]
    conditions = [c.split(" (")[0].lower() for c in profile.get("conditions", [])]
    if lang == "fr":
        conditions = [c.replace("type 2 diabetes", "le diabète de type 2").replace("high blood pressure", "l'hypertension")
                      for c in conditions]
    meds = [f"{m['name']} {m.get('dose', '')}".strip() for m in record.get("medications", [])]
    smoking = advice("intake_bits.smoker" if profile.get("smoker") else "intake_bits.non_smoker", lang)
    template = load("questions")["intro"]
    return template[f"summary_{lang}"].format(
        conditions=_join(conditions, lang) or "your health", last_bp=profile.get("last_bp", "not on file"),
        smoking_text=smoking, medications=_join(meds, lang) or advice("intake_bits.no_meds", lang))


def side_effect_matches(text, medications):
    """Symptoms in the message that are known common side effects of the patient's listed medicines."""
    tokens = words(normalize(text))
    found = []
    for med in medications:
        for effect in med.get("common_side_effects", []):
            stems = [w[:4] for w in effect.lower().split() if len(w) > 3 and w not in ("upset",)]
            if stems and any(token.startswith(stem) for token in tokens for stem in stems[-1:]):
                found.append({"symptom": effect, "medication": med["name"]})
    unique = {}
    for item in found:
        unique.setdefault(item["symptom"], item)
    return list(unique.values())


def detect_changes(text, record):
    """Rule-based change detection (offline). Returns a list of {'type', 'value'} updates."""
    updates = []
    safety = check_message(text)
    symptoms = {m.topic for m in safety.matches if m.tier in (1, 2) and not m.negated}
    for token in words(normalize(text)):
        if token in SYMPTOM_WORDS:
            symptoms.add(SYMPTOM_WORDS[token])
    if "dizziness" in symptoms:
        symptoms.discard("dizzy")
    updates += [{"type": "symptom", "value": s} for s in sorted(symptoms)]
    if has_phrase(text, NEW_MEDICATION):
        updates.append({"type": "medication", "value": advice("intake_bits.name_not_given", "en")})
    for reading in safety.readings:
        updates.append({"type": "reading", "value": f"{reading['kind']} {reading['value']}"})
    if bp_reading(text) and not safety.readings:
        updates.append({"type": "reading", "value": f"blood pressure {bp_reading(text)}"})
    condition = CONDITION.search(text)
    if condition:
        updates.append({"type": "condition", "value": condition.group(1).strip()})
    for phrase, value in LIFESTYLE.items():
        if phrase in normalize(text):
            updates.append({"type": "lifestyle", "value": value})
    return updates


def describe_updates(updates, lang):
    lines = []
    for update in updates:
        value = update["value"]
        if lang == "fr" and value == advice("intake_bits.name_not_given", "en"):
            value = advice("intake_bits.name_not_given", "fr")
        lines.append("• " + advice(f"update_labels.{update['type']}", lang, value=value))
    return "\n".join(lines)
