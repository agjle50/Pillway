"""The first-visit health questionnaire, and the health profile Sarah builds from it.

Called by: ui/patient/intake.py (the screen), core/conversation_service.py (what Sarah knows),
ai/brain.py (the AI's guesses) and the tests. Pure logic: no window, no AI calls.

Why it exists (plain words):
  * Sarah must NOT presume anything about a patient's health. Before this, the demo patients
    came with weight, blood pressure and smoking already filled in, and Sarah read them back
    as if the patient had said them. Now a new account answers a short questionnaire first
    (the same questions as Pillway's intake sheet, ids 1-18 below), and only those answers
    count as "known".
  * From the answers we build a HEALTH PROFILE: what is known, what the patient chose not to
    share (never pushed), and "areas to explore": educated guesses about what may need
    attention, each with the reason. Sarah uses those guesses to choose her questions, but
    always ASKS; a guess is never told to the patient as a fact.

When it shows: at first boot of an account that has no chat history and hasn't done it yet.
It also sits in the Tasks tab as "Complete your health questionnaire" until it's done.
"""

from ..storage.patient_store import now_iso

VERSION = 1

# Pillway's intake sheet (id: English text). The screen shows these; ids match the sheet.
SHEET = {
    1: "If you are comfortable discussing your weight and weight-related concerns, please indicate "
       "your weight and height below.",
    2: "Weight",
    3: "Height",
    4: "Do you regularly check your blood pressure?",
    5: "If yes, add your average blood pressure",
    7: "Do you use tobacco products?",
    8: "If yes, select the statement that best describes you",
    17: "Average systolic blood pressure",
    18: "Average diastolic blood pressure",
}

# Pillway's program starts with diabetes and hypertension (the challenge brief). The intake asks
# which of them the patient is managing, so Sarah's questions and the care plan fit them.
CONDITIONS = {
    "type2": ("Type 2 diabetes", "Diabète de type 2"),
    "gestational": ("Gestational diabetes", "Diabète gestationnel"),
    "hypertension": ("High blood pressure", "Hypertension artérielle"),
    "unsure": ("Not sure", "Je ne sais pas"),
}

READINESS = {
    "not_considering": "I am not considering quitting smoking at this time",
    "thinking": "I am thinking about making changes but not ready to quit smoking at this time",
    "ready": "I am motivated and ready to quit smoking",
}

LIMITS = {"weight_kg": (25, 350), "height_cm": (100, 250), "systolic": (70, 260), "diastolic": (40, 160)}
LB_PER_KG = 2.20462
CM_PER_IN = 2.54


# ---- when to show it -------------------------------------------------------------------------

def is_done(record):
    return bool((record.get("intake") or {}).get("completed"))


def has_history(record):
    """True once the patient has ever said anything to Sarah (chat or call)."""
    return any(message.get("role") == "patient" for message in record.get("messages", []))


def needed_at_boot(record):
    """Show the questionnaire straight away: a brand-new account with no chats and no intake."""
    return not is_done(record) and not has_history(record)


# ---- checking the answers --------------------------------------------------------------------

def _number(text):
    text = str(text or "").strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return "bad"


def validate(form, lang="en"):
    """Check the screen's answers. Returns (clean_answers, errors) where errors is {field: message}.

    form keys: weight, weight_unit ("kg"/"lb"), height, height_unit ("cm"/"in"),
               checks_bp ("yes"/"no"/None), systolic, diastolic,
               tobacco ("yes"/"no"/None), readiness (a READINESS key or None).
    Weight and height are optional ("if you are comfortable"). The yes/no questions are required.
    """
    fr = lang == "fr"
    errors, clean = {}, {}

    conditions = form.get("conditions")
    if conditions is not None:              # the screen always sends a list (older callers may not)
        picked = [c for c in conditions if c in CONDITIONS]
        if not picked:
            errors["conditions"] = ("Choisissez au moins une réponse (ou « Je ne sais pas »)." if fr
                                    else "Please choose at least one (or \"Not sure\").")
        else:
            clean["conditions"] = [c for c in picked if c != "unsure"] if len(picked) > 1 else picked

    weight, height = _number(form.get("weight")), _number(form.get("height"))
    if weight == "bad":
        errors["weight"] = "Entrez un nombre." if fr else "Please enter a number."
    elif weight is not None:
        kg = weight / LB_PER_KG if form.get("weight_unit") == "lb" else weight
        low, high = LIMITS["weight_kg"]
        if not low <= kg <= high:
            errors["weight"] = "Ce poids semble inhabituel." if fr else "That weight looks unusual. Please check it."
        else:
            clean["weight_kg"] = round(kg, 1)
    if height == "bad":
        errors["height"] = "Entrez un nombre." if fr else "Please enter a number."
    elif height is not None:
        cm = height * CM_PER_IN if form.get("height_unit") == "in" else height
        low, high = LIMITS["height_cm"]
        if not low <= cm <= high:
            errors["height"] = "Cette taille semble inhabituelle." if fr else "That height looks unusual. Please check it."
        else:
            clean["height_cm"] = round(cm)
    clean["shared_weight"] = "weight_kg" in clean or "height_cm" in clean

    checks_bp = form.get("checks_bp")
    if checks_bp not in ("yes", "no"):
        errors["checks_bp"] = "Choisissez Oui ou Non." if fr else "Please choose Yes or No."
    else:
        clean["checks_bp_regularly"] = checks_bp == "yes"
    if checks_bp == "yes":
        systolic, diastolic = _number(form.get("systolic")), _number(form.get("diastolic"))
        if systolic is None and diastolic is None:
            pass  # they check it but don't remember the numbers: that's fine
        elif systolic in (None, "bad") or diastolic in (None, "bad"):
            errors["bp"] = ("Entrez les deux chiffres, par exemple 130 et 85." if fr
                            else "Please enter both numbers, for example 130 and 85.")
        elif not (LIMITS["systolic"][0] <= systolic <= LIMITS["systolic"][1]
                  and LIMITS["diastolic"][0] <= diastolic <= LIMITS["diastolic"][1]) or systolic <= diastolic:
            errors["bp"] = ("Ces chiffres semblent inhabituels. Le premier est le plus grand (ex. 130/85)." if fr
                            else "Those numbers look unusual. The top number is the bigger one (e.g. 130/85).")
        else:
            clean["bp_systolic"], clean["bp_diastolic"] = round(systolic), round(diastolic)

    tobacco = form.get("tobacco")
    if tobacco not in ("yes", "no"):
        errors["tobacco"] = "Choisissez Oui ou Non." if fr else "Please choose Yes or No."
    else:
        clean["smoker"] = tobacco == "yes"
    if tobacco == "yes":
        if form.get("readiness") not in READINESS:
            errors["readiness"] = ("Choisissez l'énoncé qui vous décrit le mieux." if fr
                                   else "Please choose the statement that fits you best.")
        else:
            clean["quit_readiness"] = form["readiness"]
    return clean, errors


# ---- saving ----------------------------------------------------------------------------------

QUESTIONNAIRE_KEYS = ("weight_kg", "height_cm", "checks_bp_regularly", "last_bp", "smoker", "quit_readiness")


def apply(record, clean):
    """Save the answers on the record and (re)build the health profile. Edits record in place.

    Anything NOT answered is removed from the profile, so an old or demo value can never be
    passed off as something the patient told us.
    """
    profile = record["profile"]
    for key in QUESTIONNAIRE_KEYS:
        profile.pop(key, None)
    for key in ("weight_kg", "height_cm", "checks_bp_regularly", "smoker"):
        if key in clean:
            profile[key] = clean[key]
    if "bp_systolic" in clean:
        profile["last_bp"] = f"{clean['bp_systolic']}/{clean['bp_diastolic']}"
    profile["quit_readiness"] = READINESS.get(clean.get("quit_readiness"), "")
    # conditions: what the pharmacy has on file + what the patient told us (never removed, never guessed)
    on_file = profile.setdefault("pharmacy_conditions", list(profile.get("conditions", [])))
    merged = list(on_file)
    for key in clean.get("conditions", []):
        if key == "unsure":
            continue
        already = " ".join(merged).lower()
        if key == "hypertension" and ("blood pressure" in already or "hypertension" in already):
            continue
        if key == "type2" and "type 2" in already:
            continue
        if key == "gestational" and "gestational" in already:
            continue
        merged.append(CONDITIONS[key][0])
    profile["conditions"] = merged
    record["intake"] = {"completed": True, "time": now_iso(), "version": VERSION, "answers": dict(clean)}
    record["health_profile"] = build_profile(record)
    return record


# ---- the health profile ------------------------------------------------------------------------

def bmi(weight_kg, height_cm):
    if not weight_kg or not height_cm:
        return None
    return round(weight_kg / (height_cm / 100) ** 2, 1)


def build_profile(record):
    """What Sarah knows, what she doesn't, and what she might gently ask about (rule-based).

    Returns {"known": [...], "not_shared": [...], "unknown": [...], "areas_to_explore": [...],
             "source": "questionnaire rules", "built": time}
    Each area: {"area", "why", "ask_about"}. These are HYPOTHESES to check by asking.
    """
    answers = (record.get("intake") or {}).get("answers", {})
    profile = record.get("profile", {})
    known, not_shared, unknown, areas = [], [], [], []

    weight, height = answers.get("weight_kg"), answers.get("height_cm")
    if weight:
        known.append(f"weight {weight} kg (questionnaire)")
    if height:
        known.append(f"height {height} cm (questionnaire)")
    if not answers.get("shared_weight"):
        not_shared.append("weight and height: chose not to share. Don't ask for them; only talk about "
                          "weight if the patient brings it up.")
    value = bmi(weight, height)
    if value:
        known.append(f"BMI about {value} (calculated)")
        if value >= 30:
            areas.append({"area": "weight, eating habits and activity",
                          "why": f"BMI about {value} (from their height and weight)",
                          "ask_about": "a typical day of meals, and how active they are"})
        elif value >= 25:
            areas.append({"area": "eating habits and activity",
                          "why": f"BMI about {value} is a little above the healthy range",
                          "ask_about": "meals and activity, kindly and without judging"})
        elif value < 18.5:
            areas.append({"area": "low weight or poor appetite",
                          "why": f"BMI about {value} is below the healthy range",
                          "ask_about": "appetite and any weight they lost without trying"})

    if answers.get("checks_bp_regularly") is True:
        known.append("checks blood pressure regularly (questionnaire)")
    elif answers.get("checks_bp_regularly") is False:
        known.append("does not check blood pressure regularly (questionnaire)")
        areas.append({"area": "home blood pressure checks",
                      "why": "they don't check their blood pressure regularly",
                      "ask_about": "whether they have a home monitor and what gets in the way"})
    systolic, diastolic = answers.get("bp_systolic"), answers.get("bp_diastolic")
    if systolic:
        known.append(f"average blood pressure {systolic}/{diastolic} (questionnaire)")
        if systolic >= 140 or diastolic >= 90:
            areas.append({"area": "high blood pressure",
                          "why": f"their average of {systolic}/{diastolic} is above 140/90",
                          "ask_about": "headaches, dizziness, salt and stress, and how they're getting on with any BP medicine"})
        elif systolic >= 130 or diastolic >= 80:
            areas.append({"area": "blood pressure a little high",
                          "why": f"their average of {systolic}/{diastolic} is above the 130/80 target",
                          "ask_about": "salt, activity and how they measure it"})
        elif systolic < 90:
            areas.append({"area": "low blood pressure",
                          "why": f"their average of {systolic}/{diastolic} is low",
                          "ask_about": "dizziness or light-headedness when standing up"})
    elif answers.get("checks_bp_regularly") is True:
        unknown.append("their usual blood pressure numbers (they check it but didn't enter an average)")

    if answers.get("smoker") is True:
        stage = answers.get("quit_readiness")
        known.append(f"uses tobacco; in their words: \"{READINESS.get(stage, 'readiness not given')}\" (questionnaire)")
        areas.append({
            "area": "smoking",
            "why": "they use tobacco",
            "ask_about": {
                "ready": "what support would help them quit (the pharmacist can talk about options)",
                "thinking": "what would help them feel ready, with no pressure",
                "not_considering": "respect their choice; only gently ask about cough or shortness of breath",
            }.get(stage, "how they feel about it, with no pressure"),
        })
    elif answers.get("smoker") is False:
        known.append("does not use tobacco (questionnaire)")

    # The pharmacy's own record (prescriptions) is real information, not a guess.
    conditions = [c for c in profile.get("conditions", []) if c]
    medications = [m.get("name") for m in record.get("medications", []) if m.get("name")]
    if conditions:
        known.append("on file at the pharmacy: " + ", ".join(conditions))
    if medications:
        known.append("medications on file: " + ", ".join(medications))
    text = " ".join(conditions).lower()
    if ("blood pressure" in text or "hypertension" in text) and not any("blood pressure" in a["area"] for a in areas):
        areas.append({"area": "blood pressure: home readings, salt and activity",
                      "why": "high blood pressure is one of their conditions",
                      "ask_about": "their latest home readings, salty or packaged foods, and how active they are"})
    if "gestational" in text:
        areas.append({"area": "pregnancy and blood sugar",
                      "why": "gestational diabetes",
                      "ask_about": "how they check their sugar and what worries them; leave targets to the pharmacist"})
    if "diabetes" in text:
        areas.append({"area": "blood sugar, feet and eyes",
                      "why": "diabetes is on their pharmacy file",
                      "ask_about": "recent sugar readings, any sores or numbness on the feet, last eye exam"})
    if medications:
        areas.append({"area": "side effects and how the medicines are going",
                      "why": "they have medications on file",
                      "ask_about": "how they feel on them (never give medication advice)"})
    if not conditions:
        unknown.append("which health conditions they have (nothing on file: ask, never assume)")
    unknown.append("symptoms, diet, activity, sleep and mood (ask; nothing is known yet)")

    return {"known": known, "not_shared": not_shared, "unknown": unknown, "areas_to_explore": areas,
            "ai_suggestions": [], "source": "questionnaire rules", "built": now_iso()}


def merge_ai_suggestions(record, suggestions):
    """Add the AI's extra guesses (already checked by the parser) to the profile. In place."""
    profile = record.setdefault("health_profile", build_profile(record))
    clean = []
    for item in suggestions[:5]:
        area, why = str(item.get("area", "")).strip(), str(item.get("why", "")).strip()
        if area and why:
            clean.append({"area": area[:80], "why": why[:200], "ask_about": str(item.get("ask_about", ""))[:200]})
    profile["ai_suggestions"] = clean
    return record


def for_ai(record):
    """The profile as Sarah's AI sees it (no names or contact details are in it)."""
    profile = record.get("health_profile")
    if not profile:
        return {"status": "no questionnaire yet: nothing about their health is known; ask, never assume"}
    return {key: profile.get(key, []) for key in
            ("known", "not_shared", "unknown", "areas_to_explore", "ai_suggestions")}


AREA_QUESTIONS = (("blood pressure", ("blood_pressure",)), ("weight", ("diet", "activity")),
                  ("eating", ("diet", "activity")), ("smoking", ("smoking",)), ("low weight", ("diet",)),
                  ("blood sugar", ("blood_sugar", "feet", "eyes")), ("side effects", ("changes",)))


def priority_questions(record):
    """Check-in question ids made most important by the intake results, most important first."""
    ids = []
    profile = record.get("health_profile") or {}
    for area in profile.get("areas_to_explore", []) + profile.get("ai_suggestions", []):
        name = area.get("area", "").lower()
        for word, questions in AREA_QUESTIONS:
            if word in name:
                ids += [q for q in questions if q not in ids]
    return ids


def condition_flags(record):
    """(diabetes, high_blood_pressure, known): which program conditions this patient has.

    known is False when nothing is on file and the patient chose "Not sure": then every check-in
    question is asked, so nothing important is skipped.
    """
    text = " ".join(record.get("profile", {}).get("conditions", [])).lower()
    diabetes = "diabet" in text
    pressure = "blood pressure" in text or "hypertension" in text
    return diabetes, pressure, diabetes or pressure


def task_entry(record, lang="en"):
    """The Tasks-tab row for the questionnaire."""
    done = is_done(record)
    if lang == "fr":
        label = "Questionnaire de santé terminé" if done else "Remplissez votre questionnaire de santé (3 min)"
    else:
        label = "Health questionnaire completed" if done else "Complete your health questionnaire (3 min)"
    return {"done": done, "label": label}
