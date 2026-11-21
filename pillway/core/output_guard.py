"""Checks every AI reply BEFORE the patient sees it.

Called by: core/conversation_service.py (after the AI answers, before saving the reply).
Blocks: medication advice (start/stop/skip/change/timing/doses), definite diagnoses
("you have X"), pretending to be a human/doctor/pharmacist, emergency instructions that
contradict our rules, and empty or off-topic replies. If a reply fails, the caller retries
once with the correction; if it fails again it shows SAFE_FALLBACK and logs the event.
"""

import re

SAFE_FALLBACK = {
    "en": "That's a great question for your pharmacist, I've sent it to them.",
    "fr": "C'est une excellente question pour votre pharmacien, je la lui ai transmise.",
}

_MED_VERB = r"(?:start|stop|skip|quit|pause|double|increase|decrease|reduce|lower|raise|change|adjust|switch|hold|cut)"
_MED_NOUN = r"(?:medication|medicine|meds|pills?|tablets?|dose|dosage|insulin|metformin|ramipril|amlodipine|prescription)"

RULES = [
    ("medication advice", re.compile(
        rf"\b(?:you should|you can|you could|try to|i recommend|i suggest|it's ok to|it is ok to|go ahead and)\s+(?:\w+\s+){{0,3}}{_MED_VERB}\w*\s+(?:\w+\s+){{0,3}}{_MED_NOUN}", re.I)),
    ("medication advice", re.compile(rf"\b{_MED_VERB}\w*\s+(?:taking\s+)?(?:your|the)\s+{_MED_NOUN}", re.I)),
    ("medication dose", re.compile(r"\b(?:take|use|inject)\s+\d+(?:\.\d+)?\s*(?:mg|units?|ml|tablets?|pills?)\b", re.I)),
    ("medication timing", re.compile(rf"\btake\s+(?:your|the)\s+{_MED_NOUN}\s+(?:at|before|after|with|in the)\b", re.I)),
    ("definite diagnosis", re.compile(r"\b(?:you have|you've got|you definitely have|i know you have|you are suffering from|you're suffering from|this is definitely|you have been diagnosed with)\s+(?!a (?:question|great|good)|questions|time|been)", re.I)),
    ("pretends to be human", re.compile(r"\b(?:i am|i'm)\s+(?:a|your)\s+(?:human|real person|doctor|physician|nurse|pharmacist)\b", re.I)),
    ("contradicts emergency rules", re.compile(r"\b(?:don't|do not|no need to)\s+(?:call\s+911|go to (?:the )?(?:er|emergency))", re.I)),
    ("reveals instructions", re.compile(r"\b(?:system prompt|my instructions say|i was instructed to)\b", re.I)),
]

# French equivalents (basic).
RULES_FR = [
    ("medication advice", re.compile(r"\b(?:arrêtez|cessez|augmentez|diminuez|doublez|sautez)\s+(?:de prendre\s+)?(?:votre|vos|le|la|les)\s+(?:médicament|dose|insuline|comprimé)", re.I)),
    ("medication dose", re.compile(r"\bprenez\s+\d+(?:[.,]\d+)?\s*(?:mg|unités?|ml|comprimés?)\b", re.I)),
    ("definite diagnosis", re.compile(r"\b(?:vous avez|vous souffrez de|vous êtes atteinte? de)\s+(?:un |une |le |la |du |de la )?(?:diabète|neuropathie|infection|ulcère|maladie|hypertension|insuffisance)", re.I)),
    ("pretends to be human", re.compile(r"\bje suis\s+(?:un|une|votre)\s+(?:humain|médecin|infirmière|infirmier|pharmacien|pharmacienne)\b", re.I)),
]

HEALTH_WORDS = re.compile(
    r"\b(?:health|blood|sugar|glucose|pressure|diet|food|eat|meal|protein|fibre|fiber|walk|exercise|activity|"
    r"feet|foot|pharmacist|care plan|reading|target|sleep|weight|symptom|plan|santé|glycémie|tension|pied|"
    r"pharmacien|repas|protéines|fibres|marche|plan de soins|aliment|exercice)\b", re.I)


def check_reply(text, lang="en", allow_short=False):
    """Return a list of problems (empty list = safe to show)."""
    problems = []
    if not text or not text.strip():
        return ["empty reply"]
    for name, pattern in RULES + (RULES_FR if lang == "fr" else []):
        if pattern.search(text):
            problems.append(name)
    if not allow_short and len(text.split()) > 12 and not HEALTH_WORDS.search(text):
        problems.append("off-topic reply")
    return sorted(set(problems))


def correction_note(problems):
    """Short instruction sent back to the AI when we ask it to try again."""
    return ("Your last reply broke these rules: " + ", ".join(problems) +
            ". Rewrite it: no medication advice or doses, no definite diagnosis (only 'you may..., because...'), "
            "never claim to be a human, doctor or pharmacist, and stay on the patient's health.")
