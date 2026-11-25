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

**What counts as a change.** `time`, `log_type`, `skip_auto_attendance`, and the shift tag
(`shift`, `shift_start`, `shift_end`: all three, because the engine reads all three, `held_day.py`): the fields that decide what a punch means for the day and WHICH
day it counts on (ALV-402: the day is the date of `shift_start`). The attendance link, photo
and position are not changes to a punch. **Moving a punch to another person is refused**
(Surbhi, 25 Nov): HR adds the punch to the right person and sets the wrong one aside, which
is notified on both sides.

**Why the demand runs in `before_validate`, and what that costs.** `ignore_validate` skips
`validate` and nothing else, and one repair script already sets it on a punch
(`alv291_attendance_fix.retag`). `before_validate` runs even then (`document.py`
`run_before_save_methods`), the same reason `field_app_access.guard_shift_type_change` uses
it. The cost: on an INSERT the shift tag is not set yet at that point (Frappe HR's own
`validate` sets it), so an insert is judged on being new, not on its shift; and the day printed
on the notice is worked out later, in `write_log`, from the saved punch. An edit that only
re-tags the shift (the repair script) IS caught, because it changes `shift`/`shift_start` on
the document before it is saved.

**Deleting** a punch by hand is refused while the switch is on (Surbhi, 25 Nov 2026): there is
no place to ask for a reason on a delete, and a vanished punch would be the quietest change of all.
"""

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, getdate, now_datetime

import hrms.alvoraa_hr_core.access as access

CHECKIN = "Employee Checkin"
LOG = "Alvoraa Punch Change"
#: The Select on the punch where a person gives the reason. Always blank once saved.
FIELD = "alvoraa_change_reason"
MATERIAL = ("time", "log_type", "skip_auto_attendance", "shift", "shift_start", "shift_end")

FLAG = "in_punch_change"
_STASH = "punch_change_pending"


# ── is this a person's change, in an organisation that asked for notices? ────

def _is_a_persons_change(employee):
	"""Cheapest tests first: a punch from a machine or a phone must cost almost nothing."""
	if frappe.flags.in_punch_fix_apply or frappe.flags.in_install or frappe.flags.in_migrate:
		return False
	user = frappe.session.user
	if not user or user == "Guest":
		return False
	from alvoraa_portal.register_notice import notices_are_on

	company = frappe.get_cached_value("Employee", employee, "company") if employee else None
	if not company or not notices_are_on(company):
		return False
	if frappe.get_cached_value("Employee", employee, "user_id") == user:
		return False                                   # the employee's own act
	from alvoraa_portal.field_app_access import files_as_machine

	return not files_as_machine(user)


def _moved(doc, before):
	"""True when a material field differs from the saved copy. A new punch always counts."""
	if not before:
		return True
	# Cast on both sides (`get_value`): a REST call or an import sends "0" and "2026-11-20 14:00",
	# the database holds 0 and a datetime with seconds, and a raw comparison calls those a change.
	return any((doc.get_value(f) or "") != (before.get_value(f) or "") for f in MATERIAL)


def _valid_reason(reason):
	"""The reason has to be one of the log's own options. Frappe skips the Select check for the
	whole of a Data Import (`flags.in_import`, `base_document.py`), so without this a spreadsheet
	could write any sentence into the record, and the record can never be corrected."""
	return reason in (frappe.get_meta(LOG).get_field("reason_code").options or "").split("\n")


def _refuse(message, rule, doc):
	"""A refusal this slice makes, written down like every other one (`log_refusal`) and then
	raised as an ordinary validation message the person can act on."""
	access.log_refusal(rule, "Employee Checkin " + rule, CHECKIN, doc.name)
	frappe.throw(message)


# ── the handlers ─────────────────────────────────────────────────────────────

def require_reason(doc, method=None):
	"""Employee Checkin before_validate. A person's change needs a reason; everything else passes.

	The field is blanked on every path so a reason never sits on the punch and never gets
	reused by the next edit. The chosen reason is carried to `write_log` on the document's own
	flags, which only code on this server can set."""
	reason = doc.get(FIELD)
	doc.set(FIELD, None)
	before = None if doc.is_new() else doc.get_doc_before_save()
	if before and doc.employee != before.employee:
		# Refused, not logged: only the gaining person would be told. Either side counts.
		if _is_a_persons_change(before.employee) or _is_a_persons_change(doc.employee):
			_refuse(_("A punch cannot be moved to another person while change notices are on. Add "
			          "the punch to the right person, then open this one, tick 'Skip Auto "
			          "Attendance' and pick a reason. Both people are told."),
			        "088c-move", doc)
		return
	if not _moved(doc, before) or not _is_a_persons_change(doc.employee):
		return
	if not reason:
		if (frappe.form_dict.get("cmd") or "").endswith("bulk_fetch_shift"):
			# The Desk list action. It re-tags every row it is given, so every row needs a reason,
			# and the action has nowhere to ask for one.
			_refuse(_("'Fetch Shift' is not available while change notices are on. It re-tags a "
			          "punch's shift, which can move it to another day, and every such change "
			          "needs a reason that is printed on the employee's notice. Open the punch, "
			          "correct it and pick a reason."), "088c-reason", doc)
		_refuse(_("Pick a reason for this change. It is printed on the employee's monthly "
		          "notice. (If you are importing punches or calling the API, put the reason in "
		          "the 'Reason For This Change' column, {0}, on every row.)").format(FIELD),
		        "088c-reason", doc)
	if not _valid_reason(reason):
		_refuse(_("That is not one of the reasons on the list. Pick one from the list."),
		        "088c-reason-list", doc)
	# An addition's sentence is written in `write_log`, once the working day is known.
	doc.flags[_STASH] = {"reason": reason, "what": _sentence(doc, before) if before else None}


def write_log(doc, method=None):
	"""Employee Checkin on_update (after the punch is written, in the same transaction).

	Runs for an insert too: `in_insert` is set while Frappe runs on_update on a new document."""
	pending = doc.flags.pop(_STASH, None)
	if not pending:
		return
	if not _valid_reason(pending["reason"]):
		# The last line of defence: the same check as above, because this is the row that
		# is evidence for ever.
		_refuse(_("That is not one of the reasons on the list. Pick one from the list."),
		        "088c-reason-list", doc)
	from alvoraa_portal.payroll_rules_apply import shift_day

	day = getdate(shift_day(doc))
	what = pending["what"] or "Punch at %s added" % _when(doc.time, day)   # date shown when it is not the shift's day
	frappe.flags[FLAG] = True
	try:
		frappe.get_doc({
			"doctype": LOG,
			"punch": doc.name,
			"employee": doc.employee,
			# The working day (ALV-402: the date the punch's SHIFT started), the one rule the
			# engine, the reports and the screens use. NOT the calendar date: a 00:30 punch
			# on a 20:30 shift belongs to the evening before.
			"day": day,
			"reason_code": pending["reason"],
			"what": what,
			"changed_by": frappe.session.user,
			"changed_on": now_datetime(),
		}).insert(ignore_permissions=True)
	finally:
		frappe.flags[FLAG] = False
	access.security_logger().info("punch_change logged punch=%s user=%s", doc.name, frappe.session.user)


def refuse_delete(doc, method=None):
	"""Employee Checkin on_trash. A person may not delete a punch while notices are on."""
	if not _is_a_persons_change(doc.employee):
		return
	_refuse(_("A punch cannot be deleted while change notices are on. To stop it counting, "
	          "open it, tick 'Skip Auto Attendance' and pick a reason. The employee is told."),
	        "088c-delete", doc)


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
	if cint(doc.get_value("skip_auto_attendance")) != cint(before.get_value("skip_auto_attendance")):
		bits.append("Punch at %s %s" % (_hm(doc.time), "not counted" if cint(doc.get_value("skip_auto_attendance"))
		                                else "counted again"))
	if doc.shift_start and str(get_datetime(doc.shift_start)) != str(get_datetime(before.shift_start or doc.shift_start)):
		d = get_datetime(doc.shift_start)
		bits.append("Punch moved to the %d %s shift" % (d.day, d.strftime("%b")))
	elif (doc.shift or "") != (before.shift or "") or doc.get_value("shift_end") != before.get_value("shift_end"):
		bits.append("Punch shift changed")
	# Never empty: the record requires a sentence, and an empty one would fail the punch save.
	return "; ".join(bits) or "Punch changed"


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
