"""A friendly, adjustable rule-based assistant; not a diagnosis or medical service."""

from datetime import datetime
import re

from .medical_guidance import (
    EMERGENCY_SIGNS,
    GREETINGS,
    MEDICAL_KEYWORDS,
    REDIRECT_RESPONSES,
    SYMPTOM_KEYWORDS,
    WELLNESS_REPLIES,
)


class MedicalRobot:
    def __init__(self):
        self.last_topic = None
        self.topic_turns = {}
        self.off_topic_turn = 0

    def greeting(self, now=None):
        hour = (now or datetime.now()).hour
        if 5 <= hour < 12:
            salutation = "Good morning"
        elif 12 <= hour < 18:
            salutation = "Good afternoon"
        else:
            salutation = "Good evening"
        return (
            f"{salutation}! I'm Sarah, Pillway's automated virtual assistant. "
            "I'm here to help with general questions about your care plan. "
            "How are you feeling today? Tell me what you're noticing."
        )

    def reply(self, message):
        text = " ".join(message.lower().split())
        if not text:
            return "I'm here with you. What would you like help with today?"

        if self._has_emergency_sign(text):
            self.last_topic = None
            return (
                "Those symptoms could be an emergency. Please call your local emergency number now "
                "or have someone nearby call for you. Don't wait for a chat reply. I can't assess or "
                "treat an emergency."
            )

        greeting_text = text.strip("!.,?")
        if greeting_text in GREETINGS:
            return "Hi! I'm here with you. How are you feeling, or what health concern can I help with?"

        for branch in MEDICAL_KEYWORDS:
            if self._matches_topic(text, branch["keywords"]):
                return self._topic_reply(text, branch)

        if self.last_topic:
            if self.last_topic == "blood pressure":
                reading = re.search(r"\b\d{2,3}\s*/\s*\d{2,3}\b", text)
                if reading:
                    return self._numeric_follow_up(reading.group())
            elif self.last_topic == "blood sugar":
                reading = re.search(r"\b\d{2,4}(?:\.\d+)?\b", text)
                if reading:
                    return self._numeric_follow_up(reading.group())
            if re.fullmatch(r"[\d./\s]+", text):
                return self._numeric_follow_up(text)
            if any(word in text for word in ("worried", "scared", "anxious", "concerned")):
                return self._short_follow_up("a little")

        if self.last_topic and text in ("yes", "no", "a little", "not really",
                                        "i'm not sure", "im not sure"):
            return self._short_follow_up(text)

        wellness_key = self._wellness_key(text)
        if wellness_key:
            if self.last_topic:
                return (
                    f"I'm glad to hear that. Are you still concerned about your "
                    f"{self.last_topic}?"
                )
            return WELLNESS_REPLIES[wellness_key]

        if self._matches_topic(text, SYMPTOM_KEYWORDS):
            self.last_topic = None
            return (
                "I'm sorry you're feeling unwell. I can't diagnose symptoms. If they're severe, sudden, "
                "getting worse, or you feel unsafe, seek urgent medical help. Otherwise, contact your "
                "doctor or pharmacist and tell them when this started, how it feels, and any medicines "
                "you take. What symptom is bothering you most?"
            )

        self.last_topic = None
        response = REDIRECT_RESPONSES[self.off_topic_turn % len(REDIRECT_RESPONSES)]
        self.off_topic_turn += 1
        return response

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
        if topic == "blood sugar":
            return (
                f"Thanks for sharing that reading ({reading}). Compare it with your personal target and "
                "follow your clinician's plan for readings outside range. Don't change insulin or other "
                "doses based on this chat. How are you feeling right now?"
            )
        return (
            "Thanks for sharing the number. I can't interpret it without the test and your personal "
            "target; please review it with your pharmacist or prescriber. What does the reading refer to?"
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
    def _wellness_key(text):
        if text in WELLNESS_REPLIES:
            return text
        match = re.fullmatch(r"(?:i am|i'm|im|i feel|feeling|doing)\s+(good|fine|okay|great|better|well)", text)
        return match.group(1) if match else None

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
    def _matches_topic(text, keywords):
        return any(
            re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", text)
            for keyword in keywords
        )

    @staticmethod
    def _has_emergency_sign(text):
        for sign in EMERGENCY_SIGNS:
            match = re.search(rf"\b{re.escape(sign)}\b", text)
            if not match:
                continue
            prefix = text[max(0, match.start() - 36):match.start()]
            if re.search(
                r"\b(?:no|not|never|without|don't|dont|denies)\s+"
                r"(?:(?:have|having|experiencing|feeling|any|a|an|the)\s+)?$",
                prefix,
            ):
                continue
            return True
        return False
