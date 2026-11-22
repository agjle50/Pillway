"""Keeps the screen in step with the shared data, and runs slow work off the UI thread.

Called by: pillway/app.py (start_live_sync) and the chat/call/pharmacist screens.
- Every 0.7 s it checks whether any patient file changed (this window OR another window /
  process). If so, it redraws: the pharmacist's red badge, live chat and ACTIVE dot update
  within about a second, with no restart.
- run_in_background(work) runs AI calls in a worker thread so the window never freezes.
"""

import threading

from ..storage.patient_store import PatientStore

POLL_MS = 700


class LiveSyncMixin:
    def start_live_sync(self):
        self._last_stamp = None
        self._background_done = False
        self._background_errors = []
        self._pending_session_ends = {}
        self.after(POLL_MS, self._poll_changes)

    def refresh_record(self):
        """Load the latest copy of the patient shown on the patient side."""
        if self.role == "patient":
            self.record = self.store.load(self.patient_id)
            self.lang = self.record.get("language", self.lang)
        return self.record

    def _poll_changes(self):
        try:
            for (patient_id, session_id), duration_s in list(self._pending_session_ends.items()):
                if patient_id not in self.service.busy:
                    self._pending_session_ends.pop((patient_id, session_id), None)
                    self.service.end_session(patient_id, session_id, duration_s)
            stamp = (self.store.stamp(), tuple(sorted(self.service.busy)))
            if self._background_errors:
                error = self._background_errors.pop(0)
                self.toast = error
            if self.role and (stamp != self._last_stamp or self._background_done):
                self._background_done = False
                first = self._last_stamp is None
                self._last_stamp = stamp
                if not first and not self._user_is_typing_elsewhere():
                    self.render()
        finally:
            self.after(POLL_MS, self._poll_changes)

    def end_session_when_idle(self, patient_id, session_id, duration_s=None):
        if patient_id in self.service.busy:
            self._pending_session_ends[(patient_id, session_id)] = duration_s
        else:
            self.service.end_session(patient_id, session_id, duration_s)

    def _user_is_typing_elsewhere(self):
        """Don't redraw under a pharmacist who is typing in a box (it would lose focus)."""
        focused = self.focus_get()
        return focused is not None and focused is not self.chat_entry and focused.winfo_class() in ("Entry", "Text")

    def run_in_background(self, work, friendly_error="Something went wrong. Please try again."):
        """Run work() in a thread; the poll loop redraws when it finishes."""
        def runner():
            try:
                work()
            except Exception as error:  # never crash the window
                self._background_errors.append(friendly_error)
                print(f"[background] {type(error).__name__}: {error}")
            finally:
                self._background_done = True
        threading.Thread(target=runner, daemon=True).start()

    def all_records(self):
        return PatientStore.all(self.store)
