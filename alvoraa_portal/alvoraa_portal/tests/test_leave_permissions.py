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
