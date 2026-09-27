"""Field check-in: attendance from a phone, for people who have no desk.

Drivers, guards and anyone else who works away from a branch. They open a web
app added to their phone's home screen, take a photo, and press Check In. The
punch lands in Frappe HR's own `Employee Checkin`, beside the punches the
reception machine writes, so there is one attendance story per person.

Three things make this different from the portal's `do_checkin`:

1. **There is no login.** A driver has no email address and no password. The
   phone registers once against an employee ID and is handed a secret it keeps.
   Every later call proves itself with that secret. An employee ID on its own
   is not enough to punch for somebody.
2. **A photo is the evidence.** Stored as a PRIVATE file on the check-in. It is
   never written into `/public/files`, where anybody holding the URL could read
   it, and it never reaches the error log.
3. **The GPS fix carries its accuracy**, and a vague fix is refused rather than
   quietly treated as if it were exact. A phone that says "somewhere within
   500 m" cannot answer "are you at the store".

Geofencing is NOT implemented here. Frappe HR already enforces it in
`Employee Checkin.validate_distance_from_shift_location`, driven by the
`checkin_radius` on the Shift Location attached to the employee's Shift
Assignment. This module catches that refusal and rewrites it into words a
driver can act on, with the real distance in it. The rule stays Frappe's.
"""

import datetime
import functools
import hashlib
import hmac
import secrets
import traceback

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import (
	add_to_date,
	cint,
	convert_utc_to_system_timezone,
	flt,
	get_datetime,
	now,
	time_diff_in_seconds,
	today,
)

from alvoraa_portal import field_app_errors as errors
from alvoraa_portal import field_app_housekeeping as housekeeping
from alvoraa_portal import field_app_notice as notice
from alvoraa_portal import field_app_settings as settings
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_app_invite.alvoraa_app_invite import (
	INVITE,
	cancel_invite,
)
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_field_device import (
	alvoraa_field_device as device_rules,
)
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_notice_acknowledgement.alvoraa_notice_acknowledgement import (
	latest_version_for,
	record_acknowledgement,
)

# ── the pieces that used to live in this file ────────────────────────────────
#
# This module was 1,126 lines and slice 013 roughly doubles it, so the parts
# that are not about the punch or the phone's identity now live beside it. The
# names are imported straight back, because `hooks.py`, the web page and the
# browser all call them at `alvoraa_portal.field_checkin.<name>` and a path in
# a hook or a browser URL is a promise. Nothing moved changed.
from alvoraa_portal.field_app_access import (  # re-exported: hooks.py and the web page still name these here
	_HR_ROLES,
	ACCESS_LOG,
	_viewer,
	checkin_has_permission,
	checkin_query_conditions,
	log_photo_view,
)
from alvoraa_portal.field_app_errors import refuse, requires_field_app_plan
from alvoraa_portal.field_app_limits import (  # re-exported: _hash is named here by the join and the tests
	PHONE_KEY,
	_hash,
	_limited,
)
from alvoraa_portal.field_app_photos import (  # re-exported: hooks.py and the web page still name these here
	DEFAULT_RETENTION_DAYS,
	JPEG_MAGIC,
	MAX_PHOTO_B64_CHARS,
	MAX_PHOTO_BYTES,
	SETTING_RETENTION_DAYS,
	_setting,
	photo_retention_days,
	purge_old_checkin_photos,
)
from alvoraa_portal.field_app_photos import attach_photo as _attach_photo
from alvoraa_portal.field_app_pwa import (  # re-exported: the browser's URLs still name these here
	_SERVICE_WORKER,
	_brand,
	_darker,
	app_icon,
	manifest,
	service_worker,
)

DEVICE = "Alvoraa Field Device"

# The version of the notice shown at setup. Change it whenever the notice's
# meaning changes. A consent record that says only "agreed" cannot answer "agreed
# to what?" once the words have moved on; one that names the version can.
#
# The words themselves now live in `field_app_notice`, as data, one entry per
# version. This name is kept because the web page, the two stored fields and
# slice 014's tests all call it that, and a name is not worth a migration.
CONSENT_VERSION = notice.CURRENT_VERSION

# A phone that cannot place itself better than this cannot be used to answer
# "were you at the branch". 50 m is a decent fix outdoors (user decision, step
# 4; it was 100); a reading worse than this usually means the phone fell back
# to the mobile network rather than GPS. Applies to every phone, web page
# included - the physics is the same. The sentence the web page matches on is
# unchanged; only the number moved.
MAX_ACCURACY_METRES = 50.0

# Two punches of the same kind inside this window are one punch, retried.
# Measured on server time. The query behind it filters on `employee` (indexed)
# and then `log_type` and `time` (`time` is NOT indexed in Frappe HR - see the
# impact analysis, Finding D); at ~52 rows per person per month that is fine,
# and no index is added to a standard hrms doctype.
DUPLICATE_WINDOW_SECONDS = 60

# The smallest check-in radius a Shift Location may be saved with. Twice the
# accuracy a phone is trusted to (above): a 30 m fence checked with a 50 m fix
# refuses people who are genuinely standing at the door, and attendance is pay.
# Refused when the radius is SAVED, never at punch time (user decision, step 4),
# so an existing smaller radius keeps working until HR next edits it. 0 still
# means "no radius" - Frappe HR's own rule - and is allowed.
MIN_RADIUS_M = 100

DEFAULT_RADIUS_M = 100


# ── keeping photos, positions and names out of the logs (slice 014) ──────────
#
# Frappe writes a failed request into its logs in two ways, and neither knows
# what a photo or a coordinate is:
#
#   * Every Error Log row - including the ones our own `frappe.log_error` calls
#     write - carries the request's fields in `metadata`. Frappe hides only
#     fields whose NAME contains password, secret, token, key or pwd. `photo`,
#     `latitude` and `longitude` went in whole.
#   * An exception that reaches Frappe's request handler is written with the
#     local variables of every frame - on a 5xx always, and in developer mode
#     (dev) on every refusal too. Frappe's own `frappe.call` frame holds the
#     request arguments, so catching and re-raising cannot help: the new
#     exception climbs through that frame and prints them all the same.
#
# So the wrapper below does two things. It takes the personal fields out of the
# request as soon as the endpoint has them, and it never lets an exception leave
# the endpoint: a refusal is answered exactly as Frappe would answer it (same
# status, same sentence), and anything unexpected is rolled back, written to the
# Error Log as a place in the code with no values, and answered with a plain 500.

# What an operator sees for a crash: where it happened, never with what.
_SERVER_ERROR_TITLE = "Field check-in: unexpected error"

# Taken out of EVERY wrapped request, whatever the endpoint names (ALV-128).
# Frappe already masks field names containing "password" or "pwd" in an Error
# Log row, but not "otp", and a local variable in a crash dump is not masked
# at all. Nothing here needs them from form_dict: the endpoints are handed
# their arguments directly.
_NEVER_KEPT = ("password", "pwd", "otp")


def _code_places(exc):
	"""The exception's class and file:line:function for each frame. No values.

	`str(exc)` is left out on purpose: a database error can quote the value it
	choked on.
	"""
	places = [type(exc).__name__]
	for frame in traceback.extract_tb(exc.__traceback__):
		path = frame.filename.replace("\\", "/")
		if "/apps/" in path:
			path = path.split("/apps/", 1)[1]
		places.append(f"{path}:{frame.lineno} in {frame.name}")
	return "\n".join(places)


def _private_request(*fields):
	"""Keep personal data out of every log Frappe writes for this endpoint.

	Put it directly under `@frappe.whitelist(...)`, so it also covers the plan
	gate and the rate limit beneath it.
	"""
	def decorator(fn):
		@functools.wraps(fn)
		def wrapper(*args, **kwargs):
			# The arguments were already handed to us; the copy in form_dict is
			# only read by logging from here on.
			for field in (*fields, *_NEVER_KEPT):
				frappe.form_dict.pop(field, None)
			_never_cache()
			try:
				out = fn(*args, **kwargs)
				# The day's numbers (step 6, US-22): endpoint, outcome, app
				# version - never a value from the request. Counting never
				# raises and never changes the answer.
				housekeeping.record_outcome(fn.__name__, "ok", errors.sent_app_version())
				return out
			except Exception as exc:
				status = getattr(exc, "http_status_code", None) or 500
				frappe.db.rollback()
				if status < 500:
					# A refusal: frappe.throw has already queued its sentence, and
					# the page matches on that sentence. Answer as Frappe would,
					# plus the code the app picks its screen from (slice 013).
					code, values = errors.code_and_values(exc, status)
					frappe.local.response["http_status_code"] = status
					frappe.local.response["exc_type"] = errors.exc_type_for(exc, status)
					frappe.local.response["code"] = code
					frappe.local.response["values"] = values
					housekeeping.record_outcome(fn.__name__, code, errors.sent_app_version())
					return None
				_log_server_error(fn.__name__, exc)
				housekeeping.record_outcome(fn.__name__, "SERVER_ERROR", errors.sent_app_version())
				frappe.clear_messages()
				frappe.msgprint(_("Something went wrong on our side. Please try again "
				                  "in a minute."))
				frappe.local.response["http_status_code"] = 500
				frappe.local.response["exc_type"] = "ServerError"
				frappe.local.response["code"] = "SERVER_ERROR"
				frappe.local.response["values"] = {}
				return None

		wrapper.__alvoraa_private_request__ = fields    # so tests can see it
		return wrapper

	return decorator


def _never_cache():
	"""No answer from a device endpoint may sit in a cache. AC-28.

	Frappe already defaults API answers to no-store, which means this line
	changes nothing today - and that is exactly why it is written down. A
	default can move in a framework upgrade; a punch refusal served from a proxy
	cache would tell somebody they are checked in when they are not.
	"""
	try:
		frappe.local.response_headers["Cache-Control"] = "no-store"
	except Exception:
		# No request at all: a test, a console, a background job.
		pass


def _log_server_error(endpoint, exc):
	"""One Error Log row an operator can find, with nothing personal in it."""
	message = f"endpoint: {endpoint}\n{_code_places(exc)}"
	try:
		frappe.log_error(title=f"{_SERVER_ERROR_TITLE} in {endpoint}", message=message)
	except Exception:
		# The database may be the thing that failed. The log file still gets the
		# same words; this logger does not add the request's fields.
		frappe.logger("alvoraa_portal.field_checkin").error(
			f"{_SERVER_ERROR_TITLE} in {endpoint} (Error Log not written)\n{message}")


# ── the device secret ────────────────────────────────────────────────────────
#
# `_hash` lives in `field_app_limits` since step 4 (the limiter needs it and
# this file imports the limiter). It is imported above under its old name.

# The longest a device secret can honestly be. `secrets.token_urlsafe(32)` is 43
# characters; anything past this is not one of ours and is refused before it is
# hashed, so a very long string cannot be used to make the server work (AC-30).
MAX_TOKEN_CHARS = 128

# Only an Active phone may do anything. Every other state gets its own code, so
# the app can show the right screen and so a blocked phone is never told why
# (PRIV-13). "Consent not given" is the state a phone sits in when it is linked
# but the person has not agreed to the notice yet; it holds a live secret and
# may not punch.
_REFUSAL_FOR_STATUS = {
	"Blocked": ("DEVICE_BLOCKED",
	            "This phone has been blocked. Please speak to HR."),
	"Replaced": ("DEVICE_REPLACED",
	             "You joined on another phone. Use that one, or ask HR for a new code."),
	"Removed": ("DEVICE_REMOVED",
	            "This phone is no longer linked. Ask HR for a new code to set it up again."),
	"Consent not given": ("CONSENT_REQUIRED",
	                      "Please read the notice and agree before you check in."),
	# ALV-128, 26 Sep 2026: a password phone whose login's password changed. Not
	# a block - the person signs in again with the new password.
	"Signed out": ("PASSWORD_CHANGED_SIGN_IN_AGAIN",
	               "Your password was changed. Please sign in again."),
}

# Which field carries the time each final state was reached, for the one value
# the app is allowed to show. A blocked phone gets NOTHING - not a time, not a
# reason - because the reason is HR's and the time invites a guess at it.
_REFUSAL_TIME_VALUE = {
	"Replaced": "replaced_at",
	"Removed": "removed_at",
}


def _device_from_token(token: str, allowed=("Active",)):
	"""Resolve a device secret to its registration, or refuse with a named code.

	Looks up by hash, so the secret is never compared in the database and never
	appears in a query log.

	`allowed` is the set of states the caller can work with. The punch and the
	start screen take the default - Active only. The notice endpoints (step 3)
	also accept "Consent not given", because reading the notice again is how a
	phone in that state becomes Active.
	"""
	if not token or not isinstance(token, str) or len(token) < 20:
		refuse("NOT_SET_UP",
		       _("This phone is not set up. Please register it again."))
	if len(token) > MAX_TOKEN_CHARS:
		# Deliberately a different answer from "not set up": this is a malformed
		# request, not a phone. It names no field, so it tells an attacker
		# nothing about what we check (SEC-19).
		refuse("INVALID_REQUEST", _("We could not read that request."))

	hashed = _hash(token)
	retired = False
	name = frappe.db.get_value(DEVICE, {"token_hash": hashed}, "name")
	if not name:
		retired = True
		# A phone that stopped keeps its old hash in `retired_token_hash`, so the
		# secret it is still holding is recognised and answered with its own
		# reason - "you joined on another phone", not "this phone is not set up".
		# Without this the person is told to set up again, does, and loses the
		# record of why they were stopped.
		name = frappe.db.get_value(DEVICE, {"retired_token_hash": hashed}, "name")
	if not name:
		# A well-formed secret we never stored gets the SAME answer as a phone
		# waiting for approval. register_device hands out a secret for every ID,
		# real or not (slice 014), so "not set up" here would tell the caller the
		# ID they typed was fake - the staff-directory leak, one call later.
		# The cost: a phone whose registration HR deleted also reads "waiting";
		# that screen offers "set up again", and HR knows why.
		_refuse_as_pending()

	device = frappe.get_doc(DEVICE, name)

	if retired and device.status not in device_rules.NO_LIVE_SECRET:
		# A retired hash on a phone that is not in a final state should be
		# impossible - the two are written in the same save. If it ever happens,
		# the row is not to be trusted, so the secret opens nothing.
		frappe.log_error(f"field device {device.name} holds a retired secret while "
		                 f"its status is {device.status}", "Field check-in")
		_refuse_as_pending()

	if device.status == "Pending":
		_refuse_as_pending()

	if device.status not in allowed:
		code, sentence = _REFUSAL_FOR_STATUS.get(
			device.status,
			# A status nobody has taught this code about. Fail closed: refuse,
			# and say nothing about which state it is in.
			("DEVICE_BLOCKED", "This phone has been blocked. Please speak to HR."))
		values = {}
		value_name = _REFUSAL_TIME_VALUE.get(device.status)
		if value_name and device.get("status_changed_on"):
			values[value_name] = str(device.status_changed_on)
		if code == "CONSENT_REQUIRED":
			values["version"] = CONSENT_VERSION
		refuse(code, _(sentence), **values)

	return device


def _refuse_unless_app_phone_is_eligible(device, designation=None):
	"""An APP phone works only while the organisation's settings allow it.

	The switch in HR Settings and the designation list are read on every call
	(US-3, AC-22, AC-78), so HR can stop the app in a minute without a deploy.
	A phone set up on the web check-in page is not touched by those settings
	(section 3.5 of the spec: "web-page phones keep working"), which is why the
	check is keyed on how the phone joined and not on the phone existing.

	The secret is kept and the phone's status is not changed: when HR restores
	the setting, the same phone works again with no new code (AC-78, AC-211).

	ALV-128: a phone that signed in with email and password answers to the
	master switch only - never the designation list (anyone with a login may
	use the app), and never the password switch, which stops NEW sign-ins
	only (the user's decision, 26 Sep 2026). It also stops, failing closed:
	  * when its login is disabled, even if the User hook that blocks it was
	    skipped (a script, `db.set_value`) - DEVICE_BLOCKED;
	  * when the employee record no longer names the login that signed it in
	    (SEC-28), even if the Employee hook was skipped - LOGIN_UNLINKED;
	  * when the login's password has changed since the phone signed in, by
	    ANY path (the User form, "forgot password", `bench set-password`, a
	    script) - the phone is signed out, not blocked, and told
	    PASSWORD_CHANGED_SIGN_IN_AGAIN (the user's decision, 26 Sep 2026).
	Three primary-key reads (Employee, User, `__Auth`). A QR phone makes none.
	"""
	if device.join_method == device_rules.JOIN_PASSWORD:
		settings.refuse_unless_app_on()
		linked = frappe.db.get_value("Employee", device.employee, "user_id")
		if not device.activated_by or linked != device.activated_by:
			refuse("LOGIN_UNLINKED",
			       _("This phone was set up with a login that is no longer linked to your "
			         "employee record. Sign in again, or speak to HR."))
		if not cint(frappe.db.get_value("User", device.activated_by, "enabled")):
			refuse("DEVICE_BLOCKED", _("This phone has been blocked. Please speak to HR."))
		_sign_out_if_password_changed(device)
		return
	if device.join_method != device_rules.JOIN_QR:
		return
	if designation is None:
		designation = frappe.db.get_value("Employee", device.employee, "designation")
	settings.refuse_unless_eligible(designation)


def password_stamp(user):
	"""A fingerprint of the login's CURRENT password, for a password phone to
	carry (ALV-128, 26 Sep 2026).

	HMAC-SHA256 of the password hash Frappe keeps in `__Auth`, keyed with this
	site's encryption key, cut to 32 hex characters. Never the password and
	never the hash: without the site's key the fingerprint cannot be matched to
	anything, and it changes whenever the hash does - which is every time the
	password is set, by any path, because Frappe salts each new hash.

	One read on `__Auth`'s primary key (doctype, name, fieldname), the same
	shape as Frappe's own `check_password`. An empty string when the login has
	no password at all, which never matches a stored fingerprint.
	"""
	from frappe.utils.password import Auth, get_encryption_key

	if not user:
		return ""
	row = (
		frappe.qb.from_(Auth)
		.select(Auth.password)
		.where((Auth.doctype == "User") & (Auth.name == user)
		       & (Auth.fieldname == "password") & (Auth.encrypted == 0))
		.limit(1)
	).run()
	if not row or not row[0][0]:
		return ""
	key = get_encryption_key().encode()
	return hmac.new(key, str(row[0][0]).encode(), hashlib.sha256).hexdigest()[:32]


def _sign_out_if_password_changed(device):
	"""Sign a password phone out when its login's password has changed.

	Not a block: the secret is retired and the record goes to "Signed out", so
	the next call from the same secret gets the same code, and signing in
	again (on this phone or another) replaces the record with no HR step.

	Written and committed BEFORE the refusal, because a refusal rolls the
	request back. Locks in the fixed order - the employee, then the phone -
	and re-reads the phone under the lock, so a block HR made a moment earlier
	is answered as a block, never overwritten.

	A phone with no fingerprint (signed in before this check existed) fails
	closed: it is signed out once and signs in again.
	"""
	stored = device.get("password_stamp") or ""
	current = password_stamp(device.activated_by)
	if stored and current and hmac.compare_digest(stored, current):
		return

	frappe.db.get_value("Employee", device.employee, "name", for_update=True)
	now_row = frappe.db.get_value(DEVICE, device.name, ["status", "token_hash"], as_dict=True,
	                              for_update=True)
	if not now_row or now_row.token_hash != device.token_hash 			or now_row.status not in ("Active", "Consent not given"):
		# Something else stopped this phone while we looked. Its own answer.
		code, sentence = _REFUSAL_FOR_STATUS.get(
			now_row.status if now_row else None,
			("DEVICE_BLOCKED", "This phone has been blocked. Please speak to HR."))
		refuse(code, _(sentence))

	phone = frappe.get_doc(DEVICE, device.name)
	phone.status = device_rules.SIGNED_OUT
	phone.flags[device_rules.SERVER_FLAG] = True
	phone.flags["alvoraa_change_source"] = "System"
	phone.save(ignore_permissions=True)
	frappe.db.commit()
	refuse("PASSWORD_CHANGED_SIGN_IN_AGAIN",
	       _("Your password was changed. Please sign in again."))


def _refuse_as_pending():
	"""One answer for a phone waiting for HR and for a secret nobody holds.

	The two must be indistinguishable, byte for byte, or this endpoint becomes a
	way to ask "does this employee exist" one call after register_device refused
	to answer it (slice 014, AC-1).
	"""
	refuse("DEVICE_PENDING",
	       _("This phone is waiting for HR to approve it. You will be able to check "
	         "in as soon as they do. If nothing happens today, check your employee ID "
	         "with HR and set up again."))


# ── registration: the one-time setup on the phone ────────────────────────────

@frappe.whitelist(allow_guest=True, methods=["POST"])
@_private_request("employee_id", "device_label", "platform")
@requires_field_app_plan
@rate_limit(limit=10, seconds=60 * 60)
def register_device(employee_id, device_label=None, platform=None,
                    consent=0, consent_version=None):
	"""Tie this phone to an employee and hand it a secret, which HR must enable.

	Open to guests because the person doing it has no login - that is the whole
	point of the feature. Which makes it the most attacked surface we have, so
	it is built to give an attacker nothing:

	  * **Every registration is Pending.** An earlier version trusted the first
	    phone to register for an employee and held only the second. That is
	    backwards: on the day a driver is hired nobody has registered, so an
	    attacker only had to be first. Being first is easy. Now a human decides,
	    every time, and the real driver is never the one left locked out.
	  * **The answer is identical whether the employee ID exists or not** - no
	    name, no company, no different error. Employee IDs run in sequence, so
	    anything that varies by ID is a staff directory for whoever asks.
	  * Rate limited **per caller**, not per employee ID. Keying the limit on
	    the ID meant each new ID an attacker tried opened a fresh bucket, which
	    limited the one thing nobody wants to do and nothing an attacker does.
	  * The secret is returned once and only its hash is kept.

	POST only. On a GET, nginx writes the whole query string - device secret and
	all - into an access log that is backed up and outlives the punch.
	"""
	# Before anything else, and before the employee is looked up. Checked later,
	# it would refuse a real ID and a fake one differently - the staff-directory
	# leak this endpoint was rebuilt to close.
	if not cint(consent):
		refuse("CONSENT_REQUIRED",
		       _("Please read the notice and tick the box to continue."),
		       version=CONSENT_VERSION)
	if consent_version != CONSENT_VERSION:
		# The page and the server disagree on what was shown - an old cached
		# page, most likely. Agreement to words the person never saw is not
		# agreement, so ask again rather than record it.
		refuse("NOTICE_CHANGED",
		       _("This screen is out of date. Close the app, open it "
		         "again, and read the notice."),
		       version=CONSENT_VERSION)

	employee_id = (employee_id or "").strip()
	if not employee_id:
		refuse("INVALID_REQUEST", _("Please enter your employee ID."))

	emp = frappe.db.get_value(
		"Employee",
		{"name": employee_id, "status": "Active"},
		["name", "employee_name"],
		as_dict=True,
	)

	# One reply for every outcome: unknown ID, employee who has left, first
	# phone, second phone. The caller learns only that somebody will look at it.
	answer = {
		"status": "pending",
		# It says "set up again" because a mistyped employee ID gets this same
		# answer on purpose (nobody may test employee IDs against this endpoint).
		# Without that sentence the person waits for an approval nobody was asked
		# for, is not marked present, and attendance is pay.
		"message": _("Thanks. HR needs to approve this phone before you can check "
		             "in. You only have to do this once. If nothing happens today, "
		             "check your employee ID with HR and set up again."),
	}

	# Every caller gets a secret, so the reply has the same shape for a real ID
	# and a made-up one. Before slice 014 only a real ID got a `token`, which
	# told anyone which IDs exist. A made-up ID's secret is never stored, so it
	# opens nothing; field_status answers it exactly as it answers a phone
	# still waiting for HR.
	token = secrets.token_urlsafe(32)

	if not emp:
		answer["token"] = token
		return answer

	phone = frappe.get_doc({
		"doctype": DEVICE,
		"employee": emp.name,
		"employee_name": emp.employee_name,
		"status": "Pending",
		# How it arrived. It decides later which rules apply: only a web phone
		# is switched on by a human in HR, because only a web phone was never
		# approved in advance by somebody making a code.
		"join_method": "Web check-in page",
		"device_label": (device_label or "")[:140],
		"platform": (platform or "")[:60],
		"token_hash": _hash(token),
		"registered_on": now(),
		"consent_given_on": now(),
		"consent_version": CONSENT_VERSION,
	})
	# Nobody makes one of these by hand any more (US-2). This says the server is
	# the author, which is the only way a phone record is allowed to appear.
	phone.flags[device_rules.SERVER_FLAG] = True
	phone.insert(ignore_permissions=True)
	# The history row (PRIV-3, AC-95): which words this person read, on which
	# phone, from which screen. The two fields above stay written as well - they
	# are what the web page and slice 014's tests read today, and stopping them
	# is the web page's own change, not this one.
	record_acknowledgement(emp.name, CONSENT_VERSION, "Web check-in page",
	                       device=phone.name)
	frappe.db.commit()

	# The phone keeps this and starts working the moment HR activates it. It is
	# said once; no endpoint anywhere gives it back.
	answer["token"] = token
	return answer


# ── the punch ────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True, methods=["POST"])
@_private_request("photo", "latitude", "longitude", "accuracy", "captured_at")
@requires_field_app_plan
@_limited(PHONE_KEY, "token", limit=30)
def field_checkin(token, log_type, latitude=None, longitude=None,
                  accuracy=None, photo=None, captured_at=None, mock_location=0):
	"""Record a punch from the field app (E5).

	`captured_at` is what the phone believed the time was when the photo was
	taken. The time written to the record is always the SERVER's, because a
	phone clock belongs to the person holding it. The phone's claim is kept
	beside it, because the gap between the two is the only thing that would
	expose a punch that was stored and replayed later.

	`mock_location` is the app saying its own operating system reported a fake
	position (SEC-21). It is recorded on the punch and nothing else: the punch
	is still saved, because a false positive on a cheap phone would mean
	somebody is not marked present (user decision Q-15, flag only).

	Rate limited **per phone**, 30 an hour, keyed on the hash of the secret
	(section 6). It used to be 60 an hour per IP address, which would have
	refused a depot where 400 phones share one Wi-Fi (AC-140).
	"""
	errors.check_app_version()
	device = _device_from_token(token)

	emp = frappe.db.get_value(
		"Employee", device.employee,
		["name", "employee_name", "status", "designation"], as_dict=True)
	if not emp or emp.status != "Active":
		refuse("EMPLOYEE_NOT_ACTIVE",
		       _("This employee record is no longer active. Please speak "
		         "to HR."))
	_refuse_unless_app_phone_is_eligible(device, emp.designation)
	_refuse_unless_notice_is_current(device)

	if log_type not in ("IN", "OUT"):
		refuse("INVALID_REQUEST", _("Invalid check-in type."))

	lat, lon = _require_position(latitude, longitude, accuracy,
	                             accuracy_required=device.join_method in device_rules.APP_JOIN_METHODS)
	claimed = _validated_captured_at(captured_at, errors.sent_app_version())

	_refuse_duplicate(device, log_type)

	doc = frappe.get_doc({
		"doctype": "Employee Checkin",
		"employee": emp.name,
		"employee_name": emp.employee_name,
		"log_type": log_type,
		"time": now(),
		# Distinguishes a phone punch from the reception machine's, so reports
		# can tell them apart without a field of our own.
		"device_id": "alvoraa-field-app",
		"latitude": lat,
		"longitude": lon,
		"alvoraa_gps_accuracy": flt(accuracy) if accuracy not in (None, "") else None,
		"alvoraa_checkin_offline": 1 if claimed else 0,
		"alvoraa_captured_at": claimed,
		"alvoraa_mock_location": _flag(mock_location),
		# Which phone. Without this, "who punched for Ramesh on 3 March" has no
		# answer, so an incident cannot be scoped and a deduction cannot be
		# defended in a grievance.
		"alvoraa_field_device": device.name,
	})

	try:
		doc.insert(ignore_permissions=True)
	except Exception as e:
		# Frappe HR refuses a punch outside the branch radius. Its own words are
		# "You must be within 100 meters of your shift location to check in.",
		# which tells a driver nothing about where they are. Rewrite it with the
		# real distance, and leave every other failure alone.
		friendly = _geofence_message(e, emp.name, lat, lon)
		if friendly:
			# REPLACE Frappe's wording, do not add to it. Its message is already
			# queued in the message log by the time we get here, so throwing on
			# top produced both sentences stitched together - "You must be within
			# 250 meters of your shift location to check in. You are about 2029 m
			# from Demo Field Site..." - which is twice as long and says the
			# radius twice.
			frappe.clear_messages()
			refuse("OUTSIDE_WORKPLACE", friendly["message"], **friendly["values"])
		raise

	if photo:
		_attach_photo(doc, photo)

	# Deliberately no position here. The punch already holds where somebody was;
	# a second copy on a doctype with different permissions and no retention
	# rule would be personal data kept for no reason.
	activity = {
		"last_seen": now(),
		"checkin_count": cint(device.checkin_count) + 1,
	}
	# The build that sent this punch, for support. Written on a saved punch and
	# never on an app open (section 4.1), so opening the app moves nothing.
	sent_version = errors.sent_app_version()
	if sent_version and sent_version != device.app_version:
		activity["app_version"] = sent_version
	device.db_set(activity, update_modified=False)

	frappe.db.commit()

	return {
		"status": "ok",
		"log_type": log_type,
		"time": str(doc.time),
		"name": doc.name,
		"employee_name": emp.employee_name,
		# So the app can redraw home from this answer with no extra E4 (AC-199).
		"todays_checkins": _todays_punches(emp.name),
		# Where the punch was, as measured here (fix of 27 Sep 2026): the app
		# said "At <workplace>" for someone 13 km away because it only had the
		# workplace's name. Never the workplace's coordinates (PRIV-6).
		"location": _where_it_was(emp.name, lat, lon, accuracy),
	}


def _flag(value):
	"""A yes/no the phone sent, as 1 or 0. JSON true, "1" and 1 are yes;
	anything else, including nothing, is no."""
	if isinstance(value, bool):
		return 1 if value else 0
	return 1 if str(value or "").strip().lower() in ("1", "true") else 0


def _refuse_unless_notice_is_current(device):
	"""An APP phone whose owner has not read the current notice may not punch
	or see home until they do (AC-80, AC-91, D19). Web phones are never asked
	again (AC-96): they registered under the words the page showed them.

	One indexed read on the acknowledgement table (by device). Both app ways
	in are asked (ALV-128); only the web page is not.
	"""
	if device.join_method not in device_rules.APP_JOIN_METHODS:
		return
	if latest_version_for(device.name) == notice.CURRENT_VERSION:
		return
	facts = notice.facts()
	refuse("NOTICE_CHANGED",
	       _("The notice has changed. Please read it again."),
	       version=facts["version"], rows=facts["rows"],
	       retention_days=facts["retention_days"], what_changed=facts["what_changed"])


def _todays_punches(employee):
	"""Today's punches for one employee, oldest first. Uses the `employee`
	index; `time` is not indexed in Frappe HR and does not need to be at this
	volume (Finding D)."""
	return frappe.get_all(
		"Employee Checkin",
		filters={"employee": employee, "time": [">=", today() + " 00:00:00"]},
		fields=["name", "log_type", "time", "device_id"],
		order_by="time asc",
		ignore_permissions=True,
	)


def _radius_checked():
	"""Frappe HR checks the workplace radius only when HR Settings allows
	location tracking. With it off, a radius is a rule nobody enforces, so the
	phone must say "from anywhere" rather than promise a distance (27 Sep 2026)."""
	return bool(cint(frappe.db.get_single_value("HR Settings", "allow_geolocation_tracking")))


def _enforced_radius(site):
	return cint(site.checkin_radius) if site and _radius_checked() else 0


def _workplace(site):
	"""Name and radius only. Never the coordinates (PRIV-6). The radius is 0
	when nobody enforces it (location tracking off in HR Settings)."""
	return {"name": site.location_name, "radius_m": _enforced_radius(site)} if site else None


def _where_it_was(employee, lat, lon, accuracy):
	"""How far a saved punch was from the workplace, for the phone's result card.

	`within` is True or False only when the workplace has a radius above 0;
	with no workplace, a radius of 0 (Frappe HR's "no limit") or no
	coordinates on the workplace, it is None and the app never claims the
	person was at the workplace. The distance is measured the same way Frappe
	HR's own radius rule measures it (`get_distance_between_coordinates`).
	Two small reads, on a punch that has already been saved.
	"""
	acc = flt(accuracy) if accuracy not in (None, "") else None
	answer = {
		"workplace": None,
		"radius_m": None,
		"distance_m": None,
		"within": None,
		"accuracy_m": int(round(acc)) if acc is not None else None,
	}
	site = _shift_location_for(employee)
	if not site:
		return answer
	radius = _enforced_radius(site)
	answer["workplace"] = site.location_name
	answer["radius_m"] = radius
	if not (site.latitude or site.longitude):
		return answer

	from hrms.hr.utils import get_distance_between_coordinates

	distance = get_distance_between_coordinates(
		flt(site.latitude), flt(site.longitude), flt(lat), flt(lon))
	answer["distance_m"] = int(round(distance))
	if radius > 0:
		answer["within"] = distance <= radius
	return answer


def _require_position(latitude, longitude, accuracy, accuracy_required=False):
	"""A punch without a trustworthy position is not recorded.

	Two separate refusals, because they need different words: no fix at all
	usually means location is switched off, while a vague fix means the phone is
	indoors or has not settled yet. Telling somebody to "enable location" when
	it is already on sends them round in circles.

	`accuracy_required` is on for app phones: the app always has the accuracy,
	so a reading that arrives without one is not a reading we can judge, and
	the decision (step 4) is that every stored app reading carries it. The web
	page is left as it was (AC-35).
	"""
	if latitude in (None, "") or longitude in (None, ""):
		refuse("LOCATION_MISSING",
		       _("We could not get your location. Turn on location for "
		         "this app and try again."))

	acc = flt(accuracy) if accuracy not in (None, "") else None
	if accuracy_required and acc is None:
		refuse("LOCATION_MISSING",
		       _("We could not get your location. Turn on location for "
		         "this app and try again."))
	if acc is not None and acc > MAX_ACCURACY_METRES:
		refuse("GPS_NOT_EXACT",
		       _("Your location is only accurate to about {0} m, which is not "
		         "close enough to record. Step outside or into the open and try "
		         "again.").format(int(acc)),
		       accuracy_m=int(acc), limit_m=int(MAX_ACCURACY_METRES))

	return flt(latitude), flt(longitude)


# App builds before this one sent the phone's time in UTC with no offset.
FIRST_BUILD_WITH_OFFSET = (0, 2, 1)


def _validated_captured_at(captured_at, app_version=None):
	"""The phone's own timestamp, kept only when it is plausible.

	Anything more than a day either side of server time is a wrong clock or a
	replayed request, and is dropped rather than stored as if it meant
	something. Returns None when there is nothing trustworthy to keep.

	A time that carries its offset from UTC ("2026-09-27T14:05:09+05:30", what
	the app sends from 0.2.1) is moved into the site's time zone before it is
	compared or stored. A time with no offset from an app build before 0.2.1
	is UTC (those builds sent `toISOString()` without the Z), so it is read as
	UTC and moved the same way. A time with no offset and no app version (the
	web check-in page) is read as site time, as before (27 Sep 2026).
	"""
	if not captured_at:
		return None
	try:
		claimed = get_datetime(captured_at)
	except Exception:
		return None
	if not claimed:
		return None
	if claimed.tzinfo is None and _sends_bare_utc(app_version):
		claimed = claimed.replace(tzinfo=datetime.timezone.utc)
	if claimed.tzinfo is not None:
		claimed = convert_utc_to_system_timezone(
			claimed.astimezone(datetime.timezone.utc)).replace(tzinfo=None)
	if abs(time_diff_in_seconds(now(), claimed)) > 24 * 60 * 60:
		return None
	return claimed


def _sends_bare_utc(app_version):
	"""True for an app build older than 0.2.1. No version (the web page) is False."""
	parsed = errors.parse_version(app_version) if app_version else None
	return bool(parsed) and parsed < FIRST_BUILD_WITH_OFFSET


def _refuse_duplicate(device, log_type):
	"""Stop the same punch being recorded twice.

	A flaky mobile connection makes the phone retry, and an offline queue can
	send the same punch again on reconnect. Without this, one arrival becomes
	three, and the working-hours total that feeds pay is wrong.
	"""
	recent = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": device.employee,
			"log_type": log_type,
			"time": [">", add_to_date(now(), seconds=-DUPLICATE_WINDOW_SECONDS)],
		},
		fields=["time"],
		order_by="time desc",
		limit=1,
	)
	if recent:
		refuse("ALREADY_RECORDED", _("That check-in is already recorded."),
		       time=str(recent[0].time))


def _geofence_message(exc, employee, lat, lon):
	"""Turn Frappe HR's radius refusal into something a driver can act on.

	Returns None for any other error, so real failures are never swallowed and
	dressed up as a location problem. Otherwise `{"message", "values"}`: the
	sentence for the person reading it, and the same facts as named values so an
	app can draw its own screen from them. The sentences are word for word what
	they were before slice 013 (AC-35); only the values beside them are new.
	"""
	try:
		from hrms.hr.doctype.employee_checkin.employee_checkin import (
			CheckinRadiusExceededError,
		)
	except Exception:
		return None

	if not isinstance(exc, CheckinRadiusExceededError):
		return None

	site = _shift_location_for(employee)
	if not site:
		return {"message": _("You are too far from your work location to check in."),
		        "values": {}}

	try:
		from hrms.hr.utils import get_distance_between_coordinates
		distance = int(get_distance_between_coordinates(
			site.latitude, site.longitude, lat, lon))
	except Exception:
		return {"message": _("You are too far from {0} to check in.").format(
			site.location_name),
			"values": {"site": site.location_name,
			           "radius_m": cint(site.checkin_radius)}}

	return {
		"message": _("You are about {0} m from {1}. You need to be within {2} m to "
		             "check in.").format(distance, site.location_name,
		                                 cint(site.checkin_radius)),
		# Never the workplace coordinates. The distance is what a person can act
		# on; the position of the branch is not the phone's business (PRIV-6).
		"values": {"distance_m": distance, "site": site.location_name,
		           "radius_m": cint(site.checkin_radius)},
	}


def _shift_location_for(employee):
	"""The Shift Location Frappe HR would have measured against.

	Mirrors the lookup in `validate_distance_from_shift_location` so the message
	names the same place the rule used.
	"""
	names = frappe.get_all(
		"Shift Assignment",
		filters={
			"employee": employee,
			"start_date": ["<=", today()],
			"shift_location": ["is", "set"],
			"docstatus": 1,
			"status": "Active",
		},
		or_filters=[["end_date", ">=", today()], ["end_date", "is", "not set"]],
		pluck="shift_location",
	)
	if not names:
		return None
	return frappe.db.get_value(
		"Shift Location", names[0],
		["location_name", "checkin_radius", "latitude", "longitude"], as_dict=True)


# ── what the phone shows ─────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True, methods=["POST"])
@_private_request()
@requires_field_app_plan
@_limited(PHONE_KEY, "token", limit=60)
def field_status(token):
	"""Today's punches for this phone, and whether they are currently in (E4).

	Deliberately narrow: this endpoint answers for one employee, on one
	registered phone, for one day. It is not a way to read anybody else.

	It reads and never writes: opening the app five times moves nothing on the
	phone record (AC-77), so "last seen" stays the last PUNCH and nobody can
	watch when a person opens their phone (PRIV-9).

	The workplace is sent as a name and a radius. An APP phone never receives
	the branch's coordinates (PRIV-6). The web check-in page still gets its
	`work_location` block, coordinates included, because that page reads it
	today and step 4 may not change that page (AC-35); the block is simply not
	built for app phones.

	Rate limited per phone, 60 an hour, keyed on the hash of the secret.
	"""
	errors.check_app_version()
	device = _device_from_token(token)

	emp = frappe.db.get_value(
		"Employee", device.employee,
		["name", "first_name", "employee_name", "status", "designation", "company"],
		as_dict=True)
	if not emp or emp.status != "Active":
		# A leaver whose phone the hook has not blocked yet (AC-83): the same
		# answer the punch gives, so the app shows one screen for it.
		refuse("EMPLOYEE_NOT_ACTIVE",
		       _("This employee record is no longer active. Please speak "
		         "to HR."))
	_refuse_unless_app_phone_is_eligible(device, emp.designation)
	_refuse_unless_notice_is_current(device)

	rows = _todays_punches(device.employee)
	last = rows[-1] if rows else None
	site = _shift_location_for(device.employee)

	answer = {
		"employee": device.employee,
		"employee_name": emp.employee_name,
		"first_name": emp.first_name,
		"designation": emp.designation,
		"company": emp.company,
		"checked_in": bool(last and last.log_type == "IN"),
		"todays_checkins": rows,
		"server_time": now(),
		"workplace": _workplace(site),
		"min_version": errors.MIN_APP_VERSION,
		"notice_version": notice.CURRENT_VERSION,
		"joined_on": str(device.registered_on or ""),
	}
	if device.join_method not in device_rules.APP_JOIN_METHODS:
		# The web page's block, byte for byte what it was before slice 013.
		answer["work_location"] = {
			"name": site.location_name,
			"radius": cint(site.checkin_radius),
			"latitude": site.latitude,
			"longitude": site.longitude,
		} if site else None
	return answer


# ── what the setup notice has to say ─────────────────────────────────────────
#
# The retention number comes from the organisation's own setting, which lives in
# `field_app_photos`. The web page's template reads this, so its shape is part of
# that page's contract.

def notice_facts():
	"""What the setup notice has to state, from this organisation's settings.

	Rendered into the page rather than written into it, so the notice cannot
	promise 90 days while the organisation keeps photos for a year.
	"""
	days = photo_retention_days()
	return {
		"photo_retention_days": days,
		"consent_version": CONSENT_VERSION,
		# The words themselves, so a screen can render the notice from the store
		# instead of holding its own copy. The web page does not read these yet -
		# that change belongs with the page's own work, and this slice's step 1
		# must leave that page byte for byte as it was (AC-35).
		"notice": notice.facts(),
	}


# ── install: the fields this feature adds to Employee Checkin ────────────────

def after_migrate():
	"""Add our columns to Employee Checkin, on migrate AND on install.

	Wired to both for the reason written into `attendance_correction.after_migrate`:
	a site built with `bench install-app` never runs a migrate, so an install-only
	site would be missing the columns and every field punch would fail on
	"Unknown column".
	"""
	if not frappe.db.exists("DocType", "Employee Checkin"):
		return False

	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({
		"Employee Checkin": [
			{
				"fieldname": "alvoraa_checkin_photo",
				"label": "Check-in Photo",
				"fieldtype": "Attach Image",
				"insert_after": "device_id",
				"read_only": 1,
				"no_copy": 1,
				"description": "Taken by the field app at the moment of the punch. Stored privately.",
			},
			{
				"fieldname": "alvoraa_gps_accuracy",
				"label": "GPS Accuracy (m)",
				"fieldtype": "Float",
				"insert_after": "longitude",
				"read_only": 1,
				"no_copy": 1,
				"precision": "1",
				"description": "How precise the phone said its position was. A large number means the fix was weak.",
			},
			{
				"fieldname": "alvoraa_checkin_offline",
				"label": "Recorded Offline",
				"fieldtype": "Check",
				"insert_after": "alvoraa_gps_accuracy",
				"read_only": 1,
				"no_copy": 1,
				"default": "0",
				"description": "The punch was taken with no signal and sent when the phone reconnected.",
			},
			{
				"fieldname": "alvoraa_captured_at",
				"label": "Taken At (phone clock)",
				"fieldtype": "Datetime",
				"insert_after": "alvoraa_checkin_offline",
				"read_only": 1,
				"no_copy": 1,
				"description": "What the phone said the time was. The punch time beside it is the server's. A wide gap is worth a look.",
			},
			{
				"fieldname": "alvoraa_mock_location",
				"label": "Phone reported a fake location",
				"fieldtype": "Check",
				"insert_after": "alvoraa_captured_at",
				"read_only": 1,
				"no_copy": 1,
				"in_standard_filter": 1,
				"default": "0",
				"description": "The phone's own operating system said the position was faked (a mock-location app). The punch is saved; look before you trust it.",
			},
			{
				"fieldname": "alvoraa_legal_hold",
				"label": "Hold (do not delete photo)",
				"fieldtype": "Check",
				"insert_after": "alvoraa_field_device",
				"default": "0",
				"description": "Keeps the photo past the retention period. For a dispute, an investigation or anything somebody has asked you to preserve.",
			},
			{
				"fieldname": "alvoraa_field_device",
				"label": "Field Device",
				"fieldtype": "Link",
				"options": "Alvoraa Field Device",
				"insert_after": "alvoraa_mock_location",
				"read_only": 1,
				"no_copy": 1,
				"description": "Which registered phone sent this punch.",
			},
		]
	}, ignore_validate=True)

	return True


def refuse_small_radius(doc, method=None):
	"""doc_events Shift Location validate: a radius under MIN_RADIUS_M cannot be
	honestly checked by a phone, so it cannot be saved (user decision, step 4).

	A hook in our app, not an edit to Frappe HR's Shift Location: that keeps
	`bench update` safe. It fires on every door - form, import, REST. 0 keeps
	Frappe HR's meaning, "no radius", and is allowed. Rows already saved with a
	smaller radius are untouched until HR next edits them; the punch never
	refuses on the radius setting itself.
	"""
	radius = cint(doc.get("checkin_radius"))
	if 0 < radius < MIN_RADIUS_M:
		frappe.throw(
			_("A check-in radius under {0} m cannot be checked by a phone. Phone "
			  "location is only trusted to about {1} m, so people standing at the "
			  "door would be refused. Use {0} m or more, or 0 for no radius.").format(
				MIN_RADIUS_M, int(MAX_ACCURACY_METRES)),
			frappe.ValidationError)


def block_devices_for_leaver(doc, method=None):
	"""A phone stops working the day its owner stops being an employee.

	The punch endpoint already refuses a non-Active employee, so this is the
	second lock rather than the only one. It matters because a status that goes
	back to Active - a rehire, a correction, a script - would otherwise re-arm a
	secret that somebody left the company still holding.

	**This used to write straight to the table** with
	`frappe.db.set_value(..., update_modified=False)`, which skips `validate` and
	`on_update`. Every rule slice 013 put in the controller - retiring the
	secret's hash, recording who changed the status and when, requiring a reason
	- would therefore have fired for every phone in the product EXCEPT a
	leaver's, which is the one case that matters most. It now goes through the
	document, so a leaver's phone is stopped exactly the way HR blocking it is.
	"""
	if doc.status == "Active":
		return
	if not frappe.db.exists("DocType", DEVICE):
		return

	# The codes first, then the phones: the fixed lock order every writer of
	# these rows follows (field_app_join says why). The Employee row itself is
	# already locked by the save this hook runs inside.
	if frappe.db.exists("DocType", INVITE):
		for name in frappe.get_all(INVITE, filters={"employee": doc.name, "status": "Waiting"},
		                           pluck="name"):
			try:
				cancel_invite(name, "Employee left")
			except Exception:
				frappe.log_error(f"could not cancel app invite {name} for a leaver",
				                 "Field check-in leaver")

	for name in frappe.get_all(
		DEVICE,
		filters={"employee": doc.name,
		         # "Signed out" too (ALV-128 review): no live secret, but HR must
		         # read "Left the company", not "can sign in again".
		         "status": ["in", ["Active", "Pending", "Consent not given", "Signed out"]]},
		pluck="name",
	):
		try:
			phone = frappe.get_doc(DEVICE, name)
			phone.status = "Blocked"
			phone.block_reason = "Left the company"
			phone.flags[device_rules.SERVER_FLAG] = True
			phone.save(ignore_permissions=True)
		except Exception:
			# One phone that will not save must not stop the others, and must not
			# stop HR saving the employee record. The row is named; nothing
			# personal goes into the log.
			frappe.log_error(f"could not block field device {name} for a leaver",
			                 "Field check-in leaver")
