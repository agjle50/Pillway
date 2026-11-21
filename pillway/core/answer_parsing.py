"""Understands short patient answers without AI: yes/no, numbers, times, weights, buckets.

Called by: core/conversation_flow.py, core/patient_summary.py and ai/demo_mode.py.
Works in English and French. Keeps the demo working with no internet.
"""

import re

from .text_normalize import normalize

YES = ("yes", "yeah", "yep", "yup", "sure", "oui", "ouais", "i have", "he did", "she did", "they did", "a doctor did")
NO = ("no", "nope", "nah", "non", "never", "not really", "no changes", "no change", "nothing", "aucun",
      "rien", "pas de changement", "that's all", "thats all", "c'est tout", "all good", "i'm good", "im good")
UNSURE = ("not sure", "i'm not sure", "im not sure", "don't know", "dont know", "i don't remember", "unsure",
          "maybe", "je ne sais pas", "pas sûr", "pas sur", "je ne suis pas sûr")

MEDICATION_QUESTION = re.compile(
    r"\b(?:dose|dosage|how much (?:insulin|medication|medicine|metformin|ramipril)|how many (?:pills|units|mg)|insulin|should i (?:take|stop|skip|start|double|increase|lower)|"
    r"can i (?:take|stop|skip|start|double|increase|lower)|stop taking|skip (?:my|a) (?:pill|dose)|"
    r"double (?:my|the) dose|my (?:pills?|meds|medication|medicine)\b.*\?|when (?:do|should) i take|"
    r"dois-je (?:prendre|arrêter)|quelle dose|insuline)\b", re.I)

INJECTION = re.compile(
    r"\b(?:ignore (?:all |your |the |any )?(?:previous |prior )?(?:instructions|rules)|you are now|pretend (?:to be|you are)|"
    r"act as (?:a|my) (?:doctor|pharmacist)|system prompt|developer mode|turn off (?:the )?safety|disable (?:the )?safety|"
    r"jailbreak|new instructions|reveal your (?:prompt|instructions)|forget your rules|override)\b", re.I)


def has_phrase(text, phrases):
    clean = " " + re.sub(r"[^\w'À-ſ ]", " ", normalize(text)) + " "
    return any(f" {phrase} " in clean for phrase in phrases)


def yes_no_unsure(text):
    """'yes', 'no', 'unsure' or None. Unsure wins over yes/no ("no idea" is unsure)."""
    if has_phrase(text, UNSURE) or "?" == text.strip():
        return "unsure"
    if has_phrase(text, NO) or has_phrase(text, ("didn't", "hasn't", "has not", "did not", "not told")):
        return "no"
    if has_phrase(text, YES) or has_phrase(text, ("told me to limit", "limit my protein", "kidney")):
        return "yes"
    return None


def first_number(text):
    found = re.search(r"\d+(?:[.,]\d+)?", text)
    return float(found.group().replace(",", ".")) if found else None


def weight_kg(text):
    """'78 kg' -> 78, '172 lbs' -> 78.0. Plain numbers over 120 are assumed to be pounds."""
    value = first_number(text)
    if value is None:
        return None
    if re.search(r"\b(?:lb|lbs|pounds?|livres?)\b", text, re.I) or value > 120:
        value = value * 0.4536
    return round(value, 1)


def time_mentioned(text):
    """Pull out a time like '8 am', '7:30', 'this morning', 'before breakfast'."""
    clean = normalize(text)
    parts = []
    clock = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.|h)\b", clean)
    if clock:
        parts.append(clock.group(0))
    for phrase in ("before breakfast", "after breakfast", "before lunch", "after lunch", "before dinner",
                   "after dinner", "before supper", "after supper", "this morning", "last night", "yesterday",
                   "fasting", "before a meal", "after a meal", "before meals", "after meals",
                   "avant le déjeuner", "après le repas", "avant le repas", "ce matin"):
        if phrase in clean:
            parts.append(phrase)
    return ", ".join(parts)


def bp_reading(text):
    found = re.search(r"\b(\d{2,3})\s*/\s*(\d{2,3})\b", text)
    return f"{found.group(1)}/{found.group(2)}" if found else None


def sugar_reading(text):
    if bp_reading(text) and not re.search(r"sugar|glucose|glyc", text, re.I):
        return None
    value = first_number(re.sub(r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm|h)\b", "", text, flags=re.I))
    if value is None or value <= 0:
        return None
    if value > 40:
        value = round(value / 18, 1)
    return f"{value:g} mmol/L"


def activity_bucket(text):
    clean = normalize(text)
    if "more than 150" in clean or "plus de 150" in clean:
        return "high"
    if "90 to 150" in clean or "90 à 150" in clean or "30 to 90" in clean or "30 à 90" in clean:
        return "medium"
    if "less than 30" in clean or "moins de 30" in clean:
        return "low"
    minutes = first_number(clean)
    if minutes is None:
        return "low" if has_phrase(text, NO + ("none", "aucune", "not much", "pas beaucoup")) else "medium"
    if "hour" in clean or "heure" in clean:
        minutes *= 60
    return "high" if minutes >= 150 else "medium" if minutes >= 30 else "low"


def alcohol_bucket(text):
    clean = normalize(text)
    if has_phrase(text, ("none", "aucun", "no", "never", "jamais", "don't drink")) or clean.startswith("1 to 2") or clean.startswith("1 à 2"):
        return "low"
    number = first_number(clean)
    return "high" if number is not None and number > 2 else "low"


def choose(text, options):
    """Return the key from {key: [phrases]} whose phrase appears in the text, else None."""
    for key, phrases in options.items():
        if has_phrase(text, phrases):
            return key
    return None


def is_medication_question(text):
    return bool(MEDICATION_QUESTION.search(text))


def is_injection_attempt(text):
    return bool(INJECTION.search(text))
