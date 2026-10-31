# SPDX-License-Identifier: GPL-3.0-or-later
"""Synthetic privacy patterns only; no actual credentials or personal paths."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("publication_check", ROOT / "tools/check_publication.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class PublicationTests(unittest.TestCase):
    def test_detects_credential_shapes_without_exposing_values(self):
        token = "ghp_" + "A" * 40
        issues = audit.scan_text(token)
        self.assertIn("credential-shaped value", issues)
        self.assertNotIn(token, " ".join(issues))

    def test_detects_personal_paths_and_nonexample_emails(self):
        path = "/" + "Users" + "/fictional-user/private.txt"
        email = "fictional" + "@" + "mail.invalid"
        self.assertIn("private home path", audit.scan_text(path))
        self.assertIn("non-example email address", audit.scan_text(email))
        self.assertEqual(audit.scan_text("fixture@example.test"), [])

    def test_rejects_unexpected_runtime_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "inventory.json").write_text("{}")
            issues = audit.check(root)
            self.assertTrue(any("inventory.json: unexpected" in issue for issue in issues))

    def test_current_source_has_no_flagged_publication_content(self):
        self.assertEqual(audit.check(ROOT), [])


if __name__ == "__main__":
    unittest.main()
