"""Canvas views for the Pillway dashboard and secondary pages."""

import os
import textwrap
import tkinter as tk

from .constants import (
    BORDER,
    INK,
    NAVY,
    NAVY_DARK,
    ORDERS,
    RED,
    SETTINGS_ITEMS,
    SHADOW,
    SOFT_BLUE,
    TEXT_DARK,
    TEXT_MUTED,
    TEXT_OFF,
    TOGGLE_OFF,
    TABS,
    VIRTUAL_ASSISTANT_POPUP_TEXT,
    WHITE,
)


class DashboardViewMixin:
    def panel_box(self):
        return (self.sw + self.S(14), self.S(92), self.w - self.S(14), self.h - self.S(14))

    def draw_dashboard(self):
        px1, py1, px2, py2 = self.panel_box()
        self.rrect(px1, py1, px2, py2, self.S(16), fill=WHITE, outline=BORDER, width=self.S(1.2))
        if self.chat_open:
            self.draw_chat_page(px1, py1, px2, py2)
            return
        if self.prescription_flow:
            self.draw_prescription_page(px1, py1, px2, py2)
            return
        pcx = (px1 + px2) / 2

        gap = self.S(150)
        for i, (name, icon) in enumerate(TABS):
            x = pcx + (i - (len(TABS) - 1) / 2) * gap
            tag = f"tab::{name}"
            sel = name == self.tab
            col = RED if sel else TEXT_MUTED
            self.c.create_rectangle(x - gap / 2 + self.S(6), py1 + self.S(8), x + gap / 2 - self.S(6),
                                    py1 + self.S(96), fill=WHITE, outline=WHITE, tags=tag)
            self.draw_icon(icon, x, py1 + self.S(40), self.S(32), col, tag)
            self.text(x, py1 + self.S(76), name, 14, col, "bold" if sel else "normal",
                      anchor="center", tag=tag)
            if sel:
                self.rrect(x - self.S(26), py1 + self.S(92), x + self.S(26), py1 + self.S(96),
                           self.S(2), fill=RED, outline="", tags=tag)
            self.clickable(tag, lambda n=name: self.select_tab(n))
        self.c.create_line(px1, py1 + self.S(98), px2, py1 + self.S(98), fill=BORDER)

        y = py1 + self.S(118)
        if self.banner and self.tab != "Medications":
            bw = min(self.S(700), px2 - px1 - self.S(60))
            bx1, bx2 = pcx - bw / 2, pcx + bw / 2
            self.rrect(bx1, y, bx2, y + self.S(56), self.S(14), fill=NAVY_DARK, outline="")
            self.text(bx1 + self.S(22), y + self.S(28), VIRTUAL_ASSISTANT_POPUP_TEXT, 14, WHITE)
            self.c.create_oval(bx2 - self.S(36), y + self.S(14), bx2 - self.S(8), y + self.S(42),
                               fill=NAVY_DARK, outline="", tags="banner_x")
            self.draw_icon("close", bx2 - self.S(22), y + self.S(28), self.S(16), WHITE, "banner_x")
            self.clickable("banner_x", self.close_banner)
            y += self.S(80)
        else:
            y += self.S(10)

        content_w = min(self.S(820), px2 - px1 - self.S(80))
        x1, x2 = pcx - content_w / 2, pcx + content_w / 2
        {"Check up": self.draw_checkup, "Medications": self.draw_medications,
         "Orders": self.draw_orders, "Tasks": self.draw_tasks}[self.tab](x1, x2, y)

    def draw_checkup(self, x1, x2, y):
        self.text((x1 + x2) / 2, y + self.S(14), "How would you like to check in?", 20, INK,
                  "bold", anchor="center")
        y += self.S(48)
        bars = [("Call", "phone", "Talk to a Pillway pharmacist now"),
                ("Chat", "chat", "Message your care assistant, any time")]
        bh = self.S(104)
        for i, (title, icon, sub) in enumerate(bars):
            off = (1 - self.anim) * self.S(70) * (i + 1)
            by = y + i * (bh + self.S(22)) + off
            tag = f"bar::{title}"
            self.rrect(x1, by + self.S(4), x2, by + bh + self.S(4), self.S(20),
                       fill=SHADOW, outline="", tags=tag)
            self.rrect(x1, by, x2, by + bh, self.S(20), fill=WHITE,
                       outline=BORDER, width=self.S(1.2), tags=tag)
            cx, cy, r = x1 + self.S(56), by + bh / 2, self.S(30)
            self.c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=RED, outline="", tags=tag)
            self.draw_icon(icon, cx, cy, self.S(28), WHITE, tag, bg=RED)
            self.text(x1 + self.S(106), cy - self.S(14), title, 26, INK, "bold", tag=tag)
            self.text(x1 + self.S(106), cy + self.S(20), sub, 14, TEXT_MUTED, tag=tag)
            self.draw_icon("chev_right", x2 - self.S(34), cy, self.S(24), TEXT_MUTED, tag)
            self.clickable(tag, lambda t=title: self.checkup_choice(t))
        if self.status and self.anim >= 1:
            self.text((x1 + x2) / 2, y + 2 * bh + self.S(60),
                      self.status, 14, TEXT_MUTED, anchor="center")

    def draw_medications(self, x1, x2, y):
        if not self.prescriptions:
            cx = (x1 + x2) / 2
            bottom = self.h - self.S(30)
            cy = (y + bottom) / 2
            self.text(cx, cy - self.S(38), "Let's add your first prescription!", 20,
                      TEXT_DARK, anchor="center")
            bw, bh = min(self.S(440), x2 - x1), self.S(62)
            bx1, bx2 = cx - bw / 2, cx + bw / 2
            by1, by2 = cy, cy + bh
            self.rrect(bx1, by1, bx2, by2, self.S(14), fill=RED, outline="", tags="addrx")
            self.draw_icon("plus", cx - self.S(52), (by1 + by2) / 2, self.S(20), WHITE, "addrx")
            self.text(cx - self.S(34), (by1 + by2) / 2, "Add prescription", 18,
                      WHITE, "bold", tag="addrx")
            self.clickable("addrx", self.add_prescription)
        else:
            self.list_header(x1, x2, y, "Your medications")
            y += self.S(40)
            for name in self.prescriptions:
                self.text(x1 + self.S(6), y + self.S(30), name, 20, INK)
                self.text(x1 + self.S(6), y + self.S(55),
                          "Prescription added today", 13, TEXT_MUTED)
                y += self.S(76)
                self.c.create_line(x1, y, x2, y, fill=BORDER)

    def draw_chat_page(self, x1, y1, x2, y2):
        c = self.c
        c.create_rectangle(x1 + self.S(1), y1 + self.S(1), x2 - self.S(1), y2 - self.S(1),
                           fill="#f3f3f5", outline="")
        header_y = y1 + self.S(54)
        c.create_rectangle(x1 + self.S(12), header_y - self.S(20), x1 + self.S(48),
                           header_y + self.S(20), fill="#f3f3f5", outline="#f3f3f5", tags="chat_back")
        self.draw_icon("back", x1 + self.S(30), header_y, self.S(24), INK, "chat_back")
        self.text(x1 + self.S(62), header_y, "Chat with Pillway", 20, INK, "bold")
        self.clickable("chat_back", self.close_chat)

        date_y = y1 + self.S(112)
        self.rrect((x1 + x2) / 2 - self.S(70), date_y - self.S(18),
                   (x1 + x2) / 2 + self.S(70), date_y + self.S(18), self.S(18),
                   fill=WHITE, outline=BORDER)
        self.text((x1 + x2) / 2, date_y, "TODAY", 12, TEXT_MUTED, "bold", anchor="center")

        messages = self.chat_messages or [
            ("Pillway", "Hi! How can we help you today?")
        ]
        y = date_y + self.S(32)
        max_width = (x2 - x1) * 0.72
        for sender, message in messages:
            lines = textwrap.wrap(message, max(12, int(max_width / self.S(9))))
            bubble_h = self.S(52 + max(1, len(lines)) * 20)
            bubble_w = max_width
            bx1 = x2 - self.S(28) - bubble_w if sender == "You" else x1 + self.S(28)
            bx2 = bx1 + bubble_w
            bg = "#e7e8ee" if sender == "You" else WHITE
            self.rrect(bx1, y, bx2, y + bubble_h, self.S(18), fill=bg,
                       outline="" if sender == "You" else BORDER)
            self.text(bx1 + self.S(18), y + self.S(18), sender, 14, INK, "bold")
            self.text(bx2 - self.S(18), y + self.S(18), "now", 12, TEXT_MUTED, anchor="e")
            self.text(bx1 + self.S(18), y + self.S(42), "\n".join(lines), 14, TEXT_DARK)
            y += bubble_h + self.S(16)

        input_h = self.S(58)
        input_y = y2 - self.S(30) - input_h
        self.rrect(x1 + self.S(28), input_y, x2 - self.S(28), input_y + input_h,
                   self.S(16), fill=WHITE, outline=BORDER, width=self.S(1.2))
        entry = tk.Entry(self, relief="flat", bd=0, font=self.font(14), fg=TEXT_DARK,
                         insertbackground=INK)
        entry.insert(0, self.chat_draft or self.chat_placeholder)
        if not self.chat_draft:
            entry.configure(fg=TEXT_MUTED)
        entry.bind("<FocusIn>", self.chat_focus_in)
        entry.bind("<FocusOut>", self.chat_focus_out)
        entry.bind("<Return>", self.send_chat_message)
        self.chat_entry = entry
        c.create_window(x1 + self.S(52), input_y + input_h / 2,
                        width=max(20, x2 - x1 - self.S(160)), height=self.S(34),
                        window=entry, anchor="w")
        send_x = x2 - self.S(58)
        c.create_oval(send_x - self.S(21), input_y + input_h / 2 - self.S(21),
                      send_x + self.S(21), input_y + input_h / 2 + self.S(21),
                      fill=RED, outline="", tags="chat_send")
        self.draw_icon("send", send_x, input_y + input_h / 2, self.S(20), WHITE,
                       "chat_send", bg=RED)
        self.clickable("chat_send", self.send_chat_message)

    def draw_prescription_page(self, x1, y1, x2, y2):
        c = self.c
        left, right = x1 + self.S(32), x2 - self.S(32)
        top = y1 + self.S(42)
        self.text(left, top, "How would you like to add your prescription?",
                  26, "#3d3d3d", "bold")
        close_x = right - self.S(8)
        self.draw_icon("close", close_x, top, self.S(24), INK, "prescription_close")
        self.clickable("prescription_close", self.close_prescription_flow)

        if self.prescription_stage is None:
            self.text(left, top + self.S(42), "Please select your preferred option:",
                      24, "#3d3d3d")
            card1_y = top + self.S(88)
            self._prescription_option_card(
                left, right, card1_y, self.S(114), "Transfer", "transfer",
                "Have prescriptions at a different pharmacy? Request to transfer",
                "some or all prescriptions and deliver them to your doorstep."
            )
            card2_y = card1_y + self.S(132)
            self._prescription_option_card(
                left, right, card2_y, self.S(198), "Upload Photo", "upload",
                "Have a written prescription? Upload a photo to have it filled",
                "and delivered."
            )
            self.c.create_line(left, card2_y + self.S(114), right, card2_y + self.S(114),
                               fill=BORDER, dash=(3, 3))
            self.text(left + self.S(20), card2_y + self.S(150),
                      "Note:", 17, "#3d3d3d", "bold")
            self.text(left + self.S(61), card2_y + self.S(150),
                      "We need to contact your prescriber to verify the information",
                      16, "#3d3d3d")
            self.text(left + self.S(20), card2_y + self.S(174),
                      "before we can fill the prescription; this may take some time.",
                      16, "#3d3d3d")
            footer_y = card2_y + self.S(224)
            self.c.create_line(left, footer_y, right, footer_y, fill=BORDER)
            self.draw_icon("phone", left + self.S(24), footer_y + self.S(38),
                           self.S(24), "#222222", "schedule_call")
            self.text(left + self.S(54), footer_y + self.S(38),
                      "Prefer to transfer over the phone?", 17, "#3d3d3d")
            self.text(left + self.S(386), footer_y + self.S(38),
                      "Schedule a call", 17, RED, "bold", tag="schedule_call")
            self.text(left + self.S(518), footer_y + self.S(38),
                      "to have a team", 17, "#3d3d3d")
            self.text(left + self.S(54), footer_y + self.S(62),
                      "member complete the steps.", 17, "#3d3d3d")
            self.clickable("schedule_call", lambda: self.set_prescription_status(
                "A team member can help you transfer your prescription by phone."
            ))
            return

        method = self.prescription_stage
        self.text(left, top + self.S(52), f"{method} a prescription", 20, RED, "bold")
        self.text(left, top + self.S(90), "Medication name", 16, TEXT_MUTED)
        entry = tk.Entry(self, relief="flat", bd=0, font=self.font(16), fg=TEXT_DARK,
                         insertbackground=INK)
        entry.insert(0, self.prescription_draft)
        self.prescription_entry = entry
        self.rrect(left, top + self.S(108), right, top + self.S(150),
                   self.S(8), fill="", outline=BORDER, width=self.S(1))
        c.create_window(left + self.S(8), top + self.S(128),
                        width=right - left - self.S(16), height=self.S(40),
                        window=entry, anchor="w")

        action_y = top + self.S(174)
        if method == "Upload Photo":
            selected = os.path.basename(self.prescription_photo) if self.prescription_photo else "Choose a photo"
            self.rrect(left, action_y, left + self.S(240), action_y + self.S(46),
                       self.S(8), fill=WHITE, outline=RED, width=self.S(1.2), tags="choose_photo")
            self.text(left + self.S(120), action_y + self.S(23), selected, 15, RED,
                      "bold", anchor="center", tag="choose_photo")
            self.clickable("choose_photo", self.choose_prescription_photo)
            action_y += self.S(64)

        bx1, bx2 = left, left + self.S(220)
        self.rrect(bx1, action_y, bx2, action_y + self.S(48),
                   self.S(9), fill=RED, outline="", tags="save_prescription")
        self.text((bx1 + bx2) / 2, action_y + self.S(24), "Add prescription",
                  16, WHITE, "bold", anchor="center", tag="save_prescription")
        self.clickable("save_prescription", self.save_prescription)
        if self.status:
            self.text(left, action_y + self.S(70), self.status, 14, TEXT_MUTED)

    def _prescription_option_card(self, x1, x2, y, height, title, icon, line1, line2):
        tag = f"prescription::{icon}"
        self.rrect(x1, y, x2, y + height, self.S(13), fill=WHITE,
                   outline=RED, width=self.S(1.2), tags=tag)
        self.draw_icon(icon, x1 + self.S(35), y + self.S(34), self.S(24), RED, tag)
        self.text(x1 + self.S(70), y + self.S(31), title, 22, RED, "bold", tag=tag)
        self.text(x1 + self.S(70), y + self.S(58), line1, 17, "#4a4a4a", tag=tag)
        self.text(x1 + self.S(70), y + self.S(81), line2, 17, "#4a4a4a", tag=tag)
        self.clickable(tag, lambda selected=title: self.choose_prescription_method(selected))

    def draw_orders(self, x1, x2, y):
        self.list_header(x1, x2, y, "Recent orders")
        y += self.S(40)
        colours = {"Processing": ("#fff4e5", "#b26a00"), "Shipped": (SOFT_BLUE, NAVY),
                   "Delivered": ("#e8f6ee", "#1e7a46")}
        for title, sub, status in ORDERS:
            self.text(x1 + self.S(6), y + self.S(38), title, 30, INK, "normal")
            self.text(x1 + self.S(6), y + self.S(72), sub, 14, TEXT_MUTED)
            bg, fg = colours[status]
            pw = self.S(120)
            self.rrect(x2 - pw, y + self.S(34), x2, y + self.S(66), self.S(16), fill=bg, outline="")
            self.text(x2 - pw / 2, y + self.S(50), status, 13, fg, "bold", anchor="center")
            y += self.S(98)
            self.c.create_line(x1, y, x2, y, fill=BORDER)

    def draw_tasks(self, x1, x2, y):
        self.draw_icon("bulb", x1 + self.S(14), y + self.S(14), self.S(22), INK, None)
        self.text(x1 + self.S(34), y + self.S(14), "Daily care plan", 18, INK, "bold")
        self.c.create_line(x1, y + self.S(36), x2, y + self.S(36), fill=BORDER)
        y += self.S(36)
        for i, (time, ampm, label, on) in enumerate(self.tasks):
            col = INK if on else TEXT_OFF
            t = self.text(x1 + self.S(6), y + self.S(44), time, 46, col, "normal")
            tx2 = self.c.bbox(t)[2]
            self.text(tx2 + self.S(4), y + self.S(54), ampm, 20, col)
            self.text(x1 + self.S(8), y + self.S(84), label, 14, TEXT_MUTED if on else TEXT_OFF)
            self.toggle(x2 - self.S(70), y + self.S(50), on,
                        f"toggle::{i}", lambda k=i: self.flip_task(k))
            y += self.S(106)
            self.c.create_line(x1, y, x2, y, fill=BORDER)

    def list_header(self, x1, x2, y, title):
        self.text(x1, y + self.S(16), title, 18, INK, "bold")
        self.c.create_line(x1, y + self.S(38), x2, y + self.S(38), fill=BORDER)

    def toggle(self, x, cy, on, tag, func):
        w, h = self.S(68), self.S(40)
        self.rrect(x, cy - h / 2, x + w, cy + h / 2, h / 2,
                   fill=RED if on else TOGGLE_OFF, outline="", tags=tag)
        r = h / 2 - self.S(3)
        kx = x + w - h / 2 if on else x + h / 2
        self.c.create_oval(kx - r, cy - r + self.S(1.5), kx + r, cy + r + self.S(1.5),
                           fill="#c4c9d4", outline="", tags=tag)
        self.c.create_oval(kx - r, cy - r, kx + r, cy + r, fill=WHITE, outline="", tags=tag)
        self.clickable(tag, func)

    def draw_dropdown(self):
        if self.dropdown == "notifications":
            items = self.notifications
            x2 = self.bell_box[0] + self.S(330)
            title = "Notifications"
        else:
            items = [("Manage profiles", "Switch between family members"),
                     ("Settings", "Account, payments, notifications"),
                     ("Sign out", "")]
            x2 = self.w - self.S(18)
            title = "Team AGILE"
        top = self.S(86)
        dw = self.S(340)
        x1 = x2 - dw
        rh = self.S(66)
        y2 = top + self.S(56) + rh * len(items)
        self.rrect(x1, top + self.S(5), x2, y2 + self.S(5), self.S(16), fill=SHADOW, outline="")
        self.rrect(x1, top, x2, y2, self.S(16), fill=WHITE, outline=BORDER, width=self.S(1.2))
        self.text(x1 + self.S(20), top + self.S(28), title, 16, INK, "bold")
        y = top + self.S(56)
        for i, (head, sub) in enumerate(items):
            tag = f"dd::{i}"
            self.c.create_line(x1 + self.S(16), y, x2 - self.S(16), y, fill=BORDER)
            self.c.create_rectangle(x1 + self.S(2), y + 1, x2 - self.S(2), y + rh - 1,
                                    fill=WHITE, outline=WHITE, tags=tag)
            if sub:
                self.text(x1 + self.S(20), y + self.S(22), head, 14, INK, "bold", tag=tag)
                self.text(x1 + self.S(20), y + self.S(46), sub, 13, TEXT_MUTED, tag=tag)
            else:
                self.text(x1 + self.S(20), y + rh / 2, head, 14, RED, "bold", tag=tag)
            if self.dropdown == "profile" and head in ("Manage profiles", "Settings"):
                self.clickable(tag, lambda h=head: self.go(h))
            else:
                self.clickable(tag, lambda: self.toggle_dropdown(None))
            y += rh


class SettingsViewMixin:
    def page_title(self, title):
        y = self.S(120)
        self.c.create_rectangle(self.sw + self.S(18), y - self.S(20), self.sw + self.S(56),
                                y + self.S(20), fill=WHITE, outline=WHITE, tags="back")
        self.draw_icon("back", self.sw + self.S(36), y, self.S(26), INK, "back")
        self.clickable("back", lambda: self.go("Dashboard"))
        self.text(self.sw + self.S(70), y, title, 22, INK)
        self.c.create_line(self.sw, y + self.S(36), self.w, y + self.S(36), fill=BORDER)
        return y + self.S(36)

    def draw_settings(self):
        y = self.page_title("Settings")
        x1 = self.sw + self.S(20)
        x2 = x1 + min(self.S(520), self.w - x1 - self.S(20))
        row = self.S(70)
        for label, icon in SETTINGS_ITEMS:
            tag = f"set::{label}"
            self.c.create_rectangle(x1, y, x2, y + row, fill=WHITE, outline=WHITE, tags=tag)
            self.draw_icon(icon, x1 + self.S(16), y + row / 2, self.S(26), INK, tag)
            self.text(x1 + self.S(46), y + row / 2, label, 17, INK, tag=tag)
            self.draw_icon("chev_right", x2 - self.S(20), y + row / 2, self.S(16), TEXT_MUTED, tag)
            self.c.create_line(x1, y + row, x2, y + row, fill=BORDER)
            self.clickable(tag, lambda: None)
            y += row

    def draw_placeholder_page(self, title):
        y = self.page_title(title)
        cx = (self.sw + self.w) / 2
        cy = (y + self.h) / 2
        msg = "Payments are made here." if title == "Payments" else f"{title} will appear here."
        self.text(cx, cy, msg, 16, TEXT_MUTED, anchor="center")
