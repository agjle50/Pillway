"""Shared test helpers: a temporary data folder and demo-mode settings, so tests never touch real data."""

import tempfile

from config import load_settings, set_settings
from config.loader import ROOT


def use_temp_settings(demo_mode=True, **overrides):
    """Load the real config, point storage at a fresh temp folder, return the settings."""
    settings = load_settings(ROOT, env={})
    settings.storage.data_folder = tempfile.mkdtemp(prefix="pillway-test-")
    settings.ai.demo_mode = demo_mode
    settings.api_key = ""
    for dotted, value in overrides.items():
        section, key = dotted.split("__")
        setattr(getattr(settings, section), key, value)
    set_settings(settings)
    return settings
