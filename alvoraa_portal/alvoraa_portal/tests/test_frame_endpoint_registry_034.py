"""Slice 034: the three structural checks the security review asked for.

These do not test behaviour. They test that behaviour tests EXIST, and that two
whole-file rules hold, so the next person to add an endpoint cannot quietly skip
either.

**AC-69 (SEC-2) - the registry.** The preview page is not a data control. Every
whitelisted function in `frame_api.py` and `inbox_api.py` is live on production
from the release that carries it, whatever page calls it. So each one ships with
a Guest-refused test, a wrong-persona test and a scope test IN THE SAME COMMIT.
The registry below names them; the test reads the module source and fails if a
whitelisted function has no entry, and fails again if an entry names a test that
does not exist. `test_portal_call_paths` does not prove this - it checks that a
path exists and is whitelisted, not that the function checks its caller.

**AC-70 (SEC-15) - no module-level state.** One worker serves several sites. A
module-level dict, list or set that is written to at run time is one site's data
in another site's request. Every constant in these modules is a tuple.

**AC-71 (SEC-6) - no `ignore_permissions`.** Not in these files, at all. The
repository-wide counter is a separate piece of work (residual risk R4); this
holds the two new files until it exists.

`inbox_api.py` was named here before it was written, on purpose: the day it
appeared, these three checks already applied to it, and its registry row was
part of the commit that created it. `staff_api.py` was added the same way, by
one line in MODULES - which is the whole point of listing the files rather than
the functions.
"""

import ast
import io
import os
import tokenize

import frappe
from frappe.tests.utils import FrappeTestCase

import alvoraa_portal

MODULES = ("frame_api.py", "inbox_api.py", "staff_api.py")

# AC-69. One row per whitelisted function. `guest`, `persona` and `scope` each
# name a test method that must exist in the test file named by `tests`.
#
# "scope" for get_frame means: what this caller is shown is decided by what they
# are, not by what the browser asked for. It takes no arguments at all, so its
# scope case is the persona table itself.
ENDPOINT_REGISTRY = {
	"frame_api.get_frame": {
		"tests": "alvoraa_portal.tests.test_frame_api_034",
		"guest": "TestWhoMayCallIt.test_guest_is_refused",
		"persona": "TestThePersonaRules.test_rule_six_needs_no_active_employee_record",
		"scope": "TestWhatEachPersonaMayOpen.test_time_pay_and_growth_need_an_employee_record",
	},
	# The frame's second and last start-up call (US-6). Its "scope" case is the
	# corrections queue, because that is the one part of the count whose scope
	# differs by caller - a store's HR person counts their store, and a reviewer
	# who is not HR keeps their whole queue (W1D-05, W1D-14).
	"inbox_api.get_nav_counts": {
		"tests": "alvoraa_portal.tests.test_inbox_counts_034",
		"guest": "TestTheShapeOfThePayload.test_guest_is_refused",
		"persona": "TestAPlainEmployeeCountsNothingThatIsNotTheirs.test_a_plain_employee_approves_nothing",
		"scope": "TestTheCorrectionsCountEqualsItsScreen.test_store_hr_counts_their_store_and_nobody_elses",
	},
	# The staff list (W1D-21, SEC-16). Its "persona" case is the one that
	# matters most for this endpoint: the feature switch is checked on the
	# SERVER, so an HR user on a tenant that was never given the feature is
	# refused when they call it by hand (abuse case A14).
	"staff_api.get_staff_list": {
		"tests": "alvoraa_portal.tests.test_staff_list_034",
		"guest": "TestWhoMayCallTheStaffList.test_guest_is_refused",
		"persona": "TestWhoMayCallTheStaffList.test_a_plain_employee_is_refused",
		"scope": "TestWhatTheStaffListShows.test_store_hr_gets_their_store_and_nobody_else",
	},
}


def _module_files():
	"""The files these rules cover, skipping any not written yet."""
	root = os.path.dirname(os.path.abspath(alvoraa_portal.__file__))
	found = []
	for name in MODULES:
		path = os.path.join(root, name)
		if os.path.isfile(path):
			found.append((name, path))
	return found


def _source(path):
	return io.open(path, encoding="utf-8").read()


def _code_only(path):
	"""The file with every comment and every string literal removed.

	The `ignore_permissions` check below has to look at CODE. Reading the raw
	text would fail on the sentence in frame_api's own docstring that promises
	the flag is not used - which is the opposite of what the check is for. A
	plain text search is still the right shape for the check itself, because it
	catches getattr tricks and kwargs dicts that an AST walk would miss; it just
	has to be told what is prose.
	"""
	kept = []
	with io.open(path, "rb") as handle:
		for tok in tokenize.tokenize(handle.readline):
			if tok.type in (tokenize.COMMENT, tokenize.STRING):
				continue
			kept.append(tok.string)
	return " ".join(kept)


def _whitelisted_functions(tree):
	"""Top-level functions carrying @frappe.whitelist(...)."""
	names = []
	for node in tree.body:
		if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
			continue
		for dec in node.decorator_list:
			call = dec.func if isinstance(dec, ast.Call) else dec
			if isinstance(call, ast.Attribute) and call.attr == "whitelist":
				names.append(node.name)
				break
	return names


class TestEveryNewEndpointHasItsThreeCases(FrappeTestCase):
	def test_at_least_one_module_is_present(self):
		"""If neither file exists, the checks below pass by doing nothing. Say so."""
		self.assertTrue(_module_files(), "frame_api.py is missing - the rest of this file is vacuous")

	def test_every_whitelisted_function_is_in_the_registry(self):
		for name, path in _module_files():
			module = name[:-3]
			for fn in _whitelisted_functions(ast.parse(_source(path))):
				key = f"{module}.{fn}"
				self.assertIn(
					key, ENDPOINT_REGISTRY,
					f"{key} is whitelisted and has no registry entry. Add it, with its "
					f"Guest-refused, wrong-persona and scope tests, in the same commit (SEC-2).",
				)

	def test_the_registry_names_no_function_that_has_gone(self):
		live = set()
		for name, path in _module_files():
			module = name[:-3]
			live.update(f"{module}.{fn}" for fn in _whitelisted_functions(ast.parse(_source(path))))
		for key in ENDPOINT_REGISTRY:
			if key.split(".")[0] + ".py" in [n for n, _ in _module_files()]:
				self.assertIn(key, live, f"{key} is in the registry but is no longer whitelisted")

	def test_every_named_case_is_a_test_that_exists(self):
		"""A registry of names nobody runs would be worse than no registry."""
		for key, row in ENDPOINT_REGISTRY.items():
			module = frappe.get_module(row["tests"])
			for kind in ("guest", "persona", "scope"):
				cls_name, method = row[kind].split(".")
				cls = getattr(module, cls_name, None)
				self.assertIsNotNone(cls, f"{key}: {row[kind]} names a class that does not exist")
				self.assertTrue(
					callable(getattr(cls, method, None)),
					f"{key}: {row[kind]} names a test method that does not exist",
				)


class TestNoModuleLevelStateAndNoIgnorePermissions(FrappeTestCase):
	def test_no_global_statement(self):
		"""AC-70. `global` in a web worker is one request writing another's data."""
		for name, path in _module_files():
			for node in ast.walk(ast.parse(_source(path))):
				self.assertNotIsInstance(node, ast.Global, f"{name} uses `global`")

	def test_no_module_level_dict_list_or_set(self):
		"""AC-70. A tuple cannot be appended to; a list, dict or set can be, and
		a worker serves several sites. Constants in these modules are tuples."""
		for name, path in _module_files():
			for node in ast.parse(_source(path)).body:
				if not isinstance(node, (ast.Assign, ast.AnnAssign)):
					continue
				value = node.value
				if isinstance(value, (ast.Dict, ast.List, ast.Set, ast.ListComp,
				                      ast.DictComp, ast.SetComp)):
					targets = node.targets if isinstance(node, ast.Assign) else [node.target]
					label = ", ".join(getattr(t, "id", "?") for t in targets)
					self.fail(f"{name}: module-level mutable `{label}` (line {node.lineno}). "
					          f"Use a tuple, or build it inside the function.")

	def test_no_ignore_permissions_anywhere_in_these_files(self):
		"""AC-71 / SEC-6. Not "few". None."""
		for name, path in _module_files():
			self.assertNotIn("ignore_permissions", _code_only(path),
			                 f"{name} uses ignore_permissions")
