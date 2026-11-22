"""Simple information pages that used to say "Coming soon".

Called by: PillwayApp.render() for See a doctor, Contact us, Account tour, Payments and the
Settings rows (Profile settings, Account settings, Payment method, Promotions, Referral code,
Notifications, Info and legal).
The words live in data/info_pages.json (made-up demo details), so anyone can edit them
without touching code. Notifications has real on/off switches (kept for this session).
Each page scrolls if it doesn't fit the window.
"""

import json

from config import get_settings

from ...storage.patient_store import display_name
from ..theme import BORDER, INK, RED, TEXT_MUTED, WHITE

SETTINGS_PAGES = {"Profile settings", "Account settings", "Payment method", "Promotions",
                  "Referral code", "Notifications", "Info and legal"}

# Patient-only buttons are hidden on the pharmacist side.
PATIENT_ONLY_ACTIONS = {"talk_to_pharmacist", "open_chat", "open_call"}
PATIENT_ONLY_PAGES = {"Tasks"}

NOTIFICATION_CHOICES = [
    ("orders", "Order and delivery updates", True),
    ("check_ins", "Check-in messages from the care assistant", True),
    ("care_plan", "Care plan ready or updated", True),
    ("pharmacist", "Messages from your pharmacist", True),
    ("promotions", "Promotions and offers", False),
]


def load_pages():
    path = get_settings().path("data/info_pages.json")
    return json.loads(path.read_text(encoding="utf-8"))


def has_info_page(title):
    return title == "Notifications" or title in load_pages()


class InfoPagesMixin:
    def _info_values(self):
        if self.role == "patient" and self.record:
            name = display_name(self.record)
            language = "Français" if self.lang == "fr" else "English"
        else:
            name, language = "Pharmacist (demo)", "English"
        first = name.split()[0].lower() if name else "demo"
        return {"name": name, "language": language, "email": f"{first}.demo@example.com",
                "referral": f"{first.upper()}-2026"}

    def draw_info_page(self, title):
        back_to = "Settings" if title in SETTINGS_PAGES else "Dashboard"
        y = self.page_title(title, back_to=back_to)
        x1, x2 = self.sw + self.S(28), self.w - self.S(28)
        canvas = self.make_scroll(x1, y + self.S(8), x2, self.h - self.S(10))
        width = min(x2 - x1 - self.S(24), self.S(760))
        if title == "Notifications":
            bottom = self._draw_notification_switches(canvas, width)
        else:
            pages = load_pages()
            cards = pages.get(title, [])
            if isinstance(cards, str):  # an alias, e.g. "Payment method" -> "Payments"
                cards = pages.get(cards, [])
            bottom = self._draw_info_cards(canvas, cards, width)
        self.finish_scroll(canvas, bottom + self.S(30))

    def _draw_info_cards(self, canvas, cards, width):
        values = self._info_values()
        y, pad = self.S(16), self.S(22)
        for card in cards:
            top = y
            y += pad
            item = self.tx(canvas, pad, y, card["title"], 17, INK, "bold", width=width - 2 * pad)
            y = self.bottom_of(canvas, item) + self.S(10)
            if card.get("text"):
                item = self.tx(canvas, pad, y, card["text"].format_map(values), 13, TEXT_MUTED,
                               width=width - 2 * pad)
                y = self.bottom_of(canvas, item) + self.S(12)
            label_w = min(self.S(230), width * 0.38)
            for label, value in card.get("rows", []):
                canvas.create_line(pad, y, width - pad, y, fill=BORDER)
                y += self.S(10)
                self.tx(canvas, pad, y, label, 13, TEXT_MUTED, width=label_w - self.S(10))
                item = self.tx(canvas, pad + label_w, y, value.format_map(values), 14, INK, "bold",
                               width=width - 2 * pad - label_w)
                y = self.bottom_of(canvas, item) + self.S(10)
            buttons = [b for b in card.get("buttons", []) if self._button_allowed(b)]
            if buttons:
                y += self.S(6)
                bx = pad
                for button in buttons:
                    bx = self.btn(canvas, bx, y, button["label"], lambda b=button: self._info_button(b),
                                  kind=button.get("kind", "primary"), size=13, height=self.S(44)) + self.S(12)
                y += self.S(44)
            y += pad
            back = self.rr(canvas, 0, top, width, y, self.S(16), fill=WHITE, outline=BORDER,
                           width=max(1, self.S(1.2)))
            canvas.tag_lower(back)  # the white card goes behind its text
            y += self.S(16)
        return y

    def _button_allowed(self, button):
        if self.role == "patient":
            return True
        return button.get("action") not in PATIENT_ONLY_ACTIONS and button.get("go") not in PATIENT_ONLY_PAGES

    def _info_button(self, button):
        if "toast" in button:
            self.flash(button["toast"])
        elif "go" in button:
            self.go(button["go"])
        else:
            action = button.get("action")
            if action == "talk_to_pharmacist":
                self.talk_to_pharmacist()
            elif action == "open_chat":
                self.go("Dashboard")
                self.open_profile_chat()
            elif action == "open_call":
                self.go("Dashboard")
                self.checkup_choice("Call")
            elif action == "sign_out":
                self.sign_out()
            elif action == "copy_referral":
                code = self._info_values()["referral"]
                self.clipboard_clear()
                self.clipboard_append(code)
                self.flash(f"Copied {code}")

    def _draw_notification_switches(self, canvas, width):
        prefs = self.notification_prefs
        pad, row = self.S(22), self.S(64)
        y = self.S(16)
        top = y
        self.tx(canvas, pad, y + pad, "Choose what we notify you about", 17, INK, "bold")
        y += pad + self.S(40)
        for key, label, default in NOTIFICATION_CHOICES:
            on = prefs.setdefault(key, default)
            canvas.create_line(pad, y, width - pad, y, fill=BORDER)
            tag = f"notif::{key}"
            canvas.create_rectangle(pad, y + 1, width - pad, y + row - 1, fill=WHITE, outline=WHITE, tags=tag)
            self.tx(canvas, pad, y + row / 2, label, 14, INK, anchor="w", tag=tag,
                    width=width - 2 * pad - self.S(80))
            sx2, sy = width - pad, y + row / 2
            sx1, h = sx2 - self.S(56), self.S(30)
            self.rr(canvas, sx1, sy - h / 2, sx2, sy + h / 2, h / 2, fill=RED if on else "#c7cbd4",
                    outline="", tags=tag)
            knob = sx2 - h / 2 if on else sx1 + h / 2
            r = h / 2 - self.S(3)
            canvas.create_oval(knob - r, sy - r, knob + r, sy + r, fill=WHITE, outline="", tags=tag)
            self.bind_click(canvas, tag, lambda k=key: self._toggle_notification(k))
            y += row
        y += self.S(10)
        item = self.tx(canvas, pad, y, "Changes are kept while the app is open (demo).", 12, TEXT_MUTED,
                       width=width - 2 * pad)
        y = self.bottom_of(canvas, item) + pad
        back = self.rr(canvas, 0, top, width, y, self.S(16), fill=WHITE, outline=BORDER, width=max(1, self.S(1.2)))
        canvas.tag_lower(back)
        return y

    def _toggle_notification(self, key):
        self.notification_prefs[key] = not self.notification_prefs.get(key)
        self.render()
