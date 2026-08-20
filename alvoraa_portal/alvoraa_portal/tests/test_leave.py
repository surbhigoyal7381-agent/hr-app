"""Leave application rules, through the portal API that the browser actually calls.

These go through `hr_api.apply_leave` and `hr_api.preview_leave_request` rather than
building Leave Application documents directly, because the API layer is where the
portal's own permission and on-behalf logic lives. A test that inserts the doctype
directly would pass while the portal stayed broken.
"""

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import hr_api
from alvoraa_portal.tests.leave_fixtures import (
	HOLIDAY,
	WEEK_FRI,
	WEEK_MON,
	WEEK_TUE,
	ensure_employee_with_leave,
	ensure_leave_type,
)


def _as_employee(employee):
	"""Run as the user linked to `employee`, so _get_employee() resolves to them."""
	user = frappe.db.get_value("Employee", employee, "user_id")
	frappe.set_user(user or "Administrator")


class TestLeaveBalanceRules(FrappeTestCase):
	"""The quota rules Frappe HR enforces, exercised through the portal API."""

	@classmethod
	def setUpClass(cls):
		cls.lt = ensure_leave_type("Alvoraa Casual")
		cls.emp = ensure_employee_with_leave("Balance", cls.lt, days=10)

	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_preview_counts_working_days_only(self):
		"""Mon-Fri spanning one mid-week holiday is 4 days, not 5.

		This is the exact arithmetic the portal must not attempt in JavaScript.
		"""
		r = hr_api.preview_leave_request(
			leave_type=self.lt, from_date=WEEK_MON, to_date=WEEK_FRI,
			on_behalf_of=self.emp,
		)
		self.assertEqual(r["days"], 4, "the Wednesday holiday should not be charged")
		self.assertEqual(r["balance"], 10)

	@unittest.skip("KI-4: half-day leave is broken in the hrms fork - see KNOWN_ISSUES.md")
	def test_preview_half_day_counts_half(self):
		r = hr_api.preview_leave_request(
			leave_type=self.lt, from_date=WEEK_MON, to_date=WEEK_MON,
			half_day=1, half_day_date=WEEK_MON, on_behalf_of=self.emp,
		)
		self.assertEqual(r["days"], 0.5)

	def test_holiday_only_range_costs_nothing(self):
		"""A range that is entirely holiday costs 0 days - Frappe rejects those."""
		r = hr_api.preview_leave_request(
			leave_type=self.lt, from_date=HOLIDAY, to_date=HOLIDAY,
			on_behalf_of=self.emp,
		)
		self.assertEqual(r["days"], 0)

	def test_apply_leave_succeeds_within_balance(self):
		res = hr_api.apply_leave(
			leave_type=self.lt, from_date=WEEK_MON, to_date=WEEK_TUE,
			on_behalf_of=self.emp,
		)
		self.assertTrue(res.get("name"))
		doc = frappe.get_doc("Leave Application", res["name"])
		self.assertEqual(doc.employee, self.emp)
		self.assertEqual(doc.total_leave_days, 2)

	def test_apply_leave_over_quota_is_rejected(self):
		"""The server is the authority: more days than balance must not be created."""
		emp = ensure_employee_with_leave("Small", self.lt, days=1, last_name="Balance")
		with self.assertRaises(frappe.ValidationError):
			hr_api.apply_leave(
				leave_type=self.lt, from_date=WEEK_MON, to_date=WEEK_FRI,
				on_behalf_of=emp,
			)

	def test_preview_agrees_with_the_server(self):
		"""The preview must not tell the user something the server then contradicts.

		If these two ever disagree the portal either blocks a valid request or
		promises one that fails on submit.
		"""
		emp = ensure_employee_with_leave("Agree", self.lt, days=1, last_name="Balance")
		r = hr_api.preview_leave_request(
			leave_type=self.lt, from_date=WEEK_MON, to_date=WEEK_FRI, on_behalf_of=emp,
		)
		preview_would_block = (r["days"] > r["balance"]) and not r["allow_negative"]
		self.assertTrue(preview_would_block, "preview should see this as over quota")

		with self.assertRaises(frappe.ValidationError):
			hr_api.apply_leave(
				leave_type=self.lt, from_date=WEEK_MON, to_date=WEEK_FRI, on_behalf_of=emp,
			)

	def test_allow_negative_leave_type_permits_over_quota(self):
		"""With allow_negative, Frappe warns instead of blocking - so must we."""
		lt = ensure_leave_type("Alvoraa Negative OK", allow_negative=1)
		emp = ensure_employee_with_leave("Negative", lt, days=1, last_name="Balance")

		r = hr_api.preview_leave_request(
			leave_type=lt, from_date=WEEK_MON, to_date=WEEK_FRI, on_behalf_of=emp,
		)
		self.assertTrue(r["allow_negative"], "preview must not block this type")

		res = hr_api.apply_leave(
			leave_type=lt, from_date=WEEK_MON, to_date=WEEK_FRI, on_behalf_of=emp,
		)
		self.assertTrue(res.get("name"))

	def test_lwp_has_no_balance_to_check(self):
		"""Leave Without Pay draws on no allocation, so it is never over quota."""
		lt = ensure_leave_type("Alvoraa LWP", is_lwp=1)
		emp = ensure_employee_with_leave("Lwp", lt, days=0, last_name="Balance")

		r = hr_api.preview_leave_request(
			leave_type=lt, from_date=WEEK_MON, to_date=WEEK_FRI, on_behalf_of=emp,
		)
		self.assertTrue(r["unlimited"])
		self.assertIsNone(r["balance"])
