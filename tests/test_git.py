"""The git segment: porcelain v2 parsing, symbols, colours, and a real repo."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import statusline
from statusline import BLUE, CYAN, GREEN, MAGENTA, RED, RESET, YELLOW
from tests.support import changed, environment, porcelain, renamed, unmerged, untracked

DATA = {"cwd": "/work/repo"}


class GitSegmentTest(unittest.TestCase):
    def render(self, status, **env):
        """The segment's richest variant for canned `git status` output."""
        with environment(git=status, **env):
            seg = statusline.git_segment(DATA)
        return seg[1][0] if seg else None

    def test_clean_branch_shows_repo_and_branch_only(self):
        self.assertEqual(self.render(porcelain()), "repo:main")

    def test_each_status_code_maps_to_its_symbol(self):
        cases = {
            "worktree modified": (changed(".M"), "!1"),
            "type changed": (changed(".T"), "!1"),
            "staged modified": (changed("M."), "+1"),
            "staged new file": (changed("A."), "+1"),
            "staged and modified again": (changed("MM"), "!1 +1"),
            "deleted in worktree": (changed(".D"), "✘1"),
            "deletion staged": (changed("D."), "✘1"),
            "renamed": (renamed(), "+1"),
            "untracked": (untracked(), "?1"),
            "merge conflict": (unmerged(), "!1"),
        }
        for name, (entry, symbols) in cases.items():
            with self.subTest(name):
                self.assertEqual(self.render(porcelain(entry)), f"repo:main {symbols}")

    def test_counts_accumulate(self):
        status = porcelain(changed(".M", "a"), changed(".M", "b"), untracked("c"))
        self.assertEqual(self.render(status), "repo:main !2 ?1")

    def test_symbols_keep_a_fixed_order(self):
        status = porcelain(untracked(), changed(".D"), changed("A."), changed(".M"), ab="+1 -1")
        self.assertEqual(self.render(status), "repo:main !1 +1 ?1 ✘1 ⇡1 ⇣1")

    def test_ahead_and_behind(self):
        self.assertEqual(self.render(porcelain(ab="+2 -0")), "repo:main ⇡2")
        self.assertEqual(self.render(porcelain(ab="+0 -3")), "repo:main ⇣3")
        self.assertEqual(self.render(porcelain(ab="+0 -0")), "repo:main")

    def test_detached_head_shows_short_sha(self):
        status = porcelain(head="(detached)", oid="abc1234def5678")
        self.assertEqual(self.render(status), "repo:@abc1234")

    def test_unknown_repo_name_shows_branch_alone(self):
        with environment(git=porcelain(), repo=None):
            self.assertEqual(statusline.git_segment(DATA)[1], ["main"])

    def test_symbols_shed_before_the_branch(self):
        with environment(git=porcelain(untracked())):
            variants = statusline.git_segment(DATA)[1]
        self.assertEqual(variants[0], "repo:main ?1")
        self.assertEqual(variants[-1], "repo:main")

    def test_no_git_output_hides_the_segment(self):
        self.assertIsNone(self.render(None))

    def test_no_cwd_hides_the_segment(self):
        with environment(git=porcelain()):
            self.assertIsNone(statusline.git_segment({}))

    def test_each_symbol_has_its_colour(self):
        status = porcelain(untracked(), changed(".D"), changed("A."), changed(".M"), ab="+1 -1")
        line = self.render(status, colour=True)
        for text, code in (
            ("!1", YELLOW),
            ("+1", GREEN),
            ("?1", BLUE),
            ("✘1", RED),
            ("⇡1", CYAN),
            ("⇣1", MAGENTA),
        ):
            with self.subTest(text):
                self.assertIn(f"{code}{text}{RESET}", line)


@unittest.skipUnless(shutil.which("git"), "git not installed")
class RealRepoTest(unittest.TestCase):
    """Against a real repository, so a change in git's porcelain or in how we
    call it shows up here rather than as a blank field."""

    def setUp(self):
        self.dir = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.repo = self.dir / "demo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.repo)], check=True)
        # Real git and repo_name here: patch only the display switches.
        self.enterContext(mock.patch.dict(statusline.CONFIG, {"icons": False, "colour": False}))

    def test_untracked_file_in_a_fresh_repo(self):
        (self.repo / "new.txt").write_text("x")
        seg = statusline.git_segment({"cwd": str(self.repo)})
        self.assertEqual(seg[1][0], "demo:main ?1")

    def test_subdirectory_names_the_repo_root(self):
        sub = self.repo / "a" / "b"
        sub.mkdir(parents=True)
        self.assertEqual(statusline.repo_name(str(sub)), "demo")

    def test_outside_a_repo_hides_the_segment(self):
        self.assertIsNone(statusline.git_status(str(self.dir)))
        self.assertIsNone(statusline.repo_name(str(self.dir)))

    def test_missing_directory_hides_the_segment(self):
        self.assertIsNone(statusline.git_status(str(self.dir / "nope")))


if __name__ == "__main__":
    unittest.main()
