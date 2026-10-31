"""The whole line: field order, the narrow-terminal shrink sequence, labels
and colour switches."""

from __future__ import annotations

import unittest

import statusline
from tests.payloads import base
from tests.support import HOME, NOW, changed, environment, porcelain, run_main, strip_ansi, untracked

GIT = porcelain(changed(".M"), untracked(), ab="+2 -0")


def payload(**overrides) -> dict:
    data = base(NOW.timestamp(), cwd=f"{HOME}/projects/work/demo")
    data.update(overrides)
    return data


class OrderTest(unittest.TestCase):
    def test_fields_in_order_with_text_labels(self):
        with environment(git=GIT):
            line = run_main(payload())
        self.assertEqual(
            line,
            "~/…/demo | 5h 23.5% [14:00] | Week: 41.2% [Sun 12:00] | "
            "Context: 15.5k/200k 8% | Opus 5.5 (high) | repo:main !1 ?1 ⇡2",
        )

    def test_session_cost_is_not_shown(self):
        with environment(git=GIT):
            self.assertNotIn("$", run_main(payload()))

    def test_model_without_effort_shows_alone(self):
        data = payload()
        del data["effort"]
        with environment(git=None):
            self.assertTrue(run_main(data).endswith("| Opus 5.5"))


class ShrinkTest(unittest.TestCase):
    """Narrowing the terminal one column at a time must shed detail in the
    agreed order, and only then drop whole fields: git, model, cwd."""

    EXPECTED = [
        "~/…/demo | 5h 23.5% [14:00] | Week: 41.2% [Sun 12:00] | Context: 15.5k/200k 8% | Opus 5.5 (high) | repo:main !1 ?1 ⇡2",
        # 1. reset times
        "~/…/demo | 5h 23.5% | Week: 41.2% | Context: 15.5k/200k 8% | Opus 5.5 (high) | repo:main !1 ?1 ⇡2",
        # 2. context's raw counts
        "~/…/demo | 5h 23.5% | Week: 41.2% | Context: 8% | Opus 5.5 (high) | repo:main !1 ?1 ⇡2",
        # 3. cwd down to its leaf
        "demo | 5h 23.5% | Week: 41.2% | Context: 8% | Opus 5.5 (high) | repo:main !1 ?1 ⇡2",
        # 4. git symbols
        "demo | 5h 23.5% | Week: 41.2% | Context: 8% | Opus 5.5 (high) | repo:main",
        # 5. effort
        "demo | 5h 23.5% | Week: 41.2% | Context: 8% | Opus 5.5 | repo:main",
        # then whole fields: git, model, cwd
        "demo | 5h 23.5% | Week: 41.2% | Context: 8% | Opus 5.5",
        "demo | 5h 23.5% | Week: 41.2% | Context: 8%",
        "5h 23.5% | Week: 41.2% | Context: 8%",
    ]

    def test_shrink_sequence(self):
        seen: list[str] = []
        with environment(git=GIT):
            for width in range(200, 19, -1):
                line = run_main(payload(), columns=width)
                if not seen or line != seen[-1]:
                    seen.append(line)
        self.assertEqual(seen, self.EXPECTED)

    def test_every_line_fits_until_only_quota_and_context_remain(self):
        floor = len(self.EXPECTED[-1])
        with environment(git=GIT):
            for width in range(floor, 200):
                with self.subTest(width=width):
                    self.assertLessEqual(len(run_main(payload(), columns=width)), width)

    def test_quota_and_context_are_never_dropped(self):
        with environment(git=GIT):
            self.assertEqual(run_main(payload(), columns=20), self.EXPECTED[-1])


class LabelsAndColourTest(unittest.TestCase):
    def test_icons_replace_text_labels(self):
        with environment(icons=True, git=GIT):
            line = run_main(payload())
        for key, icon in statusline.ICONS.items():
            with self.subTest(key):
                self.assertIn(icon, line)
        for label in statusline.TEXT_LABELS.values():
            with self.subTest(label):
                self.assertNotIn(label, line)

    def test_colour_on_emits_ansi(self):
        with environment(colour=True, git=GIT):
            self.assertIn("\033[", run_main(payload()))

    def test_no_color_strips_every_escape(self):
        with environment(colour=False, git=GIT):
            line = run_main(payload())
        self.assertEqual(line, strip_ansi(line))

    def test_colour_does_not_change_the_fitted_width(self):
        # Escapes are invisible, so they must not count towards the width.
        with environment(colour=True, git=GIT):
            coloured = strip_ansi(run_main(payload(), columns=90))
        with environment(colour=False, git=GIT):
            plain = run_main(payload(), columns=90)
        self.assertEqual(coloured, plain)


if __name__ == "__main__":
    unittest.main()
