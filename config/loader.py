"""Reads pillway_config.toml, pillway_config.local.toml and .env into one `settings` object.

Read by: everything that needs a setting calls `get_settings()`.
This is the ONLY code that opens the config files or .env (rule of the codebase).

Order (later wins): built-in defaults -> pillway_config.toml -> pillway_config.local.toml.
API key order: environment variable -> local file `api_key` -> .env -> none (demo mode).
"""

import os
import subprocess
import tomllib
from pathlib import Path
from types import SimpleNamespace

from .schema import SCHEMA
from .validation import ConfigError, cross_checks, validate

ROOT = Path(__file__).resolve().parent.parent
SHARED_FILE = "pillway_config.toml"
LOCAL_FILE = "pillway_config.local.toml"
KEY_PREFIX = "sk-ant-"


class Settings(SimpleNamespace):
    """Typed settings. Use like `settings.ai.chat_model`. Never prints the API key."""

    def path(self, relative):
        """Turn a path from the config (like "data/questions.json") into a full path."""
        candidate = Path(relative)
        return candidate if candidate.is_absolute() else self.root / candidate

    def masked_key(self):
        return f"…{self.api_key[-4:]}" if self.api_key else "(none)"

    def __repr__(self):
        return f"Settings(root={self.root}, key={self.masked_key()})"


def _read_toml(path):
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(
            f"{path.name} has a typing mistake: {error}. Check quotes and = signs on that line."
        ) from None


def _read_dotenv(path):
    """Tiny .env reader (KEY=value lines). Avoids needing python-dotenv to start."""
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _is_tracked_by_git(root, path):
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(path)], cwd=root,
            capture_output=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def _file_contains_key(path):
    return path.exists() and KEY_PREFIX in path.read_text(encoding="utf-8", errors="ignore")


def _safety_net(root):
    """Refuse to start if a real-looking key sits in a shared or committed file."""
    for name in (SHARED_FILE, LOCAL_FILE, ".env", f"{LOCAL_FILE.replace('.toml', '.example.toml')}"):
        path = root / name
        if not _file_contains_key(path):
            continue
        if name == SHARED_FILE or _is_tracked_by_git(root, path):
            raise ConfigError(
                f"An API key was found in {name}, which is shared on GitHub. "
                f"Remove your API key from this file and put it in {LOCAL_FILE}."
            )
    warnings = []
    gitignore = root / ".gitignore"
    if not gitignore.exists() or LOCAL_FILE not in gitignore.read_text(encoding="utf-8"):
        warnings.append(f".gitignore does not list {LOCAL_FILE}; your key could be committed by accident.")
    return warnings


def _find_api_key(root, values, env):
    env_name = values["ai"]["api_key_env_var"]
    if env.get(env_name):
        return env[env_name].strip(), f"environment variable {env_name}"
    if values["ai"]["api_key"]:
        return values["ai"]["api_key"].strip(), LOCAL_FILE
    dotenv_key = _read_dotenv(root / ".env").get(env_name, "")
    if dotenv_key:
        return dotenv_key, ".env file"
    return "", "none"


def load_settings(root=None, env=None):
    """Build a fresh Settings object. Raises ConfigError with plain-English messages."""
    root = Path(root) if root else ROOT
    env = os.environ if env is None else env
    values = {section: {key: spec[0] for key, spec in keys.items()} for section, keys in SCHEMA.items()}
    all_errors, all_warnings = [], _safety_net(root)

    shared_path, local_path = root / SHARED_FILE, root / LOCAL_FILE
    if not shared_path.exists():
        all_warnings.append(f"{SHARED_FILE} was not found, so built-in defaults are used.")
    for path in (shared_path, local_path):
        if not path.exists():
            continue
        clean, errors, warnings = validate(_read_toml(path), path.name)
        if path == shared_path and clean.get("ai", {}).get("api_key"):
            errors.append(f"{SHARED_FILE}: `api_key` is not allowed here. Put it in {LOCAL_FILE}.")
        all_errors += errors
        all_warnings += warnings
        for section, section_values in clean.items():
            values[section].update(section_values)
    all_errors += cross_checks(values)
    if all_errors:
        raise ConfigError("Your settings need fixing:\n  - " + "\n  - ".join(all_errors))

    api_key, key_source = _find_api_key(root, values, env)
    sections = {name: SimpleNamespace(**section) for name, section in values.items()}
    sections["ai"].api_key = ""  # the key lives only on settings.api_key
    return Settings(root=root, api_key=api_key, api_key_source=key_source,
                    warnings=all_warnings, **sections)


_cached = None


def get_settings():
    """The single shared settings object (loaded once)."""
    global _cached
    if _cached is None:
        _cached = load_settings()
    return _cached


def set_settings(settings):
    """Replace the shared settings (used by tests and by --demo flags)."""
    global _cached
    _cached = settings
