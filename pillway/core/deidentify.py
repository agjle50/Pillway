"""Removes names and contact details BEFORE anything is sent to the AI, and puts the first name back after.

Called by: ai/client.py (every outgoing request) and `python Pillway.py --show-ai-payload`.
What leaves the app: age, weight, conditions, medications, readings, recent messages, all
with "Patient A" instead of the name. What never leaves: name, phone, email, address,
health card number, date of birth.
"""

import re

PLACEHOLDER = "Patient A"

PATTERNS = [
    ("[email]", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("[health card]", re.compile(r"\b\d{4}[- ]?\d{3}[- ]?\d{3}(?:[- ]?[A-Za-z]{2})?\b")),
    ("[health card]", re.compile(r"\b[A-Z]{4}[- ]?\d{4}[- ]?\d{4}\b")),
    ("[phone]", re.compile(r"(?:\+?1[ .-]?)?\(?\b\d{3}\)?[ .-]?\d{3}[ .-]?\d{4}\b")),
    ("[postal code]", re.compile(r"\b[A-Za-z]\d[A-Za-z][ -]?\d[A-Za-z]\d\b")),
    ("[date]", re.compile(r"\b(?:19|20)\d{2}[-/](?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12]\d|3[01])\b")),
    ("[address]", re.compile(r"\b\d{1,5}\s+(?:[A-Z][a-z]+\s){1,3}(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Dr|Drive|Cres|Crescent|Way|Lane|Ln|Court|Ct|rue)\b\.?", re.IGNORECASE)),
]


def _name_patterns(profile):
    names = [profile.get("first_name", ""), profile.get("last_name", "")]
    full = " ".join(n for n in names if n)
    found = [n for n in [full] + names if n and len(n) > 1]
    return [re.compile(r"\b" + re.escape(name) + r"\b", re.IGNORECASE) for name in found]


def redact_text(text, profile=None):
    """Replace identifiers inside free text (also used before writing logs)."""
    if not text:
        return text
    for pattern in _name_patterns(profile or {}):
        text = pattern.sub(PLACEHOLDER, text)
    for label, pattern in PATTERNS:
        text = pattern.sub(label, text)
    return text


def safe_profile(profile):
    """Only the facts the AI needs. No name, contact details, health card or birth date."""
    keep = ("age", "sex", "weight_kg", "height_cm", "conditions", "diabetes_type", "diagnosis_date",
            "monitoring", "last_bp", "last_a1c", "smoker", "quit_readiness", "allergies", "alcohol", "activity")
    facts = {key: profile[key] for key in keep if key in profile and profile[key] not in ("", None, [])}
    if "diagnosis_date" in facts:
        facts["diagnosis_date"] = str(facts["diagnosis_date"])[:7]  # year-month only
    facts["name"] = PLACEHOLDER
    return facts


def restore_name(text, profile):
    """Put the patient's first name back where the AI wrote the placeholder."""
    first = (profile or {}).get("first_name") or ""
    if not text or not first:
        return text
    return text.replace(PLACEHOLDER, first)
