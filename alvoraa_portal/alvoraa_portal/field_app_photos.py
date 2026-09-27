"""The check-in photo: the size rules, saving it, and deleting it when its time is up.

Moved out of `field_checkin.py` unchanged, so that file can hold the punch and
the phone's identity and nothing else. Every name here is imported back into
`field_checkin`, so `alvoraa_portal.field_checkin.purge_old_checkin_photos`
(which is what `hooks.py` names) still resolves to this code.
"""

import base64
import binascii

import frappe
from frappe.utils import add_to_date, now

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


def photo_retention_days():
	"""How long a check-in photo is kept. 0 means keep it for ever."""
	days = _setting(SETTING_RETENTION_DAYS, DEFAULT_RETENTION_DAYS)
	return max(0, days)


def attach_photo(checkin, photo):
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
