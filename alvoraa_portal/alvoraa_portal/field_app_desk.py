"""What HR sees on the Employee record about the field app (slice 013, step 5).

US-16: one section on the Employee form, "Field attendance app", that says in
one line where this person stands - not joined, code waiting, joined, blocked,
not a field worker, app switched off, not in the plan - and shows only the
actions that state allows. Under it, the person's phones and the history of
their codes. E12 is the one call behind that section.

Three rules, each with a test:

  * **HR only, and only for a person this HR user may read.** The role AND
    Frappe's own read permission on that Employee, server side, every call.
    An HR user limited to one company gets nothing about another company's
    employee (SEC-13, AC-109, US-27).
  * **Nothing the phone must never see, and nothing that watches people.** No
    secret, no hash, no code, no coordinates. No "last seen", no "online now":
    the only time on a phone row is its last saved PUNCH (PRIV-9, AC-107).
  * **Bounded.** Two list reads for one employee, capped, plus a handful of
    name lookups. Nothing loops over a query per row (AC-109).

The words on the screen are the form script's (`public/js/employee_field_app.js`).
This file sends facts and a state; it does not decide wording. The state is
worked out here, not in the browser, so that a screen change can never widen
what an HR user is offered.
"""

import frappe
from frappe import _
from frappe.permissions import has_permission
from frappe.utils import get_datetime, get_fullname, get_url, getdate, now

from alvoraa_portal import field_app_settings as settings
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_app_invite.alvoraa_app_invite import INVITE
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_field_device.alvoraa_field_device import (
	APP_JOIN_METHODS,
	JOIN_PASSWORD,
)
from alvoraa_portal.field_app_errors import desk_request, requires_field_app_plan
from alvoraa_portal.field_checkin import DEVICE

HR_ROLES = {"HR Manager", "HR User", "System Manager"}

# The Employee form gets one section and one HTML box; the script draws into it.
F_SECTION = "alvoraa_field_app_section"
F_HTML = "alvoraa_field_app_html"

# How many phones and codes the section reads for one person. AC-109's design
# volume is 10 phones and 30 codes; the cap keeps a pathological record cheap.
ROW_LIMIT = 50

# What a phone's status is called on the screen (English keys; the script
# translates). "Stopped" is not a stored state: it is an Active app phone that
# the switch or the designation list is refusing right now (section 5.1).
STATUS_WORDS = {
	"Active": "Active",
	"Pending": "Waiting for HR",
	"Blocked": "Blocked",
	"Replaced": "Replaced",
	"Removed": "Removed",
	"Consent not given": "Not agreed yet",
	"Signed out": "Signed out",
}

# A phone in one of these states still holds a live secret, so HR may block it.
BLOCKABLE = ("Active", "Pending", "Consent not given")

# Why a phone was blocked - the Select on the phone record, pinned by a test.
BLOCK_REASONS = (
	"Phone lost or stolen",
	"Has a new phone",
	"Someone else was using it",
	"Left the company",
	# ALV-128: set by the server when the login that signed a phone in is
	# disabled, or is unlinked from the employee record (SEC-28). A changed
	# password is not a block: the phone is signed out (26 Sep 2026).
	"Login disabled",
	"Login unlinked",
	"Other",
)


# ── who may act ──────────────────────────────────────────────────────────────

def hr_who_may_act(employee, refusal):
	"""An HR user whom Frappe lets read THIS employee. Server side, every time.

	Shared by E7 (make a code), E10 (cancel), E11 (block) and E12 (the section).
	`refusal` is the sentence for a signed-in user who is not HR. The last check
	is the one that scopes HR to their own companies: delete it and the
	"store HR user cannot see or touch another company's employee" tests in
	the step-3 and step-5 modules fail.
	"""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please sign in."), frappe.PermissionError)
	if user != "Administrator" and not (HR_ROLES & set(frappe.get_roles(user))):
		frappe.throw(refusal, frappe.PermissionError)
	if not employee or not isinstance(employee, str) or not frappe.db.exists("Employee", employee):
		frappe.throw(_("Choose an employee."), frappe.ValidationError)
	if not has_permission("Employee", "read", doc=employee, user=user, print_logs=False):
		frappe.throw(_("You cannot see this employee."), frappe.PermissionError)
	return user


# ── the pieces of the answer ─────────────────────────────────────────────────

_PHONE_FIELDS = [
	"name", "device_label", "platform", "app_version", "join_method", "status",
	"registered_on", "last_seen", "checkin_count", "block_reason", "status_changed_on",
	"status_changed_by", "status_change_source", "activated_by", "invite", "replaced_by",
	"creation",
]

_CODE_FIELDS = [
	"name", "owner", "creation", "lifetime_hours", "status", "expires_at", "used_at",
	"used_device", "cancel_reason", "cancelled_by", "cancelled_at",
]


def _names_of(users):
	"""Full names for a handful of users. `get_fullname` caches per request."""
	return {u: get_fullname(u) for u in users if u and u != "Guest"}


def _workplaces(employee, dates):
	"""The workplace a punch on each of these dates was measured against: the
	Shift Assignment with a location that covered the date. One query for the
	assignments, one for the location names; matched here."""
	dates = [d for d in dates if d]
	if not dates:
		return {}
	rows = frappe.get_all(
		"Shift Assignment",
		filters={"employee": employee, "docstatus": 1, "shift_location": ["is", "set"]},
		fields=["shift_location", "start_date", "end_date"],
		order_by="start_date desc",
		limit=200,
	)
	if not rows:
		return {}
	names = frappe.get_all("Shift Location",
	                       filters={"name": ["in", list({r.shift_location for r in rows})]},
	                       fields=["name", "location_name"])
	label = {n.name: n.location_name for n in names}
	out = {}
	for d in dates:
		day = getdate(d)
		for r in rows:
			if r.start_date and r.start_date <= day and (not r.end_date or r.end_date >= day):
				out[str(d)] = label.get(r.shift_location) or ""
				break
	return out


def _code_outcome(code, at):
	if code.status == "Used":
		return "used"
	if code.status == "Cancelled":
		return {
			"By HR": "cancelled_by_hr",
			"This is not me (on a phone)": "not_me",
			"Newer code made": "newer_code",
			"Employee left": "employee_left",
		}.get(code.cancel_reason, "cancelled_by_hr")
	if code.status == "Ran out" or (code.expires_at and get_datetime(code.expires_at) < at):
		# The daily job (step 6) marks these; until it runs the section says so itself.
		return "ran_out"
	return "waiting"


def _phone_rows(employee, phones, codes_by_name, current, listed, names):
	places = _workplaces(employee, [p.last_seen for p in phones if p.last_seen])
	out = []
	for p in phones:
		app_phone = p.join_method in APP_JOIN_METHODS
		# What would refuse this Active app phone right now. Both answer to the
		# master switch; a code phone also to the designation list. The two
		# "ways in" switches stop new joins only (ALV-128, 26 Sep decision).
		if p.join_method == JOIN_PASSWORD:
			allowed = current["enabled"]
		else:
			allowed = current["enabled"] and listed
		stopped = app_phone and p.status == "Active" and not allowed
		inv = codes_by_name.get(p.invite) if p.invite else None
		out.append({
			"name": p.name,
			"device_label": p.device_label or "",
			"platform": p.platform or "",
			"app_version": p.app_version or "",
			"join_method": p.join_method or "Web check-in page",
			"status": p.status,
			"status_word": "Stopped" if stopped else STATUS_WORDS.get(p.status, p.status),
			"stopped": stopped,
			"registered_on": str(p.registered_on or p.creation or ""),
			"last_seen": str(p.last_seen or ""),
			"last_place": places.get(str(p.last_seen), "") if p.last_seen else "",
			"checkin_count": int(p.checkin_count or 0),
			"block_reason": p.block_reason or "",
			"status_changed_on": str(p.status_changed_on or ""),
			"status_changed_by": p.status_changed_by or "",
			"status_changed_by_name": names.get(p.status_changed_by, ""),
			"status_change_source": p.status_change_source or "",
			"activated_by": p.activated_by or "",
			"activated_by_name": names.get(p.activated_by, ""),
			"invite": p.invite or "",
			"invite_made_by": (inv.owner if inv else "") or "",
			"invite_made_by_name": names.get(inv.owner, "") if inv else "",
			"invite_made_at": str(inv.creation) if inv else "",
			"replaced_by": p.replaced_by or "",
			"can_block": p.status in BLOCKABLE,
			# AC-106: a web-page phone of somebody who is not (or no longer) a field
			# worker keeps working. The pill says so.
			"not_field_worker": (not app_phone) and p.status == "Active" and not listed,
		})
	return out


def _code_rows(codes, phones_by_name, names, at):
	out = []
	for c in codes:
		used = phones_by_name.get(c.used_device) if c.used_device else None
		out.append({
			"name": c.name,
			"made_at": str(c.creation or ""),
			"made_by": c.owner or "",
			"made_by_name": names.get(c.owner, ""),
			"lifetime_hours": int(c.lifetime_hours or 0),
			"status": c.status,
			"outcome": _code_outcome(c, at),
			"expires_at": str(c.expires_at or ""),
			"used_at": str(c.used_at or ""),
			"used_device": c.used_device or "",
			"used_device_label": (used.device_label if used else "") or "",
			"cancel_reason": c.cancel_reason or "",
			"cancelled_by": c.cancelled_by or "",
			"cancelled_by_name": names.get(c.cancelled_by, ""),
			"cancelled_at": str(c.cancelled_at or ""),
		})
	return out


def _state(emp, current, listed, waiting, phones):
	"""One word for where this person stands (01b section 9.1), in the order
	the design lists them. Worked out on the server so the screen can only
	ever offer less than the server allows, never more."""
	if emp.status != "Active":
		return "not_active"
	if not current["enabled"]:
		return "app_off"
	# A person outside the designation list who signed in with their password
	# is still a joined person (ALV-128), not "not a field worker".
	# A phone signed out after a password change counts too: the person can
	# sign in again at any time, with no code from HR.
	signed_in = any(p["join_method"] == JOIN_PASSWORD
	                and p["status"] in ("Active", "Consent not given", "Signed out")
	                for p in phones)
	if not listed and not signed_in:
		return "not_field"
	if waiting:
		return "code_waiting"
	if any(p["status"] == "Active" for p in phones):
		return "joined"
	if any(p["status"] == "Consent not given" for p in phones):
		return "not_agreed"
	if any(p["status"] == "Pending" for p in phones):
		return "web_pending"
	if phones and phones[0]["status"] == "Blocked":
		return "blocked"
	return "no_phone"


def _line_phone(state, phones):
	"""The phone the status line talks about, if any."""
	want = {
		"joined": "Active", "not_agreed": "Consent not given", "web_pending": "Pending",
		"blocked": "Blocked",
	}.get(state)
	if want:
		return next((p for p in phones if p["status"] == want), None)
	if state == "no_phone" and phones and phones[0]["status"] in ("Removed", "Signed out"):
		return phones[0]
	return None


# ── E12 · the section's data ─────────────────────────────────────────────────

@frappe.whitelist()
@desk_request
@requires_field_app_plan
def employee_app_section(employee):
	"""Everything the "Field attendance app" section shows for one employee.

	Read-only. Two capped list reads (phones, codes), one read of the settings,
	one grouped read of shift assignments for the "last punch" place, and a
	full-name lookup per distinct HR user named. Nothing here writes.
	"""
	user = hr_who_may_act(employee, _("Only HR can see the field attendance app section."))
	emp = frappe.db.get_value(
		"Employee", employee,
		["name", "first_name", "employee_name", "status", "designation", "company"],
		as_dict=True)
	current = settings.settings()
	listed = bool(emp.designation) and emp.designation in current["designations"]
	at = get_datetime(now())

	phones = frappe.get_all(DEVICE, filters={"employee": employee}, fields=_PHONE_FIELDS,
	                        order_by="registered_on desc, creation desc", limit=ROW_LIMIT)
	codes = frappe.get_all(INVITE, filters={"employee": employee}, fields=_CODE_FIELDS,
	                       order_by="creation desc", limit=ROW_LIMIT)
	codes_by_name = {c.name: c for c in codes}
	phones_by_name = {p.name: p for p in phones}
	names = _names_of(
		{p.status_changed_by for p in phones} | {p.activated_by for p in phones}
		| {c.owner for c in codes} | {c.cancelled_by for c in codes})

	phone_rows = _phone_rows(employee, phones, codes_by_name, current, listed, names)
	code_rows = _code_rows(codes, phones_by_name, names, at)
	waiting = next((c for c in code_rows if c["outcome"] == "waiting"), None)
	state = _state(emp, current, listed, waiting, phone_rows)

	lifetimes = [{"hours": h, "label": label} for label, h in settings.LIFETIME_HOURS.items()
	             if h <= current["lifetime_hours"]]
	return {
		"me": user,
		"employee": {
			"name": emp.name,
			"first_name": emp.first_name or emp.employee_name,
			"employee_name": emp.employee_name,
			"status": emp.status,
			"designation": emp.designation or "",
			"company": emp.company or "",
		},
		"app": {
			"enabled": bool(current["enabled"]),
			"listed": listed,
			"lifetime_hours": current["lifetime_hours"],
			"lifetime_label": current["lifetime"],
			"lifetimes": lifetimes,
		},
		"state": state,
		"can_invite": state in ("no_phone", "code_waiting", "joined", "not_agreed",
		                        "web_pending", "blocked"),
		"waiting_code": waiting,
		"phone": _line_phone(state, phone_rows),
		"phones": phone_rows,
		"codes": code_rows,
		"block_reasons": list(BLOCK_REASONS),
		"checkin_url": get_url("/checkin"),
		"server_time": str(at),
	}


# ── install: the section on the Employee form ────────────────────────────────

def after_migrate():
	"""Add the section and the HTML box to Employee, on migrate AND on install
	(a site built with `bench install-app` never runs a migrate). Safe to run
	twice: `create_custom_fields` updates in place. Two layout fields, no data
	field - nothing about a person is stored here."""
	if not frappe.db.exists("DocType", "Employee"):
		return False

	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({
		"Employee": [
			{
				"fieldname": F_SECTION,
				"fieldtype": "Section Break",
				"label": "Field attendance app",
				# The last field of ERPNext's "Attendance & Leaves" tab, so the
				# section lands in that tab (AC-102).
				"insert_after": "holiday_list",
			},
			{
				"fieldname": F_HTML,
				"fieldtype": "HTML",
				"label": "Field attendance app",
				"insert_after": F_SECTION,
			},
		]
	}, ignore_validate=True)
	return True
