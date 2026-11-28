"""ALV-495: a SECOND emergency contact on Employee - name, relation, phone.

Surbhi's decision of 28 November 2026. The new joiner form may ask for one more
person to ring, and **the joiner's answers must survive becoming an employee** -
her words, "when they become employees". The standard `Employee` record carries
exactly ONE set (`person_to_be_contacted`, `relation`, `emergency_phone_number`,
read from `erpnext/setup/doctype/employee/employee.json`), so without these three
columns there is nowhere for the second set to land on hire and the answers would
be erased with the joiner's row.

NOT COMPULSORY, AND THAT NEEDED NO CODE. Whether the joiner MUST answer is a
separate HR tick (`alvoraa_joiner_required_fields`). Leaving it unticked is the
whole of "optional". Nothing here decides it.

PERMLEVEL 0, AND IT TAKES A SECOND EDIT TO GET IT. Surbhi said on 28 November
2026 that the employee may edit these later from the portal, so they must end up
at level 0 - "the employee's own details", the level the FIRST emergency contact
sits at.

**Creating the field is not enough, and this is the trap.** ALV-266's rule runs
the other way round: every Employee field that is NOT on
`employee_field_rights.SELF_EDITABLE` is forced to **level 2**, in two places -
`lock_fields()` and the `Custom Field` after_insert hook. So the three names are
on `SELF_EDITABLE` as well. Without that they were created at level 2 on the
first run and the employee could not have changed their own next of kin, which
is the opposite of the decision. A test caught it; reading did not.

`hooks.py` puts this module BEFORE `employee_field_rights.apply` in both lists,
so the fields exist by the time the levels are applied.

WHY A HOOK AND NOT A PATCH. A patch never runs on a new install - Frappe marks
every patch done when the site is built - so a brand new tenant would have the
tick and the joiner form reading a column that does not exist. Same lesson as
`alternative_number.py`, `employee_field_rights.py` and `payroll_fields.py`:
one field definition, `after_migrate()`, wired into BOTH `after_migrate` and
`after_install`. `create_custom_fields` writes only what is missing, so every
run is safe and running it twice changes nothing.

THE LABELS ARE HERS, APPROVED 28 NOVEMBER 2026. Do not rename them. The
descriptions are the help text Frappe renders under each input on the Employee
form, which is the one Desk screen anybody fills these in on.

`options: "Phone"` on the number so it is dialable rather than free text, the
same as `cell_number` and as `alvoraa_alternative_number`. They sit after
`relation`, which is the last field of ERPNext's own "Emergency Contact"
section, so the second set reads directly under the first.
"""

import frappe

EMPLOYEE = "Employee"

NAME_FIELD = "alvoraa_second_person_to_be_contacted"
RELATION_FIELD = "alvoraa_second_relation"
PHONE_FIELD = "alvoraa_second_emergency_phone_number"

# In the order they appear on the form. `insert_after` chains through them so
# the three stay together whatever else a tenant has added to Employee.
SECOND_EMERGENCY_CONTACT = [
	{"fieldname": NAME_FIELD, "fieldtype": "Data",
	 "label": "Second emergency contact name", "insert_after": "relation",
	 "description": "A second person we could ring. Optional."},
	{"fieldname": RELATION_FIELD, "fieldtype": "Data",
	 "label": "Second relation", "insert_after": NAME_FIELD,
	 "description": "How this second person is related to the employee."},
	{"fieldname": PHONE_FIELD, "fieldtype": "Data", "options": "Phone",
	 "label": "Second emergency phone", "insert_after": RELATION_FIELD,
	 "description": "A number for the second contact."},
]

FIELDS = (NAME_FIELD, RELATION_FIELD, PHONE_FIELD)


def after_migrate():
	"""Guarded on the doctype existing, because install order is not ours.

	A site that installs this app before ERPNext gets nothing here and picks it
	up on the next migrate, rather than failing the install.
	"""
	if not frappe.db.exists("DocType", EMPLOYEE):
		return False

	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({EMPLOYEE: SECOND_EMERGENCY_CONTACT})
	return True
