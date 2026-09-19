"""Slice 020 - a test run must leave the site's permissions as it found them.

A `Custom DocPerm` row REPLACES a doctype's shipped permissions. Frappe decides
per doctype (frappe/permissions.py, v16.33.1):

    doctypes_with_custom_perms = get_doctypes_with_custom_docperms()
    for p in perms:
        if p.parent not in doctypes_with_custom_perms:
            custom_perms.append(p)          # else the STANDARD rows are ignored

So one leftover row is enough to deny a whole doctype to everybody who is not in
it. `module_access.sync_permissions` writes hundreds of those rows on purpose -
that is how an unsold module is denied - and it COMMITS them, so a test's
rollback cannot undo them. Only `module_access.release_permissions` can.

What went wrong: `test_module_access.TestHrKeepsTheDesk` called `sync_site()` in
setUp and only rolled back in tearDown. Measured on the shared local test_site:
554 leftover rows across 338 doctypes, and unrelated suites then died in
setUpClass with permission errors on doctypes they never touched.

Two guards, and they cover different things:

  * The STATIC one is the real guard. It reads the test tree and fails if any
    class denies permissions without restoring them. It holds whatever order
    the suites run in, and it fails on the file being written rather than on a
    victim three suites later.

  * The RUNTIME one is a tripwire, not proof. Frappe runs a module's files in
    name order, so this file sits after the three suites that deny permissions
    and just before `test_portal_security_010`, the suite that was breaking. It
    cannot catch a file that sorts after it, and nothing in Frappe promises
    that order - which is why it is the second guard and not the first.
"""

import ast
import os

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import module_access as ma
from alvoraa_portal import subscription as sub

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))

# Functions that write committed Custom DocPerm rows. sync_site calls
# sync_permissions, so it counts too.
DENIERS = {"sync_site", "sync_permissions"}
RESTORER = "release_permissions"

# Six doctypes instead of 450: the same round trip, in seconds rather than
# minutes. The full set is exercised by test_access_control.
WATCH = ["Salary Slip", "Payroll Entry", "Sales Invoice",
         "Leave Application", "Attendance", "Expense Claim"]


def _called_names(node):
	"""Every function name CALLED anywhere under this node.

	ast, not a text search. `test_provision_guards` and `test_access_control`
	both mention `sync_site` and `release_permissions` inside strings they hand
	to `inspect.getsource`, and a grep-based version of this test flagged them
	as writers that never restore - a false failure on two innocent files.
	"""
	names = set()
	for child in ast.walk(node):
		if not isinstance(child, ast.Call):
			continue
		func = child.func
		if isinstance(func, ast.Attribute):
			names.add(func.attr)
		elif isinstance(func, ast.Name):
			names.add(func.id)
	return names


def _mentioned_names(node):
	"""Every name REFERENCED under this node, called or not.

	The restore is usually handed to addCleanup rather than called:

	    self.addCleanup(ma.release_permissions)

	which is a reference, not a call. Looking only at calls reported the fixed
	classes as offenders. Still ast, so a name inside a string does not count.
	"""
	names = set()
	for child in ast.walk(node):
		if isinstance(child, ast.Attribute):
			names.add(child.attr)
		elif isinstance(child, ast.Name):
			names.add(child.id)
	return names


def _class_map(path):
	"""{class name: (names it CALLS, names it MENTIONS, in-file base names)}.

	The two name sets stay apart on purpose. A denier only counts when it is
	CALLED - `test_module_access` reads `inspect.getsource(ma.sync_site)` to
	assert on its source, which mentions the name without writing a single row,
	and counting mentions reported that class as a writer. A restore counts when
	it is merely MENTIONED, because addCleanup takes it as a reference.
	"""
	with open(path, encoding="utf-8") as f:
		tree = ast.parse(f.read(), filename=path)
	out = {}
	for node in ast.walk(tree):
		if isinstance(node, ast.ClassDef):
			bases = {b.id for b in node.bases if isinstance(b, ast.Name)}
			out[node.name] = (_called_names(node), _mentioned_names(node), bases)
	return out


def _restores(name, classes, seen=None):
	"""Does this class, or anything it inherits from in the same file, restore?"""
	seen = seen or set()
	if name in seen or name not in classes:
		return False
	seen.add(name)
	_calls, mentions, bases = classes[name]
	if RESTORER in mentions:
		return True
	return any(_restores(b, classes, seen) for b in bases)


class TestNoSuiteDeniesPermissionsWithoutGivingThemBack(FrappeTestCase):
	"""The guard that has to hold. Static, so order cannot hide a leak."""

	def test_every_class_that_denies_permissions_also_restores_them(self):
		offenders = []
		for fname in sorted(os.listdir(TESTS_DIR)):
			if not (fname.startswith("test_") and fname.endswith(".py")):
				continue
			classes = _class_map(os.path.join(TESTS_DIR, fname))
			for cls, (calls, _mentions, _bases) in classes.items():
				if calls & DENIERS and not _restores(cls, classes):
					offenders.append(f"{fname}::{cls}")

		self.assertEqual(
			offenders, [],
			"These classes write committed Custom DocPerm rows and never call "
			f"module_access.{RESTORER}. A leftover row replaces a doctype's "
			"shipped permissions, so the next suite to run fails on a doctype "
			"it never touched. Register the restore with addCleanup BEFORE the "
			f"call: self.addCleanup(ma.{RESTORER}). Offenders: "
			+ ", ".join(offenders))

	def test_the_scan_actually_finds_a_writer(self):
		"""A scan that matched nothing would pass for the wrong reason."""
		writers = []
		for fname in sorted(os.listdir(TESTS_DIR)):
			if not (fname.startswith("test_") and fname.endswith(".py")):
				continue
			for cls, (calls, _m, _b) in _class_map(os.path.join(TESTS_DIR, fname)).items():
				if calls & DENIERS:
					writers.append(f"{fname}::{cls}")
		self.assertTrue(writers, "the scan found no permission writers at all, "
		                         "so it is proving nothing")

	def test_a_planted_offender_is_caught(self):
		"""The guard fails before the leak is fixed, or it is not a guard.

		Parsed from source text rather than written to disk: the scan must not
		need a throwaway file in a shared checkout to be provable.
		"""
		src = (
			"class Leaky:\n"
			"	def setUp(self):\n"
			"		ma.sync_site(feats)\n"
			"class Tidy(Leaky):\n"
			"	def setUp(self):\n"
			"		self.addCleanup(ma.release_permissions)\n"
			"class Quoting:\n"
			"	def test_it(self):\n"
			"		self.assertIn('sync_permissions', src)\n"
		)
		tree = ast.parse(src)
		classes = {n.name: (_called_names(n), _mentioned_names(n),
		                    {b.id for b in n.bases if isinstance(b, ast.Name)})
		           for n in tree.body if isinstance(n, ast.ClassDef)}

		self.assertTrue(classes["Leaky"][0] & DENIERS, "sync_site is a writer")
		self.assertFalse(_restores("Leaky", classes), "a leaky class must be caught")
		# A restore handed to addCleanup counts, and it counts on a base class.
		self.assertTrue(_restores("Tidy", classes))
		# A name that only appears inside a string is not a write.
		self.assertFalse(classes["Quoting"][0] & DENIERS,
		                 "a quoted name must never be read as a write")


class TestTheSiteIsLeftAsItWasFound(FrappeTestCase):
	"""The round trip, measured in rows rather than assumed."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# Read BEFORE any test in this class touches anything. The round-trip
		# test below releases first to get a clean baseline, which would repair
		# an earlier suite's leak and hide it from the tripwire. Capturing it
		# here makes the two tests independent of each other's order.
		cls.leaked_before_this_file = set(ma._recorded_restrictions())

	def setUp(self):
		frappe.set_user("Administrator")
		self._plane = frappe.conf.get("alvoraa_control_plane")
		frappe.conf.pop("alvoraa_control_plane", None)
		self.addCleanup(ma.release_permissions)

	def tearDown(self):
		if self._plane is not None:
			frappe.conf["alvoraa_control_plane"] = self._plane

	def _rows(self):
		total = frappe.db.count("Custom DocPerm")
		parents = len({r.parent for r in frappe.get_all(
			"Custom DocPerm", fields=["parent"], distinct=1)})
		return total, parents

	def test_a_deny_and_release_round_trip_changes_no_row_count(self):
		"""Not "zero rows afterwards" - zero would be WRONG.

		hrms/setup.py writes Custom DocPerm rows at install (add_permission and
		update_permission_property, hrms/setup.py ~line 896), so an honest site
		has a non-empty baseline. The invariant is that a run does not CHANGE
		it. A repair that deletes every row throws the tenant's real
		configuration away with the leak.
		"""
		# Start from a clean slate, so the delta measured is this test's own. If
		# an earlier suite leaked, this releases it - and the tripwire below
		# still reports it, because it reads the state captured in setUpClass.
		ma.release_permissions()
		before = self._rows()
		ma.sync_permissions(sub.plan_features("starter"), only=WATCH)
		self.assertNotEqual(self._rows(), before,
		                    "nothing was denied, so this proves nothing")
		ma.release_permissions()
		self.assertEqual(self._rows(), before,
		                 "the row count and the doctype count must both come back")

	def test_nothing_is_recorded_as_restricted_when_this_file_runs(self):
		"""The tripwire. Frappe runs a module's files in name order, so the three
		suites that deny permissions - test_access_control, test_module_access,
		test_tenant_setup... - sort around this one, and the first two sort
		BEFORE it. A leak from either shows up here rather than as a permission
		error inside test_portal_security_010's setUpClass.

		It cannot see a file that sorts after it, and file order is not a
		promise Frappe makes. The static test above is the guard; this is a
		tripwire.
		"""
		left = self.leaked_before_this_file
		self.assertEqual(
			sorted(left)[:10], [],
			f"{len(left)} doctypes were still recorded as restricted before this "
			"file ran. An earlier suite denied permissions and did not give them "
			"back. Repair: module_access.release_permissions() - NOT a blanket "
			"delete of Custom DocPerm, which would destroy a tenant's own rows.")
