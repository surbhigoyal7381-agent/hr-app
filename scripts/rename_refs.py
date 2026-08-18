"""Rewrite doctype names and app prefixes across the codebase, safely.

These names are referenced as plain strings - in Python (`frappe.get_doc("X", ...)`),
in raw SQL (`tabX`), and in front-end call paths. Nothing in the build checks them, so
they are rewritten with explicit, ordered pairs rather than a blanket find-and-replace.

Dry-run by default. Nothing is written without --apply.

    python scripts/rename_refs.py --mode doctypes-to-grace
    python scripts/rename_refs.py --mode doctypes-to-grace --apply

Modes:
    doctypes-to-alvoraa   Alvox * -> Alvoraa *    (Phase 2, run with the rename_doc patch)
    portal-to-alvoraa     alvoraa_portal -> alvoraa_portal   (Phase 4)
    goals-to-alvoraa      alvoraa_goals  -> alvoraa_goals    (Phase 4)

The servers already run the Alvox names (verified on dev.alvoraa.co 2026-08-18:
apps are alvoraa_goals / alvoraa_portal, doctypes are "Alvox Cycle Config" etc). The
repo DIRECTORIES still say grace_*, but the deployed identifiers do not. So the
remaining rename is Alvox -> Alvoraa, NOT Grace -> Alvoraa.
"""

import argparse
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_DIRS = ["alvoraa_goals", "alvoraa_portal"]
SCAN_EXTS = (".py", ".js", ".html", ".json", ".md", ".txt")
SKIP_DIRS = {".git", "node_modules", "__pycache__", "worktrees", "backups",
             ".pytest_cache", "dist", "build", ".claude"}

# Longest first - "Rating Scale Item" must be rewritten before "Rating Scale",
# otherwise it becomes "Grace Rating Scale Item" via a partial match.
DOCTYPES = ["Rating Scale Item", "Appraisal Extension", "Cycle Config", "Rating Scale"]


def pairs_for(mode):
	if mode == "doctypes-to-alvoraa":
		old, new = "Alvox", "Alvoraa"
		out = []
		for d in DOCTYPES:
			out.append(("tab%s %s" % (old, d), "tab%s %s" % (new, d)))   # raw SQL table
			out.append(("%s %s" % (old, d), "%s %s" % (new, d)))         # doctype name
		return out
	if mode == "portal-to-alvoraa":
		return [("alvoraa_portal.", "alvoraa_portal.")]
	if mode == "goals-to-alvoraa":
		return [("alvoraa_goals.", "alvoraa_goals.")]
	raise SystemExit("unknown mode: %s" % mode)


def iter_files():
	for base in SCAN_DIRS:
		root = os.path.join(REPO, base)
		if not os.path.isdir(root):
			continue
		for dirpath, dirnames, filenames in os.walk(root):
			dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
			for fn in filenames:
				if fn.endswith(SCAN_EXTS):
					yield os.path.join(dirpath, fn)


def main():
	ap = argparse.ArgumentParser(description=__doc__,
	                             formatter_class=argparse.RawDescriptionHelpFormatter)
	ap.add_argument("--mode", required=True)
	ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
	args = ap.parse_args()

	subs = pairs_for(args.mode)
	total, touched = 0, []
	for path in iter_files():
		with open(path, "rb") as fh:
			raw = fh.read()
		out, n = raw, 0
		for old, new in subs:
			cnt = out.count(old.encode())
			if cnt:
				out = out.replace(old.encode(), new.encode())
				n += cnt
		if n:
			total += n
			touched.append((os.path.relpath(path, REPO).replace("\\", "/"), n))
			if args.apply:
				with open(path, "wb") as fh:
					fh.write(out)

	print("mode: %s" % args.mode)
	for old, new in subs:
		print("   %-34s -> %s" % (old, new))
	print("")
	for rel, n in sorted(touched, key=lambda r: -r[1]):
		print("  %4d  %s" % (n, rel))
	print("")
	print("%s: %d replacement(s) across %d file(s)" % (
		"APPLIED" if args.apply else "DRY RUN (nothing written)", total, len(touched)))
	return 0


if __name__ == "__main__":
	sys.exit(main())
