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
import ast, glob, io, json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPS = {"alvoraa_goals": "alvoraa_goals", "alvoraa_portal": "alvoraa_portal"}
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


# ── Portal page templates ────────────────────────────────────────────────────
# Both checks below are regressions that already happened once and are invisible
# until someone clicks. Neither shows up in linting or in a bench migrate.
PORTAL_WWW = os.path.join(REPO, "alvoraa_portal", "alvoraa_portal", "www")

for page in sorted(glob.glob(os.path.join(PORTAL_WWW, "*.html"))):
	name = os.path.basename(page)
	html = io.open(page, encoding="utf-8-sig", errors="ignore").read()

	if "{% extends" not in html:
		continue

	# 1. Double footer. A page carrying its own <footer> must suppress Frappe's.
	if "<footer" in html:
		checks += 1
		if "{% block footer %}" not in html:
			err("%s : renders its own <footer> but does not override "
			    "`{%% block footer %%}` - Frappe's Standard Footer renders too "
			    "(two footers). context.no_footer does NOT do this." % name)

	# 2. Tab panes escaping their panel. Compare each gp-tab-* pane's ancestors.
	panes = re.findall(r'<div\b[^>]*id="(gp-tab-[^"]+)"', html)
	if panes:
		stack, outside = [], []
		for m in re.finditer(r'<div\b[^>]*>|</div>', html):
			tag = m.group(0)
			if tag == "</div>":
				if stack:
					stack.pop()
				continue
			idm = re.search(r'id="([^"]+)"', tag)
			pane = idm.group(1) if idm else None
			if pane and pane.startswith("gp-tab-") and "panel-goals" not in stack:
				outside.append(pane)
			stack.append(pane)
		checks += 1
		if outside:
			err("%s : %s outside #panel-goals - switchPanel() only hides .panel "
			    "elements, so these stay visible on every page once opened"
			    % (name, ", ".join(sorted(set(outside)))))


# 3. `context.no_footer` is a DEAD flag - it appears nowhere in Frappe v16. Code that
#    sets it reads as "this page has no footer" while Frappe renders one anyway. The
#    working mechanism is a `{% block footer %}{% endblock %}` override in the template.
for ctrl in sorted(glob.glob(os.path.join(PORTAL_WWW, "*.py"))):
	checks += 1
	if "context.no_footer" in io.open(ctrl, encoding="utf-8", errors="ignore").read():
		err("%s : sets context.no_footer, which does nothing in Frappe v16. "
		    "Override `{%% block footer %%}` in the template instead."
		    % os.path.basename(ctrl))


# 4. Inline on*= handlers resolve only against GLOBAL scope. This page wraps most of
#    its code in an IIFE, so a helper declared inside it is invisible to a button -
#    the click throws ReferenceError and NOTHING happens, silently. That is exactly
#    how Apply Leave / New Claim died. A handler must be a column-0 `function NAME(`
#    or be attached with `window.NAME =`.
EVENTS = ("onclick=", "onchange=", "oninput=", "onsubmit=",
          "onkeyup=", "onkeydown=", "onfocus=", "onblur=")
NOT_FUNCS = {"if", "for", "while", "return", "function", "typeof", "new", "var",
             "JSON", "Math", "Number", "String", "Array", "Object", "Boolean",
             "parseInt", "parseFloat", "isNaN", "encodeURIComponent",
             "decodeURIComponent", "alert", "confirm", "prompt", "setTimeout",
             "setInterval", "rgba", "rgb", "url", "translate", "rotate", "scale"}
CONCAT = re.compile(chr(39) + r"[^']*?[+][^+]*?[+][^']*?" + chr(39), re.S)
BSQ = chr(92) + chr(34)      # backslash-quote, as it appears in JS-built HTML
IDENT = re.compile(r"(?<![.\w$])([A-Za-z_$][\w$]*)\s*\(")

for page in sorted(glob.glob(os.path.join(PORTAL_WWW, "*.html"))):
	name = os.path.basename(page)
	html = io.open(page, encoding="utf-8-sig", errors="ignore").read()

	handlers = set()
	for ev in EVENTS:
		i = 0
		while True:
			i = html.find(ev, i)
			if i < 0:
				break
			# Stop at the attribute's own closing quote. Handlers also appear inside
			# JS-generated HTML, where the quotes are backslash-escaped.
			rest = html[i + len(ev):]
			if rest.startswith(BSQ):
				end = rest.find(BSQ, len(BSQ))
				seg = rest[len(BSQ):end] if end > 0 else ""
			elif rest[:1] in ('"', "'"):
				q = rest[0]
				end = rest.find(q, 1)
				seg = rest[1:end] if end > 0 else ""
			else:
				seg = ""
			# Handlers built by JS contain concatenated expressions such as
			#   onclick=\"f('  +  esc(x)  +  ')\"
			# The concatenated part runs at BUILD time in the enclosing scope, not on
			# click, so drop it before looking for handler names.
			seg = CONCAT.sub("", seg)
			handlers.update(n for n in IDENT.findall(seg) if n not in NOT_FUNCS)
			i += len(ev)
	if not handlers:
		continue

	reachable = set(re.findall(r"^function ([A-Za-z_$][\w$]*)", html, re.M))
	reachable |= set(re.findall(r"window\.([A-Za-z_$][\w$]*)\s*=", html))
	checks += 1
	dead = sorted(h for h in handlers if h not in reachable)
	if dead:
		err("%s : inline handler(s) not reachable from global scope: %s - the click "
		    "throws ReferenceError and nothing happens. Declare at top level or "
		    "attach with `window.NAME =`." % (name, ", ".join(dead)))


# 5. Cross-app imports into the vendored hrms tree. A wrong module path raises
#    ImportError only when that code path first runs - and if the caller swallows
#    the failure (a front-end error handler that just hides a panel), it is silent.
#    hrms lives in this repo, so the symbol can be resolved at build time.
HRMS_ROOT = os.path.join(REPO, "hrms")

for app_dir in APPS:
	for py in glob.glob(os.path.join(REPO, app_dir, "**", "*.py"), recursive=True):
		try:
			tree = ast.parse(io.open(py, encoding="utf-8-sig", errors="ignore").read())
		except SyntaxError:
			continue
		for node in ast.walk(tree):
			if not isinstance(node, ast.ImportFrom) or not node.module:
				continue
			if not node.module.startswith("hrms."):
				continue
			checks += 1
			rel = node.module.replace(".", os.sep)
			cand = [os.path.join(HRMS_ROOT, rel + ".py"),
			        os.path.join(HRMS_ROOT, rel, "__init__.py")]
			src = next((c for c in cand if os.path.exists(c)), None)
			where = "%s -> %s" % (os.path.relpath(py, REPO).replace(os.sep, "/"), node.module)
			if src is None:
				err("%s : module does not exist in the hrms tree" % where)
				continue
			names = defined_names(src)
			if names is None:
				continue
			missing = [a.name for a in node.names
			           if a.name != "*" and a.name not in names]
			if missing:
				err("%s : %s not defined there" % (where, ", ".join(missing)))


print("app integrity: %d checks" % checks)
if errors:
	print("FAIL - %d problem(s):" % len(errors))
	for e in errors:
		print("   " + e)
	sys.exit(1)
print("OK - all consistent")
