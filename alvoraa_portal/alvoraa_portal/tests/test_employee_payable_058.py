"""Slice 058: the account an expense claim is owed from, filled once.

ALV-178 restored ledger posting for expense claims. That turned a silent bug
(nothing reached the accounts) into a blocked feature (every claim refused,
because `Company.default_expense_claim_payable_account` was empty on every
tenant). Upstream Frappe HR reads that field in three places and fills it
nowhere, so nobody had ever set it.

The three tests that matter most are not the happy path:

  * **A chosen account is never overwritten.** A default that argues with an
    accountant's decision is a bug, not a convenience.
  * **An expense account is refused.** Point this field at an expense account
    and every claim debits the expense twice - once as its own line, once as
    the "payable" - and no screen shows it. Only a trial balance would, months
    later.
  * **A company with no chart of accounts still saves.** `bench migrate` runs
    the patch on every site. A tenant mid-provisioning must not be stopped.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import expense_accounts
from alvoraa_portal.tests import fixtures_043 as fx

FIELD = expense_accounts.FIELD


def _company():
	return fx.ensure_company()


class TestTheAccountIsCreatedAndPointedAt(FrappeTestCase):

	def setUp(self):
		frappe.set_user("Administrator")
		self.company = _company()

	def test_the_employee_payable_account_exists_after_filling(self):
		expense_accounts._fill(self.company)
		name = expense_accounts._leaf(self.company, expense_accounts.ACCOUNT_NAME)
		self.assertTrue(name, "Employee Payable was not created")

	def test_the_company_field_points_at_it(self):
		expense_accounts._fill(self.company)
		value = frappe.db.get_value("Company", self.company, FIELD)
		self.assertTrue(value)
		self.assertEqual(
			frappe.db.get_value("Account", value, "account_name"),
			expense_accounts.ACCOUNT_NAME,
		)

	def test_it_is_a_liability_and_payable(self):
		"""Both, because either alone is not enough.

		Without root_type Liability the books are wrong. Without account_type
		Payable, ERPNext will not offer it where a payable account is asked for,
		so the field can be set and still not work.
		"""
		expense_accounts._fill(self.company)
		account = frappe.db.get_value("Company", self.company, FIELD)
		row = frappe.db.get_value(
			"Account", account, ["root_type", "account_type", "is_group"], as_dict=True
		)
		self.assertEqual(row.root_type, "Liability")
		self.assertEqual(row.account_type, "Payable")
		self.assertEqual(row.is_group, 0)

	def test_running_it_twice_changes_nothing(self):
		"""`bench migrate` runs on every deploy. A second account would be a mess."""
		expense_accounts._fill(self.company)
		first = frappe.db.get_value("Company", self.company, FIELD)

		expense_accounts._fill(self.company)
		second = frappe.db.get_value("Company", self.company, FIELD)

		self.assertEqual(first, second)
		matches = frappe.get_all(
			"Account",
			filters={"account_name": expense_accounts.ACCOUNT_NAME, "company": self.company},
			pluck="name",
		)
		self.assertEqual(len(matches), 1, f"duplicate accounts created: {matches}")

	def test_it_sits_under_a_liability_group(self):
		"""Beside Creditors, never inside it - the whole reason Creditors was refused."""
		expense_accounts._fill(self.company)
		account = frappe.db.get_value("Company", self.company, FIELD)
		parent = frappe.db.get_value("Account", account, "parent_account")
		self.assertTrue(parent)
		self.assertEqual(frappe.db.get_value("Account", parent, "root_type"), "Liability")
		self.assertNotIn("Creditors", parent)


class TestItNeverOverwritesADecision(FrappeTestCase):
	"""The failure mode that would be worst in a customer's hands."""

	def setUp(self):
		frappe.set_user("Administrator")
		self.company = _company()
		self.saved = frappe.db.get_value("Company", self.company, FIELD)

	def tearDown(self):
		frappe.db.set_value("Company", self.company, FIELD, self.saved,
		                    update_modified=False)

	def test_an_account_already_chosen_is_left_alone(self):
		chosen = frappe.db.get_value(
			"Account",
			{"company": self.company, "is_group": 0, "root_type": "Liability",
			 "account_type": "Payable"},
			"name",
		)
		self.assertTrue(chosen, "fixture needs a payable account to choose")

		frappe.db.set_value("Company", self.company, FIELD, chosen, update_modified=False)
		expense_accounts._fill(self.company)

		self.assertEqual(
			frappe.db.get_value("Company", self.company, FIELD), chosen,
			"the default overwrote an account somebody had chosen",
		)


class TestTheWrongKindOfAccountIsRefused(FrappeTestCase):
	"""An expense account here double-counts every claim, invisibly."""

	def setUp(self):
		frappe.set_user("Administrator")
		self.company = _company()

	def test_an_expense_account_is_refused_with_a_plain_reason(self):
		expense = frappe.db.get_value(
			"Account", {"company": self.company, "is_group": 0, "root_type": "Expense"}, "name"
		)
		self.assertTrue(expense, "fixture needs an expense account")

		doc = frappe.get_doc("Company", self.company)
		doc.set(FIELD, expense)
		with self.assertRaises(frappe.ValidationError):
			expense_accounts.validate_expense_claim_payable_account(doc)

	def test_a_liability_account_passes(self):
		liability = frappe.db.get_value(
			"Account", {"company": self.company, "is_group": 0, "root_type": "Liability"}, "name"
		)
		doc = frappe.get_doc("Company", self.company)
		doc.set(FIELD, liability)
		expense_accounts.validate_expense_claim_payable_account(doc)  # must not raise

	def test_an_empty_field_passes(self):
		"""Mid-provisioning, and on any site with no ERPNext."""
		doc = frappe.get_doc("Company", self.company)
		doc.set(FIELD, None)
		expense_accounts.validate_expense_claim_payable_account(doc)  # must not raise


class TestACompanyWithNoChartIsNotBroken(FrappeTestCase):
	"""`bench migrate` runs the patch everywhere. It must not throw.

	**These two tests used to pass for the wrong reason**, and that is worth
	recording. They stubbed out `_parent_group` only, which is enough ONLY while
	the account does not exist yet. Once the patch had created `Employee
	Payable` on the test site, `_fill` found it through `_leaf` and returned
	before `_parent_group` was ever reached - so the stub did nothing and both
	tests went red. The first green run was luck of ordering.

	A company with no chart of accounts has neither the account nor a parent
	group to create it under, so both have to be stubbed to describe that
	company honestly.
	"""

	def setUp(self):
		frappe.set_user("Administrator")
		self.company = _company()
		self.saved = frappe.db.get_value("Company", self.company, FIELD)
		self._leaf = expense_accounts._leaf
		self._parent_group = expense_accounts._parent_group
		# No existing account, and nowhere to create one: a company with no
		# chart of accounts.
		expense_accounts._leaf = lambda c, n: None
		expense_accounts._parent_group = lambda c: None
		frappe.db.set_value("Company", self.company, FIELD, None, update_modified=False)

	def tearDown(self):
		expense_accounts._leaf = self._leaf
		expense_accounts._parent_group = self._parent_group
		frappe.db.set_value("Company", self.company, FIELD, self.saved,
		                    update_modified=False)

	def test_filling_a_company_with_no_liability_group_does_nothing_quietly(self):
		expense_accounts._fill(self.company)  # must not raise
		self.assertFalse(frappe.db.get_value("Company", self.company, FIELD))

	def test_the_backfill_reports_which_companies_still_need_attention(self):
		"""The patch prints this list. If it lies, a tenant is silently broken."""
		result = expense_accounts.backfill([self.company])
		self.assertIn(self.company, result["no_chart_of_accounts"])
		self.assertNotIn(self.company, result["filled"])

	def test_the_stubs_really_describe_a_company_with_no_chart(self):
		"""Otherwise the two tests above pass without exercising anything."""
		self.assertIsNone(expense_accounts._leaf(self.company, expense_accounts.ACCOUNT_NAME))
		self.assertIsNone(expense_accounts._parent_group(self.company))


class TestTheHookIsActuallyRegistered(FrappeTestCase):
	"""A function nothing calls protects nobody."""

	def test_company_events_point_at_this_module(self):
		events = frappe.get_hooks("doc_events").get("Company", {})
		flat = " ".join(
			" ".join(v) if isinstance(v, list) else str(v) for v in events.values()
		)
		self.assertIn(
			"alvoraa_portal.expense_accounts.set_expense_claim_payable_account", flat
		)
		self.assertIn(
			"alvoraa_portal.expense_accounts.validate_expense_claim_payable_account", flat
		)

	def test_the_patch_is_registered(self):
		import pathlib

		txt = pathlib.Path(frappe.get_app_path("alvoraa_portal", "patches.txt")).read_text()
		self.assertIn("alvoraa_portal.patches.v1_0.employee_payable_account", txt)


class TestAClaimTypeAddedLaterGetsItsAccount(FrappeTestCase):
	"""The other half of the gap.

	ALV-178 fills an Expense Claim Type's account, but only when a COMPANY is
	saved. A tenant who adds a type afterwards gets one with no account, and
	every claim against it is refused with a message about HR setup.
	"""

	def setUp(self):
		frappe.set_user("Administrator")
		self.company = _company()
		self.name = "ALV058 Added Later"
		if frappe.db.exists("Expense Claim Type", self.name):
			frappe.delete_doc("Expense Claim Type", self.name,
			                  force=True, ignore_permissions=True)

	def tearDown(self):
		if frappe.db.exists("Expense Claim Type", self.name):
			frappe.delete_doc("Expense Claim Type", self.name,
			                  force=True, ignore_permissions=True)

	def test_a_new_claim_type_gets_an_account_for_this_company(self):
		doc = frappe.get_doc({
			"doctype": "Expense Claim Type",
			"expense_type": self.name,
			"accounts": [],
		})
		doc.flags.ignore_permissions = True
		doc.insert()

		self.assertTrue(
			frappe.db.exists("Expense Claim Account",
			                 {"parent": self.name, "company": self.company}),
			"a claim type created after setup got no expense account",
		)

	def test_the_account_is_an_expense_account(self):
		"""A payable account here would book the claim to the wrong side."""
		doc = frappe.get_doc({
			"doctype": "Expense Claim Type", "expense_type": self.name, "accounts": [],
		})
		doc.flags.ignore_permissions = True
		doc.insert()

		account = frappe.db.get_value(
			"Expense Claim Account",
			{"parent": self.name, "company": self.company}, "default_account")
		self.assertEqual(frappe.db.get_value("Account", account, "root_type"), "Expense")

	def test_filling_twice_adds_one_row_not_two(self):
		doc = frappe.get_doc({
			"doctype": "Expense Claim Type", "expense_type": self.name, "accounts": [],
		})
		doc.flags.ignore_permissions = True
		doc.insert()

		expense_accounts.fill_claim_type_accounts(self.name)

		rows = frappe.get_all("Expense Claim Account",
		                      filters={"parent": self.name, "company": self.company},
		                      pluck="name")
		self.assertEqual(len(rows), 1, f"duplicate rows: {rows}")

	def test_the_hook_is_registered(self):
		events = frappe.get_hooks("doc_events").get("Expense Claim Type", {})
		flat = " ".join(
			" ".join(v) if isinstance(v, list) else str(v) for v in events.values()
		)
		self.assertIn("alvoraa_portal.expense_accounts.set_expense_claim_type_account", flat)
