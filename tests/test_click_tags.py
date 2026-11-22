"""Regression test: canvas tag names must never contain spaces (real Tk splits them, so clicks die)."""

import unittest

try:
    from pillway.ui.components.scroll_area import safe_tag
except ImportError:  # no tkinter on this computer
    raise unittest.SkipTest("tkinter is not installed")


class SafeTagTests(unittest.TestCase):
    def test_spaces_become_underscores(self):
        self.assertEqual(safe_tag("btn::1::Read aloud::2::3"), "btn::1::Read_aloud::2::3")
        self.assertEqual(safe_tag("btn::Lire à voix haute"), "btn::Lire_à_voix_haute")
        self.assertEqual(safe_tag("plain"), "plain")


if __name__ == "__main__":
    unittest.main()
