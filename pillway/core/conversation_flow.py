"""The check-in flow, one step at a time (patient steps 2 to 8). Pure logic, no UI, no AI.

Called by: core/conversation_service.py for each patient message.
It decides WHAT happens next (which question, which required sentences, whether to make
the care plan). The AI (or demo mode) only writes the friendly advice paragraph in between.
That keeps the important rules in code, where they can't be talked out of:
  * one question at a time, in the order of data/questions.json
  * the protein rule: ask about protein limits first, then compute 0.8-1.0 g/kg from weight
  * after the questions: "Is there anything else?" until the patient says no, then the care plan

Stages: consent -> greeting -> changes -> (changes_detail) -> questions -> wrap_up -> done
"""

from config import get_settings

from . import answer_parsing as parse
from .content import advice, load
from .patient_summary import detect_changes, intake_summary, side_effect_matches


def question_fits(record, question):
    """Does this question fit the patient's conditions? (Unknown conditions: every question fits.)"""
    from .intake import condition_flags
    diabetes, pressure, known = condition_flags(record)
    wanted = question.get("for")
    if not wanted or not known:
        return True
    return ("diabetes" in wanted and diabetes) or ("blood pressure" in wanted and pressure)


def question_list(record):
    """The questions for this patient, after skip rules, pharmacist choices and the max setting."""
    settings = get_settings()
    questions = [q for q in load("questions")["questions"] if not q.get("optional")]  # extras: AI only
    chosen = record["bot_settings"].get("question_ids")
    if chosen:
        by_id = {q["id"]: q for q in questions}
        questions = [by_id[qid] for qid in chosen if qid in by_id]
    profile = record["profile"]
    # Pillway's program: diabetes and/or high blood pressure. Only ask what fits this patient's
    # conditions (when nothing is known, everything is asked so nothing important is skipped).
    from .intake import condition_flags
    diabetes, _pressure, known = condition_flags(record)
    kept = [q for q in questions if question_fits(record, q)
            and not any(profile.get(key) == value for key, value in q.get("skip_if", {}).items())]
    limit = settings.patient.max_questions_per_check_in
    # goals and main concerns shape the care plan, so the question limit never drops them
    must_keep = ({"feet"} if record["bot_settings"].get("ask_feet_every_check_in") and (diabetes or not known)
                 else set()) | {"concerns", "goal"}
    trimmed = kept[:limit]
    ids = [q["id"] for q in trimmed]
    by_id = {q["id"]: q for q in kept}
    if "diet" in ids and "protein_limit" not in ids and "protein_limit" in by_id:
        trimmed.insert(ids.index("diet") + 1, by_id["protein_limit"])  # protein rule: never drop it after diet
    for q in kept[limit:]:
        if q["id"] in must_keep and q not in trimmed:
            trimmed.append(q)
    trimmed.sort(key=lambda q: [k["id"] for k in kept].index(q["id"]))
    return trimmed


def question_payload(record, index, lang):
    questions = question_list(record)
    if index >= len(questions):
        return None
    q = questions[index]
    return {"id": q["id"], "topic": q["topic"], "text": q.get(lang) or q["en"],
            "quick": q.get(f"quick_{lang}") or q.get("quick_en", []),
            "n": index + 1, "total": len(questions),
            "progress": advice("intake_bits.progress", lang, n=index + 1, total=len(questions))}


def _wrap_up_payload(lang):
    intro = load("questions")["intro"]
    return {"id": "wrap_up", "topic": "wrap up", "text": intro[f"wrap_up_{lang}"],
            "quick": intro[f"wrap_up_quick_{lang}"], "n": None, "total": None, "progress": ""}


def protein_targets(weight):
    return round(weight * 0.8), round(weight * 1.0)


def empty_plan(stage):
    return {"stage_before": stage, "stage_after": stage, "answer_to": None, "advice_key": None,
            "question_in_advice": False,
            "advice_values": {}, "required": [], "updates": [], "side_effects": [], "next_question": None,
            "handoff": None, "generate_care_plan": False, "ai_role": "advice", "answer_value": None}


def plan_turn(record, text):
    """Decide what Sarah does with this patient message. Returns a plan dict (see empty_plan)."""
    convo, lang = record["conversation"], record["language"]
    stage = convo["stage"]
    plan = empty_plan(stage)
    if stage in ("consent", "greeting"):
        plan.update(stage_after="changes", ai_role=None, advice_key="greeting")
        plan["required"].append(intake_summary(record, lang))
        intro = load("questions")["intro"]
        plan["next_question"] = {"id": "changes", "topic": "changes", "text": intro[f"changes_{lang}"],
                                 "quick": intro[f"changes_quick_{lang}"], "n": None, "total": None, "progress": ""}
        return plan
    if stage in ("changes", "changes_detail"):
        return _plan_changes(record, text, plan, lang)
    if stage == "questions":
        return _plan_question_answer(record, text, plan, lang)
    if stage == "wrap_up":
        if parse.yes_no_unsure(text) == "no":
            plan.update(stage_after="done", generate_care_plan=True, ai_role=None, advice_key="writing_care_plan")
        elif parse.yes_no_unsure(text) == "yes" and len(text.split()) <= 2:
            plan.update(ai_role=None, advice_key="anything_else_yes")
        else:
            plan.update(ai_role="free", advice_key="anything_else_more", next_question=_wrap_up_payload(lang))
        return plan
    plan.update(ai_role="free")
    return plan


def _plan_changes(record, text, plan, lang):
    answer = parse.yes_no_unsure(text)
    updates = detect_changes(text, record)
    plan["updates"] = updates
    plan["side_effects"] = side_effect_matches(text, record["medications"])
    if updates:
        plan.update(stage_after="questions", ai_role="changes", advice_key=None)
    elif answer == "no":
        plan.update(stage_after="questions", ai_role=None, advice_key="changes_none")
    elif answer == "yes" and plan["stage_before"] == "changes":
        plan.update(stage_after="changes_detail", ai_role=None, advice_key="changes_ask_detail")
        return plan
    elif plan["stage_before"] == "changes":
        plan.update(stage_after="changes_detail", ai_role="changes", advice_key="changes_unclear")
        return plan
    else:
        plan.update(stage_after="questions", ai_role="changes", advice_key="changes_none")
    record["conversation"]["question_index"] = 0
    plan["next_question"] = question_payload(record, 0, lang)
    return plan


def _plan_question_answer(record, text, plan, lang):
    convo = record["conversation"]
    index = convo["question_index"]
    current = question_payload(record, index, lang)
    if current is None:
        plan.update(stage_after="wrap_up", next_question=_wrap_up_payload(lang))
        return plan
    plan["answer_to"] = current["id"]
    handler = ANSWER_HANDLERS.get(current["id"], _generic_answer)
    stay = handler(record, text, plan, lang)
    if stay:
        if not plan.get("question_in_advice"):
            plan["next_question"] = plan["next_question"] or current
        return plan
    # protein rule: anyone asking about protein must first get the protein-limit question
    asked = set(convo["answers"]) | {current["id"]}
    if "protein" in text.lower() and "protein_limit" not in asked:
        ids = [q["id"] for q in question_list(record)]
        if "protein_limit" in ids:
            convo["question_index"] = ids.index("protein_limit")
            plan["next_question"] = question_payload(record, convo["question_index"], lang)
            return plan
    convo["question_index"] = index + 1
    nxt = question_payload(record, index + 1, lang)
    if nxt is None:
        plan.update(stage_after="wrap_up", next_question=_wrap_up_payload(lang))
    else:
        plan["next_question"] = nxt
    return plan


# ---- one small function per question (return True to stay on the same question) ----

def _answer_diet(record, text, plan, lang):
    bucket = parse.choose(text, {"unsure": ["not sure", "unsure", "don't know", "confused", "ne sais pas", "no idea"],
                                 "better": ["better", "improve", "mieux", "want to"],
                                 "well": ["well", "good", "fine", "pretty well", "bien"]}) or "unsure"
    plan.update(advice_key=f"diet.{bucket}", answer_value=bucket)


def _answer_protein(record, text, plan, lang):
    if record["conversation"].pop("awaiting_weight", False) and parse.weight_kg(text):
        record["profile"]["weight_kg"] = parse.weight_kg(text)
        text = "no"
    answer = parse.yes_no_unsure(text) or "unsure"
    plan["answer_value"] = answer
    if answer == "yes":
        plan.update(advice_key="protein.limited", handoff="Doctor has asked patient to limit protein: please set protein target.")
        return False
    if answer == "unsure":
        plan.update(advice_key="protein.unsure", handoff="Patient unsure whether protein should be limited: please check.")
        return False
    weight = record["profile"].get("weight_kg")
    if not weight:
        plan.update(advice_key="protein.no_weight", question_in_advice=True)
        record["conversation"]["awaiting_weight"] = True
        return True
    low, high = protein_targets(weight)
    plan.update(advice_key="protein.target", advice_values={"weight": round(weight), "low": low, "high": high})
    record["profile"]["protein_target"] = f"{low}-{high}"
    return False


def _answer_feet(record, text, plan, lang):
    bucket = parse.choose(text, {"dont_check": ["don't check", "dont check", "never check", "ne les vérifie pas"],
                                 "fine": ["fine", "look fine", "good", "ok", "okay", "nothing", "no", "vont bien", "rien"]})
    plan.update(advice_key=f"feet.{bucket or 'noticed'}", answer_value=bucket or text)
    if bucket is None and parse.choose(text, {"vague": ["i noticed something", "j'ai remarqué quelque chose"]}):
        plan["question_in_advice"] = True  # the advice text itself asks "what did you notice?"
        return True
    return False


def _answer_blood_sugar(record, text, plan, lang):
    reading = parse.sugar_reading(text)
    if reading:
        when = parse.time_mentioned(text)
        plan.update(advice_key="blood_sugar.reading", answer_value=reading,
                    advice_values={"reading": reading, "when": f" ({when})" if when else ""})
    else:
        plan.update(advice_key="blood_sugar.none", answer_value="no reading")


def _answer_blood_pressure(record, text, plan, lang):
    reading = parse.bp_reading(text)
    if reading:
        when = parse.time_mentioned(text)
        plan.update(advice_key="blood_pressure.reading", answer_value=reading,
                    advice_values={"reading": reading, "when": f" ({when})" if when else ""})
        record["profile"]["last_bp"] = reading
    else:
        plan.update(advice_key="blood_pressure.none", answer_value="no reading")


def _answer_activity(record, text, plan, lang):
    bucket = parse.activity_bucket(text)
    plan.update(advice_key=f"activity.{bucket}", answer_value=text.strip())


def _answer_alcohol(record, text, plan, lang):
    plan.update(advice_key=f"alcohol.{parse.alcohol_bucket(text)}", answer_value=text.strip())


def _answer_smoking(record, text, plan, lang):
    bucket = parse.choose(text, {"ready": ["ready", "prêt", "prête"], "thinking": ["thinking", "j'y pense"]}) or "not_thinking"
    plan.update(advice_key=f"smoking.{bucket}", answer_value=bucket)
    record["profile"]["quit_readiness"] = bucket
    if bucket == "ready":
        plan["handoff"] = "Patient is ready to quit smoking: please help make a plan."


def _answer_barriers(record, text, plan, lang):
    bucket = parse.choose(text, {"time": ["time", "temps", "busy"], "cost": ["cost", "money", "coût", "expensive"],
                                 "motivation": ["motivation", "motivated"], "pain": ["pain", "tired", "douleur", "fatigue"]})
    plan.update(advice_key=f"barriers.{bucket or 'other'}", answer_value=text.strip())


def _answer_concerns(record, text, plan, lang):
    plan.update(advice_key="concerns.any", answer_value=text.strip())


def _answer_goal(record, text, plan, lang):
    plan.update(advice_key="goal.any", answer_value=text.strip())


def _generic_answer(record, text, plan, lang):
    plan.update(advice_key=None, answer_value=text.strip())


ANSWER_HANDLERS = {"diet": _answer_diet, "protein_limit": _answer_protein, "feet": _answer_feet,
                   "blood_sugar": _answer_blood_sugar, "blood_pressure": _answer_blood_pressure,
                   "activity": _answer_activity, "alcohol": _answer_alcohol, "smoking": _answer_smoking,
                   "barriers": _answer_barriers, "concerns": _answer_concerns, "goal": _answer_goal}


def go_back(record):
    """Let the patient change their previous answer: step back one question."""
    convo = record["conversation"]
    if convo["stage"] == "wrap_up":
        convo["stage"] = "questions"
        convo["question_index"] = len(question_list(record)) - 1
    elif convo["stage"] == "questions" and convo["question_index"] > 0:
        convo["question_index"] -= 1
    return question_payload(record, convo["question_index"], record["language"])
