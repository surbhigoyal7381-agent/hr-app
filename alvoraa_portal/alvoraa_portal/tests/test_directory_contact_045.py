"""045 - the staff directory carries work contact, and only work contact.

Surbhi's decision of 24 September 2026: the directory is for employees too,
and contact details are IN. Her reason: *"the companies have NDAs"*.

**What shipped: work email, and no phone number at all.**

`Employee.company_email` exists and is genuinely a work field, so it is in.
**There is no work phone or extension field in the data model.** `cell_number`
is labelled "Mobile", `personal_email` says what it is, and
`emergency_phone_number` is somebody else's number entirely. Her instruction
had a stop condition for exactly this - *"If the data model has only a
personal mobile field, say so and stop rather than shipping a personal
number"* - so no phone number ships, and adding a work-phone field needs her
word.

**The NDA point, because it is the half that is easy to get backwards:** an
NDA binds the employee who LOOKS. It is not the same as the employer's own
duty to the person whose data it is. Keeping the directory to work contact is
what makes the wider audience safe.
"""

import frappe

from alvoraa_portal import staff_api
from alvoraa_portal.tests.fixtures_045 import (
	FORBIDDEN_VALUES,
	STORE_B,
	Wave4Base,
	own_company,
	own_employee,
	own_user,
	second_company,
)
from alvoraa_portal.tests.test_team_payload_045 import find_key, find_value

WORK_EMAIL = "s045.work.contact@example.com"
PERSONAL_EMAIL = "S045-PERSONAL-do-not-show@example.com"


class TestTheDirectoryCarriesWorkContactOnly(Wave4Base):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# Populated on purpose. An empty fixture would let every "must not
		# contain" assertion below pass while the field was still going out.
		frappe.db.set_value("Employee", cls.rahul, "company_email", WORK_EMAIL,
		                    update_modified=False)
		frappe.db.set_value("Employee", cls.rahul, "personal_email", PERSONAL_EMAIL,
		                    update_modified=False)

		# **This module's own people, in this module's own companies.**
		#
		# The lesson this slice paid for: a fixture that hires into a shared
		# company changes every other test's data. So the outsider lives in a
		# SECOND company that belongs to Wave 4's fixture, and the two people
		# added to Wave 4's own company are the smallest number that can prove
		# a scope moved: one in the other store, one who has left.
		cls.outsider = own_employee("S045Outsider", branch=None,
		                            company=second_company())
		cls.other_branch = own_employee("S045OtherStore", branch=STORE_B)
		cls.leaver = own_employee("S045Leaver")
		frappe.db.set_value("Employee", cls.leaver, "status", "Left",
		                    update_modified=False)

		# A login with no Employee record at all: a platform operator, a vendor
		# login, anybody the product cannot place in a scope.
		cls.no_employee_user = own_user("directory.nobody", ("Employee",))
		frappe.db.commit()

	def test_the_fixture_really_carries_both_emails(self):
		"""The check on the check."""
		row = frappe.db.get_value("Employee", self.rahul,
		                          ["company_email", "personal_email", "cell_number"],
		                          as_dict=True)
		self.assertEqual(WORK_EMAIL, row.company_email)
		self.assertEqual(PERSONAL_EMAIL, row.personal_email)
		self.assertTrue(row.cell_number, "the fixture has no mobile number, so "
		                                 "the assertion about it proves nothing")

	def test_work_email_is_in_the_row_keys(self):
		self.assertIn("work_email", staff_api.ROW_KEYS)

	def test_no_personal_contact_field_is_anywhere_in_the_key_list(self):
		for field in ("cell_number", "personal_email", "emergency_phone_number",
		              "date_of_birth", "current_address", "permanent_address",
		              "passport_number"):
			with self.subTest(field=field):
				self.assertNotIn(field, staff_api.ROW_KEYS)
				self.assertNotIn(field, " ".join(staff_api.ROW_FIELDS))

	def setUp(self):
		super().setUp()
		# **Turn the feature ON rather than skipping when it is off.**
		#
		# The first version of this test skipped itself with
		# "the staff_list feature is not on for this tenant" - and reported
		# "OK (skipped=1)", which reads as a pass and proves nothing at all.
		# A test that skips the only assertion it exists for is worse than no
		# test, because it appears in the count.
		import alvoraa_portal.subscription as sub

		self._saved_features = frappe.conf.get("features")
		frappe.conf["features"] = list(sub.DEFAULT_ON) + [staff_api.FEATURE]

	def tearDown(self):
		if self._saved_features is None:
			frappe.conf.pop("features", None)
		else:
			frappe.conf["features"] = self._saved_features
		super().tearDown()

	def test_a_plain_employee_can_now_open_the_directory(self):
		"""**This test REPLACES the one that pinned the old refusal.**

		The commit before this one asserted
		`test_a_plain_employee_still_cannot_open_the_directory_at_all`, and its
		docstring said it was expected to be replaced once the scope was decided -
		not deleted. This is that replacement, and the name changes on purpose so
		a reader of the history sees the behaviour turn over rather than a test
		quietly disappear.

		Surbhi's decision 4 had two halves. The field half shipped in `59d0c0d`;
		this is the audience half.
		"""
		self.as_user(self.rahul_user)
		out = staff_api.get_staff_list()
		self.assertTrue(out.get("rows"),
		                "a plain employee opened the directory and got nothing")
		self.assertIn(self.rahul, [r["employee"] for r in out["rows"]],
		              "a directory that does not contain the person reading it "
		              "is a bug people report")

	def test_a_plain_employee_sees_their_own_company_and_no_other(self):
		"""The scope, asserted against somebody who really is in another company.

		The other company and the person in it belong to THIS test module. Nobody
		new is hired into a shared company: that is the trap this slice walked
		into once already, when five extra names pushed another test's person on
		to page two.
		"""
		self.as_user(self.rahul_user)
		out = staff_api.get_staff_list(limit=50)
		drawn = [r["employee"] for r in out["rows"]]
		self.assertNotIn(self.outsider, drawn,
		                 "somebody from another company reached the directory")
		companies = set(frappe.get_all(
			"Employee", filters={"name": ["in", drawn]}, pluck="company"))
		self.assertEqual({frappe.db.get_value("Employee", self.rahul, "company")},
		                 companies)

	def test_the_count_equals_the_list_it_is_the_total_of(self):
		"""Surbhi's standing rule, on the new scope."""
		self.as_user(self.rahul_user)
		out = staff_api.get_staff_list(limit=50)
		company = frappe.db.get_value("Employee", self.rahul, "company")
		self.assertEqual(
			frappe.db.count("Employee", {"company": company, "status": "Active"}),
			out["total"])

	def test_one_constant_reverses_the_decision_to_store_only(self):
		"""**The line that reverses it, exercised rather than described.**

		`DIRECTORY_SCOPE_FOR_EMPLOYEES = "own_branch"` narrows a plain employee's
		directory to their own store. This test sets that one constant and
		asserts the scope really moves, so the sentence in the notes is a fact
		about the code and not a promise.

		This is NOT patching a gate. The feature switch, the refusal and the
		permission path are untouched; what moves is the one documented
		configuration constant, which is the thing under test.
		"""
		branch = frappe.db.get_value("Employee", self.rahul, "branch")
		self.as_user(self.rahul_user)
		wide = [r["employee"] for r in staff_api.get_staff_list(limit=50)["rows"]]
		self.assertIn(self.other_branch, wide,
		              "the wide scope does not contain the other store, so "
		              "narrowing it would prove nothing")

		saved = staff_api.DIRECTORY_SCOPE_FOR_EMPLOYEES
		try:
			staff_api.DIRECTORY_SCOPE_FOR_EMPLOYEES = "own_branch"
			narrow = [r["employee"]
			          for r in staff_api.get_staff_list(limit=50)["rows"]]
		finally:
			staff_api.DIRECTORY_SCOPE_FOR_EMPLOYEES = saved
		self.assertNotIn(self.other_branch, narrow)
		self.assertIn(self.rahul, narrow)
		self.assertTrue(all(
			frappe.db.get_value("Employee", e, "branch") == branch for e in narrow))

	def test_an_unknown_value_in_the_constant_fails_closed(self):
		"""A typo in the constant refuses; it does not fall back to the wider one.

		Falling back to `own_company` would hide the typo AND ship the wider
		scope, which is the worse of the two failures.
		"""
		saved = staff_api.DIRECTORY_SCOPE_FOR_EMPLOYEES
		try:
			staff_api.DIRECTORY_SCOPE_FOR_EMPLOYEES = "own_planet"
			self.as_user(self.rahul_user)
			with self.assertRaises(frappe.PermissionError):
				staff_api.get_staff_list()
		finally:
			staff_api.DIRECTORY_SCOPE_FOR_EMPLOYEES = saved

	def test_the_scope_helper_never_returns_an_empty_filter_dict(self):
		"""SEC-4 / AC-84. `{}` in Frappe means everybody."""
		import hrms.alvoraa_hr_core.access as access

		for user in ("Guest", self.rahul_user, "s045.no.such.login@example.com"):
			with self.subTest(user=user):
				got = staff_api._own_scope_filters(user)
				self.assertNotEqual({}, got)
				self.assertTrue(got)
		self.assertEqual(
			access.NO_EMPLOYEES,
			staff_api._own_scope_filters("s045.no.such.login@example.com"))

	def test_guest_is_still_refused(self):
		self.as_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			staff_api.get_staff_list()

	def test_a_login_with_no_employee_record_is_still_refused(self):
		"""A platform operator, a vendor login, anybody the product cannot place."""
		self.as_user(self.no_employee_user)
		with self.assertRaises(frappe.PermissionError):
			staff_api.get_staff_list()

	def test_the_refusal_reads_the_same_whichever_the_cause(self):
		"""045's standing rule: "not bought" and "not allowed" say the same thing.

		Two causes, one sentence. A refusal that varies is a map of what to go
		after next.
		"""
		import alvoraa_portal.subscription as sub

		said = []
		self.as_user(self.rahul_user)
		frappe.conf["features"] = list(sub.DEFAULT_ON)
		try:
			staff_api.get_staff_list()
		except frappe.PermissionError as exc:
			said.append(str(exc))
		finally:
			frappe.conf["features"] = list(sub.DEFAULT_ON) + [staff_api.FEATURE]

		self.as_user(self.no_employee_user)
		try:
			staff_api.get_staff_list()
		except frappe.PermissionError as exc:
			said.append(str(exc))

		self.assertEqual(2, len(said), "one of the two causes did not refuse")
		self.assertEqual(said[0], said[1])

	def test_the_feature_switch_still_gates_an_employee(self):
		"""Opening the audience did not open the tenant switch (SEC-16, A14)."""
		import alvoraa_portal.subscription as sub

		frappe.conf["features"] = list(sub.DEFAULT_ON)
		self.as_user(self.rahul_user)
		with self.assertRaises(frappe.PermissionError):
			staff_api.get_staff_list()

	def test_an_hr_caller_still_gets_the_hr_scope_and_not_the_employee_one(self):
		"""The new floor must not take over from a scope somebody already had.

		Kamal is given a Company permission for the OTHER company - the shape a
		real multi-company HR person has. His directory must then be that
		company, decided by `permitted_employee_filters`. If the new employee
		scope had been applied to him instead, he would see his own company,
		which is the opposite answer - so this distinguishes the two paths
		rather than merely finding rows.
		"""
		from alvoraa_portal.tests.fixtures_045 import OTHER_COMPANY

		frappe.get_doc({
			"doctype": "User Permission", "user": self.kamal_user,
			"allow": "Company", "for_value": OTHER_COMPANY,
		}).insert(ignore_permissions=True)
		frappe.clear_cache(user=self.kamal_user)
		try:
			self.as_user(self.kamal_user)
			drawn = [r["employee"]
			         for r in staff_api.get_staff_list(limit=50)["rows"]]
		finally:
			frappe.set_user("Administrator")
			frappe.db.delete("User Permission", {"user": self.kamal_user})
			frappe.clear_cache(user=self.kamal_user)
		self.assertIn(self.outsider, drawn,
		              "the HR scope did not decide an HR caller's directory")
		self.assertNotIn(self.rahul, drawn,
		                 "the employee scope leaked into an HR caller's "
		                 "directory - he is seeing his own company as well")

	def test_a_leaver_is_absent_for_an_employee_caller_too(self):
		"""Active only, on the query - PRIV-2, and easy to lose on a new path."""
		self.as_user(self.rahul_user)
		drawn = [r["employee"]
		         for r in staff_api.get_staff_list(limit=50)["rows"]]
		self.assertNotIn(self.leaver, drawn)

	def test_the_payload_carries_the_work_email_and_not_the_personal_one(self):
		"""Searched recursively over the real payload, for values that are
		really in the database.

		Driven as **Priya**, who is HR, because a plain employee cannot open
		this endpoint at all yet (see the test above). What is under test here
		is which FIELDS the rows carry, and that is the same for every caller.
		"""
		self.as_user(self.priya_user)
		out = staff_api.get_staff_list()
		self.assertTrue(out.get("rows"),
		                "the staff list came back empty, so this proves nothing")
		self.assertTrue(find_value(out, WORK_EMAIL),
		                "the work email did not reach the directory at all")
		self.assertEqual([], find_value(out, PERSONAL_EMAIL),
		                 "a personal email reached the staff directory")
		self.assertEqual([], find_value(out, FORBIDDEN_VALUES["cell_number"]),
		                 "a personal mobile number reached the staff directory")
		self.assertEqual([], find_key(out, "cell_number"))
		self.assertEqual([], find_key(out, "personal_email"))

	def test_no_phone_number_ships_because_the_field_does_not_exist(self):
		"""The stop condition, asserted rather than described.

		If somebody later adds a work-phone custom field, this test does not
		fail - it is not a ban on work phones. What it bans is the PERSONAL
		one being used as a substitute, which is what would have happened if
		"contact details are in" had been read as "whatever contact fields
		exist".
		"""
		joined = " ".join(staff_api.ROW_FIELDS)
		self.assertNotIn("cell_number", joined)
		self.assertIn("company_email", joined)
