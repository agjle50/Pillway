"""The sidebar items, top tabs and settings rows (names + icon names).

Read by: ui/shell/sidebar.py, ui/patient/dashboard.py, ui/patient/settings.py.
To add a sidebar item: add ("Label", "icon_name") here, then (optionally) a screen
for it in ui/app_router.py. Items without a screen open a "Coming soon" page.
"""

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

PHARMACIST_NAV_ITEMS = [
    ("Dashboard", "grid"),
    ("Settings", "gear"),
    ("Manage profiles", "person"),
    None,
    ("Contact us", "phone"),
    ("FAQ", "question"),
]

# Top icon tab bar on the patient dashboard. Labels are translated with data/french_strings.json.
TABS = [
    ("Check up", "heart", "tab.check_up"),
    ("Medications", "pills", "tab.medications"),
    ("Orders", "box", "tab.orders"),
    ("Tasks", "task", "tab.tasks"),
    ("Care plan", "clipboard", "tab.care_plan"),
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
