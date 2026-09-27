"""What the app holds about me (slice 013, step 6, US-28 / PRIV-12).

The setup notice promises: "Ask HR to see what was recorded about you." This
is the server side of that promise, for the person themselves: one call that
returns the caller's OWN phones, the codes HR made for them, the notice
versions they acknowledged and their last punches from the app. It exists so
that an access request under the DPDP Act can be answered from one place
instead of by somebody reading four tables.

Three rules, each with a test:

  * **Only your own.** There is no `employee` argument. The employee record is
    the one Frappe links to the signed-in user, full stop. An HR user gets
    their own records too, not anyone else's - HR's view of one employee is
    the Employee form's section (E12) and, later, a report.
  * **Nothing secret, and nothing that is not yours.** No hash, no code, no
    device secret, no block reason (PRIV-13: the reason is HR's), no workplace
    coordinates (PRIV-6). A punch's own position is in the answer, because it
    is the thing the notice says is recorded about you, and it is already on
    your own check-in record.
  * **Bounded.** Fifty rows of each kind, newest first, and ten calls an hour
    per user. Four list reads and one read of the notice store.

Where it surfaces: the employee portal's "What this app records" screen (the
redesign owns `www/hrms-employee.html`; this slice does not touch it). The
portal team calls `alvoraa_portal.field_app_records.my_field_app_records`
with a POST and no arguments.
"""

import frappe
from frappe import _

from alvoraa_portal import field_app_notice as notice
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_app_invite.alvoraa_app_invite import INVITE
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_notice_acknowledgement.alvoraa_notice_acknowledgement import (
	ACKNOWLEDGEMENT,
)
from alvoraa_portal.field_app_errors import desk_request, requires_field_app_plan
from alvoraa_portal.field_app_limits import SELF_KEY, _limited

DEVICE = "Alvoraa Field Device"

# How many of each kind. An access request is about what is held, and fifty
# newest rows of each plus the count of the rest says that without a dump.
ROW_LIMIT = 50

# Punches from the field app carry this device id (field_checkin.py).
FIELD_APP_DEVICE_ID = "alvoraa-field-app"

# Cancel reasons the person may read as they are: each is about their own code.
_CODE_OUTCOME = {
	"By HR": "cancelled_by_hr",
	"This is not me (on a phone)": "not_me",
	"Newer code made": "newer_code",
	"Employee left": "employee_left",
}


def _my_employees(user):
	"""The employee records linked to this sign-in. Usually one; a rehire
	can leave two. Never anyone else's."""
	if not user or user == "Guest":
		frappe.throw(_("Please sign in."), frappe.PermissionError)
	names = frappe.get_all("Employee", filters={"user_id": user}, pluck="name", limit=5)
	if not names:
		frappe.throw(
			_("No employee record is linked to your sign-in, so there is nothing to show. "
			  "Ask HR to link your employee record to your user."),
			frappe.PermissionError)
	return names


def _phones(employees):
	rows = frappe.get_all(
		DEVICE, filters={"employee": ["in", employees]},
		fields=["device_label", "platform", "join_method", "status", "registered_on",
		        "status_changed_on", "status_change_source", "last_seen", "checkin_count",
		        "app_version"],
		order_by="registered_on desc, creation desc", limit=ROW_LIMIT)
	return [{
		"device_label": r.device_label or "",
		"platform": r.platform or "",
		"join_method": r.join_method or "Web check-in page",
		"status": r.status,
		"joined_on": str(r.registered_on or ""),
		"status_changed_on": str(r.status_changed_on or ""),
		# HR, The employee, or System - who moved it, never why (PRIV-13).
		"status_changed_by": r.status_change_source or "",
		"last_punch": str(r.last_seen or ""),
		"punches_from_this_phone": int(r.checkin_count or 0),
		"app_version": r.app_version or "",
	} for r in rows]


def _codes(employees):
	rows = frappe.get_all(
		INVITE, filters={"employee": ["in", employees]},
		fields=["creation", "lifetime_hours", "status", "expires_at", "used_at",
		        "cancel_reason", "cancelled_at"],
		order_by="creation desc", limit=ROW_LIMIT)
	return [{
		"made_at": str(r.creation or ""),
		"lifetime_hours": int(r.lifetime_hours or 0),
		"expires_at": str(r.expires_at or ""),
		"status": r.status,
		"used_at": str(r.used_at or ""),
		"cancelled_at": str(r.cancelled_at or ""),
		"outcome": ("used" if r.status == "Used"
		            else _CODE_OUTCOME.get(r.cancel_reason, "cancelled") if r.status == "Cancelled"
		            else "ran_out" if r.status == "Ran out" else "waiting"),
	} for r in rows]


def _acknowledgements(employees):
	rows = frappe.get_all(
		ACKNOWLEDGEMENT, filters={"employee": ["in", employees]},
		fields=["notice_version", "acknowledged_at", "channel", "language", "app_version"],
		order_by="acknowledged_at desc, creation desc", limit=ROW_LIMIT)
	return [{
		"notice_version": r.notice_version,
		"acknowledged_at": str(r.acknowledged_at or ""),
		"channel": r.channel,
		"language": r.language or "",
		"app_version": r.app_version or "",
	} for r in rows]


def _punches(employees):
	"""The last punches from the app: what the notice says is recorded - the
	time, the position, and that a photo was taken. Never the photo itself
	here (it is on the person's own check-in record), and never the
	workplace's coordinates."""
	rows = frappe.get_all(
		"Employee Checkin",
		filters={"employee": ["in", employees], "device_id": FIELD_APP_DEVICE_ID},
		fields=["log_type", "time", "latitude", "longitude", "alvoraa_gps_accuracy",
		        "alvoraa_mock_location", "alvoraa_checkin_photo", "alvoraa_captured_at"],
		order_by="time desc", limit=ROW_LIMIT)
	return [{
		"log_type": r.log_type,
		"time": str(r.time or ""),
		"latitude": r.latitude,
		"longitude": r.longitude,
		"accuracy_m": r.alvoraa_gps_accuracy,
		"phone_said_fake_location": bool(r.alvoraa_mock_location),
		"has_photo": bool(r.alvoraa_checkin_photo),
		"phone_clock_time": str(r.alvoraa_captured_at or ""),
	} for r in rows]


def _notice_words(acks):
	"""The words of every version the person acknowledged, from the store."""
	out = {}
	for a in acks:
		v = a["notice_version"]
		if v and v not in out:
			out[v] = {"rows": notice.rows_for(v), "agree": notice.agree_wording(v)}
	return out


@frappe.whitelist(methods=["POST"])
@desk_request
@requires_field_app_plan
@_limited(SELF_KEY, "user", limit=10)
def my_field_app_records():
	"""Everything the field app holds about the signed-in employee. Read-only.

	No arguments on purpose: there is no way to name somebody else.
	"""
	user = frappe.session.user
	employees = _my_employees(user)
	phones = _phones(employees)
	codes = _codes(employees)
	acks = _acknowledgements(employees)
	punches = _punches(employees)
	return {
		"employee": employees[0],
		"row_limit": ROW_LIMIT,
		"phones": phones,
		"codes": codes,
		"acknowledgements": acks,
		"notice_words": _notice_words(acks),
		"punches": punches,
		"totals": {
			"phones": frappe.db.count(DEVICE, {"employee": ["in", employees]}),
			"codes": frappe.db.count(INVITE, {"employee": ["in", employees]}),
			"acknowledgements": frappe.db.count(ACKNOWLEDGEMENT, {"employee": ["in", employees]}),
			"punches": frappe.db.count("Employee Checkin", {
				"employee": ["in", employees], "device_id": FIELD_APP_DEVICE_ID}),
		},
		"how_to_get_more": _("HR can give you the full list and any photo from your "
		                     "employee record."),
	}
