# SPDX-License-Identifier: MIT
"""Installer behavior in temporary directories; never installs into a real host."""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("install_skill", ROOT / "tools/install_skill.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def test_dry_run_creates_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve() / "host/skills/iphone-health-cleanup"
            installer.install(target, dry_run=True)
            self.assertFalse(target.parent.exists())

    def test_install_copies_skill_and_preserves_unrelated_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "unrelated.txt").write_text("keep")
            target = root / "iphone-health-cleanup"
            installer.install(target)
            self.assertEqual((target / "SKILL.md").read_bytes(), (installer.SOURCE / "SKILL.md").read_bytes())
            self.assertEqual((target / "LICENSE").read_bytes(), (ROOT / "LICENSE").read_bytes())
            self.assertIn("pymobiledevice3", (target / "NOTICE.md").read_text())
            self.assertEqual((root / "unrelated.txt").read_text(), "keep")
            self.assertFalse(list(target.rglob("*.pyc")))
            (target / "SKILL.md").write_text("user customization")
            with self.assertRaises(ValueError):
                installer.install(target)
            self.assertEqual((target / "SKILL.md").read_text(), "user customization")

    def test_rejects_symlink_parent_and_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "real").mkdir()
            (root / "link").symlink_to(root / "real", target_is_directory=True)
            with self.assertRaises(ValueError):
                installer.install(root / "link/skill")
            source = root / "source"
            source.mkdir()
            (source / "SKILL.md").write_text("test")
            (source / "linked").symlink_to(root / "real", target_is_directory=True)
            with mock.patch.object(installer, "SOURCE", source), self.assertRaises(ValueError):
                installer.install(root / "target")

    def test_agent_destinations_and_configured_codex_root(self):
        with mock.patch.dict(os.environ, {"CODEX_HOME": "/tmp/fictional-codex-root"}):
            self.assertEqual(installer.destination("codex"), Path("/tmp/fictional-codex-root/skills/iphone-health-cleanup"))
        self.assertEqual(installer.destination("claude", Path("/tmp/fictional-home")),
                         Path("/tmp/fictional-home/.claude/skills/iphone-health-cleanup"))

    def test_android_uses_a_separate_destination(self):
        self.assertEqual(installer.destination("claude", Path("/tmp/fictional-home"), "android"),
                         Path("/tmp/fictional-home/.claude/skills/android-health-cleanup"))

    def test_selected_module_cannot_overwrite_other_platform(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            existing = root / "iphone-health-cleanup"
            existing.mkdir()
            (existing / "SKILL.md").write_text("existing iPhone instructions")
            source = root / "android-source"
            source.mkdir()
            (source / "SKILL.md").write_text("fictional Android instructions")
            target = root / "android-health-cleanup"
            installer.install(target, source=source)
            self.assertEqual((target / "SKILL.md").read_text(), "fictional Android instructions")
            self.assertEqual((existing / "SKILL.md").read_text(), "existing iPhone instructions")


if __name__ == "__main__":
    unittest.main()
