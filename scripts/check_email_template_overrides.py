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

    python scripts/check_email_template_overrides.py              # fail on any hit
    python scripts/check_email_template_overrides.py --report      # list hits, exit 0
    python scripts/check_email_template_overrides.py --self-test   # prove it can fail
"""
import argparse
import ast
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
	return failed


def main(argv=None):
	parser = argparse.ArgumentParser(description=__doc__,
	                                 formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("--self-test", action="store_true")
	parser.add_argument("--report", action="store_true")
	args = parser.parse_args(argv)
	if args.self_test:
		failed = self_test()
		print(f"check_email_template_overrides self-test: {'OK' if not failed else str(failed) + ' FAILED'}")
		return 1 if failed else 0
	return check(REPO, report=args.report)


if __name__ == "__main__":
	sys.exit(main())
