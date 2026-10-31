#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Copy this skill into one local host; no dependency install or device access."""
import argparse
import os
import shutil
from pathlib import Path

NAME = "iphone-health-cleanup"
SOURCE = Path(__file__).resolve().parents[1] / "skills" / NAME


def destination(agent, home=None):
    home = Path.home() if home is None else Path(home)
    roots = {"codex": Path(os.environ.get("CODEX_HOME", str(home / ".codex"))),
             "claude": home / ".claude", "agents": home / ".agents"}
    return roots[agent].expanduser() / "skills" / NAME


def install(target, dry_run=False):
    target = Path(target)
    if target.exists() or target.is_symlink():
        raise ValueError("Destination already exists; review and back it up before an update: " + str(target))
    for parent in target.parents:
        if parent.is_symlink():
            raise ValueError("Refusing an installation through a symlink: " + str(parent))
    if not (SOURCE / "SKILL.md").is_file() or any(p.is_symlink() for p in SOURCE.rglob("*")):
        raise ValueError("Source skill is missing or contains symlinks.")
    if dry_run:
        print("Would install skill at: " + str(target))
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    # copytree refuses a concurrently created destination; never merge/overwrite.
    shutil.copytree(SOURCE, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    print("Installed skill at: " + str(target))
    print("No phone was contacted and no dependencies were installed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=("codex", "claude", "agents"), default="codex")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        install(destination(args.agent), args.dry_run)
    except (ValueError, OSError) as exc:
        parser.exit(2, str(exc) + "\n")


if __name__ == "__main__":
    main()
