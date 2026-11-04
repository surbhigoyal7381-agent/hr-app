"""Expense claims, and the rule that a user sees only their own records.

The scoping checks matter because the portal's permission hooks fail OPEN: a wrong
path does not raise, it silently stops filtering. Nothing surfaces that except a
test that logs in as one employee and looks for another's data.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_goals.tests.utils import ensure_company
from alvoraa_portal import hr_api
from alvoraa_portal.tests.leave_fixtures import (
	ensure_employee_with_leave,
	ensure_leave_type,
	ensure_user,
	link_user_to_employee,
)


def _leaf_account(company, root_type, account_type=None):
	filters = {"company": company, "is_group": 0, "root_type": root_type}
	if account_type:
		filters["account_type"] = account_type
	return frappe.db.get_value("Account", filters, "name", order_by="lft")


def ensure_expense_setup(company=None):
	"""ALV-178: an Expense Claim posts to the ledger again, so the portal needs the
	company's payable account and an expense account on the claim type. Give the
	test company both, the way HR would."""
	company = company or ensure_company()
	if not frappe.db.get_value("Company", company, "default_expense_claim_payable_account"):
		frappe.db.set_value(
			"Company",
			company,
			"default_expense_claim_payable_account",
			_leaf_account(company, "Liability", "Payable"),
		)
	return company


def ensure_expense_type(name="Alvoraa Travel", company=None):
	company = ensure_expense_setup(company)
	if not frappe.db.exists("Expense Claim Type", name):
		doc = frappe.get_doc({"doctype": "Expense Claim Type", "expense_type": name, "accounts": []})
		doc.insert(ignore_permissions=True)
	if not frappe.db.exists("Expense Claim Account", {"parent": name, "company": company}):
		doc = frappe.get_doc("Expense Claim Type", name)
		doc.append("accounts", {"company": company, "default_account": _leaf_account(company, "Expense")})
		doc.save(ignore_permissions=True)
	frappe.db.commit()
	return name


def a_bill(user=None):
	"""One real uploaded bill, and the `File` row id `apply_expense_claim` needs.

	Slice 081 made the bill compulsory. **Every test that files a claim
	successfully was updated to pass one, and not one assertion was loosened to
	let a bill-less claim through** - that would have deleted the feature from
	the suite while leaving the tests green.

	It is a real upload through the real endpoint, so these fixtures exercise
	the magic-byte check and the re-encode rather than planting a `File` row
	that the product would never have produced.
	"""
	from PIL import Image

	import base64
	import io

	from alvoraa_portal import expense_evidence

	img = Image.new("RGB", (900, 700))
	px = img.load()
	for y in range(0, 700, 3):
		for x in range(0, 900, 3):
			px[x, y] = ((x * 7) % 256, (y * 13) % 256, (x * y) % 256)
	out = io.BytesIO()
	img.save(out, format="JPEG", quality=90)

	was = frappe.session.user
	if user:
		frappe.set_user(user)
	try:
		return expense_evidence.upload_evidence(
			file=base64.b64encode(out.getvalue()).decode(), kind="bill")["file_id"]
	finally:
		if user:
			frappe.set_user(was)


def _give_an_approver(*employees):
	"""Slice 076 Part C (decision 4): a claim with no approver is refused, so the
	claimants here get one, as real data must have."""
	approver = ensure_user("alvoraa.claim.approver@example.com", roles=("Expense Approver",))
	# An approver must be an enabled login with an Active Employee record, or
	# the claim is refused too (Surbhi, 30 Oct 2026).
	lt = ensure_leave_type("Alvoraa Casual")
	link_user_to_employee(ensure_employee_with_leave("Claim", lt, days=1, last_name="Approver"), approver)
	for emp in employees:
		frappe.db.set_value("Employee", emp, "expense_approver", approver)
	frappe.db.commit()


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
		_give_an_approver(cls.emp_a, cls.emp_b)

	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_zero_amount_is_rejected(self):
		frappe.set_user(self.user_a)
		with self.assertRaises(frappe.ValidationError):
			hr_api.apply_expense_claim(expense_type=self.etype, expense_date=frappe.utils.today(), amount=0)

	def test_negative_amount_is_rejected(self):
		frappe.set_user(self.user_a)
		with self.assertRaises(frappe.ValidationError):
			hr_api.apply_expense_claim(expense_type=self.etype, expense_date=frappe.utils.today(), amount=-50)

	def test_claim_is_filed_for_the_caller(self):
		"""There is no on-behalf path here: the claim must belong to whoever called."""
		frappe.set_user(self.user_a)
		res = hr_api.apply_expense_claim(
			expense_type=self.etype, expense_date=frappe.utils.today(), amount=123,
			file_id=a_bill(),
		)
		doc = frappe.get_doc("Expense Claim", res["name"])
		self.assertEqual(doc.employee, self.emp_a)

	def test_claim_takes_the_company_payable_account_and_cost_centre(self):
		"""ALV-178: without these the claim cannot be approved (submitted)."""
		frappe.set_user(self.user_a)
		res = hr_api.apply_expense_claim(
			expense_type=self.etype, expense_date=frappe.utils.today(), amount=45,
			file_id=a_bill(),
		)
		doc = frappe.get_doc("Expense Claim", res["name"])
		company = frappe.db.get_value(
			"Company", doc.company, ["default_expense_claim_payable_account", "cost_center"], as_dict=True
		)
		self.assertEqual(doc.payable_account, company.default_expense_claim_payable_account)
		self.assertEqual(doc.cost_center, company.cost_center)

	def test_missing_payable_account_says_what_hr_must_set(self):
		"""ALV-178: a plain message naming the setting, before anything is saved."""
		company = frappe.db.get_value("Employee", self.emp_a, "company")
		saved = frappe.db.get_value("Company", company, "default_expense_claim_payable_account")
		frappe.db.set_value("Company", company, "default_expense_claim_payable_account", None)
		try:
			frappe.set_user(self.user_a)
			before = frappe.db.count("Expense Claim", {"employee": self.emp_a})
			with self.assertRaises(frappe.ValidationError) as ctx:
				hr_api.apply_expense_claim(
					expense_type=self.etype, expense_date=frappe.utils.today(), amount=10
				)
			self.assertIn("Default Expense Claim Payable Account", str(ctx.exception))
			self.assertEqual(frappe.db.count("Expense Claim", {"employee": self.emp_a}), before)
		finally:
			frappe.set_user("Administrator")
			frappe.db.set_value("Company", company, "default_expense_claim_payable_account", saved)


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
		_give_an_approver(cls.emp_a, cls.emp_b)

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
			expense_type=ensure_expense_type(), expense_date=frappe.utils.today(), amount=77,
			file_id=a_bill(),
		)

		frappe.set_user(self.user_b)
		claims = hr_api.get_expense_claims()
		rows = claims if isinstance(claims, list) else claims.get("claims", [])
		for row in rows:
			self.assertNotEqual(
				row.get("employee"),
				self.emp_a,
				"employee B can see employee A's expense claim",
			)
