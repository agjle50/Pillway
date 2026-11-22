"""Builds, edits, approves and renders Pillway's SIMPLE care plan (everyday words, EN + FR).

Called by: core/conversation_service.py (draft after the check-in), the patient Care plan tab
and the pharmacist care plan editor.

How a plan is made (plain words):
  1. RULES look at the patient's intake questionnaire and check-in answers and decide which
     lines are relevant. Nothing is included "just because": no alcohol line for someone who
     doesn't drink, no protein line until the protein question was answered "no limit", etc.
  2. For each target line the rules propose a starting value WITH A REASON
     (e.g. "Move: 90 minutes a week" because "you said about 30 minutes last week").
  3. The AI (DeepSeek by default) then writes SMART goals from the patient's own goal and concerns, may
     improve the suggested values (with reasons), and picks recommendations ONLY from Pillway's
     fixed list (data/care_plan_template.json -> recommendations).
  4. Every suggested value is marked "to check": the pharmacist sees it highlighted with the
     reason, and can Confirm or Change it. Approving accepts whatever is left as suggested
     (logged), so a pharmacist can let a good plan straight through.
The Medications section is never written by the AI.
"""

import copy
import re

from config import get_settings

from ..storage import audit_log
from ..storage.edit_history import last_undoable, record_edit
from ..storage.patient_store import now_iso
from .content import load

BLANK = "_____"
FOOT_WORDS = ("foot", "feet", "toe", "heel", "pied", "orteil", "talon")


# ---- 1 + 2: what is relevant for THIS patient, and the starting values ---------------------

def _answer(record, qid):
    item = record["conversation"]["answers"].get(qid) or {}
    return str(item.get("value") or "").strip(), str(item.get("text") or "").strip()


def _minutes(text):
    match = re.search(r"(\d+(?:\.\d+)?)", text or "")
    if not match:
        return None
    value = float(match.group(1))
    return value * 60 if re.search(r"hour|heure|hr", text, re.I) else value


def _drinks(text):
    if re.search(r"\b(no|none|never|don't drink|do not drink|0|aucun|jamais)\b", text or "", re.I):
        return 0
    match = re.search(r"(\d+)", text or "")
    return int(match.group(1)) if match else None


def relevant(record):
    """{line_id: (value or "", reason)} for target lines + the chosen recommendation ids.

    Returns (targets, recommendations, every_day). Pure rules: works with no AI at all.
    """
    profile = record["profile"]
    intake = (record.get("intake") or {}).get("answers", {})
    conditions = " ".join(profile.get("conditions", [])).lower()
    diabetes = "diabet" in conditions
    bp_known = ("blood pressure" in conditions or "hypertension" in conditions or intake.get("bp_systolic")
                or _answer(record, "blood_pressure")[0] not in ("", "no reading"))
    targets, recs, daily = {}, [], []

    gestational = "gestational" in conditions
    if diabetes or _answer(record, "blood_sugar")[0]:
        if gestational:   # pregnancy targets are different: the pharmacist sets this one
            targets["a1c_target"] = ("", "Gestational diabetes: targets in pregnancy differ, so the pharmacist sets this.")
        else:
            targets["a1c_target"] = ("7.0", "Diabetes Canada's usual A1C target for most adults with type 2 diabetes.")
        monitoring = str(profile.get("monitoring", "")).lower()
        if "libre" in monitoring or "cgm" in monitoring or "sensor" in monitoring:
            targets["sugar_checks"] = ("keep your sensor on and look at your readings every day",
                                       "They already use a glucose sensor.",
                                       "gardez votre capteur et regardez vos lectures chaque jour")
        else:
            sugar = _answer(record, "blood_sugar")[0]
            targets["sugar_checks"] = ("before breakfast and 2 hours after your biggest meal, 3 days a week",
                                       "Newly diagnosed and using finger pricks" + (f"; last reading {sugar}."
                                       if sugar and sugar != "no reading" else "; no recent reading given."),
                                       "avant le déjeuner et 2 heures après votre plus gros repas, 3 jours par semaine")
    pressure_condition = "blood pressure" in conditions or "hypertension" in conditions
    if bp_known:
        average = f"{intake['bp_systolic']}/{intake['bp_diastolic']}" if intake.get("bp_systolic") else profile.get("last_bp")
        targets["bp_target"] = ("130/80", "Pillway's resting blood pressure target" +
                                (" with diabetes" if diabetes else "") + (f"; their average is {average}." if average else "."))
        daily.append("bp_daily")
    salt = _answer(record, "salt")[0].lower()
    if pressure_condition or (salt and "rarely" not in salt):
        daily.append("salt_daily")
    activity_value, activity_text = _answer(record, "activity")
    if activity_value or activity_text:
        minutes = _minutes(activity_text or activity_value)
        if minutes is None or minutes < 60:
            targets["exercise_target"] = ("90", f"They said about {round(minutes) if minutes is not None else 'little'} "
                                          "minutes last week: build up slowly toward Pillway's 150 minimum.")
        elif minutes < 150:
            targets["exercise_target"] = ("150", f"They said about {round(minutes)} minutes: Pillway's minimum is 150.")
        else:
            targets["exercise_target"] = ("300", f"Already about {round(minutes)} minutes: Pillway's target is 300.")
    protein_value = _answer(record, "protein_limit")[0].lower()
    if protein_value == "no" and profile.get("protein_target"):
        targets["protein"] = ("", "Worked out from their weight (0.8 to 1.0 g per kg); no doctor limit on protein.")
    diet = _answer(record, "diet")[0].lower()
    if diet:
        targets["fibre"] = ("30", "Pillway's guideline is 30 to 50 g; start at the easier end.")
    drinks = _drinks(" ".join(_answer(record, "alcohol")))
    if drinks:
        targets["alcohol"] = ("2", f"They have about {drinks} a week; Pillway's maximum is 2 standard drinks.")

    concerns = " ".join(_answer(record, "concerns") + _answer(record, "goal")).lower()
    bmi_high = False
    if profile.get("weight_kg") and profile.get("height_cm"):
        bmi_high = profile["weight_kg"] / (profile["height_cm"] / 100) ** 2 >= 25
    if diabetes:
        recs += ["coaching", "labs"]
        monitoring = str(profile.get("monitoring", "")).lower()
        if not any(word in monitoring for word in ("libre", "cgm", "sensor")):
            recs.append("cgm")
        daily.insert(0, "feet_daily")
        recs.append("eye_exam")             # retinopathy: one of the topics in Pillway's care plans
    elif bp_known:
        recs.append("labs")
    if diet in ("unsure", "better") or bmi_high or any(w in concerns for w in ("weight", "diet", "food", "eat")) \
            or (targets.get("exercise_target", ("",))[0] == "90"):
        recs.insert(0, "lifestylerx")
    if diet == "unsure" or protein_value in ("yes", "unsure"):
        recs.append("dietitian")
    if profile.get("smoker") and str(profile.get("quit_readiness", "")).lower().startswith(("i am motivated", "i am thinking",
                                                                                            "ready", "thinking")):
        recs.append("quit_smoking")
    return targets, list(dict.fromkeys(recs)), daily


# Pillway's guideline ranges. An AI-suggested value outside them is ignored (the rule's value stays).
def _between(low, high):
    def check(value):
        match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(?:%|g|minutes|min)?\s*", value)
        return bool(match) and low <= float(match.group(1)) <= high
    return check


def _bp_ok(value):
    match = re.fullmatch(r"\s*(\d{2,3})\s*/\s*(\d{2,3})\s*(?:mmhg)?\s*", value.lower())
    return bool(match) and 110 <= int(match.group(1)) <= 140 and 60 <= int(match.group(2)) <= 90


GUIDELINE_RANGES = {
    "a1c_target": _between(6.0, 8.5),          # usually 7.0 or lower; up to 8.5 for frail older adults
    "bp_target": _bp_ok,                        # below 130/80 usual; never above 140/90
    "exercise_target": _between(30, 300),       # a small start is allowed, up to Pillway's 300 target
    "fibre": _between(30, 50),                  # Pillway: 30-50 g a day
    "alcohol": _between(0, 2),                  # Pillway: max 2 standard drinks a week
    "sugar_checks": lambda value: 5 <= len(value) <= 120,
}


def ai_value_ok(line_id, value):
    check = GUIDELINE_RANGES.get(line_id)
    return bool(check and check(str(value)))


def _has(record, word):
    return word in " ".join(record["profile"].get("conditions", [])).lower()


def rule_goals(record):
    """Backup SMART goals (used when the AI is off): specific, measurable, timed."""
    goals = []
    targets, _recs, _daily = relevant(record)
    goal_text = _answer(record, "goal")[1] or _answer(record, "goal")[0]
    if "exercise_target" in targets:
        first = {"90": ("Walk 15 minutes after dinner, 5 days a week, for the next 4 weeks.",
                        "Marchez 15 minutes après le souper, 5 jours par semaine, pendant les 4 prochaines semaines."),
                 "150": ("Walk 30 minutes, 5 days a week, for the next 4 weeks.",
                         "Marchez 30 minutes, 5 jours par semaine, pendant les 4 prochaines semaines."),
                 "300": ("Keep your walks and add 2 short strength sessions a week this month.",
                         "Continuez vos marches et ajoutez 2 courtes séances de renforcement par semaine ce mois-ci.")}
        goals.append(first[targets["exercise_target"][0]])
    if "fibre" in targets:
        goals.append(("Use the plate method at dinner (half vegetables) at least 5 days a week for 4 weeks.",
                      "Utilisez la méthode de l'assiette au souper (moitié légumes) au moins 5 jours par semaine pendant 4 semaines."))
    if "sugar_checks" in targets:
        goals.append(("Write down every blood sugar reading with the time for the next 2 weeks, and bring the list to your pharmacist.",
                      "Notez chaque glycémie avec l'heure pendant les 2 prochaines semaines, et apportez la liste à votre pharmacien."))
    if goal_text:
        goals.insert(0, (f"Your goal ({goal_text}): choose one small step, do it 3 times a week, and we'll check "
                         "how it's going at your follow-up in 4 weeks.",
                         f"Votre objectif ({goal_text}) : choisissez une petite étape, faites-la 3 fois par semaine, et "
                         "nous ferons le point à votre suivi dans 4 semaines."))
    return [{"en": en, "fr": fr} for en, fr in goals[:3]]


# ---- 3: build the draft ------------------------------------------------------------------

def _line(base, **extra):
    line = {"id": base["id"], "kind": base["kind"], "en": base["en"], "fr": base["fr"], "value": "", "included": True,
            "ai": False, "needs_review": False, "note": base.get("note", ""), "suggested": False, "confirmed": True,
            "reason": ""}
    line.update(extra)
    return line


def build_draft(record, ai_plan, source):
    """A new simple draft: rules decide what's relevant, the AI's suggestions are merged in.

    ai_plan: {"smart_goals": [{en, fr}], "values": [{id, value, reason}], "recommendations": [ids],
              "barrier_plans": [...]} (from ai/brain.py or the demo backup). Anything it says about a
    line that isn't relevant, or a recommendation that isn't on Pillway's list, is ignored.
    """
    template = load("care_plan_template")
    settings = get_settings()
    ai_plan = ai_plan or {}
    targets, recs, daily = relevant(record)
    by_ai = {str(v.get("id", "")).strip(): v for v in ai_plan.get("values", []) if isinstance(v, dict)}
    catalogue = {item["id"]: item for item in template["recommendations"]}
    for rec in ai_plan.get("recommendations", []):
        rec = str(rec).strip()
        if rec in catalogue and rec not in recs and rec != "quit_smoking":   # smoking stays rule-based
            recs.append(rec)
    feet_flag = any(f.get("tier") == 1 and any(w in (f.get("topic", "") + " " + f.get("text", "")).lower()
                                               for w in FOOT_WORDS) for f in record.get("flags", []))
    sections = []
    for section in template["sections"]:
        lines = []
        sid = section["id"]
        if sid == "smart_goals":
            goals = [g for g in ai_plan.get("smart_goals", []) if isinstance(g, dict) and g.get("en")][:3]
            from_ai = bool(goals) and source == "ai"
            for index, goal in enumerate(goals or rule_goals(record)):
                lines.append(_line({"id": f"goal_{index}", "kind": "smart_goal", "en": goal["en"],
                                    "fr": goal.get("fr") or goal["en"]}, ai=from_ai, needs_review=True,
                                   note="SMART goal written by the AI from the patient's answers." if from_ai
                                   else "SMART goal from the backup rules."))
        elif sid == "targets":
            for base in section["lines"]:
                if base["id"] not in targets:
                    continue
                value, reason, *french = targets[base["id"]]
                value_fr = french[0] if french else ""
                ai = by_ai.get(base["id"])
                if not value and base["id"] == "a1c_target":
                    ai = None   # left for the pharmacist on purpose (e.g. gestational diabetes): the AI never fills it
                if ai and str(ai.get("value", "")).strip() and not ai_value_ok(base["id"], ai["value"]):
                    from .. import debug_log
                    debug_log.log("careplan", "AI value outside Pillway's guideline ignored", line=base["id"],
                                  value=str(ai["value"])[:20])
                    ai = None
                if ai and str(ai.get("value", "")).strip() and base["kind"] == "suggested":
                    value, reason = str(ai["value"]).strip()[:60], str(ai.get("reason") or reason)[:200]
                    value_fr = ""
                suggested = base["kind"] == "suggested" and bool(value)   # empty = the pharmacist sets it
                lines.append(_line(base, value=value, value_fr=value_fr, suggested=suggested,
                                   confirmed=not suggested, reason=reason, ai=bool(ai) and suggested))
        elif sid == "recommended":
            for rec in recs:
                item = catalogue[rec]
                lines.append(_line({"id": f"rec_{rec}", "kind": "recommendation", "en": item["en"], "fr": item["fr"]},
                                   reason=f"Included because: {item['when']}."))
        elif sid == "every_day":
            for base in section["lines"]:
                if base["id"] not in daily:
                    continue
                line = _line(base)
                if base["id"] == "feet_daily" and feet_flag:
                    line.update(en="Your pharmacist is following up on the sore you told Sarah about. Until then, look at "
                                   "your feet every day and keep the area clean and covered.",
                                fr="Votre pharmacien fait le suivi de la plaie dont vous avez parlé à Sarah. D'ici là, "
                                   "regardez vos pieds chaque jour et gardez la zone propre et couverte.",
                                reason="A foot sore was flagged during the check-in.")
                lines.append(line)
        elif sid == "resources":
            diabetes_on, pressure_on = _has(record, "diabet"), (_has(record, "blood pressure") or _has(record, "hypertension"))
            for base in section["lines"]:
                wanted = base.get("for")
                if (wanted == "diabetes" and diabetes_on) or (wanted == "blood pressure" and pressure_on) \
                        or not (diabetes_on or pressure_on):
                    lines.append(_line(base, reason="Public patient resource (plain language)."))
        elif sid == "medications":
            meds = record.get("medications", [])
            if meds:
                listed = "; ".join(f"{m['name']} {m.get('dose', '')} {m.get('frequency', '')}".strip() for m in meds)
                lines.append(_line({"id": "med_list", "kind": "pharmacy_record", "en": f"On file: {listed}.",
                                    "fr": f"Au dossier : {listed}."}, note="From the pharmacy record, not the AI."))
            lines += [_line(base) for base in section["lines"]]
        if lines:
            sections.append({"id": sid, "en": section["en"], "fr": section["fr"], "lines": lines})
    goal = _answer(record, "goal")[1] or _answer(record, "goal")[0]
    review = settings.pharmacist.pharmacist_review_required
    plan = {
        "format": "simple",
        "status": "draft" if review else "published_without_review",
        "created": now_iso(), "source": source, "review_required": review,
        "readiness": None, "readiness_other": "",
        "goals": [goal] if goal else [],
        "protein_target": record["profile"].get("protein_target", ""),
        "sections": sections,
        "barriers": ai_plan.get("barrier_plans", []),
        "approved_by": None, "approved_at": None, "change_requests": [],
    }
    audit_log.record("care_plan_drafted", record["id"], source=source, review_required=review,
                     suggested_values=len(to_check(plan)))
    return plan


def find_line(plan, line_id):
    for section in plan["sections"]:
        for line in section["lines"]:
            if line["id"] == line_id:
                return line
    raise KeyError(line_id)


def render_line(line, lang, plan, pharmacy=None):
    pharmacy = pharmacy or get_settings().branding.pharmacy_name
    text = line.get(lang) or line["en"]
    value = (line.get("value_fr") if lang == "fr" else "") or line.get("value") or BLANK
    protein = plan.get("protein_target") or BLANK
    return (text.replace("{blank}", value).replace("{protein_target}", protein)
            .replace("{pharmacy}", pharmacy))


def blanks_to_fill(plan):
    """Medical targets still empty (highlighted for the pharmacist)."""
    return [line for section in plan["sections"] for line in section["lines"]
            if line["included"] and "{blank}" in line["en"] and not line.get("value")]


def to_check(plan):
    """AI/rule-suggested values the pharmacist hasn't confirmed or changed yet (highlighted)."""
    return [line for section in plan["sections"] for line in section["lines"]
            if line["included"] and line.get("suggested") and not line.get("confirmed")]


def visible_lines(section):
    return [line for line in section["lines"] if line["included"]]


# ---- pharmacist edits (each one is logged with before/after and can be undone) ----

def set_value(record, line_id, value, who):
    line = find_line(record["care_plan"], line_id)
    record_edit(record, who, line_id, {"value": line["value"], "confirmed": line.get("confirmed", True),
                                       "value_fr": line.get("value_fr", "")},
                {"value": value, "confirmed": True, "value_fr": ""})
    line["value"], line["confirmed"], line["value_fr"] = value, True, ""
    _changed(record, who, "fill_target", line_id)


def confirm_value(record, line_id, who):
    """The pharmacist checked a suggested value and agrees with it."""
    line = find_line(record["care_plan"], line_id)
    record_edit(record, who, line_id, {"confirmed": False}, {"confirmed": True})   # undoable
    line["confirmed"] = True
    _changed(record, who, "confirm_value", line_id)


def edit_text(record, line_id, lang, text, who):
    line = find_line(record["care_plan"], line_id)
    record_edit(record, who, line_id, {lang: line[lang]}, {lang: text})
    line[lang] = text
    if lang == "fr":
        line["needs_review"] = False
    _changed(record, who, "edit_line", line_id)


def set_included(record, line_id, included, who):
    line = find_line(record["care_plan"], line_id)
    record_edit(record, who, line_id, {"included": line["included"]}, {"included": included})
    line["included"] = included
    _changed(record, who, "include_line" if included else "exclude_line", line_id)


def set_readiness(record, option_id, who, other=""):
    plan = record["care_plan"]
    record_edit(record, who, "readiness", {"readiness": plan.get("readiness")}, {"readiness": option_id})
    plan["readiness"], plan["readiness_other"] = option_id, other
    _changed(record, who, "set_readiness", "readiness")


def undo_last(record, who):
    """Undo the most recent edit. Returns the history entry that was undone, or None."""
    entry = last_undoable(record)
    if not entry:
        return None
    plan = record["care_plan"]
    if entry["line_id"] == "readiness":
        plan["readiness"] = entry["before"]["readiness"]
    elif entry["line_id"] in ("status", "suggestions"):
        return None
    else:
        find_line(plan, entry["line_id"]).update(copy.deepcopy(entry["before"]))
    entry["undone"] = True
    record_edit(record, who, entry["line_id"], entry["after"], entry["before"], action="undo")
    _changed(record, who, "undo", entry["line_id"])
    return entry


def approve(record, who):
    """Approve. Suggested values not yet checked are accepted as they are (and logged as such)."""
    plan = record["care_plan"]
    accepted = to_check(plan)
    for line in accepted:
        line["confirmed"] = True
    if accepted:
        record_edit(record, who, "suggestions", {"unchecked": [l["id"] for l in accepted]}, {"accepted": True},
                    action="accept_suggestions")
    plan.update(status="approved", approved_by=who, approved_at=now_iso())
    record_edit(record, who, "status", {"status": "draft"}, {"status": "approved"}, action="approve")
    audit_log.record("care_plan_approved", record["id"], by=who, blanks_left=len(blanks_to_fill(plan)))


def request_changes(record, who, note):
    plan = record["care_plan"]
    plan["status"] = "changes_requested"
    plan["change_requests"].append({"by": who, "time": now_iso(), "note": note})
    record_edit(record, who, "status", {"status": "draft"}, {"status": "changes_requested"}, action="request_changes")
    audit_log.record("care_plan_changes_requested", record["id"], by=who)


def _changed(record, who, action, line_id):
    plan = record["care_plan"]
    if plan["status"] == "approved":
        plan["status"] = "draft"  # an edited plan needs approving again
    audit_log.record("care_plan_edit", record["id"], by=who, action=action, line_id=line_id)


def to_text(record):
    """Plain-text export: English first, then French, like the PDF."""
    plan, template = record["care_plan"], load("care_plan_template")
    out = []
    for lang in ("en", "fr"):
        out.append(template["care_plan_title"][lang].upper())
        if plan["goals"]:
            out.append(template["goals_title"][lang])
            out += [f"  - {goal}" for goal in plan["goals"]]
        for section in plan["sections"]:
            out.append("")
            out.append(section[lang])
            out += [f"  - {render_line(line, lang, plan)}" for line in visible_lines(section)]
        if plan["barriers"]:
            out.append("")
            out.append(template["barriers_title"][lang])
            for item in plan["barriers"]:
                out.append(f"  - {item.get('barrier_' + lang, '')}: {item.get('plan_' + lang, '')}")
        out.append("\n")
    return "\n".join(out)
