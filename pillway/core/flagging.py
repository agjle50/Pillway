"""Combines LAYER 1 (hard rules) and LAYER 2 (AI context) into one flag decision.

Called by: core/conversation_service.py for every patient chat message and call sentence.
The rules that protect patients live here:
  * A Tier 1 from layer 1 can never be removed or downgraded by the AI.
  * The AI may ADD a flag or RAISE its tier ("I can't feel my toes").
  * The AI may only clear a match that layer 1 itself marked "needs AI check"
    (a negated phrase like "my foot doesn't hurt").
  * If the AI is unavailable, layer 1 still shows its flag with "AI context unavailable".
Every decision is written to the audit log.
"""

from datetime import datetime, timedelta

from ..storage import audit_log
from ..storage.patient_store import new_id, now_iso

AI_OK, AI_UNAVAILABLE, AI_DISABLED = "ok", "unavailable", "disabled"


def decide(layer1, layer2, ai_status):
    """Return the final decision dict. layer2 is a validated dict or None."""
    base = layer1.tier if layer1.tier in (1, 2) else None
    final = base
    ai_says_concern = bool(layer2 and layer2.get("is_concern") and layer2.get("tier") in (1, 2))
    if ai_says_concern:
        final = min(final or 9, layer2["tier"])
    if base is None and layer1.needs_ai_check and not ai_says_concern:
        if ai_status != AI_OK or layer2 is None:
            final = 2  # never fail silently: let the pharmacist look
    reason = _reason(layer1, layer2, ai_status, final)
    ask_next = layer1.ask_next if base == 1 else ((layer2 or {}).get("ask_next") or layer1.ask_next)
    return {
        "final_tier": final,
        "colour": {1: "red", 2: "amber"}.get(final),
        "reason": reason,
        "ask_next": ask_next,
        "ai_status": ai_status,
        "matched_words": layer1.matched_words,
        "readings": [r for r in layer1.readings if r.get("tier")],
        "context_topics": sorted({m.topic for m in layer1.matches if m.tier == 3 and not m.negated}),
    }


def _reason(layer1, layer2, ai_status, final):
    if layer2 and layer2.get("reason"):
        return layer2["reason"]
    parts = []
    if layer1.matched_words:
        parts.append("Matched: " + ", ".join(layer1.matched_words[:4]))
    for reading in layer1.readings:
        if reading.get("tier"):
            parts.append(f"{reading['kind']} reading {reading['value']} is past the safety threshold")
    if final and not parts and layer1.needs_ai_check:
        parts.append("A danger word was used with 'no/not'; please check the wording")
    note = {AI_UNAVAILABLE: " (AI context unavailable)", AI_DISABLED: " (AI check turned off)"}.get(ai_status, "")
    return ("; ".join(parts) or "Flagged by safety rules") + note


def _primary_topic(layer1, layer2):
    live = sorted((m for m in layer1.matches if not m.negated and m.tier in (1, 2)), key=lambda m: m.tier)
    if live:
        return live[0].topic
    if any(r.get("tier") for r in layer1.readings):
        return next(r["kind"] for r in layer1.readings if r.get("tier"))
    return (layer2 or {}).get("topic") or "concern noted by AI"


def apply_flag(record, message, decision, layer1, layer2, source="chat"):
    """Add (or group into) a flag on the patient record. Returns the flag dict or None."""
    if not decision["final_tier"]:
        _audit(record["id"], message, decision, layer1, layer2, None)
        return None
    topic = _primary_topic(layer1, layer2)
    cutoff = datetime.now().astimezone() - timedelta(hours=24)
    for flag in record["flags"]:
        if flag["status"] == "open" and flag["topic"] == topic and datetime.fromisoformat(flag["time"]) > cutoff:
            flag["occurrences"].append({"message_id": message["id"], "text": message["text"], "time": message["time"]})
            flag["tier"] = min(flag["tier"], decision["final_tier"])
            flag["updated"] = now_iso()
            _audit(record["id"], message, decision, layer1, layer2, flag["id"], grouped=True)
            return flag
    context = [m["text"] for m in record["messages"][-4:-1]]
    flag = {
        "id": new_id("flag"), "message_id": message["id"], "time": message["time"], "updated": now_iso(),
        "text": message["text"], "context": context, "topic": topic, "tier": decision["final_tier"],
        "matched_words": decision["matched_words"], "readings": decision["readings"],
        "ai_reason": decision["reason"], "ai_status": decision["ai_status"], "ask_next": decision["ask_next"],
        "source": source, "status": "open", "resolved_by": None, "resolved_at": None,
        "notes": [], "feedback": None, "occurrences": [],
        "layer1_tier": layer1.tier, "layer2": layer2,
    }
    record["flags"].append(flag)
    _audit(record["id"], message, decision, layer1, layer2, flag["id"])
    return flag


def upgrade_with_layer2(record, flag_id, layer1, layer2, ai_status):
    """Layer 2 arrived later: re-decide and update the existing card (can only add/raise)."""
    decision = decide(layer1, layer2, ai_status)
    for flag in record["flags"]:
        if flag["id"] == flag_id:
            flag["tier"] = min(flag["tier"], decision["final_tier"] or flag["tier"])
            flag["ai_reason"], flag["ai_status"], flag["layer2"] = decision["reason"], ai_status, layer2
            return flag
    return None


def open_flags(record):
    return [flag for flag in record.get("flags", []) if flag["status"] == "open"]


def _audit(patient_id, message, decision, layer1, layer2, flag_id, grouped=False):
    audit_log.record(
        "flag_decision", patient_id, message_id=message["id"], flag_id=flag_id, grouped=grouped,
        layer1_tier=layer1.tier, layer1_words=layer1.matched_words, needs_ai_check=layer1.needs_ai_check,
        layer2=layer2, ai_status=decision["ai_status"], final_tier=decision["final_tier"],
    )
