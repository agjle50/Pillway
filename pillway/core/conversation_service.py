"""The front door for every patient message (chat or call). Used from a background thread.

Called by: ui/patient/chat_actions.py and ui/patient/call.py (through a worker thread),
and by the tests and the stage-script runner.
What happens to one message:
  1. it is SAVED immediately (data never disappears)
  2. LAYER 1 safety runs instantly; an alert becomes a flag on the pharmacist dashboard at once
  3. Tier 1: Sarah's urgent reply is written by code right away (no waiting for the AI)
  4. otherwise LAYER 2 (AI flag check) and Sarah's paragraph run, the output guard checks it,
     and the reply is assembled with exactly one next question
  5. layer 2 updates the flag card when it arrives; every decision goes to the audit log
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from datetime import datetime

from config import get_settings

from ..ai.brain import Brain
from ..storage import audit_log
from ..storage.patient_store import PatientStore, new_id, now_iso
from . import answer_parsing as parse
from . import care_plan as care_plan_logic
from . import flagging, intake, reply_builder, tasks
from .content import advice
from .conversation_flow import (ANSWER_HANDLERS, _generic_answer, empty_plan, go_back, plan_turn,
                                protein_targets, question_list, question_payload)
from .output_guard import check_reply
from .patient_summary import detect_changes

MEMORY_EVERY_N_TURNS = 3   # refresh Sarah's compact memory every 3rd patient message


def load_questions_intro():
    from .content import load
    return load("questions")["intro"]
from .safety_rules import check_message


class ConversationService:
    def __init__(self, store=None, brain=None):
        self.store = store or PatientStore()
        self.brain = brain or Brain()
        self.busy = set()           # patient ids Sarah is currently "typing" for
        self._turns_since_memory = {}   # patient id -> messages since Sarah's memory was refreshed
        self.timings = []

    # ---- simple actions -------------------------------------------------------

    def accept_consent(self, patient_id, accepted=True):
        def change(record):
            record["consent"] = {"accepted": accepted, "time": now_iso(), "version": 1}
            if accepted and record["conversation"]["stage"] == "consent":
                record["conversation"]["stage"] = "greeting"
        record = self.store.update(patient_id, change)
        audit_log.record("consent", patient_id, accepted=accepted)
        return record

    def submit_intake(self, patient_id, form, lang="en"):
        """Save the first-visit questionnaire and build the health profile.

        Returns (record, errors). If errors is not empty nothing was saved (show them on the form).
        """
        from .. import debug_log
        clean, errors = intake.validate(form, lang)
        if errors:
            debug_log.log("intake", "questionnaire has problems", fields=",".join(sorted(errors)))
            return self.store.load(patient_id), errors
        record = self.store.update(patient_id, lambda r: intake.apply(r, clean))
        audit_log.record("intake_questionnaire", patient_id, shared_weight=clean.get("shared_weight"))
        profile = record["health_profile"]
        debug_log.log("intake", "questionnaire saved", patient=patient_id,
                      answered=",".join(k for k in clean if k != "shared_weight"))
        debug_log.log("profile", "health profile built (rules)",
                      areas=[a["area"] for a in profile["areas_to_explore"]] or "none",
                      not_shared=len(profile["not_shared"]))
        return record, {}

    def refine_health_profile(self, patient_id):
        """Ask the AI for extra areas to explore (live AI only). Safe to run in the background."""
        record = self.store.load(patient_id)
        suggestions = self.brain.suggest_health_areas(record)
        if suggestions:
            record = self.store.update(patient_id, lambda r: intake.merge_ai_suggestions(r, suggestions))
        return record

    def set_language(self, patient_id, lang):
        return self.store.update(patient_id, lambda r: r.update(language=lang))

    def request_pharmacist(self, patient_id, reason="Patient pressed 'Talk to a pharmacist'"):
        def change(record):
            open_requests = [r for r in record["pharmacist_requests"] if r["status"] == "open"]
            if not open_requests:  # no duplicates
                record["pharmacist_requests"].append({"id": new_id("req"), "time": now_iso(), "reason": reason,
                                                      "status": "open"})
            self._add_sarah(record, advice("pharmacist_request", record["language"]), source="code")
        audit_log.record("pharmacist_request", patient_id, reason=reason)
        return self.store.update(patient_id, change)

    def back_one_question(self, patient_id):
        def change(record):
            question = go_back(record)
            if question:
                self._add_sarah(record, question["text"], quick=question["quick"], progress=question["progress"],
                                source="code")
        return self.store.update(patient_id, change)

    def start_session(self, patient_id, kind="CHAT"):
        session = {"id": new_id("ses"), "kind": kind, "start": now_iso(), "end": None, "duration_s": None}

        def change(record):
            previous = self._previous_interaction(record)
            for existing in record["sessions"]:
                if existing.get("end") is None:
                    existing["end"] = session["start"]
            if previous:
                session["previous_interaction"] = previous
            record["sessions"].append(session)
            record["conversation"]["session_id"] = session["id"]
            if record["consent"]["accepted"] and previous:
                record["conversation"]["stage"] = "done"
                if not record["conversation"].get("pending_flag_followup"):
                    self._add_sarah(
                        record, self._returning_greeting(record, previous),
                        source="code", channel="call" if kind.upper() == "CALL" else "chat",
                    )
        self.store.update(patient_id, change)
        return session["id"]

    def end_session(self, patient_id, session_id, duration_s=None):
        def change(record):
            for session in record["sessions"]:
                if session["id"] == session_id:
                    session["end"], session["duration_s"] = now_iso(), duration_s
            if record["conversation"].get("session_id") == session_id:
                record["conversation"]["session_id"] = None
        return self.store.update(patient_id, change)

    @staticmethod
    def _previous_interaction(record):
        messages_by_session = {}
        for message in record.get("messages", []):
            session_id = message.get("session_id")
            if session_id:
                messages_by_session.setdefault(session_id, []).append(message)
        for session in reversed(record.get("sessions", [])):
            messages = messages_by_session.get(session["id"], [])
            patient_messages = [message for message in messages if message.get("role") == "patient"]
            if not patient_messages:
                continue
            topic_message = next(
                (message for message in reversed(patient_messages)
                 if len(message.get("text", "").split()) >= 3),
                patient_messages[-1],
            )
            contact_time = session.get("end") or patient_messages[-1].get("time") or session.get("start")
            flagged = [flag.get("topic", "") for flag in record.get("flags", [])
                       if flag.get("session_id") == session["id"] and flag.get("topic")]
            return {
                "session_id": session["id"],
                "kind": session.get("kind", "CHAT"),
                "at": contact_time,
                "topic": " ".join(topic_message.get("text", "").split())[:180],
                "flag_topic": flagged[-1] if flagged else "",   # a clean topic name, safe to say aloud
            }
        return None

    @staticmethod
    def _returning_greeting(record, previous):
        first_name = record.get("profile", {}).get("first_name") or ""
        is_french = record.get("language") == "fr"
        kind = (
            "un appel" if previous.get("kind") == "CALL" else "un clavardage"
        ) if is_french else (
            "a phone call" if previous.get("kind") == "CALL" else "a chat"
        )
        timestamp = previous.get("at", "")
        try:
            last_contact = datetime.fromisoformat(timestamp)
            now = datetime.now().astimezone()
            if last_contact.tzinfo is None:
                last_contact = last_contact.astimezone()
            days_ago = (now.date() - last_contact.astimezone(now.tzinfo).date()).days
            if is_french:
                months = (
                    "janvier", "février", "mars", "avril", "mai", "juin",
                    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
                )
                when = "aujourd'hui" if days_ago == 0 else "hier" if days_ago == 1 else (
                    f"il y a {days_ago} jours" if 1 < days_ago < 7 else
                    f"le {last_contact.day} {months[last_contact.month - 1]}"
                )
            else:
                when = "earlier today" if days_ago == 0 else "yesterday" if days_ago == 1 else (
                    f"{days_ago} days ago" if 1 < days_ago < 7 else
                    "on " + last_contact.strftime("%b %d").replace(" 0", " ")
                )
        except (TypeError, ValueError):
            when = "récemment" if is_french else "recently"
        # Sound like a person who remembers the gist, not a machine replaying a transcript:
        # never quote the patient's last words (speech-to-text mistakes would be read back).
        topic = previous.get("flag_topic", "").strip()
        if is_french:
            about = f", au sujet de : {topic}" if topic else ""
            return (f"Bonjour {first_name}, contente de vous retrouver! On s'est parlé {when}{about}. "
                    "Voulez-vous un petit résumé, reprendre là où on s'était laissées, ou parler d'un nouveau sujet? "
                    "Pas besoin de vous souvenir de tout, on peut repartir à zéro.")
        about = f", about {topic}" if topic else ""
        return (f"Hi {first_name}, welcome back! We last talked {when}{about}. "
                "Would you like a quick recap, pick up where we left off, or talk about something new? "
                "You don't need to remember what we talked about, we can start fresh.")

    # ---- the main entry point --------------------------------------------------

    def handle_message(self, patient_id, text, channel="chat", on_update=None):
        """Process one patient message. Blocking (call it from a worker thread)."""
        text = (text or "").strip()
        if not text:
            return None
        started = time.monotonic()
        self.busy.add(patient_id)
        try:
            return self._handle(patient_id, text, channel, on_update or (lambda: None), started)
        finally:
            self.busy.discard(patient_id)
            self._turns_since_memory[patient_id] = self._turns_since_memory.get(patient_id, MEMORY_EVERY_N_TURNS - 1) + 1
            if (self.brain.live and get_settings().ai.conversation_style == "natural"
                    and self._turns_since_memory[patient_id] >= MEMORY_EVERY_N_TURNS):
                # update Sarah's memory in the background, without making the patient wait.
                # Only every few messages: the free Gemini tier allows few requests per minute.
                self._turns_since_memory[patient_id] = 0
                threading.Thread(target=self._safe_refresh_memory, args=(patient_id,), daemon=True).start()
            self.timings.append(round(time.monotonic() - started, 2))
            if get_settings().dev.dev_mode:
                print(f"[timing] reply for {patient_id} in {self.timings[-1]}s")

    def _handle(self, patient_id, text, channel, on_update, started):
        record = self.store.load(patient_id)
        layer1 = check_message(text, extra_words=record.get("custom_flag_words", []))
        quick_decision = flagging.decide(layer1, None, "pending") if layer1.is_alert else None
        message_id = new_id("msg")

        def save_patient(record):
            message = {"id": message_id, "role": "patient", "text": text, "time": now_iso(), "channel": channel,
                       "session_id": record["conversation"].get("session_id"), "tier": None, "flag_id": None}
            record["messages"].append(message)
            record["last_patient_activity"] = message["time"]
            if quick_decision and quick_decision["final_tier"]:
                quick_decision["ai_status"] = "pending"
                flag = flagging.apply_flag(record, message, quick_decision, layer1, None, source=channel)
                message.update(tier=flag["tier"], flag_id=flag["id"])
        record = self.store.update(patient_id, save_patient)
        on_update()

        if layer1.tier == 1:  # urgent always wins, even inside an injection attempt
            return self._urgent_turn(patient_id, text, layer1, message_id, quick_decision, channel, on_update)
        if parse.is_injection_attempt(text) or (parse.is_medication_question(text)
                                                and record["conversation"]["stage"] not in ("consent", "greeting")):
            return self._handoff_turn(patient_id, text, message_id, channel, injection=parse.is_injection_attempt(text))
        return self._normal_turn(patient_id, text, layer1, message_id, channel, on_update)

    # ---- the three kinds of turn ------------------------------------------------

    def _urgent_turn(self, patient_id, text, layer1, message_id, decision, channel, on_update):
        record = self.store.load(patient_id)
        demo_issues = self.brain.demo.reply(record, {"ai_role": None, "advice_key": None, "side_effects": []},
                                            text, layer1)["possible_issues"]

        def change(record):
            convo = record["conversation"]
            previous = convo.get("pending_flag_followup")
            resume = previous["resume"] if previous else None
            if convo["stage"] in ("questions", "changes", "changes_detail", "wrap_up") and not previous:
                plan = plan_turn(record, text)
                self._remember_answer(record, plan, text)
                self._apply_summary_updates(record, plan)
                convo["stage"] = plan["stage_after"]
                resume = plan["next_question"]
            reply, statements = reply_builder.build_tier1(record, decision, demo_issues)
            flag_id = next(m["flag_id"] for m in record["messages"] if m["id"] == message_id)
            convo["pending_flag_followup"] = {"flag_id": flag_id, "resume": resume}
            self._save_issues(record, statements, message_id)
            self._add_sarah(record, reply, tier=1, source="code", channel=channel)
        self.store.update(patient_id, change)
        on_update()
        layer2, status = self.brain.flag_check(self.store.load(patient_id), text, layer1)

        def upgrade(record):
            flag_id = next(m["flag_id"] for m in record["messages"] if m["id"] == message_id)
            flagging.upgrade_with_layer2(record, flag_id, layer1, layer2, status if status != "disabled" else "disabled")
        self.store.update(patient_id, upgrade)
        on_update()
        return self.store.load(patient_id)

    def _handoff_turn(self, patient_id, text, message_id, channel, injection):
        def change(record):
            lang = record["language"]
            parts = []
            if injection:
                parts.append({"en": "I'm Pillway's automated assistant, so I can't change my rules or act as a doctor or pharmacist.",
                              "fr": "Je suis l'assistante automatisée de Pillway; je ne peux pas changer mes règles ni agir comme médecin ou pharmacien."}[lang])
                audit_log.record("prompt_injection_blocked", patient_id, message_id=message_id)
            if parse.is_medication_question(text) or not injection:
                parts.append(advice("medication_question", lang))
                record["pharmacist_requests"].append({"id": new_id("req"), "time": now_iso(), "status": "open",
                                                      "reason": "Medication question: " + text[:140]})
            question = self._current_question(record)
            if question:
                parts.append(question["text"])
            self._add_sarah(record, "\n\n".join(parts), quick=(question or {}).get("quick"),
                            progress=(question or {}).get("progress", ""), source="code", channel=channel)
        return self.store.update(patient_id, change)

    def _normal_turn(self, patient_id, text, layer1, message_id, channel, on_update):
        record = self.store.load(patient_id)
        convo = record["conversation"]
        if convo.get("pending_flag_followup"):
            return self._flag_followup_turn(patient_id, text, message_id, channel, on_update)
        if self._natural_mode(record):
            return self._natural_turn(patient_id, text, layer1, message_id, channel, on_update)
        return self._scripted_turn(patient_id, text, layer1, message_id, channel, on_update)

    # ---- natural conversation (the AI writes the whole reply) ---------------------

    def _natural_mode(self, record):
        return (get_settings().ai.conversation_style == "natural" and self.brain.live
                and record["conversation"]["stage"] not in ("consent", "greeting"))

    def _checklist(self, record):
        """What this conversation should achieve, as gentle guidance for the AI (not a script).

        First consultation (replaces the pharmacist's ~30-minute call): the remaining check-in
        questions, adapting to each answer. After the care plan: a monthly follow-up on ONE
        topic (data/follow_up_topics.json), like the pharmacist's 10-15 minute calls.
        """
        convo, lang = record["conversation"], record["language"]
        profile = record["profile"]
        # Only answers the patient actually gave in the questionnaire count (never demo/seed values).
        done = intake.is_done(record)
        questionnaire = {key: profile[key] for key in intake.QUESTIONNAIRE_KEYS
                         if done and profile.get(key) not in (None, "")}
        base = {"off_topic_turns": convo.get("off_topic_turns", 0),
                "questionnaire_done": done,
                "already_in_questionnaire": questionnaire}
        if convo["stage"] == "done":
            topic = self._follow_up_topic(record)
            if topic:
                answers = record.get("follow_up", {}).get("answers", {})
                remaining = [{"id": q["id"], "about": topic["title_en"], "example_question": q["en"]}
                             for q in topic["questions"] if q["id"] not in answers]
                return {**base, "session_type": "monthly follow-up call (10-15 minutes, ONE topic only)",
                        "topic": {k: topic[k] for k in ("id", "title_en", "goal", "facts", "source")},
                        "remaining": remaining, "suggested_next": remaining[0]["id"] if remaining else "anything_else",
                        "already_answered": answers}
            return {**base, "session_type": "check-in (all monthly topics done)", "remaining": [],
                    "suggested_next": "anything_else", "already_answered": {}}
        intro = load_questions_intro()
        remaining = []
        if convo["stage"] in ("changes", "changes_detail"):
            remaining.append({"id": "changes", "about": "anything new since their questionnaire",
                              "example_question": intro[f"changes_{lang}"]})
        for question in question_list(record):
            if question["id"] not in convo["answers"]:
                remaining.append({"id": question["id"], "about": question["topic"],
                                  "example_question": question.get(lang) or question["en"]})
        from .content import load
        extras = [{"id": q["id"], "about": q["topic"], "example_question": q.get(lang) or q["en"]}
                  for q in load("questions")["questions"] if q.get("optional") and q["id"] not in convo["answers"]]
        return {**base, "session_type": "first consultation (in place of the pharmacist's 30-minute call)",
                "stage": convo["stage"], "remaining": remaining,
                "optional_if_time_allows": extras,
                "suggested_next": remaining[0]["id"] if remaining else "anything_else",
                "already_answered": {qid: a.get("value") for qid, a in convo["answers"].items()}}

    @staticmethod
    def _follow_up_topic(record):
        """This month's follow-up topic: the current one, or the next one not done yet."""
        from .content import load
        state = record.setdefault("follow_up", {"done": [], "current": None, "answers": {}})
        topics = load("follow_up_topics")["topics"]
        by_id = {topic["id"]: topic for topic in topics}
        if state.get("current") in by_id:
            return by_id[state["current"]]
        done = {item["id"] for item in state.get("done", [])}
        for topic in topics:
            skip = any(record["profile"].get(key) == value for key, value in topic.get("skip_if", {}).items())
            if topic["id"] not in done and not skip:
                state["current"], state["answers"] = topic["id"], {}
                return topic
        return None

    @staticmethod
    def _facts(record):
        """Numbers the app computed; the AI must use them exactly."""
        facts = {}
        if not intake.is_done(record):     # demo/seed numbers are never presented as the patient's
            return facts
        weight = record["profile"].get("weight_kg")
        if weight:
            low, high = protein_targets(weight)
            facts["protein_target_grams_per_day"] = f"{low} to {high} (0.8 to 1.0 g per kg; only after protein_limit is answered 'no')"
        if record["profile"].get("last_bp"):
            facts["last_blood_pressure"] = record["profile"]["last_bp"]
        return facts

    def _natural_turn(self, patient_id, text, layer1, message_id, channel, on_update):
        record = self.store.load(patient_id)
        with ThreadPoolExecutor(max_workers=2) as pool:
            flag_job = pool.submit(self.brain.flag_check, record, text, layer1)
            talk_job = pool.submit(self.brain.converse, record, text, channel, self._checklist(record),
                                   self._facts(record))
            layer2, flag_status = flag_job.result()
            talk, status = talk_job.result()
        lang = record["language"]
        if status != "ok" or not (talk or {}).get("reply") or check_reply(talk["reply"], lang, allow_short=True):
            if talk and talk.get("reply"):
                audit_log.record("output_guard_blocked", patient_id, problems=check_reply(talk["reply"], lang, True),
                                 source="ai")
            return self._scripted_turn(patient_id, text, layer1, message_id, channel, on_update)

        # The AI's best reading of a speech-to-text message gets the same word-list safety check.
        heard = talk.get("heard_as") or text
        if heard.strip().lower() != text.strip().lower():
            second = check_message(heard, extra_words=record.get("custom_flag_words", []))
            if second.is_alert and (not layer1.is_alert or (second.tier or 9) < (layer1.tier or 9)):
                layer1 = second
                if layer1.tier == 1:
                    quick = flagging.decide(layer1, None, "pending")

                    def flag_now(record):
                        message = next(m for m in record["messages"] if m["id"] == message_id)
                        message["heard_as"] = heard
                        if not message.get("flag_id"):
                            quick["ai_status"] = "pending"
                            flag = flagging.apply_flag(record, message, quick, layer1, None, source=channel)
                            message.update(tier=flag["tier"], flag_id=flag["id"])
                    self.store.update(patient_id, flag_now)
                    return self._urgent_turn(patient_id, heard, layer1, message_id, quick, channel, on_update)
        decision = flagging.decide(layer1, layer2, flag_status)
        wants_care_plan = [False]

        def change(record):
            convo, lang = record["conversation"], record["language"]
            message = next(m for m in record["messages"] if m["id"] == message_id)
            if heard != text:
                message["heard_as"] = heard
            flag = None
            if decision["final_tier"]:
                if message.get("flag_id"):
                    flag = flagging.upgrade_with_layer2(record, message["flag_id"], layer1, layer2, flag_status)
                else:
                    flag = flagging.apply_flag(record, message, decision, layer1, layer2, source=channel)
                message.update(tier=flag["tier"], flag_id=flag["id"])
            else:
                flagging.apply_flag(record, message, decision, layer1, layer2, source=channel)  # audit only
            if flag and flag["tier"] == 1:  # the AI safety check found something urgent
                reply, statements = reply_builder.build_tier1(record, decision, talk.get("possible_issues", []))
                convo["pending_flag_followup"] = {"flag_id": flag["id"], "resume": None}
                self._save_issues(record, statements, message_id)
                self._add_sarah(record, reply, tier=1, source="code", channel=channel)
                return

            convo["off_topic_turns"] = convo.get("off_topic_turns", 0) + 1 if talk.get("small_talk") else 0
            if convo["stage"] == "done":
                self._record_follow_up(record, talk, heard)
            from .content import load as load_content
            optional = {q["id"] for q in load_content("questions")["questions"] if q.get("optional")}
            known = ({q["id"] for q in question_list(record)} | optional) if convo["stage"] != "done" else set()
            for item in talk.get("answered", []):
                qid, value = item["id"].strip(), (item.get("value") or heard).strip()
                if qid == "changes" and convo["stage"] in ("changes", "changes_detail"):
                    for update in detect_changes(heard, record):
                        talk.setdefault("summary_updates", []).append(update)
                    convo["stage"] = "questions"
                elif qid in known and qid not in convo["answers"]:
                    plan = empty_plan("questions")
                    plan["answer_to"] = qid
                    if ANSWER_HANDLERS.get(qid, _generic_answer)(record, value, plan, lang):
                        continue  # e.g. protein needs their weight first: still open
                    convo["answers"][qid] = {"value": plan.get("answer_value") or value, "text": heard,
                                             "time": now_iso()}
                    if plan.get("handoff"):
                        record["pharmacist_requests"].append({"id": new_id("req"), "time": now_iso(),
                                                              "status": "open", "reason": plan["handoff"]})
            seen = {u["text"].lower() for u in record["summary_updates"]}
            for update in talk.get("summary_updates", []):
                line = f"{update['type'].title()}: {update['value']}"
                if line.lower() not in seen:
                    record["summary_updates"].append({"time": now_iso(), "type": update["type"], "text": line})
                    seen.add(line.lower())
            if convo["stage"] in ("changes", "changes_detail") and talk.get("asking") in known:
                convo["stage"] = "questions"  # they've moved on to the check-in questions
            questions = question_list(record)
            remaining = [q for q in questions if q["id"] not in convo["answers"]]
            if convo["stage"] == "questions":
                if remaining:
                    convo["question_index"] = questions.index(remaining[0])
                else:
                    convo["stage"] = "wrap_up"
            if talk.get("finished") and not remaining and convo["stage"] in ("questions", "wrap_up"):
                convo["stage"] = "done"
                wants_care_plan[0] = True

            reply = talk["reply"]
            if talk.get("medication_question"):
                record["pharmacist_requests"].append({"id": new_id("req"), "time": now_iso(), "status": "open",
                                                      "reason": "Medication question: " + heard[:140]})
                line = advice("medication_question", lang)
                if line.split(",")[0].lower() not in reply.lower():
                    reply += " " + line
            if flag and flag["tier"] == 2:  # always tell them the pharmacist will see it
                reply += "\n\n" + advice("tier2_suffix", lang)
            statements = [{"issue": i["issue"], "reason": i["reason"],
                           "statement": advice("possible_issue", lang, issue=i["issue"], reason=i["reason"])}
                          for i in talk.get("possible_issues", [])[:2]]
            self._save_issues(record, statements, message_id)
            asking = talk.get("asking")
            index = next((n for n, q in enumerate(questions) if q["id"] == asking), None)
            payload = question_payload(record, index, lang) if index is not None else None
            self._add_sarah(record, reply, quick=(payload or {}).get("quick"),
                            progress=(payload or {}).get("progress", ""), source="ai",
                            tier=decision["final_tier"], channel=channel)
        self.store.update(patient_id, change)
        on_update()
        if wants_care_plan[0]:
            self.make_care_plan(patient_id, channel)
            on_update()
        return self.store.load(patient_id)

    def _record_follow_up(self, record, talk, heard):
        """Save this month's follow-up answers; when the topic is covered, log it for the pharmacist."""
        topic = self._follow_up_topic(record)
        if not topic:
            return
        state = record["follow_up"]
        ids = {q["id"] for q in topic["questions"]}
        for item in talk.get("answered", []):
            if item["id"] in ids:
                state["answers"][item["id"]] = (item.get("value") or heard).strip()
        if talk.get("finished") or ids <= set(state["answers"]):
            summary = "; ".join(f"{qid.replace('_', ' ')}: {value}" for qid, value in state["answers"].items())
            record["summary_updates"].append({"time": now_iso(), "type": "lifestyle",
                                              "text": f"Follow-up ({topic['title_en']}): {summary or 'discussed'}"})
            state["done"].append({"id": topic["id"], "time": now_iso(), "answers": dict(state["answers"])})
            state["current"], state["answers"] = None, {}

    # ---- memory: a compact note Sarah reads before every reply --------------------

    def refresh_memory(self, patient_id):
        """Fold the latest exchange into the patient's compact memory (runs in the background)."""
        record = self.store.load(patient_id)
        messages = record["messages"]
        last_patient = max((n for n, m in enumerate(messages) if m["role"] == "patient"), default=None)
        if last_patient is None:
            return
        exchange = [("Patient", messages[last_patient].get("heard_as") or messages[last_patient]["text"])]
        exchange += [("Assistant", m["text"]) for m in messages[last_patient + 1:] if m["role"] == "sarah"]
        text = self.brain.update_memory(record, exchange)
        if text:
            def save(record):
                record["memory"] = {"text": text, "updated": now_iso()}
            self.store.update(patient_id, save)

    # ---- the original scripted turn (fixed question order) ------------------------

    def _scripted_turn(self, patient_id, text, layer1, message_id, channel, on_update):
        record = self.store.load(patient_id)
        plan = plan_turn(record, text)  # works on a copy; re-applied inside update() below
        task = reply_builder.task_for_ai(plan, text, record)
        with ThreadPoolExecutor(max_workers=2) as pool:
            flag_job = pool.submit(self.brain.flag_check, record, text, layer1)
            reply_job = pool.submit(self.brain.reply, record, plan, text, task, layer1)
            layer2, flag_status = flag_job.result()
            ai_result, source = reply_job.result()
        decision = flagging.decide(layer1, layer2, flag_status)

        def change(record):
            plan = plan_turn(record, text)
            self._merge_ai_updates(plan, ai_result)
            message = next(m for m in record["messages"] if m["id"] == message_id)
            flag = None
            if decision["final_tier"]:
                if message.get("flag_id"):
                    flag = flagging.upgrade_with_layer2(record, message["flag_id"], layer1, layer2, flag_status)
                else:
                    flag = flagging.apply_flag(record, message, decision, layer1, layer2, source=channel)
                message.update(tier=flag["tier"], flag_id=flag["id"])
            else:
                flagging.apply_flag(record, message, decision, layer1, layer2, source=channel)  # audit only
            ask_specifics = bool(flag and flag["tier"] == 2 and plan["stage_before"] == "questions")
            if ask_specifics or (flag and flag["tier"] == 1):
                record["conversation"]["pending_flag_followup"] = {"flag_id": flag["id"], "resume": plan["next_question"]}
            if flag and flag["tier"] == 1:  # the AI found something urgent the word list missed
                reply, statements = reply_builder.build_tier1(record, decision, ai_result.get("possible_issues", []))
                problems, ask_specifics = [], True
            else:
                reply, statements, problems = reply_builder.build(record, plan, ai_result, decision if flag else None,
                                                                  ask_specifics)
            if problems:
                audit_log.record("output_guard_blocked", record["id"], problems=problems, source=source)
                record["pharmacist_requests"].append({"id": new_id("req"), "time": now_iso(), "status": "open",
                                                      "reason": "Sarah could not answer safely; please follow up."})
            if ai_result.get("medication_question") or plan.get("handoff"):
                record["pharmacist_requests"].append({"id": new_id("req"), "time": now_iso(), "status": "open",
                                                      "reason": plan.get("handoff") or "Medication question: " + text[:140]})
            self._remember_answer(record, plan, text)
            self._apply_summary_updates(record, plan)
            self._save_issues(record, statements, message_id)
            record["conversation"]["stage"] = plan["stage_after"]
            question = None if ask_specifics else plan.get("next_question")
            self._add_sarah(record, reply, quick=(question or {}).get("quick"), progress=(question or {}).get("progress", ""),
                            source=source, tier=decision["final_tier"], channel=channel)
            wants_care_plan[0] = plan.get("generate_care_plan", False)
        wants_care_plan = [False]
        self.store.update(patient_id, change)
        on_update()
        if wants_care_plan[0]:
            self.make_care_plan(patient_id, channel)
            on_update()
        return self.store.load(patient_id)

    def _flag_followup_turn(self, patient_id, text, message_id, channel, on_update):
        def change(record):
            convo = record["conversation"]
            pending = convo.pop("pending_flag_followup")
            tier = 2
            for flag in record["flags"]:
                if flag["id"] == pending["flag_id"]:
                    flag.setdefault("details", []).append({"text": text, "time": now_iso(), "message_id": message_id})
                    tier = flag["tier"]
            lang = record["language"]
            thanks = advice("flag_followup_thanks", lang) if tier == 1 else advice("anything_else_more", lang)
            question = pending.get("resume") or self._current_question(record)
            parts = [thanks] + ([question["text"]] if question else [])
            self._add_sarah(record, "\n\n".join(parts), quick=(question or {}).get("quick"),
                            progress=(question or {}).get("progress", ""), source="code", channel=channel)
        record = self.store.update(patient_id, change)
        on_update()
        return record

    def _safe_refresh_memory(self, patient_id):
        try:
            self.refresh_memory(patient_id)
        except Exception as error:  # memory is a nice-to-have; never break the chat
            print(f"[memory] {type(error).__name__}: {error}")

    # ---- care plan ----------------------------------------------------------------

    def make_care_plan(self, patient_id, channel="chat"):
        self.busy.add(patient_id)
        try:
            lifestyle, source = self.brain.care_plan_lifestyle(self.store.load(patient_id))

            def change(record):
                record["care_plan"] = care_plan_logic.build_draft(record, lifestyle, source)
                record["care_plan_history"] = []
                record["tasks"] = tasks.merge(record.get("tasks", []), tasks.generate(record))
                self._add_sarah(record, advice("care_plan_ready", record["language"],
                                               first_name=record["profile"].get("first_name", "")), source="code",
                                channel=channel)
            return self.store.update(patient_id, change)
        finally:
            self.busy.discard(patient_id)

    # ---- helpers ------------------------------------------------------------------

    def _current_question(self, record):
        convo = record["conversation"]
        if convo["stage"] == "questions":
            return question_payload(record, convo["question_index"], record["language"])
        return None

    def _remember_answer(self, record, plan, text):
        if plan.get("answer_to"):
            record["conversation"]["answers"][plan["answer_to"]] = {"value": plan.get("answer_value"), "text": text,
                                                                    "time": now_iso()}

    def _merge_ai_updates(self, plan, ai_result):
        seen = {(u["type"], u["value"].lower()) for u in plan["updates"]}
        for update in (ai_result or {}).get("summary_updates", []):
            if plan["stage_before"] in ("changes", "changes_detail") and (update["type"], update["value"].lower()) not in seen:
                plan["updates"].append(update)
                seen.add((update["type"], update["value"].lower()))

    def _apply_summary_updates(self, record, plan):
        for update in plan.get("updates", []):
            record["summary_updates"].append({"time": now_iso(), "type": update["type"],
                                              "text": f"{update['type'].title()}: {update['value']}"})

    def _save_issues(self, record, statements, message_id):
        for item in statements:
            record["possible_issues"].append({"id": new_id("iss"), "time": now_iso(), "message_id": message_id, **item})

    def _add_sarah(self, record, text, quick=None, progress="", source="code", tier=None, channel="chat"):
        record["messages"].append({"id": new_id("msg"), "role": "sarah", "text": text, "time": now_iso(),
                                   "channel": channel, "session_id": record["conversation"].get("session_id"),
                                   "quick": quick or [], "progress": progress, "source": source,
                                   "lang": record["language"], "about_tier": tier})
