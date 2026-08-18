"""Pre-flight checks that need no bench, no database and no site.

Catches the failure modes a rename introduces, which normal linting does not:
  - a doctype whose name, folder and filename disagree (Frappe cannot load it)
  - a doctype whose "module" is not in the app's modules.txt
  - a doctype controller class that does not match the doctype name. Frappe derives it
    as doctype.replace(" ", "").replace("-", "") and raises ImportError otherwise; on
    the next `bench migrate` that doctype is treated as ORPHANED AND DELETED
  - a hooks.py handler pointing at a function that does not exist
    (a missed permission hook fails OPEN - it silently widens visibility)
  - a patches.txt entry pointing at a module with no execute()
"""
import ast, glob, io, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPS = {"grace_goals": "grace_goals", "grace_vendor_portal": "grace_vendor_portal"}
errors, checks = [], 0


def err(msg):
	errors.append(msg)


def module_path_to_file(app_dir, app_pkg, dotted):
	parts = dotted.split(".")
	if parts[0] != app_pkg:
		return None
	stem = os.path.join(REPO, app_dir, *parts)
	for cand in (stem + ".py", os.path.join(stem, "__init__.py")):
		if os.path.isfile(cand):
			return cand
	return None


def defined_names(py_file):
	try:
		tree = ast.parse(io.open(py_file, encoding="utf-8-sig", errors="ignore").read())
	except (OSError, SyntaxError) as e:
		return None
	return {n.name for n in ast.walk(tree)
	        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}


for app_dir, app_pkg in APPS.items():
	base = os.path.join(REPO, app_dir, app_pkg)
	if not os.path.isdir(base):
		err("app package missing: %s/%s" % (app_dir, app_pkg))
		continue

	mods = [m.strip() for m in io.open(os.path.join(base, "modules.txt"),
	                                   encoding="utf-8").read().split("\n") if m.strip()]

	# 1. module name <-> directory
	for m in mods:
		checks += 1
		scrub = m.lower().replace(" ", "_").replace("-", "_")
		if not os.path.isdir(os.path.join(base, scrub)):
			err("module %r declared in modules.txt but directory %r missing" % (m, scrub))

	# 2. doctype name <-> folder <-> filename <-> module
	for p in glob.glob(os.path.join(base, "*", "doctype", "*", "*.json")):
		try:
			j = json.load(io.open(p, encoding="utf-8"))
		except Exception as e:
			err("unparseable JSON: %s (%s)" % (p, e)); continue
		if not isinstance(j, dict) or j.get("doctype") != "DocType":
			continue
		checks += 1
		name, folder = j.get("name", ""), os.path.basename(os.path.dirname(p))
		fname, scrub = os.path.basename(p)[:-5], name.lower().replace(" ", "_").replace("-", "_")
		rel = os.path.relpath(p, REPO).replace("\\", "/")
		if folder != scrub:
			err("doctype %r: folder is %r, expected %r  (%s)" % (name, folder, scrub, rel))
		if fname != scrub:
			err("doctype %r: file is %r.json, expected %r.json  (%s)" % (name, fname, scrub, rel))
		if j.get("module") not in mods:
			err("doctype %r: module %r not in modules.txt %s  (%s)" % (name, j.get("module"), mods, rel))

		# Controller class. Frappe: classname = doctype.replace(" ","").replace("-","")
		# A mismatch raises ImportError, and remove_orphan_doctypes() then DELETES the
		# doctype on the next migrate. Silent, and destructive.
		checks += 1
		ctrl = os.path.join(os.path.dirname(p), scrub + ".py")
		want = name.replace(" ", "").replace("-", "")
		if not os.path.isfile(ctrl):
			err("doctype %r: controller %s.py missing  (%s)" % (name, scrub, rel))
		else:
			names_ = defined_names(ctrl)
			if names_ is None:
				err("doctype %r: controller unparseable  (%s)" % (name, rel))
			elif want not in names_:
				err("doctype %r: controller class %r missing in %s.py (found: %s)" % (
					name, want, scrub, ", ".join(sorted(names_)) or "nothing"))

	# 3. hooks.py dotted handlers must resolve
	hooks = os.path.join(base, "hooks.py")
	if os.path.isfile(hooks):
		src = io.open(hooks, encoding="utf-8-sig").read()
		try:
			tree = ast.parse(src)
		except SyntaxError as e:
			err("hooks.py does not parse: %s" % e); tree = None
		if tree:
			for node in ast.walk(tree):
				if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
					continue
				dotted = node.value
				if not dotted.startswith(app_pkg + ".") or dotted.count(".") < 2:
					continue
				checks += 1
				mod, fn = dotted.rsplit(".", 1)
				f = module_path_to_file(app_dir, app_pkg, mod)
				if f is None:
					err("hooks.py -> %s : module not found" % dotted); continue
				names = defined_names(f)
				if names is None:
					err("hooks.py -> %s : module unparseable" % dotted)
				elif fn not in names:
					err("hooks.py -> %s : %r not defined in %s" % (
						dotted, fn, os.path.relpath(f, REPO).replace("\\", "/")))

	# 4. patches.txt entries must exist and expose execute()
	pt = os.path.join(base, "patches.txt")
	if os.path.isfile(pt):
		for line in io.open(pt, encoding="utf-8"):
			line = line.strip()
			if not line or line.startswith("#"):
				continue
			checks += 1
			f = module_path_to_file(app_dir, app_pkg, line)
			if f is None:
				err("patches.txt -> %s : module not found" % line); continue
			names = defined_names(f)
			if names is None or "execute" not in names:
				err("patches.txt -> %s : no execute()" % line)

print("app integrity: %d checks" % checks)
if errors:
	print("FAIL - %d problem(s):" % len(errors))
	for e in errors:
		print("   " + e)
	sys.exit(1)
print("OK - all consistent")
