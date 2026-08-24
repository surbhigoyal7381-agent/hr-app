"""Wave 4 - denial, and the ability to undo it.

Three levers were built before this one, and a tenant still showed Payroll,
Recruitment and CRM. Every desk sidebar item type except `workspace` is decided
by PERMISSIONS, so hiding could never finish the job.

This is the first mechanism that actually denies. The tests are ordered
deliberately: the REVERSAL is proven before the restriction, because a change
that can stop a customer working should not ship until putting it back is
proven.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import module_access as ma
from alvoraa_portal import subscription as sub

USER = "wave4.tester@access.test"

# The doctypes these tests actually assert on. Passing them to sync_permissions
# keeps a run to six doctypes instead of 450: the same behaviour, in seconds
# rather than eight minutes. TestItScales still exercises the full set.
WATCH = ["Salary Slip", "Payroll Entry", "Sales Invoice",
         "Leave Application", "Attendance", "Expense Claim"]


class Wave4Mixin:
	"""A plain mixin, deliberately NOT a FrappeTestCase.

	When this was an intermediate FrappeTestCase base, Frappe's discovery found
	only the classes that inherited it directly and silently ran 5 of 18 tests.
	A suite that quietly skips two thirds of itself is worse than no suite.
	"""

	def setUp(self):
		frappe.set_user("Administrator")
		self._plane = frappe.conf.get("alvoraa_control_plane")
		frappe.conf.pop("alvoraa_control_plane", None)
		ma.release_permissions()          # never inherit another test's state
		if not frappe.db.exists("User", USER):
			u = frappe.get_doc({"doctype": "User", "email": USER, "first_name": "Wave4",
			                    "send_welcome_email": 0, "user_type": "System User",
			                    "roles": [{"role": "HR Manager"}, {"role": "HR User"}]})
			u.flags.ignore_permissions = True
			u.insert(ignore_permissions=True)
		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")
		ma.release_permissions()
		if frappe.db.exists("User", USER):
			frappe.delete_doc("User", USER, force=True, ignore_permissions=True)
		if self._plane is not None:
			frappe.conf["alvoraa_control_plane"] = self._plane
		frappe.db.commit()

	def _can_read(self, doctype):
		frappe.clear_cache()
		frappe.set_user(USER)
		try:
			return frappe.has_permission(doctype, "read")
		finally:
			frappe.set_user("Administrator")

	def _custom_roles(self, doctype):
		return sorted({r.role for r in frappe.get_all(
			"Custom DocPerm", filters={"parent": doctype}, fields=["role"])})


class TestTheDoctypeListIsDerived(FrappeTestCase):
	"""Nothing is hardcoded. The doctypes come from the modules the registry
	blocks, which come from the features the site bought - so a doctype added by
	a future ERPNext release is covered the day it appears."""

	FAKE = [("Salary Slip", "Payroll"), ("Leave Application", "HR"),
	        ("Sales Invoice", "Accounts"), ("Custom Thing", "Some New Module")]

	def test_it_blocks_doctypes_of_blocked_modules(self):
		got = sub.blocked_doctypes(sub.plan_features("starter"), existing=self.FAKE)
		self.assertIn("Salary Slip", got)
		self.assertIn("Sales Invoice", got)

	def test_it_never_blocks_a_sold_module(self):
		got = sub.blocked_doctypes(sub.plan_features("starter"), existing=self.FAKE)
		self.assertNotIn("Leave Application", got, "HR is on every plan")

	def test_an_unknown_module_is_DENIED_by_default(self):
		"""The allow-list is the definition; everything else is blocked.

		This used to assert the opposite, because blocked_module_defs() built an
		explicit blocked list - so a module from a future ERPNext release, or from
		a third-party app somebody installs, was visible to every tenant the day
		it appeared, on nobody's list and nobody's radar.
		"""
		got = sub.blocked_doctypes(sub.plan_features("starter"), existing=self.FAKE)
		self.assertIn("Custom Thing", got)

	def test_business_releases_payroll_doctypes(self):
		got = sub.blocked_doctypes(sub.plan_features("business"), existing=self.FAKE)
		self.assertNotIn("Salary Slip", got)

	def test_it_is_a_pure_function(self):
		"""Injectable input, so the ladder can be tested without a database."""
		a = sub.blocked_doctypes(sub.plan_features("starter"), existing=self.FAKE)
		b = sub.blocked_doctypes(sub.plan_features("starter"), existing=self.FAKE)
		self.assertEqual(a, b)


class TestReversalFirst(Wave4Mixin, FrappeTestCase):
	"""Proven before the restriction it undoes."""

	def test_a_full_round_trip_restores_access(self):
		before = self._can_read("Salary Slip")
		ma.sync_permissions(sub.plan_features("starter"), only=WATCH)
		ma.release_permissions()
		self.assertEqual(self._can_read("Salary Slip"), before)

	def test_it_restores_pre_existing_customisations_exactly(self):
		"""40 of the 450 doctypes a Starter tenant blocks already carry Custom
		DocPerm rows from hrms/setup.py. reset_perms would restore the STANDARD
		permissions for those - which is not what was there. So we snapshot."""
		before = self._custom_roles("Salary Slip")
		self.assertTrue(before, "this test needs a doctype that has custom perms")
		ma.sync_permissions(sub.plan_features("starter"), only=WATCH)
		ma.release_permissions()
		self.assertEqual(self._custom_roles("Salary Slip"), before)

	def test_releasing_twice_is_harmless(self):
		ma.sync_permissions(sub.plan_features("starter"), only=WATCH)
		first = ma.release_permissions()
		second = ma.release_permissions()
		self.assertTrue(first["released"])
		self.assertEqual(second["released"], [])

	def test_it_only_releases_what_we_recorded(self):
		"""A Custom DocPerm somebody else made is not ours to delete."""
		r = ma.release_permissions(["Some Doctype We Never Touched"])
		self.assertEqual(r["released"], [])

	def test_state_is_cleared_after_release(self):
		ma.sync_permissions(sub.plan_features("starter"), only=WATCH)
		ma.release_permissions()
		self.assertEqual(ma._recorded_restrictions(), set())
		self.assertEqual(ma._load("permission_snapshot"), {})


class TestDenialActuallyDenies(Wave4Mixin, FrappeTestCase):
	"""The point of the whole wave."""

	def test_an_unsold_doctype_becomes_unreadable(self):
		self.assertTrue(self._can_read("Salary Slip"), "should start readable")
		ma.sync_permissions(sub.plan_features("starter"), only=WATCH)
		self.assertFalse(self._can_read("Salary Slip"),
		                 "Starter does not include Payroll")

	def test_a_sold_doctype_keeps_working(self):
		"""The failure that would matter most: denying something they bought."""
		ma.sync_permissions(sub.plan_features("starter"), only=WATCH)
		for dt in ("Leave Application", "Attendance", "Expense Claim"):
			self.assertTrue(self._can_read(dt), f"{dt} is on every plan")

	def test_an_upgrade_grants_it_back(self):
		ma.sync_permissions(sub.plan_features("starter"), only=WATCH)
		self.assertFalse(self._can_read("Salary Slip"))
		ma.sync_permissions(sub.plan_features("business"), only=WATCH)
		self.assertTrue(self._can_read("Salary Slip"), "Business includes Payroll")

	def test_a_restricted_doctype_always_keeps_one_exempt_row(self):
		"""LOAD-BEARING. A doctype with ZERO custom rows falls back to its
		STANDARD permissions, which silently undoes the denial. Measured: an HR
		Manager could still read Salary Slip after it was 'restricted'."""
		ma.sync_permissions(sub.plan_features("starter"), only=WATCH)
		for dt in ("Salary Slip", "Sales Invoice"):
			self.assertTrue(self._custom_roles(dt),
			                f"{dt} has no custom rows, so standard perms apply again")

	def test_the_exempt_role_is_the_one_module_hiding_exempts(self):
		"""One definition of 'exempt' in this module, not two that can drift."""
		self.assertEqual(ma._exempt_roles(), set(ma.ADMIN_ROLES))


class TestItScales(Wave4Mixin, FrappeTestCase):
	"""The first implementation died at 450 doctypes."""

	def test_release_does_not_flood_the_background_queue(self):
		"""frappe.permissions.reset_perms deletes each row as a DOCUMENT, which
		queues a job apiece. Across 450 doctypes that hit the limit and the
		release died half-done:

		    QueueOverloaded: Too many queued background jobs (550)
		"""
		import inspect

		src = inspect.getsource(ma.release_permissions)
		self.assertIn('frappe.db.delete("Custom DocPerm"', src)

		# Comment lines mention reset_perms to explain why it is not used, so
		# check the CODE. The first version of this test read the docstring and
		# failed on its own explanation.
		code = [ln.split("#", 1)[0] for ln in src.split("\n")]
		code = [ln for ln in code if ln.strip() and not ln.strip().startswith(('"', "'"))]
		self.assertFalse([ln for ln in code if "reset_perms(" in ln],
		                 "release_permissions must not call reset_perms")

	def test_restoring_a_snapshot_bypasses_the_document_layer(self):
		import inspect

		self.assertIn("db_insert", inspect.getsource(ma._restore_snapshot))

	def test_the_whole_ladder_applies_without_error(self):
		for plan in ("starter", "business", "enterprise"):
			r = ma.sync_permissions(sub.plan_features(plan))
			self.assertEqual(r["failed"], 0, f"{plan} had failures")
