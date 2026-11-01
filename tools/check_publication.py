#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Publication allowlist with reviewed media hashes, not a full privacy detector."""
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "skills/iphone-health-cleanup/"
ALLOWED = {"plugin.json", ".claude-plugin/plugin.json", "README.md", "LICENSE", "NOTICE.md", "CONTRIBUTING.md", ".gitignore", "docs/workflow.svg",
           ".github/workflows/checks.yml", "tools/install_skill.py", "tools/check_publication.py",
           "tests/test_installer.py", "tests/test_publication.py"}
ALLOWED |= {PACKAGE + name for name in (
    "SKILL.md", "agents/openai.yaml", "scripts/cleanup.py", "scripts/health.py", "scripts/requirements.txt",
    "references/workflow.md", "references/health-workflow.md", "references/health-research.md",
    "references/source-audit.md", "references/photo-cleanup.md", "references/browser-cleanup.md",
    "tests/test_cleanup.py", "tests/test_health.py", "tests/test_health_safety.py")}
ALLOWED |= {"skills/android-health-cleanup/" + name for name in (
    "SKILL.md", "agents/openai.yaml", "scripts/android.py", "tests/test_android.py",
    "references/research.md", "references/workflow.md")}
ALLOWED |= {"docs/blog/" + name for name in (
    "README.md", "article.md", "reader.html", "linkedin-post.md",
    "workflow-comparison.svg", "manual-work-estimate.svg", "user-journey.svg")}
ALLOWED |= {"docs/blog/medium-article.md", "docs/demo/README.md", "tools/render_demo.py"}
# Only synthetic illustrations reviewed visually, never arbitrary device captures.
# Regeneration needs a fresh manual privacy/visual review before changing hashes.
REVIEWED_MEDIA = {
    "docs/demo/phone-cleanup-demo.gif": (b"GIF89a", "25ff1f9de59ac7f9231df7187f7ffddb404596cb9b7d4a61c60f7ac287456919"),
    "docs/demo/phone-cleanup-demo.mp4": (b"\x00\x00\x00 ftyp", "79d225941d2f7ea7a5cb93130c09465b628aa62deab90aa45212e5e33dcad5a1"),
    "docs/demo/phone-cleanup-demo-poster.png": (b"\x89PNG\r\n\x1a\n", "f3dc2957eea4d6a2d2c47c9ce03d71bb8ab2897ac86980ea3ea4f9e4d4112ca6"),
}
ALLOWED |= set(REVIEWED_MEDIA)
PATTERNS = {
    "private home path": re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+/"),
    "private temporary path": re.compile(r"/(?:private/)?var/folders/[A-Za-z0-9/_.-]+"),
    "private key material": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "credential-shaped value": re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9_-]{30,})"),
}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def scan_text(text):
    issues = [label for label, regex in PATTERNS.items() if regex.search(text)]
    for email in EMAIL.findall(text):
        domain = email.rsplit("@", 1)[1].lower()
        if domain not in {"example.com", "example.org", "example.test", "users.noreply.github.com"}:
            issues.append("non-example email address")
    return sorted(set(issues))


def check(root=ROOT):
    root = Path(root)
    files = {}
    for directory, folders, names in os.walk(root, followlinks=False):
        folders[:] = [name for name in folders if name not in {".git", ".venv", "venv", "__pycache__"}]
        for name in names + [name for name in folders if (Path(directory) / name).is_symlink()]:
            path = Path(directory) / name
            files[path.relative_to(root).as_posix()] = path
    problems = []
    for name in sorted(set(files) - ALLOWED):
        problems.append(name + ": unexpected file; review before publishing")
    for name in sorted(ALLOWED - set(files)):
        problems.append(name + ": required source file missing")
    for name in sorted(set(files) & ALLOWED):
        path = files[name]
        if path.is_symlink():
            problems.append(name + ": symlink not allowed")
            continue
        if name in REVIEWED_MEDIA:
            signature, expected_hash = REVIEWED_MEDIA[name]
            data = path.read_bytes()
            if len(data) > 5_000_000 or not data.startswith(signature):
                problems.append(name + ": unexpected media type or size")
            if hashlib.sha256(data).hexdigest() != expected_hash:
                problems.append(name + ": media changed; new privacy/visual review required")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeError, OSError):
            problems.append(name + ": cannot read as text")
            continue
        problems.extend(name + ": " + issue for issue in scan_text(text))
    if (root / ".git").is_dir():
        result = subprocess.run(["git", "log", "--all", "--format=%ae%n%ce"], cwd=root,
                                text=True, capture_output=True)
        if result.returncode == 0:
            for email in set(result.stdout.splitlines()):
                if email and not email.endswith("@users.noreply.github.com"):
                    problems.append("Git history contains a non-no-reply author/committer email")
    return sorted(set(problems))


if __name__ == "__main__":
    findings = check()
    if findings:
        print("Publication check failed:\n" + "\n".join(findings))
        sys.exit(1)
    print("Publication allowlist check passed. Manual privacy review is still required.")
