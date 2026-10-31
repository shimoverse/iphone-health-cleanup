# Contributing

Please keep the boundary between implemented scripts, guided actions and proposed capabilities clear. Useful changes include supported-device field observations, focused bug fixes and an independently tested on-phone photo scanner with strict Favorites protection.

## Offline checks

Use the isolated environment from the README, then run from the repository root:

```sh
.venv/bin/python -m unittest discover -s skills/iphone-health-cleanup/tests -v
python3 -m unittest discover -s skills/android-health-cleanup/tests -v
python3 -m unittest discover -s tests -v
python3 tools/check_publication.py
git diff --check
```

Both skill suites use fake devices. One contract test inspects the installed pinned library; run the suite in that environment so it does not skip. Test output is not proof of real-device access, successful deletion, malware absence or a faster phone. The installer tests use isolated temporary directories, never a real skill directory.

## Device testing

Phone access is opt-in and outside ordinary tests. Use your own authorized device and a private run directory outside Git. Start read-only; approve an exact ordinary app/action pilot only after reviewing its local-data consequences. Preserve logs locally and provide a minimal redacted explanation of results. Do not publish a whole inventory as a bug report.

## Privacy and review

Do not contribute device IDs, pair records, personal app lists, private paths, names, emails, browser history, photos, backups, credentials or runtime reports. Fictional fixtures should be clearly marked. Use your GitHub no-reply commit email if you want to keep your email private.

Before publication, review the full diff and tracked file list, run the privacy check, and inspect every scanner finding in context. A small allowlist intentionally limits publishable files; update it deliberately when adding reviewed source files. Never copy a private repository's Git history into a public release.

Changes to approval, deletion, locking, identity or verification behavior need meaningful offline failure tests and a fresh-context independent review. Keep the review route and any remaining limits in the change description. Use supported APIs; do not delete raw Photos-library files or silently change security settings.

Public issues should contain a short problem description, software versions and synthetic/redacted reproduction only. Report a security issue through GitHub's private reporting facilities if available; do not expose exploitable private details or personal data in an issue.
