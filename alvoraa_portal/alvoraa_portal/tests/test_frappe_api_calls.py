"""Every `frappe.something()` we call has to exist.

This is here because of `frappe.has_role("HR Manager")`, which does not. Python
does not object to a name until the line runs, so it sat in the code from
18 August, and the five endpoints behind that guard - Company Values among them -
answered every caller with

    AttributeError: module 'frappe' has no attribute 'has_role'

Nothing caught it. Not the linter, which cannot know what a module holds at
runtime; not the tests, because no test exercised those five; and not a review,
because `frappe.has_role(...)` reads exactly like something Frappe would have.

The real answer is on the line above where it was used:
`frappe.get_roles(user)`. A near-miss on a real name is the easiest kind of
mistake to make and the hardest to see.

So: read our source, collect every attribute reached for on `frappe`, and check
each against the module actually loaded. Cheap, and it would have failed the day
the line was written.
"""

import ast
import os

import frappe
from frappe.tests.utils import FrappeTestCase

APPS = ("alvoraa_portal", "alvoraa_goals")

# Names that only exist once something has set them up - a request, a job, a
# logged-in session. They are real; they are just not attributes of the module
# at import time.
RUNTIME_ONLY = {
	"local", "session", "request", "response", "form_dict", "flags", "conf",
	"cache", "db", "qb", "lang", "user", "job_name", "site",
}


def _frappe_calls(tree):
	"""Every `frappe.<name>(...)` actually invoked in this module."""
	out = set()
	for node in ast.walk(tree):
		if not isinstance(node, ast.Call):
			continue
		fn = node.func
		if (isinstance(fn, ast.Attribute)
				and isinstance(fn.value, ast.Name) and fn.value.id == "frappe"):
			out.add(fn.attr)
	return out


def _source_files():
	for app in APPS:
		try:
			base = frappe.get_app_path(app)
		except Exception:
			continue
		for root, dirs, files in os.walk(base):
			dirs[:] = [d for d in dirs if d not in ("__pycache__", "node_modules")]
			for fn in files:
				if fn.endswith(".py"):
					yield os.path.join(root, fn)


class TestEveryFrappeCallResolves(FrappeTestCase):
	def test_no_call_to_something_frappe_does_not_have(self):
		"""A name that does not exist is a crash waiting for its first caller."""
		missing = {}
		for path in _source_files():
			try:
				src = open(path, encoding="utf-8-sig").read()
			except Exception:
				continue
			# Parsed, not pattern-matched. A comment or a docstring naming a
			# function is not a call to it - this test's own explanation of the
			# bug was the first thing the pattern version accused.
			try:
				tree = ast.parse(src)
			except SyntaxError:
				continue
			for attr in _frappe_calls(tree):
				if attr in RUNTIME_ONLY or hasattr(frappe, attr):
					continue
				missing.setdefault(attr, set()).add(os.path.basename(path))

		self.assertEqual(
			missing, {},
			"These are called on `frappe` but do not exist, so every caller gets "
			"an AttributeError:\n" + "\n".join(
				"  frappe.%s()  in %s" % (a, ", ".join(sorted(f)))
				for a, f in sorted(missing.items())))

	def test_no_call_passes_a_keyword_frappe_does_not_accept(self):
		"""The same bug one level down: a real function, a keyword it never had.

		`frappe.has_permission(..., raise_exception=False)` was written twice in
		hr_api. There is no such argument, so every call raised TypeError - and
		both were inside `try/except Exception`, which turned the crash into a
		quiet `False`. The result was that the Attendance Request and Request
		Advance items were hidden in the sidebar for every user on every tenant,
		with nothing in any log to say why.

		Checking the name exists was never going to catch that. Checking the
		signature does, and costs one `inspect` call per distinct function.
		"""
		import inspect

		wrong = {}
		for path in _source_files():
			try:
				tree = ast.parse(open(path, encoding="utf-8-sig").read())
			except Exception:
				continue
			for node in ast.walk(tree):
				if not isinstance(node, ast.Call):
					continue
				fn = node.func
				if not (isinstance(fn, ast.Attribute)
						and isinstance(fn.value, ast.Name) and fn.value.id == "frappe"):
					continue
				if fn.attr in RUNTIME_ONLY:
					continue
				target = getattr(frappe, fn.attr, None)
				if not callable(target):
					continue
				try:
					sig = inspect.signature(target)
				except (ValueError, TypeError):
					continue
				# A function taking **kwargs accepts anything, so there is
				# nothing to be wrong about.
				if any(p.kind is inspect.Parameter.VAR_KEYWORD
				       for p in sig.parameters.values()):
					continue
				for kw in node.keywords:
					if kw.arg and kw.arg not in sig.parameters:
						wrong.setdefault("frappe.%s(%s=...)" % (fn.attr, kw.arg),
						                 set()).add(os.path.basename(path))

		self.assertEqual(
			wrong, {},
			"These pass a keyword the function does not accept, so every call "
			"raises TypeError: " + "; ".join(
				"%s in %s" % (c, ", ".join(sorted(f)))
				for c, f in sorted(wrong.items())))

	def test_the_sidebar_items_that_were_always_hidden_now_appear(self):
		"""Both features were computed as False for everybody, so the screens
		behind them could not be reached from the portal at all."""
		from alvoraa_portal.hr_api import get_available_features

		frappe.set_user("Administrator")
		features = get_available_features()
		self.assertTrue(features["attendance_request"],
		                "Administrator can create these, so the item must show")
		self.assertTrue(features["advance_request"])

	def test_the_guard_that_was_broken_now_works(self):
		"""_require_hr refused everybody, including HR, by raising AttributeError
		before it could decide anything."""
		from alvoraa_portal.hr_api import _require_hr

		# Administrator holds System Manager, so this must simply return.
		frappe.set_user("Administrator")
		_require_hr()

		# And it must still refuse somebody who holds neither role, with a
		# permission error rather than a crash.
		email = "no.roles.test@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc({"doctype": "User", "email": email, "first_name": "No",
			                "send_welcome_email": 0}).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			with self.assertRaises(frappe.PermissionError):
				_require_hr()
		finally:
			frappe.set_user("Administrator")
