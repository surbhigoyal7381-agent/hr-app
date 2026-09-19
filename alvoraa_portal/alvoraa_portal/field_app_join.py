"""Joining the field app with a code from HR (slice 013, step 3).

HR makes a code for one person (E7). The phone checks it without using it (E1),
the person can say "this is not me" (E2), and "Agree and finish" uses the code
and sets the phone up in one locked save (E3). Afterwards the phone can read the
notice again when it changes (E9), or withdraw its agreement (the user's
decision C-3). Every guest endpoint here is wrapped the way the punch is: POST
only, personal fields kept out of every log, `Cache-Control: no-store`, a code
in the body the app picks its screen from.

**The one rule that keeps the join honest: a fixed lock order.** Four rows
change in a join - the employee is read, the code is used, an old phone is
replaced, a new phone is made - and two callers can collide on the same rows: two
phones pressing Agree on one code, or HR making a new code while a phone is
joining. Every path that writes any of these rows locks them in the same order:

    Employee  ->  the person's codes  ->  the person's phones

E3 (join), E7 (make a code), E2 (this is not me), E9 (read it again), the
withdrawal and the leaver hook all follow it. Two callers that want the same
person therefore queue on the Employee row and never wait on each other in a
circle, and the one that waits re-reads the code AFTER it gets the lock, so it
sees what the winner did. The collision test in the step-3 test module runs two
joins on two database connections; exactly one wins, the other is told the code
is used. Take the locks out and it fails.

**The code is never stored.** Only its SHA-256 hash, while the code is waiting;
after that the hash is moved aside (the code record says why). The rate limits
are keyed on that hash, never on the code: Frappe writes a rate-limit key into
Redis in clear, and the step-1 probe confirmed it.
"""

import functools
import secrets

import frappe
from frappe import _
from frappe.permissions import has_permission
from frappe.rate_limiter import rate_limit
from frappe.utils import add_to_date, cint, get_datetime, get_url, now, today

from alvoraa_portal import field_app_alerts as alerts
from alvoraa_portal import field_app_errors as errors
from alvoraa_portal import field_app_notice as notice
from alvoraa_portal import field_app_settings as settings
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_app_invite.alvoraa_app_invite import (
	INVITE,
	SERVER_FLAG,
	cancel_invite,
)
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_notice_acknowledgement.alvoraa_notice_acknowledgement import (
	latest_version_for,
	record_acknowledgement,
)
from alvoraa_portal.field_app_errors import refuse, requires_field_app_plan
from alvoraa_portal.field_checkin import (
	DEVICE,
	MAX_TOKEN_CHARS,
	_device_from_token,
	_hash,
	_private_request,
	_refuse_unless_app_phone_is_eligible,
	_shift_location_for,
)
from alvoraa_portal.tenant_context import get_branding

# `secrets.token_urlsafe(32)` is 43 characters. A code shorter than this was not
# made here; one longer than the device-secret ceiling is not a code at all.
MIN_CODE_CHARS = 43

# The form fields the rate limiter reads. Their NAMES contain "key", so Frappe's
# own Error Log redaction masks their values (utils/logger.py sanitized_dict);
# the values are hashes, never the code or the secret.
CODE_KEY = "code_hash_key"
PHONE_KEY = "phone_hash_key"
HR_KEY = "hr_user_key"

HR_ROLES = {"HR Manager", "HR User", "System Manager"}

# The states an app phone can be in and still talk to the notice endpoints.
_NOTICE_STATES = ("Active", "Consent not given")


# ── rate limits keyed on a hash, never on the secret ─────────────────────────

def _limited(field, source, limit):
	"""Rate limit an endpoint on one of its arguments, hashed.

	Frappe's limiter reads `form_dict[key]` and writes it into the Redis key in
	clear (C-11a, proven in step 1). So the argument is hashed into a field of
	its own first, and that field is taken out again afterwards. `ip_based` is
	off: one phone behind a changing mobile IP is still one phone.
	"""
	def decorator(fn):
		limited = rate_limit(key=field, limit=limit, seconds=60 * 60, methods=["POST"],
		                     ip_based=False)(fn)

		@functools.wraps(fn)
		def wrapper(*args, **kwargs):
			value = kwargs.get(source)
			if source == "user":
				value = frappe.session.user
			if not value:
				refuse("INVALID_REQUEST", _("We could not read that request."))
			hashed = _hash(value)
			frappe.form_dict[field] = hashed
			try:
				return limited(*args, **kwargs)
			except frappe.RateLimitExceededError:
				# Frappe's decorator says how many, not how long. The app needs
				# the wait (section 7.1), which is what is left of the window.
				frappe.clear_messages()
				refuse("TOO_MANY_TRIES",
				       _("Too many tries. Please wait a while and try again."),
				       retry_after_s=_seconds_left(field, hashed, 60 * 60))
			finally:
				frappe.form_dict.pop(field, None)

		return wrapper

	return decorator


def _seconds_left(field, hashed, window):
	"""How long until Frappe's window for this key opens again. The key is the
	one `rate_limit` builds (rl:<cmd>:<identity>:<seconds>); step 1 saw it."""
	try:
		ttl = frappe.cache.ttl(frappe.cache.make_key(f"rl:{frappe.form_dict.cmd}:{hashed}:{window}"))
		return int(ttl) if ttl and int(ttl) > 0 else window
	except Exception:
		return window


def _refuse_bad_code(code):
	if not code or not isinstance(code, str) or len(code) < MIN_CODE_CHARS:
		refuse("QR_NOT_RECOGNISED", _("This code is not recognised. Ask HR for a new one."))
	if len(code) > MAX_TOKEN_CHARS:
		refuse("INVALID_REQUEST", _("We could not read that request."))


# ── the locks, in the one order ──────────────────────────────────────────────

_EMPLOYEE_FIELDS = ["name", "first_name", "last_name", "employee_name", "status",
                    "designation", "company"]


def _employee(name, lock=False):
	"""The employee row. `lock=True` takes the first lock of the fixed order."""
	return frappe.db.get_value("Employee", name, _EMPLOYEE_FIELDS, as_dict=True,
	                           for_update=lock)


_INVITE_FIELDS = ["name", "employee", "status", "expires_at", "used_at", "used_device", "owner"]


def _invite_by_code(code):
	"""Find the code's record by its hash - live first, then retired - without a lock."""
	hashed = _hash(code)
	row = frappe.db.get_value(INVITE, {"token_hash": hashed}, _INVITE_FIELDS, as_dict=True)
	if not row:
		row = frappe.db.get_value(INVITE, {"retired_token_hash": hashed}, _INVITE_FIELDS,
		                          as_dict=True)
	return row


def _invite_locked(name):
	"""Re-read one code's record WITH the row lock (second lock of the order)."""
	return frappe.db.get_value(INVITE, name, _INVITE_FIELDS, as_dict=True, for_update=True)


def _waiting_invites_locked(employee):
	"""Every waiting code for this person, locked (second lock of the order)."""
	Invite = frappe.qb.DocType(INVITE)
	return (
		frappe.qb.from_(Invite)
		.select(Invite.name)
		.where((Invite.employee == employee) & (Invite.status == "Waiting"))
		.orderby(Invite.name)
		.for_update()
	).run(pluck=True)


def _phones_locked(employee, old_hash=None):
	"""The phones a join has to settle, locked (third lock of the order).

	This person's live APP phones (a web phone is not stopped by an app join -
	user decision Q-3), plus whichever phone holds the secret the app is still
	carrying, whoever it belongs to (SEC-14). Ordered by name so two callers
	take the rows the same way round.
	"""
	Device = frappe.qb.DocType(DEVICE)
	own = ((Device.employee == employee)
	       & (Device.status.isin(list(_NOTICE_STATES)))
	       & (Device.join_method == "App QR code"))
	where = own | (Device.token_hash == old_hash) if old_hash else own
	return (
		frappe.qb.from_(Device)
		.select(Device.name, Device.employee, Device.status, Device.token_hash)
		.where(where)
		.orderby(Device.name)
		.for_update()
	).run(as_dict=True)


def _phone_locked(name):
	return frappe.db.get_value(DEVICE, name, "name", for_update=True)


# ── what a code's record says, and how it is refused ─────────────────────────

def _refuse_if_dead(row):
	"""Used, cancelled or run out: its own code, one time at most, never a name."""
	if row.status == "Used":
		refuse("QR_USED", _("This code has already been used."),
		       used_at=str(row.used_at or ""))
	if row.status == "Cancelled":
		refuse("QR_CANCELLED", _("This code was cancelled. Ask HR for a new one."))
	if row.status == "Ran out" or (row.expires_at and get_datetime(row.expires_at) < get_datetime(now())):
		refuse("QR_EXPIRED", _("This code has run out. Ask HR for a new one."),
		       expired_at=str(row.expires_at or ""))


def _live_invite(code, token=None, alert_if_used=False):
	"""The waiting code and its Active employee, or a refusal. Writes nothing -
	except the one case the spec names (AC-60): a waiting code for somebody who
	has left is cancelled here, so it cannot be used after the leaver hook was
	skipped by an import.

	`alert_if_used` is E1's alone: a used code scanned again is worth telling HR
	about (N3). E2 on a dead code answers as E1 would and sends nothing (AC-62) -
	the first run sent N3 from E2 too, to every HR Manager on the site."""
	_refuse_bad_code(code)
	row = _invite_by_code(code)
	if not row:
		refuse("QR_NOT_RECOGNISED", _("This code is not recognised. Ask HR for a new one."))

	if row.status == "Used" and alert_if_used:
		_alert_if_scanned_from_another_phone(row, token)

	_refuse_if_dead(row)

	emp = _employee(row.employee)
	if not emp or emp.status != "Active":
		_employee(row.employee, lock=True)
		cancel_invite(row.name, "Employee left")
		# Committed before the refusal, because the wrapper rolls back a refusal.
		frappe.db.commit()
		refuse("QR_CANCELLED", _("This code was cancelled. Ask HR for a new one."))

	return row, emp


def _alert_if_scanned_from_another_phone(row, token):
	"""N3: a used code scanned again, from a phone that is not the one that used it."""
	same_phone = False
	if token and isinstance(token, str) and 20 <= len(token) <= MAX_TOKEN_CHARS and row.used_device:
		same_phone = frappe.db.get_value(DEVICE, row.used_device, "token_hash") == _hash(token)
	if same_phone:
		return
	alerts.used_code_scanned_again(row.name)
	# The refusal that follows rolls the request back; the alert must not go with it.
	frappe.db.commit()


def _app_version():
	try:
		raw = frappe.get_request_header(errors.VERSION_HEADER)
	except Exception:
		return None
	return (raw or "").strip()[:20] or None


def _todays_punches(employee):
	return frappe.get_all(
		"Employee Checkin",
		filters={"employee": employee, "time": [">=", today() + " 00:00:00"]},
		fields=["name", "log_type", "time", "device_id"],
		order_by="time asc",
		ignore_permissions=True,
	)


def _workplace(employee):
	site = _shift_location_for(employee)
	# Name and radius only. Never the coordinates (PRIV-6).
	return {"name": site.location_name, "radius_m": cint(site.checkin_radius)} if site else None


# ── E1 · check the code, using nothing ───────────────────────────────────────

@frappe.whitelist(allow_guest=True, methods=["POST"])
@_private_request("code", "token")
@requires_field_app_plan
@_limited(CODE_KEY, "code", limit=20)
def check_code(code, token=None):
	"""Is this code live, and whose is it? Changes nothing (SEC-3).

	The answer is the least the confirm screen needs (PRIV-5): first name, the
	initial of the surname, designation, company. No employee ID, no full name,
	no email, no phone number, no date of birth, no workplace.
	"""
	errors.check_app_version()
	row, emp = _live_invite(code, token, alert_if_used=True)
	settings.refuse_unless_eligible(emp.designation)
	return {
		"first_name": emp.first_name,
		"surname_initial": (emp.last_name or "").strip()[:1],
		"designation": emp.designation,
		"company": emp.company,
		"brand_colour": get_branding()["primary_color"],
		"notice": notice.facts(),
		"min_version": errors.MIN_APP_VERSION,
	}


# ── E2 · this is not me ──────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True, methods=["POST"])
@_private_request("code")
@requires_field_app_plan
@_limited(CODE_KEY, "code", limit=5)
def refuse_code(code):
	"""The person holding the code says it is not theirs. The code is cancelled
	and HR is told (D2, SEC-7). A dead code gets the same answer E1 gives it."""
	errors.check_app_version()
	row, emp = _live_invite(code)
	settings.refuse_unless_eligible(emp.designation)

	_employee(row.employee, lock=True)
	cancel_invite(row.name, "This is not me (on a phone)")
	frappe.db.commit()

	alerts.code_refused_on_a_phone(row.name)
	return {}


# ── E3 · agree and finish: the locked join ───────────────────────────────────

@frappe.whitelist(allow_guest=True, methods=["POST"])
@_private_request("code", "token", "device_label", "platform", "notice_version", "agreed")
@requires_field_app_plan
@_limited(CODE_KEY, "code", limit=5)
def join_with_code(code, notice_version=None, device_label=None, platform=None,
                   token=None, agreed=1):
	"""Use the code and set this phone up, in one save that either all happens
	or none of it does (SEC-5, AC-64 to AC-70).

	`agreed=0` is the user's 2026-09-17 decision: a person who reaches the
	notice and chooses "Not now" still links the phone, in the "Consent not
	given" state - it holds its secret, cannot punch, and is asked again on the
	next open (E9 moves it to Active). No new code from HR is needed. Nothing
	here records a refusal, so a prompt the person merely dismissed for the
	session (C-4) leaves no trace.

	`token` is the device secret the app was already holding, if any (SEC-14).
	"""
	errors.check_app_version()
	agreed = cint(agreed)
	_refuse_bad_code(code)

	# Where is the code? No lock yet: a dead code is refused without touching a row.
	found = _invite_by_code(code)
	if not found:
		refuse("QR_NOT_RECOGNISED", _("This code is not recognised. Ask HR for a new one."))
	_refuse_if_dead(found)

	# Lock 1: the employee. Whoever else wants this person queues here.
	emp = _employee(found.employee, lock=True)
	if not emp or emp.status != "Active":
		refuse("EMPLOYEE_NOT_ACTIVE",
		       _("This employee record is no longer active. Please speak to HR."))

	# Lock 2: the code, re-read AFTER the lock. If another phone got here first
	# this is where we find out, and the answer is "already used".
	inv = _invite_locked(found.name)
	_refuse_if_dead(inv)
	if inv.status != "Waiting":
		refuse("QR_CANCELLED", _("This code was cancelled. Ask HR for a new one."))

	settings.refuse_unless_eligible(emp.designation)

	if agreed and notice_version != notice.CURRENT_VERSION:
		facts = notice.facts()
		refuse("NOTICE_CHANGED",
		       _("The notice has changed. Please read it again."),
		       version=facts["version"], rows=facts["rows"],
		       retention_days=facts["retention_days"], what_changed=facts["what_changed"])

	old_hash = _hash(token) if token and isinstance(token, str) and 20 <= len(token) <= MAX_TOKEN_CHARS else None

	# Lock 3: the phones this join settles.
	phones = _phones_locked(emp.name, old_hash)

	secret = secrets.token_urlsafe(32)
	app_version = _app_version()
	phone = frappe.get_doc({
		"doctype": DEVICE,
		"employee": emp.name,
		"employee_name": emp.employee_name,
		"status": "Active" if agreed else "Consent not given",
		"join_method": "App QR code",
		"invite": inv.name,
		"device_label": (device_label or "")[:140],
		"platform": (platform or "")[:60],
		"app_version": app_version,
		"token_hash": _hash(secret),
		"registered_on": now(),
		# Who allowed this phone: the person who made the code. Set here so the
		# controller does not write "Guest" into it.
		"activated_by": inv.owner,
	})
	phone.flags[SERVER_FLAG] = True
	phone.insert(ignore_permissions=True)

	two_people = []
	for old in phones:
		if old.status in ("Blocked", "Replaced", "Removed"):
			continue
		old_doc = frappe.get_doc(DEVICE, old.name)
		old_doc.flags[SERVER_FLAG] = True
		if old.employee == emp.name:
			# The same person on a new phone, or the same phone again (AC-72, AC-75).
			old_doc.status = "Replaced"
			old_doc.replaced_by = phone.name
			old_doc.flags["alvoraa_change_source"] = "System"
		else:
			# One phone, two people (AC-74, SEC-14): the earlier person's record
			# is removed, and HR is told after the save.
			old_doc.status = "Removed"
			old_doc.flags["alvoraa_change_source"] = "System"
			two_people.append(old.name)
		old_doc.save(ignore_permissions=True)

	used = frappe.get_doc(INVITE, inv.name)
	used.status = "Used"
	used.used_at = now()
	used.used_device = phone.name
	used.flags[SERVER_FLAG] = True
	used.save(ignore_permissions=True)

	if agreed:
		record_acknowledgement(emp.name, notice.CURRENT_VERSION, "App", device=phone.name,
		                       app_version=app_version)

	frappe.db.commit()

	alerts.code_used(inv.name)
	for old_name in two_people:
		alerts.one_phone_two_people(old_name, phone.name)

	return {
		# The only answer, anywhere, that carries the device secret.
		"token": secret,
		"status": "active" if agreed else "not_agreed",
		"first_name": emp.first_name,
		"company": emp.company,
		"workplace": _workplace(emp.name),
		"todays_checkins": _todays_punches(emp.name),
	}


# ── E9 · the notice changed: read it again ───────────────────────────────────

@frappe.whitelist(allow_guest=True, methods=["POST"])
@_private_request("token", "notice_version")
@requires_field_app_plan
@_limited(PHONE_KEY, "token", limit=5)
def acknowledge_notice(token, notice_version=None):
	"""Record that this phone's owner read the current notice (AC-94).

	Also the way a phone parked in "Consent not given" - at join, or after a
	withdrawal - becomes Active again, with no new code.
	"""
	errors.check_app_version()
	device = _device_from_token(token, allowed=_NOTICE_STATES)
	emp = _employee(device.employee)
	if not emp or emp.status != "Active":
		refuse("EMPLOYEE_NOT_ACTIVE",
		       _("This employee record is no longer active. Please speak to HR."))
	_refuse_unless_app_phone_is_eligible(device, emp.designation)

	if notice_version != notice.CURRENT_VERSION:
		facts = notice.facts()
		refuse("NOTICE_CHANGED",
		       _("The notice has changed. Please read it again."),
		       version=facts["version"], rows=facts["rows"],
		       retention_days=facts["retention_days"], what_changed=facts["what_changed"])

	_employee(device.employee, lock=True)
	_phone_locked(device.name)

	if latest_version_for(device.name) != notice.CURRENT_VERSION:
		record_acknowledgement(device.employee, notice.CURRENT_VERSION, "App",
		                       device=device.name, app_version=_app_version())

	if device.status == "Consent not given":
		device.status = "Active"
		device.flags[SERVER_FLAG] = True
		device.flags["alvoraa_change_source"] = "The employee"
		device.save(ignore_permissions=True)

	frappe.db.commit()
	return {}


# ── withdrawal · "I no longer agree" (user decision C-3) ─────────────────────

@frappe.whitelist(allow_guest=True, methods=["POST"])
@_private_request("token")
@requires_field_app_plan
@_limited(PHONE_KEY, "token", limit=5)
def withdraw_agreement(token):
	"""The person no longer agrees. The phone keeps its secret and its record,
	stops being able to punch, and is asked again next time it opens. Nothing is
	erased - that waits for counsel (C-2)."""
	errors.check_app_version()
	device = _device_from_token(token, allowed=_NOTICE_STATES)
	if device.status == "Consent not given":
		return {}

	_employee(device.employee, lock=True)
	_phone_locked(device.name)
	device.status = "Consent not given"
	device.flags[SERVER_FLAG] = True
	device.flags["alvoraa_change_source"] = "The employee"
	device.save(ignore_permissions=True)
	frappe.db.commit()
	return {}


# ── E7 · HR makes a code (desk) ──────────────────────────────────────────────

def _hr_who_may_invite(employee):
	"""An HR user whom Frappe lets read THIS employee. Server side, every time."""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please sign in."), frappe.PermissionError)
	if user != "Administrator" and not (HR_ROLES & set(frappe.get_roles(user))):
		frappe.throw(_("Only HR can invite an employee to the app."), frappe.PermissionError)
	if not employee or not isinstance(employee, str) or not frappe.db.exists("Employee", employee):
		frappe.throw(_("Choose an employee."), frappe.ValidationError)
	if not has_permission("Employee", "read", doc=employee, user=user, print_logs=False):
		frappe.throw(_("You cannot invite this employee."), frappe.PermissionError)
	return user


def _lifetime(lifetime_hours):
	"""The lifetime for this code: one of the six options, no longer than the
	organisation's setting (SEC-4). Empty means the setting itself."""
	current = settings.settings()
	if lifetime_hours in (None, ""):
		return current["lifetime_hours"]
	try:
		hours = int(lifetime_hours)
	except (TypeError, ValueError):
		hours = -1
	if hours not in settings.LIFETIME_HOURS.values() or hours > current["lifetime_hours"]:
		frappe.throw(
			_("Choose a time up to your organisation's setting of {0}.").format(
				_(current["lifetime"])),
			frappe.ValidationError)
	return hours


@frappe.whitelist(methods=["POST"])
@requires_field_app_plan
@_limited(HR_KEY, "user", limit=30)
def make_code(employee, lifetime_hours=None):
	"""Make a single-use code for one field worker (US-5).

	The answer is the only thing, anywhere, that carries the code: the browser
	draws the QR from it and forgets it when the dialog closes. Any code already
	waiting for this person is cancelled in the same save (SEC-6).
	"""
	user = _hr_who_may_invite(employee)

	# Lock 1: the employee.
	emp = _employee(employee, lock=True)
	if not emp or emp.status != "Active":
		frappe.throw(_("Only active employees can be invited."), frappe.ValidationError)
	settings.refuse_unless_eligible(emp.designation)
	hours = _lifetime(lifetime_hours)

	# Lock 2: this person's waiting codes. Cancel every one of them first.
	for name in _waiting_invites_locked(emp.name):
		cancel_invite(name, "Newer code made", cancelled_by=user)

	code = secrets.token_urlsafe(32)
	inv = frappe.get_doc({
		"doctype": INVITE,
		"employee": emp.name,
		"employee_name": emp.employee_name,
		"status": "Waiting",
		"lifetime_hours": hours,
		"expires_at": add_to_date(now(), hours=hours),
		"token_hash": _hash(code),
	})
	inv.flags[SERVER_FLAG] = True
	# As the server, in this HR user's name: `owner` is the maker, and HR has no
	# create permission on the doctype by design (section 8 of the spec).
	inv.insert(ignore_permissions=True)
	frappe.db.commit()

	return {
		"invite": inv.name,
		"link": f"{get_url('/enrol')}#t={code}",
		"expires_at": str(inv.expires_at),
		"lifetime_hours": hours,
	}
