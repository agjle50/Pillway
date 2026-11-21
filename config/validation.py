"""Checks settings read from the TOML files and turns mistakes into plain English.

Read by: config/loader.py.
Why it exists: a teammate who types `blood_sugar_high = "lots"` should see
"`blood_sugar_high` must be a number, like 14.0", not a Python stack trace.
"""

import re

from .schema import SCHEMA

TYPE_WORDS = {int: "a whole number", float: "a number", bool: "true or false",
              str: "text in quotes", list: "a list in square brackets"}
COLOUR = re.compile(r"^#[0-9a-fA-F]{6}$")


class ConfigError(Exception):
    """Raised when one or more settings are invalid. The message is beginner-friendly."""


def _example(default):
    if isinstance(default, bool):
        return "true" if default else "false"
    if isinstance(default, str):
        return f'"{default}"'
    return str(default)


def _coerce(key, value, kind, default):
    """Return (value, error). Ints are accepted where floats are expected."""
    if kind is float and isinstance(value, int) and not isinstance(value, bool):
        return float(value), None
    if kind is int and isinstance(value, bool):
        return None, f"`{key}` must be {TYPE_WORDS[kind]}, like {_example(default)}"
    if not isinstance(value, kind):
        return None, f"`{key}` must be {TYPE_WORDS[kind]}, like {_example(default)}"
    return value, None


def validate(raw, source_name):
    """Check one parsed TOML file. Returns (clean_values, errors, warnings).

    clean_values only contains keys that were present and valid, so the caller
    can layer files on top of each other (shared file, then local file).
    """
    clean, errors, warnings = {}, [], []
    for section, values in raw.items():
        if section not in SCHEMA:
            warnings.append(f"{source_name}: unknown section [{section}] was ignored")
            continue
        if not isinstance(values, dict):
            errors.append(f"{source_name}: [{section}] must be a section, not a single value")
            continue
        for key, value in values.items():
            if key not in SCHEMA[section]:
                warnings.append(f"{source_name}: unknown setting `{key}` in [{section}] was ignored")
                continue
            default, kind, rule = SCHEMA[section][key]
            value, error = _coerce(key, value, kind, default)
            if error is None:
                error = _check_rule(key, value, rule)
            if error:
                errors.append(f"{source_name} [{section}]: {error}")
                continue
            clean.setdefault(section, {})[key] = value
    return clean, errors, warnings


def _check_rule(key, value, rule):
    if rule is None:
        return None
    if rule == "colour":
        if not COLOUR.match(value):
            return f"`{key}` must be a colour like \"#0a0f42\""
        return None
    if isinstance(rule, tuple):
        low, high = rule
        if not low <= value <= high:
            return f"`{key}` must be between {low} and {high} (you wrote {value})"
        return None
    if value not in rule:
        allowed = ", ".join(f'"{item}"' for item in rule)
        return f"`{key}` must be one of {allowed} (you wrote \"{value}\")"
    return None


def cross_checks(values):
    """Rules that involve two settings at once."""
    errors = []
    safety = values["safety"]
    if safety["blood_sugar_high"] >= safety["blood_sugar_very_high"]:
        errors.append("`blood_sugar_high` must be lower than `blood_sugar_very_high`")
    if safety["blood_sugar_low"] >= safety["blood_sugar_high"]:
        errors.append("`blood_sugar_low` must be lower than `blood_sugar_high`")
    demo = values["demo"]
    if demo["minutes_per_follow_up_low"] > demo["minutes_per_follow_up_high"]:
        errors.append("`minutes_per_follow_up_low` must not be bigger than `minutes_per_follow_up_high`")
    for key in ("daily_check_in_time", "weekly_summary_time", "quiet_hours_start", "quiet_hours_end"):
        if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", values["check_ins"][key]):
            errors.append(f"`{key}` must be a 24-hour time like \"19:00\"")
    return errors
