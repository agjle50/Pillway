# Example 2: changes, a possible side effect, and the urgent foot flag

**Task:** "changes" step. Patient said: "I've been feeling dizzy and my doctor started me on a new pill"
```json
{"advice": "Thank you for telling me, that's helpful. Please stand up slowly and sit down if you feel dizzy.",
 "possible_issues": [{"issue": "a side effect from a medicine", "reason": "the dizziness started around when you began a new pill, and dizziness is a common side effect of Ramipril"}],
 "summary_updates": [{"type": "symptom", "value": "dizziness"}, {"type": "medication", "value": "new pill started (name not given yet)"}],
 "medication_question": false, "needs_pharmacist": true}
```
(The app adds: "Here's what I updated: ...", "Dizziness can be a common side effect of Ramipril, which is on your
medication list. I've let your pharmacist know so they can check.", then the first question.)

**Flag check** for: "I have a sore on my foot that won't heal and my toes feel numb"
```json
{"is_concern": true, "tier": 1, "reason": "Non-healing foot sore with numb toes: risk of diabetic foot ulcer.", "ask_next": "Where on your foot is the sore, how long has it been there, and is it getting bigger, red, warm or leaking?"}
```
(The app turns the message red, asks those specifics, and says: "A pharmacist will contact you soon. If you feel
very unwell, call 911 or go to the nearest emergency department.")

**Flag check** for: "My foot doesn't hurt, I just wanted to say I walked today"
```json
{"is_concern": false, "tier": null, "reason": "Patient reports no foot pain.", "ask_next": ""}
```
