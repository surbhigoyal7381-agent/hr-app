"""My profile: the details an employee may correct about themselves.

Slice 078, step 1, US-3 to US-6.

Two things about this module are deliberate and easy to get wrong.

**The write does not go through `doc.save()`.** The `Employee` role holds READ
ONLY on `Employee` in ERPNext - `employee.json` grants it
`{'read': 1, 'report': 1, 'print': 1, 'email': 1}` and no `write`. So an
ordinary employee cannot save their own record, and the alternative to this
module would be granting the Employee role write on the HR master, which is a
much wider change than "let somebody correct their mobile number". The write is
authorised HERE: own Active record, one field at a time, from a closed list,
intersected again with whatever the organisation ticked. `Employee.validate`
hooks do not run on a `db.set_value`, which is why nothing on either list is a
field any validate hook cares about - all six are permlevel 0.

**The Version row is written by hand.** `db.set_value` writes no history, and
"who changed my mobile number" has to have an answer. One Version row per save,
owned by the employee, naming each field's old and new value - the same shape
`alvoraa_org_structure/settings.py` already uses for an access-granting change.

What an employee may NOT do here is the more important half, and it is
`people_fields.MY_PROFILE_WRITE_FIELDS` that does it: not their job title, not
their pay, not their bank details, not their identity numbers, not their date
of birth, and nothing at all on anybody else's record. A self-service screen
must not become a way round field rights.
"""

import json

import frappe
import hrms.alvoraa_org_structure.people_fields as people_fields
from frappe import _
from frappe.utils import cstr

from alvoraa_portal import people_settings
from alvoraa_portal.employee_photo import IMAGE_FIELD, _my_employee
from alvoraa_portal.field_app_limits import SELF_KEY, _limited

EMPLOYEE = "Employee"

# Which of the six an employee may change is the organisation's choice, stored
# as one access-granting settings key. Empty - the shipped default - means the
# details card says so rather than offering nothing and looking broken.
MY_PROFILE_KEY = "alvoraa_my_profile_fields"


REQUIRED_KEY = "alvoraa_my_profile_required_fields"


def _ticked():
	"""The fields this organisation opened to its employees.

	Intersected with the allow-list HERE as well as at the setter, so a value
	written straight into `DefaultValue` by any other route produces nothing.
	That second intersection is the only half that survives a future UI.
	"""
	return people_fields.allowed(MY_PROFILE_KEY,
	                             frappe.db.get_default(MY_PROFILE_KEY))


def _ticked_and_needed():
	"""Slice 079: which of the opened fields this organisation keeps asking for.

	**A required mark here never refuses a save** (decision 3), and the reason
	is the whole point: blocking would mean somebody with no permanent address
	could never change anything on this page again - not even their own phone
	number - and their only way out is a telephone call to HR. A rule that locks
	a person out of correcting their own record is worse than an incomplete
	record.

	So `save_my_profile` below is unchanged, deliberately: it already had no
	required concept and it still has none. This function feeds the MARKS, not
	a rule.

	Required is intersected with asked at both ends, so a required mark can
	never widen what may be written (AC-105, 078-SEC-18).
	"""
	return people_fields.asked_and_required(MY_PROFILE_KEY, REQUIRED_KEY)


@frappe.whitelist()
def get_my_profile():
	"""The caller's own picture, their editable details, and their password date.

	Returns `{"no_employee": True}` rather than failing when the login is not
	linked to an Active employee. That case is an administrator opening what is
	about to be every employee's main screen, and it threw a 500 before this
	slice - `birthdays_this_month` failed for `hr@...` and the panel said
	"Something went wrong at the office."
	"""
	if frappe.session.user in ("Guest", ""):
		frappe.throw(_("Please sign in."), frappe.PermissionError)

	me = _my_employee()
	if not me:
		return {"no_employee": True}

	fields, needed = _ticked_and_needed()
	values = frappe.db.get_value(EMPLOYEE, me.name, list(fields), as_dict=True) if fields else {}
	thumb = people_fields.thumbnails_for([me.name]).get(me.name)
	last_set = frappe.db.get_value("User", frappe.session.user, "last_password_reset_date")

	return {
		"employee": me.name,
		"employee_name": me.employee_name,
		"image": me.get(IMAGE_FIELD) or None,
		"thumb": thumb or None,
		# Field names and values only. Every label, hint and sentence on this
		# screen is translated copy and lives in the front end, so there is one
		# place it can be read and one place it can be changed.
		# `needed` is a MARK, never a rule: the save below refuses nothing
		# (decision 3). The front end draws the amber chip and the standing
		# block from it, and the same word - "Needed" - is used on the joiner's
		# form, so the two screens read as one rule rather than as an
		# inconsistency.
		"fields": [{"fieldname": f, "value": cstr((values or {}).get(f) or ""),
		            "needed": f in needed}
		           for f in fields],
		"password_last_set": str(last_set) if last_set else None,
		# 078-PRIV-1. The notice has to say what this organisation has actually
		# chosen, not a fixed claim: counsel's setting (29 Oct 2026) lets the
		# employer keep photographs out of company-wide mail, and it is OFF by
		# default. A notice that overstates the audience is the one failure a
		# notice cannot have.
		"photo_in_emails": people_settings.photo_in_emails(),
	}


@frappe.whitelist(methods=["POST"])
@_limited(SELF_KEY, "user", limit=30)
def save_my_profile(values=None):
	"""Save the details this organisation opened, on the caller's OWN record.

	There is no employee argument, so there is nothing a browser can post that
	makes this write another person's record.
	"""
	me = _my_employee()
	if not me:
		frappe.throw(_("This account is not linked to an employee record. Ask "
		               "HR to link it to this account."), frappe.PermissionError)

	if isinstance(values, str):
		try:
			values = json.loads(values)
		except ValueError:
			values = None
	if not isinstance(values, dict):
		frappe.throw(_("Nothing to save."), frappe.ValidationError)

	allowed = set(_ticked())
	off_list = sorted(k for k in values if k not in allowed)
	if off_list:
		# Refused, not silently dropped. A save that quietly ignored a field is
		# how somebody comes to believe a field is editable (078-SEC-7).
		from hrms.alvoraa_hr_core.access import refuse

		refuse(_("That detail is not one you can change here. Tell HR instead."),
		       "078-SEC-7", "my_profile.save_my_profile", EMPLOYEE, me.name)

	before = frappe.db.get_value(EMPLOYEE, me.name, sorted(allowed), as_dict=True) or {}
	changed = []
	for field in sorted(allowed):
		if field not in values:
			continue
		new = cstr(values.get(field) or "").strip()
		old = cstr(before.get(field) or "")
		if new == old:
			continue
		frappe.db.set_value(EMPLOYEE, me.name, field, new)
		changed.append([field, old, new])

	if changed:
		# `db.set_value` writes no history, and "who changed my emergency
		# contact" has to have an answer. Owner is the employee, which is also
		# the brief's instrumentation for self-edits. Nobody holds create on
		# Version; Frappe writes its own the same way.
		frappe.get_doc({
			"doctype": "Version",
			"ref_doctype": EMPLOYEE,
			"docname": me.name,
			"data": frappe.as_json({"changed": changed}, indent=None,
			                       separators=(",", ":")),
		}).insert(ignore_permissions=True)
		frappe.db.commit()
		# The document name and the count. Never a value: a mobile number and a
		# home address are exactly what must not reach a log line.
		frappe.logger("alvoraa").info(
			f"my profile: {len(changed)} field(s) changed on {me.name} "
			f"by {frappe.session.user}")

	return {"saved": len(changed), "fields": [c[0] for c in changed]}
