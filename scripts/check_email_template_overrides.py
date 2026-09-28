"""ALV-174: our own email-template overrides must not drift back to saying
"Frappe" or "ERPNext" - the whole reason they exist.

Narrow on purpose: this is not the brand-spelling guard (`check_brand_spelling.py`
checks for the wrong SPELLING of our own name, "Alvoraa" where a person reads
it). This checks for the WRONG BRAND - "Frappe"/"ERPNext" - appearing in the
handful of files that exist specifically to replace an upstream app's own
branded email text (`alvoraa_portal/templates/emails/`,
`alvoraa_portal/overrides/`). If an upstream app is upgraded and one of these
is hand-copied from the new version without editing it, this fails instead of
a customer noticing.

It skips comments (HTML/Jinja `<!-- -->` `{# #}`, Python docstrings and `#`
lines) on purpose - the files' own comments explain the Frappe/ERPNext bug
they are fixing, in plain English, and that is not something a user reads.

ALV-175 added a second, separate job: some of these files (`standard.html`)
are not new content but a byte-for-byte copy of an upstream file with one
deliberate change, and they say so in a comment that records the upstream
file's sha256. `--check-upstream-shape` reads that comment and compares the
hash against the upstream file as ACTUALLY INSTALLED, so a Frappe/ERPNext/CRM/
Helpdesk upgrade that reshapes the file we copied from gets caught here
instead of silently shipping a stale override.

    python scripts/check_email_template_overrides.py              # fail on any hit
    python scripts/check_email_template_overrides.py --report      # list hits, exit 0
    python scripts/check_email_template_overrides.py --self-test   # prove it can fail
    python scripts/check_email_template_overrides.py --check-upstream-shape
"""
import argparse
import ast
import hashlib
import os
import re
import shutil
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGETS = (
	"alvoraa_portal/alvoraa_portal/templates/emails",
	"alvoraa_portal/alvoraa_portal/overrides",
)
BRAND = re.compile(r"\bFrappe\b|\bERPNext\b")

HTML_COMMENTS = (
	re.compile(r"<!--.*?-->", re.S),
	re.compile(r"\{#.*?#\}", re.S),
)


def _read(path):
	return open(path, encoding="utf-8-sig", errors="ignore").read()


def _blank(m):
	return re.sub(r"[^\n]", " ", m.group(0))


def scan_html(path):
	text = _read(path)
	stripped = text
	for rx in HTML_COMMENTS:
		stripped = rx.sub(_blank, stripped)
	out = []
	for m in BRAND.finditer(stripped):
		n = stripped.count("\n", 0, m.start()) + 1
		out.append((path, n, text.splitlines()[n - 1].strip()[:140]))
	return out


def scan_python(path):
	text = _read(path)
	if not BRAND.search(text):
		return []
	try:
		tree = ast.parse(text)
	except SyntaxError:
		return [(path, 1, "could not parse this file")]

	skip = set()
	for node in ast.walk(tree):
		# docstrings and any other bare string statement: our own explanation,
		# not text a user reads
		if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
				and isinstance(node.value.value, str):
			skip.add(id(node.value))

	out = []
	for node in ast.walk(tree):
		if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
			continue
		if id(node) in skip or not BRAND.search(node.value):
			continue
		out.append((path, node.lineno, node.value.strip().replace("\n", " ")[:140]))
	return out


def scan(root):
	hits = []
	for top in TARGETS:
		base = os.path.join(root, top)
		if not os.path.isdir(base):
			continue
		for folder, dirs, files in os.walk(base):
			dirs[:] = sorted(d for d in dirs if d != "__pycache__")
			for name in sorted(files):
				path = os.path.join(folder, name)
				if name.endswith((".html", ".js")):
					hits += scan_html(path)
				elif name.endswith(".py") and not name.startswith("test_"):
					hits += scan_python(path)
	return hits


def check(root, report=False):
	hits = scan(root)
	for path, n, what in hits:
		print(f"{os.path.relpath(path, root)}:{n}: {what}")
	print(f"email template overrides: {len(hits)} 'Frappe'/'ERPNext' hit(s)")
	if not hits:
		print("OK - our own overrides do not say Frappe or ERPNext")
		return 0
	if report:
		print("REPORT ONLY - not failing")
		return 0
	print("FAIL - one of our own email-override files still says Frappe or "
	      "ERPNext where a recipient would read it (ALV-174).")
	return 1


def _find_bench_apps():
	"""Locate an installed bench's apps/ directory, or None. Same probing as
	check_app_integrity.py's _find_bench_apps - kept separate, not imported,
	because these are two independent standalone scripts by design."""
	env = os.environ.get("BENCH_APPS_PATH")
	if env:
		return env if os.path.isdir(os.path.join(env, "frappe")) else None
	candidates = [
		"/home/frappe/frappe-bench/apps",
		os.path.expanduser("~/frappe-bench/apps"),
		os.path.join(os.path.dirname(REPO), "frappe-bench", "apps"),
	]
	for c in candidates:
		if os.path.isdir(os.path.join(c, "frappe")):
			return c
	return None


UPSTREAM_HASH_LINE = re.compile(
	r"sha256\s+of\s+the\s+unmodified\s+([\w./-]+)\s+this\s+file\s+was\s+copied"
	r"\s+from\s*\(([^)]*)\):\s*([0-9a-f]{64})"
)


def _declared_upstream_hashes(root):
	"""(override_path, upstream_relpath, version, declared_sha256) for every
	override file that names the upstream file it was copied from."""
	out = []
	for top in TARGETS:
		base = os.path.join(root, top)
		if not os.path.isdir(base):
			continue
		for folder, dirs, files in os.walk(base):
			dirs[:] = sorted(d for d in dirs if d != "__pycache__")
			for name in sorted(files):
				path = os.path.join(folder, name)
				m = UPSTREAM_HASH_LINE.search(_read(path))
				if m:
					out.append((path, m.group(1), m.group(2), m.group(3)))
	return out


def check_upstream_shape(root):
	declared = _declared_upstream_hashes(root)
	if not declared:
		print("no override file declares an upstream sha256 - nothing to check")
		return 0

	apps = _find_bench_apps()
	if not apps:
		print("note: no bench found - skipping the upstream-shape check "
		      "(set BENCH_APPS_PATH to run it)")
		return 0

	bad = 0
	for override_path, upstream_rel, version, declared_hash in declared:
		upstream_path = os.path.join(apps, upstream_rel)
		rel_override = os.path.relpath(override_path, root)
		if not os.path.isfile(upstream_path):
			print(f"{rel_override}: upstream file {upstream_rel} not found on this "
			      f"bench - cannot verify")
			bad += 1
			continue
		actual_hash = hashlib.sha256(open(upstream_path, "rb").read()).hexdigest()
		if actual_hash != declared_hash:
			print(f"{rel_override}: upstream {upstream_rel} has changed shape since "
			      f"it was copied from {version} (declared {declared_hash}, "
			      f"actual {actual_hash}). Read the new upstream file, decide "
			      f"whether the block this override changes still looks the "
			      f"same, and update both files together.")
			bad += 1
		else:
			print(f"{rel_override}: matches the declared upstream {upstream_rel} "
			      f"({version}) - OK")

	print(f"upstream shape: {len(declared)} declared, {bad} changed")
	if bad:
		print("FAIL - an override's upstream file has changed shape (ALV-175).")
		return 1
	print("OK - every override still matches the upstream shape it was copied from")
	return 0


def self_test():
	root = tempfile.mkdtemp(prefix="email-override-self-test-")
	failed = 0
	try:
		good_dir = os.path.join(root, "alvoraa_portal/alvoraa_portal/templates/emails")
		os.makedirs(good_dir, exist_ok=True)
		with open(os.path.join(good_dir, "good.html"), "w", encoding="utf-8") as f:
			f.write("<!-- overrides Frappe's own crm_invitation.html -->\n"
			        "<p>You have been invited to join {{ title }}</p>\n")
		hits = scan(root)
		ok = not hits
		print(("ok   " if ok else "FAIL ") + "a clean override, with an explanatory comment, passes")
		failed += 0 if ok else 1

		bad_dir = os.path.join(root, "alvoraa_portal/alvoraa_portal/overrides")
		os.makedirs(bad_dir, exist_ok=True)
		with open(os.path.join(bad_dir, "bad.py"), "w", encoding="utf-8") as f:
			f.write('"""Replaces Frappe CRM\'s invite email."""\n'
			        'import frappe\n'
			        'def f():\n'
			        '    frappe.sendmail(subject="Join Frappe CRM")\n')
		hits = scan(root)
		ok = any("bad.py" in h[0] for h in hits)
		print(("ok   " if ok else "FAIL ") + "'Frappe CRM' in a live string is caught, the docstring is not")
		failed += 0 if ok else 1
	finally:
		shutil.rmtree(root, ignore_errors=True)

	# ── --check-upstream-shape, without needing a real bench ───────────────
	root = tempfile.mkdtemp(prefix="email-override-shape-self-test-")
	old_env = os.environ.get("BENCH_APPS_PATH")
	try:
		override_dir = os.path.join(root, "alvoraa_portal/alvoraa_portal/templates/emails")
		os.makedirs(override_dir, exist_ok=True)
		upstream_dir = os.path.join(root, "fake-apps/frappe/frappe/templates/emails")
		os.makedirs(upstream_dir, exist_ok=True)
		upstream_content = b"<html>the real frappe template, v16.35.0</html>\n"
		upstream_path = os.path.join(upstream_dir, "standard.html")
		with open(upstream_path, "wb") as f:
			f.write(upstream_content)
		declared_hash = hashlib.sha256(upstream_content).hexdigest()
		with open(os.path.join(override_dir, "standard.html"), "w", encoding="utf-8") as f:
			f.write(
				"{#\nsha256 of the unmodified frappe/frappe/templates/emails/"
				"standard.html this file was copied from (v16.35.0): "
				f"{declared_hash}\n#}}\n<html>our override</html>\n")

		os.environ["BENCH_APPS_PATH"] = os.path.join(root, "fake-apps")
		ok = check_upstream_shape(root) == 0
		print(("ok   " if ok else "FAIL ") + "an override matching its declared upstream hash passes")
		failed += 0 if ok else 1

		with open(upstream_path, "ab") as f:
			f.write(b"<!-- upstream changed -->\n")
		ok = check_upstream_shape(root) == 1
		print(("ok   " if ok else "FAIL ") + "an upstream file that changed shape is caught")
		failed += 0 if ok else 1
	finally:
		if old_env is None:
			os.environ.pop("BENCH_APPS_PATH", None)
		else:
			os.environ["BENCH_APPS_PATH"] = old_env
		shutil.rmtree(root, ignore_errors=True)

	return failed


def main(argv=None):
	parser = argparse.ArgumentParser(description=__doc__,
	                                 formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("--self-test", action="store_true")
	parser.add_argument("--report", action="store_true")
	parser.add_argument("--check-upstream-shape", action="store_true")
	args = parser.parse_args(argv)
	if args.self_test:
		failed = self_test()
		print(f"check_email_template_overrides self-test: {'OK' if not failed else str(failed) + ' FAILED'}")
		return 1 if failed else 0
	if args.check_upstream_shape:
		return check_upstream_shape(REPO)
	return check(REPO, report=args.report)


if __name__ == "__main__":
	sys.exit(main())
