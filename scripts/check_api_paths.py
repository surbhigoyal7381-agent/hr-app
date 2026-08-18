"""Verify that every dotted API path used by the front-end resolves to a real
whitelisted Python function.

Frappe resolves `frappe.call({method: "app.module.func"})` at *runtime*. Nothing in the
build, the linter, or `bench migrate` catches a path that points nowhere — it fails when a
user clicks a button. This script turns that runtime contract into a build-time check, which
is the guard rail an app/module rename needs.

Usage
-----
    python scripts/check_api_paths.py                  # check against current directory names
    python scripts/check_api_paths.py --alias alvox_portal=grace_vendor_portal
    python scripts/check_api_paths.py --json           # machine-readable, for CI

Exit codes: 0 = all paths resolve, 1 = at least one unresolved path.
"""

import argparse
import ast
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Directories holding front-end assets that may contain dotted API paths.
SCAN_DIRS = ["grace_goals", "grace_vendor_portal", "alvox_compensation", "hrms"]
SCAN_EXTS = (".html", ".js", ".vue", ".jsx", ".ts")
SKIP_DIRS = {".git", "node_modules", "__pycache__", "worktrees", "backups",
             ".pytest_cache", "dist", "build", ".claude"}

# app name -> filesystem directory holding the python package.
# An app installed as `X` is importable as `X`; its package lives at <dir>/<dir>/.
APP_DIRS = {
    "grace_goals": "grace_goals",
    "grace_vendor_portal": "grace_vendor_portal",
    "alvox_compensation": "alvox_compensation",
    "hrms": "hrms",
    # Rename targets AND superseded names. Both must be listed: a head that is not in
    # this dict is skipped by extract_paths(), so dropping the old names would make the
    # broken paths vanish from the report instead of being reported as broken.
    # These map to directories that do not exist, so they resolve to "no-app".
    "alvoraa_goals": "alvoraa_goals",
    "alvoraa_portal": "alvoraa_portal",
    "alvox_goals": "alvox_goals",      # superseded by alvoraa_goals
    "alvox_portal": "alvox_portal",    # superseded; 21 committed front-end calls still use it
    "frappe": None,      # not vendored here — cannot verify, treated as external
    "erpnext": None,
}

# app.module.func — at least three segments, lowercase python identifiers.
DOTTED = re.compile(r"""["'`]([a-z][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*){2,})["'`]""")


def iter_frontend_files():
    for base in SCAN_DIRS:
        root_dir = os.path.join(REPO, base)
        if not os.path.isdir(root_dir):
            continue
        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                if fn.endswith(SCAN_EXTS):
                    yield os.path.join(dirpath, fn)


def extract_paths():
    """Return {dotted_path: [(relative_file, line_no), ...]}."""
    found = {}
    for path in iter_frontend_files():
        try:
            with io.open(path, encoding="utf-8", errors="ignore") as fh:
                lines = fh.readlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            for match in DOTTED.findall(line):
                head = match.split(".")[0]
                if head not in APP_DIRS:
                    continue  # not an app path; ignore css classes, urls, etc.
                rel = os.path.relpath(path, REPO).replace("\\", "/")
                found.setdefault(match, []).append((rel, i))
    return found


def whitelisted_functions(py_file):
    """Return the set of function names decorated with @frappe.whitelist in a file."""
    try:
        # utf-8-sig: matches Python's own source loading, which strips a UTF-8 BOM.
        with io.open(py_file, encoding="utf-8-sig", errors="ignore") as fh:
            tree = ast.parse(fh.read(), filename=py_file)
    except (OSError, SyntaxError):
        return None
    names = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            target = dec.func if isinstance(dec, ast.Call) else dec
            attr = getattr(target, "attr", None) or getattr(target, "id", None)
            if attr == "whitelist":
                names.add(node.name)
    return names


def resolve(dotted, aliases):
    """Resolve 'app.module.sub.func' -> (status, detail)."""
    parts = dotted.split(".")
    app, rest, func = parts[0], parts[1:-1], parts[-1]

    real_app = aliases.get(app, app)
    app_dir = APP_DIRS.get(real_app, real_app)
    if app_dir is None:
        return "external", "%s not vendored in this repo" % real_app

    pkg = os.path.join(REPO, app_dir, real_app)
    if not os.path.isdir(pkg):
        return "no-app", "no package at %s/%s/" % (app_dir, real_app)

    # A module may be a file (foo.py) or a package (foo/__init__.py).
    stem = os.path.join(pkg, *rest)
    if os.path.isfile(stem + ".py"):
        module_file = stem + ".py"
    elif os.path.isfile(os.path.join(stem, "__init__.py")):
        module_file = os.path.join(stem, "__init__.py")
    else:
        return "no-module", "no %s.py or %s/__init__.py" % (
            os.path.relpath(stem, REPO).replace("\\", "/"),
            os.path.relpath(stem, REPO).replace("\\", "/"))

    fns = whitelisted_functions(module_file)
    if fns is None:
        return "unparsed", "could not parse module"
    if func not in fns:
        return "no-func", "%s not @frappe.whitelist in %s" % (
            func, os.path.relpath(module_file, REPO).replace("\\", "/"))
    return "ok", ""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--alias", action="append", default=[], metavar="INSTALLED=DIR",
                    help="treat app INSTALLED as living in directory DIR "
                         "(e.g. alvox_portal=grace_vendor_portal)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--max", type=int, default=0, metavar="N",
                    help="tolerate up to N unresolved paths (known debt). Exits non-zero only "
                         "if the count EXCEEDS N, so regressions fail the build while existing "
                         "debt does not. Lower this as the debt is paid down.")
    args = ap.parse_args()

    aliases = {}
    for a in args.alias:
        if "=" not in a:
            ap.error("--alias expects INSTALLED=DIR, got %r" % a)
        k, v = a.split("=", 1)
        aliases[k] = v
        APP_DIRS.setdefault(v, v)
        APP_DIRS.setdefault(k, v)

    paths = extract_paths()
    results = {}
    for dotted, sites in sorted(paths.items()):
        status, detail = resolve(dotted, aliases)
        results[dotted] = {"status": status, "detail": detail,
                           "used_in": ["%s:%d" % s for s in sites]}

    broken = {k: v for k, v in results.items()
              if v["status"] not in ("ok", "external")}

    over = len(broken) > args.max

    if args.json:
        print(json.dumps({"total": len(results), "broken": len(broken),
                          "max_allowed": args.max, "results": results}, indent=2))
        return 1 if over else 0

    ok = sum(1 for v in results.values() if v["status"] == "ok")
    ext = sum(1 for v in results.values() if v["status"] == "external")
    print("Scanned front-end assets for dotted API paths.")
    print("  total distinct paths : %d" % len(results))
    print("  resolved             : %d" % ok)
    print("  external (skipped)   : %d" % ext)
    print("  UNRESOLVED           : %d" % len(broken))

    if broken:
        by_reason = {}
        for k, v in broken.items():
            by_reason.setdefault(v["status"], []).append((k, v))
        print("")
        for reason in sorted(by_reason):
            print("--- %s (%d)" % (reason, len(by_reason[reason])))
            for dotted, info in sorted(by_reason[reason]):
                print("    %s" % dotted)
                print("        %s" % info["detail"])
                print("        used in: %s" % ", ".join(info["used_in"][:3]))

    print("")
    if over:
        print("FAIL: %d unresolved exceeds the allowed maximum of %d." % (len(broken), args.max))
        print("      A front-end call points at a Python function that does not exist.")
    elif broken:
        print("OK (within tolerance): %d unresolved, maximum allowed %d." % (len(broken), args.max))
        print("      Known debt - lower --max as these are fixed.")
    else:
        print("OK: every front-end API path resolves.")
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main())
