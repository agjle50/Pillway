"""Builds, edits, approves and renders the care plan in Pillway's own format (EN first, then FR).

Called by: core/conversation_service.py (draft after the check-in), the patient Care plan tab
and the pharmacist care plan editor.
The structure comes from data/care_plan_template.json (copied from Pillway's PDF).
Medical targets (A1C, TIR, exercise target...) stay BLANK for the pharmacist. The AI only adds
personal lifestyle lines. The Medications section is never written by the AI.
"""

import copy

from config import get_settings

from ..storage import audit_log
from ..storage.edit_history import last_undoable, record_edit
from ..storage.patient_store import now_iso
from .content import load

BLANK = "_____"


def build_draft(record, lifestyle, source):
    """Make a new draft from the template + this patient's answers + the AI lifestyle lines."""
    template = load("care_plan_template")
    settings = get_settings()
    avoid_weight = record["bot_settings"].get("avoid_weight_talk")
    sections = []
    for section in template["sections"]:
        lines = []
        for line in section["lines"]:
            if avoid_weight and line["id"] == "ex_bmi":
                continue
            lines.append({"id": line["id"], "kind": line["kind"], "en": line["en"], "fr": line["fr"],
                          "value": "", "included": line["kind"] != "optional", "ai": False,
                          "needs_review": line.get("fr_source") != "pillway_pdf", "note": line.get("note", "")})
        if section["id"] == "medications":
            meds = record.get("medications", [])
            if meds:
                listed = "; ".join(f"{m['name']} {m.get('dose', '')} {m.get('frequency', '')}".strip() for m in meds)
                lines.insert(0, {"id": "med_list", "kind": "pharmacy_record", "en": f"Medications on file: {listed}.",
                                 "fr": f"Médicaments au dossier : {listed}.", "value": "", "included": True,
                                 "ai": False, "needs_review": True, "note": "From the pharmacy record, not the AI."})
        if section.get("ai_lifestyle"):
            for index, extra in enumerate((lifestyle.get("sections") or {}).get(section["id"], [])[:3]):
                lines.append({"id": f"{section['id']}_ai_{index}", "kind": "ai_lifestyle", "en": extra.get("en", ""),
                              "fr": extra.get("fr", ""), "value": "", "included": True, "ai": True,
                              "needs_review": True, "note": "Written by the AI from the patient's answers."})
        sections.append({"id": section["id"], "en": section["en"], "fr": section["fr"], "lines": lines})
    answers = record["conversation"]["answers"]
    goal = answers.get("goal", {}).get("text")
    review = settings.pharmacist.pharmacist_review_required
    plan = {
        "status": "draft" if review else "published_without_review",
        "created": now_iso(), "source": source, "review_required": review,
        "readiness": None, "readiness_other": "",
        "goals": [goal] if goal else [],
        "protein_target": record["profile"].get("protein_target", ""),
        "sections": sections,
        "barriers": lifestyle.get("barrier_plans", []),
        "approved_by": None, "approved_at": None, "change_requests": [],
    }
    audit_log.record("care_plan_drafted", record["id"], source=source, review_required=review)
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
    value = line.get("value") or BLANK
    protein = plan.get("protein_target") or BLANK
    return (text.replace("{blank}", value).replace("{protein_target}", protein)
            .replace("{pharmacy}", pharmacy))


def blanks_to_fill(plan):
    """Medical targets still empty (highlighted for the pharmacist)."""
    return [line for section in plan["sections"] for line in section["lines"]
            if line["included"] and "{blank}" in line["en"] and not line.get("value")]


def visible_lines(section):
    return [line for line in section["lines"] if line["included"]]


# ---- pharmacist edits (each one is logged with before/after and can be undone) ----

def set_value(record, line_id, value, who):
    line = find_line(record["care_plan"], line_id)
    record_edit(record, who, line_id, {"value": line["value"]}, {"value": value})
    line["value"] = value
    _changed(record, who, "fill_target", line_id)


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
    else:
        find_line(plan, entry["line_id"]).update(copy.deepcopy(entry["before"]))
    entry["undone"] = True
    record_edit(record, who, entry["line_id"], entry["after"], entry["before"], action="undo")
    _changed(record, who, "undo", entry["line_id"])
    return entry


def approve(record, who):
    plan = record["care_plan"]
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
