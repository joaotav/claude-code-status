"""Value formatting: token counts, percentages, reset times and the cwd."""

from __future__ import annotations

import unittest

import statusline
from tests.support import HOME, environment, epoch


class FmtTokensTest(unittest.TestCase):
    def test_scales(self):
        cases = {
            999: "999",
            1000: "1k",
            16700: "16.7k",
            200000: "200k",
            476500: "476.5k",
            1_000_000: "1M",
            1_250_000: "1.25M",
        }
        for n, expected in cases.items():
            with self.subTest(n=n):
                self.assertEqual(statusline.fmt_tokens(n), expected)

    def test_non_numeric_is_a_dash(self):
        for value in (None, "big", []):
            with self.subTest(value=value):
                self.assertEqual(statusline.fmt_tokens(value), "—")


class FmtPctTest(unittest.TestCase):
    def test_drops_a_decimal_that_adds_nothing(self):
        self.assertEqual(statusline.fmt_pct(23.0), "23%")
        self.assertEqual(statusline.fmt_pct(23.5), "23.5%")


class FmtResetTest(unittest.TestCase):
    def setUp(self):
        self.enterContext(environment())

    def test_same_day_is_time_only(self):
        self.assertEqual(statusline.fmt_reset(epoch(hours=2)), "14:00")

    def test_this_week_is_weekday_and_time(self):
        self.assertEqual(statusline.fmt_reset(epoch(days=2)), "Fri 12:00")

    def test_further_out_is_date_and_time(self):
        self.assertEqual(statusline.fmt_reset(epoch(days=10)), "7 Nov 12:00")

    def test_unknown_or_invalid_is_none(self):
        for value in (None, "abc", float("inf")):
            with self.subTest(value=value):
                self.assertIsNone(statusline.fmt_reset(value))


class CwdSegmentTest(unittest.TestCase):
    def setUp(self):
        self.enterContext(environment())

    def variants(self, path):
        seg = statusline.cwd_segment({"cwd": path})
        return seg[1] if seg else None

    def test_home_is_tilde(self):
        self.assertEqual(self.variants(HOME), ["~"])

    def test_root_is_slash(self):
        self.assertEqual(self.variants("/"), ["/"])

    def test_shallow_path_is_shown_whole(self):
        self.assertEqual(self.variants(f"{HOME}/a/b")[0], "~/a/b")

    def test_deep_path_is_trimmed_then_shrinks_to_its_leaf(self):
        v = self.variants(f"{HOME}/a/b/c")
        self.assertEqual(v[0], "~/…/c")
        self.assertEqual(v[-1], "c")

    def test_deep_path_outside_home(self):
        self.assertEqual(self.variants("/usr/share/doc")[0], "/…/doc")

    def test_sibling_of_home_is_not_abbreviated(self):
        # /home/tester2 shares a prefix with HOME but is not under it.
        self.assertFalse(self.variants(f"{HOME}2/x")[0].startswith("~"))

    def test_workspace_dir_wins_over_cwd(self):
        data = {"cwd": "/elsewhere", "workspace": {"current_dir": HOME}}
        self.assertEqual(statusline.cwd_segment(data)[1], ["~"])

    def test_missing_cwd_is_no_segment(self):
        self.assertIsNone(statusline.cwd_segment({}))


if __name__ == "__main__":
    unittest.main()
