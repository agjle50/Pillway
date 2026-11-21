"""Friendly scripted triage based on adjustable care-plan keyword rules."""

from datetime import datetime
import re

from .medical_guidance import (
    ACUTE_CRISIS_KEYWORDS,
    DIABETES_RISK_FACTORS,
    EMERGENCY_SIGNS,
    GREETINGS,
    HYPERGLYCEMIA_FOLLOW_UPS,
    HYPERGLYCEMIA_SYMPTOMS,
    MEDICAL_KEYWORDS,
    REDIRECT_RESPONSES,
    RISK_FOLLOW_UPS,
    SYMPTOM_KEYWORDS,
    WELLNESS_REPLIES,
)


class MedicalRobot:
    def __init__(self):
        self.known_conditions = ("diabetes", "hypertension")
        self.assessment_stage = "awaiting_change_status"
        self.last_topic = None
        self.topic_turns = {}
        self.off_topic_turn = 0
        self.urgent_turn = 0
        self.screening_turn = 0
        self.risk_turn = 0
        self.blood_pressure_followup_turn = 0

    def greeting(self, now=None):
        hour = (now or datetime.now()).hour
        if 5 <= hour < 12:
            salutation = "Good morning"
        elif 12 <= hour < 18:
            salutation = "Good afternoon"
        else:
            salutation = "Good evening"
        self.assessment_stage = "awaiting_change_status"
        conditions = " and ".join(self.known_conditions)
        return (
            f"{salutation}! I'm Juliez, Pillway's automated virtual assistant. "
            f"I understand you've completed the short assessment and have {conditions}. "
            "Has anything changed since then, or is there anything new you'd like to tell me?"
        )

    def reply(self, message):
        original_message = message.strip()
        text = " ".join(original_message.lower().split())
        if not text:
            return "I'm here with you. What would you like help with today?"

        acute_signs = self._matched_rules(text, ACUTE_CRISIS_KEYWORDS)
        if acute_signs:
            self.last_topic = None
            self.assessment_stage = "complete"
            return self._urgent_response(acute_signs)

        if self._matches_keywords(text, EMERGENCY_SIGNS):
            self.last_topic = None
            self.assessment_stage = "complete"
            return self._urgent_response([])

        symptoms = self._matched_rules(text, HYPERGLYCEMIA_SYMPTOMS)
        if symptoms:
            assessment_change = self._is_assessment_pending()
            response = self._hyperglycemia_response(text, symptoms)
            return self._assessment_result(original_message, response) if assessment_change else response

        risk_factors = self._matched_rules(text, DIABETES_RISK_FACTORS)
        if self._mentions_age_40_plus(text):
            risk_factors.append({"topic": "age 40 or older"})

        if self._is_greeting(text):
            return "Hi! I'm here with you. How are you feeling, or what health concern can I help with?"

        if (
            self.last_topic == "blood pressure"
            and (not self._is_question(text) or self._is_blood_pressure_feeling_high(text))
            and self._is_blood_pressure_follow_up(text)
            and not any(
                branch["topic"] != "blood pressure"
                and self._matches_keywords(text, branch["keywords"])
                for branch in MEDICAL_KEYWORDS
            )
        ):
            reading = re.search(r"\b\d{2,3}\s*/\s*\d{2,3}\b", text)
            if reading:
                return self._numeric_follow_up(reading.group())
            return self._blood_pressure_follow_up(text)

        assessment_change = False
        if self.assessment_stage == "awaiting_change_status":
            change_status = self._assessment_status(text)
            if change_status == "no":
                self.assessment_stage = "complete"
                self.last_topic = None
                return (
                    "Check-in summary: your short assessment notes diabetes and hypertension, and "
                    "you report no new changes. How are you feeling today? If you'd like, share a "
                    "blood-pressure or glucose reading."
                )
            if change_status == "yes":
                self.assessment_stage = "awaiting_change_detail"
                self.last_topic = "assessment changes"
                return (
                    "Thanks for letting me know. What has changed since your short assessment? "
                    "You can mention symptoms, a blood-pressure or glucose reading, medication, or "
                    "anything else."
                )
            if self._is_vague_message(text):
                return "Prompt Claude"
            if self._is_related_health_message(text, risk_factors):
                assessment_change = not self._is_question(text)
                self.assessment_stage = "complete"
        elif self.assessment_stage == "awaiting_change_detail":
            if self._is_vague_message(text):
                return "Prompt Claude"
            if self._is_related_health_message(text, risk_factors):
                assessment_change = not self._is_question(text)
                self.assessment_stage = "complete"
            else:
                self.assessment_stage = "complete"
                self.last_topic = None
                return self._assessment_summary(original_message)

        blood_pressure_reading = re.search(r"\b\d{2,3}\s*/\s*\d{2,3}\b", text)
        if blood_pressure_reading and self._matches_keywords(
            text, ("blood pressure", "hypertension", "systolic", "diastolic", "bp")
        ):
            self.last_topic = "blood pressure"
            response = self._numeric_follow_up(blood_pressure_reading.group())
            return (
                self._assessment_result(original_message, response)
                if assessment_change else response
            )

        explicit_glucose_topic = self._matches_keywords(
            text, ("blood sugar", "glucose", "a1c", "insulin", "hypoglyc", "hyperglyc")
        )
        if risk_factors and self._matches_keywords(text, ("diabetes",)) and not explicit_glucose_topic:
            self.last_topic = "diabetes screening"
            response = self._risk_response(risk_factors)
            return self._assessment_result(original_message, response) if assessment_change else response

        for branch in MEDICAL_KEYWORDS:
            if self._matches_keywords(text, branch["keywords"]):
                response = self._topic_reply(text, branch)
                if risk_factors and branch["topic"] not in ("blood pressure", "cholesterol"):
                    response += " " + self._risk_context(risk_factors)
                return (
                    self._assessment_result(original_message, response)
                    if assessment_change else response
                )

        if risk_factors:
            self.last_topic = "diabetes screening"
            response = self._risk_response(risk_factors)
            return self._assessment_result(original_message, response) if assessment_change else response

        if self.last_topic:
            if self.last_topic == "blood pressure":
                reading = re.search(r"\b\d{2,3}\s*/\s*\d{2,3}\b", text)
                if reading:
                    return self._numeric_follow_up(reading.group())
                return self._blood_pressure_follow_up(text)
            elif self.last_topic.startswith("blood sugar"):
                reading = re.search(r"\b\d{2,4}(?:\.\d+)?\b", text)
                if reading:
                    return self._numeric_follow_up(reading.group())
            if re.fullmatch(r"[\d./\s]+", text):
                return self._numeric_follow_up(text)
            if text in ("yes", "no", "a little", "not really", "i'm not sure", "im not sure"):
                return self._short_follow_up(text)
            if any(word in text for word in ("worried", "scared", "anxious", "concerned")):
                return self._short_follow_up("a little")

        wellness_key = self._wellness_key(text)
        if wellness_key:
            if self.last_topic:
                return f"I'm glad to hear that. Are you still concerned about your {self.last_topic}?"
            return WELLNESS_REPLIES[wellness_key]

        if self._matches_keywords(text, SYMPTOM_KEYWORDS):
            self.last_topic = None
            response = (
                "I'm sorry you're feeling unwell. I can't diagnose symptoms. If they're severe, sudden, "
                "getting worse, or you feel unsafe, seek urgent medical help. Otherwise, contact your "
                "doctor or pharmacist and tell them when this started, how it feels, and any medicines "
                "you take. What symptom is bothering you most?"
            )
            return (
                self._assessment_result(original_message, response)
                if assessment_change else response
            )

        if assessment_change:
            return self._assessment_summary(original_message)
        self.last_topic = None
        if self._is_vague_message(text):
            return "Prompt Claude"
        response = REDIRECT_RESPONSES[self.off_topic_turn % len(REDIRECT_RESPONSES)]
        self.off_topic_turn += 1
        return response

    def has_alert_keyword(self, message):
        text = " ".join(message.lower().split())
        return bool(
            self._matched_rules(text, ACUTE_CRISIS_KEYWORDS)
            or self._matches_keywords(text, EMERGENCY_SIGNS)
            or self._matched_rules(text, HYPERGLYCEMIA_SYMPTOMS)
            or self._matched_rules(text, DIABETES_RISK_FACTORS)
            or self._mentions_age_40_plus(text)
            or self._matches_keywords(
                text, ("diabetes", "hypertension", "blood pressure", "blood sugar", "glucose", "bp")
            )
        )

    def _is_assessment_pending(self):
        return self.assessment_stage in ("awaiting_change_status", "awaiting_change_detail")

    def _assessment_result(self, message, response):
        self.assessment_stage = "complete"
        return (
            f"Thanks for sharing that change: {message}. I'll consider it alongside your known "
            f"{' and '.join(self.known_conditions)}. "
            f"{response}"
        )

    def _assessment_summary(self, message):
        return (
            f"Check-in summary: your short-assessment history includes "
            f"{' and '.join(self.known_conditions)}. "
            f"You reported this change: {message}. This is a chat summary, not a diagnosis or "
            "medical-record update. Is there a blood-pressure or glucose reading you'd like to add?"
        )

    @staticmethod
    def _assessment_status(text):
        normalized = text.strip(" .,!?:;")
        if normalized in {
            "no", "no changes", "no change", "nothing new", "nothing changed",
            "nothing has changed", "same", "same as before", "about the same",
            "everything is the same", "unchanged", "not really", "no, not really",
            "no, nothing new", "no, nothing has changed", "no changes, thanks",
            "nothing to report", "same as usual", "all the same", "nope",
        } or MedicalRobot._wellness_key(normalized) in {"good", "fine", "okay", "great", "well"}:
            return "no"
        if normalized in {
            "yes", "yeah", "yep", "something changed", "something is different",
            "there is a change", "there's a change", "i have a change",
            "a few things changed", "some things changed", "yes, something changed",
            "yes, there is", "i noticed a change", "i noticed something different",
            "something new", "there's something new", "things are different",
            "i feel different", "yes, different",
        }:
            return "yes"
        return None

    @staticmethod
    def _is_vague_message(text):
        return text.strip(" .,!?:;") in {
            "recent", "recently", "maybe", "not sure", "i'm not sure", "im not sure",
            "i don't know", "i dont know", "idk", "something", "it changed",
            "same", "okay", "fine", "yes", "no", "sure", "i'm worried", "im worried",
            "worried", "concerned",
        }

    @staticmethod
    def _is_blood_pressure_follow_up(text):
        return MedicalRobot._matches_keywords(
            text,
            (
                "blood pressure", "bp", "recent", "recently", "today", "yesterday",
                "cuff", "reading", "checked", "measured", "feel", "feeling", "high",
                "low", "worried", "dizzy", "dizziness", "headache", "fine", "okay",
                "yes", "no", "not sure", "maybe",
            ),
        )

    @staticmethod
    def _is_blood_pressure_feeling_high(text):
        return MedicalRobot._matches_keywords(
            text,
            (
                "feel like my blood pressure is high", "feel like my bp is high",
                "think my blood pressure is high", "think my bp is high",
                "feel like it's high", "think it's high",
            ),
        )

    @staticmethod
    def _is_question(text):
        return text.endswith("?") or bool(re.match(
            r"^(?:what|why|how|can i|could i|should i|is it|do i|when)\b",
            text,
        ))

    @staticmethod
    def _is_related_health_message(text, risk_factors):
        if risk_factors or MedicalRobot._matches_keywords(text, SYMPTOM_KEYWORDS):
            return True
        if MedicalRobot._matches_keywords(text, EMERGENCY_SIGNS):
            return True
        if any(MedicalRobot._matches_keywords(text, branch["keywords"]) for branch in MEDICAL_KEYWORDS):
            return True
        return bool(
            re.search(r"\b\d{2,3}\s*/\s*\d{2,3}\b", text)
            or re.search(r"\b(?:blood glucose|glucose)\s*(?:is|of|:)?\s*\d{2,4}\b", text)
        )

    def _urgent_response(self, signs):
        self.urgent_turn += 1
        if signs:
            details = ", ".join(rule["topic"] for rule in signs[:3])
            opening = f"You mentioned {details}. "
        elif self.urgent_turn % 2:
            opening = "I'm concerned by the symptoms you described. "
        else:
            opening = "Those symptoms need urgent attention. "
        return (
            opening
            + "They can be warning signs of a serious blood-sugar emergency. Please seek emergency "
            "medical help now. If there is deep or gasping breathing, confusion, fainting, severe "
            "dehydration, or difficulty waking, call your local emergency number now. Don't drive "
            "yourself if you feel faint or drowsy. I can't diagnose or treat this in chat."
        )

    def _hyperglycemia_response(self, text, symptoms):
        topics = list(dict.fromkeys(rule["topic"] for rule in symptoms))
        self.last_topic = "blood sugar screening"
        opener = self._acknowledgement(text)
        follow_up = HYPERGLYCEMIA_FOLLOW_UPS[
            self.screening_turn % len(HYPERGLYCEMIA_FOLLOW_UPS)
        ]
        self.screening_turn += 1
        listed = ", ".join(topics[:4])
        if len(topics) > 4:
            listed += f", and {len(topics) - 4} more symptoms"
        return (
            f"{opener} You mentioned {listed}. These symptoms can happen with high blood sugar, "
            "but they can also have other causes and don't diagnose diabetes. Please contact a "
            "healthcare professional to discuss assessment or glucose testing. Follow your personal "
            "care plan, and don't change medication doses based on this chat. "
            f"{follow_up}"
        )

    def _risk_response(self, risk_factors):
        self.risk_turn += 1
        topics = list(dict.fromkeys(rule["topic"] for rule in risk_factors))
        listed = ", ".join(topics[:3])
        if len(topics) > 3:
            listed += f", and {len(topics) - 3} other factor(s)"
        medication_note = ""
        if "medication history" in topics:
            medication_note = (
                " Don't stop or change any medicine on this basis; ask the prescriber whether "
                "monitoring is appropriate."
            )
        background_note = ""
        if "background associated with higher population risk" in topics:
            background_note = (
                " Population-level patterns don't determine an individual's health; your own "
                "circumstances matter."
            )
        follow_up = RISK_FOLLOW_UPS[(self.risk_turn - 1) % len(RISK_FOLLOW_UPS)]
        self.last_topic = "diabetes screening"
        return (
            f"Thanks for sharing that. You mentioned {listed}. These can be relevant when a clinician "
            "assesses type 2 diabetes risk, but they don't mean you have diabetes. A healthcare "
            "professional can decide whether glucose or A1C screening is appropriate."
            f"{medication_note}{background_note} {follow_up}"
        )

    def _risk_context(self, risk_factors):
        topics = list(dict.fromkeys(rule["topic"] for rule in risk_factors))
        listed = ", ".join(topics[:3])
        return (
            f"You also mentioned {listed}. Those factors may be relevant to a clinician's diabetes "
            "risk assessment, but they don't diagnose diabetes."
        )

    def _topic_reply(self, text, branch):
        topic = branch["topic"]
        turn = self.topic_turns.get(topic, 0)
        self.topic_turns[topic] = turn + 1
        self.last_topic = topic
        opener = self._acknowledgement(text)
        follow_up = branch["follow_ups"][turn % len(branch["follow_ups"])]
        return f"{opener} {branch['response']} {follow_up}"

    def _numeric_follow_up(self, reading):
        topic = self.last_topic
        if topic == "blood pressure":
            return (
                f"Thanks for sharing that reading ({reading}). One reading alone doesn't tell the full "
                "story. Compare it with the target your care team gave you and contact them if readings "
                "are repeatedly above that target. Are you having any symptoms?"
            )
        if topic and topic.startswith("blood sugar"):
            return (
                f"Thanks for sharing that reading ({reading}). Compare it with your personal target and "
                "follow your clinician's plan for readings outside range. Don't change insulin or other "
                "doses based on this chat. How are you feeling right now?"
            )
        return (
            "Thanks for sharing the number. I can't interpret it without the test and your personal "
            "target; please review it with your pharmacist or prescriber. What does the reading refer to?"
        )

    def _blood_pressure_follow_up(self, text):
        self.blood_pressure_followup_turn += 1
        if self._matches_keywords(text, (
            "not recently", "not recent", "not lately", "haven't checked", "have not checked",
            "didn't check", "do not have a cuff", "don't have a cuff", "dont have a cuff",
            "no cuff", "no recent reading", "not today", "no",
        )):
            return (
                "That's okay—please don't guess a number. Blood pressure can be high without "
                "noticeable symptoms, so feeling fine can't rule it out. If you have access to a "
                "cuff later, follow its instructions and share the reading."
            )

        if self._matches_keywords(text, (
            "recent", "recently", "today", "this morning", "yesterday", "checked it",
            "checked my bp", "checked my blood pressure", "took a reading", "measured it",
            "used my cuff",
        )):
            if self.blood_pressure_followup_turn % 2:
                return (
                    "Thanks—when you say it was recent, do you have the top and bottom numbers? "
                    "Please share the reading if available; if you haven't measured it, don't guess."
                )
            return (
                "Got it. What numbers did the cuff show, and when did you take the reading? "
                "If you only meant that you checked recently but don't have the numbers, that's okay."
            )

        if self._matches_keywords(text, (
            "feel like my blood pressure is high", "feel like my bp is high",
            "think my blood pressure is high", "think my bp is high",
            "feel like it's high", "think it's high",
            "my blood pressure feels high", "my bp feels high", "feel my pressure is high",
        )):
            return (
                "I hear that you're concerned it may be high. What are you feeling that makes you "
                "think that? Symptoms alone can't reliably tell blood pressure; a cuff reading is "
                "the way to check. If you have one, please take a reading according to its instructions."
            )

        if self._matches_keywords(text, ("blood pressure", "bp", "high", "low")):
            return (
                "I hear you're concerned about the reading. Are you having any symptoms, or do you "
                "just feel it may be high? Feeling alone can't reliably tell; if you have a cuff, "
                "please check it and share the numbers."
            )

        if self._matches_keywords(text, ("dizzy", "dizziness", "headache", "blurry vision")):
            return (
                "I'm sorry you're feeling that. Sit somewhere safe and avoid driving while dizzy. "
                "These symptoms can have many causes; if you can safely check with a cuff, share the "
                "reading. Seek urgent help for severe or sudden symptoms."
            )

        if self._wellness_key(text) in {"good", "fine", "okay", "great", "well"}:
            return (
                "I'm glad you're feeling okay. Blood pressure can be high without symptoms, so if "
                "you're concerned, use a cuff rather than relying on how you feel. Do you have one "
                "available to take a reading?"
            )

        if text in ("yes", "yeah", "yep"):
            return "Do you have the reading? Share the top and bottom numbers if you can."
        if self._is_vague_message(text):
            return "Prompt Claude"
        return (
            "Could you share either a blood-pressure reading or what you're feeling right now? "
            "A cuff is needed to know the number; symptoms alone aren't a reliable measure."
        )

    def _short_follow_up(self, text):
        if text == "a little":
            return (
                f"Thanks for explaining. What feels most concerning about your {self.last_topic}, "
                "and when did you first notice it?"
            )
        if text == "yes":
            return (
                f"Okay. Is it your {self.last_topic} reading, a symptom, or something else that's "
                "concerning you?"
            )
        if text == "no":
            return f"Thanks for clarifying. What would you like to know about your {self.last_topic}?"
        return (
            f"That's okay. Could you tell me a little more about your {self.last_topic}, such as a "
            "recent reading, symptom, or what changed?"
        )

    @staticmethod
    def _acknowledgement(text):
        if any(word in text for word in ("worried", "scared", "anxious", "concerned")):
            return "I hear that this is worrying you."
        if any(word in text for word in ("hurt", "hurts", "pain", "side effect", "unwell")):
            return "I'm sorry you're dealing with that."
        if any(word in text for word in ("high", "low", "reading", "result")):
            return "Thanks for sharing that with me."
        return "Thanks for letting me know."

    @staticmethod
    def _matches_keywords(text, keywords):
        return any(MedicalRobot._contains_phrase(text, keyword) for keyword in keywords)

    @staticmethod
    def _matched_rules(text, rules):
        matches = []
        for rule in rules:
            if rule["topic"] == "background associated with higher population risk":
                found = any(
                    MedicalRobot._demographic_keyword_matches(text, keyword)
                    for keyword in rule["keywords"]
                )
            else:
                found = MedicalRobot._matches_keywords(text, rule["keywords"])
            if not found:
                continue
            requirements = rule.get("requires_any", ())
            if requirements and not MedicalRobot._matches_keywords(text, requirements):
                continue
            matches.append(rule)
        return matches

    @staticmethod
    def _demographic_keyword_matches(text, keyword):
        if keyword in {"asian", "african", "black", "arab", "hispanic", "latino"}:
            if text.strip() == keyword:
                return True
            context = (
                r"\b(?:i am|i'm|im|i identify as|identify as|my background is|"
                r"my ethnicity is|my heritage is)\s+(?:a |an )?"
            )
            descriptor = r"\b" + re.escape(keyword) + r"\s+(?:person|american|background|heritage)\b"
            return bool(
                re.search(context + re.escape(keyword) + r"\b", text)
                or re.search(descriptor, text)
            )
        return MedicalRobot._contains_phrase(text, keyword)

    @staticmethod
    def _contains_phrase(text, phrase):
        for match in re.finditer(rf"(?<!\w){re.escape(phrase)}(?!\w)", text):
            prefix = text[max(0, match.start() - 48):match.start()]
            if re.search(
                r"\b(?:no|not|never|without|denies|don't|dont|do not)\s+"
                r"(?:(?:have|having|had|experiencing|feeling|feel|felt|any|a|an|the|longer|"
                r"history|of|symptoms|diagnosed|with|currently|take|taking|use|using|on)\s+){0,3}$",
                prefix,
            ):
                continue
            return True
        return False

    @staticmethod
    def _has_emergency_sign(text):
        return MedicalRobot._matches_keywords(text.lower(), EMERGENCY_SIGNS)

    @staticmethod
    def _mentions_age_40_plus(text):
        if MedicalRobot._matches_keywords(text, (
            "over 40", "40s", "50s", "60s", "70s",
        )):
            return True
        age_match = re.search(
            r"\b(?:i am|i'm|im|age|aged)\s+(\d{2,3})\b|"
            r"\b(\d{2,3})\s*(?:years old|year old|yo|y/o)\b",
            text,
        )
        if not age_match:
            return False
        age = int(age_match.group(1) or age_match.group(2))
        return age >= 40

    @staticmethod
    def _is_greeting(text):
        greeting_text = text.strip("!.,?")
        if greeting_text in GREETINGS:
            return True
        return bool(re.fullmatch(
            r"(?:hello|hi|hey|howdy|yo)(?: juliez| there)?",
            greeting_text,
        ))

    @staticmethod
    def _wellness_key(text):
        if text in WELLNESS_REPLIES:
            return text
        match = re.fullmatch(
            r"(?:i am|i'm|im|i feel|feeling|doing)\s+(good|fine|okay|great|better|well)",
            text,
        )
        return match.group(1) if match else None
