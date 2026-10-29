"""Slice 076 Part C (AC-79): open portal claims get the approver they never had.

Before Part C the portal filed claims with no `expense_approver`, so nobody's
Pending list could ever show them. This sets it on every open Draft claim that
has none, by the same lookup filing now uses (the Employee's expense approver,
else their Department's first). It saves the document, so Frappe HR shares the
claim with the approver as it does for any claim.

A claim whose person has no approver, or which will not save, is left as it is
and counted. Prints "set N, unresolvable M" and names no person. A second run
finds nothing to do. Rollback: clear the field by hand; nothing else changed.
"""

import frappe

from alvoraa_portal.hr_api import expense_approver_for


def execute():
	done = left = 0
	for name in frappe.get_all("Expense Claim", filters={"docstatus": 0, "approval_status": "Draft",
	                                                     "expense_approver": ["is", "not set"]}, pluck="name"):
		doc = frappe.get_doc("Expense Claim", name)
		approver = expense_approver_for(doc.employee)
		# The claimant as their own approver would be a claim nobody can decide.
		if not approver or approver == frappe.db.get_value("Employee", doc.employee, "user_id"):
			left += 1
			continue
		frappe.db.savepoint("alvoraa_ec_backfill")
		try:
			doc.expense_approver = approver
			doc.save()
			done += 1
		except Exception:
			frappe.db.rollback(save_point="alvoraa_ec_backfill")
			left += 1
	print("Expense claim approvers: set %d, unresolvable %d" % (done, left))
