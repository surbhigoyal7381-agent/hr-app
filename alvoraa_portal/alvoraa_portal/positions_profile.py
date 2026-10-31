"""The mini profile: who is this, what do they do, since when.

Slice 078, step 3. One whitelisted read, made WHEN A PROFILE IS OPENED - never
columns on the Positions table's own payload. Ten fields for 403 people would
be 4,030 personal values delivered to a browser that is showing ten of them
(078-PRIV-4), and the query-count assertion that proves it is also the privacy
gate, because a per-person read is how a payload quietly grows.

**Five things this refuses, and the order matters.**

1. Anyone who cannot open the Positions page at all - Frappe's own Read on
   `Alvoraa Position`, through `register.may_view()`. One rule for the page and
   for every endpoint behind it.
2. Anyone outside their own companies and branches, through
   `access.employee_in_scope`. A REFUSAL, not an empty profile: a reader scoped
   to one branch who asks about another branch's employee must not learn that
   such a person or such a branch exists.
3. A caller with no companies at all. `employee_in_scope` fails closed, and its
   own docstring records the trap not to re-make - do NOT write
   `dict(permitted_employee_filters(user), name=chosen_id)`, because both
   NO_EMPLOYEES and ALL_EMPLOYEES are keyed on `name`, so the caller's own
   `name` would replace the refusal. `scripts/check_scope_traps.py` fails CI on
   exactly that, so there is no new scope helper here.
4. Any field the organisation did not tick, and any field that is not on the
   closed allow-list - intersected here as well as at the setter, so a value
   written straight into `DefaultValue` by any other route produces nothing.
5. Any field whose value is a link into a doctype this reader may not read. The
   row is **absent** from the response, never blank and never the string
   "hidden": a label saying something is hidden tells the reader it exists.

**What it never carries, whatever is ticked:** pay, CTC, bank details, PAN,
Aadhaar, ESI, PF, salary mode, date of birth, personal mobile, personal email,
home address, the emergency contact, marital status, blood group, and every
field a payroll rule set names. That is `people_fields.POSITIONS_PROFILE_FIELDS`
and it is the control - not a permission level, because
`employee_field_rights.py` deliberately locked WRITE on those fields and left
READ open.
"""

import frappe
import hrms.alvoraa_org_structure.people_fields as people_fields
from frappe import _
from frappe.utils import cstr

from alvoraa_portal.field_app_limits import SELF_KEY, _limited

EMPLOYEE = "Employee"
PROFILE_KEY = "alvoraa_positions_profile_fields"
RULE = "078-SEC-2"
ENDPOINT = "positions_profile.get_positions_profile"

# The fields that are a link into another doctype. A reader who may not read
# that doctype does not get the row at all.
LINKED = {
	"department": "Department",
	"branch": "Branch",
	"company": "Company",
	"grade": "Employee Grade",
	"employment_type": "Employment Type",
	"designation": "Designation",
	"default_shift": "Shift Type",
	"reports_to": EMPLOYEE,
}


def ticked_fields():
	"""The work facts this organisation chose, intersected with the allow-list."""
	return people_fields.allowed(PROFILE_KEY, frappe.db.get_default(PROFILE_KEY))


def _refuse(employee):
	from hrms.alvoraa_hr_core.access import refuse

	# The message says nothing about whether that person or that branch exists.
	refuse(_("You cannot see that person's details."), RULE, ENDPOINT,
	       EMPLOYEE, employee)


def _guard(employee):
	"""The two checks every surface behind the Positions page shares."""
	from hrms.alvoraa_hr_core.access import employee_in_scope
	from hrms.alvoraa_org_structure.register import may_view

	if not isinstance(employee, str) or not employee.strip():
		_refuse(employee)
	employee = employee.strip()
	if not may_view():
		_refuse(employee)
	if not employee_in_scope(employee):
		_refuse(employee)
	return employee


@frappe.whitelist()
@_limited(SELF_KEY, "user", limit=240)
def get_positions_profile(employee=None):
	"""One person's short profile, for the drawer and for the seat page.

	Both surfaces call THIS, and the field list exists in this one place, so the
	two cannot drift into giving different answers to the same question.
	"""
	employee = _guard(employee)

	fields = ticked_fields()
	# `name` and the job role are not part of the ticked list: they are what the
	# reader clicked on, and the drawer opens with them even when the
	# organisation has ticked nothing at all.
	base = frappe.db.get_value(
		EMPLOYEE, employee,
		["name", "employee_name", "designation", "image", "status",
		 "relieving_date"], as_dict=True)
	if not base:
		_refuse(employee)

	values = frappe.db.get_value(EMPLOYEE, employee, list(fields),
	                             as_dict=True) if fields else {}
	rows = []
	for field in fields:
		if not _may_read_link(field):
			# ABSENT, not blank. Not "hidden".
			continue
		rows.append({"fieldname": field,
		             "value": _display(field, (values or {}).get(field))})

	out = {
		"employee": base.name,
		"employee_name": base.employee_name,
		"designation": base.designation or "",
		# The stored 512 px picture: the drawer's enlargement is the one place
		# in this product that uses it. The cards and the table draw the 48 px
		# copy instead.
		"image": base.image or None,
		"thumb": people_fields.thumbnails_for([employee]).get(employee),
		"rows": rows,
		# Only a System Manager is offered the link to the setting when nothing
		# is ticked - telling everybody else about a setting they cannot change
		# is just noise.
		"can_change_setting": "System Manager" in frappe.get_roles(),
	}

	# The one sentence a leaving date may appear in. It is never a profile row -
	# `relieving_date` is on the deny list - and the REASON for leaving is never
	# recorded here at all.
	if base.relieving_date:
		out["left_on"] = cstr(base.relieving_date)
		out["still_here"] = base.status == "Active"

	return out


def _may_read_link(field):
	"""Can this reader read the doctype behind this field?"""
	doctype = LINKED.get(field)
	if not doctype:
		return True
	try:
		return bool(frappe.has_permission(doctype, "read"))
	except Exception:
		# Fail closed. The cost of a missing row is a question to HR; the cost
		# of a wrong row is a disclosure.
		return False


def _display(field, value):
	"""What a person reads, not an id.

	`reports_to` holds an Employee id, which is meaningless on screen. Their
	NAME is shown - and only when they are inside the reader's own scope, so a
	manager in another branch does not arrive as a side effect of reading
	somebody who is in scope.
	"""
	if not value:
		return ""
	if field == "reports_to":
		from hrms.alvoraa_hr_core.access import employee_in_scope

		if not employee_in_scope(value):
			return ""
		return cstr(frappe.db.get_value(EMPLOYEE, value, "employee_name") or "")
	return cstr(value)
