"""HR is told, not left to look (slice 013, US-19 / SEC-13).

Four things about a joining code are worth a desk-bell notification the same
day: the code was used; somebody pressed "This is not me" on it; a used code was
scanned again from a phone that is not the one that used it; a phone that held
one person's secret joined as another person. Each becomes a Frappe
`Notification Log` row - the desk bell, and an email only where that person has
email on in their own notification settings - for the people named in section
10 of the spec.

Three rules, each with a test:

  * **Nothing secret in a message.** No code, no hash, no device secret, no
    photo, no coordinates, no block reason. The employee's name, the phone's
    model and a time are what HR needs to act; nothing else is in here.
  * **After the save, never inside it.** The join or the cancel is committed
    first. A notification that cannot be written (Redis down, a bad user row) is
    logged as a place in the code and the join stands (AC-122). In production
    the rows are written by a job on the `short` queue, after the commit; in a
    test run they are written at once, which is the framework's own rule for
    `enqueue`.
  * **Only people who may read the employee.** The HR Managers who get an
    alert are the enabled ones whom Frappe's own permission check lets read
    that Employee - so an HR Manager limited to another company is not told
    (AC-117).
"""

import frappe
from frappe import _
from frappe.permissions import has_permission
from frappe.utils import add_to_date, cint, format_datetime, formatdate, get_fullname, now

INVITE = "Alvoraa App Invite"
DEVICE = "Alvoraa Field Device"

# One "scanned again" alert per code per hour, or a phone left on a table would
# ring the bell every time somebody picked it up (AC-118).
SCANNED_AGAIN_QUIET_HOURS = 1


# ── who ──────────────────────────────────────────────────────────────────────

def _email_of(user):
	if not user or user == "Guest":
		return None
	row = frappe.db.get_value("User", user, ["email", "enabled"], as_dict=True)
	return row.email if row and row.enabled and row.email else None


def hr_managers_who_can_read(*employees):
	"""Enabled HR Managers whom Frappe lets read EVERY one of these employees.

	A loop of permission checks, bounded by how many HR Managers a tenant has -
	a handful - not by headcount.
	"""
	users = frappe.get_all("Has Role", filters={"role": "HR Manager", "parenttype": "User"},
	                       pluck="parent", distinct=True)
	out = []
	for user in users:
		if user in ("Administrator", "Guest"):
			continue
		if all(has_permission("Employee", "read", doc=e, user=user, print_logs=False)
		       for e in employees):
			email = _email_of(user)
			if email:
				out.append(email)
	return sorted(set(out))


# ── the four events ──────────────────────────────────────────────────────────

def code_used(invite_name):
	"""N1 - to the HR person who made the code."""
	inv = frappe.db.get_value(INVITE, invite_name,
	                          ["owner", "employee", "employee_name", "used_at", "used_device",
	                           "creation"], as_dict=True)
	if not inv:
		return
	to = _email_of(inv.owner)
	if not to:
		return
	first = _first_name(inv.employee)
	model = frappe.db.get_value(DEVICE, inv.used_device, "device_label") or _("a phone")
	_send(
		[to],
		_("{0} joined the Alvora app").format(inv.employee_name),
		_("{0} set up {1} at {2} with the code you made on {3}. If this was not {4}, "
		  "block the phone from their employee record.").format(
			inv.employee_name, model, format_datetime(inv.used_at), formatdate(inv.creation),
			first),
		INVITE, invite_name,
	)


def code_refused_on_a_phone(invite_name):
	"""N2 - to the maker and to every HR Manager who can read the employee."""
	inv = frappe.db.get_value(INVITE, invite_name, ["owner", "employee", "employee_name"],
	                          as_dict=True)
	if not inv:
		return
	to = set(hr_managers_who_can_read(inv.employee))
	maker = _email_of(inv.owner)
	if maker:
		to.add(maker)
	first = _first_name(inv.employee)
	_send(
		sorted(to),
		_("App code for {0} was refused on a phone").format(inv.employee_name),
		_("Someone pressed \"This is not me\" on the app code for {0}. The code is "
		  "cancelled. Make a new code if {1} still needs one, and give it only to {1}.").format(
			inv.employee_name, first),
		INVITE, invite_name,
	)


def used_code_scanned_again(invite_name):
	"""N3 - a used code scanned from a phone that is not the one that used it."""
	inv = frappe.db.get_value(INVITE, invite_name,
	                          ["employee", "employee_name", "used_at", "used_device"], as_dict=True)
	if not inv:
		return
	subject = _("Used app code for {0} was scanned again").format(inv.employee_name)
	if frappe.db.exists("Notification Log", {
		"document_type": INVITE, "document_name": invite_name, "subject": subject,
		"creation": [">", add_to_date(now(), hours=-SCANNED_AGAIN_QUIET_HOURS)],
	}):
		return
	first = _first_name(inv.employee)
	model = frappe.db.get_value(DEVICE, inv.used_device, "device_label") or _("a phone")
	_send(
		hr_managers_who_can_read(inv.employee),
		subject,
		_("The app code for {0} was used at {1} on {2}, and has now been scanned on "
		  "another phone. If {3} did not set up {2}, block that phone and make a new "
		  "code.").format(inv.employee_name, format_datetime(inv.used_at), model, first),
		INVITE, invite_name,
	)


def one_phone_two_people(old_device_name, new_device_name):
	"""N4 - to HR Managers who can read BOTH employees."""
	old = frappe.db.get_value(DEVICE, old_device_name, ["employee", "employee_name"], as_dict=True)
	new = frappe.db.get_value(DEVICE, new_device_name, ["employee", "employee_name"], as_dict=True)
	if not old or not new:
		return
	_send(
		hr_managers_who_can_read(old.employee, new.employee),
		_("One phone was used by two employees"),
		_("A phone set up for {0} was just set up for {1}. {0}'s phone has been "
		  "removed. Check with both of them.").format(old.employee_name, new.employee_name),
		DEVICE, new_device_name,
	)


def too_many_bad_codes(n):
	"""N5 (step 6) - to every HR Manager of the tenant, at most once an hour.

	`n` is how many code checks were refused in the last clock hour. The
	threshold and the counting are in `field_app_housekeeping`; this only says
	it. No code, no address, no name: nothing in a refused code check is about
	a person, and the message must not make it so (AC-121).
	"""
	subject = _("Many app codes that do not work were tried")
	if frappe.db.exists("Notification Log", {
		"document_type": "HR Settings", "document_name": "HR Settings", "subject": subject,
		"creation": [">", add_to_date(now(), hours=-1)],
	}):
		return
	_send(
		hr_managers_who_can_read(),
		subject,
		_("{0} app codes that do not work were tried in the last hour. This may be "
		  "someone guessing codes. No phone was set up with them.").format(cint(n)),
		"HR Settings", "HR Settings",
	)


# ── the mechanism ────────────────────────────────────────────────────────────

def _first_name(employee):
	return frappe.db.get_value("Employee", employee, "first_name") or get_fullname(employee)


def _send(emails, subject, body, doctype, name):
	"""Queue the Notification Log rows. Never raises: the save it follows stands."""
	emails = [e for e in emails if e]
	if not emails:
		return
	try:
		frappe.enqueue(
			"frappe.desk.doctype.notification_log.notification_log.make_notification_logs",
			queue="short",
			doc={
				"type": "Alert",
				"subject": subject,
				"email_content": body,
				"document_type": doctype,
				"document_name": name,
				# Guest for a phone's call, the HR user for a desk one. Frappe's
				# email path reads it, and its own callers always set it.
				"from_user": frappe.session.user,
			},
			users=emails,
			now=frappe.in_test,
			enqueue_after_commit=not frappe.in_test,
		)
	except Exception as exc:
		# The row this is about is named, and the place in the code; nobody's
		# name or secret goes in (`_code_places` carries no values).
		from alvoraa_portal.field_checkin import _code_places
		place = _code_places(exc)
		frappe.log_error("Field app alerts",
		                 f"could not queue a field app alert for {doctype} {name}: {place}")
