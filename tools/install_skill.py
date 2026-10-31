#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Copy this skill into one local host; no dependency install or device access."""
import argparse
import os
import shutil
from pathlib import Path

NAME = "iphone-health-cleanup"
SKILLS = Path(__file__).resolve().parents[1] / "skills"
PLATFORMS = {"iphone": NAME, "android": "android-health-cleanup"}
SOURCE = SKILLS / NAME


def destination(agent, home=None, platform="iphone"):
    home = Path.home() if home is None else Path(home)
    roots = {"codex": Path(os.environ.get("CODEX_HOME", str(home / ".codex"))),
             "claude": home / ".claude", "agents": home / ".agents"}
    return roots[agent].expanduser() / "skills" / PLATFORMS[platform]


def install(target, dry_run=False, source=None):
    target = Path(target)
    source = SOURCE if source is None else Path(source)
    if target.exists() or target.is_symlink():
        raise ValueError("Destination already exists; review and back it up before an update: " + str(target))
    for parent in target.parents:
        if parent.is_symlink():
            raise ValueError("Refusing an installation through a symlink: " + str(parent))
    if not (source / "SKILL.md").is_file() or any(p.is_symlink() for p in source.rglob("*")):
        raise ValueError("Source skill is missing or contains symlinks.")
    if dry_run:
        print("Would install skill at: " + str(target))
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    # copytree refuses a concurrently created destination; never merge/overwrite.
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    print("Installed skill at: " + str(target))
    print("No phone was contacted and no dependencies were installed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=("codex", "claude", "agents"), default="codex")
    parser.add_argument("--platform", choices=tuple(PLATFORMS), default="iphone")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        install(destination(args.agent, platform=args.platform), args.dry_run,
                SKILLS / PLATFORMS[args.platform])
    except (ValueError, OSError) as exc:
        parser.exit(2, str(exc) + "\n")


if __name__ == "__main__":
    main()
