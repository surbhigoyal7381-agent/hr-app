"""ALV-178: pin Frappe HR's ERPNext integration so it cannot vanish again.

On 31 Jul 2026 one commit (48f5439) removed the hooks and functions that connect
Frappe HR to accounting. Nothing failed loudly: the "Create Payment" button broke,
expense claims stopped posting to the ledger and never became "Paid", and the
change went unnoticed for two months.

These tests live in alvoraa_portal because its suite runs in CI. Each one names
what it protects, so a merge that drops a hook fails here.
"""

import importlib
import inspect

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal.tests.leave_fixtures import ensure_employee_with_leave, ensure_leave_type
from alvoraa_portal.tests.test_expense_and_scoping import ensure_expense_type
from alvoraa_portal.tests.utils import ensure_fiscal_years

EC = "hrms.hr.doctype.expense_claim.expense_claim"
FNF = "hrms.hr.doctype.full_and_final_statement.full_and_final_statement"
SW = "hrms.payroll.doctype.salary_withholding.salary_withholding"
SS = "hrms.payroll.doctype.salary_slip.salary_slip"


def _handlers(doctype, event):
	return frappe.get_hooks("doc_events").get(doctype, {}).get(event, [])


class TestIntegrationHooksArePresent(FrappeTestCase):
	def assertHook(self, doctype, event, handler):
		self.assertIn(
			handler,
			_handlers(doctype, event),
			f"{doctype}.{event} lost {handler} - see ALV-178",
		)

	def test_payment_entry_marks_expense_claims_paid(self):
		for event in ("on_submit", "on_cancel", "on_update_after_submit"):
			self.assertHook("Payment Entry", event, f"{EC}.update_payment_for_expense_claim")

	def test_unreconcile_payment_updates_expense_claims(self):
		self.assertHook("Unreconcile Payment", "on_submit", f"{EC}.update_payment_for_expense_claim")

	def test_journal_entry_hooks(self):
		self.assertHook("Journal Entry", "validate", f"{EC}.validate_expense_claim_in_jv")
		for event in ("on_submit", "on_cancel"):
			self.assertHook("Journal Entry", event, f"{EC}.update_payment_for_expense_claim")
			self.assertHook("Journal Entry", event, f"{FNF}.update_full_and_final_statement_status")
			self.assertHook("Journal Entry", event, f"{SW}.update_salary_withholding_payment_status")
		self.assertHook("Journal Entry", "on_update_after_submit", f"{EC}.update_payment_for_expense_claim")
		self.assertHook("Journal Entry", "on_cancel", f"{SS}.unlink_ref_doc_from_salary_slip")

	def test_company_fills_expense_claim_type_accounts(self):
		self.assertHook("Company", "on_update", "hrms.overrides.company.set_expense_claim_type_accounts")

	def test_payment_entry_override(self):
		self.assertIn(
			"hrms.overrides.employee_payment_entry.EmployeePaymentEntry",
			frappe.get_hooks("override_doctype_class").get("Payment Entry", []),
		)
		self.assertIn(
			"hrms.overrides.employee_project.EmployeeProject",
			frappe.get_hooks("override_doctype_class").get("Project", []),
		)

	def test_erpnext_hook_lists(self):
		expected = {
			"advance_payment_payable_doctypes": ("Leave Encashment", "Gratuity", "Employee Advance"),
			"invoice_doctypes": ("Expense Claim",),
			"repost_allowed_doctypes": ("Expense Claim",),
			"audit_trail_doctypes": (
				"Expense Claim",
				"Payroll Entry",
				"Salary Slip",
				"Leave Encashment",
				"Gratuity",
			),
		}
		for hook, doctypes in expected.items():
			got = frappe.get_hooks(hook) or []
			for doctype in doctypes:
				self.assertIn(doctype, got, f"hook {hook} lost {doctype} - see ALV-178")

	def test_payment_entry_and_journal_entry_form_scripts(self):
		doctype_js = frappe.get_hooks("doctype_js")
		self.assertIn("public/js/erpnext/payment_entry.js", doctype_js.get("Payment Entry", []))
		self.assertIn("public/js/erpnext/journal_entry.js", doctype_js.get("Journal Entry", []))


class TestIntegrationCodeIsPresent(FrappeTestCase):
	def test_payment_functions_exist_and_are_whitelisted(self):
		pe = importlib.import_module("hrms.overrides.employee_payment_entry")

		for name in ("get_payment_entry_for_employee", "get_payment_reference_details"):
			fn = getattr(pe, name, None)
			self.assertIsNotNone(fn, f"{name} is missing - the Create Payment button breaks")
			self.assertIn(fn, frappe.whitelisted, f"{name} is not whitelisted")

	def test_payment_entry_override_allows_hr_references(self):
		from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry

		from hrms.overrides.employee_payment_entry import EmployeePaymentEntry

		self.assertTrue(issubclass(EmployeePaymentEntry, PaymentEntry))
		pe = frappe.new_doc("Payment Entry")
		self.assertIsInstance(pe, EmployeePaymentEntry)
		pe.party_type = "Employee"
		for doctype in ("Expense Claim", "Employee Advance", "Leave Encashment", "Gratuity"):
			self.assertIn(doctype, pe.get_valid_reference_doctypes())

	def test_ledger_posting_controllers_are_accounts_controllers(self):
		from erpnext.controllers.accounts_controller import AccountsController

		from hrms.hr.doctype.expense_claim.expense_claim import ExpenseClaim
		from hrms.hr.doctype.leave_encashment.leave_encashment import LeaveEncashment
		from hrms.payroll.doctype.gratuity.gratuity import Gratuity

		for cls in (ExpenseClaim, LeaveEncashment, Gratuity):
			self.assertTrue(issubclass(cls, AccountsController), f"{cls.__name__} lost AccountsController")

	def test_no_ledger_stub_left_behind(self):
		"""48f5439 replaced ledger code with `pass  # ... (no erpnext)`."""
		for name in (
			"hrms.hr.doctype.expense_claim.expense_claim",
			"hrms.hr.doctype.employee_advance.employee_advance",
			"hrms.hr.doctype.leave_encashment.leave_encashment",
			"hrms.payroll.doctype.gratuity.gratuity",
			"hrms.overrides.employee_payment_entry",
		):
			module = importlib.import_module(name)
			self.assertNotIn("(no erpnext)", inspect.getsource(module), name)


class TestExpenseClaimPaidEndToEnd(FrappeTestCase):
	"""The path Surbhi hit on production: submit a claim, Create Payment, submit it,
	and the claim is Paid, with ledger entries on both sides."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		ensure_fiscal_years()
		lt = ensure_leave_type("Alvoraa Casual")
		cls.employee = ensure_employee_with_leave("Payee", lt, days=1, last_name="ALV178")
		cls.company = frappe.db.get_value("Employee", cls.employee, "company")
		cls.etype = ensure_expense_type(company=cls.company)
		cls.bank = frappe.db.get_value(
			"Account", {"company": cls.company, "account_type": "Cash", "is_group": 0}, "name"
		)
		if not frappe.db.get_value("Company", cls.company, "default_cash_account"):
			frappe.db.set_value("Company", cls.company, "default_cash_account", cls.bank)

	def _claim(self, amount=250):
		company = frappe.db.get_value(
			"Company", self.company, ["default_expense_claim_payable_account", "cost_center"], as_dict=True
		)
		claim = frappe.get_doc(
			{
				"doctype": "Expense Claim",
				"employee": self.employee,
				"company": self.company,
				"posting_date": frappe.utils.today(),
				"currency": frappe.db.get_value("Company", self.company, "default_currency"),
				"exchange_rate": 1,
				"approval_status": "Approved",
				"payable_account": company.default_expense_claim_payable_account,
				"cost_center": company.cost_center,
				"expenses": [
					{
						"expense_date": frappe.utils.today(),
						"expense_type": self.etype,
						"amount": amount,
						"sanctioned_amount": amount,
						"cost_center": company.cost_center,
					}
				],
			}
		)
		claim.insert(ignore_permissions=True)
		claim.submit()
		return claim

	def _gl_count(self, voucher_type, voucher_no):
		return frappe.db.count(
			"GL Entry", {"voucher_type": voucher_type, "voucher_no": voucher_no, "is_cancelled": 0}
		)

	def test_claim_posts_and_becomes_paid_then_unpaid_on_cancel(self):
		from hrms.overrides.employee_payment_entry import get_payment_entry_for_employee

		claim = self._claim()
		self.assertGreaterEqual(self._gl_count("Expense Claim", claim.name), 2, "claim posted nothing")
		self.assertEqual(claim.status, "Unpaid")

		pe = get_payment_entry_for_employee("Expense Claim", claim.name)
		pe.reference_no = "ALV-178"
		pe.reference_date = frappe.utils.today()
		pe.insert(ignore_permissions=True)
		pe.submit()
		self.assertGreaterEqual(self._gl_count("Payment Entry", pe.name), 2)

		claim.reload()
		self.assertEqual(claim.status, "Paid")
		self.assertEqual(claim.total_amount_reimbursed, claim.grand_total)

		pe.cancel()
		claim.reload()
		self.assertEqual(claim.status, "Unpaid")
		self.assertEqual(claim.total_amount_reimbursed, 0)

	def test_claim_paid_by_journal_entry_then_cancelled(self):
		claim = self._claim(amount=120)
		je = frappe.get_doc({
			"doctype": "Journal Entry",
			"voucher_type": "Bank Entry",
			"company": self.company,
			"posting_date": frappe.utils.today(),
			"cheque_no": "ALV-178",
			"cheque_date": frappe.utils.today(),
			"accounts": [
				{
					"account": claim.payable_account,
					"party_type": "Employee",
					"party": self.employee,
					"debit_in_account_currency": 120,
					"reference_type": "Expense Claim",
					"reference_name": claim.name,
					"cost_center": claim.cost_center,
				},
				{
					"account": self.bank,
					"credit_in_account_currency": 120,
					"cost_center": claim.cost_center,
				},
			],
		})
		je.insert(ignore_permissions=True)
		je.submit()
		claim.reload()
		self.assertEqual(claim.status, "Paid")

		je.cancel()
		claim.reload()
		self.assertEqual(claim.status, "Unpaid")

	def test_journal_entry_cannot_overpay_a_claim(self):
		claim = self._claim(amount=50)
		je = frappe.get_doc({
			"doctype": "Journal Entry",
			"company": self.company,
			"posting_date": frappe.utils.today(),
			"accounts": [
				{
					"account": claim.payable_account,
					"party_type": "Employee",
					"party": self.employee,
					"debit_in_account_currency": 80,
					"reference_type": "Expense Claim",
					"reference_name": claim.name,
					"cost_center": claim.cost_center,
				},
				{"account": self.bank, "credit_in_account_currency": 80, "cost_center": claim.cost_center},
			],
		})
		with self.assertRaises(frappe.ValidationError):
			je.insert(ignore_permissions=True)

	def test_employee_advance_paid_then_unpaid_on_cancel(self):
		from hrms.overrides.employee_payment_entry import get_payment_entry_for_employee

		advance_account = frappe.db.get_value("Company", self.company, "default_employee_advance_account")
		self.assertTrue(advance_account, "the test company has no Employee Advances account")
		# Frappe HR only accepts a Receivable advance account. The standard chart
		# leaves "Employee Advances" untyped, so HR has to set it; do the same here.
		frappe.db.set_value("Account", advance_account, "account_type", "Receivable")
		advance = frappe.get_doc({
			"doctype": "Employee Advance",
			"employee": self.employee,
			"company": self.company,
			"posting_date": frappe.utils.today(),
			"currency": frappe.db.get_value("Company", self.company, "default_currency"),
			"exchange_rate": 1,
			"advance_amount": 300,
			"advance_account": advance_account,
			"purpose": "ALV-178",
		})
		advance.insert(ignore_permissions=True)
		advance.submit()
		self.assertEqual(advance.status, "Unpaid")

		pe = get_payment_entry_for_employee("Employee Advance", advance.name)
		pe.reference_no = "ALV-178"
		pe.reference_date = frappe.utils.today()
		pe.insert(ignore_permissions=True)
		pe.submit()
		advance.reload()
		self.assertEqual(advance.paid_amount, 300)
		self.assertEqual(advance.status, "Paid")

		pe.cancel()
		advance.reload()
		self.assertEqual(advance.paid_amount, 0)
		self.assertEqual(advance.status, "Unpaid")
