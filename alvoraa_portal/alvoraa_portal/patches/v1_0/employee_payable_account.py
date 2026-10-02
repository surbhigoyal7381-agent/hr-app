"""Slice 058: give every existing company an Employee Payable account.

New companies get it from the `after_insert` hook. This is for the tenants that
already exist — dtc, aahr, ppj and the dev tenants — whose Company records were
saved long before the field mattered.

It is deliberately quiet about failure. A company with no chart of accounts is
reported, not raised: `bench migrate` runs this on every site, and a tenant
mid-provisioning or restored from an old backup must not have its migration
stopped by an account it does not need yet. The log line is what tells us.
"""

import frappe

from alvoraa_portal import expense_accounts


def execute():
	if not frappe.db.exists("DocType", "Account"):
		# A site with no ERPNext at all. Nothing to do, nothing wrong.
		return

	result = expense_accounts.backfill()

	# The other half: an Expense Claim Type needs an expense account per
	# company. ALV-178 fills it on a Company save only, so types that already
	# exist on a tenant were never covered.
	types = expense_accounts.backfill_claim_types()
	if types:
		frappe.logger().info("slice 058 claim type accounts: %s" % types)

	frappe.logger().info(
		"slice 058 employee payable account: filled=%s already_set=%s no_chart=%s"
		% (result["filled"], result["already_set"], result["no_chart_of_accounts"])
	)

	# Said on the console too, because a migrate is watched by a person and this
	# is the line that tells them whether a tenant still needs attention.
	if result["no_chart_of_accounts"]:
		print(
			"  slice 058: no chart of accounts, expense claims will still refuse: %s"
			% ", ".join(result["no_chart_of_accounts"])
		)
