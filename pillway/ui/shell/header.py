"""The top header: page title, EN/FR toggle, "Talk to a pharmacist", bell, card and profile button.

Called by: PillwayApp.render(). The pharmacist's patient screen has its own header
(ui/pharmacist/patient_detail.py).
The language toggle and "Talk to a pharmacist" are always visible on the patient side.
"""

from config import get_settings

from ...storage.patient_store import display_name, initials
from ..theme import BORDER, INK, RED, TEXT_DARK, TEXT_MUTED, WHITE


class HeaderMixin:
    def draw_header(self):
        if self.role == "pharmacist" and self.section == "Dashboard" and self.doctor_workspace_open:
            self.draw_detail_header()
            return
        c, w = self.c, self.w
        top, size = self.S(18), self.S(54)
        cy = top + size / 2
        title = {"Dashboard": "Dashboard" if self.role == "patient" else "Patients"}.get(self.section)
        if title:
            self.text(self.sw + self.S(28), cy, title, 28, TEXT_DARK, "bold")

        if self.role == "patient" and self.record:
            name, short = display_name(self.record), initials(self.record)
        else:
            name, short = "Pharmacist", "PH"
        self.draw_icon("chev_down", w - self.S(34), cy, self.S(22), INK, "profile")
        name_item = self.text(w - self.S(54), cy, name, 17, INK, "bold", anchor="e", tag="profile")
        r = self.S(27)
        ax = c.bbox(name_item)[0] - self.S(14) - r
        c.create_oval(ax - r, cy - r, ax + r, cy + r, fill="#080b32", outline="#080b32", tags="profile")
        self.text(ax, cy, short, 16, WHITE, "bold", anchor="center", tag="profile")
        self.clickable("profile", lambda: self.toggle_dropdown("profile"))
        self.profile_box = (ax - r, top + size)

        right = ax - r - self.S(24)
        if self.role == "patient":
            self.beveled_button(right - size, top, right, top + size, "card", "payments", lambda: self.go("Payments"))
            right -= size + self.S(14)
        self.beveled_button(right - size, top, right, top + size, "bell", "bell",
                            lambda: self.toggle_dropdown("notifications"))
        if self.unread_notifications():
            d = self.S(7)
            c.create_oval(right - d * 1.6, top - d * 0.4, right + d * 0.4, top + d * 1.6,
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
        x1 = right - text_w - self.S(64)
        self.rrect(x1, cy - self.S(25), right, cy + self.S(25), self.S(25), fill=RED, outline="", tags=tag)
        self.draw_icon("phone", x1 + self.S(24), cy, self.S(20), WHITE, tag, bg=RED)
        self.text(x1 + self.S(42), cy, label, 14, WHITE, "bold", tag=tag)
        self.clickable(tag, self.talk_to_pharmacist)
        return x1

    def _draw_language_toggle(self, right, cy):
        width, height = self.S(108), self.S(44)
        x1 = right - width
        self.rrect(x1, cy - height / 2, right, cy + height / 2, height / 2, fill="#eef1f6", outline=BORDER)
        for index, code in enumerate(("en", "fr")):
            sx1 = x1 + self.S(4) + index * (width - self.S(8)) / 2
            sx2 = sx1 + (width - self.S(8)) / 2
            tag = f"lang::{code}"
            selected = self.lang == code
            self.rrect(sx1, cy - height / 2 + self.S(4), sx2, cy + height / 2 - self.S(4), height / 2,
                       fill=INK if selected else "#eef1f6", outline="", tags=tag)
            self.text((sx1 + sx2) / 2, cy, code.upper(), 14, WHITE if selected else TEXT_MUTED, "bold",
                      anchor="center", tag=tag)
            self.clickable(tag, lambda lang=code: self.set_language(lang))
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
