"""The account an expense claim is owed from, filled once so nobody has to know it.

## Why this file exists

On 31 July 2026 a commit stripped ERPNext out of our Frappe HR fork. Expense
claims, leave encashment and gratuity stopped writing to the ledger — silently.
`aahr` has seven submitted claims and no ledger entries for any of them. ALV-178
put the accounting back. This file closes the hole that restoring it opened.

An Expense Claim books to a **payable account**: the company owes the employee
money until it is paid. Frappe HR reads that account from
`Company.default_expense_claim_payable_account` and **never fills it** — checked
against upstream v16, which reads the field in three places and sets it nowhere.
Upstream expects a human to choose it.

No human ever did, because for two months nothing used it. So the moment ALV-178
restored the posting, every claim on every tenant hit "Payable Account is
mandatory". A silent bug became a blocked feature.

## Why a tenant cannot simply be told to set it

Every tenant HAS a chart of accounts. `tenant_setup.complete_company_setup`
runs ERPNext's setup wizard with `chart_of_accounts: "Standard"` on every
provisioning, whatever plan they are on. The Accounts module is hidden from
their desk by the plan; it is not absent from the database.

So the field is empty, not unfillable. But a Starter tenant has no Accounts
screens, and more to the point **nobody knows which account to pick.** That is a
knowledge gap, and the fix for a knowledge gap is a default, not a feature.

Frappe HR already works this way for its other two accounts:
`hrms.overrides.company.set_default_hr_accounts` fills
`default_payroll_payable_account` and `default_employee_advance_account` by
looking for accounts named "Payroll Payable" and "Employee Advances". There is
no standard-chart account for expense claims, so this one has to be created.

## Why "Employee Payable", and why not Creditors

Surbhi's decision, 2 October 2026: a dedicated account called **Employee
Payable**.

Creditors was the cheaper option — it exists on every tenant already. It was
refused for a reason worth keeping written down: Creditors is where trade
suppliers sit. Putting staff reimbursements in it makes every supplier ageing
report wrong, and a tenant who finds employee claims inside their supplier
ageing stops trusting the whole ledger.

## Why this lives in alvoraa_portal and not in the hrms fork

`set_default_hr_accounts` is the obvious place and it is the wrong one. It sits
inside our vendored copy of Frappe HR, and about sixty of their files already
carry our edits — every one a merge conflict at every upgrade (ALV-169). This
does the same job from our own app, through a `doc_events` hook, and adds
nothing to that pile.

It is also not a change to how Frappe HR behaves. We fill a field they read.
If upstream ever fills it themselves, `_fill` leaves their value alone.
"""

import frappe
from frappe import _

# The account we create and point the field at. Not translated: an account name
# is data a tenant's accountant reads and reconciles, and a chart of accounts
# that changes name with the viewer's language cannot be reconciled at all.
ACCOUNT_NAME = "Employee Payable"

# Where it goes. ERPNext's standard chart puts trade payables under
# "Accounts Payable", itself under "Current Liabilities". We sit beside
# Creditors rather than inside it, so the two never mix.
PARENT_CANDIDATES = ("Accounts Payable", "Current Liabilities")

FIELD = "default_expense_claim_payable_account"


def _leaf(company, name):
	"""An existing non-group account of this name on this company, or None."""
	return frappe.db.get_value(
		"Account", {"account_name": name, "company": company, "is_group": 0}, "name"
	)


def _parent_group(company):
	"""The group account to create under, preferring the narrower one."""
	for name in PARENT_CANDIDATES:
		found = frappe.db.get_value(
			"Account",
			{"account_name": name, "company": company, "is_group": 1, "root_type": "Liability"},
			"name",
		)
		if found:
			return found
	return None


def ensure_account(company):
	"""Create `Employee Payable` for this company if it is missing. Return its name.

	Returns None when the company has no chart of accounts to put it in, rather
	than throwing. A tenant mid-provisioning, or one restored from a backup
	taken before its accounts existed, must not be stopped from saving.
	"""
	existing = _leaf(company, ACCOUNT_NAME)
	if existing:
		return existing

	parent = _parent_group(company)
	if not parent:
		return None

	doc = frappe.get_doc({
		"doctype": "Account",
		"account_name": ACCOUNT_NAME,
		"parent_account": parent,
		"company": company,
		"is_group": 0,
		"root_type": "Liability",
		# What makes it usable as a payable account at all. Without this
		# ERPNext will not offer it where a payable account is asked for.
		"account_type": "Payable",
		"account_currency": frappe.db.get_value("Company", company, "default_currency"),
	})
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


def _is_liability(account):
	"""Guard against the one mistake that would be invisible.

	If somebody points this field at an EXPENSE account, every claim debits the
	expense twice - once as the claim's own expense line and once as the
	"payable" - and the books are wrong in a way no screen shows. Refusing a
	wrong type is cheap; finding this in a trial balance is not.
	"""
	return frappe.db.get_value("Account", account, "root_type") == "Liability"


def _fill(company_name):
	"""Point the company's claim payable field at `Employee Payable`.

	**Never overwrites.** A tenant whose accountant has already chosen an
	account has made a decision, and a default that argues with a decision is a
	bug. Only an empty field is filled.
	"""
	if frappe.local.flags.get("ignore_chart_of_accounts"):
		return

	if frappe.db.get_value("Company", company_name, FIELD):
		return

	account = ensure_account(company_name)
	if not account:
		return

	frappe.db.set_value("Company", company_name, FIELD, account, update_modified=False)


def set_expense_claim_payable_account(doc, method=None):
	"""`doc_events` hook on Company: after_insert and on_update."""
	_fill(doc.name)


def validate_expense_claim_payable_account(doc, method=None):
	"""`doc_events` validate hook: whatever is in the field must be a liability."""
	account = doc.get(FIELD)
	if account and not _is_liability(account):
		frappe.throw(
			_("{0} cannot be used for paying expense claims because it is not a "
			  "liability account. Expense claims are money the company owes its "
			  "staff, so this must be a liability account such as {1}.").format(
				frappe.bold(account), frappe.bold(ACCOUNT_NAME)),
			title=_("Wrong kind of account"),
		)


def backfill(companies=None):
	"""Fill the field on companies that already exist. Safe to run repeatedly.

	Called by the patch, and callable by hand on a tenant. Returns what it did,
	so a run can be read rather than trusted.
	"""
	names = companies or frappe.get_all("Company", pluck="name")
	done, skipped, no_chart = [], [], []

	for name in names:
		if frappe.db.get_value("Company", name, FIELD):
			skipped.append(name)
			continue
		_fill(name)
		if frappe.db.get_value("Company", name, FIELD):
			done.append(name)
		else:
			no_chart.append(name)

	return {"filled": done, "already_set": skipped, "no_chart_of_accounts": no_chart}
