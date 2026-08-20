"""Expense claims, and the rule that a user sees only their own records.

The scoping checks matter because the portal's permission hooks fail OPEN: a wrong
path does not raise, it silently stops filtering. Nothing surfaces that except a
test that logs in as one employee and looks for another's data.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import hr_api
from alvoraa_portal.tests.leave_fixtures import (
	ensure_employee_with_leave,
	ensure_leave_type,
	ensure_user,
	link_user_to_employee,
)


def ensure_expense_type(name="Alvoraa Travel"):
	if frappe.db.exists("Expense Claim Type", name):
		return name
	doc = frappe.get_doc(
		{
			"doctype": "Expense Claim Type",
			"expense_type": name,
			"accounts": [],
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return doc.name


class TestExpenseClaims(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		lt = ensure_leave_type("Alvoraa Casual")
		cls.etype = ensure_expense_type()

		cls.emp_a = ensure_employee_with_leave("Claimant", lt, days=1, last_name="Aye")
		cls.user_a = ensure_user("alvoraa.claimant.a@example.com", roles=("Employee",))
		link_user_to_employee(cls.emp_a, cls.user_a)

		cls.emp_b = ensure_employee_with_leave("Claimant", lt, days=1, last_name="Bee")
		cls.user_b = ensure_user("alvoraa.claimant.b@example.com", roles=("Employee",))
		link_user_to_employee(cls.emp_b, cls.user_b)

	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_zero_amount_is_rejected(self):
		frappe.set_user(self.user_a)
		with self.assertRaises(frappe.ValidationError):
			hr_api.apply_expense_claim(
				expense_type=self.etype, expense_date=frappe.utils.today(), amount=0
			)

	def test_negative_amount_is_rejected(self):
		frappe.set_user(self.user_a)
		with self.assertRaises(frappe.ValidationError):
			hr_api.apply_expense_claim(
				expense_type=self.etype, expense_date=frappe.utils.today(), amount=-50
			)

	def test_claim_is_filed_for_the_caller(self):
		"""There is no on-behalf path here: the claim must belong to whoever called."""
		frappe.set_user(self.user_a)
		res = hr_api.apply_expense_claim(
			expense_type=self.etype, expense_date=frappe.utils.today(), amount=123
		)
		doc = frappe.get_doc("Expense Claim", res["name"])
		self.assertEqual(doc.employee, self.emp_a)


class TestEmployeeScoping(FrappeTestCase):
	"""One employee must never see another's records through the portal API."""

	@classmethod
	def setUpClass(cls):
		lt = ensure_leave_type("Alvoraa Casual")
		cls.emp_a = ensure_employee_with_leave("Scope", lt, days=5, last_name="Aye")
		cls.user_a = ensure_user("alvoraa.scope.a@example.com", roles=("Employee",))
		link_user_to_employee(cls.emp_a, cls.user_a)

		cls.emp_b = ensure_employee_with_leave("Scope", lt, days=5, last_name="Bee")
		cls.user_b = ensure_user("alvoraa.scope.b@example.com", roles=("Employee",))
		link_user_to_employee(cls.emp_b, cls.user_b)

	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_portal_context_returns_the_callers_own_employee(self):
		frappe.set_user(self.user_a)
		ctx = hr_api.get_portal_context()
		self.assertEqual(ctx["employee"]["name"], self.emp_a)
		self.assertEqual(ctx["user"], self.user_a)

	def test_an_ordinary_employee_is_not_hr_or_manager(self):
		"""If this ever flips true, every HR-only screen opens up."""
		frappe.set_user(self.user_a)
		ctx = hr_api.get_portal_context()
		self.assertFalse(ctx["is_hr"], "an ordinary employee must not be treated as HR")

	def test_expense_claims_are_not_visible_across_employees(self):
		frappe.set_user(self.user_a)
		hr_api.apply_expense_claim(
			expense_type=ensure_expense_type(), expense_date=frappe.utils.today(), amount=77
		)

		frappe.set_user(self.user_b)
		claims = hr_api.get_expense_claims()
		rows = claims if isinstance(claims, list) else claims.get("claims", [])
		for row in rows:
			self.assertNotEqual(
				row.get("employee"), self.emp_a,
				"employee B can see employee A's expense claim",
			)
