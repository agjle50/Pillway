"""The top header: page title, bell, card and profile button.

Called by: PillwayApp.render().
"""


from ..theme import (
    INK,
    RED,
    TEXT_DARK,
    WHITE,
)


class HeaderMixin:
    def draw_header(self):
        if (
            self.section == "Dashboard"
            and self.profiles[self.active_profile_id]["role"] == "Doctor"
            and self.doctor_workspace_open
        ):
            self.draw_doctor_header()
            return
        c, w = self.c, self.w
        top = self.S(18)
        size = self.S(54)

        if self.section == "Dashboard":
            self.text(self.sw + self.S(28), top + size / 2, "Dashboard", 28, TEXT_DARK, "bold")

        # profile (circle avatar + name + chevron), right aligned
        cy = top + size / 2
        self.draw_icon("chev_down", w - self.S(34), cy, self.S(22), INK, "profile")
        name = self.text(w - self.S(54), cy, "Team AGILE", 17, INK, "bold", anchor="e", tag="profile")
        nx1 = c.bbox(name)[0]
        r = self.S(27)
        ax = nx1 - self.S(14) - r
        c.create_oval(ax - r, cy - r, ax + r, cy + r, fill="#080b32", outline="#080b32", tags="profile")
        self.text(ax, cy, "T A", 16, WHITE, "bold", anchor="center", tag="profile")
        self.clickable("profile", lambda: self.toggle_dropdown("profile"))

        # credit card (payments) and bell (notifications): beveled rectangles
        card_x2 = ax - r - self.S(24)
        self.beveled_button(card_x2 - size, top, card_x2, top + size, "card", "payments",
                            lambda: self.go("Payments"))
        bell_x2 = card_x2 - size - self.S(14)
        self.beveled_button(bell_x2 - size, top, bell_x2, top + size, "bell", "bell",
                            lambda: self.toggle_dropdown("notifications"))
        # unread dot
        d = self.S(7)
        c.create_oval(bell_x2 - d * 1.6, top - d * 0.4, bell_x2 + d * 0.4, top + d * 1.6,
                      fill=RED, outline=WHITE, width=self.S(2), tags="bell")
        self.bell_box = (bell_x2 - size, top + size)
        self.profile_box = (ax - r, top + size)
