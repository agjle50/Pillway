"""DEMO MODE: realistic offline replies with no API call. Same JSON shapes as the real AI.

Called by: ai/brain.py when demo_mode = true, when there is no API key, or when an AI call
fails mid-demo (then the reply shows a small "offline mode" note).
Built on the team's existing rule-based assistant (core/medical_robot.py) and data/advice.json.
"""

import re

from ..core import answer_parsing as parse
from ..core.content import advice
from ..core.medical_robot import MedicalRobot
from ..core.patient_summary import side_effect_matches
from ..core.text_normalize import normalize

FOOT_TOPICS = {"foot wound or sore", "numb feet", "foot problem", "slow healing", "tingling or numbness"}
MISSED_BY_WORDS = re.compile(r"\b(?:toe|toes|foot|feet)\b.*\b(?:purple|blue|grey|gray|cold|turned dark|smells?)\b", re.I)


class DemoBrain:
    source = "demo"

    def __init__(self):
        self._robots = {}

    # ---- layer 2 flag check ---------------------------------------------------
    def flag_check(self, record, text, layer1):
        if MISSED_BY_WORDS.search(text):
            return {"is_concern": True, "tier": 1, "reason": "Colour or temperature change in the foot: possible poor blood flow.",
                    "ask_next": "Since when has your toe looked like this? Is it painful or cold?"}
        live = [m for m in layer1.matches if not m.negated and m.tier in (1, 2)]
        if not live and not any(r.get("tier") for r in layer1.readings):
            if layer1.needs_ai_check:
                return {"is_concern": False, "tier": None, "reason": "Patient says they do not have this symptom.", "ask_next": ""}
            return {"is_concern": False, "tier": None, "reason": "", "ask_next": ""}
        topics = {m.topic for m in live}
        if topics & FOOT_TOPICS and any(m.tier == 1 for m in live):
            reason = "Non-healing foot sore and/or numb toes: risk of diabetic foot ulcer and amputation if missed."
        elif "dizziness" in topics and side_effect_matches(text, record["medications"]):
            med = side_effect_matches(text, record["medications"])[0]["medication"]
            reason = f"Dizziness, possibly a side effect of {med}" + (" or a new pill" if "new" in normalize(text) else "") + "."
        else:
            reason = "Reported " + ", ".join(sorted(topics) or [r["kind"] for r in layer1.readings]) + "."
        tier = min([m.tier for m in live] + [r["tier"] for r in layer1.readings if r.get("tier")])
        return {"is_concern": True, "tier": tier, "reason": reason, "ask_next": layer1.ask_next}

    # ---- Sarah's paragraph for one turn ---------------------------------------
    def reply(self, record, plan, text, layer1=None):
        lang = record["language"]
        result = {"advice": "", "possible_issues": [], "summary_updates": [],
                  "medication_question": parse.is_medication_question(text), "needs_pharmacist": False}
        if plan.get("advice_key") and plan["advice_key"] != "greeting":
            result["advice"] = advice(plan["advice_key"], lang, **_values(record, plan))
        if plan["ai_role"] == "changes":
            if any(u["value"] == "dizziness" for u in plan["updates"]):
                result["advice"] = {"en": "Thank you for telling me. Please stand up slowly, and sit down if you feel dizzy.",
                                    "fr": "Merci de me le dire. Levez-vous lentement et assoyez-vous si vous êtes étourdie."}[lang]
            for match in plan["side_effects"]:
                result["possible_issues"].append({
                    "issue": "a side effect from a medicine",
                    "reason": f"{match['symptom']} started recently and is a common side effect of {match['medication']}"})
        if layer1 and layer1.tier == 1 and {m.topic for m in layer1.matches} & FOOT_TOPICS:
            result["possible_issues"].append({
                "issue": "a diabetes-related foot problem",
                "reason": "a sore that won't heal and numb toes can be signs of nerve and blood-flow problems in the feet"})
        if plan["ai_role"] == "free" and not result["advice"]:
            result["advice"] = self.free_reply(record, text)
        return result

    def free_reply(self, record, text):
        if record["language"] == "fr":
            return advice("after_flow", "fr")
        robot = self._robots.setdefault(record["id"], MedicalRobot())
        robot.assessment_stage = "complete"
        answer = robot.reply(text)
        return advice("after_flow", "en") if answer == "Prompt Claude" else answer

    # ---- care plan lifestyle lines --------------------------------------------
    def care_plan_lifestyle(self, record):
        answers = record["conversation"]["answers"]
        lines = {"pharmacist_identified_goals": [], "a1c": [], "blood_pressure": [], "exercise": []}
        diet = answers.get("diet", {}).get("value")
        if diet == "unsure":
            lines["pharmacist_identified_goals"].append({
                "en": "Use the plate method at meals: half vegetables, a quarter protein, a quarter whole grains.",
                "fr": "Utilisez la méthode de l'assiette : moitié légumes, un quart protéines, un quart grains entiers."})
        sugar = answers.get("blood_sugar", {}).get("value")
        lines["a1c"].append({"en": "Write down each reading with the time and whether it was before or after a meal."
                                   + (f" Your last reading was {sugar}." if sugar and sugar != "no reading" else ""),
                             "fr": "Notez chaque mesure avec l'heure et si c'était avant ou après un repas."
                                   + (f" Votre dernière mesure était de {sugar}." if sugar and sugar != "no reading" else "")})
        lines["blood_pressure"].append({"en": "Check your blood pressure at the same time each morning, after sitting quietly for 5 minutes.",
                                        "fr": "Mesurez votre tension chaque matin à la même heure, après 5 minutes assise au calme."})
        activity = answers.get("activity", {}).get("value", "")
        bucket = parse.activity_bucket(activity) if activity else "low"
        walk = {"low": ("Start with a 10-minute walk after dinner, 5 days a week.", "Commencez par une marche de 10 minutes après le souper, 5 jours par semaine."),
                "medium": ("Add one 20-minute walk on most days to reach 150 minutes a week.", "Ajoutez une marche de 20 minutes la plupart des jours pour atteindre 150 minutes par semaine."),
                "high": ("Keep up your walks and add 2 short strength sessions a week.", "Continuez vos marches et ajoutez 2 courtes séances de renforcement par semaine.")}[bucket]
        lines["exercise"].append({"en": walk[0], "fr": walk[1]})
        lines["exercise"].append({"en": "Check your feet every evening, including between your toes.",
                                  "fr": "Vérifiez vos pieds chaque soir, y compris entre les orteils."})
        barrier = answers.get("barriers", {}).get("value")
        barrier_plans = []
        if barrier:
            plan_key = f"barriers.{parse.choose(barrier, {'time': ['time', 'temps'], 'cost': ['cost', 'coût'], 'motivation': ['motivation'], 'pain': ['pain', 'tired', 'douleur', 'fatigue']}) or 'other'}"
            barrier_plans.append({"barrier_en": barrier, "barrier_fr": barrier,
                                  "plan_en": advice(plan_key, "en").replace(" I'll add this to your care plan.", ""),
                                  "plan_fr": advice(plan_key, "fr").replace(" Je l'ajoute à votre plan de soins.", "")})
        return {"sections": lines, "barrier_plans": barrier_plans}

    # ---- pharmacist recap --------------------------------------------------------
    def recap(self, record):
        open_flags = [f for f in record["flags"] if f["status"] == "open"]
        urgent = [f for f in open_flags if f["tier"] == 1]
        first = urgent[0] if urgent else (open_flags[0] if open_flags else None)
        if not first:
            return ["No open flags.", "Check-in up to date.", "No action needed today."]
        details = [m["text"] for m in record["messages"] if m["role"] == "patient"
                   and m["time"] >= first["time"]][1:2]
        return [f"{'URGENT' if first['tier'] == 1 else 'Watch'}: {first['topic']} reported in {first['source']}.",
                f"Patient said: \"{first['text'][:90]}\"" + (f" Then: \"{details[0][:60]}\"" if details else ""),
                "Patient told a pharmacist will contact them. Suggested next step: call today."
                if first["tier"] == 1 else "Suggested next step: review at next check-in."]


def _values(record, plan):
    values = dict(plan.get("advice_values", {}))
    profile = record["profile"]
    values.setdefault("first_name", profile.get("first_name", ""))
    return values
