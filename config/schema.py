"""Every setting the app understands, with its default, type and allowed values.

Read by: config/validation.py (checks the TOML files against this list).
Why it exists: one place lists every setting, so a typo in the TOML file gets a
plain-English error instead of a crash somewhere deep in the app.

Each entry: "key": (default, type, rule)
  rule is None, a (min, max) tuple for numbers, or a list of allowed values.
"""

MODEL_NAMES = [
    "claude-opus-5-5",    # smartest, slower, most expensive
    "claude-sonnet-5-5",  # balanced
    "claude-haiku-5-5",   # fastest and cheapest
    "claude-fable-5-2",
]

SCHEMA = {
    "ai": {
        "provider": ("anthropic", str, ["anthropic"]),
        "chat_model": ("claude-opus-5-5", str, None),
        "flag_model": ("claude-haiku-5-5", str, None),
        "care_plan_model": ("claude-opus-5-5", str, None),
        "summary_model": ("claude-sonnet-5-5", str, None),
        "temperature": (0.3, float, (0.0, 1.0)),
        "max_tokens": (900, int, (100, 8000)),
        "timeout_seconds": (20, int, (3, 120)),
        "retries": (1, int, (0, 3)),
        "demo_mode": (False, bool, None),
        "ai_safety_layer_enabled": (True, bool, None),
        "deidentify_before_ai": (True, bool, None),
        "prompt_caching": (True, bool, None),
        "api_key_env_var": ("ANTHROPIC_API_KEY", str, None),
        "api_key": ("", str, None),  # only allowed in pillway_config.local.toml
    },
    "safety": {
        "blood_sugar_low": (3.9, float, (1.0, 10.0)),
        "blood_sugar_high": (14.0, float, (7.0, 40.0)),
        "blood_sugar_very_high": (20.0, float, (8.0, 50.0)),
        "bp_systolic_urgent": (180, int, (120, 260)),
        "bp_diastolic_urgent": (110, int, (70, 160)),
        "bp_systolic_watch": (160, int, (110, 250)),
        "bp_diastolic_watch": (100, int, (60, 150)),
        "bp_systolic_low": (90, int, (60, 120)),
        "missed_check_in_days": (2, int, (1, 30)),
        "buzzwords_file": ("data/buzzwords.json", str, None),
        "questions_file": ("data/questions.json", str, None),
    },
    "pharmacist": {
        "pharmacist_review_required": (True, bool, None),
        "default_filter": ("All", str, ["All", "ACTIVE", "WATCHING"]),
        "default_sort": ("Needs attention", str, ["Needs attention", "Name"]),
        "default_view": ("comfortable", str, ["comfortable", "compact"]),
        "alert_method": ("dashboard", str, ["dashboard"]),
        "active_window_seconds": (180, int, (10, 3600)),
        "demo_username": ("pharmacist", str, None),
        "demo_password": ("demo", str, None),
    },
    "patient": {
        "default_language": ("en", str, ["en", "fr"]),
        "read_aloud": (True, bool, None),
        "voice_input": (True, bool, None),
        "text_size": (1.0, float, (0.8, 1.6)),
        "quick_replies": (True, bool, None),
        "max_questions_per_check_in": (10, int, (1, 20)),
        "demo_username": ("maria", str, None),
        "demo_password": ("demo", str, None),
    },
    "french": {
        "show_translation_review_status": (True, bool, None),
        "french_strings_file": ("data/french_strings.json", str, None),
    },
    "call": {
        "call_enabled": (True, bool, None),
        "speech_to_text_engine": ("vosk", str, ["vosk", "none"]),
        "microphone_device": ("", str, None),
        "listening_mode": ("continuous", str, ["hold_to_talk", "continuous"]),
        "voice_meter_sensitivity": (1.0, float, (0.1, 5.0)),
        "sarah_voice": ("", str, None),
        "sarah_speech_rate": (165, int, (80, 300)),
    },
    "check_ins": {
        "daily_check_in_time": ("19:00", str, None),
        "weekly_summary_day": ("Sunday", str, [
            "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]),
        "weekly_summary_time": ("18:00", str, None),
        "quiet_hours_start": ("21:30", str, None),
        "quiet_hours_end": ("08:00", str, None),
        "reminders_opt_in_default": (False, bool, None),
        "check_in_messages_file": ("data/check_in_messages.json", str, None),
    },
    "branding": {
        "app_name": ("Pillway", str, None),
        "assistant_name": ("Sarah", str, None),
        "pharmacy_name": ("Pillway", str, None),
        "navy": ("#0a0f42", str, "colour"),
        "navy_dark": ("#080c38", str, "colour"),
        "red": ("#ef3f3f", str, "colour"),
        "text_dark": ("#4a566f", str, "colour"),
        "text_muted": ("#768197", str, "colour"),
        "border": ("#dde2ea", str, "colour"),
        "logo_path": ("", str, None),
    },
    "demo": {
        "seed_patients_file": ("data/seed_patients.json", str, None),
        "visible_patients": (["maria"], list, None),
        "fake_watch_data": (True, bool, None),
        "plans_per_month": (100, int, (1, 100000)),
        "follow_ups_per_plan": (6, int, (1, 50)),
        "minutes_per_follow_up_low": (10, int, (1, 120)),
        "minutes_per_follow_up_high": (15, int, (1, 120)),
    },
    "storage": {
        "data_folder": ("", str, None),
    },
    "dev": {
        "dev_mode": (False, bool, None),
    },
}

# Settings that are risky to change; --check-config warns about them.
UNSAFE_WHEN = {
    ("pharmacist", "pharmacist_review_required"): (False, "pharmacist review is OFF: care plans go to patients without approval"),
    ("ai", "ai_safety_layer_enabled"): (False, "the AI safety layer (layer 2) is OFF: only hard-coded rules check messages"),
    ("ai", "deidentify_before_ai"): (False, "de-identification is OFF: names and contact details would be sent to the AI"),
    ("ai", "demo_mode"): (True, "demo mode is ON: replies are scripted, not real AI"),
}
