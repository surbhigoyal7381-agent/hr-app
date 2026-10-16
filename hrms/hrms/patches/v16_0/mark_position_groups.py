"""Mark every position that has somebody reporting to it as a group.

Nothing ever set `is_group` on Alvoraa Position. It is a NestedSet, and
`NestedSet.validate_ledger` refuses to save a node that has children while
`is_group` is 0:

    Alvoraa Position <name> cannot be a leaf node as it has children

So a seat became uneditable the moment another seat was pointed at it, and the
message named a field the dialog does not show. On the PPJ tenant that was 38
of 120 positions - every manager seat in the company.

`alvoraa_position.py` now derives `is_group` on every save, which keeps it true
from here on. This repairs the rows saved before that.

Runs by itself: it only ever sets the flag to what the data already says, so
running it twice changes nothing the second time.
"""

import frappe


def execute():
	if not frappe.db.table_exists("Alvoraa Position"):
		return
	if not frappe.get_meta("Alvoraa Position").has_field("is_group"):
		return

	parents = {
		row.reports_to_position
		for row in frappe.get_all("Alvoraa Position",
		                          filters={"reports_to_position": ("is", "set")},
		                          fields=["reports_to_position"],
		                          limit_page_length=0)
		if row.reports_to_position
	}

	fixed = 0
	for name in parents:
		if frappe.db.get_value("Alvoraa Position", name, "is_group"):
			continue
		frappe.db.set_value("Alvoraa Position", name, "is_group", 1,
		                    update_modified=False)
		fixed += 1

	# A seat that has NO children but claims to be a group is the harmless
	# direction - it saves fine - so it is corrected quietly rather than
	# reported.
	cleared = 0
	for name in frappe.get_all("Alvoraa Position", filters={"is_group": 1},
	                           pluck="name", limit_page_length=0):
		if name not in parents:
			frappe.db.set_value("Alvoraa Position", name, "is_group", 0,
			                    update_modified=False)
			cleared += 1

	if fixed or cleared:
		print("  Alvoraa Position: %d marked as groups, %d cleared" % (fixed, cleared))
