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

# A role that exists only for the fixture below, so the customisation it builds
# is recognisably ours and cannot collide with a role the site really uses.
FIXTURE_ROLE = "Wave4 Fixture Customisation"


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
		# Every test in this mixin restricts doctypes, and those writes are
		# committed. tearDown releases them, but unittest skips tearDown when
		# setUp raises, and the user insert below can raise - so the restore is
		# also registered as a cleanup, which always runs.
		self.addCleanup(ma.release_permissions)
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

	def _custom_perms(self, doctype):
		"""Every custom permission row on a doctype, every field, in a stable order.

		`_custom_roles` compares only the role names, which cannot see a changed
		flag - and "restores the customisation EXACTLY" is a claim about the
		flags. Comparing the whole row is what makes the word `exactly` true.
		"""
		rows = frappe.get_all("Custom DocPerm", filters={"parent": doctype},
		                      fields=list(ma._SNAPSHOT_FIELDS))
		return sorted(tuple(sorted(dict(r).items())) for r in rows)

	def _give_it_a_pre_existing_customisation(self, doctype, role=FIXTURE_ROLE):
		"""Build the precondition instead of hoping the site has it.

		This test used to read whatever `Salary Slip` happened to carry. That
		held while a bench had been through an hrms install that left rows on
		it, and stopped holding the day `test_site` was rebuilt: on a fresh
		site, NONE of the 322 doctypes a Starter tenant blocks carries a custom
		permission row - measured, not assumed. So the test could not run, and
		the snapshot-and-restore path it guards had no coverage at all.

		`add_permission` and `update_permission_property` are Frappe's own API
		and are exactly what `hrms/setup.py` calls, so what this builds is the
		real situation rather than an imitation of it. `add_permission` copies
		the doctype's standard rows into Custom DocPerm first, which is how a
		doctype comes to carry a whole set of them.
		"""
		from frappe.permissions import add_permission, update_permission_property

		self.assertIn(doctype, set(sub.blocked_doctypes(sub.plan_features("starter"))),
		              f"{doctype} must be denied on Starter or this proves nothing")

		# Put the doctype back exactly as it was found, whatever happens. The
		# release runs first inside the cleanup rather than relying on cleanup
		# ORDER: cleanups run last-registered-first, so the mixin's release
		# would otherwise run after this one and restore its snapshot on top.
		had = [dict(r) for r in frappe.get_all(
			"Custom DocPerm", filters={"parent": doctype},
			fields=list(ma._SNAPSHOT_FIELDS))]
		self.addCleanup(self._put_the_doctype_back, doctype, had, role)

		if not frappe.db.exists("Role", role):
			r = frappe.get_doc({"doctype": "Role", "role_name": role,
			                    "desk_access": 1})
			r.flags.ignore_permissions = True
			r.insert(ignore_permissions=True)

		add_permission(doctype, role)
		# A distinctive flag, so the assertion is about THIS customisation and
		# not about whatever the standard rows happen to say.
		update_permission_property(doctype, role, 0, "read", 1)
		frappe.db.commit()

	def _put_the_doctype_back(self, doctype, rows, role):
		ma.release_permissions()          # first, whatever order cleanups run in
		frappe.db.delete("Custom DocPerm", {"parent": doctype})
		# Bounded to the one doctype this test customised. Never a sweep of the
		# whole table: on a real tenant those rows are the configuration.
		for row in rows:
			doc = frappe.get_doc({"doctype": "Custom DocPerm", "parent": doctype,
			                      "parenttype": "DocType",
			                      "parentfield": "permissions", **row})
			doc.name = frappe.generate_hash(length=10)
			doc.db_insert()
		if frappe.db.exists("Role", role):
			frappe.delete_doc("Role", role, force=True, ignore_permissions=True)
		frappe.db.commit()
		frappe.clear_cache()


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
		"""A doctype that was already customised gets its OWN rows back.

		Some of the doctypes a Starter tenant blocks already carry Custom
		DocPerm rows - `hrms/setup.py` writes them at install, and a tenant's
		administrator can add more at any time. `reset_perms` would restore the
		STANDARD permissions for those, which is not what was there. So we
		snapshot the originals and put them back verbatim, and this is the test
		that says so.

		The customisation is BUILT here rather than borrowed from the site. It
		used to read whatever `Salary Slip` happened to carry, which made the
		test a hostage to the bench's history: when `test_site` was rebuilt the
		row was gone, `before` was empty and the test could not run at all.
		"""
		dt = "Salary Slip"
		self._give_it_a_pre_existing_customisation(dt)

		before = self._custom_perms(dt)
		self.assertTrue(before, "the fixture must leave custom rows behind")
		self.assertIn(FIXTURE_ROLE, self._custom_roles(dt),
		              "the fixture's own row must be among them")

		ma.sync_permissions(sub.plan_features("starter"), only=WATCH)
		# Denial really did replace them, so the restore below is undoing
		# something. Without this the test would pass even if sync_permissions
		# did nothing at all.
		self.assertNotEqual(self._custom_perms(dt), before,
		                    "the doctype was not actually denied")
		# And the snapshot branch is the one that ran. This is the whole point
		# of the test: a doctype with NO custom rows takes the other path and
		# is restored by doing nothing, which proves nothing about snapshots.
		self.assertIn(dt, ma._load("permission_snapshot"),
		              "the original rows were never snapshotted")

		ma.release_permissions()
		self.assertEqual(self._custom_perms(dt), before,
		                 "every original row must come back, flags and all")

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


class TestHrStillWorksAfterDenial(Wave4Mixin, FrappeTestCase):
	"""The failure that would matter most: denying something the tenant needs.

	Denying by module alone broke Frappe HR, and CI caught it, not a person.
	ERPNext keeps the most fundamental HR entities in its `Setup` module -
	Employee, Company, Department, Designation, Branch, Holiday List - so
	blocking Setup denied `Employee` itself and an HR Manager could not read a
	leave balance.

	The dependency list is derived from Frappe HR's own link fields, so a doctype
	a future release starts linking to is covered the day it appears.
	"""

	CORE = ["Employee", "Company", "Holiday List", "Department", "Designation"]

	def test_hr_can_still_read_what_frappe_hr_depends_on(self):
		ma.sync_permissions(sub.plan_features("starter"))
		for dt in self.CORE:
			if frappe.db.exists("DocType", dt):
				self.assertTrue(self._can_read(dt),
				                f"{dt} is an HR dependency and must stay readable")

	def test_those_doctypes_are_never_in_the_blocked_list(self):
		blocked = set(sub.blocked_doctypes(sub.plan_features("starter")))
		for dt in self.CORE:
			if frappe.db.exists("DocType", dt):
				self.assertNotIn(dt, blocked, dt)

	def test_the_exemption_does_not_swallow_an_unsold_feature(self):
		"""Something in the HR module links to Salary Slip, so a plain dependency
		rule made Payroll readable on Starter - exactly what the plan withholds.
		A module claimed by an unsold feature is never exempted."""
		blocked = set(sub.blocked_doctypes(sub.plan_features("starter")))
		self.assertIn("Salary Slip", blocked,
		              "Payroll is not on Starter, linked or not")

	def test_erpnext_plumbing_stays_reachable(self):
		"""Frappe HR posts payroll to Journal Entry and reads Bank Account. The
		strategy has always been that ERPNext keeps working underneath while
		staying out of sight."""
		needed = set(sub.linked_dependencies(sub.plan_features("enterprise")))
		self.assertTrue(needed, "the dependency scan found nothing at all")


class TestFrameworkDoctypesAreNeverDenied(Wave4Mixin, FrappeTestCase):
	"""Deny-by-default swept up 140 of Frappe's own doctypes.

	The first thing a real user saw was

	    Insufficient Permission for Notification Log

	every time the desk polled its notification bell. Frappe's doctypes are
	framework machinery, not product: withholding them sells nothing and breaks
	everything. They are still HIDDEN from the module list, which is the right
	lever for framework clutter and always was.
	"""

	# Doctypes an ordinary desk user reads constantly. `Comment` is deliberately
	# absent: Frappe restricts it to System Manager by default, so an HR Manager
	# cannot read it either way and asserting otherwise tests Frappe, not us.
	FRAMEWORK = ["Notification Log", "ToDo", "File"]

	def test_framework_doctypes_are_not_in_the_blocked_list(self):
		blocked = set(sub.blocked_doctypes(sub.plan_features("starter")))
		for dt in self.FRAMEWORK + ["Comment"]:
			if frappe.db.exists("DocType", dt):
				self.assertNotIn(dt, blocked, f"{dt} belongs to frappe, not to a plan")

	def test_the_desk_still_works_after_denial(self):
		ma.sync_permissions(sub.plan_features("starter"))
		for dt in self.FRAMEWORK:
			if frappe.db.exists("DocType", dt):
				self.assertTrue(self._can_read(dt), f"{dt} must stay readable")

	def test_frappe_modules_are_still_hidden_from_the_module_list(self):
		"""Hiding tidies the desk; denying breaks it. We keep the first."""
		blocked_modules = set(sub.blocked_module_defs(sub.plan_features("starter")))
		self.assertIn("Desk", blocked_modules)


class TestFeaturesSharingTheHrModule(Wave4Mixin, FrappeTestCase):
	"""Recruitment and Tenure live in `HR`, which every plan includes.

	Module-level denial cannot separate them, so a tenant that never bought
	Recruitment could still open Job Opening by URL, and the desk still drew a
	Recruitment sidebar - a sidebar shows when ANY of its items is readable.

	The mapping is taken from Frappe's own data: a feature names its workspace,
	the workspace names its doctypes. A doctype added to the Recruitment
	workspace by a future release is covered the day it appears.
	"""

	UNSOLD = ["Job Opening", "Job Applicant", "Interview"]
	SOLD = ["Leave Application", "Attendance", "Expense Claim"]

	def test_unsold_doctypes_in_a_shared_module_are_denied(self):
		ma.sync_permissions(sub.plan_features("starter"))
		for dt in self.UNSOLD:
			if frappe.db.exists("DocType", dt):
				self.assertFalse(self._can_read(dt),
				                 f"{dt} belongs to Recruitment, not on Starter")

	def test_sold_doctypes_in_the_same_module_still_work(self):
		"""The failure that would matter most: they share a module, so a clumsy
		rule takes both."""
		ma.sync_permissions(sub.plan_features("starter"))
		for dt in self.SOLD:
			if frappe.db.exists("DocType", dt):
				self.assertTrue(self._can_read(dt), f"{dt} is on every plan")

	def test_business_grants_recruitment_back(self):
		ma.sync_permissions(sub.plan_features("business"))
		for dt in self.UNSOLD:
			if frappe.db.exists("DocType", dt):
				self.assertTrue(self._can_read(dt), f"{dt} is included in Business")

	def test_being_linked_does_not_rescue_an_unsold_doctype(self):
		"""Job Applicant lives in HR and links to Job Opening, so the dependency
		exemption was quietly handing Recruitment back. Belonging to an unsold
		feature wins over being linked."""
		blocked = set(sub.blocked_doctypes(sub.plan_features("starter")))
		if frappe.db.exists("DocType", "Job Opening"):
			self.assertIn("Job Opening", blocked)

	def test_erpnext_plumbing_in_an_unsold_workspace_is_not_denied(self):
		"""The Payroll workspace lists Account, Currency and Journal Entry -
		things Leaves and Expenses need too. Denying those to withhold Payroll
		would break the plan the tenant did buy."""
		blocked = set(sub.blocked_doctypes(sub.plan_features("starter")))
		for dt in ("Currency", "Account", "Cost Center"):
			if frappe.db.exists("DocType", dt):
				self.assertNotIn(dt, blocked, f"{dt} is ERPNext plumbing, not Payroll")


class TestTheMappingReadsBothSources(Wave4Mixin, FrappeTestCase):
	"""A workspace names its doctypes in TWO places, and reading one is not enough.

	`Employee Separation` has no Workspace Link at all - Frappe HR references it
	only from the Tenure SIDEBAR. Reading links alone left it readable while the
	rest of Tenure was denied, and that is exactly how it was spotted: with the
	feature switched off, Employee Separation was the one thing still showing.
	"""

	TENURE = ["Employee Onboarding", "Employee Separation",
	          "Training Event", "Employee Grievance"]

	def _without_tenure(self):
		return [f for f in sub.plan_features("business") if f != "tenure"]

	def test_the_whole_feature_moves_together(self):
		"""Every Tenure doctype denied without it, every one allowed with it. A
		feature that is half-denied is worse than one that is not denied at all -
		it looks gated while a door stands open."""
		off = set(sub.blocked_doctypes(self._without_tenure()))
		on = set(sub.blocked_doctypes(sub.plan_features("business")))
		for dt in self.TENURE:
			if not frappe.db.exists("DocType", dt):
				continue
			self.assertIn(dt, off, f"{dt} should be denied without Tenure")
			self.assertNotIn(dt, on, f"{dt} should be allowed with Tenure")

	def test_a_doctype_reachable_only_from_the_sidebar_is_covered(self):
		"""The specific miss. Employee Separation has no Workspace Link."""
		if not frappe.db.exists("DocType", "Employee Separation"):
			self.skipTest("no Employee Separation on this bench")
		links = frappe.get_all("Workspace Link",
		                       filters={"link_to": "Employee Separation"}, limit=1)
		self.assertEqual(links, [], "if this gains a Workspace Link the test is moot")
		self.assertIn("Employee Separation",
		              set(sub.blocked_doctypes(self._without_tenure())))

	def test_both_sources_are_read(self):
		import inspect

		src = inspect.getsource(sub.workspace_scoped_doctypes)
		self.assertIn("Workspace Link", src)
		self.assertIn("Workspace Sidebar Item", src)

	def test_sold_features_are_untouched_by_the_wider_net(self):
		"""Reading a second source widens what gets denied, so the risk is
		catching something sold."""
		off = set(sub.blocked_doctypes(self._without_tenure()))
		for dt in ("Leave Application", "Attendance", "Expense Claim",
		           "Employee", "Holiday List"):
			if frappe.db.exists("DocType", dt):
				self.assertNotIn(dt, off, dt)
