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

import functools
import hashlib
import secrets
import traceback

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import (
	add_to_date,
	cint,
	flt,
	get_datetime,
	now,
	time_diff_in_seconds,
	today,
)

from alvoraa_portal.subscription import requires_feature

# ── the pieces that used to live in this file ────────────────────────────────
#
# This module was 1,126 lines and slice 013 roughly doubles it, so the parts
# that are not about the punch or the phone's identity now live beside it. The
# names are imported straight back, because `hooks.py`, the web page and the
# browser all call them at `alvoraa_portal.field_checkin.<name>` and a path in
# a hook or a browser URL is a promise. Nothing moved changed.
from alvoraa_portal.field_app_access import (  # noqa: F401  (re-exported for hooks.py)
	ACCESS_LOG,
	_HR_ROLES,
	_viewer,
	checkin_has_permission,
	checkin_query_conditions,
	log_photo_view,
)
from alvoraa_portal.field_app_photos import (  # noqa: F401  (re-exported for hooks.py)
	DEFAULT_RETENTION_DAYS,
	JPEG_MAGIC,
	MAX_PHOTO_B64_CHARS,
	MAX_PHOTO_BYTES,
	SETTING_RETENTION_DAYS,
	_setting,
	photo_retention_days,
	purge_old_checkin_photos,
)
from alvoraa_portal.field_app_photos import attach_photo as _attach_photo  # noqa: F401
from alvoraa_portal.field_app_pwa import (  # noqa: F401  (re-exported: the browser's URLs)
	_brand,
	_darker,
	_SERVICE_WORKER,
	app_icon,
	manifest,
	service_worker,
)

DEVICE = "Alvoraa Field Device"

# The version of the notice shown at setup. Change it whenever the notice's
# meaning changes. A consent record that says only "agreed" cannot answer "agreed
# to what?" once the words have moved on; one that names the version can.
CONSENT_VERSION = "2026-09-13"

# A phone that cannot place itself better than this cannot be used to answer
# "were you at the branch". Roughly the accuracy of a decent fix outdoors; a
# reading worse than this usually means the phone fell back to the mobile
# network rather than GPS.
MAX_ACCURACY_METRES = 100.0

# Two punches of the same kind inside this window are one punch, retried.
DUPLICATE_WINDOW_SECONDS = 60

# Frappe HR treats a radius of 0 or less as "no geofence", so 1 metre is the
# smallest real boundary the framework has. It is offered, but it is not
# sensible - see ADVISED_MIN_RADIUS_M.
FRAPPE_MIN_RADIUS_M = 1

# Below this, a phone will refuse people who are genuinely standing at the door.
# The Org Settings screen warns under this number; it does not block it.
ADVISED_MIN_RADIUS_M = 50

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
			for field in fields:
				frappe.form_dict.pop(field, None)
			try:
				return fn(*args, **kwargs)
			except Exception as exc:
				status = getattr(exc, "http_status_code", None) or 500
				frappe.db.rollback()
				if status < 500:
					# A refusal: frappe.throw has already queued its sentence, and
					# the page matches on that sentence. Answer as Frappe would.
					frappe.local.response["http_status_code"] = status
					frappe.local.response["exc_type"] = type(exc).__name__
					return None
				_log_server_error(fn.__name__, exc)
				frappe.clear_messages()
				frappe.msgprint(_("Something went wrong on our side. Please try again "
				                  "in a minute."))
				frappe.local.response["http_status_code"] = 500
				frappe.local.response["exc_type"] = "ServerError"
				return None

		wrapper.__alvoraa_private_request__ = fields    # so tests can see it
		return wrapper

	return decorator


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

def _hash(token: str) -> str:
	"""Store only the hash, the way an API secret should be kept.

	If this table ever leaks, the secrets in it cannot be replayed.
	"""
	return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _device_from_token(token: str):
	"""Resolve a device secret to its registration, or throw.

	Looks up by hash, so the secret is never compared in the database and never
	appears in a query log.
	"""
	if not token or not isinstance(token, str) or len(token) < 20:
		frappe.throw(_("This phone is not set up. Please register it again."),
		             frappe.AuthenticationError)

	name = frappe.db.get_value(DEVICE, {"token_hash": _hash(token)}, "name")
	if not name:
		# A well-formed secret we never stored gets the SAME answer as a phone
		# waiting for approval. register_device hands out a secret for every ID,
		# real or not (slice 014), so "not set up" here would tell the caller the
		# ID they typed was fake - the staff-directory leak, one call later.
		# The cost: a phone whose registration HR deleted also reads "waiting";
		# that screen offers "set up again", and HR knows why.
		_refuse_as_pending()

	device = frappe.get_doc(DEVICE, name)

	if device.status == "Blocked":
		frappe.throw(_("This phone has been blocked. Please speak to HR."),
		             frappe.AuthenticationError)
	if device.status == "Pending":
		_refuse_as_pending()

	return device


def _refuse_as_pending():
	frappe.throw(
		_("This phone is waiting for HR to approve it. You will be able to check "
		  "in as soon as they do. If nothing happens today, check your employee ID "
		  "with HR and set up again."),
		frappe.AuthenticationError)


# ── registration: the one-time setup on the phone ────────────────────────────

@frappe.whitelist(allow_guest=True, methods=["POST"])
@_private_request("employee_id", "device_label", "platform")
@requires_feature("field_checkin")
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
		frappe.throw(_("Please read the notice and tick the box to continue."))
	if consent_version != CONSENT_VERSION:
		# The page and the server disagree on what was shown - an old cached
		# page, most likely. Agreement to words the person never saw is not
		# agreement, so ask again rather than record it.
		frappe.throw(_("This screen is out of date. Close the app, open it "
		               "again, and read the notice."))

	employee_id = (employee_id or "").strip()
	if not employee_id:
		frappe.throw(_("Please enter your employee ID."))

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

	frappe.get_doc({
		"doctype": DEVICE,
		"employee": emp.name,
		"employee_name": emp.employee_name,
		"status": "Pending",
		"device_label": (device_label or "")[:140],
		"platform": (platform or "")[:60],
		"token_hash": _hash(token),
		"registered_on": now(),
		"consent_given_on": now(),
		"consent_version": CONSENT_VERSION,
	}).insert(ignore_permissions=True)
	frappe.db.commit()

	# The phone keeps this and starts working the moment HR activates it. It is
	# said once; no endpoint anywhere gives it back.
	answer["token"] = token
	return answer


# ── the punch ────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True, methods=["POST"])
@_private_request("photo", "latitude", "longitude", "accuracy", "captured_at")
@requires_feature("field_checkin")
@rate_limit(limit=60, seconds=60 * 60)
def field_checkin(token, log_type, latitude=None, longitude=None,
                  accuracy=None, photo=None, captured_at=None):
	"""Record a punch from the field app.

	`captured_at` is what the phone believed the time was when the photo was
	taken. The time written to the record is always the SERVER's, because a
	phone clock belongs to the person holding it. The phone's claim is kept
	beside it, because the gap between the two is the only thing that would
	expose a punch that was stored and replayed later.

	Rate limited per caller, and not keyed on the token: Frappe puts a rate
	limit key into the Redis key in clear, which would write every device
	secret into Redis and into any error about it.
	"""
	device = _device_from_token(token)

	if log_type not in ("IN", "OUT"):
		frappe.throw(_("Invalid check-in type."))

	lat, lon = _require_position(latitude, longitude, accuracy)
	claimed = _validated_captured_at(captured_at)

	emp = frappe.db.get_value(
		"Employee", device.employee,
		["name", "employee_name", "status"], as_dict=True)
	if not emp or emp.status != "Active":
		frappe.throw(_("This employee record is no longer active. Please speak "
		               "to HR."), frappe.AuthenticationError)

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
			frappe.throw(friendly, exc=frappe.ValidationError)
		raise

	if photo:
		_attach_photo(doc, photo)

	# Deliberately no position here. The punch already holds where somebody was;
	# a second copy on a doctype with different permissions and no retention
	# rule would be personal data kept for no reason.
	device.db_set({
		"last_seen": now(),
		"checkin_count": cint(device.checkin_count) + 1,
	}, update_modified=False)

	frappe.db.commit()

	return {
		"status": "ok",
		"log_type": log_type,
		"time": str(doc.time),
		"name": doc.name,
		"employee_name": emp.employee_name,
	}


def _require_position(latitude, longitude, accuracy):
	"""A punch without a trustworthy position is not recorded.

	Two separate refusals, because they need different words: no fix at all
	usually means location is switched off, while a vague fix means the phone is
	indoors or has not settled yet. Telling somebody to "enable location" when
	it is already on sends them round in circles.
	"""
	if latitude in (None, "") or longitude in (None, ""):
		frappe.throw(_("We could not get your location. Turn on location for "
		               "this app and try again."))

	acc = flt(accuracy) if accuracy not in (None, "") else None
	if acc is not None and acc > MAX_ACCURACY_METRES:
		frappe.throw(
			_("Your location is only accurate to about {0} m, which is not "
			  "close enough to record. Step outside or into the open and try "
			  "again.").format(int(acc)))

	return flt(latitude), flt(longitude)


def _validated_captured_at(captured_at):
	"""The phone's own timestamp, kept only when it is plausible.

	Anything more than a day either side of server time is a wrong clock or a
	replayed request, and is dropped rather than stored as if it meant
	something. Returns None when there is nothing trustworthy to keep.
	"""
	if not captured_at:
		return None
	try:
		claimed = get_datetime(captured_at)
	except Exception:
		return None
	if abs(time_diff_in_seconds(now(), claimed)) > 24 * 60 * 60:
		return None
	return claimed


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
		limit=1,
	)
	if recent:
		frappe.throw(_("That check-in is already recorded."))


def _geofence_message(exc, employee, lat, lon):
	"""Turn Frappe HR's radius refusal into something a driver can act on.

	Returns None for any other error, so real failures are never swallowed and
	dressed up as a location problem.
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
		return _("You are too far from your work location to check in.")

	try:
		from hrms.hr.utils import get_distance_between_coordinates
		distance = int(get_distance_between_coordinates(
			site.latitude, site.longitude, lat, lon))
	except Exception:
		return _("You are too far from {0} to check in.").format(site.location_name)

	return _("You are about {0} m from {1}. You need to be within {2} m to "
	         "check in.").format(distance, site.location_name, cint(site.checkin_radius))


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
@requires_feature("field_checkin")
@rate_limit(limit=120, seconds=60 * 60)
def field_status(token):
	"""Today's punches for this phone, and whether they are currently in.

	Deliberately narrow: this endpoint answers for one employee, on one
	registered phone, for one day. It is not a way to read anybody else.
	"""
	device = _device_from_token(token)

	emp = frappe.db.get_value(
		"Employee", device.employee,
		["name", "employee_name", "designation"], as_dict=True)

	rows = frappe.get_all(
		"Employee Checkin",
		filters={"employee": device.employee, "time": [">=", today() + " 00:00:00"]},
		fields=["name", "log_type", "time", "device_id"],
		order_by="time asc",
		ignore_permissions=True,
	)

	last = rows[-1] if rows else None
	site = _shift_location_for(device.employee)

	return {
		"employee": device.employee,
		"employee_name": emp.employee_name if emp else device.employee_name,
		"designation": emp.designation if emp else None,
		"checked_in": bool(last and last.log_type == "IN"),
		"todays_checkins": rows,
		"server_time": now(),
		# Sent so the phone can show "You need to be within 100 m of PPJ Noida"
		# before somebody walks somewhere, rather than after they are refused.
		"work_location": {
			"name": site.location_name,
			"radius": cint(site.checkin_radius),
			"latitude": site.latitude,
			"longitude": site.longitude,
		} if site else None,
	}


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
				"insert_after": "alvoraa_captured_at",
				"read_only": 1,
				"no_copy": 1,
				"description": "Which registered phone sent this punch.",
			},
		]
	}, ignore_validate=True)

	return True


def block_devices_for_leaver(doc, method=None):
	"""A phone stops working the day its owner stops being an employee.

	The punch endpoint already refuses a non-Active employee, so this is the
	second lock rather than the only one. It matters because a status that goes
	back to Active - a rehire, a correction, a script - would otherwise re-arm a
	secret that somebody left the company still holding.
	"""
	if doc.status == "Active":
		return
	if not frappe.db.exists("DocType", DEVICE):
		return
	for name in frappe.get_all(
		DEVICE,
		filters={"employee": doc.name, "status": ["in", ["Active", "Pending"]]},
		pluck="name",
	):
		frappe.db.set_value(DEVICE, name, "status", "Blocked", update_modified=False)
