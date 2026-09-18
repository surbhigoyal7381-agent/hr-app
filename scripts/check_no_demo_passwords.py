#!/usr/bin/env python3
"""Fail if a login password is written into the seed and demo scripts.

Why this exists
---------------
The repository history scan of 2026-09-17 found three shared demo passwords
sitting in public code, for sites anyone on the internet can reach. Slice 015
took them out: every script that creates users now reads its password from an
environment variable and stops if it is not set.

That fix only stays fixed if something checks. This is that something. It is a
plain text check - no bench, no database - run by the CI lint job, in the same
shape as scripts/check_api_paths.py and scripts/check_nginx_conf.py.

It lives here rather than in a Frappe test because CI copies only hrms/,
alvoraa_goals/ and alvoraa_portal/ into the bench. demo/ never gets there, so a
unittest could not see the files it is meant to guard and would skip for ever.

**This file scans itself.** The first version carried the two real leaked values
in a comment, which is exactly the thing it exists to stop. Nothing in here may
contain a password-shaped assignment, and no example may be a real value.

What counts as a failure
------------------------
1. A password-shaped name given a literal value, in any of the shapes that
   have actually appeared in this repository: a module constant such as
   DEMO_PASSWORD; a plain local called password; a dict key such as
   new_password handed to frappe.get_doc; and an unquoted shell assignment
   of a variable whose name ends in PASSWORD. No example of one is written
   out here, because this file scans itself.
2. A password written between backticks in a document.

A value is fine when it is empty (the fail-closed default), a placeholder in
angle brackets, or a reference to something else - an environment variable, a
shell variable, a template expansion.

Test files are not scanned: made-up values are their input, not a credential.

Run it by hand from the repository root:

    python scripts/check_no_demo_passwords.py
"""

from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Folders where a leaked password would end up on a real tenant.
SCAN_DIRS = [
    "demo",
    "docs/pp_jewellers",
]

# Files outside those folders that create users, plus this script itself.
SCAN_FILES = [
    "alvoraa_portal/alvoraa_portal/demo_setup.py",
    "alvoraa_portal/alvoraa_portal/demo_seeder.py",
    "scripts/check_no_demo_passwords.py",
]

SCAN_SUFFIXES = (".py", ".sh", ".md", ".js", ".json", ".yml", ".yaml", ".txt")

SKIP_DIR_NAMES = {"__pycache__", "node_modules", "tests", "test"}

WORDS = r"password|passwd|pwd|secret|admin_pass"

# A password-shaped key given a quoted value: a module constant, a plain local,
# or a dict key such as the one frappe.get_doc takes for a new user's password.
# The optional quote after the key is what catches the dict-key form, which the
# first version of this check missed - and that was the exact line that had to
# be removed from demo_setup.py.
QUOTED_ASSIGN = re.compile(
    rf"""(?ix)
    (?<![A-Za-z0-9_\-])
    (?P<key>[A-Za-z0-9_\-]* (?:{WORDS}) [A-Za-z0-9_\-]*)
    ["']? \s* (?: = | : ) =? \s*
    (?P<q>["'])(?P<val>.*?)(?P=q)
    """
)

# An unquoted shell assignment - the shape that would appear in run_all.sh or
# in a docker exec line. A quoted value is left to QUOTED_ASSIGN above, so the
# value here may not start with a quote.
SHELL_ASSIGN = re.compile(
    rf"""(?ix)
    (?<![A-Za-z0-9_\-])
    (?P<key>[A-Za-z0-9_]* (?:{WORDS}) [A-Za-z0-9_]*)
    = (?P<val>[^\s"'`#;)\]]+)
    """
)

# A password quoted in a sentence in a document.
MARKDOWN_PW = re.compile(r"(?i)password[^\n`]{0,40}`(?P<val>[^`\n]{4,64})`")

# Values that are not a password: empty, a placeholder, or a reference to
# something else. There is deliberately NO "contains the word password" escape
# here - the first version had one, and it waved through a literal that merely
# contained that word.
SAFE_VALUE = re.compile(
    r"""(?x)
    ^\s*$                                  # empty -> the fail-closed default
    | ^<.*>$                               # <a new, strong password>
    | ^\$                                  # $VAR, ${VAR}
    | ^\{\{ | ^%\( | ^\{[A-Za-z_]          # {{ secrets.X }}, %(name)s, {value}
    | ^(?:x{3,}|\*{3,}|\.{3,}|-{3,})$      # xxxx, ****, ----
    | ^(?:none|null|true|false|0|1)$
    | ^(?:os\.environ|environ|getenv)      # a value read from the environment
    """,
    re.IGNORECASE,
)


def _is_test_path(rel: str) -> bool:
    """True for a test file. Matched on path PARTS, not as a substring.

    The first version matched "test_" anywhere in the path, so a folder like
    demo/latest_helpers/ was skipped by accident.
    """
    parts = rel.split("/")
    if any(part in ("tests", "test") for part in parts[:-1]):
        return True
    name = parts[-1]
    return name.startswith("test_") or name.endswith(("_test.py", "_tests.py"))


def _files() -> list[str]:
    out: list[str] = []
    for rel in SCAN_DIRS:
        base = os.path.join(ROOT, rel)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES]
            for name in filenames:
                if name.endswith(SCAN_SUFFIXES):
                    out.append(os.path.join(dirpath, name))
    for rel in SCAN_FILES:
        path = os.path.join(ROOT, rel)
        if os.path.exists(path):
            out.append(path)

    keep = []
    for path in out:
        rel = os.path.relpath(path, ROOT).replace("\\", "/")
        if not _is_test_path(rel):
            keep.append(path)
    return keep


def _mask(value: str) -> str:
    """Never print the thing we are complaining about."""
    return (value[:2] + "...") if len(value) > 2 else "..."


def scan_line(rel: str, line: str) -> list[str]:
    """Every complaint about one line. Separate so a harness can drive it."""
    found = []
    for match in QUOTED_ASSIGN.finditer(line):
        if not SAFE_VALUE.search(match.group("val")):
            found.append(
                f"{match.group('key')} is set to a literal value "
                f"({_mask(match.group('val'))}) - read it from an environment "
                f"variable and stop if it is not set"
            )
    for match in SHELL_ASSIGN.finditer(line):
        if not SAFE_VALUE.search(match.group("val")):
            found.append(
                f"{match.group('key')} is set to a literal value "
                f"({_mask(match.group('val'))}) - pass it in from the "
                f"environment instead"
            )
    if rel.endswith(".md"):
        for match in MARKDOWN_PW.finditer(line):
            value = match.group("val")
            if SAFE_VALUE.search(value) or value.isupper() or " " in value:
                continue
            found.append(
                f"a password ({_mask(value)}) is written in the document - "
                f"name the environment variable instead"
            )
    return found


def main() -> int:
    findings: list[str] = []

    for path in _files():
        rel = os.path.relpath(path, ROOT).replace("\\", "/")
        try:
            with open(path, encoding="utf-8") as handle:
                lines = handle.read().splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(lines, 1):
            findings.extend(f"{rel}:{number}: {note}" for note in scan_line(rel, line))

    if findings:
        print("Demo or seed passwords must not be written into the repository.")
        print("The 2026-09-17 history scan found three of them live on public sites.")
        print("")
        for line in findings:
            print(f"  {line}")
        print("")
        print("Fix: read the value from an environment variable and stop with a")
        print("clear message when it is not set. Never add a built-in default.")
        return 1

    print(f"No demo or seed password literals found ({len(_files())} files scanned).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
