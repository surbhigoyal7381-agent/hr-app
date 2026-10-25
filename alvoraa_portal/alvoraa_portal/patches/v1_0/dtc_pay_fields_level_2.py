"""ALV-215 (slice 063 SEC-17): three DTC Employee fields that set pay go to level 2.

The fields a pay rule set names are locked by employee_field_rights.apply().
These three are not named by DTC's rule set, but they describe pay or decide
which agency is told about a person's days (PRIV-7), so HR alone may change them.

A no-op on every site without these fields, which is every site but DTC.
Runs before after_migrate, which adds the level-2 permission rows.
"""

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

FIELDS = ("dtc_pay_type", "dtc_employee_category", "dtc_agency")


def execute():
	if not frappe.db.exists("DocType", "Employee"):
		return
	meta = frappe.get_meta("Employee")
	for fieldname in FIELDS:
		df = meta.get_field(fieldname)
		if df and not df.permlevel:
			make_property_setter("Employee", fieldname, "permlevel", 2, "Int",
			                     validate_fields_for_doctype=False)
	frappe.clear_cache(doctype="Employee")
