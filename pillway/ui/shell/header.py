"""The top header: page title, EN/FR toggle, "Talk to a pharmacist", bell, card and profile button.

Called by: PillwayApp.render(). The pharmacist's patient screen has its own header
(ui/pharmacist/patient_detail.py).
The language toggle and "Talk to a pharmacist" are always visible on the patient side.
"""

from config import get_settings

from ...storage.patient_store import display_name, initials
from ..theme import BORDER, HOVER, INK, NAVY, RADIUS, RED, TEXT_DARK, TEXT_MUTED, WHITE


class HeaderMixin:
    def draw_header(self):
        if self.role == "pharmacist" and self.section == "Dashboard" and self.doctor_workspace_open:
            self.draw_detail_header()
            return
        c, w = self.c, self.w
        size = self.S(44)
        cy = self.S(46)
        top = cy - size / 2
        title = {"Dashboard": "Dashboard" if self.role == "patient" else "Patients"}.get(self.section)
        if title:
            self.text(self.sw + self.S(26), cy, self.t(title), 25, TEXT_DARK, "bold")

        if self.role == "patient" and self.record:
            name, short = display_name(self.record), initials(self.record)
        else:
            profile = self.profiles.get(self.active_profile_id, {}) if hasattr(self, "profiles") else {}
            name = profile.get("name") or "Pharmacist"
            short = "".join(part[:1] for part in name.split()[:2]).upper() or "PH"
        # account button: navy initials circle, name, chevron (opens the account menu)
        self.draw_icon("chev_down", w - self.S(30), cy, self.S(18), INK, "profile")
        name_item = self.text(w - self.S(46), cy, name, 15, INK, anchor="e", tag="profile")
        r = self.S(20)
        ax = c.bbox(name_item)[0] - self.S(10) - r
        self.circle(c, ax - r, cy - r, ax + r, cy + r, fill=NAVY, tags="profile")
        self.text(ax, cy, short, 14, WHITE, "bold", anchor="center", tag="profile")
        self.clickable("profile", lambda: self.toggle_dropdown("profile"))
        self.profile_box = (ax - r, cy + size / 2)

        right = ax - r - self.S(30)
        if self.role == "patient":
            self.beveled_button(right - size, top, right, top + size, "card", "payments", lambda: self.go("Payments"))
            right -= size + self.S(14)
        self.beveled_button(right - size, top, right, top + size, "bell", "bell",
                            lambda: self.toggle_dropdown("notifications"))
        if self.unread_notifications():
            d = self.S(6)
            self.circle(c, right - d * 1.8, top - d * 0.2, right + d * 0.2, top + d * 1.8,
                        fill=RED, outline=WHITE, width=self.S(2), tags="bell")
        self.bell_box = (right - size, top + size)
        right -= size + self.S(18)
        if self.role == "patient":
            right = self._draw_talk_button(right, cy)
            self._draw_language_toggle(right - self.S(14), cy)

    def _draw_talk_button(self, right, cy):
        tag = "talk_to_pharmacist"
        label = self.t("talk_to_pharmacist")
        probe = self.c.create_text(0, -500, text=label, font=self.font(14, "bold"))
        text_w = self.c.bbox(probe)[2] - self.c.bbox(probe)[0]
        self.c.delete(probe)
        x1 = right - text_w - self.S(60)
        h = self.S(22)
        self.rrect(x1, cy - h, right, cy + h, self.S(RADIUS), fill=RED, tags=(tag, f"{tag}::bg"))
        self.draw_icon("phone", x1 + self.S(22), cy, self.S(18), WHITE, tag, bg=RED)
        self.text(x1 + self.S(40), cy, label, 14, WHITE, "bold", tag=tag)
        self.clickable(tag, self.talk_to_pharmacist)
        self._hover_shade(tag, f"{tag}::bg", RED, "#c7361f")
        return x1

    def _draw_language_toggle(self, right, cy):
        """EN | FR segmented control: outlined like the icon buttons, selected half in navy."""
        width, height = self.S(100), self.S(44)
        x1 = right - width
        self.rrect(x1, cy - height / 2, right, cy + height / 2, self.S(RADIUS), fill=WHITE, outline=BORDER,
                   width=self.S(1.2))
        for index, code in enumerate(("en", "fr")):
            sx1 = x1 + self.S(4) + index * (width - self.S(8)) / 2
            sx2 = sx1 + (width - self.S(8)) / 2
            tag = f"lang::{code}"
            selected = self.lang == code
            fill = NAVY if selected else WHITE
            self.rrect(sx1, cy - height / 2 + self.S(4), sx2, cy + height / 2 - self.S(4), self.S(RADIUS - 2),
                       fill=fill, outline=fill, tags=(tag, f"{tag}::bg"))
            self.text((sx1 + sx2) / 2, cy, code.upper(), 14, WHITE if selected else TEXT_DARK, "bold",
                      anchor="center", tag=tag)
            self.clickable(tag, lambda lang=code: self.set_language(lang))
            if not selected:
                self._hover_shade(tag, f"{tag}::bg", WHITE, HOVER)
        if self.lang == "fr" and get_settings().french.show_translation_review_status:
            from ...core.content import load
            key = "translation.ok" if load("french_strings").get("reviewed") else "translation.review"
            self.text(x1 + width / 2, cy + height / 2 + self.S(12), self.t(key), 9, TEXT_MUTED, anchor="center")

    def unread_notifications(self):
        if self.role == "pharmacist":
            records = self.store.all()
            return any(
                request["status"] == "open"
                for record in records
                for request in record["pharmacist_requests"]
            ) or any(
                flag["status"] == "open" and flag["tier"] == 1
                for record in records
                for flag in record["flags"]
            )
        return bool(self.notifications)

    def set_language(self, lang):
        self.lang = lang
        if self.role == "patient":
            self.service.set_language(self.patient_id, lang)
        self.render()

    def talk_to_pharmacist(self):
        self.service.request_pharmacist(self.patient_id)
        self.flash("A pharmacist will contact you." if self.lang == "en" else "Un pharmacien communiquera avec vous.")
