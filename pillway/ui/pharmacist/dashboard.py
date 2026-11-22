"""Pharmacist dashboard: who needs me, what did they say, what do I do next, at a glance.

Called by: PillwayApp.render() for the pharmacist's Dashboard.
- Summary tiles: open urgent flags, plans waiting for approval, estimated hours saved (an estimate).
- Filters All · ACTIVE · WATCHING, sort, compact/comfortable view (remembered between sessions).
- Patient tiles: rounded squares, initials, name, RED BADGE (top-left) = unresolved flags,
  green "live" dot when chatting now. New flags move a patient to the front with a calm highlight.
"""

import time

from config import get_settings

from ...core import check_ins
from ...core.care_plan import blanks_to_fill
from ...storage import app_state
from ...storage.patient_store import display_name, initials
from ..theme import (AMBER, AMBER_SOFT, BORDER, GREEN, GREEN_SOFT, INK, LIVE_GREEN, NAVY, PAGE_BG, RED,
                     RED_SOFT, RED_TEXT, SHADOW, TEXT_DARK, TEXT_MUTED, WHITE)


def needs_attention_key(record):
    """Sort order: newest urgent flags first, then watch flags, then plans waiting, then missed check-ins."""
    open_flags = [f for f in record["flags"] if f["status"] == "open"]
    newest = max((f.get("updated") or f["time"] for f in open_flags), default="")
    plan = record.get("care_plan") or {}
    if any(f["tier"] == 1 for f in open_flags):
        group = 0
    elif open_flags:
        group = 1
    elif plan.get("status") in ("draft", "changes_requested"):
        group = 2
    elif check_ins.missed_check_ins(record):
        group = 3
    else:
        group = 4
    return group, newest


def sort_by_attention(records):
    """Group order (urgent, watch, plan waiting, missed, rest), newest flag first inside each group."""
    newest_first = sorted(records, key=lambda r: needs_attention_key(r)[1], reverse=True)
    return sorted(newest_first, key=lambda r: needs_attention_key(r)[0])


class PharmacistDashboardMixin:
    def draw_pharmacist_dashboard(self):
        x1, y1, x2, y2 = self.sw + self.S(14), self.S(92), self.w - self.S(14), self.h - self.S(14)
        self.c.create_rectangle(x1, y1, x2, y2, fill=PAGE_BG, outline="")
        records = self.store.all()
        y = self._draw_summary_tiles(records, x1 + self.S(20), y1 + self.S(16), x2 - self.S(20))
        y = self._draw_filter_bar(x1 + self.S(20), y + self.S(14), x2 - self.S(20))
        shown = self._filtered_sorted(records)
        if not any(f["status"] == "open" for r in records for f in r["flags"]) and not any(
                (r.get("care_plan") or {}).get("status") in ("draft", "changes_requested") for r in records):
            self.rrect(x1 + self.S(20), y, x2 - self.S(20), y + self.S(50), self.S(12), fill="#e8f6ee", outline=GREEN)
            self.text(x1 + self.S(40), y + self.S(25), "All clear: no open flags and no care plans waiting.", 14, GREEN, "bold")
            y += self.S(64)
        area = self.make_scroll(x1 + self.S(10), y, x2 - self.S(10), y2 - self.S(6), PAGE_BG)
        height = self._draw_tiles(area, shown, x2 - x1 - self.S(40))
        self.finish_scroll(area, height)

    def _draw_summary_tiles(self, records, x1, y, x2):
        demo = get_settings().demo
        low = demo.plans_per_month * demo.follow_ups_per_plan * demo.minutes_per_follow_up_low // 60
        high = demo.plans_per_month * demo.follow_ups_per_plan * demo.minutes_per_follow_up_high // 60
        urgent = sum(1 for r in records for f in r["flags"] if f["status"] == "open" and f["tier"] == 1)
        waiting = sum(1 for r in records if (r.get("care_plan") or {}).get("status") in ("draft", "changes_requested"))
        requests = sum(1 for r in records for q in r["pharmacist_requests"] if q["status"] == "open")
        tiles = [("Open urgent flags", str(urgent), RED_TEXT if urgent else TEXT_DARK),
                 ("Care plans waiting for approval", str(waiting), AMBER if waiting else TEXT_DARK),
                 ("Patient requests to call back", str(requests), AMBER if requests else TEXT_DARK),
                 ("Estimated pharmacist hours saved / month", f"{low}–{high} h", GREEN)]
        gap = self.S(14)
        width = (x2 - x1 - gap * (len(tiles) - 1)) / len(tiles)
        for index, (label, value, colour) in enumerate(tiles):
            tx = x1 + index * (width + gap)
            self.rrect(tx, y, tx + width, y + self.S(92), self.S(14), fill=WHITE, outline=BORDER)
            if colour != TEXT_DARK:  # a coloured edge marks the tiles that need action
                self.c.create_rectangle(tx + 1, y + self.S(14), tx + self.S(6), y + self.S(78), fill=colour, outline="")
            self.text(tx + self.S(22), y + self.S(36), value, 30, colour, "bold")
            self.c.create_text(tx + self.S(22), y + self.S(70), text=label, anchor="w", fill=TEXT_DARK,
                               font=self.font(13), width=width - self.S(34))
        self.c.create_text(x2, y + self.S(104), text="Hours saved is an estimate: 100 plans × 6 follow-ups × 10–15 min "
                           "(set in pillway_config.toml).", anchor="e", fill=TEXT_MUTED, font=self.font(9))
        return y + self.S(110)

    def _draw_filter_bar(self, x1, y, x2):
        x = x1
        for name in ("All", "ACTIVE", "WATCHING"):
            tag = f"filter::{name}"
            selected = self.dash_filter == name
            label = name
            item = self.c.create_text(0, -500, text=label, font=self.font(13, "bold"))
            width = self.c.bbox(item)[2] - self.c.bbox(item)[0] + self.S(36) + (self.S(14) if name == "ACTIVE" else 0)
            self.c.delete(item)
            self.rrect(x, y, x + width, y + self.S(44), self.S(22), fill=INK if selected else WHITE,
                       outline=INK if selected else BORDER, tags=tag)
            self.text(x + width / 2 + (self.S(7) if name == "ACTIVE" else 0), y + self.S(22), label, 13,
                      WHITE if selected else INK, "bold", anchor="center", tag=tag)
            if name == "ACTIVE":
                self.c.create_oval(x + self.S(10), y + self.S(18), x + self.S(18), y + self.S(26), fill=LIVE_GREEN,
                                   outline="", tags=tag)
            self.clickable(tag, lambda n=name: self.set_dashboard_pref(filter=n))
            x += width + self.S(10)
        right = x2
        for label, key, value in (("+ Add patient", None, None),
                                  ("Compact view" if self.dash_view == "comfortable" else "Comfortable view", "view",
                                   "compact" if self.dash_view == "comfortable" else "comfortable"),
                                  ("Sort: " + self.dash_sort, "sort",
                                   "Name" if self.dash_sort == "Needs attention" else "Needs attention")):
            tag = "dashbtn::" + "_".join(label.split())
            item = self.c.create_text(0, -500, text=label, font=self.font(12, "bold"))
            width = self.c.bbox(item)[2] - self.c.bbox(item)[0] + self.S(30)
            self.c.delete(item)
            primary = key is None
            self.rrect(right - width, y, right, y + self.S(44), self.S(10), fill=RED if primary else WHITE,
                       outline=RED if primary else BORDER, tags=tag)
            self.text(right - width / 2, y + self.S(22), label, 12, WHITE if primary else INK, "bold", anchor="center", tag=tag)
            action = self.add_patient_profile if primary else (lambda k=key, v=value: self.set_dashboard_pref(**{k: v}))
            self.clickable(tag, action)
            right -= width + self.S(10)
        return y + self.S(60)

    def set_dashboard_pref(self, **changes):
        for key, value in changes.items():
            setattr(self, f"dash_{key}", value)
        app_state.save(**changes)
        self.render()

    def _filtered_sorted(self, records):
        if self.dash_filter != "All":
            records = [r for r in records if check_ins.status(r) == self.dash_filter]
        if self.dash_sort == "Name":
            ordered = sorted(records, key=display_name)
        else:
            ordered = sort_by_attention(records)
        previous = getattr(self, "_last_order", [])
        now = time.monotonic()
        for index, record in enumerate(ordered):
            if record["id"] in previous and previous.index(record["id"]) > index:
                self.recently_moved[record["id"]] = now + 2.5  # calm highlight, not a confusing jump
        self._last_order = [r["id"] for r in ordered]
        return ordered

    def _draw_tiles(self, canvas, records, width):
        size = self.S(150) if self.dash_view == "compact" else self.S(230)
        gap = self.S(22)
        columns = max(1, int((width + gap) // (size + gap)))
        for index, record in enumerate(records):
            row, col = divmod(index, columns)
            self._draw_tile(canvas, record, self.S(10) + col * (size + gap), self.S(16) + row * (size + gap), size)
        rows = (len(records) + columns - 1) // columns
        if not records:
            self.tx(canvas, width / 2, self.S(40), "No patients in this view.", 15, TEXT_MUTED, anchor="n")
        return self.S(30) + rows * (size + gap)

    def _draw_tile(self, canvas, record, x, y, size):
        tag = f"tile::{record['id']}"
        open_flags = [f for f in record["flags"] if f["status"] == "open"]
        moved = self.recently_moved.get(record["id"], 0) > time.monotonic()
        self.rr(canvas, x, y, x + size, y + size, self.S(22), fill=RED_SOFT if moved else WHITE,
                outline=RED if moved else BORDER, width=self.S(3 if moved else 1.2), tags=tag)
        compact = self.dash_view == "compact"
        cx, avatar_y, radius = x + size / 2, y + size * 0.30, size * 0.15
        canvas.create_oval(cx - radius, avatar_y - radius, cx + radius, avatar_y + radius, fill=NAVY, outline="", tags=tag)
        canvas.create_text(cx, avatar_y, text=initials(record), fill=WHITE, font=self.font(16 if compact else 22, "bold"), tags=tag)
        canvas.create_text(cx, y + size * 0.55, text=display_name(record), fill=INK, width=size - self.S(16),
                           font=self.font(14 if compact else 17, "bold"), tags=tag, justify="center")
        # status as a coloured pill with words (never colour alone)
        status_text, status_colour, status_soft = self._tile_status(record, open_flags)
        font = self.font(12 if compact else 13, "bold")
        label_y = y + size * (0.74 if compact else 0.71)
        label = canvas.create_text(cx, label_y, text=status_text, fill=status_colour, width=size - self.S(36),
                                   font=font, tags=tag, justify="center")
        probe = canvas.create_text(0, -2000, text=status_text, font=font)
        pb = canvas.bbox(probe)
        canvas.delete(probe)
        lb = canvas.bbox(label)
        if pb and lb:  # pill centred on the tile, as wide as the words (or the tile, if they wrap)
            half = min((pb[2] - pb[0]) / 2, (size - self.S(36)) / 2) + self.S(12)
            pill = self.rr(canvas, cx - half, lb[1] - self.S(6), cx + half, lb[3] + self.S(6),
                           self.S(12), fill=status_soft, outline="", tags=tag)
            canvas.tag_raise(label, pill)
        if not compact:
            subtitle = "\n".join(c.split(" (")[0] for c in record["profile"].get("conditions", []))
            canvas.create_text(cx, y + size * 0.89, text=subtitle, fill=TEXT_MUTED, width=size - self.S(16),
                               font=self.font(12), tags=tag, justify="center")
        if open_flags:  # red badge, top-left corner
            r = self.S(17)
            canvas.create_oval(x - r * 0.4, y - r * 0.4, x + r * 1.6, y + r * 1.6, fill=RED, outline=WHITE,
                               width=self.S(2), tags=tag)
            canvas.create_text(x + r * 0.6, y + r * 0.6, text=str(len(open_flags)), fill=WHITE,
                               font=self.font(13, "bold"), tags=tag)
        if check_ins.is_active(record):
            canvas.create_oval(x + size - self.S(30), y + self.S(14), x + size - self.S(16), y + self.S(28),
                               fill=LIVE_GREEN, outline=WHITE, tags=tag)
            canvas.create_text(x + size - self.S(36), y + self.S(21), text="LIVE", anchor="e", fill=GREEN,
                               font=self.font(9, "bold"), tags=tag)
        self.bind_click(canvas, tag, lambda pid=record["id"]: self.select_doctor_patient(pid))

    def _tile_status(self, record, open_flags):
        """(words, text colour, pill colour) for a patient tile."""
        urgent = [f for f in open_flags if f["tier"] == 1]
        if urgent:
            return f"Urgent: {urgent[-1]['topic']}", RED_TEXT, RED_SOFT
        if open_flags:
            return f"Watch: {open_flags[-1]['topic']}", AMBER, AMBER_SOFT
        if any(q["status"] == "open" for q in record["pharmacist_requests"]):
            return "Asked for a pharmacist", AMBER, AMBER_SOFT
        plan = record.get("care_plan") or {}
        if plan.get("status") in ("draft", "changes_requested"):
            return f"Care plan waiting ({len(blanks_to_fill(plan))} targets to set)", AMBER, AMBER_SOFT
        if check_ins.missed_check_ins(record):
            return f"Missed check-ins ({check_ins.days_since_check_in(record)} days)", AMBER, AMBER_SOFT
        return "All good", GREEN, GREEN_SOFT
