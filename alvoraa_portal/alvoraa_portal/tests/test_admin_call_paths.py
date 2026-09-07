"""Every method the admin console calls must exist, and be whitelisted.

The same hole the portal had, in the other console. The page builds a dotted
path as a STRING:

    api('alvoraa_portal.estimate.estimate_all?period=' + period)

Nothing checks that string. Python never imports it, the linter never sees it,
CI has nothing to compare it against. A wrong module produces a function that
exists, is spelled correctly, is whitelisted - and is still unreachable. It
fails the first time a person opens the page, and not before.

That already happened once here: `get_org_setting` was written into hr_api.py
and called through a prefix pointing at performance_api, in the same commit. The
Org Setup page did not work from the day it shipped and nobody noticed for
eleven days.

So this does the one thing nobody was doing: it reads the paths out of the page
and resolves each one against the real module.
"""

import ast
import os
import re

import frappe
from frappe.tests.utils import FrappeTestCase

# api('alvoraa_portal.x.y')  and  api("alvoraa_portal.x.y?period=" + p)
API_CALL = re.compile(r"""\bapi\(\s*['"](alvoraa_portal\.[A-Za-z0-9_.]+)""")


def _app_root():
	import alvoraa_portal

	return os.path.dirname(os.path.abspath(alvoraa_portal.__file__))


def _page():
	with open(os.path.join(_app_root(), "www", "alvoraa-admin.html"),
	          encoding="utf-8", errors="replace") as fh:
		return fh.read()


def _whitelisted(module_path):
	"""Names in `module_path` carrying @frappe.whitelist(), read from SOURCE.

	Parsed rather than imported: a module that fails to import would make every
	path in it look broken and bury the real finding in noise.
	"""
	rel = module_path.replace("alvoraa_portal.", "", 1).replace(".", os.sep) + ".py"
	path = os.path.join(_app_root(), rel)
	if not os.path.exists(path):
		return None                     # the MODULE is missing, not the function
	with open(path, encoding="utf-8-sig") as fh:
		tree = ast.parse(fh.read())
	return {node.name for node in tree.body
	        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
	        and any("whitelist" in ast.unparse(d) for d in node.decorator_list)}


def _called_paths():
	return sorted(set(API_CALL.findall(_page())))


class TestEveryAdminCallResolves(FrappeTestCase):
	def test_the_page_calls_something(self):
		"""A regex that quietly matches nothing would make the test below pass
		while checking absolutely nothing."""
		self.assertGreater(len(_called_paths()), 5)

	def test_every_called_method_exists_and_is_whitelisted(self):
		broken = []
		for path in _called_paths():
			module_path, _, fn = path.rpartition(".")
			names = _whitelisted(module_path)
			if names is None:
				broken.append(f"{path}  (no such module)")
			elif fn not in names:
				broken.append(f"{path}  (not whitelisted in {module_path})")
		self.assertEqual(broken, [],
		                 "admin console calls that cannot resolve:\n  "
		                 + "\n  ".join(broken))

	def test_the_billing_screen_is_wired_to_the_billing_code(self):
		"""Named explicitly so a regression reads as itself, not as a count."""
		called = _called_paths()
		for path in ("alvoraa_portal.estimate.estimate_all",
		             "alvoraa_portal.invoicing.invoice_run_summary",
		             "alvoraa_portal.invoicing.raise_invoices"):
			self.assertIn(path, called)
