"""Loads made-up dashboard content (orders, banner, starter notifications) from data/sample_content.json.

Called by: ui/patient/dashboard.py, ui/patient/orders.py, pillway/app.py.
"""

import json

from config import get_settings

_data = json.loads(get_settings().path("data/sample_content.json").read_text(encoding="utf-8"))

BANNER_TEXT = _data["banner_text"]
NOTIFICATIONS = [tuple(item) for item in _data["notifications"]]
ORDERS = [tuple(item) for item in _data["orders"]]
