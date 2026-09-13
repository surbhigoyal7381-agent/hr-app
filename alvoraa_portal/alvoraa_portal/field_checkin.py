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

import base64
import binascii
import hashlib
import secrets

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

# Photos are evidence for a supervisor to glance at, not portraits. The phone
# downscales to about 80 KB before sending; this is the backstop, set from the
# storage arithmetic rather than guessed: PPJ is roughly 400 people punching
# twice a day, so 400 KB a photo is about 4 GB a year, and the 2 MB this
# started at would have been 500 GB. Private files are also tarred into every
# `bench backup --with-files`, so the number is paid for more than once.
MAX_PHOTO_BYTES = 400 * 1024

# Base64 costs about a third on top, plus room for the data: prefix. Checked
# against the STRING before decoding: decoding first means a 200 MB payload is
# expanded in the worker's memory before we get to say we did not want it.
MAX_PHOTO_B64_CHARS = int(MAX_PHOTO_BYTES * 4 / 3) + 128

# What a JPEG starts with. Cheap proof that what arrived is an image rather
# than a zip, a script, or a file named to look like one.
JPEG_MAGIC = b"\xff\xd8\xff"

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
		frappe.throw(_("This phone is not set up. Please register it again."),
		             frappe.AuthenticationError)

	device = frappe.get_doc(DEVICE, name)

	if device.status == "Blocked":
		frappe.throw(_("This phone has been blocked. Please speak to HR."),
		             frappe.AuthenticationError)
	if device.status == "Pending":
		frappe.throw(
			_("This phone is waiting for HR to approve it. You will be able to "
			  "check in as soon as they do."),
			frappe.AuthenticationError)

	return device


# ── registration: the one-time setup on the phone ────────────────────────────

@frappe.whitelist(allow_guest=True, methods=["POST"])
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
		"message": _("Thanks. HR needs to approve this phone before you can "
		             "check in. You only have to do this once."),
	}

	if not emp:
		return answer

	token = secrets.token_urlsafe(32)

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


def _attach_photo(checkin, photo):
	"""Save the selfie as a PRIVATE file on the check-in.

	Private is the whole point. face_app wrote these into `/public/files`, where
	anyone with the address could download every employee's face without
	logging in. A private file is served only to somebody the permission system
	already lets read the check-in.

	A photo that will not decode loses the photo, not the punch: a guard who
	turned up should still be marked present.
	"""
	# Length of the STRING, before any decoding. This is the order that matters:
	# the other way round, an oversized payload is fully expanded in memory
	# first and the size check arrives too late to have prevented anything.
	if not isinstance(photo, str) or len(photo) > MAX_PHOTO_B64_CHARS:
		frappe.log_error(f"Field check-in photo rejected on size for {checkin.name}",
		                 "Field check-in")
		return

	try:
		raw = photo.split(",", 1)[1] if photo.startswith("data:") else photo
		blob = base64.b64decode(raw, validate=True)
	except (binascii.Error, ValueError, IndexError):
		frappe.log_error(f"Field check-in photo could not be decoded for {checkin.name}",
		                 "Field check-in")
		return

	if len(blob) > MAX_PHOTO_BYTES or not blob.startswith(JPEG_MAGIC):
		frappe.log_error(f"Field check-in photo rejected for {checkin.name}",
		                 "Field check-in")
		return

	try:
		f = frappe.get_doc({
			"doctype": "File",
			"file_name": f"checkin-{checkin.name}.jpg",
			"attached_to_doctype": "Employee Checkin",
			"attached_to_name": checkin.name,
			"attached_to_field": "alvoraa_checkin_photo",
			"is_private": 1,
			"content": blob,
		}).insert(ignore_permissions=True)
		checkin.db_set("alvoraa_checkin_photo", f.file_url, update_modified=False)
	except Exception:
		# Never let the photo take the attendance record down with it: a guard
		# who turned up should be marked present even if the picture failed.
		frappe.log_error(f"Field check-in photo failed for {checkin.name}",
		                 "Field check-in")


# ── what the phone shows ─────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True, methods=["POST"])
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


# ── settings the organisation owns ───────────────────────────────────────────
#
# Kept in Frappe's Default store, which is what get_org_setting/set_org_setting
# in hr_api.py already read and write, so the ESS Org Settings screen can edit
# them without a second mechanism. Each has a default that is safe when nobody
# has ever opened that screen - which is every tenant, on the day it is created.

SETTING_RETENTION_DAYS = "alvoraa_checkin_photo_retention_days"

# 90 days: long enough to settle a disputed punch or a payroll query, short
# enough that a leak years later cannot expose faces from years ago. Security
# recommended it; the organisation can change it.
DEFAULT_RETENTION_DAYS = 90


def _setting(key, default):
	"""Read an org setting, falling back to the default on anything unusable.

	A missing key, an empty string, or somebody typing "ninety" must never stop
	attendance working or start deleting the wrong thing.
	"""
	try:
		raw = frappe.db.get_default(key)
	except Exception:
		return default
	if raw in (None, ""):
		return default
	try:
		return int(str(raw).strip())
	except (TypeError, ValueError):
		return default


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


def photo_retention_days():
	"""How long a check-in photo is kept. 0 means keep it for ever."""
	days = _setting(SETTING_RETENTION_DAYS, DEFAULT_RETENTION_DAYS)
	return max(0, days)


# ── deleting photos when their time is up ────────────────────────────────────

def purge_old_checkin_photos():
	"""Delete check-in photos older than the retention period. Runs daily.

	Only the PHOTO goes. The attendance record, the time and the coordinates
	stay, because they are the record of work done and pay owed. A face is
	evidence for a short window; the punch is a business record.

	Three things this deliberately does:

	  * **0 means never.** An organisation that has to keep photos - a dispute,
	    an audit, a jurisdiction we have not met yet - sets 0 and nothing is
	    deleted. It is not a hidden "delete everything" value.
	  * **Legal hold wins.** A check-in flagged for hold is skipped however old
	    it is. Deleting evidence somebody has asked you to preserve is worse
	    than keeping it too long.
	  * **It says what it did.** The count goes to the log, so "are photos
	    actually being deleted" has an answer that is not "look in the files
	    folder and guess".
	"""
	days = photo_retention_days()
	if days <= 0:
		return {"skipped": "retention disabled (0 = keep for ever)"}

	if not frappe.db.has_column("Employee Checkin", "alvoraa_checkin_photo"):
		return {"skipped": "field check-in is not installed on this site"}

	cutoff = add_to_date(now(), days=-days)

	filters = {
		"alvoraa_checkin_photo": ["is", "set"],
		"time": ["<", cutoff],
	}
	if frappe.db.has_column("Employee Checkin", "alvoraa_legal_hold"):
		filters["alvoraa_legal_hold"] = 0

	rows = frappe.get_all("Employee Checkin", filters=filters,
	                      fields=["name", "alvoraa_checkin_photo"], limit=2000)

	deleted = failed = 0
	for row in rows:
		try:
			for f in frappe.get_all("File", filters={
				"attached_to_doctype": "Employee Checkin",
				"attached_to_name": row.name,
			}, pluck="name"):
				frappe.delete_doc("File", f, force=True, ignore_permissions=True,
				                  delete_permanently=True)
			frappe.db.set_value("Employee Checkin", row.name,
			                    "alvoraa_checkin_photo", None, update_modified=False)
			deleted += 1
		except Exception:
			failed += 1
			frappe.log_error(f"Could not purge the photo on {row.name}",
			                 "Field check-in retention")

	frappe.db.commit()
	if deleted or failed:
		frappe.logger("alvoraa").info(
			f"check-in photo purge: {deleted} deleted, {failed} failed, "
			f"older than {days} days")
	return {"retention_days": days, "deleted": deleted, "failed": failed,
	        "considered": len(rows)}


# ── who may see a punch, and its photo ───────────────────────────────────────
#
# The spec found NO row filter on Employee Checkin anywhere in Frappe HR or in
# this app. The `Employee` role holds plain read on it, so the only thing
# standing between a curious colleague and everybody's faces and coordinates was
# whether ERPNext happened to create a User Permission row for each user. That
# is a setting, not a control: one missing row and the whole tenant is readable.
#
# Two hooks, because they answer different questions. The query condition filters
# LISTS and reports; has_permission guards opening ONE record by name. A list
# filter alone leaves /app/employee-checkin/EMP-CKIN-00042 wide open.

_HR_ROLES = {"HR Manager", "HR User", "System Manager", "Administrator"}


def _viewer(user=None):
	"""(is_hr, employee_id) for the user asking."""
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	is_hr = bool(_HR_ROLES & roles)
	emp = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
	return is_hr, emp


def checkin_query_conditions(user=None):
	"""Row filter for the Employee Checkin list.

	HR sees everything. A manager sees their own and their direct reports'. An
	employee sees their own. Anybody with no employee record sees nothing, which
	is deliberately stricter than "sees everything" - the failure mode of a
	permission rule should be silence, not disclosure.
	"""
	is_hr, emp = _viewer(user)
	if is_hr:
		return ""
	if not emp:
		return "1=0"

	esc = frappe.db.escape
	allowed = [esc(emp)]
	# A line manager legitimately needs their own team's attendance. Direct
	# reports only - not the whole tree - because that is what a manager acts on
	# and it keeps the list from quietly widening as an org chart deepens.
	allowed += [esc(e) for e in frappe.get_all(
		"Employee", filters={"reports_to": emp, "status": "Active"}, pluck="name")]

	return "`tabEmployee Checkin`.employee in ({0})".format(", ".join(allowed))


def checkin_has_permission(doc, user=None, permission_type=None):
	"""Guards ONE record, opened by name or through the API."""
	is_hr, emp = _viewer(user)
	if is_hr:
		return True
	if not emp:
		return False
	if doc.employee == emp:
		return True
	return bool(frappe.db.exists("Employee", {
		"name": doc.employee, "reports_to": emp, "status": "Active"}))


# ── who looked at a face, and when ───────────────────────────────────────────

ACCESS_LOG = "Alvoraa Photo Access Log"


def log_photo_view(doc, method=None):
	"""Record that somebody opened a check-in carrying a photo.

	A face is the most sensitive thing this feature stores, and "who has looked
	at my photo" is a question an employee is entitled to ask. Without this the
	only honest answer is "we do not know".

	Deliberately narrow, because an access log that records everything is one
	nobody reads:
	  * only check-ins that actually HAVE a photo
	  * never the employee looking at their own
	  * one row per viewer per record per day, not one per page refresh
	"""
	if not doc.get("alvoraa_checkin_photo"):
		return
	if not frappe.db.exists("DocType", ACCESS_LOG):
		return

	user = frappe.session.user
	if user in ("Guest", "Administrator"):
		return

	is_hr, emp = _viewer(user)
	if emp and doc.employee == emp:
		return

	try:
		if frappe.db.exists(ACCESS_LOG, {
			"checkin": doc.name, "viewed_by": user, "viewed_on_date": today()}):
			return
		frappe.get_doc({
			"doctype": ACCESS_LOG,
			"checkin": doc.name,
			"employee": doc.employee,
			"employee_name": doc.employee_name,
			"viewed_by": user,
			"viewed_at": now(),
			"viewed_on_date": today(),
		}).insert(ignore_permissions=True)
		frappe.db.commit()
	except Exception:
		# Never let the log stop somebody doing their job.
		frappe.log_error(f"Could not record photo access on {doc.name}",
		                 "Field check-in access log")


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


# ── what makes it an installed app, not a web page ───────────────────────────
#
# These three are served from endpoints rather than as files because Frappe
# refuses to serve .js and .json out of www/, and because all three have to
# carry the TENANT's name and colour - a static file could only ever be one
# customer's. The icon is drawn per request for the same reason.

def _brand():
	"""Tenant name and a contrast-safe brand colour, for the icon and manifest."""
	from alvoraa_portal.tenant_context import DEFAULTS, get_branding
	b = get_branding()
	colour = b.get("primary_color") or DEFAULTS["primary_color"]
	if not (isinstance(colour, str) and colour.startswith("#") and len(colour) in (4, 7)):
		colour = DEFAULTS["primary_color"]
	if len(colour) == 4:
		colour = "#" + "".join(c * 2 for c in colour[1:])
	return (b.get("tenant_name") or "Attendance"), colour


def _darker(hex_colour, factor=0.72):
	"""A deeper shade for the icon ground, dark enough for a white tick on it.

	A fixed multiplier is not enough on its own. A tenant whose brand is white or
	a pale yellow would get 0.72 of a very light colour, which is still light,
	and the white tick would vanish. So it darkens further until white actually
	passes WCAG AA against it - the same rule brand_color.html applies on screen,
	applied here because this icon is drawn on the server.
	"""
	h = hex_colour.lstrip("#")
	rgb = [max(0, min(255, int(int(h[i:i + 2], 16) * factor))) for i in (0, 2, 4)]

	def contrast_with_white(c):
		def ch(v):
			v /= 255
			return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
		lum = 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])
		return 1.05 / (lum + 0.05)

	for _ in range(30):
		if contrast_with_white(rgb) >= 4.5:
			break
		rgb = [max(0, int(v * 0.88)) for v in rgb]

	return tuple(rgb)


@frappe.whitelist(allow_guest=True, methods=["GET"])
def app_icon(size=192):
	"""The home-screen icon, drawn in the tenant's own colour.

	A PNG rather than an SVG: Chrome is fussy about which formats it will accept
	for installation, and a PNG at 192 and 512 is the combination it documents.
	"""
	from io import BytesIO

	from PIL import Image, ImageDraw

	try:
		size = max(48, min(1024, cint(size) or 192))
	except Exception:
		size = 192

	_, colour = _brand()
	ground = _darker(colour)

	img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
	d = ImageDraw.Draw(img)
	r = int(size * 0.19)
	d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=ground + (255,))
	# A tick, drawn rather than shipped, so it scales to any requested size.
	w = max(2, int(size * 0.085))
	d.line([(size * 0.30, size * 0.52), (size * 0.44, size * 0.66),
	        (size * 0.71, size * 0.36)],
	       fill=(255, 255, 255, 255), width=w, joint="curve")

	buf = BytesIO()
	img.save(buf, format="PNG", optimize=True)

	frappe.local.response.filename = f"icon-{size}.png"
	frappe.local.response.filecontent = buf.getvalue()
	frappe.local.response.type = "download"
	frappe.local.response.display_content_as = "inline"


@frappe.whitelist(allow_guest=True, methods=["GET"])
def manifest():
	"""The web app manifest. Without a real one the page cannot install.

	It was previously built in the browser as a blob: URL, which looks right in
	the code and never installs: Chrome will not accept a blob manifest.
	"""
	name, colour = _brand()
	deep = "#%02x%02x%02x" % _darker(colour)
	base = "/api/method/alvoraa_portal.field_checkin.app_icon?size="

	frappe.local.response.type = "json"
	frappe.local.response.http_status_code = 200
	return {
		"name": name,
		"short_name": name[:12],
		"description": "Mark your attendance with a photo and your location.",
		"start_url": "/checkin",
		"scope": "/checkin",
		"display": "standalone",
		"orientation": "portrait",
		"background_color": "#F8F6F3",
		"theme_color": deep,
		"icons": [
			{"src": base + "192", "sizes": "192x192", "type": "image/png", "purpose": "any"},
			{"src": base + "512", "sizes": "512x512", "type": "image/png", "purpose": "any"},
			{"src": base + "512", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
		],
	}


# Deliberately tiny. Its only job today is to exist with a fetch handler, which
# is what lets Chrome offer to install the page. The offline queue (brief P11)
# would live here later; it is NOT implemented, and this must not pretend to
# cache anything, because a stale cached app is worse than no app.
_SERVICE_WORKER = """
self.addEventListener('install', function (e) { self.skipWaiting(); });
self.addEventListener('activate', function (e) { e.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', function (e) { return; });
"""


@frappe.whitelist(allow_guest=True, methods=["GET"])
def service_worker():
	"""Served from here so it can carry Service-Worker-Allowed.

	A worker's scope cannot be wider than the folder it is served from unless
	that header says so - and this one is served from /api/method/, which would
	otherwise be able to control nothing that matters.
	"""
	# A werkzeug Response, returned directly, because Frappe's own response types
	# cannot express what a service worker needs. `binary` hardcodes
	# application/octet-stream, and a browser REFUSES to register a worker that
	# is not served as JavaScript - so the first version of this registered
	# nothing at all and failed silently. Frappe's handler passes a Response
	# through untouched, which is the supported way to set both headers.
	from werkzeug.wrappers import Response

	return Response(
		_SERVICE_WORKER,
		mimetype="application/javascript",
		headers={
			# Without this the worker's scope could only be /api/method/, which
			# controls nothing worth controlling.
			"Service-Worker-Allowed": "/",
			# Never cache the worker itself. nginx serves /assets/ as immutable
			# for 30 days, and a worker frozen for a month is a bug that cannot
			# be shipped a fix.
			"Cache-Control": "no-cache, no-store, must-revalidate",
		},
	)
