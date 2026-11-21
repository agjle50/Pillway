"""Settings package. Use `from config import get_settings` everywhere.

Only code inside this folder reads pillway_config.toml, pillway_config.local.toml or .env.
"""

from .loader import Settings, get_settings, load_settings, set_settings
from .validation import ConfigError

__all__ = ["ConfigError", "Settings", "get_settings", "load_settings", "set_settings"]
