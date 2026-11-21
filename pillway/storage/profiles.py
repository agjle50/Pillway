"""Demo accounts shown in Manage profiles and on the sign-in screen (made up, no real people).

Called by: storage/profile_store.py when no saved profiles exist yet.
A patient account points at a patient record ("record_id") in the shared patient store.
"""

PROFILES = [
    {
        "id": "patient",
        "name": "Maria Rossi",
        "role": "Patient",
        "record_id": "maria",
        "description": "Demo patient: newly diagnosed type 2 diabetes and high blood pressure.",
    },
    {
        "id": "doctor",
        "name": "Pharmacist account",
        "role": "Pharmacist",
        "description": "Review flags, chats, calls and care plans for all patients.",
    },
]
