# Copyright 2026 Agentic Data Intelligence SA
# SPDX-License-Identifier: Apache-2.0
"""Check a PR's commits and description before anything lands on main.

Usage:
  check_commit_hygiene.py --base SHA [--head SHA]   check (what CI runs)
  check_commit_hygiene.py --fix --base origin/main  rewrite the current branch

- Every commit's author and committer email must be a GitHub noreply address,
  so personal emails stay out of the public history. (GitHub Team cannot
  enforce this with a ruleset; commit metadata rules are Enterprise-only.)
- Commit messages, and the PR title and body (read from the PR_TITLE and
  PR_BODY environment variables), must not carry AI-assistant session links
  or co-author / "generated with" attribution trailers.

--fix rebases every commit after --base onto it, drops the offending lines
from each message, and replaces a non-noreply author with your own git
identity (which must already be a noreply address). Push the result with
`git push --force-with-lease`. The PR description has to be edited by hand.

"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# <id>+<user>@users.noreply.github.com, or noreply@github.com (GitHub's own web commits).
NOREPLY_EMAIL = re.compile(r"^(noreply@github\.com|[^@\s]+@users\.noreply\.github\.com)$", re.IGNORECASE)

# Each entry: (description shown in the error, pattern). Matched case-insensitively
# per line, so a trailer anywhere in a message or description is caught.
FORBIDDEN = [
    ("Claude Code session link", re.compile(r"claude\.ai/code/session_")),
    ("Claude-Session trailer", re.compile(r"^\s*claude-session\s*:")),
    ("Claude/Anthropic co-author trailer", re.compile(r"^\s*co-authored-by\s*:.*\b(claude|anthropic)\b")),
    # Any other "<something>-by:" trailer naming Claude/Anthropic (Assisted-by, Generated-by, Signed-off-by, ...).
    (
        "Claude/Anthropic attribution trailer",
        re.compile(r"^\s*(?!co-authored-by)[a-z][a-z-]*-by\s*:.*\b(claude|anthropic)\b"),
    ),
    ("Anthropic noreply address", re.compile(r"noreply@anthropic\.com")),
    ("Anthropic email address", re.compile(r"@anthropic\.com\b")),
    ("'Generated with Claude' attribution", re.compile(r"generated (with|by) \[?(claude|anthropic)")),
    ("Claude Code attribution link", re.compile(r"claude\.com/claude-code")),
]

errors = 0


def error(message: str, file: str | None = None) -> None:
    global errors
    errors += 1
    location = f" file={file}" if file else ""
    print(f"::error{location}::{message}")


def forbidden_in(text: str) -> list[str]:
    found = []
    for line in text.splitlines():
        for label, pattern in FORBIDDEN:
            if pattern.search(line.lower()) and label not in found:
                found.append(label)
    return found


def clean_message(message: str) -> str:
    kept = [line for line in message.splitlines() if not forbidden_in(line)]
    cleaned = "\n".join(kept).strip()
    return cleaned + "\n" if cleaned else ""


def git(*args: str, stdin: str | None = None) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True, input=stdin).stdout.strip()


def own_noreply_email() -> str | None:
    email = subprocess.run(["git", "config", "user.email"], capture_output=True, text=True).stdout.strip()
    return email if NOREPLY_EMAIL.search(email) else None


def commits(base: str, head: str) -> list[dict[str, str]]:
    sep, end = "\x1f", "\x1e"
    out = subprocess.run(
        ["git", "log", f"--format=%H{sep}%an{sep}%ae{sep}%cn{sep}%ce{sep}%B{end}", f"{base}..{head}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    result = []
    for record in out.split(end):
        record = record.strip("\n")
        if not record:
            continue
        sha, an, ae, cn, ce, body = record.split(sep, 5)
        result.append(
            {"sha": sha, "author": an, "author_email": ae, "committer": cn, "committer_email": ce, "message": body}
        )
    return result


def check(base: str, head: str) -> int:
    pr_commits = commits(base, head)
    for c in pr_commits:
        short = c["sha"][:7]
        for role in ("author", "committer"):
            email = c[f"{role}_email"]
            if not NOREPLY_EMAIL.search(email):
                error(f"commit {short}: {role} email {email} is not a GitHub noreply address.")
        for label in forbidden_in(c["message"]):
            error(f"commit {short}: message contains: {label}.")

    for field in ("PR_TITLE", "PR_BODY"):
        for label in forbidden_in(os.environ.get(field, "")):
            error(f"PR {'title' if field == 'PR_TITLE' else 'description'} contains: {label}. Edit it out.")

    print(f"Checked {len(pr_commits)} commit(s) and the PR title and description.")
    if errors:
        print(
            "\nTo fix the commits, rewrite the branch:\n"
            "  1. git config --global user.email <id>+<username>@users.noreply.github.com"
            "  (yours is on https://github.com/settings/emails)\n"
            f"  2. python3 .github/scripts/check_commit_hygiene.py --fix --base origin/{os.environ.get('GITHUB_BASE_REF', 'main')}\n"
            "  3. git push --force-with-lease"
        )
    return 1 if errors else 0


def amend_head() -> int:
    """Run by --fix on each rebased commit: clean the message, fix the author."""
    author_email = git("log", "-1", "--format=%ae")
    message = git("log", "-1", "--format=%B")
    # --allow-empty-message: a commit whose whole message was attribution ends up empty.
    cmd = [
        "commit",
        "--amend",
        "--no-verify",
        "--allow-empty",
        "--allow-empty-message",
        "--cleanup=verbatim",
        "-F",
        "-",
    ]
    if not NOREPLY_EMAIL.search(author_email):
        cmd.append("--reset-author")
        print(f"  {git('rev-parse', '--short', 'HEAD')}: author {author_email} -> {git('config', 'user.email')}")
    git(*cmd, stdin=clean_message(message))
    return 0


def fix(base: str) -> int:
    if own_noreply_email() is None:
        print(
            "Your git user.email is not a GitHub noreply address, so rewritten commits would still expose it.\n"
            "Run: git config --global user.email <id>+<username>@users.noreply.github.com",
            file=sys.stderr,
        )
        return 1
    if git("status", "--porcelain"):
        print("Commit or stash your changes first; --fix rewrites the current branch.", file=sys.stderr)
        return 1
    to_fix = commits(base, "HEAD")
    if not to_fix:
        print(f"No commits after {base}; nothing to rewrite.")
        return 0
    # The rebase checks out older commits, which may not contain this script.
    with tempfile.TemporaryDirectory() as tmp:
        script = Path(tmp) / "check_commit_hygiene.py"
        shutil.copy(__file__, script)
        print(f"Rewriting {len(to_fix)} commit(s) after {base}:", flush=True)
        result = subprocess.run(
            ["git", "rebase", "--rebase-merges", "--exec", f'"{sys.executable}" "{script}" --amend-head', base]
        )
    if result.returncode != 0:
        print("Rebase stopped; resolve it (or `git rebase --abort`) and run --fix again.", file=sys.stderr)
        return result.returncode
    print("Done. Review with `git log`, then push with: git push --force-with-lease")
    return check(base, "HEAD")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", help="PR base commit or branch (e.g. origin/main)")
    parser.add_argument("--head", default="HEAD", help="PR head commit (default: HEAD)")
    parser.add_argument("--fix", action="store_true", help="rewrite the current branch's commits after --base")
    parser.add_argument("--amend-head", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.amend_head:
        return amend_head()
    if not args.base:
        parser.error("--base is required")
    return fix(args.base) if args.fix else check(args.base, args.head)


if __name__ == "__main__":
    sys.exit(main())
