# Copyright 2026 Agentic Data Intelligence SA
# SPDX-License-Identifier: Apache-2.0
"""Check skill frontmatter, and that changes under plugin/ come with a version bump.

Usage: check_skills.py [--base REF]

Without --base only the frontmatter is checked. With --base (the PR's base
commit), anything changed under plugin/ since REF must also bump the version in
plugin/.claude-plugin/plugin.json: Claude Code pins installed plugins to that
version, so without a bump existing users never receive the change. A skill
whose files changed without a metadata.version bump only gets a warning, since
no client reads that field.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

SKILLS_DIR = Path("plugin/skills")
PLUGIN_MANIFEST = Path("plugin/.claude-plugin/plugin.json")
# Shipped with the plugin but not behaviour: editing it needs no new release.
BUMP_EXEMPT = {"plugin/README.md"}
# Limits from the Agent Skills spec that Claude Code enforces.
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
NAME_MAX = 64
DESCRIPTION_MAX = 1024

errors = 0


def error(path: str, message: str) -> None:
    global errors
    errors += 1
    print(f"::error file={path}::{message}")


def warning(path: str, message: str) -> None:
    print(f"::warning file={path}::{message}")


def frontmatter(text: str) -> dict | None:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return None
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def at_ref(ref: str, path: Path) -> str | None:
    try:
        return git("show", f"{ref}:{path.as_posix()}")
    except subprocess.CalledProcessError:
        return None


def skill_version(text: str | None) -> str | None:
    meta = frontmatter(text) if text else None
    metadata = (meta or {}).get("metadata")
    version = metadata.get("version") if isinstance(metadata, dict) else None
    return str(version) if version is not None else None


def is_bump(old: str, new: str) -> bool:
    """Numeric versions (1.0.6) must increase; anything else only has to change."""
    try:
        return tuple(int(p) for p in new.split(".")) > tuple(int(p) for p in old.split("."))
    except ValueError:
        return new != old


def check_frontmatter() -> None:
    skill_dirs = sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir())
    if not skill_dirs:
        error(str(SKILLS_DIR), "no skills found")
    for skill_dir in skill_dirs:
        path = skill_dir / "SKILL.md"
        if not path.is_file():
            error(str(skill_dir), "skill directory has no SKILL.md")
            continue
        meta = frontmatter(path.read_text(encoding="utf-8"))
        if meta is None:
            error(str(path), "missing or unparsable YAML frontmatter")
            continue
        name = meta.get("name")
        if name != skill_dir.name:
            error(str(path), f"name {name!r} must match the directory name {skill_dir.name!r}")
        if not isinstance(name, str) or len(name) > NAME_MAX or not NAME_RE.match(name):
            error(str(path), f"name must be lowercase letters, digits and hyphens, at most {NAME_MAX} characters")
        description = meta.get("description")
        if not isinstance(description, str) or not description.strip():
            error(str(path), "description is required")
        elif len(description) > DESCRIPTION_MAX:
            error(str(path), f"description is {len(description)} characters; the limit is {DESCRIPTION_MAX}")
        if not meta.get("license"):
            error(str(path), "license is required")
        if skill_version(path.read_text(encoding="utf-8")) is None:
            error(str(path), "metadata.version is required")


def check_version_bumps(base: str) -> None:
    changed = git("diff", "--name-only", f"{base}...HEAD", "--", "plugin/").split()
    shipped = [f for f in changed if f not in BUMP_EXEMPT]
    if not shipped:
        print("No plugin changes that need a version bump.")
        return

    base_manifest = at_ref(base, PLUGIN_MANIFEST)
    if base_manifest is not None:
        old = str(json.loads(base_manifest).get("version"))
        new = str(json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8")).get("version"))
        if not is_bump(old, new):
            error(
                str(PLUGIN_MANIFEST),
                f"plugin files changed ({', '.join(shipped)}) but the version went from {old} to {new}, not up. "
                "Bump it in every plugin/*/plugin.json and root marketplace.json, or existing users won't get the change.",
            )

    for skill_dir in sorted({Path(f).parts[2] for f in shipped if f.startswith(f"{SKILLS_DIR}/")}):
        path = SKILLS_DIR / skill_dir / "SKILL.md"
        old = skill_version(at_ref(base, path))
        new = skill_version(path.read_text(encoding="utf-8")) if path.is_file() else None
        if old is not None and new is not None and not is_bump(old, new):
            warning(str(path), f"skill files changed but metadata.version went from {old} to {new}, not up")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="git ref to compare against for version bumps")
    args = parser.parse_args()
    check_frontmatter()
    if args.base:
        check_version_bumps(args.base)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
