"""Joining the field app with a code from HR (slice 013, step 3).

HR makes a code for one person (E7). The phone checks it without using it (E1),
the person can say "this is not me" (E2), and "Agree and finish" uses the code
and sets the phone up in one locked save (E3). Afterwards the phone can read the
notice again when it changes (E9), or withdraw its agreement (the user's
decision C-3). Every guest endpoint here is wrapped the way the punch is: POST
only, personal fields kept out of every log, `Cache-Control: no-store`, a code
in the body the app picks its screen from.

ALV-128 adds a second way in, at the end of this file: an employee with a login
signs in with their work email and password (and a one-time code when
two-factor sign-in is on). The password is checked by Frappe's own login code,
so lockout and two-factor behave exactly as on the website; after that the
phone is set up by the same `_set_up_phone` the joining code uses.

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
Redis in clear, and the step-1 probe confirmed it. The limiter itself lives in
`field_app_limits` since step 4, because the punch uses it too.
"""

import secrets

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, get_datetime, get_url, now

from alvoraa_portal import field_app_alerts as alerts
from alvoraa_portal import field_app_errors as errors
from alvoraa_portal import field_app_notice as notice
from alvoraa_portal import field_app_settings as settings
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_app_invite.alvoraa_app_invite import (
	INVITE,
	SERVER_FLAG,
	cancel_invite,
)
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_field_device.alvoraa_field_device import (
	APP_JOIN_METHODS,
	JOIN_PASSWORD,
	JOIN_QR,
)
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_notice_acknowledgement.alvoraa_notice_acknowledgement import (
	latest_version_for,
	record_acknowledgement,
)
from alvoraa_portal.field_app_desk import desk_request, hr_who_may_act
from alvoraa_portal.field_app_errors import refuse, requires_field_app_plan
from alvoraa_portal.field_app_limits import (  # re-exported: the step-3 tests name the keys here
	CODE_KEY,
	HR_KEY,
	OTP_KEY,
	PHONE_KEY,
	WINDOW_SECONDS,
	_hash,
	_limited,
	_limited_by_address,
)
from alvoraa_portal.field_checkin import (
	DEVICE,
	MAX_TOKEN_CHARS,
	_device_from_token,
	_private_request,
	_refuse_unless_app_phone_is_eligible,
	_shift_location_for,
	_todays_punches,
)
from alvoraa_portal.field_checkin import _workplace as workplace
from alvoraa_portal.tenant_context import get_branding

# `secrets.token_urlsafe(32)` is 43 characters. A code shorter than this was not
# made here; one longer than the device-secret ceiling is not a code at all.
MIN_CODE_CHARS = 43

HR_ROLES = {"HR Manager", "HR User", "System Manager"}

# The states an app phone can be in and still talk to the notice endpoints.
_NOTICE_STATES = ("Active", "Consent not given")


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
	# Either app way in (ALV-128): a phone that signed in with a password
	# replaces one that joined with a code, and the other way round - one live
	# app phone per person, whichever way it came.
	own = ((Device.employee == employee)
	       & (Device.status.isin(list(_NOTICE_STATES)))
	       & (Device.join_method.isin(list(APP_JOIN_METHODS))))
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
	return errors.sent_app_version()


def _workplace(employee):
	return workplace(_shift_location_for(employee))


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
	settings.refuse_unless_code_join_on()
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
	settings.refuse_unless_code_join_on()

	if agreed and notice_version != notice.CURRENT_VERSION:
		facts = notice.facts()
		refuse("NOTICE_CHANGED",
		       _("The notice has changed. Please read it again."),
		       version=facts["version"], rows=facts["rows"],
		       retention_days=facts["retention_days"], what_changed=facts["what_changed"])

	# Lock 3: the phones this join settles, and the new phone (shared with the
	# password sign-in, so the two ways in can never drift apart).
	phone, secret, two_people, _replaced = _set_up_phone(
		emp, JOIN_QR, agreed, device_label, platform, token,
		# Who allowed this phone: the person who made the code. Set here so the
		# controller does not write "Guest" into it.
		activated_by=inv.owner, invite=inv.name)

	used = frappe.get_doc(INVITE, inv.name)
	used.status = "Used"
	used.used_at = now()
	used.used_device = phone.name
	used.flags[SERVER_FLAG] = True
	used.save(ignore_permissions=True)

	_record_agreement(emp, phone, agreed)
	frappe.db.commit()

	alerts.code_used(inv.name)
	_tell_hr_one_phone_two_people(two_people, phone)
	return _joined_answer(emp, secret, agreed)


# ── the part of a join both ways in share (ALV-128) ──────────────────────────
#
# Moved out of join_with_code unchanged, so that the joining code and the
# password sign-in set a phone up, replace the old one, and handle "this
# phone's old secret belongs to somebody else" in exactly one place. The
# caller holds lock 1 (the Employee) already; this takes lock 3.

def _set_up_phone(emp, join_method, agreed, device_label, platform, token,
                  activated_by, invite=None):
	"""Make the new phone and settle the old ones.

	Returns (phone, secret, two_people, replaced): `replaced` are this same
	person's earlier phones that the new one replaced (the password sign-in
	emails the person about them, SEC-27).

	`token` is the secret the app was already carrying, if any (SEC-14).
	Nothing is committed here; the caller commits once, after its own writes.
	"""
	old_hash = _hash(token) if token and isinstance(token, str) and 20 <= len(token) <= MAX_TOKEN_CHARS else None

	# Lock 3: the phones this join settles.
	phones = _phones_locked(emp.name, old_hash)

	secret = secrets.token_urlsafe(32)
	phone = frappe.get_doc({
		"doctype": DEVICE,
		"employee": emp.name,
		"employee_name": emp.employee_name,
		"status": "Active" if agreed else "Consent not given",
		"join_method": join_method,
		"invite": invite,
		"device_label": (device_label or "")[:140] if isinstance(device_label, str) else "",
		"platform": (platform or "")[:60] if isinstance(platform, str) else "",
		"app_version": _app_version(),
		"token_hash": _hash(secret),
		"registered_on": now(),
		"activated_by": activated_by,
	})
	phone.flags[SERVER_FLAG] = True
	phone.insert(ignore_permissions=True)

	two_people, replaced = [], []
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
			replaced.append(old.name)
		else:
			# One phone, two people (AC-74, SEC-14): the earlier person's record
			# is removed, and HR is told after the save.
			old_doc.status = "Removed"
			old_doc.flags["alvoraa_change_source"] = "System"
			two_people.append(old.name)
		old_doc.save(ignore_permissions=True)

	return phone, secret, two_people, replaced


def _record_agreement(emp, phone, agreed):
	if agreed:
		record_acknowledgement(emp.name, notice.CURRENT_VERSION, "App", device=phone.name,
		                       app_version=phone.app_version)


def _tell_hr_one_phone_two_people(two_people, phone):
	for old_name in two_people:
		alerts.one_phone_two_people(old_name, phone.name)


def _joined_answer(emp, secret, agreed):
	return {
		# The only answers, anywhere, that carry the device secret: this one,
		# given once by join_with_code or by the password sign-in.
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
	"""An HR user whom Frappe lets read THIS employee. Server side, every time.
	The check itself lives in `field_app_desk.hr_who_may_act` since step 5, so
	E7, E10, E11 and E12 ask the same question the same way."""
	return hr_who_may_act(employee, _("Only HR can invite an employee to the app."))


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
@desk_request
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
	settings.refuse_unless_code_join_on(_("Joining codes are switched off in HR Settings."))
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
		"made_at": str(inv.creation),
	}


# ── E10 · HR cancels a waiting code (desk) ───────────────────────────────────

@frappe.whitelist(methods=["POST"])
@desk_request
@requires_field_app_plan
@_limited(HR_KEY, "user", limit=30)
def cancel_code(invite):
	"""Cancel one waiting code from the Employee record (US-7, SEC-7).

	The code goes to Cancelled "By HR", with who and when, and its hash is
	retired in the same save (the code record's rules). E1 with that code then
	answers `QR_CANCELLED`. Safe to call twice: a code that is no longer
	waiting is left exactly as it is.

	The same lock order as every other writer of these rows: the employee,
	then the code. The HR user must be able to read the employee the code
	belongs to; a code that does not exist gets the same sentence, so the
	endpoint cannot be used to find out which code names exist.
	"""
	row = None
	if invite and isinstance(invite, str) and len(invite) <= 140:
		row = frappe.db.get_value(INVITE, invite, ["name", "employee", "status"], as_dict=True)
	if not row:
		frappe.throw(_("You cannot cancel this code."), frappe.PermissionError)
	user = hr_who_may_act(row.employee, _("Only HR can cancel an app code."))

	_employee(row.employee, lock=True)
	cancel_invite(row.name, "By HR", cancelled_by=user)
	frappe.db.commit()
	return {}


# ── ALV-128 · signing in with email and password ─────────────────────────────
#
# For any active employee whose Employee record is linked to a login (the
# user's decision, 25 Sep 2026): no designation list, no code from HR. The
# master switch and the password switch on HR Settings still apply, and so
# does the plan.
#
# Four promises, each with a test in test_field_app_password_signin_128.py:
#
#   * **Frappe checks the password, not us.** `LoginManager.authenticate` -
#     the website's own function - so the failed-attempt lockout, disabled
#     logins, and the "user pass login disabled" system setting behave exactly
#     as on the website. Two-factor sign-in, when on for the person, uses
#     Frappe's own `authenticate_for_2factor` and `confirm_otp_token`.
#   * **No web session.** `LoginManager.__init__` is never run, so no session
#     row, no `sid` cookie; the phone is proven from then on by the device
#     secret, like every other app phone.
#   * **The password never lands anywhere.** It is taken out of the request's
#     form fields before anything else runs (`_private_request`), it is not
#     cached for the two-factor step (Frappe's website caches it; we hand
#     Frappe an empty string instead), and the app never stores it.
#   * **One answer for "no such email" and "wrong password".** SIGN_IN_FAILED,
#     word for word, so the app cannot be used to find out who works here.

MAX_EMAIL_CHARS = 140   # a User's name is at most 140 characters

# Everything these two endpoints are sent, kept out of every log.
_SIGNIN_PRIVATE = ("email", "password", "otp", "tmp_id", "token", "device_label",
                   "platform", "notice_version", "agreed")

# Frappe's two-factor step keeps these beside the one-time id in Redis.
_SECOND_STEP_KEYS = ("_usr", "_pwd", "_otp_secret", "_token")


def _refuse_sign_in_failed():
	frappe.clear_messages()
	refuse("SIGN_IN_FAILED",
	       _("That email and password do not match. Check them and try again. If you "
	         "forgot your password, reset it on your company's Alvoraa website."))


def _address_is_locked():
	"""Is it Frappe's per-address lock, rather than the account's, that refused?
	Frappe keeps one failure counter per login and one per caller address, and
	raises the same exception for both."""
	from frappe.auth import get_login_attempt_tracker

	ip = getattr(frappe.local, "request_ip", None)
	if not ip:
		return False
	return not get_login_attempt_tracker(ip, raise_locked_exception=False).is_user_allowed()


def _refuse_locked():
	frappe.clear_messages()
	wait = cint(frappe.db.get_single_value("System Settings", "allow_login_after_fail")) or 60
	if _address_is_locked():
		# Not "your account": the lock is on the network, and saying otherwise
		# would tell a stranger on the same Wi-Fi something about this login.
		refuse("NETWORK_LOCKED",
		       _("Too many sign-in attempts from this network. Try again later."),
		       retry_after_s=wait)
	refuse("ACCOUNT_LOCKED",
	       _("Too many wrong tries. Your account is locked for a while. Try again in "
	         "{0} minutes, or reset your password on the website.").format(max(1, wait // 60)),
	       retry_after_s=wait)


# SEC-29: ten tries an hour per ACCOUNT - the login Frappe finds for what was
# typed, not the typed text. MariaDB compares names without case or accents, so
# an address typed in capitals, or with an "ä" for an "a", finds the same login;
# a limit keyed on the text would give every spelling its own ten. Typed text that finds no
# login is counted on itself. The key starts "alvoraa_fa" like the app's other
# counters and holds a hash, never the address.
ACCOUNT_LIMIT = 10
_ACCOUNT_KEY = "alvoraa_fa_signin_account:{0}"


def _count_account_try(email):
	from frappe.core.doctype.user.user import User

	found = User.find_by_credentials(email, "", validate_password=False)
	account = found["name"] if found else email.strip().lower()
	key = frappe.cache.make_key(_ACCOUNT_KEY.format(_hash(account)))
	tries = frappe.cache.incrby(key, 1)
	if tries == 1:
		frappe.cache.expire(key, WINDOW_SECONDS)
	if tries > ACCOUNT_LIMIT:
		ttl = frappe.cache.ttl(key)
		refuse("TOO_MANY_TRIES", _("Too many tries. Please wait a while and try again."),
		       retry_after_s=int(ttl) if ttl and int(ttl) > 0 else WINDOW_SECONDS)


def _login_manager(user=None):
	"""Frappe's LoginManager WITHOUT its constructor. The constructor is what
	makes a session and sets cookies; `authenticate` and the checks after it
	need none of that."""
	from frappe.auth import LoginManager

	lm = LoginManager.__new__(LoginManager)
	lm.user = user
	lm.info = None
	lm.full_name = None
	lm.user_type = None
	lm.resume = False
	return lm


def _check_password(email, password):
	"""The website's own password check. Returns the LoginManager, or refuses."""
	from frappe.auth import MAX_PASSWORD_SIZE

	if cint(frappe.get_system_settings("disable_user_pass_login")):
		# The site allows no password logins at all (Frappe's own switch).
		refuse("PASSWORD_SIGNIN_OFF",
		       _("Signing in to the app with an email and password is switched off. "
		         "Ask HR for a joining code."))
	if (not isinstance(email, str) or not isinstance(password, str)
			or not email.strip() or not password
			or len(email) > MAX_EMAIL_CHARS or len(password) > MAX_PASSWORD_SIZE):
		_refuse_sign_in_failed()

	_count_account_try(email.strip())
	lm = _login_manager()
	try:
		lm.authenticate(user=email.strip(), pwd=password)
	except frappe.SecurityException:
		_refuse_locked()
	except frappe.AuthenticationError:
		# Unknown email, wrong password, disabled login: Frappe has already
		# counted the attempt and written its own authentication log.
		_refuse_sign_in_failed()
	finally:
		# `fail()` writes Frappe's own words ("Invalid login credentials", "User
		# disabled or missing") into the answer. They differ by case - which is
		# exactly what must not reach the phone.
		frappe.local.response.pop("message", None)

	if lm.force_user_to_reset_password():
		refuse("PASSWORD_EXPIRED",
		       _("Your password has expired. Change it on your company's Alvoraa "
		         "website, then sign in here with the new one."))
	return lm


def _checks_after_sign_in(lm):
	"""What Frappe's `post_login` checks, without making a session: the login's
	allowed addresses and allowed hours."""
	from frappe.auth import validate_ip_address

	try:
		if getattr(frappe.local, "request", None) is not None:
			validate_ip_address(lm.user)
		lm.validate_hour()
	except frappe.AuthenticationError:
		frappe.clear_messages()
		refuse("SIGN_IN_NOT_ALLOWED",
		       _("Your login cannot be used from here or at this time. Please speak to HR."))


def _employee_for_login(user):
	"""The Active employee whose record names this login, or a clear refusal."""
	rows = frappe.get_all("Employee", filters={"user_id": user, "status": "Active"},
	                      pluck="name", order_by="creation asc", limit=1)
	if rows:
		return rows[0]
	if frappe.db.exists("Employee", {"user_id": user}):
		refuse("EMPLOYEE_NOT_ACTIVE",
		       _("This employee record is no longer active. Please speak to HR."))
	refuse("NO_EMPLOYEE_RECORD",
	       _("Your login is not linked to an employee record, so this app cannot mark "
	         "attendance for you. Ask HR to link your employee record to your login."))


def _join_signed_in(user, notice_version, device_label, platform, token, agreed):
	"""Set this phone up for the person who just signed in - the same locked
	save the joining code makes, minus the code. Lock 1 (the Employee), then
	lock 3 (the phones); there is no code to take lock 2 on."""
	agreed = cint(agreed)
	name = _employee_for_login(user)

	emp = _employee(name, lock=True)
	if not emp or emp.status != "Active":
		refuse("EMPLOYEE_NOT_ACTIVE",
		       _("This employee record is no longer active. Please speak to HR."))

	if agreed and notice_version != notice.CURRENT_VERSION:
		facts = notice.facts()
		refuse("NOTICE_CHANGED",
		       _("The notice has changed. Please read it again."),
		       version=facts["version"], rows=facts["rows"],
		       retention_days=facts["retention_days"], what_changed=facts["what_changed"])

	# Who allowed this phone: the person themselves, by their own password. It is
	# also how the User hook finds this phone when the login is disabled.
	phone, secret, two_people, replaced = _set_up_phone(
		emp, JOIN_PASSWORD, agreed, device_label, platform, token, activated_by=user)
	_record_agreement(emp, phone, agreed)
	_log_sign_in(user, phone)
	frappe.db.commit()

	# After the commit, and never able to undo it: the phone is set up whether
	# or not the email can be queued (round-two review, P2).
	if replaced:
		_tell_the_person_a_new_phone_signed_in(user, phone, replaced)
	_tell_hr_one_phone_two_people(two_people, phone)
	answer = _joined_answer(emp, secret, agreed)
	# The app shows the notice next (a phone that has not agreed yet cannot
	# punch); these are the words, from the same place the code join reads them.
	answer["notice"] = notice.facts()
	answer["min_version"] = errors.MIN_APP_VERSION
	return answer


def _log_sign_in(user, phone):
	"""SEC-31: one Activity Log row per app sign-in, like the website's "Login"
	row, with the caller's address (Activity Log fills it in) and the phone's
	model. Written straight to the log - no session is made."""
	from frappe.core.doctype.activity_log.activity_log import add_authentication_log

	label = phone.device_label or _("unknown model")
	add_authentication_log(_("Phone app sign-in ({0}, {1})").format(label, phone.name), user,
	                       operation="Login", status="Success")


def _tell_the_person_a_new_phone_signed_in(user, phone, replaced):
	"""SEC-27: a sign-in that replaced this person's earlier phone. If it was not
	them, the email is how they find out. Sent through Frappe's email queue, and
	noted on the new phone's timeline. Not sent for a first-ever phone.

	Runs AFTER the sign-in is committed and never raises: a tenant with no
	outgoing Email Account makes `frappe.sendmail` raise at once, and that must
	not undo a sign-in that already succeeded (round-two review, P2). A failure
	is logged by the phone record's name only, and the timeline says so.
	Addressed to the User's `email` field, not its name (the two can differ).
	"""
	emailed = False
	try:
		address = frappe.db.get_value("User", user, "email")
		if address:
			frappe.sendmail(
				recipients=[address],
				subject=_("A new phone signed in to the Alvoraa app as you"),
				message=_("A new phone signed in to the Alvoraa attendance app as you, and your "
				          "earlier phone stopped working. If this was not you, tell HR and change "
				          "your password."),
				reference_doctype=DEVICE,
				reference_name=phone.name,
				delayed=True,
			)
			emailed = True
	except Exception:
		# The sign-in is already committed; drop only whatever half an email left.
		frappe.db.rollback()
		frappe.clear_messages()
		# Named arguments, and a message given: without one, Frappe logs the
		# traceback WITH its local variables, which would include the address.
		frappe.log_error(title="Field app sign-in email",
		                 message=f"new-phone email could not be queued for field device {phone.name}")
	try:
		note = (_("Replaced the earlier phone {0} of the same person. The person was emailed.")
		        if emailed else
		        _("Replaced the earlier phone {0} of the same person. The email to the person "
		          "could not be sent."))
		phone.add_comment("Info", note.format(", ".join(replaced)))
		frappe.db.commit()
	except Exception:
		frappe.db.rollback()
		frappe.log_error(title="Field app sign-in email",
		                 message=f"new-phone note could not be written on field device {phone.name}")


# The second step's own marker (review P1, 26 Sep 2026). Frappe writes the
# two-factor keys (`<tmp_id>_usr`, `_otp_secret`, ...) into Redis with NO site
# prefix, and one Redis serves every tenant on the bench - so an id made on one
# tenant could be confirmed on another. This key goes through `make_key`, which
# puts this site's database name in front, and the second step takes the user
# from it and from nothing else. It also means an id made by the website's own
# login is never accepted here.
_MARKER_KEY = "alvoraa_app_2fa:{0}"
_MARKER_SECONDS = 300


def _start_second_step(user):
	"""Two-factor sign-in is on for this person: send the one-time code the
	way the website does, and tell the app to ask for it."""
	from frappe.twofactor import authenticate_for_2factor

	# Frappe caches `form_dict["pwd"]` beside the one-time id, because its
	# website re-checks the password on the second step. We do not re-check
	# it - the second step proves the one-time id and the code - so Frappe is
	# handed an empty string and the real password is never cached.
	frappe.form_dict["pwd"] = ""
	try:
		authenticate_for_2factor(user)
	finally:
		frappe.form_dict.pop("pwd", None)

	verification = frappe.local.response.pop("verification", None) or {}
	tmp_id = frappe.local.response.pop("tmp_id", None)
	frappe.cache.set_value(_MARKER_KEY.format(tmp_id), user, expires_in_sec=_MARKER_SECONDS)
	return {
		"status": "otp_required",
		"tmp_id": tmp_id,
		"method": verification.get("method") or "",
		"prompt": verification.get("prompt") or "",
	}


def _forget_second_step(tmp_id):
	"""The one-time id works once. Frappe's own flow leaves it to run out."""
	frappe.cache.delete(*[tmp_id + suffix for suffix in _SECOND_STEP_KEYS])
	frappe.cache.delete_value(_MARKER_KEY.format(tmp_id))


# 500 an hour per caller address (the user's decision, 26 Sep 2026): high
# enough for a depot signing everybody in on day one from one Wi-Fi, low enough
# to stop one machine trying passwords against every address in turn. The
# per-account limit (SEC-29) and Frappe's lockout still count every try.
ADDRESS_LIMIT = 500


@frappe.whitelist(allow_guest=True, methods=["POST"])
@_private_request(*_SIGNIN_PRIVATE)
@requires_field_app_plan
@_limited_by_address(limit=ADDRESS_LIMIT)
def sign_in_with_password(email=None, password=None, notice_version=None, device_label=None,
                          platform=None, token=None, agreed=0):
	"""Sign in with a work email and password, and set this phone up (ALV-128).

	Answers one of:
	  * the joined answer - `token` (the device secret, given once), `status`
	    "active" or "not_agreed", the person's first name and company, today's
	    punches, and the notice to show;
	  * `{"status": "otp_required", "tmp_id", "method", "prompt"}` when
	    two-factor sign-in is on - the app then calls `confirm_sign_in_code`;
	  * a refusal with its code.

	The app sends `agreed=0` and shows the notice after this answer; the phone
	sits in "Consent not given" until `acknowledge_notice` moves it to Active,
	exactly as a code-joined phone does after "Not now". That way the password
	is sent once and never held while the person reads.

	Rate limits: 10 an hour per account (the login Frappe finds, SEC-29) and
	500 an hour per caller address, on top of Frappe's own lockout.
	"""
	errors.check_app_version()
	settings.refuse_unless_password_signin_on()
	lm = _check_password(email, password)
	if should_run_2fa(lm.user):
		return _start_second_step(lm.user)
	_checks_after_sign_in(lm)
	return _join_signed_in(lm.user, notice_version, device_label, platform, token, agreed)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@_private_request(*_SIGNIN_PRIVATE)
@requires_field_app_plan
@_limited_by_address(limit=ADDRESS_LIMIT)
@_limited(OTP_KEY, "tmp_id", limit=5)
def confirm_sign_in_code(tmp_id=None, otp=None, notice_version=None, device_label=None,
                         platform=None, token=None, agreed=0):
	"""The second step of a two-factor sign-in (ALV-128): the one-time id from
	`sign_in_with_password` and the code the person was sent. Checked by
	Frappe's `confirm_otp_token`, which counts a wrong code against the login's
	lockout like the website does. The id works once."""
	from frappe.twofactor import ExpiredLoginException, confirm_otp_token

	errors.check_app_version()
	settings.refuse_unless_password_signin_on()

	if not isinstance(tmp_id, str) or not tmp_id or len(tmp_id) > 32:
		refuse("OTP_EXPIRED", _("Your sign-in has timed out. Please sign in again."))
	# The user comes from THIS site's marker only - never from Frappe's
	# unprefixed `<tmp_id>_usr`, which another tenant could have written.
	user = frappe.cache.get_value(_MARKER_KEY.format(tmp_id), use_local_cache=False)
	if not user or not isinstance(user, str):
		refuse("OTP_EXPIRED", _("Your sign-in has timed out. Please sign in again."))
	if not isinstance(otp, str) or not otp.strip() or len(otp) > 12:
		refuse("OTP_WRONG", _("That code is not right. Check it and try again."))

	lm = _login_manager(user)
	try:
		confirmed = confirm_otp_token(lm, otp=otp.strip(), tmp_id=tmp_id)
	except ExpiredLoginException:
		frappe.clear_messages()
		refuse("OTP_EXPIRED", _("Your sign-in has timed out. Please sign in again."))
	except frappe.SecurityException:
		_refuse_locked()
	except frappe.AuthenticationError:
		frappe.clear_messages()
		refuse("OTP_WRONG", _("That code is not right. Check it and try again."))
	finally:
		frappe.local.response.pop("message", None)
	if not confirmed:
		refuse("OTP_WRONG", _("That code is not right. Check it and try again."))

	_forget_second_step(tmp_id)
	# The login could have been disabled in the minutes between the two steps.
	if not cint(frappe.db.get_value("User", user, "enabled")):
		_refuse_sign_in_failed()
	_checks_after_sign_in(lm)
	return _join_signed_in(user, notice_version, device_label, platform, token, agreed)


def should_run_2fa(user):
	"""Frappe's own question, imported late so a test can change the answer."""
	from frappe.twofactor import should_run_2fa as frappe_should_run_2fa

	return frappe_should_run_2fa(user)
