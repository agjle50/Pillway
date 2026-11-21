"""LAYER 1 SAFETY: hard-coded rules that run on every patient message. No internet, no AI.

Called by: core/flagging.py (every chat message and every call sentence).
Layer 1 decides whether a message is URGENT. The AI (layer 2) can add or raise a flag,
but can never remove or downgrade a Tier 1 decided here.

What it checks:
  * buzzwords from data/buzzwords.json (word-boundary match, simple plurals)
  * foot word + symptom word in the same sentence ("my toes feel numb")
  * numbers: blood sugar (mmol/L) and blood pressure (top/bottom) against config thresholds
  * negation ("no vomiting", "my foot doesn't hurt") -> "needs AI check", never silently dropped
Tier 3 words (age, background, weight, history) are context only and never alert.
"""

import json
import re
from dataclasses import asdict, dataclass, field

from config import get_settings

from .text_normalize import normalize, sentences, singular_text

_cache = {}


@dataclass
class Match:
    topic: str
    phrase: str
    tier: int
    negated: bool = False
    ask_next: str = ""


@dataclass
class SafetyResult:
    tier: int | None = None          # 1 urgent, 2 watch, 3 context only, None nothing found
    matches: list = field(default_factory=list)
    readings: list = field(default_factory=list)
    needs_ai_check: bool = False     # a danger word was negated; layer 2 should look
    ask_next: str = ""

    @property
    def is_alert(self):
        return self.tier in (1, 2)

    @property
    def matched_words(self):
        return [m.phrase for m in self.matches if not m.negated and m.tier in (1, 2)]

    def to_dict(self):
        data = asdict(self)
        data["matched_words"] = self.matched_words
        return data


def load_buzzwords(path=None):
    """Read data/buzzwords.json once (cached)."""
    path = path or get_settings().path(get_settings().safety.buzzwords_file)
    key = str(path)
    if key not in _cache:
        _cache[key] = json.loads(path.read_text(encoding="utf-8"))
    return _cache[key]


def _phrase_regex(phrase):
    return re.compile(r"(?<![\w'])" + re.escape(singular_text(phrase)) + r"(?![\w'])")


def _is_negated(sentence, start, negations):
    """True if a negation word appears in the 5 words before position `start`."""
    before = sentence[:start].split()[-5:]
    joined = " " + " ".join(before) + " "
    return any(f" {word} " in joined for word in negations)


def _scan_rules(sentence, rules, tier, negations, matches):
    for rule in rules:
        required = rule.get("requires_any")
        if required and not any(_phrase_regex(r).search(sentence) for r in required):
            continue
        for phrase in rule["phrases"]:
            found = _phrase_regex(phrase).search(sentence)
            if not found:
                continue
            rule_tier = tier
            if rule.get("tier1_if_also") and any(_phrase_regex(w).search(sentence) for w in rule["tier1_if_also"]):
                rule_tier = 1
            matches.append(Match(rule["topic"], phrase, rule_tier,
                                 _is_negated(sentence, found.start(), negations), rule.get("ask_next", "")))
            break


def _scan_foot_combo(sentence, combo, negations, matches, first_index, foot_ask):
    """Foot word + symptom word in one sentence. Skipped if a foot phrase already matched."""
    if not combo or not any(_phrase_regex(w).search(sentence) for w in combo["body"]):
        return
    this_sentence = matches[first_index:]
    if any(m.tier == 1 and not m.negated for m in this_sentence):
        return
    for tier, key in ((1, "tier1_symptoms"), (2, "tier2_symptoms")):
        for word in combo[key]:
            if _phrase_regex(word).search(sentence):
                negated = any(_phrase_regex(n).search(sentence) for n in negations)
                matches.append(Match("foot problem", word, tier, negated, foot_ask))
                return


def _number(text):
    return float(text.replace(",", "."))


def check_readings(text, thresholds):
    """Find blood pressure and blood sugar numbers. Returns a list of reading dicts."""
    readings, t = [], thresholds
    bp_spans = []
    for found in re.finditer(r"\b(\d{2,3})\s*/\s*(\d{2,3})\b", text):
        bp_spans.append(found.span())
        systolic, diastolic = int(found.group(1)), int(found.group(2))
        tier = None
        if systolic >= t.bp_systolic_urgent or diastolic >= t.bp_diastolic_urgent:
            tier = 1
        elif systolic >= t.bp_systolic_watch or diastolic >= t.bp_diastolic_watch or systolic < t.bp_systolic_low:
            tier = 2
        readings.append({"kind": "blood pressure", "value": f"{systolic}/{diastolic}", "tier": tier})
    pattern = r"(?:sugar|glucose|\bbg\b|reading|meter|glycemia|glyc[ée]mie)\D{0,25}?(\d{1,3}(?:[.,]\d+)?)|(\d{1,2}(?:[.,]\d+)?)\s*mmol"
    for found in re.finditer(pattern, text):
        if any(start <= found.start(1 if found.group(1) else 2) < end for start, end in bp_spans):
            continue
        value = _number(found.group(1) or found.group(2))
        unit_note = ""
        if value > 40:  # probably mg/dL (US units)
            value, unit_note = round(value / 18, 1), " (converted from mg/dL)"
        tier = None
        if value < t.blood_sugar_low or value >= t.blood_sugar_very_high:
            tier = 1
        elif value >= t.blood_sugar_high:
            tier = 2
        readings.append({"kind": "blood sugar", "value": f"{value:g} mmol/L{unit_note}", "tier": tier})
    return readings


def check_message(text, extra_words=(), thresholds=None, buzzwords=None):
    """Run every layer 1 rule on one patient message and return a SafetyResult."""
    data = buzzwords or load_buzzwords()
    thresholds = thresholds or get_settings().safety
    negations = data.get("negation_words", [])
    foot_ask = next((r["ask_next"] for r in data["tier1"] if r["topic"] == "foot wound or sore"), "")
    clean = normalize(text)
    matches = []
    for raw_sentence in sentences(clean):
        sentence = singular_text(raw_sentence)
        before = len(matches)
        _scan_rules(sentence, data["tier1"], 1, negations, matches)
        _scan_rules(sentence, data["tier2"], 2, negations, matches)
        _scan_foot_combo(sentence, data.get("foot_combo"), negations, matches, before, foot_ask)
        _scan_rules(sentence, data["tier3"], 3, negations, matches)
        if extra_words:
            _scan_rules(sentence, [{"topic": "pharmacist watch word", "phrases": list(extra_words),
                                    "ask_next": "Can you tell me more about that?"}], 2, negations, matches)
    result = SafetyResult(matches=matches, readings=check_readings(clean, thresholds))
    live = [m.tier for m in matches if not m.negated] + [r["tier"] for r in result.readings if r["tier"]]
    result.tier = min(live) if live else None
    result.needs_ai_check = any(m.negated and m.tier in (1, 2) for m in matches)
    urgent_first = sorted((m for m in matches if not m.negated and m.tier in (1, 2)), key=lambda m: m.tier)
    if urgent_first:
        result.ask_next = urgent_first[0].ask_next
    elif any(r["tier"] for r in result.readings):
        result.ask_next = "When did you take this reading, and how are you feeling right now?"
    return result
