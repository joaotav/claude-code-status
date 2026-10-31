"""The account field: where the email is read from, and when it is hidden."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import statusline


class AccountEmailTest(unittest.TestCase):
    """Against real files: one config dir per account, as with
    CLAUDE_CONFIG_DIR, and the default in the home directory."""

    def setUp(self):
        self.dir = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.home = self.dir / "home"
        self.home.mkdir()
        self.env = self.enterContext(mock.patch.dict(os.environ, {"HOME": str(self.home)}))
        os.environ.pop("CLAUDE_CONFIG_DIR", None)  # restored by patch.dict

    def write(self, folder: Path, content) -> None:
        text = content if isinstance(content, str) else json.dumps(content)
        (folder / ".claude.json").write_text(text)

    def test_reads_the_config_dir_named_by_the_environment(self):
        work = self.dir / ".claude-work"
        work.mkdir()
        self.write(work, {"oauthAccount": {"emailAddress": "me@work.example"}})
        self.write(self.home, {"oauthAccount": {"emailAddress": "me@home.example"}})
        os.environ["CLAUDE_CONFIG_DIR"] = str(work)
        self.assertEqual(statusline.account_email(), "me@work.example")

    def test_defaults_to_the_home_directory(self):
        self.write(self.home, {"oauthAccount": {"emailAddress": "me@home.example"}})
        self.assertEqual(statusline.account_email(), "me@home.example")

    def test_missing_or_unusable_file_is_none(self):
        cases = {
            "no file": None,
            "not json": "{oops",
            "no account (API key)": {"projects": {}},
            "account without email": {"oauthAccount": {"accountUuid": "x"}},
            "wrong type": {"oauthAccount": {"emailAddress": 42}},
        }
        for name, content in cases.items():
            with self.subTest(name):
                (self.home / ".claude.json").unlink(missing_ok=True)
                if content is not None:
                    self.write(self.home, content)
                self.assertIsNone(statusline.account_email())

    def test_config_dir_that_does_not_exist_is_none(self):
        os.environ["CLAUDE_CONFIG_DIR"] = str(self.dir / "nope")
        self.assertIsNone(statusline.account_email())


class AccountSegmentTest(unittest.TestCase):
    def setUp(self):
        self.enterContext(mock.patch.dict(statusline.CONFIG, {"icons": False}))

    def test_full_email_with_label(self):
        with mock.patch.object(statusline, "account_email", return_value="me@example.com"):
            self.assertEqual(statusline.account_segment()[1], ["Account: me@example.com"])

    def test_no_account_is_no_segment(self):
        with mock.patch.object(statusline, "account_email", return_value=None):
            self.assertIsNone(statusline.account_segment())


if __name__ == "__main__":
    unittest.main()
