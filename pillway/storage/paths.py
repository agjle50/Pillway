"""Where Pillway saves data on this computer.

Called by: every store in pillway/storage/.
Default: Windows %LOCALAPPDATA%\\Pillway, everything else ~/.local/share/Pillway
(the same folder the app used before). Override with [storage] data_folder in the config.
"""

import os
import sys
from pathlib import Path

from config import get_settings


def data_folder():
    configured = get_settings().storage.data_folder
    if configured:
        return Path(configured).expanduser()
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path.home() / ".local" / "share"
    return base / "Pillway"
