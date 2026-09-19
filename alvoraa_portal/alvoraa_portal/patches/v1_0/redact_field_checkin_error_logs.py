"""Blank the photos, positions and names already copied into Error Logs.

Until slice 014, a field check-in request that failed - or only had its photo
rejected - left an Error Log row holding the request's fields (the photo as
text, latitude, longitude, the employee ID) and, for a crash, the value of every
local variable (the employee's name among them). The code no longer writes
them. This removes the copies already there.

The rows themselves are kept: when and where something failed is a useful
record, and part of the log history. Only the personal values go.

Safe to run twice: a redacted row has nothing left to match.
"""

import json
import re

import frappe

MASK = "********"

# Request fields the field check-in endpoints receive that are about a person.
# `token` is not here because Frappe already hid it.
PERSONAL_FIELDS = (
	"photo", "latitude", "longitude", "accuracy", "captured_at",
	"employee_id", "device_label", "platform",
)

# traceback_with_variables prints each local variable indented by six spaces
# ("      photo = 'data:...'"); code lines are indented by four. A long value can
# continue on further deeply indented lines, so those go too.
_VARIABLE_LINE = re.compile(r"^(?P<indent> {6,})(?P<name>[A-Za-z_]\w*) = .*$")
_CONTINUATION_LINE = re.compile(r"^ {6,}\S.*$")

BATCH = 500


def execute():
	if not frappe.db.exists("DocType", "Error Log"):
		return

	redacted = 0
	for name in _matching_error_logs():
		row = frappe.db.get_value("Error Log", name, ["error", "metadata"], as_dict=True)
		if not row:
			continue
		changes = redact(row.error, row.metadata)
		if changes:
			frappe.db.set_value("Error Log", name, changes, update_modified=False)
			redacted += 1

	frappe.db.commit()
	# A count only, never a value.
	frappe.logger("alvoraa_portal").info(
		f"alvoraa_portal: redacted personal data from {redacted} field check-in Error Log row(s)")


def _matching_error_logs():
	"""Names of Error Log rows that came from field check-in, in name order.

	Paged on `name >`, not on an offset. None of the three searches can use an
	index - they all start with a wildcard - so an offset page would re-scan the
	whole table for every page, and this runs inside a migrate, with the site at
	503. Walking the name forward reads each row once.
	"""
	names = []
	after = ""
	while True:
		batch = frappe.get_all(
			"Error Log",
			filters=[["name", ">", after]],
			or_filters=[
				["metadata", "like", "%alvoraa_portal.field_checkin%"],
				["error", "like", "%alvoraa_portal/field_checkin.py%"],
				["method", "like", "Field check-in%"],
			],
			pluck="name", order_by="name asc", limit_page_length=BATCH,
		)
		names.extend(batch)
		if len(batch) < BATCH:
			return names
		after = batch[-1]


def redact(error, metadata):
	"""The changed fields for one row, or an empty dict when nothing changes."""
	changes = {}

	new_metadata = _redact_metadata(metadata)
	if new_metadata != metadata:
		changes["metadata"] = new_metadata

	new_error = _redact_traceback(error)
	if new_error != error:
		changes["error"] = new_error

	return changes


def _redact_metadata(metadata):
	if not metadata:
		return metadata
	try:
		data = json.loads(metadata)
	except (TypeError, ValueError):
		# Not the JSON Frappe writes. Keep nothing we cannot read safely.
		return MASK
	if not isinstance(data, dict):
		return metadata
	form = data.get("form_dict")
	if isinstance(form, dict):
		for field in PERSONAL_FIELDS:
			if field in form and form[field] != MASK:
				form[field] = MASK
	out = json.dumps(data, indent=1, sort_keys=True, default=str)
	# Only rewrite when a value really changed, so a second run is a no-op.
	return out if out != _normalise(metadata) else metadata


def _normalise(metadata):
	try:
		return json.dumps(json.loads(metadata), indent=1, sort_keys=True, default=str)
	except (TypeError, ValueError):
		return metadata


def _redact_traceback(error):
	if not error:
		return error
	lines = []
	for line in error.split("\n"):
		match = _VARIABLE_LINE.match(line)
		if match:
			line = f"{match.group('indent')}{match.group('name')} = {MASK}"
		elif _CONTINUATION_LINE.match(line) and line.strip() != MASK:
			line = " " * 6 + MASK
		lines.append(line)
	return "\n".join(lines)
