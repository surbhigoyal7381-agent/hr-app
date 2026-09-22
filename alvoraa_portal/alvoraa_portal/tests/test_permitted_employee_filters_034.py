"""Slice 034, SEC-4 / AC-73: the shared scope filter must never fail open.

`access.permitted_employees()` fails CLOSED: a caller with no HR entitlement
gets an empty **set**, and every caller of it then filters with
`["employee", "in", sorted(names) or [""]]`, which matches nothing.

`access.permitted_employee_filters()` is the same rule in the shape Frappe
wants - a filter dict, so a screen can narrow a query in the database instead of
reading every permitted name into Python first. The shape is the danger. In
Frappe an **empty filter dict means no conditions, which means every record**.
A filter-shaped twin that copied `permitted_employees()`' "return nothing"
instinct would `return {}` and hand a plain employee the whole company.

So what is pinned here is not "the query comes back empty" - that could be true
for a hundred accidental reasons on a small fixture. It is the direct assertion
that **the return value is never `{}`, and never a dict with no keys**, for
every caller, plus a real query built from it returning zero rows for the three
callers who are entitled to nothing: a plain employee, a plain manager and a
vendor-side login.

Fixtures are slice 030's two stores - synthetic people only, tagged S030.
"""

import frappe

from alvoraa_portal.tests.leave_fixtures import ensure_user
from alvoraa_portal.tests.test_store_hr_scoping_030 import STORE_A, STORE_B, _Stores
import hrms.alvoraa_hr_core.access as access


class _FiltersBase(_Stores):
	"""The two stores, plus a login that is outside HR altogether."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# A vendor-side login. ensure_user only attaches roles that exist on the
		# site, so on a bench without the vendor app this is a user with no roles
		# at all - still exactly what the test is about, a caller with no HR
		# entitlement. The assertion below says so out loud rather than assuming.
		cls.vendor_user = ensure_user("s034.vendor@example.com", roles=("Grace Vendor Portal",))
		frappe.db.commit()

	def _query(self, filters):
		"""A real Employee read built from the helper's own return value.

		frappe.get_all does not check permissions and has no default row limit for
		a real doctype (checked in frappe 16.33.1, model/qb_query.py) - the same
		call permitted_employees() makes, so the two shapes are compared fairly.
		"""
		return frappe.get_all("Employee", filters=filters, pluck="name")


class TestTheFilterHelperNeverFailsOpen(_FiltersBase):
	def test_it_is_never_an_empty_dict_for_any_caller(self):
		"""AC-73's direct assertion. `{}` is the one return value that is a leak."""
		for user in (self.store_hr_user, self.hr_user, self.sysman_user,
		             self.manager_user, self.subject_user, self.vendor_user):
			self._as(user)
			filters = access.permitted_employee_filters()
			self.assertIsInstance(filters, dict, msg=user)
			self.assertNotEqual(filters, {}, msg=user)
			self.assertTrue(filters.keys(), msg=user)

	def test_a_caller_with_no_hr_entitlement_gets_a_refusal_that_matches_nothing(self):
		"""A plain employee, a plain manager and a vendor login: zero rows."""
		for user in (self.subject_user, self.manager_user, self.vendor_user):
			self._as(user)
			self.assertFalse(
				{"HR Manager", "HR User", "System Manager", "Administrator"} & set(frappe.get_roles(user)),
				msg=f"{user} was given an HR role by a fixture; this test would pass for the wrong reason",
			)
			filters = access.permitted_employee_filters()
			self.assertEqual(filters, access.NO_EMPLOYEES, msg=user)
			self.assertEqual(self._query(filters), [], msg=user)

	def test_the_refusal_is_a_condition_not_the_absence_of_one(self):
		"""The reason the whole file exists, pinned as one line."""
		self.assertNotEqual(access.NO_EMPLOYEES, {})
		self.assertNotEqual(access.ALL_EMPLOYEES, {})
		self.assertEqual(self._query(access.NO_EMPLOYEES), [])

	def test_mutating_what_a_caller_gets_back_cannot_widen_the_next_caller(self):
		"""The helper hands out copies, so the module constants stay constants."""
		self._as(self.subject_user)
		first = access.permitted_employee_filters()
		first["name"] = ["!=", ""]
		self.assertEqual(access.NO_EMPLOYEES, {"name": ["in", []]})
		self.assertEqual(access.permitted_employee_filters(), {"name": ["in", []]})


class TestTheFilterHelperSaysExactlyWhatPermittedEmployeesSays(_FiltersBase):
	"""One rule in two shapes. If these ever disagree, one screen is wrong."""

	def test_the_two_shapes_agree_for_every_persona(self):
		for user in (self.store_hr_user, self.hr_user, self.sysman_user,
		             self.manager_user, self.subject_user, self.vendor_user):
			self._as(user)
			self.assertEqual(
				set(self._query(access.permitted_employee_filters())),
				access.permitted_employees(),
				msg=user,
			)

	def test_store_hr_is_still_their_store_and_nobody_with_an_empty_branch(self):
		self._as(self.store_hr_user)
		filters = access.permitted_employee_filters()
		self.assertEqual(filters.get("branch"), ["in", [STORE_A]])
		rows = set(self._query(filters))
		self.assertEqual(rows, {self.store_hr, self.a1, self.a2})
		self.assertFalse(rows & self.outside)

	def test_company_wide_hr_gets_companies_and_no_branch_condition(self):
		self._as(self.hr_user)
		filters = access.permitted_employee_filters()
		self.assertIn("company", filters)
		self.assertNotIn("branch", filters)
		self.assertTrue({self.a1, self.a2, self.b1, self.n1} <= set(self._query(filters)))

	def test_system_manager_is_not_narrowed(self):
		self._as(self.sysman_user)
		filters = access.permitted_employee_filters()
		self.assertEqual(filters, access.ALL_EMPLOYEES)
		self.assertTrue(
			{self.store_hr, self.a1, self.a2, self.b1, self.n1} <= set(self._query(filters))
		)

	def test_a_leaver_is_still_in_scope_because_the_caller_adds_status_itself(self):
		"""permitted_employees() returns every status on purpose (slice 030).

		The filter shape must not quietly change that, or a leaver's reviews
		stop belonging to the store that had them. A screen that wants Active
		people adds "status" itself - the Team screen does, and AC-72 tests it.
		"""
		frappe.db.set_value("Employee", self.a2, "status", "Left", update_modified=False)
		frappe.db.commit()
		try:
			self._as(self.store_hr_user)
			filters = access.permitted_employee_filters()
			self.assertIn(self.a2, self._query(filters))
			self.assertNotIn(self.a2, self._query({**filters, "status": "Active"}))
		finally:
			frappe.db.set_value("Employee", self.a2, "status", "Active", update_modified=False)
			frappe.db.commit()

	def test_the_store_b_people_are_outside_store_a(self):
		"""STORE_B exists in the fixture; name it so the import is not dead weight."""
		self.assertEqual(frappe.db.get_value("Employee", self.b1, "branch"), STORE_B)
		self._as(self.store_hr_user)
		self.assertNotIn(self.b1, self._query(access.permitted_employee_filters()))
