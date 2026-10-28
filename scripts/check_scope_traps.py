"""Two ways to let a person with no companies read everybody (slice 076, AC-117).

`permitted_employee_filters()` is the scope every employee list is built on. For
a caller entitled to nobody it returns filters that match nothing, never `{}`.
Two ways of using it quietly undo that, and neither fails any test until the day
somebody with no companies opens the screen:

  dict(permitted_employee_filters(user), name=chosen_id)
      A caller-supplied id laid over the scope: the scope's own condition on
      `name` is replaced by the caller's choice, so the id goes through whether
      or not it was in the scope.

  {**permitted_employee_filters(user), ...}
      The same thing, written with an unpack.

Check an id against the scope with list conditions, as `employee_in_scope` does.

This reads Python with `ast`, so a comment or a docstring that mentions the
pattern (as access.py does, to warn about it) is not a hit. Text only: no bench,
no database.

    python scripts/check_scope_traps.py              # fail on any hit
    python scripts/check_scope_traps.py --self-test  # prove it can fail

The count of `ignore_permissions` is NOT kept here. `test_portal_security_010`
holds a ceiling per file, runs in CI, and new files start at zero; a second
counter would only disagree with it.
"""
import ast
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOTS = ("alvoraa_portal", "alvoraa_goals", "hrms")
SCOPE_FN = "permitted_employee_filters"


def _is_scope_call(node):
	if not isinstance(node, ast.Call):
		return False
	f = node.func
	return (isinstance(f, ast.Name) and f.id == SCOPE_FN) or (
		isinstance(f, ast.Attribute) and f.attr == SCOPE_FN)


def find(source):
	"""The line numbers of every unsafe use of the scope helper in this source."""
	hits = []
	for node in ast.walk(ast.parse(source)):
		# dict(permitted_employee_filters(...), name=...)
		if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
				and node.func.id == "dict"
				and any(_is_scope_call(a) for a in node.args)
				and any(k.arg == "name" for k in node.keywords)):
			hits.append((node.lineno, "dict(%s(...), name=...)" % SCOPE_FN))
		# {**permitted_employee_filters(...), ...}
		if isinstance(node, ast.Dict):
			for key, value in zip(node.keys, node.values):
				if key is None and _is_scope_call(value):
					hits.append((node.lineno, "{**%s(...)}" % SCOPE_FN))
	return hits


def files():
	for root in ROOTS:
		for base, dirs, names in os.walk(os.path.join(REPO, root)):
			dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", "tests")]
			for n in names:
				if n.endswith(".py") and not n.startswith("test_"):
					yield os.path.join(base, n)


def main():
	bad = []
	for path in files():
		try:
			src = open(path, encoding="utf-8-sig").read()
			hits = find(src)
		except (SyntaxError, UnicodeDecodeError) as exc:
			# A file the check cannot read is a file it cannot vouch for.
			bad.append("%s: cannot be parsed (%s), so it was not checked"
			           % (os.path.relpath(path, REPO).replace(os.sep, "/"), exc))
			continue
		for line, what in hits:
			bad.append("%s:%d: %s lets a caller's id replace the scope. Check the id against "
			           "the scope with a list condition instead (see access.employee_in_scope)."
			           % (os.path.relpath(path, REPO).replace(os.sep, "/"), line, what))
	if bad:
		print("\n".join(bad))
		print("\nFAIL: %d unsafe use(s) of %s" % (len(bad), SCOPE_FN))
		return 1
	print("OK: no use of %s lets a caller's id replace the scope" % SCOPE_FN)
	return 0


def self_test():
	"""The check must fail on the bad shapes and stay quiet on the good ones."""
	bad_dict = "def f(user, x):\n    return dict(permitted_employee_filters(user), name=x)\n"
	bad_attr = "def f(user, x):\n    return dict(access.permitted_employee_filters(user), name=x)\n"
	bad_unpack = "def f(user, x):\n    return {**permitted_employee_filters(user), 'name': x}\n"
	good = ("def f(user, x):\n"
	        "    '''dict(permitted_employee_filters(user), name=x) is the trap.'''\n"
	        "    # {**permitted_employee_filters(user)} is the same trap.\n"
	        "    scope = permitted_employee_filters(user)\n"
	        "    return dict(scope_for_other_thing(user), name=x), {**other(user)}\n")
	for label, src, want in (("dict()", bad_dict, 1), ("attribute call", bad_attr, 1),
	                         ("unpack", bad_unpack, 1), ("safe shapes and prose", good, 0)):
		got = len(find(src))
		if got != want:
			print("SELF-TEST FAILED: %s gave %d hit(s), wanted %d" % (label, got, want))
			return 1
	try:
		find("def f(:" + chr(10))
	except SyntaxError:
		pass
	else:
		print("SELF-TEST FAILED: a file that does not parse was not reported")
		return 1
	print("self-test OK: the check fails on the three unsafe shapes and ignores prose")
	return 0


if __name__ == "__main__":
	sys.exit(self_test() if "--self-test" in sys.argv else main())
