"""Cautious, rule-based guidance adapted from the supplied care-plan screenshots."""

EMERGENCY_SIGNS = (
    "chest pain",
    "chest pressure",
    "trouble breathing",
    "difficulty breathing",
    "shortness of breath",
    "can't breathe",
    "cannot breathe",
    "face drooping",
    "slurred speech",
    "one-sided weakness",
    "one sided weakness",
    "seizure",
    "unconscious",
    "passed out",
    "severe allergic reaction",
    "throat closing",
    "tongue swelling",
    "confusion",
)

ACUTE_CRISIS_KEYWORDS = [
    {"topic": "vomiting", "keywords": ["vomiting", "throwing up"]},
    {"topic": "nausea", "keywords": ["nausea", "nauseous"]},
    {"topic": "abdominal pain", "keywords": ["stomach pain", "abdominal pain", "belly pain"]},
    {"topic": "fruity breath", "keywords": [
        "fruity breath", "sweet-smelling breath", "sweet smelling breath", "acetone breath",
    ]},
    {"topic": "abnormal breathing", "keywords": [
        "heavy breathing", "deep breathing", "gasping", "short of breath",
    ]},
    {"topic": "mental status change", "keywords": [
        "confused", "confusion", "disoriented", "foggy", "slurred",
    ]},
    {"topic": "reduced alertness", "keywords": [
        "drowsy", "hard to wake", "lethargic", "passing out", "fainting",
    ]},
    {"topic": "dehydration", "keywords": [
        "severely dehydrated", "can't keep fluids down", "cannot keep fluids down",
    ]},
]

HYPERGLYCEMIA_SYMPTOMS = [
    {"topic": "frequent urination", "keywords": [
        "peeing a lot", "frequent urination", "urinating constantly",
        "going to the bathroom every hour",
    ]},
    {"topic": "nighttime urination", "keywords": [
        "waking up to pee", "peeing at night", "nocturia",
    ]},
    {"topic": "bedwetting", "keywords": ["bedwetting", "wetting the bed"]},
    {"topic": "excessive thirst", "keywords": [
        "always thirsty", "constantly thirsty", "extreme thirst",
        "can't quench my thirst", "cannot quench my thirst", "drinking gallons",
    ]},
    {"topic": "dry mouth", "keywords": ["dry mouth", "cotton mouth", "parched"]},
    {"topic": "increased hunger", "keywords": [
        "always hungry", "starving all the time", "extreme hunger", "eating constantly",
    ]},
    {"topic": "unexplained weight loss", "keywords": [
        "losing weight", "weight loss", "clothes are loose", "dropping pounds",
    ], "requires_any": ["without trying", "unexplained", "unintentional"]},
    {"topic": "fatigue or weakness", "keywords": [
        "exhausted", "fatigued", "no energy", "drained", "always tired", "weak",
    ]},
    {"topic": "vision changes", "keywords": [
        "blurry vision", "blurred vision", "fuzzy vision", "trouble focusing",
        "eyesight changing",
    ]},
    {"topic": "yeast infection or thrush", "keywords": ["yeast infection", "thrush"]},
    {"topic": "urinary infection", "keywords": [
        "uti", "urinary tract infection", "bladder infection",
    ]},
    {"topic": "slow healing", "keywords": [
        "slow healing", "cuts won't heal", "cuts will not heal", "sores won't heal",
        "sores will not heal", "scabs taking forever",
    ]},
    {"topic": "skin infection", "keywords": ["skin infection", "boils"]},
    {"topic": "tingling or numbness", "keywords": [
        "tingling", "pins and needles", "numbness", "numb", "burning feet", "burning hands",
    ]},
    {"topic": "dark or velvety skin patches", "keywords": [
        "dark patches", "velvety skin", "dark neck", "dark armpits",
    ]},
]

DIABETES_RISK_FACTORS = [
    {"topic": "prediabetes or elevated glucose history", "keywords": [
        "prediabetes", "pre-diabetes", "borderline diabetes", "high sugar", "impaired glucose",
    ]},
    {"topic": "pregnancy-related history", "keywords": [
        "gestational diabetes", "diabetes during pregnancy", "pregnancy diabetes",
        "big baby", "heavy baby", "9 pound baby", "9-pound baby",
        "10 pound baby", "10-pound baby", "macrosomia",
    ]},
    {"topic": "PCOS", "keywords": ["pcos", "polycystic ovary"]},
    {"topic": "other health history", "keywords": [
        "high blood pressure", "hypertension", "high cholesterol", "high triglycerides",
        "low hdl", "heart disease", "stroke", "heart attack", "vascular disease",
        "pancreatitis", "pancreas", "fatty liver",
    ]},
    {"topic": "medication history", "keywords": [
        "prednisone", "steroids", "corticosteroids", "dexamethasone", "antipsychotic",
        "olanzapine", "quetiapine", "risperidone", "aripiprazole", "clozapine",
        "statin", "atorvastatin", "rosuvastatin", "lipitor", "crestor", "hiv meds",
        "hiv medication", "antiretroviral", "antiretroviral meds", "immunosuppressant",
        "anti-rejection", "tacrolimus", "cyclosporine",
    ]},
    {"topic": "family history", "keywords": [
        "family history", "runs in the family", "mom has diabetes", "mum has diabetes",
        "mother has diabetes", "dad has diabetes", "father has diabetes",
        "parent has diabetes", "sibling has diabetes", "brother has diabetes",
        "sister has diabetes",
    ]},
    {"topic": "weight or activity history", "keywords": [
        "overweight", "obese", "belly fat", "gained weight", "high bmi",
    ]},
    {"topic": "smoking history", "keywords": ["smoker", "smoking", "cigarettes"]},
    {"topic": "background associated with higher population risk", "keywords": [
        "indigenous", "first nations", "métis", "metis", "inuit", "south asian",
        "asian", "african", "black", "arab", "hispanic", "latino",
    ]},
]

MEDICAL_KEYWORDS = [
    {
        "topic": "blood sugar",
        "keywords": [
            "blood sugar", "high sugar", "glucose", "a1c", "diabetes", "insulin",
            "hypoglyc", "hyperglyc",
        ],
        "response": (
            "The care-plan notes you shared recommend recording glucose regularly and checking A1C "
            "about every 3 months; they list an A1C target of 6.5%. Your own clinician may set a "
            "different target. Follow your personal plan for high or low readings, and don't change "
            "insulin or other doses based on this chat. Contact your pharmacist or prescriber if "
            "readings are repeatedly outside your target or you feel unwell."
        ),
        "follow_ups": (
            "What recent readings or symptoms are worrying you?",
            "When did you last check, and how are you feeling now?",
        ),
    },
    {
        "topic": "blood pressure",
        "keywords": ["blood pressure", "hypertension", "systolic", "diastolic", "bp"],
        "response": (
            "The shared care plan lists an average resting blood-pressure goal below 130/80 mmHg and "
            "suggests checking at a consistent time each day. Repeated readings above your personal "
            "target are a reason to contact your doctor or pharmacist; don't adjust medication on my "
            "advice. If you have chest pain, trouble breathing, new weakness, or severe symptoms, seek "
            "emergency help."
        ),
        "follow_ups": (
            "How are you feeling right now, any symptoms, or do you feel concerned it may be high? "
            "If you have a blood-pressure cuff, please check it and share the numbers. Blood pressure "
            "can be high without noticeable symptoms, so don't rely on feeling alone.",
            "Do you feel unwell or have any symptoms, or are you worried it may be high? If a cuff "
            "is available, take a reading according to its instructions and tell me the result. "
            "Feeling normal can't rule out high blood pressure.",
        ),
    },
    {
        "topic": "cholesterol",
        "keywords": ["cholesterol", "ldl", "hdl", "triglyceride", "lipid"],
        "response": (
            "The care-plan screenshot lists LDL below 2.0 mmol/L or a 50% reduction from baseline, "
            "HDL above 1.0 mmol/L, and triglycerides below 1.5 mmol/L. These are plan-specific goals, "
            "not universal targets. Review your results and how often to repeat the panel with your "
            "prescriber or pharmacist; the shared plan mentions about every 6 months."
        ),
        "follow_ups": (
            "Is there a particular lab result you'd like help understanding?",
            "When were your cholesterol levels last checked?",
        ),
    },
    {
        "topic": "medication",
        "keywords": ["medication", "medicine", "medicines", "pills", "dose", "side effect",
                     "prescription", "drug", "pharmacy"],
        "response": (
            "Take medication as prescribed and tell your pharmacist or prescriber about any new "
            "medicine, dose change, missed doses, side effects, or if it doesn't seem to be working. "
            "Don't stop or change a dose based on this chat. For trouble breathing, throat or tongue "
            "swelling, or another severe reaction, call emergency services now."
        ),
        "follow_ups": (
            "What medicine or concern would you like to ask your pharmacist about?",
            "Are you noticing a side effect, or is your question about how to take it?",
        ),
    },
    {
        "topic": "exercise",
        "keywords": ["exercise", "workout", "physical activity", "walking", "activity"],
        "response": (
            "The shared plan suggests at least 150 minutes of moderate activity per week and two "
            "resistance sessions, with activities you enjoy. Start at a level that feels safe for you "
            "and check with your care team before changing activity if you have symptoms or limitations. "
            "Stop and seek urgent help for chest pain, fainting, or severe trouble breathing."
        ),
        "follow_ups": (
            "What kind of activity feels manageable for you right now?",
            "Is there a symptom or limitation that makes activity difficult?",
        ),
    },
    {
        "topic": "nutrition",
        "keywords": ["food", "diet", "nutrition", "fiber", "fibre", "protein", "fasting", "alcohol"],
        "response": (
            "The shared plan mentions fiber-rich foods, adequate protein, and limiting alcohol. It also "
            "mentions fasting; fasting isn't suitable for everyone, especially some people using insulin "
            "or other glucose-lowering medicine. Ask your clinician before starting or changing a fast "
            "or diet, and follow any individualized instructions they gave you."
        ),
        "follow_ups": (
            "Is your question about a particular food, or about fasting?",
            "Would you like to talk about a specific part of that plan?",
        ),
    },
]

SYMPTOM_KEYWORDS = (
    "pain", "fever", "dizzy", "dizziness", "nausea", "vomit", "rash", "swelling",
    "weak", "tired", "headache", "sick", "unwell",
)

GREETINGS = (
    "hello", "hi", "hey", "howdy", "yo", "what's up", "whats up",
    "good morning", "good afternoon", "good evening",
)

HYPERGLYCEMIA_FOLLOW_UPS = (
    "Have you checked your blood glucose recently, and when did these symptoms start?",
    "Have you had an A1C or glucose check lately? Are the symptoms getting worse?",
    "How long has this been happening, and have you discussed it with your care team?",
)

RISK_FOLLOW_UPS = (
    "A clinician can assess your overall risk and decide whether glucose or A1C screening is appropriate. Have you discussed this with your care team?",
    "This doesn't mean you have diabetes. Would you like help preparing questions about screening for your clinician?",
    "Risk factors are only one part of an assessment. A healthcare professional can help decide whether testing makes sense for you.",
)

CARE_PLAN_REFERENCE = [
    ("Blood glucose", "Monitor and record as directed; the supplied plan lists A1C every 3 months and a 6.5% target."),
    ("Blood pressure", "The supplied plan lists a resting target below 130/80 mmHg and regular checks."),
    ("Cholesterol", "The supplied plan lists LDL below 2.0 mmol/L or a 50% reduction from baseline."),
    ("Medication", "Take medicines as prescribed; discuss side effects or any change with the care team."),
    ("Activity", "The supplied plan suggests 150 minutes of weekly activity and two resistance sessions."),
]

WELLNESS_REPLIES = {
    "good": "Glad to hear that. Is there a health concern or care-plan topic you'd like help with?",
    "fine": "I'm glad you're doing okay. Would you like to review anything in your care plan?",
    "okay": "Thanks for letting me know. Is there something specific you'd like help with today?",
    "great": "That's good to hear. Is there a health question on your mind?",
    "better": "I'm glad you're feeling better. Is there anything else about your care plan you want to discuss?",
    "yes": "Thanks for letting me know. What symptoms or readings are you noticing?",
    "no": "Okay. What would be most helpful to talk through?",
    "i don't know": "That's okay. What feels most concerning or different from usual right now?",
    "i dont know": "That's okay. What feels most concerning or different from usual right now?",
}

REDIRECT_RESPONSES = (
    "I can help with how you're feeling and care-plan topics like blood sugar, blood pressure, "
    "cholesterol, medication, food, or exercise. I'm not able to help with unrelated topics. "
    "What health concern would you like to talk about?",
    "Let's bring it back to your health. I can talk through blood sugar, blood pressure, cholesterol, "
    "medication, food, or exercise. What's going on for you?",
    "I'm here to help with your health and care plan, rather than that topic. Is there a symptom or "
    "care-plan question on your mind?",
)
