"""Assembles Sarah's final reply text from the flow plan, the AI/demo paragraph and safety needs.

Called by: core/conversation_service.py.
Order of a normal reply: what I updated -> side-effect note -> advice paragraph ->
"you may have..., because..." -> flag note -> exactly ONE question.
Sentences that matter for safety are added here by code, so the AI can't leave them out.
"""

from .content import advice
from .output_guard import SAFE_FALLBACK, check_reply
from .patient_summary import describe_updates


def task_for_ai(plan, text, record):
    """The instruction for the AI's paragraph this turn (it never writes the next question)."""
    lang = "French (Canada)" if record["language"] == "fr" else "English"
    role, answer_to = plan.get("ai_role"), plan.get("answer_to")
    computed = plan.get("advice_values") or {}
    if role == "changes":
        return (f"Step 3. The patient was asked if anything changed since their questionnaire. Decide what is valid, "
                f"relevant health information and list it in summary_updates. Write 1-2 warm sentences acknowledging it. "
                f"The app will separately list the updates and any side-effect note. Language: {lang}.")
    if role == "free":
        return (f"The patient is chatting outside the question list. Answer helpfully in 2-4 sentences, personal to them. "
                f"If it is a medication question, set medication_question true. Language: {lang}.")
    return (f"The patient just answered the question '{answer_to}'. Give short, personal, evidence-based advice "
            f"(Diabetes Canada / Hypertension Canada style) about that answer in 2-4 sentences. Do not ask a question. "
            f"Facts computed by the app that you must use exactly: {computed}. Language: {lang}.")


def build(record, plan, ai_result, flag_decision=None, ask_specifics=False):
    """Return (reply_text, possible_issue_statements, problems_found_by_guard)."""
    lang = record["language"]
    parts, problems = [], []
    if plan["stage_before"] in ("consent", "greeting"):
        parts.append(advice("greeting", lang, first_name=record["profile"].get("first_name", ""),
                            assistant=_assistant(), pharmacy=_pharmacy()))
        parts += plan["required"]
    updates = plan.get("updates") or []
    if updates:
        parts.append(advice("updated_intro", lang) + "\n" + describe_updates(updates, lang))
    for match in plan.get("side_effects", []):
        parts.append(advice("side_effect", lang, symptom_cap=match["symptom"].capitalize(), medication=match["medication"]))
    if any(u["type"] == "medication" for u in updates):
        parts.append(advice("new_medication_noted", lang))
    paragraph = (ai_result or {}).get("advice", "").strip()
    if paragraph:
        problems = check_reply(paragraph, lang, allow_short=True)
        parts.append(paragraph if not problems else SAFE_FALLBACK[lang])
    elif plan.get("advice_key") and plan["advice_key"] != "greeting":
        parts.append(advice(plan["advice_key"], lang, **_values(record, plan)))
    statements = []
    side_effect_said = bool(plan.get("side_effects"))
    for issue in (ai_result or {}).get("possible_issues", [])[:2]:
        statement = advice("possible_issue", lang, issue=issue["issue"], reason=issue["reason"])
        statements.append({"issue": issue["issue"], "reason": issue["reason"], "statement": statement})
        if not (side_effect_said and "side effect" in issue["issue"]):  # already said above; still saved
            parts.append(statement)
    if (ai_result or {}).get("medication_question"):
        parts.append(advice("medication_question", lang))
    if flag_decision and flag_decision.get("final_tier") == 2 and not side_effect_said:
        parts.append(advice("tier2_suffix", lang))
        if ask_specifics and flag_decision.get("ask_next"):
            parts.append(flag_decision["ask_next"])
            return _join(parts), statements, problems
    question = plan.get("next_question")
    if question and not plan.get("question_in_advice"):
        parts.append(question["text"])
    return _join(parts), statements, problems


def build_tier1(record, flag_decision, possible_issues=()):
    """The urgent reply: thank, ask for specifics, say a pharmacist will contact them, 911 line."""
    lang = record["language"]
    parts = [advice("tier1_intro", lang)]
    statements = []
    for issue in list(possible_issues)[:1]:
        statement = advice("possible_issue", lang, issue=issue["issue"], reason=issue["reason"])
        statements.append({"issue": issue["issue"], "reason": issue["reason"], "statement": statement})
        parts.append(statement)
    if flag_decision.get("ask_next"):
        parts.append(flag_decision["ask_next"])
    parts.append(advice("tier1_suffix", lang))
    return _join(parts), statements


def _join(parts):
    return "\n\n".join(part.strip() for part in parts if part and part.strip())


def _values(record, plan):
    values = dict(plan.get("advice_values") or {})
    values.setdefault("first_name", record["profile"].get("first_name", ""))
    return values


def _assistant():
    from config import get_settings
    return get_settings().branding.assistant_name


def _pharmacy():
    from config import get_settings
    return get_settings().branding.pharmacy_name
