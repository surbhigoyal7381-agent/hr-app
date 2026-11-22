# Copyright (c) 2026, Alvoraa and contributors
# For license information, please see license.txt

"""Slice 088 - the monthly change notice.

When somebody else changes an employee's attendance, that employee has to be able to see
it and agree to it before their pay is locked. In the app that is the Confirm button
(slice 087). On the shop floor most of the people this matters to have no app at all, so
the same agreement happens the way it already happens in the customer's shop: a printed
page, read out if needed, and a signature or a thumb print.

This module owns that paper round:

- which changed days are waiting for which person this month;
- writing one record per print, BEFORE any content leaves the server, so there is always
  a row saying who the page was released to (088 SEC-2);
- the page itself, one A4 sheet per person;
- recording what came back - signed, with a photo of each page, or "not right" with what
  the person said - and nothing in between.

What it does NOT own: whether the change counts, whether pay is held, or what the employee
sees in the app. All of that is `punch_fix`'s, and this module reaches it through exactly
one function, `punch_fix.record_register_signature`.

**None of it appears unless the organisation has asked for it.** The switch is ALV-430's
`punch_fix.CONFIRM_SWITCH` on Company, and it ships off. Off, there is nothing to confirm,
so there is nothing to print, nothing in the list and no sentence on anybody's screen.
DTC and Grace will run with it off (Surbhi, 21 Nov 2026).
"""

import frappe

from alvoraa_portal.punch_fix import SIGNED_NOTICE, signed_column_ready

REQUEST = "Attendance Request"
NOTICE = "Alvoraa Register Notice"

#: Slice 088's own schema. The field itself is read by `punch_fix` - see
#: `punch_fix.SIGNED_NOTICE` for why the name lives there and the column is created here.
FIELDS = {
	REQUEST: [
		{"fieldname": SIGNED_NOTICE, "fieldtype": "Link", "options": NOTICE,
		 "read_only": 1, "label": "Signed On Register Notice",
		 "insert_after": "alvoraa_replaces",
		 "description": "The printed page this change was signed on, for an employee with no app. "
		                "Set only by slice 088 when HR records the signature. The signer and the "
		                "date are read from that notice, never copied here."},
	],
}


def after_migrate():
	"""The one custom field. In both hook lists, because a site built with
	`bench install-app` never runs a migrate (the reason `punch_fix.after_migrate` gives)."""
	if not frappe.db.exists("DocType", REQUEST):
		return False
	if not frappe.db.exists("DocType", NOTICE):
		# The Link's target has to exist first, or the field is created pointing at nothing.
		return False
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields(FIELDS)
	_index()
	return True


def _index():
	"""One index on (employee, month): every read in this module asks "this person, this
	month", and without it the notice list scans the table once per person in the list
	(088 OPS-21)."""
	try:
		frappe.db.add_index(NOTICE, ["employee", "month"], index_name="employee_month")
	except Exception:
		# An index that cannot be added is a slow list, not a broken one, and a migrate
		# must not fail on it.
		pass


def columns_ready():
	"""False on a site whose image is newer than its migrate. The readers then behave as
	they did before 088 rather than failing on an unknown column."""
	return signed_column_ready() and frappe.db.exists("DocType", NOTICE)
