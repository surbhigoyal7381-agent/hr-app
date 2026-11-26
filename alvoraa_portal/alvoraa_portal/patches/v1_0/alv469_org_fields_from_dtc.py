"""ALV-469: move DTC's agency and category into the two generic Employee fields.

Where `dtc_agency` / `dtc_employee_category` exist, copy each person's value
into `employment_agency` / `employee_category` (never over a value already
there), then hide the old field. The old fields and their data stay.
A no-op on a site without them. Safe to run twice.
"""

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

from alvoraa_portal import org_label as ol


def execute():
	if not frappe.db.exists("DocType", ol.EMPLOYEE):
		return
	# The new fields must exist before values go in; this patch runs before
	# the after_migrate hook does.
	ol.after_migrate()
	meta = frappe.get_meta(ol.EMPLOYEE)
	for new, old in ol.OLD_FIELD.items():
		if not meta.has_field(old):
			continue
		copied = 0
		for row in frappe.get_all(ol.EMPLOYEE, filters={old: ["is", "set"]}, fields=["name", old, new]):
			if not row.get(new):
				frappe.db.set_value(ol.EMPLOYEE, row.name, new, row.get(old), update_modified=False)
				copied += 1
		make_property_setter(ol.EMPLOYEE, old, "hidden", 1, "Check",
		                     validate_fields_for_doctype=False)
		print(f"  {old} -> {new}: {copied} row(s) copied, old field hidden")
	frappe.clear_cache(doctype=ol.EMPLOYEE)
