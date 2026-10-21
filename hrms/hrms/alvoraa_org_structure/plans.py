"""Replacement plans (slice 065): who may see one, and how it is erased.

A replacement plan is HR's private note that the person in a seat may need
replacing. It is a judgement about a named person, so three things matter
more than anything else here:

  * ONE GATE. Every door - desk lists, the form, REST, link search, counts and
    the Positions page - asks the same question, here (SEC-1).
  * NO COPIES. No change history, comments, assignments, shares, tags or
    attachments on a plan (PRIV-1, SEC-3).
  * A REAL ERASE. One erase path that leaves nothing behind, and a daily job
    that erases what has lapsed or whose person has left (PRIV-2, PRIV-3).

This is the only module that reads the plan table. A test fails if the
doctype's name appears anywhere else outside its own folder, `register.py`,
`hooks.py` and tests (SEC-7).

Nothing here logs a person's name, an employee id, a seat, an assignment or
the note. Log lines carry the plan's random name only (PRIV-4).
"""

import frappe
from frappe import _
from frappe.utils import nowdate

DOCTYPE = "Replacement Plan"

# A plan lasts this long from its last confirmation (Surbhi, 21 Oct 2026).
LIFE_DAYS = 90

# The optional note, counted on the server (PM-Q4 default).
NOTE_MAX = 200

# Set on the document by the erase function only. Any delete without it is
# refused, because Frappe's ordinary delete keeps a copy in Deleted Document.
ERASE_FLAG = "replacement_plan_erase"


def _refuse(message, endpoint):
	"""A refusal with no id in the log line: a plan's log must not point at a
	person, a seat or an assignment (PRIV-4)."""
	from hrms.alvoraa_hr_core.access import refuse

	refuse(message, "SEC-5", endpoint, DOCTYPE, None)


def _my_employees(user=None):
	"""(ids, any active) for the Employee records linked to this login."""
	rows = frappe.get_all(
		"Employee", filters={"user_id": user or frappe.session.user}, fields=["name", "status"]
	)
	return {r.name for r in rows}, any(r.status == "Active" for r in rows)


def check_assignment(assignment):
	"""The seat assignment a plan may be set or kept on: started, not ended,
	its person Active, its seat not Closed and inside the caller's scope, and
	not the caller's own (SEC-5; decision 9)."""
	from hrms.alvoraa_org_structure import register

	a = frappe.db.get_value(
		register.ASSIGNMENT, assignment, ["employee", "position", "from_date", "to_date"], as_dict=True
	)
	if not a:
		frappe.throw(_("That person is no longer in this seat. Reload Positions and try again."))
	today = nowdate()
	if str(a.from_date) > today or (a.to_date and str(a.to_date) < today):
		frappe.throw(_("That person is not in this seat today. Reload Positions and try again."))
	if frappe.db.get_value("Employee", a.employee, "status") != "Active":
		frappe.throw(_("That person is no longer an active employee, so no plan is needed."))
	seat = frappe.db.get_value(register.POSITION, a.position, ["company", "branch", "status"], as_dict=True)
	if not seat or seat.status == "Closed":
		frappe.throw(_("This seat is closed, so no plan can be kept on it."))

	companies, branches = register._scope()
	if seat.company not in companies or (branches is not None and (seat.branch or "") not in branches):
		_refuse(_("This seat is outside the companies and branches you look after."), "plans.check_assignment")
	if a.employee in _my_employees()[0]:
		_refuse(_("Nobody can set or keep a replacement plan on their own seat."), "plans.check_assignment")
