"""Sign-in screen: two big buttons, Patient or Pharmacist (made-up demo logins, no real accounts).

Called by: PillwayApp.render() when nobody is signed in, and "Sign out" in the profile menu.
"""

from config import get_settings

from .theme import INK, NAVY, NAVY_DARK, RED, TEXT_MUTED, WHITE


class LoginMixin:
    def draw_login(self):
        settings = get_settings()
        c, w, h = self.c, self.w, self.h
        left = w * 0.42
        c.create_rectangle(0, 0, left, h, fill=NAVY, outline=NAVY)
        c.create_rectangle(0, 0, left, self.S(100), fill=NAVY_DARK, outline=NAVY_DARK)
        self.text(left / 2, self.S(50), settings.branding.app_name, 38, WHITE, "bold", anchor="center")
        self.c.create_text(left / 2, h * 0.45, text="Care support any time.\nAnything urgent reaches a pharmacist at once.",
                           fill="#c8cede", font=self.font(18), justify="center", width=left - self.S(60))
        mode = ("Demo mode: scripted replies, no internet needed" if not self.service.brain.live
                else f"Live AI: {settings.ai.chat_model}")
        self.text(left / 2, h - self.S(40), mode, 12, "#9da9dc", anchor="center")

        cx = left + (w - left) / 2
        self.text(cx, self.S(150), "Sign in", 30, INK, "bold", anchor="center")
        self.text(cx, self.S(190), "Choose who you are. These are made-up demo accounts.", 14, TEXT_MUTED, anchor="center")
        card_w, card_h = min(self.S(520), w - left - self.S(80)), self.S(130)
        cards = [("patient", "I'm a patient", f"Maria Rossi  ·  login: {settings.patient.demo_username} / "
                  f"{settings.patient.demo_password}", "person"),
                 ("pharmacist", "I'm a pharmacist", f"Pharmacist dashboard  ·  login: {settings.pharmacist.demo_username}"
                  f" / {settings.pharmacist.demo_password}", "stethoscope")]
        for index, (role, title, sub, icon) in enumerate(cards):
            y = self.S(240) + index * (card_h + self.S(26))
            tag = f"login::{role}"
            self.rrect(cx - card_w / 2, y, cx + card_w / 2, y + card_h, self.S(28), fill="#eceef8",
                       outline="#eceef8", width=self.S(1.5), tags=tag)
            ix = cx - card_w / 2 + self.S(62)
            self.c.create_oval(ix - self.S(34), y + card_h / 2 - self.S(34), ix + self.S(34), y + card_h / 2 + self.S(34),
                               fill=RED if role == "patient" else NAVY, outline="", tags=tag)
            self.draw_icon(icon, ix, y + card_h / 2, self.S(32), WHITE, tag, bg=RED if role == "patient" else NAVY)
            self.text(ix + self.S(60), y + card_h / 2 - self.S(18), title, 26, INK, "bold", tag=tag)
            self.text(ix + self.S(60), y + card_h / 2 + self.S(22), sub, 13, TEXT_MUTED, tag=tag)
            self.clickable(tag, lambda r=role: self.sign_in(r))
        self.text(cx, self.S(240) + 2 * (card_h + self.S(26)) + self.S(20),
                  "Tip: run  python Pillway.py --role patient  and  --role pharmacist  in two windows side by side.",
                  11, TEXT_MUTED, anchor="center")

    def sign_in(self, role):
        self.role = role
        self.section, self.tab, self.dropdown = "Dashboard", "Check up", None
        self.chat_open = self.call_open = False
        self.intake_open = self.intake_later = False
        self.check_in_popup_dismissed = False
        self.intake_form = None
        if role == "patient":
            profile = self.profiles.get(self.active_profile_id, {})
            if profile.get("role") != "Patient":
                self.active_profile_id = next(pid for pid, p in self.profiles.items() if p["role"] == "Patient")
                profile = self.profiles[self.active_profile_id]
            self.patient_id = profile.get("record_id") or self.active_profile_id
            self.refresh_record()
            self.select_tab("Check up")
            return
        profile = self.profiles.get(self.active_profile_id, {})
        if profile.get("role") != "Pharmacist":
            self.active_profile_id = next(pid for pid, p in self.profiles.items() if p["role"] == "Pharmacist")
        self.doctor_workspace_open = False
        self.render()

    def sign_out(self):
        if self.call_open:
            self.close_call_preview()
        elif self.chat_open:
            self._end_chat_session()
        self._stop_call_input()
        self.role = None
        self.dropdown = None
        self.chat_open = self.call_open = False
        self.render()
