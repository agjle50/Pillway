"""Text clean-up used by the safety rules: lowercase, straight quotes, single spaces, simple plurals.

Called by: core/safety_rules.py and core/deidentify.py.
Why: "My  Foot SORES" and "my foot sore" must match the same buzzword.
"""

import re

_QUOTES = {"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-"}
_KEEP_S = ("ss", "us", "is", "ous")


def normalize(text):
    """Lowercase, straighten quotes, collapse spaces."""
    for curly, straight in _QUOTES.items():
        text = text.replace(curly, straight)
    return " ".join(text.lower().split())


def singular(word):
    """Very simple plural -> singular ('sores' -> 'sore'). Short words are left alone."""
    if len(word) <= 3 or not word.endswith("s") or word.endswith(_KEEP_S):
        return word
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    return word[:-1]


def words(text):
    """Split normalized text into simple word tokens (apostrophes kept: don't, can't)."""
    return re.findall(r"[a-z0-9À-ſ]+(?:['-][a-z0-9À-ſ]+)*", text)


def singular_text(text):
    """Normalized text with every word made singular, joined by single spaces."""
    return " ".join(singular(word) for word in words(normalize(text)))


def sentences(text):
    """Split into rough sentences so a 'no' in one sentence doesn't cancel another."""
    return [part.strip() for part in re.split(r"[.!?;\n]+|\bbut\b", text) if part.strip()]
