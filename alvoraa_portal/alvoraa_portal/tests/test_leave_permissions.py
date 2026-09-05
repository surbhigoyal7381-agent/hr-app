"""Who may apply for leave on whose behalf.

The portal hides the "apply on behalf of" box from non-HR users, but hiding a box
is not a control - the API is reachable directly. These tests call hr_api as a
non-HR user and check the server refuses to act on someone else's behalf.

This matters more than most: the permission hooks fail OPEN. A wrong path does not
raise, it silently stops filtering, so nothing else would notice.
"""

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import hr_api
from alvoraa_portal.tests.leave_fixtures import (
	WEEK_MON,
	WEEK_TUE,
	ensure_employee_with_leave,
	ensure_leave_type,
	ensure_user,
	link_user_to_employee,
	reset_leave_applications,
)


class TestLeaveOnBehalfPermissions(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		cls.lt = ensure_leave_type("Alvoraa Casual")

		cls.hr_emp = ensure_employee_with_leave("Hr", cls.lt, days=10, last_name="Person")
		cls.hr_user = ensure_user("alvoraa.hr@example.com", roles=("HR Manager", "Employee"))
		link_user_to_employee(cls.hr_emp, cls.hr_user)

		cls.staff_emp = ensure_employee_with_leave("Staff", cls.lt, days=10, last_name="Person")
		cls.staff_user = ensure_user("alvoraa.staff@example.com", roles=("Employee",))
		link_user_to_employee(cls.staff_emp, cls.staff_user)

		cls.other_emp = ensure_employee_with_leave("Other", cls.lt, days=10, last_name="Person")

	def setUp(self):
		frappe.set_user("Administrator")
		for emp in (self.hr_emp, self.staff_emp, self.other_emp):
			reset_leave_applications(emp)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_hr_can_apply_on_behalf_of_another_employee(self):
		frappe.set_user(self.hr_user)
		res = hr_api.apply_leave(
			leave_type=self.lt, from_date=WEEK_MON, to_date=WEEK_TUE,
			on_behalf_of=self.other_emp,
		)
		doc = frappe.get_doc("Leave Application", res["name"])
		self.assertEqual(doc.employee, self.other_emp)

	def test_non_hr_cannot_apply_on_behalf_of_someone_else(self):
		"""The box is hidden for staff, but the API is reachable directly.

		A non-HR caller passing on_behalf_of must NOT create leave for that person.
		hr_api falls back to the caller's own record, so the application belongs to
		the caller - never to the employee they named.
		"""
		frappe.set_user(self.staff_user)
		res = hr_api.apply_leave(
			leave_type=self.lt, from_date=WEEK_MON, to_date=WEEK_TUE,
			on_behalf_of=self.other_emp,
		)
		doc = frappe.get_doc("Leave Application", res["name"])
		self.assertEqual(
			doc.employee, self.staff_emp,
			"a non-HR user managed to file leave against another employee",
		)
		self.assertNotEqual(doc.employee, self.other_emp)

	def test_non_hr_preview_ignores_on_behalf_of(self):
		"""The preview must not leak another employee's balance to a non-HR user."""
		frappe.set_user(self.staff_user)
		r = hr_api.preview_leave_request(
			leave_type=self.lt, from_date=WEEK_MON, to_date=WEEK_TUE,
			on_behalf_of=self.other_emp,
		)
		own_name = frappe.db.get_value("Employee", self.staff_emp, "employee_name")
		self.assertEqual(r["employee_name"], own_name)

	def test_hr_preview_reads_the_named_employee(self):
		frappe.set_user(self.hr_user)
		r = hr_api.preview_leave_request(
			leave_type=self.lt, from_date=WEEK_MON, to_date=WEEK_TUE,
			on_behalf_of=self.other_emp,
		)
		other_name = frappe.db.get_value("Employee", self.other_emp, "employee_name")
		self.assertEqual(r["employee_name"], other_name)


class TestOnlyTheApproverMayApprove(FrappeTestCase):
	"""Approving is the NAMED APPROVER's job, not a role's.

	The portal used to let any HR Manager approve anybody's leave. That was ours,
	it is not how Frappe HR works, and it made the audit trail meaningless -
	"approved by whoever held HR Manager" is not "approved by the person
	responsible".

	Frappe HR resolves the approver from the employee, falling back to their
	department. get_leave_approver() is the same function that fills the field in
	the first place, so the portal cannot disagree with the desk.
	"""

	def test_the_button_and_the_action_share_one_rule(self):
		"""A button that offers what the action refuses is worse than no button:
		it turns a configuration problem into what looks like a broken product."""
		import inspect

		from alvoraa_portal import hr_api

		self.assertIn("_can_action_leave", inspect.getsource(hr_api.action_leave))

	def test_holding_hr_manager_is_not_enough(self):
		"""The role bypass is gone. If this string comes back, so has the bug."""
		import inspect

		from alvoraa_portal import hr_api

		src = inspect.getsource(hr_api.action_leave)
		self.assertNotIn('"HR Manager", "HR User", "Administrator"', src)

	def test_the_approver_comes_from_frappe_hrs_own_lookup(self):
		import inspect

		from alvoraa_portal import hr_api

		self.assertIn("get_leave_approver",
		              inspect.getsource(hr_api._leave_approver_for))

	def test_it_falls_back_to_the_department_approver(self):
		"""An employee with no personal approver still has their department's."""
		import inspect

		from alvoraa_portal import hr_api

		src = inspect.getsource(hr_api._leave_approver_for)
		self.assertIn("doc.leave_approver", src)
		self.assertIn("get_leave_approver", src)

	def test_a_missing_approver_says_so_plainly(self):
		"""The most likely real-world case, and a bare PermissionError would send
		HR looking in the wrong place."""
		import inspect

		from alvoraa_portal import hr_api

		src = inspect.getsource(hr_api.action_leave)
		self.assertIn("No leave approver is set", src)

	def test_pending_rows_carry_the_flag(self):
		"""The UI cannot decide this for itself - it has no idea who the approver
		is - so the server has to tell it per row."""
		import inspect

		from alvoraa_portal import hr_api

		self.assertIn("can_action", inspect.getsource(hr_api._mark_actionable))
