"""The product is spelled "Alvora" wherever a person can read it (ALV-149).

Surbhi's rule of 27 Sep 2026: every screen, email, message and phone string says
"Alvora". Code, identifiers, domains (alvoraa.co), the app id co.alvoraa.app,
email addresses, URL paths and doctype names keep "alvoraa".

This check fails when "Alvoraa" or "ALVORAA" appears in text a user can read. It
is a repository check: no bench, no database, no site.

WHAT IT READS
  * portal and web pages, templates and browser JavaScript of our three apps;
  * the phone app's bundled page (mobile/field-app/web), its Android strings.xml
    and capacitor.config.json;
  * Python in our three apps, PARSED rather than searched: every string literal
    counts except docstrings and the arguments of a log call or print(). So a
    frappe.throw, an email subject or a page title is checked, and a comment,
    docstring or Error Log title is not;
  * `app_title` in each hooks.py;
  * the translation files: translations/*.csv and locale/*.po must not put the
    old spelling back on screen.

WHAT IS ALLOWED, AND WHY IT IS COMPUTED RATHER THAN LISTED
  * lowercase "alvoraa" - domains, paths, ids. The match is case-sensitive;
  * an identifier: the brand joined to more letters, digits or "_"
    (AlvoraaJoinScreens, ALVORAA_KEY), or a header name like X-Alvoraa-App-Version;
  * a quoted string that is EXACTLY a doctype, module or workspace name, read at
    run time from the doctype JSON and modules.txt files. Exactly, not
    "contains": "Alvoraa Pricing Settings" as a code argument passes, but a
    message that SAYS "…in Alvoraa Pricing Settings" fails, because the desk
    now shows that doctype as "Alvora Pricing Settings";
  * NAMED below: a few record names we keep on purpose, each with its reason.

THE COMPLETENESS RULE
  Every doctype, module and workspace name that contains "Alvoraa" must have a
  row in alvoraa_portal/translations/en.csv that turns it into "Alvora …". A new
  "Alvoraa Something" doctype therefore cannot reach the desk under the old
  spelling without CI saying so.

    python scripts/check_brand_spelling.py              # fail on any hit
    python scripts/check_brand_spelling.py --report     # list hits, exit 0
    python scripts/check_brand_spelling.py --self-test  # prove it can fail
"""
import argparse
import ast
import csv
import io
import json
import os
import re
import shutil
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BRAND = re.compile(r"Alvoraa|ALVORAA")
APPS = ("alvoraa_portal/alvoraa_portal", "alvoraa_goals/alvoraa_goals", "hrms/hrms")
EN_CSV = "alvoraa_portal/alvoraa_portal/translations/en.csv"

# Folders never scanned: tests assert on data, patches record history, vendor
# code is not ours, and the Frappe HR front ends are Frappe's own product.
SKIP_DIRS = {
	"tests", "test", "patches", "node_modules", "vendor", "__pycache__",
	"frontend", "roster", "dist", ".git",
}

# Files that hold the OLD spelling on purpose, because finding it is their job.
SKIP_FILES = {
	"alvoraa_portal/alvoraa_portal/brand_text.py",   # the tenant patch's list of old defaults
}

# Record names we keep on purpose. (path suffix, exact string, reason)
NAMED = (
	("alvoraa_portal/invoicing.py", "Alvoraa Platform Fee",
	 "Item record name on the control plane; issued invoices name it (Surbhi, 27 Sep)"),
	("alvoraa_portal/invoicing.py", "Alvoraa Additional Employees", "Item record name, as above"),
	("alvoraa_portal/invoicing.py", "Alvoraa Module", "Item record name, as above"),
	("alvoraa_portal/invoicing.py", "Alvoraa Operations Packs", "Item record name, as above"),
	("alvoraa_portal/invoicing.py", "Alvoraa Implementation", "Item record name, as above"),
	("alvoraa_portal/module_access.py", "Alvoraa Plan (HR)",
	 "Module Profile record name that the code looks up (Surbhi, 27 Sep)"),
	("alvoraa_portal/tenant_api.py", "Alvoraa Provision Job",
	 "doctype name used as a code constant"),
	("hrms/alvoraa_policy_library/access.py", "Alvoraa CXO",
	 "role name compared in code, never displayed by this line"),
)


def rel(path, root):
	return os.path.relpath(path, root).replace("\\", "/")


def walk(root, top, exts):
	base = os.path.join(root, top)
	if os.path.isfile(base):
		yield base
		return
	for folder, dirs, files in os.walk(base):
		dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
		for name in sorted(files):
			if name.startswith("test_") or name.endswith(".min.js"):
				continue
			if os.path.splitext(name)[1] in exts:
				yield os.path.join(folder, name)


def read(path):
	return open(path, encoding="utf-8-sig", errors="ignore").read()


# ── The names code is allowed to use ─────────────────────────────────────────
def brand_names(root):
	"""Every doctype, module and workspace name that carries the brand."""
	names = set()
	for top in APPS:
		base = os.path.join(root, top)
		for folder, dirs, files in os.walk(base):
			dirs[:] = [d for d in dirs if d not in {"node_modules", "__pycache__", "frontend"}]
			for name in files:
				path = os.path.join(folder, name)
				if name == "modules.txt":
					names.update(l.strip() for l in read(path).splitlines() if l.strip())
				elif name.endswith(".json") and (os.sep + "doctype" + os.sep in path
				                                 or os.sep + "workspace" + os.sep in path):
					try:
						doc = json.loads(read(path))
					except ValueError:
						continue
					if isinstance(doc, dict) and doc.get("doctype") in ("DocType", "Workspace"):
						names.add(doc.get("name") or "")
						if doc.get("doctype") == "Workspace":
							names.update(filter(None, (doc.get("label"), doc.get("title"))))
	return {n for n in names if BRAND.search(n)}


def named_allowed(path_rel, text):
	return any(path_rel.endswith(p) and text == s for p, s, _why in NAMED)


# ── Whether one piece of text shows the brand to a reader ────────────────────
IDENT_AROUND = re.compile(r"[A-Za-z0-9_]")


def visible_hits(text, names):
	"""Positions of brand matches that are not an identifier and not a quoted name."""
	masked = text
	if names:
		alternatives = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
		pattern = re.compile(r"""(['"`])(""" + alternatives + r""")\1""")
		masked = pattern.sub(lambda m: " " * len(m.group(0)), masked)
	hits = []
	for m in BRAND.finditer(masked):
		before = masked[m.start() - 1] if m.start() else ""
		after = masked[m.end()] if m.end() < len(masked) else ""
		if IDENT_AROUND.match(before or " ") or IDENT_AROUND.match(after or " "):
			continue
		if before == "-" and after == "-":      # X-Alvoraa-App-Version
			continue
		hits.append(m.start())
	return hits


def line_of(text, pos):
	return text.count("\n", 0, pos) + 1


# ── Markup and script files ──────────────────────────────────────────────────
COMMENTS = (
	re.compile(r"<!--.*?-->", re.S),
	re.compile(r"\{#.*?#\}", re.S),
	re.compile(r"/\*.*?\*/", re.S),
	re.compile(r"(^|[\s;{}(),>])//[^\n]*"),
)


def blank(m):
	return re.sub(r"[^\n]", " ", m.group(0))


def scan_markup(path, root, names):
	text = read(path)
	if not BRAND.search(text):
		return []
	stripped = text
	for rx in COMMENTS:
		stripped = rx.sub(blank, stripped)
	lines = text.splitlines()
	out = []
	for pos in visible_hits(stripped, names):
		n = line_of(stripped, pos)
		out.append((rel(path, root), n, lines[n - 1].strip()[:140]))
	return out


# ── Python, parsed ───────────────────────────────────────────────────────────
LOG_CALLS = {"log_error", "error", "warning", "warn", "info", "debug", "exception", "print"}


def scan_python(path, root, names):
	text = read(path)
	if not BRAND.search(text):
		return []
	try:
		tree = ast.parse(text)
	except SyntaxError:
		return [(rel(path, root), 1, "could not parse this file")]

	skip = set()
	for node in ast.walk(tree):
		# docstrings, and any other bare string statement
		if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
				and isinstance(node.value.value, str):
			skip.add(id(node.value))
		# log titles and print() output are read by our staff, not users
		if isinstance(node, ast.Call):
			fn = node.func
			name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
			if name in LOG_CALLS:
				for sub in ast.walk(node):
					skip.add(id(sub))
			# refuse(...) helpers: the message a user sees is always wrapped in
			# _(); the bare strings beside it (rule, endpoint, code) go to the
			# refusal log, which only our staff read.
			if name == "refuse":
				for arg in node.args:
					if isinstance(arg, ast.Constant):
						skip.add(id(arg))

	path_rel = rel(path, root)
	is_hooks = path_rel.endswith("/hooks.py")
	out = []
	for node in ast.walk(tree):
		# hooks.py app_title is the app's display name - an exact module name
		# there is still a name a person reads (Help -> About).
		if is_hooks and isinstance(node, ast.Assign) and any(
				getattr(t, "id", "") == "app_title" for t in node.targets):
			value = getattr(node.value, "value", "")
			if isinstance(value, str) and BRAND.search(value):
				out.append((path_rel, node.lineno, "app_title = " + value))
				skip.add(id(node.value))
			continue
		if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
			continue
		if id(node) in skip or not BRAND.search(node.value):
			continue
		value = node.value
		if value in names or named_allowed(path_rel, value):
			continue
		if visible_hits(value, names):
			out.append((path_rel, node.lineno, value.strip().replace("\n", " ")[:140]))
	return out


# ── Translation files ────────────────────────────────────────────────────────
def scan_translations(root):
	out = []
	for top in APPS:
		base = os.path.join(root, top)
		for sub, ext in (("translations", ".csv"), ("locale", ".po")):
			folder = os.path.join(base, sub)
			if not os.path.isdir(folder):
				continue
			for name in sorted(os.listdir(folder)):
				if not name.endswith(ext):
					continue
				path = os.path.join(folder, name)
				text = read(path)
				if ext == ".csv":
					for n, row in enumerate(csv.reader(io.StringIO(text)), 1):
						if len(row) >= 2 and BRAND.search(row[1]):
							out.append((rel(path, root), n, "translates to: " + row[1]))
				else:
					for n, line in enumerate(text.splitlines(), 1):
						if line.startswith("msgstr") and BRAND.search(line):
							out.append((rel(path, root), n, line.strip()[:140]))
	return out


def missing_translations(root, names):
	"""Brand names with no en.csv row that removes the old spelling."""
	path = os.path.join(root, EN_CSV)
	have = {}
	if os.path.exists(path):
		for row in csv.reader(io.StringIO(read(path))):
			if len(row) >= 2:
				have[row[0]] = row[1]
	return sorted(n for n in names if n not in have or BRAND.search(have[n]))


# ── The whole check ──────────────────────────────────────────────────────────
MARKUP_TARGETS = []
for _app in APPS:
	MARKUP_TARGETS += [(_app + "/www", {".html", ".js"}),
	                   (_app + "/templates", {".html", ".js"}),
	                   (_app + "/public/js", {".js", ".html"})]
MARKUP_TARGETS += [
	("mobile/field-app/web", {".html", ".js"}),
	("mobile/field-app/android/app/src/main/res", {".xml"}),
	("mobile/field-app/capacitor.config.json", {".json"}),
]


def scan(root):
	names = brand_names(root)
	hits = []
	for top, exts in MARKUP_TARGETS:
		for path in walk(root, top, exts):
			hits += scan_markup(path, root, names)
	for top in APPS:
		for path in walk(root, top, {".py"}):
			if rel(path, root) not in SKIP_FILES:
				hits += scan_python(path, root, names)
	hits += scan_translations(root)
	return names, hits, missing_translations(root, names)


def check(root, report=False):
	names, hits, missing = scan(root)
	for path, n, what in hits:
		print(f"{path}:{n}: {what}")
	for name in missing:
		print(f"{EN_CSV}: no row turns '{name}' into 'Alvora …'")
	bad = len(hits) + len(missing)
	print(f"brand spelling: {len(names)} brand names known, "
	      f"{len(hits)} visible 'Alvoraa', {len(missing)} missing translations")
	if not bad:
		print("OK - every screen says Alvora")
		return 0
	if report:
		print("REPORT ONLY - not failing")
		return 0
	print("FAIL - a person would read 'Alvoraa'. Write 'Alvora' there. Keep "
	      "'alvoraa' only in addresses, ids and code (ALV-149).")
	return 1


# ── The positive control ─────────────────────────────────────────────────────
def self_test():
	"""Prove the check fails on each shape of mistake, and stays quiet on code."""
	portal = "alvoraa_portal/alvoraa_portal"
	files = {
		portal + "/modules.txt": "Alvoraa Portal\n",
		portal + "/alvoraa_portal/doctype/alvoraa_thing/alvoraa_thing.json":
			json.dumps({"doctype": "DocType", "name": "Alvoraa Thing"}),
		portal + "/hooks.py": 'app_name = "alvoraa_portal"\napp_title = "Alvora HRMS"\n',
		portal + "/good.py": (
			'"""Docstrings may say Alvoraa."""\n'
			'import frappe\n'
			'DT = "Alvoraa Thing"\n'
			'def f():\n'
			'    frappe.get_all("Alvoraa Thing")\n'
			'    frappe.log_error(title="Alvoraa: job failed")\n'
			'    print("Alvoraa operator note")\n'
			'    return "https://x.alvoraa.co", "AlvoraaJoin", "X-Alvoraa-App-Version"\n'),
		portal + "/www/good.html": (
			'<!-- Alvoraa comment -->\n{# Alvoraa too #}\n'
			'<a href="https://dtc.alvoraa.co">Alvora</a>\n'
			'<script>// Alvoraa note\nwindow.AlvoraaThing = 1;</script>\n'),
		"mobile/field-app/web/js/good.js": 'var s = "Powered by Alvora"; /* Alvoraa */\n',
		"mobile/field-app/android/app/src/main/res/values/strings.xml":
			'<resources><string name="app_name">Alvora Attendance</string>'
			'<string name="package_name">co.alvoraa.app</string></resources>\n',
		"mobile/field-app/capacitor.config.json": '{"appId": "co.alvoraa.app", "appName": "Alvora Attendance"}\n',
		EN_CSV: "Alvoraa Portal,Alvora Portal\nAlvoraa Thing,Alvora Thing\n",
	}
	bad = {
		"template": (portal + "/www/bad.html", "<p>Welcome to Alvoraa</p>\n"),
		"throw": (portal + "/bad.py",
		          'import frappe\nfrappe.throw(frappe._("Set it in Alvoraa Thing first."))\n'),
		"page title": (portal + "/bad2.py", 'def ctx(context):\n    context.title = "Admin - Alvoraa"\n'),
		"app_title": (portal + "/hooks.py", 'app_title = "Alvoraa Portal"\n'),
		"strings.xml": ("mobile/field-app/android/app/src/main/res/values/strings.xml",
		                '<resources><string name="app_name">Alvoraa Attendance</string></resources>\n'),
		"capacitor": ("mobile/field-app/capacitor.config.json", '{"appName": "Alvoraa Attendance"}\n'),
		"phone js": ("mobile/field-app/web/js/bad.js", 'el.textContent = "Alvoraa Attendance";\n'),
		"translation": (EN_CSV, "Alvoraa Portal,Alvora Portal\nAlvoraa Thing,Alvoraa Thing\n"),
		"missing row": (EN_CSV, "Alvoraa Portal,Alvora Portal\n"),
	}

	def build(extra=None):
		root = tempfile.mkdtemp(prefix="brand-self-test-")
		content = dict(files)
		if extra:
			content[extra[0]] = extra[1]
		for path, body in content.items():
			full = os.path.join(root, path)
			os.makedirs(os.path.dirname(full), exist_ok=True)
			open(full, "w", encoding="utf-8").write(body)
		return root

	failed = 0
	root = build()
	try:
		_n, hits, missing = scan(root)
		ok = not hits and not missing
		print(("ok   " if ok else "FAIL ") + "clean code, domains, ids, names and comments pass")
		for h in hits:
			print("       unexpected:", h)
		failed += 0 if ok else 1
	finally:
		shutil.rmtree(root, ignore_errors=True)

	for label, extra in bad.items():
		root = build(extra)
		try:
			_n, hits, missing = scan(root)
			ok = bool(hits or missing)
			print(("ok   " if ok else "FAIL ") + f"'Alvoraa' in {label} is caught")
			failed += 0 if ok else 1
		finally:
			shutil.rmtree(root, ignore_errors=True)

	root = build(bad["template"])
	try:
		print("--- what the check prints when it catches one, on purpose: ---")
		code = check(root)
		print("--- end of the deliberate failure; the build is not failing here ---")
		print(("ok   " if code == 1 else "FAIL ") + "a bad file makes the check exit 1")
		failed += 0 if code == 1 else 1
	finally:
		shutil.rmtree(root, ignore_errors=True)
	return failed


def main(argv=None):
	parser = argparse.ArgumentParser(description=__doc__,
	                                 formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("--self-test", action="store_true", help="prove the check can fail")
	parser.add_argument("--report", action="store_true", help="list the hits, exit 0")
	args = parser.parse_args(argv)
	if args.self_test:
		failed = self_test()
		print(f"check_brand_spelling self-test: {'OK' if not failed else str(failed) + ' FAILED'}")
		return 1 if failed else 0
	return check(REPO, report=args.report)


if __name__ == "__main__":
	sys.exit(main())
