"""Slice 080: the one field "Alternative number", on Employee.

Surbhi's decision of 2 November 2026. A number the company hands out so
colleagues can reach somebody - not a number the person picks. **HR fills it
in; the employee cannot.** That half is not here: it is the field's permission
level, `alvoraa_alternative_number` on `employee_field_rights.LEVEL_2`, which
is what actually refuses the employee's own write. This module only creates the
column.

WHY A HOOK AND NOT A PATCH. A patch never runs on a new install - Frappe marks
every patch done when the site is built - so a brand new tenant would have the
tick and the directory column reading a column that does not exist. The same
lesson is written out in `employee_field_rights.py` and in
`payroll_fields.py`, and this follows the pattern those two set: one field
definition, `after_migrate()`, wired into BOTH `after_migrate` and
`after_install`. `create_custom_fields` writes only what is missing, so it is
safe on every run.

THE LABEL AND THE HELP TEXT ARE HERS, WORD FOR WORD. "Alternative number" - she
rejected "Work phone". Do not rename it. The description is the help text
Frappe renders under the input on the Employee form, which is the one screen
anybody fills this in on, and the right moment to be told who can see it.

`options: "Phone"` so it is a dialable number rather than free text, the same
as `cell_number`. It sits after `company_email` because the two are the same
kind of thing: work contact the company publishes.
"""

import frappe

EMPLOYEE = "Employee"
FIELD = "alvoraa_alternative_number"

ALTERNATIVE_NUMBER = [
	{"fieldname": FIELD, "fieldtype": "Data", "options": "Phone",
	 "label": "Alternative number", "insert_after": "company_email",
	 "description": "A number colleagues may use to reach this person. "
	                "Everyone in the company can see it."},
]


def after_migrate():
	"""Guarded on the doctype existing, because install order is not ours.

	A site that installs this app before ERPNext gets nothing here and picks it
	up on the next migrate, rather than failing the install.
	"""
	if not frappe.db.exists("DocType", EMPLOYEE):
		return False

	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({EMPLOYEE: ALTERNATIVE_NUMBER})
	return True
