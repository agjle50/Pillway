"""Reads pillway_config.toml, pillway_config.local.toml and .env into one `settings` object.

Read by: everything that needs a setting calls `get_settings()`.
This is the ONLY code that opens the config files or .env (rule of the codebase).

Order (later wins): built-in defaults -> pillway_config.toml -> pillway_config.local.toml.
API key order: environment variable -> local file `api_key` -> .env -> none (demo mode).
"""

import os
import re
import subprocess
import tomllib
from pathlib import Path
from types import SimpleNamespace

from .schema import SCHEMA
from .validation import ConfigError, cross_checks, validate

ROOT = Path(__file__).resolve().parent.parent
SHARED_FILE = "pillway_config.toml"
LOCAL_FILE = "pillway_config.local.toml"
# what a Google (Gemini) or DeepSeek API key looks like (used to spot a key pasted in the wrong file)
KEY_PATTERN = re.compile(r"AIza[0-9A-Za-z_\-]{30,}|sk-[0-9A-Za-z]{24,}")


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
    """Read .env with python-dotenv if installed, otherwise a tiny KEY=value reader."""
    values = {}
    if not path.exists():
        return values
    try:
        from dotenv import dotenv_values
        return {key: value or "" for key, value in dotenv_values(path).items()}
    except ImportError:
        pass
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
    return path.exists() and bool(KEY_PATTERN.search(path.read_text(encoding="utf-8", errors="ignore")))


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


PROVIDER_ENV_VARS = {"deepseek": "DEEPSEEK_API_KEY", "gemini": "GEMINI_API_KEY"}
KEY_PREFIX = {"deepseek": "sk-", "gemini": "AIza"}


def clean_key(value):
    """Tidy a pasted key: spaces, line breaks, quotes and a stray "Bearer " are removed."""
    value = (value or "").strip().strip('"').strip("'").strip()
    if value.lower().startswith("bearer "):
        value = value[7:].strip()
    return "".join(value.split())


def find_api_keys(root, values, env):
    """Every key the app can find, in priority order: [(key, source), ...].

    BUG FIX ("it pulls the wrong API key"): a key in the computer's settings (environment
    variable) or .env used to beat the key you saved in the app, so an old key silently won.
    Now the key saved in the app (pillway_config.local.toml) comes first.
    """
    names = list(dict.fromkeys(filter(None, [values["ai"]["api_key_env_var"],
                                             PROVIDER_ENV_VARS.get(values["ai"]["provider"], ""),
                                             *PROVIDER_ENV_VARS.values()])))
    found = []
    if values["ai"]["api_key"]:
        found.append((clean_key(values["ai"]["api_key"]), LOCAL_FILE))
    for env_name in names:
        if env.get(env_name):
            found.append((clean_key(env[env_name]), f"environment variable {env_name}"))
    dotenv = _read_dotenv(root / ".env")
    for env_name in names:
        if dotenv.get(env_name):
            found.append((clean_key(dotenv[env_name]), f".env file ({env_name})"))
    return [(key, source) for key, source in found if key]


def _find_api_key(root, values, env):
    """The first key that fits the chosen provider (a Gemini key is skipped when using DeepSeek)."""
    found = find_api_keys(root, values, env)
    prefix = KEY_PREFIX.get(values["ai"]["provider"], "")
    for key, source in found:
        if key.startswith(prefix):
            return key, source
    return found[0] if found else ("", "none")


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
    # every key found, masked, for --check-ai and Settings > AI connection (never the full key)
    found = [{"source": source, "ends": key[-4:], "kind": _kind(key), "used": source == key_source}
             for key, source in find_api_keys(root, values, env)]
    for item in found:
        if not item["used"] and item["ends"] != api_key[-4:]:
            all_warnings.append(f"A different API key (ending …{item['ends']}) in {item['source']} is NOT used; "
                                f"the app uses the one from {key_source}.")
    sections = {name: SimpleNamespace(**section) for name, section in values.items()}
    sections["ai"].api_key = ""  # the key lives only on settings.api_key
    return Settings(root=root, api_key=api_key, api_key_source=key_source, api_keys_found=found,
                    warnings=all_warnings, **sections)


def _kind(key):
    return "DeepSeek" if key.startswith("sk-") else "Gemini" if key.startswith("AIza") else "unknown"


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
