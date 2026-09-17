#!/usr/bin/env python3
"""Fail if a login password is written into the seed and demo scripts.

Why this exists
---------------
The repository history scan of 2026-09-17 found three shared demo passwords
sitting in public code, for sites anyone on the internet can reach. Slice 015
took them out: every seed script now reads its password from an environment
variable and stops if it is not set.

That fix only stays fixed if something checks. This is that something. It is a
plain text check - no bench, no database - run by the CI lint job, in the same
shape as scripts/check_api_paths.py and scripts/check_nginx_conf.py.

It lives here rather than in a Frappe test because CI copies only hrms/,
alvoraa_goals/ and alvoraa_portal/ into the bench. demo/ never gets there, so a
unittest could not see the files it is meant to guard and would skip forever.

What counts as a failure
------------------------
A string literal assigned to something password-shaped, or handed to a
password-shaped key, whose value is not empty and does not come from the
environment or a placeholder. Test files are not scanned: made-up values are
their input, not a credential.

Run it by hand from the repository root:

    python scripts/check_no_demo_passwords.py
"""

from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where a leaked demo password would actually do damage: the seed scripts, and
# the docs that tell someone how to run them.
SCAN_DIRS = [
    "demo",
    "docs/pp_jewellers",
]

# Single files outside those folders that seed users.
SCAN_FILES = [
    "alvoraa_portal/alvoraa_portal/demo_setup.py",
]

SCAN_SUFFIXES = (".py", ".sh", ".md", ".js", ".json", ".yml", ".yaml")

# Test files are input data, not credentials - the scan of 2026-09-17 judged
# them harmless and they are not seeded onto any real site.
SKIP_PARTS = ("/tests/", "\\tests\\", "test_", "__pycache__", "node_modules")

# password = "..." / "new_password": "..." / PPJ_DEMO_PASSWORD='...'
ASSIGN = re.compile(
    r"""(?ix)
    (?P<key>[A-Za-z_][A-Za-z0-9_\-]*
        (?:password|passwd|pwd|secret|admin_pass)
        [A-Za-z0-9_\-]*)
    \s* (?: = | :=? ) \s*
    (?P<q>["'])(?P<val>.*?)(?P=q)
    """
)

# `Ppj@2026`, `Hr@2026` — a password quoted in a markdown sentence.
MARKDOWN_PW = re.compile(
    r"(?i)password[^\n`]{0,40}`(?P<val>[^`\n]{4,64})`"
)

# Values that are not a password: empty, an environment read, a placeholder, a
# variable reference, or a shell/template expansion.
SAFE_VALUE = re.compile(
    r"""(?x)
    ^\s*$                                  # empty  -> the fail-closed default
    | ^<.*>$                               # <a new, strong password>
    | ^\$                                  # $VAR, ${VAR}
    | ^\{\{ | ^%\(                         # {{ secrets.X }}, %(name)s
    | ^(?:x{3,}|\*{3,}|\.{3,})$            # xxxx, ****
    | ^(?:none|null|true|false)$
    | PASSWORD                             # the name of the variable itself
    """,
    re.IGNORECASE,
)


def _files() -> list[str]:
    out: list[str] = []
    for rel in SCAN_DIRS:
        base = os.path.join(ROOT, rel)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in ("__pycache__", "node_modules")]
            for name in filenames:
                if name.endswith(SCAN_SUFFIXES):
                    out.append(os.path.join(dirpath, name))
    for rel in SCAN_FILES:
        path = os.path.join(ROOT, rel)
        if os.path.exists(path):
            out.append(path)
    return [p for p in out if not any(s in p.replace("\\", "/") for s in SKIP_PARTS)]


def _mask(value: str) -> str:
    """Never print the thing we are complaining about."""
    return (value[:2] + "...") if len(value) > 2 else "..."


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
            if "check_no_demo_passwords" in line:
                continue
            for match in ASSIGN.finditer(line):
                value = match.group("val")
                if SAFE_VALUE.search(value):
                    continue
                findings.append(
                    f"{rel}:{number}: {match.group('key')} is set to a literal "
                    f"value ({_mask(value)}) - read it from an environment "
                    f"variable and stop if it is not set"
                )
            if rel.endswith(".md"):
                for match in MARKDOWN_PW.finditer(line):
                    value = match.group("val")
                    if SAFE_VALUE.search(value) or value.isupper() or " " in value:
                        continue
                    findings.append(
                        f"{rel}:{number}: a password ({_mask(value)}) is written "
                        f"in the document - name the environment variable instead"
                    )

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

    print("No demo or seed password literals found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
