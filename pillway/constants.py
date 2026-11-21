"""Shared colors, sizing, and sample content for the Pillway UI."""

NAVY = "#0a0f42"
NAVY_DARK = "#080c38"
RED = "#ef3f3f"
RED_DARK = "#d93636"
ORANGE = "#f28c28"
TEXT_DARK = "#4a566f"
TEXT_MUTED = "#768197"
TEXT_OFF = "#b4bccb"
BORDER = "#dde2ea"
WHITE = "#ffffff"
SOFT_BLUE = "#eef2ff"
INK = "#101a3c"
NAV_TEXT = "#edf0ff"
NAV_ICON = "#9da9dc"
DIVIDER = "#9098b8"
SHADOW = "#e8ebf2"
TOGGLE_OFF = "#d5dae4"

FONT = "Segoe UI"
BASE_W, BASE_H = 1500, 900

VIRTUAL_ASSISTANT_POPUP_TEXT = (
    "Get a virtual assistant doctor to help you discover your condition today, live."
)

NAV_ITEMS = [
    ("Dashboard", "grid"),
    ("Settings", "gear"),
    ("Manage profiles", "person"),
    None,
    ("Medications", "pills"),
    ("Prescription", "rx"),
    ("See a doctor", "stethoscope"),
    ("Orders", "order"),
    ("Tasks", "task"),
    None,
    ("Contact us", "phone"),
    ("Account tour", "bulb"),
    ("FAQ", "question"),
]

TABS = [
    ("Check up", "heart"),
    ("Medications", "pills"),
    ("Orders", "box"),
    ("Tasks", "task"),
]

SETTINGS_ITEMS = [
    ("Profile settings", "person"),
    ("Account settings", "lock"),
    ("Payment method", "card"),
    ("Promotions", "tag"),
    ("Referral code", "ticket"),
    ("Notifications", "bell"),
    ("Account tour", "bulb"),
    ("Info and legal", "doc"),
]

NOTIFICATIONS = [
    ("Weekly check-in is ready", "Foot-care week. Takes 2 minutes."),
    ("Reminder", "Check your blood sugar at 8:00 AM."),
    ("Order shipped", "Order #1057 is on its way."),
]

ORDERS = [
    ("Order #1063", "Glucose sensors  ·  Processing", "Processing"),
    ("Order #1057", "Test strips  ·  Shipped Nov 20", "Shipped"),
    ("Order #1042", "Monthly refill  ·  Delivered Nov 18", "Delivered"),
]
