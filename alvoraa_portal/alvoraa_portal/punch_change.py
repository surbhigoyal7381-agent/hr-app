# Copyright (c) 2026, Alvoraa and contributors
# For license information, please see license.txt

"""Slice 088c - a reason for every punch a person adds or changes, and a record of it.

Counsel's condition (24 Nov 2026): the employee must be told of every manual punch addition
and every direct edit, each with a reason code. Frappe records who, when and what, but never
why, and a plain insert leaves no Version row at all (see 00b-notice-scope-analysis.md).
So the reason is taken at the point of entry and copied into one append-only row,
`Alvoraa Punch Change`, which the monthly notice reads.

**It applies only while the organisation's notice switch is on** (`register_notice.NOTICE_SWITCH`).
Off, every handler here returns first: nothing is demanded and nothing is written. Nothing
before the switch is ever in the log, which is how "October is untouched" is kept without a
date column or a migration.

**Whose change counts.** A person's. Never a machine, never the employee's own punch:

- a biometric sync account (`field_app_access.files_as_machine`) - never judged by device_id;
- the phone app and the web check-in (no human session, or the employee's own session);
- the employee editing their own punch;
- an approved 087 punch fix, which writes under `frappe.flags.in_punch_fix_apply` and is
  already on the notice through its request.

The first thing the tests prove is that none of those is refused or logged.

**What counts as a change.** `time`, `log_type`, `employee` and `skip_auto_attendance`: the
four fields that decide what a punch means for the day. Shift, attendance link, photo and
position are not changes to a punch.

**Deleting** a punch by hand is refused while the switch is on (Surbhi, 25 Nov 2026): there is
no place to ask for a reason on a delete, and a vanished punch would be the quietest change of all.
"""

import frappe
from frappe import _
from frappe.utils import get_datetime, getdate, now_datetime

import hrms.alvoraa_hr_core.access as access

CHECKIN = "Employee Checkin"
LOG = "Alvoraa Punch Change"
#: The Select on the punch where a person gives the reason. Always blank once saved.
FIELD = "alvoraa_change_reason"
MATERIAL = ("time", "log_type", "employee", "skip_auto_attendance")

FLAG = "in_punch_change"
_STASH = "punch_change_pending"


# ── is this a person's change, in an organisation that asked for notices? ────

def _is_a_persons_change(doc):
	"""Cheapest tests first: a punch from a machine or a phone must cost almost nothing."""
	if frappe.flags.in_punch_fix_apply or frappe.flags.in_install or frappe.flags.in_migrate:
		return False
	user = frappe.session.user
	if not user or user == "Guest":
		return False
	from alvoraa_portal.register_notice import notices_are_on

	company = frappe.get_cached_value("Employee", doc.employee, "company") if doc.employee else None
	if not company or not notices_are_on(company):
		return False
	if frappe.get_cached_value("Employee", doc.employee, "user_id") == user:
		return False                                   # the employee's own act
	from alvoraa_portal.field_app_access import files_as_machine

	return not files_as_machine(user)


def _moved(doc, before):
	"""True when a material field differs from the saved copy. A new punch always counts."""
	if not before:
		return True
	return any(str(doc.get(f) or "") != str(before.get(f) or "") for f in MATERIAL)


# ── the handlers ─────────────────────────────────────────────────────────────

def require_reason(doc, method=None):
	"""Employee Checkin validate. A person's change needs a reason; everything else passes.

	The field is blanked on every path so a reason never sits on the punch and never gets
	reused by the next edit. The chosen reason is carried to `write_log` on the document's own
	flags, which only code on this server can set."""
	reason = doc.get(FIELD)
	doc.set(FIELD, None)
	before = None if doc.is_new() else doc.get_doc_before_save()
	if not _moved(doc, before) or not _is_a_persons_change(doc):
		return
	if not reason:
		frappe.throw(_("Pick a reason for this change. It is printed on the employee's monthly "
		               "notice. If you are importing punches or calling the API, fill in "
		               "'Reason For This Change' ({0}) on every row.").format(FIELD))
	doc.flags[_STASH] = {"reason": reason, "what": _sentence(doc, before)}


def write_log(doc, method=None):
	"""Employee Checkin on_update (after the punch is written, in the same transaction).

	Runs for an insert too: `in_insert` is set while Frappe runs on_update on a new document."""
	pending = doc.flags.pop(_STASH, None)
	if not pending:
		return
	frappe.flags[FLAG] = True
	try:
		frappe.get_doc({
			"doctype": LOG,
			"punch": doc.name,
			"employee": doc.employee,
			"company": frappe.get_cached_value("Employee", doc.employee, "company"),
			"day": getdate(doc.time),
			"kind": "Added" if doc.flags.in_insert else "Changed",
			"reason_code": pending["reason"],
			"what": pending["what"],
			"changed_by": frappe.session.user,
			"changed_on": now_datetime(),
		}).insert(ignore_permissions=True)
	finally:
		frappe.flags[FLAG] = False
	access.security_logger().info("punch_change logged punch=%s user=%s", doc.name, frappe.session.user)


def refuse_delete(doc, method=None):
	"""Employee Checkin on_trash. A person may not delete a punch while notices are on."""
	if not _is_a_persons_change(doc):
		return
	frappe.throw(_("A punch cannot be deleted while change notices are on. To stop it counting, "
	               "open it, tick 'Skip Auto Attendance' and pick a reason. The employee is told."))


# ── the words the paper uses (plain English, never translated: see register_notice.WHAT) ──

def _hm(value):
	return str(get_datetime(value))[11:16]


def _when(value, relative_to=None):
	"""The time, with its date only when the date differs from `relative_to`."""
	d = get_datetime(value)
	if relative_to and getdate(d) == getdate(relative_to):
		return d.strftime("%H:%M")
	return "%d %s %s" % (d.day, d.strftime("%b"), d.strftime("%H:%M"))


def _sentence(doc, before):
	if not before:
		return "Punch at %s added" % _hm(doc.time)
	bits = []
	if get_datetime(doc.time) != get_datetime(before.time):
		bits.append("Punch moved from %s to %s" % (_when(before.time, doc.time), _when(doc.time, before.time)))
	label = {"IN": "In", "OUT": "Out"}
	if (doc.log_type or "") != (before.log_type or ""):
		bits.append("Punch type changed from %s to %s" % (
			label.get(before.log_type, "blank"), label.get(doc.log_type, "blank")))
	if bool(doc.skip_auto_attendance) != bool(before.skip_auto_attendance):
		bits.append("Punch at %s %s" % (_hm(doc.time), "not counted" if doc.skip_auto_attendance
		                                else "counted again"))
	if doc.employee != before.employee:
		bits.append("Punch moved to another person")
	return "; ".join(bits)


# ── install ──────────────────────────────────────────────────────────────────

def after_migrate():
	"""The Select on Employee Checkin and one index on the log.

	In both hook lists, because a site built with `bench install-app` never runs a migrate.
	The options are read from the log's own field, so there is one list and the two cannot drift."""
	if not (frappe.db.exists("DocType", CHECKIN) and frappe.db.exists("DocType", LOG)):
		return False
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	options = frappe.get_meta(LOG).get_field("reason_code").options
	create_custom_fields({CHECKIN: [{
		"fieldname": FIELD, "fieldtype": "Select", "label": "Reason For This Change",
		"options": "\n" + options, "insert_after": "skip_auto_attendance",
		"no_copy": 1, "print_hide": 1,
		"description": "Needed when you add or change a punch for somebody else, if your "
		               "organisation prints change notices. It is printed on the employee's "
		               "notice. Always blank once saved.",
	}]})
	try:
		frappe.db.add_index(LOG, ["employee", "day"], index_name="employee_day")
	except Exception:
		pass
	return True
