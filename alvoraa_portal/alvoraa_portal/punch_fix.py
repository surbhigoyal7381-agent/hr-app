"""Punch fixes (slice 087): attendance follows the punches.

A request that carries a missing time, or a list of punches to set aside, is a
**punch fix**. HR approves it through `attendance_correction.decide` and nothing
else. The approval adds ONE real Employee Checkin as the approver, sets the
ticked punches aside (they stay on record, marked, and stop counting), judges the
day again from the real punches, writes the day, and keeps a before and after.
All of it is one transaction: any error undoes all of it.

Everything here is a `doc_events` hook, a Custom Field, a whitelisted endpoint or
the small subclass in `overrides/attendance_request.py`. No vendored file is edited.
The order of the file: fields, the day, the punches, raising, the card, approving,
the marks on a punch.
"""

import hashlib
import re
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, get_datetime, get_first_day, get_last_day, getdate, now_datetime, nowdate

import alvoraa_portal.held_day as held_day
import hrms.alvoraa_hr_core.access as access
from alvoraa_portal.payroll_rules import DUPLICATE_PUNCH_MINUTES
from alvoraa_portal.payroll_rules_apply import shift_day  # the one working-day rule (ALV-402)

REQUEST = "Attendance Request"
ATTENDANCE = "Attendance"
CHECKIN = "Employee Checkin"

ADDED = "alvoraa_fix_added_request"
ASIDE = "alvoraa_fix_aside_request"
ASIDE_BY = "alvoraa_fix_aside_by"
ASIDE_ON = "alvoraa_fix_aside_on"
MARKS = (ADDED, ASIDE, ASIDE_BY, ASIDE_ON)
HR_ROLES = {"HR User", "HR Manager", "System Manager"}

SERVER_OWNED = ("alvoraa_needs_confirm", "alvoraa_confirmed_by", "alvoraa_confirmed_on", "alvoraa_replaces",
                "alvoraa_disputed_by", "alvoraa_disputed_on", "alvoraa_dispute_reason",
                "alvoraa_undone_by", "alvoraa_undone_on", "alvoraa_undone_reason")


# What a Confirm vouches for: the day, the time and kind, the punches to set aside, the words.
CONFIRMED_CONTENT = ("employee", "from_date", "to_date", "alvoraa_missing_time", "alvoraa_missing_log", "alvoraa_set_aside",
                     "explanation", "reason", "half_day", "half_day_date")

FIELDS = {
	CHECKIN: [
		{"fieldname": ADDED, "fieldtype": "Link", "options": REQUEST, "read_only": 1,
		 "label": "Added By Fix Request", "insert_after": "skip_auto_attendance"},
		{"fieldname": ASIDE, "fieldtype": "Link", "options": REQUEST, "read_only": 1,
		 "label": "Set Aside By Fix Request", "insert_after": ADDED},
		{"fieldname": ASIDE_BY, "fieldtype": "Link", "options": "User", "read_only": 1,
		 "label": "Set Aside By", "insert_after": ASIDE},
		{"fieldname": ASIDE_ON, "fieldtype": "Datetime", "read_only": 1,
		 "label": "Set Aside On", "insert_after": ASIDE_BY},
	],
	REQUEST: [
		{"fieldname": "alvoraa_set_aside", "fieldtype": "Small Text",
		 "label": "Punches To Set Aside", "insert_after": "alvoraa_missing_log"},
		{"fieldname": "alvoraa_for_held_day", "fieldtype": "Check", "read_only": 1, "default": "0",
		 "label": "Raised For A Held Day", "insert_after": "alvoraa_set_aside"},
		{"fieldname": "alvoraa_fix_before", "fieldtype": "Small Text", "read_only": 1,
		 "label": "Day Before The Fix", "insert_after": "alvoraa_for_held_day"},
		{"fieldname": "alvoraa_fix_after", "fieldtype": "Small Text", "read_only": 1,
		 "label": "Day After The Fix", "insert_after": "alvoraa_fix_before"},
		# ALV-419: a request somebody else filed for the employee waits for their Confirm.
		{"fieldname": "alvoraa_needs_confirm", "fieldtype": "Check", "read_only": 1, "default": "0",
		 "label": "Needs The Employee's Confirm", "insert_after": "alvoraa_fix_after"},
		{"fieldname": "alvoraa_confirmed_by", "fieldtype": "Link", "options": "User", "read_only": 1,
		 "label": "Confirmed By", "insert_after": "alvoraa_needs_confirm"},
		{"fieldname": "alvoraa_confirmed_on", "fieldtype": "Datetime", "read_only": 1,
		 "label": "Confirmed On", "insert_after": "alvoraa_confirmed_by"},
		# V4: the employee's own request that replaces one filed for them ("Not right" with a time).
		{"fieldname": "alvoraa_replaces", "fieldtype": "Link", "options": REQUEST, "read_only": 1,
		 "label": "Replaces Request", "insert_after": "alvoraa_confirmed_on"},
		# V5 D-1: after HR approved a change, "Not right" without a time (or for a cut) is a dispute: the
		# employee's reason goes to HR and the day stays as approved.
		{"fieldname": "alvoraa_disputed_by", "fieldtype": "Link", "options": "User", "read_only": 1,
		 "label": "Disputed By", "insert_after": "alvoraa_replaces"},
		{"fieldname": "alvoraa_disputed_on", "fieldtype": "Datetime", "read_only": 1,
		 "label": "Disputed On", "insert_after": "alvoraa_disputed_by"},
		{"fieldname": "alvoraa_dispute_reason", "fieldtype": "Small Text", "read_only": 1,
		 "label": "Dispute Reason", "insert_after": "alvoraa_disputed_on"},
		# HR's "Undo this change" on an approved change the employee disputed (Surbhi, 21 Nov).
		{"fieldname": "alvoraa_undone_by", "fieldtype": "Link", "options": "User", "read_only": 1,
		 "label": "Undone By", "insert_after": "alvoraa_dispute_reason"},
		{"fieldname": "alvoraa_undone_on", "fieldtype": "Datetime", "read_only": 1,
		 "label": "Undone On", "insert_after": "alvoraa_undone_by"},
		{"fieldname": "alvoraa_undone_reason", "fieldtype": "Small Text", "read_only": 1,
		 "label": "Undone Reason", "insert_after": "alvoraa_undone_on"},
	],
}


def after_migrate():
	"""The eight fields. Wired to after_migrate AND after_install: a site built with
	`bench install-app` never runs a migrate."""
	if not (frappe.db.exists("DocType", REQUEST) and frappe.db.exists("DocType", CHECKIN)):
		return False
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields(FIELDS)
	return True


def columns_ready():
	"""False on a site whose image is newer than its migrate: the readers then behave
	exactly as before instead of failing with an unknown column."""
	try:
		return bool(frappe.db.has_column(CHECKIN, ASIDE) and frappe.db.has_column(REQUEST, "alvoraa_set_aside")
		            and frappe.db.has_column(REQUEST, "alvoraa_needs_confirm")
		            and frappe.db.has_column(REQUEST, "alvoraa_undone_on"))
	except Exception:
		return False


def counting_only(filters):
	"""Add "not set aside" to a punch query's filters (SEC-8): the readers that turn punches
	into pay or a flag about pay (month view break, analytics, team days, grooming) leave a
	set-aside punch out, as the engine does. Unchanged where the column does not exist yet."""
	if columns_ready():
		filters[ASIDE] = ("is", "not set")
	return filters


# ── what a punch fix is ──────────────────────────────────────────────────────

def aside_names(doc):
	return [n for n in re.split(r"[,\s]+", (doc.get("alvoraa_set_aside") or "").strip()) if n]


def is_punch_fix(doc):
	return held_day._has_time(doc) or bool(aside_names(doc))


def _mins(value, date):
	"""Minutes from the start of `date`; over 1440 for a punch after midnight on the shift day (ALV-402),
	so a screen can place it after the evening punches."""
	return int((get_datetime(value) - get_datetime(getdate(date))).total_seconds() // 60)


def _hhmm(value):
	return get_datetime(value).strftime("%H:%M")


# ── the day ──────────────────────────────────────────────────────────────────

DAY_FIELDS = ["name", "employee", "attendance_date", "shift", "status", "company", "in_time",
              "owner", "attendance_request", "leave_application", "creation", "working_hours",
              "late_entry", "early_exit"]


def day_row(employee, date, for_update=False):
	return frappe.db.get_value(
		ATTENDANCE, {"employee": employee, "attendance_date": getdate(date), "docstatus": 1},
		DAY_FIELDS, as_dict=True, for_update=for_update)


def day_state(employee, date, row=None, emp=None, ctx=None):
	"""None when the day can be fixed, else one word: left, unmarked, slip, leave,
	hand, noshift. ONE answer, asked at raise and again at approval (SEC-5). A caller that
	has the employee's status and the day's row already passes them in, with `ctx` (from
	`card_context`) holding every pending leave and slip, so a list of cards asks once."""
	status = emp.status if emp else frappe.db.get_value("Employee", employee, "status")
	if status != "Active":
		return "left"
	row = row or day_row(employee, date)
	if not row:
		return "unmarked"
	# A day that was Held keeps 085's arrear path (Surbhi, 21 Nov): approval goes through even on a
	# final slip, the slip is never touched, and the day is flagged released-after-final-slip.
	day = getdate(date)
	if row.status != held_day.HELD and (
			any(x.employee == employee and x.start_date <= day <= x.end_date for x in ctx["slips"]) if ctx
			else held_day.is_in_final_slip(employee, date)):
		return "slip"
	if row.status == "On Leave" or (
			any(x.employee == employee and x.from_date <= day <= x.to_date for x in ctx["leaves"]) if ctx
			else frappe.db.exists("Leave Application", {
				"employee": employee, "docstatus": 1, "status": "Approved",
				"from_date": ("<=", day), "to_date": (">=", day)})):
		return "leave"
	# Only auto-attendance sets `in_time`, and it creates rows as Administrator; a
	# status-only request leaves its own link; leave leaves its link. What is left,
	# made by a named person, was marked by hand.
	if not row.in_time and row.owner != "Administrator" \
			and not row.attendance_request and not row.leave_application:
		return "hand"
	if not row.shift:
		return "noshift"
	return None


def blocked_sentence(code, employee, date):
	if code == "hand":
		made = frappe.utils.formatdate(day_row(employee, date).creation, "d MMM")
		return _("HR marked this day by hand on {0}, so punches do not change it. If it is "
		         "wrong, ask HR to look at it.").format(made)
	return {
		"slip": _("It is on a salary slip that is already final, so its punches cannot be "
		          "changed here. Tell HR which day it was and what happened. HR can pay the "
		          "difference with an Additional Salary."),
		"leave": _("It is covered by approved leave, so punches do not change it. If you worked "
		           "that day, ask HR to cancel the leave first."),
		"unmarked": _("This day has not been marked yet. You can fix it once it has."),
		"left": _("This person has left, so no punch can be added. Decline it and say why."),
		"noshift": _("This day has no shift, so its hours cannot be worked out. Ask a "
		             "System Manager to set the shift on the day, then approve again."),
	}[code]


# ── the punches ──────────────────────────────────────────────────────────────

def day_punches(employee, date):
	"""Every punch of the day, set-aside ones too, for the card, the sheet and the token. The same
	day rule as the engine (ALV-402): a punch counts on its `shift_start` date, or its own date
	with no shift, so a 00:00 departure is the last punch of the day before."""
	date = getdate(date)
	rows = frappe.get_all(
		CHECKIN, filters={"employee": employee,
		                  "time": ("between", [f"{date} 00:00:00", f"{add_days(date, 1)} 23:59:59"])},
		fields=["name", "time", "log_type", "device_id", "skip_auto_attendance", "offshift", "shift_start",
		        ADDED, ASIDE],
		order_by="time asc")
	return [r for r in rows if shift_day(r) == str(date)]


def counted(employee, date, aside=()):
	"""The punches the day is judged from: the same list `worked_out` reads."""
	return held_day._day_logs(employee, date, None, aside)


def kind_for(before_count, after_count, log_type):
	"""Arrival, Leaving, Back in after a break or Out for a break (01b v2.2)."""
	if not before_count:
		return "Arrival"
	if log_type == "OUT":
		return "Leaving" if not after_count else "Out for a break"
	return "Back in after a break"


def derive(employee, date, when_time, aside=(), shift=None, logs=None):
	"""(log_type, label, datetime) for a punch added at `when_time` on `date`. The
	server's answer is the one stored: a log type sent by a client is never read."""
	shift = shift or frappe.db.get_value(ATTENDANCE, {"employee": employee, "attendance_date": getdate(date),
	                                                  "docstatus": 1}, "shift")
	logs = counted(employee, date, aside) if logs is None else logs
	shift_doc = frappe.get_cached_doc("Shift Type", shift) if shift else frappe._dict()
	when = held_day.extra_when(shift_doc, date, frappe.utils.get_time(when_time), logs[0].time if logs else None)
	before = sum(1 for x in logs if get_datetime(x.time) < when)
	log_type = "IN" if before % 2 == 0 else "OUT"
	return log_type, kind_for(before, len(logs) - before, log_type), when


def outcome(row, add=None, aside=(), logs=None):
	"""What the day comes to, from the counted punches, with `add` = (time, log_type)
	put in and `aside` (punch names) left out. THE one function: the card calls it
	to show "If approved" and the approval calls it to write, so they cannot differ."""
	logs = held_day._day_logs(row.employee, row.attendance_date, row.shift, aside) if logs is None else logs
	status, hours, late, early, first, last = held_day.worked_out(row, add, aside, logs)
	count = len(logs) + (1 if add else 0)
	# An odd count is still a missing punch. Held stays held; elsewhere the company's switch decides.
	if count % 2 and (row.status == held_day.HELD or held_day._switch_on(row.company)):
		status = held_day.HELD
	return {"status": status, "hours": flt(hours, 3), "late": cint(late), "early": cint(early),
	        "in_time": first, "out_time": last, "count": count}


def _snapshot(row, aside=()):
	"""The day as the audit fields keep it: counted punches, times only, no names."""
	logs = counted(row.employee, row.attendance_date, aside)
	return frappe.as_json({"status": row.status, "working_hours": flt(row.working_hours, 2),
	                       "late_entry": cint(row.late_entry), "early_exit": cint(row.early_exit),
	                       "punches": [_hhmm(x.time) for x in logs]})


def _token(modified, punches):
	return hashlib.sha1(f"{modified}|{','.join(sorted(p.name for p in punches))}".encode()).hexdigest()


def seen_token(doc):
	"""What HR saw: the request as last saved and the ids of the day's punches. If
	either moves, an approval sent with the old token is refused (SEC-1)."""
	return _token(doc.modified, day_punches(doc.employee, doc.from_date))


# ── raising (validate: Desk, REST, the portal) ───────────────────────────────

def validate(doc, method=None):
	"""Attendance Request validate, first in the list. Runs on a draft only: at
	submit Frappe validates again with docstatus 1, and the approval has its own checks.

	It also owns `alvoraa_for_held_day`: set here on a new request from whether the
	day is Held now, and put back to the stored value on an edit. A client value is
	never read, so a time cannot be used to dodge the monthly limit."""
	if not frappe.db.has_column(REQUEST, "alvoraa_for_held_day"):
		return
	before = None if doc.is_new() else doc.get_doc_before_save()
	if before is not None:
		# An edit keeps the stored value, unless it is no longer a punch fix: a held-day draft
		# edited into an ordinary request is an ordinary request and counts (085 F4).
		doc.alvoraa_for_held_day = cint(before.get("alvoraa_for_held_day")) if is_punch_fix(doc) else 0
	else:
		doc.alvoraa_for_held_day = 1 if (is_punch_fix(doc) and str(doc.from_date) == str(doc.to_date)
		                                 and held_day._held_row(doc.employee, doc.from_date)) else 0
	if before is not None and (is_punch_fix(before) or is_punch_fix(doc)):
		# Whose day it is never changes on a saved request, for anyone including Administrator (SEC-4, ALV-419).
		if before.employee != doc.employee or any(
				before.get(f) and doc.get(f) and before.get(f) != doc.get(f) for f in ("employee_name", "company")):
			frappe.throw(_("A request cannot be moved to another employee. Withdraw it and send a new one for the right person."))
	_own_the_confirm_fields(doc, before)
	if doc.docstatus or not is_punch_fix(doc):
		return

	if str(doc.from_date) != str(doc.to_date):
		frappe.throw(_("A punch fix is for one day. Send each day on its own."))
	# Only the employee sends their own fix. A manager or HR person may send a time
	# for a Held day (085) and nothing else; a manager never sets a punch aside.
	if doc.is_new() and frappe.session.user != "Administrator" and not access.is_own_record(doc.employee) \
			and not (doc.alvoraa_for_held_day and not aside_names(doc)):
		access.refuse(_("Only the employee can send a punch fix for an ordinary day. Ask them to send it, "
		                "or ask HR."), "SEC-4", "Attendance Request insert", REQUEST, doc.name)
	code = day_state(doc.employee, doc.from_date)
	if code and code != "noshift":
		frappe.throw(blocked_sentence(code, doc.employee, doc.from_date))

	ticked = _check_aside(doc)
	if held_day._has_time(doc):
		log_type, _label, when = derive(doc.employee, doc.from_date, doc.alvoraa_missing_time, ticked)
		_check_not_a_repeat(doc, when, ticked)
		doc.alvoraa_missing_log = log_type
	elif len(counted(doc.employee, doc.from_date, ticked)) == 0:
		frappe.throw(_("A day cannot be left with no punches. Add a punch too."))
	# Nothing in a refusal names a person or quotes the note.


def _own_the_confirm_fields(doc, before):
	"""ALV-419. A request filed by anybody but the employee waits for the employee's Confirm. The
	server decides that when the request is created (Administrator, the break-glass account, is
	not a person filing for somebody, so it is the one exception) and puts all three fields back
	to what is stored on every edit, so a client value changes nothing. They are written by
	`confirm` alone, with no validate, so this does not stand in its way."""
	if not frappe.db.has_column(REQUEST, "alvoraa_needs_confirm"):
		return
	if before is None:
		login = frappe.db.get_value("Employee", doc.employee, "user_id")
		filer = frappe.session.user
		# Counsel, 21 Nov (manager additions): a request the employee's MANAGER files that only ADDS a time
		# goes straight to HR. HR-filed requests, and anything that sets a punch aside, still wait. A manager
		# is whoever files for the employee without an HR role (the same test as `_filed_by_hr`); decided
		# here from the session, never from the client.
		manager_adds = (filer != login and not held_day._filed_by_hr(filer, login)
		                and held_day._has_time(doc) and not aside_names(doc))
		doc.alvoraa_needs_confirm = 0 if (filer in ("Administrator", login) or manager_adds) else 1
		doc.alvoraa_confirmed_by = doc.alvoraa_confirmed_on = None
		doc.alvoraa_disputed_by = doc.alvoraa_disputed_on = doc.alvoraa_dispute_reason = None
		doc.alvoraa_undone_by = doc.alvoraa_undone_on = doc.alvoraa_undone_reason = None
		# Only `confirm` sets the link (a process flag a client cannot send), so it cannot be used to
		# dodge the monthly limit.
		doc.alvoraa_replaces = frappe.flags.get("punch_fix_replaces")
	else:
		for f in SERVER_OWNED:
			doc.set(f, before.get(f))
		# Decided again on every save, from who is saving and what the request now does (review B1): an edit
		# by anybody but the employee that ADDS a cut puts the Confirm back and clears any earlier one.
		login = frappe.db.get_value("Employee", doc.employee, "user_id")
		if (not cint(doc.alvoraa_needs_confirm) and frappe.session.user not in ("Administrator", login)
				and set(aside_names(doc)) - set(aside_names(before))):
			doc.alvoraa_needs_confirm = 1
			doc.alvoraa_confirmed_by = doc.alvoraa_confirmed_on = None
		# SEC-7 (from 086's review): a Confirm is for what the employee saw. If the filer changes what the
		# request says after that, the Confirm is cleared and the employee must confirm again. Cleared, not
		# refused: HR may need to correct a typo, and nothing is lost by asking the employee once more.
		if doc.get("alvoraa_confirmed_on") and any(doc.has_value_changed(f) for f in CONFIRMED_CONTENT):
			doc.alvoraa_confirmed_by = doc.alvoraa_confirmed_on = None


def _check_aside(doc):
	"""Each punch to set aside must be this employee's, on this day, and still counting."""
	names = aside_names(doc)
	for name in names:
		row = frappe.db.get_value(CHECKIN, name, ["employee", "time", "shift_start", "skip_auto_attendance", ASIDE],
		                          as_dict=True)
		if not row or row.employee != doc.employee or shift_day(row) != str(getdate(doc.from_date)):
			access.log_refusal("SEC-4", "punch_fix.validate", REQUEST, doc.name)
			frappe.throw(_("One of the punches you picked is not on this day. Open the day again and pick "
			               "from the list."))
		if row.skip_auto_attendance or row.get(ASIDE):
			frappe.throw(_("One of the punches you picked does not count already, so there is nothing to "
			               "set aside."))
	return names


def _check_not_a_repeat(doc, when, aside):
	window = timedelta(minutes=DUPLICATE_PUNCH_MINUTES, seconds=59)
	for x in counted(doc.employee, doc.from_date, aside):
		if abs(get_datetime(x.time) - when) <= window:
			frappe.throw(_("There is already a punch at {0} (within {1} minutes). Check the time.").format(
				_hhmm(x.time), DUPLICATE_PUNCH_MINUTES))


@frappe.whitelist(methods=["POST"])
def send(date, time=None, set_aside=None, note=None):
	"""The employee's send: one punch to add and/or punches to set aside, own record
	only. Exactly these four things; the kind of punch and the reason are worked out
	here, never taken from the caller (PRIV-1)."""
	import alvoraa_portal.attendance_correction as ac

	me = ac._me()
	if isinstance(time, (list, tuple)) or "," in str(time or ""):
		frappe.throw(_("One punch per request. If another is missing, send this first and add the next "
		               "after HR decides."))
	if isinstance(set_aside, str) and set_aside.strip().startswith("["):
		set_aside = frappe.parse_json(set_aside)
	ticked = [n for n in (set_aside if isinstance(set_aside, (list, tuple)) else
	                      re.split(r"[,\s]+", str(set_aside or ""))) if n]
	if not time and not ticked:
		frappe.throw(_("Enter the time first."))
	# ALV-418 (counsel, 21 Nov): a reason on every request, a Held day too. This reverses PRIV-2.
	if not (note or "").strip():
		frappe.throw(_("Say why, so HR can decide. A reason is needed on every request."))
	if time:
		try:
			time = frappe.utils.get_time(time).strftime("%H:%M:%S")
		except Exception:
			frappe.throw(_("That time was not understood. Enter it like 18:30."))
	if getdate(date) > getdate(frappe.utils.nowdate()):
		frappe.throw(_("You cannot send a fix for a day that has not happened yet."))
	doc = frappe.get_doc({
		"doctype": REQUEST, "employee": me.name, "employee_name": me.employee_name,
		"company": me.company, "from_date": date, "to_date": date,
		"reason": "Other", "explanation": (note or "").strip() or None,
		"alvoraa_missing_time": time, "alvoraa_set_aside": ", ".join(ticked) or None,
		"alvoraa_review_status": "Waiting"})
	if time:
		log_type, _label, _when = derive(me.name, date, time, ticked)
		doc.reason = "Forgot to Punch Out" if log_type == "OUT" else "Forgot to Punch In"
	# No permission bypass: the Employee role holds create on this DocType.
	doc.insert()
	return ac._shape(doc.as_dict())


def _shift_line(shift):
	"""Start, end and expected hours of a Shift Type, for the day sheet and the card."""
	doc = frappe.get_cached_doc("Shift Type", shift)
	start, end = held_day._as_time(doc.start_time), held_day._as_time(doc.end_time)
	span = (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute)
	return {"start": start.strftime("%H:%M"), "end": end.strftime("%H:%M"),
	        "expected": round((span % 1440) / 60, 2)}


def _source(p):
	return (_("Added by HR") if p.get(ADDED) else _("Machine") if p.device_id else _("Check In on this portal"))


def _filer(owner, employee_login):
	"""Who filed a request for somebody: ("HR" or "manager", full name). The employee sees the name of
	a manager and not of HR (v1 decision 7); HR sees both names."""
	kind = "HR" if held_day._filed_by_hr(owner, employee_login) else "manager"
	return kind, frappe.db.get_value("User", owner, "full_name") or owner


def _reason_of(explanation):
	"""The filer's own words: a request a manager files has the system's stamp ("Raised by ...") added after a blank line."""
	return (explanation or "").split("\n\n")[0].strip() or None


@frappe.whitelist()
def day_sheet(date):
	"""Everything the employee's day sheet draws for ONE of their own days: whether it can be
	fixed (a code and its sentence), the shift, the punches with their marks, and the latest
	punch fix for the day. One day, a handful of queries, own record only, never cached."""
	import alvoraa_portal.attendance_correction as ac

	me = ac._me()
	out = {"date": str(getdate(date)), "blocked": None, "blocked_text": None}
	code = day_state(me.name, date)
	if code:
		out["blocked"], out["blocked_text"] = code, blocked_sentence(code, me.name, date)
	row = day_row(me.name, date)
	if not row:
		return out
	out.update({"status": row.status, "hours": flt(row.working_hours, 2), "held": row.status == held_day.HELD,
	            "shift": _shift_line(row.shift) if row.shift else None})
	out["punches"] = [{"name": p.name, "time": _hhmm(p.time), "m": _mins(p.time, date), "log_type": p.log_type,
	                   "source": _source(p),
	                   "added": bool(p.get(ADDED)), "aside": bool(p.get(ASIDE)),
	                   "counted": not (p.skip_auto_attendance or p.offshift or p.get(ASIDE))}
	                  for p in day_punches(me.name, date)]
	for r in frappe.get_all(
			REQUEST, filters={"employee": me.name, "docstatus": ("<", 2), "from_date": getdate(date)},
			fields=["name", "docstatus", "alvoraa_review_status", "creation", "alvoraa_missing_time",
			        "alvoraa_missing_log", "alvoraa_set_aside", "explanation", "alvoraa_review_note",
			        "alvoraa_reviewed_on", "alvoraa_reviewed_by", "alvoraa_needs_confirm", "alvoraa_confirmed_on",
			        "alvoraa_replaces", "alvoraa_disputed_on", "alvoraa_dispute_reason", "owner"],
			order_by="creation desc", limit_page_length=5):
		if is_punch_fix(r):
			state = ac._state(r)
			filed_for = r.owner != frappe.session.user
			needs = bool(cint(r.alvoraa_needs_confirm))
			confirm_state = ("confirmed" if r.alvoraa_confirmed_on
			                 else "disputed" if r.alvoraa_disputed_on else "not_yet") if needs else None
			out["request"] = {
				"name": r.name, "state": state, "sent_at": str(r.creation)[11:16],
				"time": frappe.utils.get_time(r.alvoraa_missing_time).strftime("%H:%M") if held_day._has_time(r) else None,
				"log_type": r.alvoraa_missing_log, "aside": aside_names(r), "note": r.explanation,
				# ALV-419: waiting on the employee's own Confirm, and whether HR or a manager filed it.
				# V5: approval never waits. `needs_confirm` = HR-filed or a cut, confirmed before pay is locked;
				# `can_confirm` = Confirm is offered; `can_not_right` = filed for the employee and still open
				# (pending or approved), so Not right is offered (also for a manager's addition).
				"needs_confirm": needs, "confirm_state": confirm_state,
				"can_confirm": bool(needs and confirm_state == "not_yet" and state in ("waiting", "approved")),
				"can_not_right": bool(filed_for and state in ("waiting", "approved") and not r.alvoraa_disputed_on),
				"was_filed": filed_for, "approved": state == "approved",
				"disputed": ({"on": str(r.alvoraa_disputed_on)[:10], "reason": r.alvoraa_dispute_reason}
				             if r.alvoraa_disputed_on else None),
				"filed_by": "HR" if held_day._filed_by_hr(r.owner, frappe.session.user) else "manager",
				"filed_by_name": (_filer(r.owner, frappe.session.user)[1]
				                  if filed_for and not held_day._filed_by_hr(r.owner, frappe.session.user) else None),
				"filer_reason": _reason_of(r.explanation) if filed_for else None,
				"item": _filed_item(r, me.name, date),
				"confirmed_at": str(r.alvoraa_confirmed_on)[11:16] if r.alvoraa_confirmed_on else None,
				"declined_by_you": bool(state == "declined" and r.alvoraa_reviewed_by == frappe.session.user),
				"replaces": _replaced(r, me),
				"hr_note": r.alvoraa_review_note if state in ("declined", "approved") else None,
				"decided_on": str(r.alvoraa_reviewed_on)[:10] if r.alvoraa_reviewed_on else None}
			break
	return out


def _filed_item(r, employee, date):
	"""What a request asks, for the Confirm block: add a punch (with its kind), or set one aside."""
	if held_day._has_time(r):
		time = frappe.utils.get_time(r.alvoraa_missing_time)
		_log, label, _when = derive(employee, date, time, aside_names(r))
		return {"kind": "add", "time": time.strftime("%H:%M"), "label": label}
	for name in aside_names(r)[:1]:
		t = frappe.db.get_value(CHECKIN, name, "time")
		return {"kind": "aside", "time": _hhmm(t) if t else None}
	return None


def _replaced(r, me):
	"""The request this one replaces (the employee said "Not right" to it), for the screens."""
	if not r.alvoraa_replaces:
		return None
	old = frappe.db.get_value(REQUEST, r.alvoraa_replaces, ["alvoraa_missing_time", "owner"], as_dict=True)
	if not old:
		return None
	kind, name = _filer(old.owner, me.user_id if "user_id" in me else frappe.session.user)
	return {"time": _hhmm_t(old.alvoraa_missing_time) if old.alvoraa_missing_time else None,
	        "filed_by": kind, "filed_by_name": name}


def home_rows(employee):
	"""Requests somebody filed for this employee that wait for their Confirm, for Home's "Needs you" row
	(V4, P-19). One row each; the caller's own facts only. Bounded."""
	if not columns_ready():
		return []
	login = frappe.db.get_value("Employee", employee, "user_id")
	out = []
	for r in frappe.get_all(
			REQUEST, filters=dict(_unconfirmed_filters(), employee=employee),
			fields=["name", "from_date", "owner", "docstatus", "alvoraa_missing_time", "alvoraa_set_aside"],
			order_by="from_date desc", limit_page_length=10):
		kind, who = _filer(r.owner, login)
		out.append({"name": r.name, "date": str(r.from_date), "filed_by": kind, "filer": who,
		            "punch_fix": is_punch_fix(r), "approved": r.docstatus == 1})
	return out


# ── the card HR reads (the same `outcome` the approval runs) ─────────────────

def card_context(rows):
	"""Everything the cards of these waiting requests read, in about eight queries for the whole
	list (AC-35): the requests, the employees, the day rows, the punches, and the approved leave
	and final slips that overlap. `card` then reads memory, not the database."""
	rows = [r for r in rows if r.get("punch_fix")]
	if not rows:
		return {}
	names, emps = [r["name"] for r in rows], list({r["employee"] for r in rows})
	days = [getdate(r["from_date"]) for r in rows]
	lo, hi = min(days), max(days)
	by_emp = {}
	for p in frappe.get_all(
			CHECKIN, filters={"employee": ("in", emps), "time": ("between", [f"{lo} 00:00:00", f"{add_days(hi, 1)} 23:59:59"])},
			fields=["name", "employee", "time", "log_type", "device_id", "skip_auto_attendance", "offshift",
			        "shift_start", "shift_end", ADDED, ASIDE], order_by="time asc", limit_page_length=0):
		by_emp.setdefault(p.employee, []).append(p)
	return {
		"req": {x.name: x for x in frappe.get_all(
			REQUEST, filters={"name": ("in", names)},
			fields=[f for f in ("name", "modified", "alvoraa_missing_time", "alvoraa_set_aside", "alvoraa_needs_confirm",
			                 "alvoraa_confirmed_on", "alvoraa_replaces", "owner", "creation", "explanation")
			        if f in ("name", "modified", "owner", "creation") or frappe.db.has_column(REQUEST, f)],  # M2: before migrate
			limit_page_length=0)},
		"emp": {x.name: x for x in frappe.get_all(
			"Employee", filters={"name": ("in", emps)}, fields=["name", "status", "user_id"], limit_page_length=0)},
		"att": {(x.employee, str(x.attendance_date)): x for x in frappe.get_all(
			ATTENDANCE, filters={"employee": ("in", emps), "docstatus": 1, "attendance_date": ("between", [lo, hi])},
			fields=DAY_FIELDS, limit_page_length=0)},
		"punches": by_emp,
		"leaves": frappe.get_all(
			"Leave Application", filters={"employee": ("in", emps), "docstatus": 1, "status": "Approved",
			                              "from_date": ("<=", hi), "to_date": (">=", lo)},
			fields=["employee", "from_date", "to_date"], limit_page_length=0),
		"slips": frappe.get_all(
			"Salary Slip", filters={"employee": ("in", emps), "docstatus": 1, "start_date": ("<=", hi), "end_date": (">=", lo)},
			fields=["employee", "start_date", "end_date"], limit_page_length=0),
	}


def card(row, ctx=None):
	"""Now and If approved for one waiting punch fix, plus the token to send back. Pass the
	`card_context` of the whole list; alone, it makes the context for this one row."""
	if not columns_ready():
		return {}
	doc = frappe._dict(row)
	ctx = ctx or card_context([dict(row, punch_fix=True)])
	req, emp = ctx["req"][doc.name], ctx["emp"].get(doc.employee)
	date = getdate(doc.from_date)
	day = ctx["att"].get((doc.employee, str(date)))
	punches = [p for p in ctx["punches"].get(doc.employee, []) if shift_day(p) == str(date)]
	out = {"blocked": day_state(doc.employee, date, day, emp, ctx) if emp else "left", "seen": _token(req.modified, punches),
	       "own_day": bool(emp and emp.user_id == frappe.session.user),
	       # V5: approval never waits. This is only the quiet line under the reason: does the change need the
	       # employee's confirmation before pay is locked, and where does it stand.
	       "awaiting_confirm": bool(cint(req.alvoraa_needs_confirm) and not req.alvoraa_confirmed_on
	                                )}
	# V4 (P-15, P-16, P-17): who filed it, when, and whether the employee has confirmed; and the request
	# this one replaces. HR sees the filer's name.
	if req.owner != (emp.user_id if emp else None):
		kind, who = _filer(req.owner, emp.user_id if emp else None)
		needs = bool(cint(req.alvoraa_needs_confirm))
		out["filed"] = {"by": kind, "name": who, "on": str(req.creation)[:10], "at": str(req.creation)[11:16],
		                "needs_confirm": needs,
		                "state": ("confirmed" if req.alvoraa_confirmed_on else "not_yet") if needs else None,
		                "reason": _reason_of(req.explanation),
		                "confirmed_on": (str(req.alvoraa_confirmed_on)[:10], str(req.alvoraa_confirmed_on)[11:16])
		                if req.alvoraa_confirmed_on else None}
	if req.alvoraa_replaces:
		old = frappe.db.get_value(REQUEST, req.alvoraa_replaces, ["alvoraa_missing_time", "owner"], as_dict=True)
		if old:
			kind, who = _filer(old.owner, emp.user_id if emp else None)
			out["replaces"] = {"time": _hhmm_t(old.alvoraa_missing_time) if old.alvoraa_missing_time else None,
			                   "by": kind, "name": who}
	if not day:
		return out
	ticked = aside_names(req)
	out["now"] = {"status": day.status, "hours": flt(day.working_hours, 2),
	              "shift": _shift_line(day.shift) if day.shift else None,
	              "punches": [{"time": _hhmm(p.time), "m": _mins(p.time, date), "log_type": p.log_type,
	                           "source": _source(p), "aside": bool(p.name in ticked or p.skip_auto_attendance or p.get(ASIDE)),
	                           "ticked": p.name in ticked, "name": p.name} for p in punches]}
	# Q6: HR is told in words when the punch to set aside came from a machine.
	out["sets_aside_machine"] = any(p["ticked"] and p["source"] == _("Machine") for p in out["now"]["punches"])
	if out["blocked"] or not day.shift:
		return out
	# The same list `_day_logs` returns (counting punches, the ticked ones left out), from memory.
	# A replacement of an approved change: approving it first puts that change back, so its added
	# punch does not count in the preview (the same as `apply`).
	gone = set(frappe.get_all(CHECKIN, filters={ADDED: req.alvoraa_replaces}, pluck="name")) if req.get("alvoraa_replaces") else set()
	logs = [p for p in punches if not p.skip_auto_attendance and not p.offshift and p.name not in ticked and p.name not in gone]
	add = None
	if held_day._has_time(req):
		log_type, label, when = derive(doc.employee, date, req.alvoraa_missing_time, ticked, day.shift, logs)
		add = (when, log_type)
		out["kind"] = label
	try:
		after = outcome(day, add, ticked, logs)
	except Exception:
		return out
	# If approved: what counts, the added punch, and the ticked ones struck through (AC-27).
	shown = ([{"time": _hhmm(x.time), "m": _mins(x.time, date), "added": False} for x in logs]
	         + ([{"time": _hhmm(add[0]), "m": _mins(add[0], date), "added": True}] if add else [])
	         + [{"time": p["time"], "m": p["m"], "added": False, "aside": True} for p in out["now"]["punches"] if p["ticked"]])
	out["after"] = {"status": after["status"], "hours": flt(after["hours"], 2), "late": after["late"],
	                "still_held": after["status"] == held_day.HELD,
	                "punches": sorted(shown, key=lambda x: x["m"])}
	return out


# ── approving ────────────────────────────────────────────────────────────────

def before_submit(doc, method=None):
	"""One door (SEC-1) and HR in scope (SEC-3). The own-day and raiser rules are the
	two hooks listed before this one."""
	if not is_punch_fix(doc):
		return
	if not doc.flags.get("punch_fix_decided"):
		frappe.throw(_("A punch fix is approved from the review card, so HR sees what will change first. "
		               "Open it from the Attendance page or the Inbox."))
	if not HR_ROLES & set(frappe.get_roles()):
		access.refuse(_("Only HR decides a punch fix."), "SEC-3", "punch_fix.before_submit", REQUEST, doc.name)
	if not access.employee_in_scope(doc.employee):
		access.refuse(_("That employee is outside the companies and branches you look after."), "SEC-17",
		              "punch_fix.before_submit", REQUEST, doc.name)
	code = day_state(doc.employee, doc.from_date)
	if code:
		frappe.throw(blocked_sentence(code, doc.employee, doc.from_date))


def _unconfirmed_filters():
	"""Requests that need the employee's confirmation before pay is locked and have not had it: HR-filed
	or a cut (`alvoraa_needs_confirm`), not confirmed in the app, not
	declined or withdrawn. Approved ones count: approval never waits (V5)."""
	f = {"alvoraa_needs_confirm": 1, "alvoraa_confirmed_on": ("is", "not set"), "docstatus": ("<", 2),
	     "alvoraa_undone_on": ("is", "not set"),
	     "alvoraa_review_status": ("not in", ["Declined", "Withdrawn"])}
	return f


def _what(r):
	"""A change in words: "added 14:40", "set aside 11:00"."""
	bits = []
	if held_day._has_time(r):
		bits.append(_("added {0}").format(_hhmm_t(r.alvoraa_missing_time)))
	for name in aside_names(r):
		t = frappe.db.get_value(CHECKIN, name, "time")
		bits.append(_("set aside {0}").format(_hhmm(t) if t else "?"))
	return _(", ").join(bits) or _("a correction")


def unconfirmed_changes(employees=None, start=None, end=None, limit=100):
	"""The unconfirmed changes (see `_unconfirmed_filters`) with their day in [start, end], for the given
	employees or everybody. Plain facts: employee, day, what, who filed it, whether HR has approved."""
	filters = _unconfirmed_filters()
	if employees is not None:
		filters["employee"] = ("in", list(employees) or [""])
	if start and end:
		filters["from_date"] = ("between", [start, end])
	rows = frappe.get_all(
		REQUEST, filters=filters, order_by="from_date asc", limit_page_length=limit,
		fields=["name", "employee", "employee_name", "from_date", "owner", "docstatus", "alvoraa_review_status",
		        "alvoraa_missing_time", "alvoraa_set_aside", "alvoraa_disputed_on"])
	logins = {}
	out = []
	for r in rows:
		login = logins.setdefault(r.employee, frappe.db.get_value("Employee", r.employee, "user_id"))
		kind, who = _filer(r.owner, login)
		out.append({"name": r.name, "employee": r.employee, "employee_name": r.employee_name,
		            "date": str(r.from_date), "what": _what(r), "filed_by": kind, "filer": who,
		            "approved": r.docstatus == 1, "disputed": bool(r.alvoraa_disputed_on)})
	return out


def _day_label(date):
	return frappe.utils.formatdate(date, "d MMM")


def refuse_slip_while_unconfirmed(doc, method=None):
	"""Salary Slip before_submit (V5, Option 1): the slip of an employee cannot be submitted while an
	HR-filed or cut change in its period is unconfirmed, unless it is withdrawn. Names each change.
	Manager additions and the employee's own requests never block it."""
	if doc.docstatus == 2 or not doc.employee or not columns_ready():
		return
	rows = unconfirmed_changes([doc.employee], doc.start_date, doc.end_date, limit=20)
	# Surbhi, 21 Nov: a change for a day that is already on a final slip is paid as an arrear in this slip,
	# so it holds this slip too until the employee confirms.
	rows += [r for r in unconfirmed_changes([doc.employee], "1900-01-01", frappe.utils.add_days(doc.start_date, -1), limit=20)
	         if r["approved"] and held_day.is_in_final_slip(doc.employee, r["date"])]
	if not rows:
		return
	first = (doc.employee_name or "").split(" ")[0] or _("the employee")
	lines = "; ".join(_("{0}: {1}, sent by {2} ({3})").format(_day_label(r["date"]), r["what"], r["filer"], r["filed_by"])
	                  for r in rows)
	frappe.throw(_("The salary slip for {0}, {1}, cannot be submitted. {2} not confirmed: {3}. Ask {4} to "
	               "confirm in the app, record the signed register, or withdraw the change.").format(
		doc.employee_name or doc.employee, frappe.utils.formatdate(doc.start_date, "MMM yyyy"),
		_("1 change is") if len(rows) == 1 else _("{0} changes are").format(len(rows)), lines, first))


def unconfirmed_text_by_employee(employees, start, end):
	"""One line per employee for the Salary Workings report (DTC pays outside the portal)."""
	if not columns_ready() or not employees:
		return {}
	out = {}
	for r in unconfirmed_changes(employees, start, end, limit=1000):
		out.setdefault(r["employee"], []).append(f"{frappe.utils.formatdate(r['date'], 'EEE d MMM')} {r['what']}")
	return {k: "; ".join(v) for k, v in out.items()}


@frappe.whitelist()
def before_payroll(month=None):
	"""HR's list before payroll: the unconfirmed changes of the month, for the employees this caller looks
	after (company and branch, fail closed). Not a screen of its own: a card on the HR page."""
	import alvoraa_portal.attendance_correction as ac

	if not HR_ROLES & set(frappe.get_roles()):
		access.refuse(_("Only HR sees this list."), "SEC-3", "punch_fix.before_payroll", REQUEST, None)
	first = get_first_day(month or nowdate())
	conditions = ac._scope_conditions()
	scoped = frappe.get_all("Employee", filters=conditions, pluck="name", limit_page_length=0) \
		if conditions is not None else None
	rows = unconfirmed_changes(scoped, first, get_last_day(first), limit=100)
	# An approved change the employee sent their own time against: HR approves that request instead (its
	# approval reverses this one), so there is no Undo to press.
	instead = {x.alvoraa_replaces: x for x in frappe.get_all(
		REQUEST, filters={"alvoraa_replaces": ("in", [r["name"] for r in rows] or [""]), "docstatus": 0,
		                 "alvoraa_review_status": "Waiting"},
		fields=["name", "alvoraa_replaces", "alvoraa_missing_time"])}
	for r in rows:
		r["can_withdraw"] = not r["approved"]  # D-2: only a change still pending can be withdrawn
		rep = instead.get(r["name"])
		r["instead"] = {"name": rep.name, "time": _hhmm_t(rep.alvoraa_missing_time)} if rep and rep.alvoraa_missing_time else None
		r["can_undo"] = bool(r["approved"] and r["disputed"] and not r["instead"])  # Undo only on a disputed approved change
	return {"month": str(first), "rows": rows}


@frappe.whitelist(methods=["POST"])
def withdraw_filed(name):
	"""HR takes back a change that was filed for an employee and is still pending (V5 D-2). It becomes
	Withdrawn, so it no longer blocks the slip. An approved change cannot be withdrawn."""
	doc = frappe.get_doc(REQUEST, name, for_update=True)
	if not HR_ROLES & set(frappe.get_roles()) or not access.employee_in_scope(doc.employee):
		access.refuse(_("That request is outside the people you look after."), "SEC-17", "punch_fix.withdraw_filed",
		              REQUEST, name)
	access.refuse_own_decision(doc.employee, REQUEST, name, "punch_fix.withdraw_filed")
	if doc.docstatus != 0 or doc.get("alvoraa_review_status") != "Waiting" or not cint(doc.get("alvoraa_needs_confirm")):
		frappe.throw(_("Only a change that is still waiting for HR can be withdrawn."))
	doc.db_set({"alvoraa_review_status": "Withdrawn", "alvoraa_reviewed_by": frappe.session.user,
	            "alvoraa_reviewed_on": now_datetime()})
	access.security_logger().warning("punch_fix withdrawn request=%s user=%s", name, frappe.session.user)
	return {"name": name}


def _reverse(orig, user):
	"""Take an approved change back through the same marks, deleting nothing: a set-aside punch counts again;
	a punch the change added is marked not counted, with its aside link pointing at this request (the undo
	record). Order matters: the restore comes first, because both use the same link."""
	frappe.flags.in_punch_fix_apply = True
	try:
		for name in frappe.get_all(CHECKIN, filters={ASIDE: orig.name}, pluck="name"):
			punch = frappe.get_doc(CHECKIN, name)
			punch.update({ASIDE: None, ASIDE_BY: None, ASIDE_ON: None, "skip_auto_attendance": 0})
			punch.save()
		for name in frappe.get_all(CHECKIN, filters={ADDED: orig.name}, pluck="name"):
			punch = frappe.get_doc(CHECKIN, name)
			punch.update({ASIDE: orig.name, ASIDE_BY: user, ASIDE_ON: now_datetime(), "skip_auto_attendance": 1})
			punch.save()
	finally:
		frappe.flags.in_punch_fix_apply = False


@frappe.whitelist(methods=["POST"])
def undo_change(name, reason):
	"""HR undoes an approved change the employee disputed (Surbhi, 21 Nov). A reason is required. The day is
	judged again from the real punches by the same `outcome` approval uses, the draft slip is refreshed as
	usual, who, when and why are kept on the request, and the change no longer holds the salary slip. HR in
	scope, never on their own day, POST only; nothing is deleted. If the employee sent their own time, HR
	approves that request instead (it reverses this one)."""
	if not (reason or "").strip():
		frappe.throw(_("Say why you are undoing this change."))
	doc = frappe.get_doc(REQUEST, name, for_update=True)
	if not HR_ROLES & set(frappe.get_roles()) or not access.employee_in_scope(doc.employee):
		access.refuse(_("That request is outside the people you look after."), "SEC-17", "punch_fix.undo_change", REQUEST, name)
	access.refuse_own_decision(doc.employee, REQUEST, name, "punch_fix.undo_change")
	if doc.docstatus != 1 or not is_punch_fix(doc) or not doc.get("alvoraa_disputed_on") or doc.get("alvoraa_undone_on"):
		frappe.throw(_("Only an approved change that the employee disputed can be undone, and only once."))
	code = day_state(doc.employee, doc.from_date)
	if code and code != "noshift":
		frappe.throw(blocked_sentence(code, doc.employee, doc.from_date))
	row = day_row(doc.employee, doc.from_date, for_update=True)
	if not row or not row.shift:
		frappe.throw(blocked_sentence("unmarked" if not row else "noshift", doc.employee, doc.from_date))
	user = frappe.session.user
	_reverse(doc, user)
	actual = outcome(row)
	_write_day(row, (actual["status"], actual["hours"], actual["late"], actual["early"],
	                 actual["in_time"], actual["out_time"]))
	_engine_must_agree(row, actual)
	doc.db_set({"alvoraa_undone_by": user, "alvoraa_undone_on": now_datetime(),
	            "alvoraa_undone_reason": reason.strip()}, update_modified=False)
	frappe.flags.held_slip = held_day.refresh_draft_slip(doc.employee, row.attendance_date)
	access.security_logger().warning("punch_fix undone request=%s attendance=%s user=%s outcome=%s",
	                                     name, row.name, user, actual["status"])
	return {"name": name, "status": actual["status"]}


def record_register_signature(requests, notice):
	"""The seam with slice 088 (088's 02-functional-spec section 8.5). 088 implements it: it sets
	`alvoraa_signed_notice = notice` on each request in the list under a process flag, with no commit,
	called only from its own transaction. Declared here so 087 and 088 agree the name and the shape.
	Until 088 lands it refuses in plain words."""
	frappe.throw(_("Recording a signed register is not available yet."))


@frappe.whitelist(methods=["POST"])
def confirm(name, ok, reason=None, time=None):
	"""The employee answers a request somebody filed for them: Confirm (ok=1) or Not right (ok=0).

	Approval never waits for this (V5): it can come before or after HR decides. Confirm is for an HR-filed
	or a cut change (`alvoraa_needs_confirm`); a manager's addition needs none, but the employee can still
	say Not right. Not right needs a reason, and a time when one was sent:
	- still pending: the filed request is declined and, with a time, the employee's OWN request goes in
	  its place (`alvoraa_replaces`), in the same transaction;
	- already approved (D-1): the day stays as approved. With a time it is a NEW request; with no time, or
	  for a cut, it is a dispute: the reason goes to HR.
	Own request only; who and when are recorded on the request."""
	import alvoraa_portal.attendance_correction as ac

	me = ac._me()
	doc = frappe.get_doc(REQUEST, name, for_update=True)
	if doc.employee != me.name:
		access.refuse(_("That request is not about you."), "SEC-4", "punch_fix.confirm", REQUEST, name)
	approved = doc.docstatus == 1
	if doc.owner == frappe.session.user or doc.docstatus == 2 or doc.get("alvoraa_review_status") in ("Declined", "Withdrawn") \
			or (doc.docstatus == 0 and doc.get("alvoraa_review_status") != "Waiting"):
		frappe.throw(_("There is nothing to confirm on this request."))
	user, now = frappe.session.user, now_datetime()
	if cint(ok):
		if not cint(doc.get("alvoraa_needs_confirm")):
			frappe.throw(_("There is nothing to confirm on this request."))
		if doc.get("alvoraa_confirmed_on"):
			frappe.throw(_("You have already confirmed this one."))
		doc.db_set({"alvoraa_confirmed_by": user, "alvoraa_confirmed_on": now}, update_modified=not approved)
		access.security_logger().warning("punch_fix confirm request=%s employee=%s user=%s answer=confirmed",
		                                     name, me.name, user)
		return ac._shape(frappe.get_doc(REQUEST, name).as_dict())
	if not (reason or "").strip():
		frappe.throw(_("Say what is not right, so HR knows what to fix."))
	filed_time = _hhmm_t(doc.alvoraa_missing_time) if held_day._has_time(doc) else None
	if filed_time and not (time or "").strip():
		frappe.throw(_("Enter the time first."))
	frappe.db.savepoint("pf_not_right")
	replacement = disputed = None
	try:
		if approved:
			if filed_time:
				replacement = _replacement(doc, me, reason, time, filed_time)
			else:
				doc.db_set({"alvoraa_disputed_by": user, "alvoraa_disputed_on": now,
				            "alvoraa_dispute_reason": reason.strip()}, update_modified=False)
				disputed = True
		else:
			# Declined first: the one-open-request rule then lets the replacement in.
			doc.db_set({"alvoraa_review_status": "Declined", "alvoraa_review_note": reason.strip(),
			            "alvoraa_reviewed_by": user, "alvoraa_reviewed_on": now})
			replacement = _replacement(doc, me, reason, time, filed_time) if filed_time else None
	except Exception:
		frappe.db.rollback(save_point="pf_not_right")
		raise
	access.security_logger().warning("punch_fix confirm request=%s employee=%s user=%s answer=not right replacement=%s disputed=%s",
	                                     name, me.name, user, replacement, bool(disputed))
	out = ac._shape(frappe.get_doc(REQUEST, name).as_dict())
	out["replacement"], out["disputed"] = replacement, bool(disputed)
	return out


def _hhmm_t(value):
	return frappe.utils.get_time(value).strftime("%H:%M")


def _replacement(filed, me, reason, time, filed_time):
	"""The employee's own request for the time they say is right. The same checks as `send` (the
	request's own `validate` runs them: day, repeat within 2 minutes, kind), plus: not the time that
	was sent."""
	try:
		when = frappe.utils.get_time(time).strftime("%H:%M:%S")
	except Exception:
		frappe.throw(_("That time was not understood. Enter it like 18:30."))
	if when[:5] == filed_time:
		frappe.throw(_("That is the time that was sent. If it is right, go back and press Confirm."))
	log_type, _label, _when = derive(me.name, filed.from_date, when, [])
	new = frappe.get_doc({
		"doctype": REQUEST, "employee": me.name, "employee_name": me.employee_name, "company": me.company,
		"from_date": filed.from_date, "to_date": filed.from_date,
		"reason": "Forgot to Punch Out" if log_type == "OUT" else "Forgot to Punch In",
		"explanation": (reason or "").strip() or None, "alvoraa_missing_time": when,
		"alvoraa_review_status": "Waiting"})
	frappe.flags.punch_fix_replaces = filed.name
	try:
		new.insert()  # as the employee, no permission bypass
	finally:
		frappe.flags.punch_fix_replaces = None
	return new.name


def refuse_cancel(doc, method=None):
	"""An approved fix is never cancelled: cancelling would not take the punch back."""
	# before_cancel only runs on a submitted request, and by then docstatus already reads 2.
	if is_punch_fix(doc):
		frappe.throw(_("Raise a new request to change this day."))


def apply(doc, method=None):
	"""Attendance Request on_submit, the ONE writer of the day for a punch fix. Any
	error raised here undoes the whole approval, punches and all."""
	if not is_punch_fix(doc):
		return
	row = day_row(doc.employee, doc.from_date, for_update=True)
	if not row or not row.shift:
		frappe.throw(blocked_sentence("unmarked" if not row else "noshift", doc.employee, doc.from_date))
	user = frappe.session.user
	before = _snapshot(row)
	was_held = row.status == held_day.HELD
	# The employee's own request that replaces an approved change: approving it puts that change back first
	# (the same marks as "Undo this change"), so the day does not carry both times.
	orig = frappe.get_doc(REQUEST, doc.alvoraa_replaces) if doc.get("alvoraa_replaces") else None
	if orig and orig.docstatus == 1 and not orig.get("alvoraa_undone_on") and is_punch_fix(orig):
		_reverse(orig, user)
		orig.db_set({"alvoraa_undone_by": user, "alvoraa_undone_on": now_datetime(),
		             "alvoraa_undone_reason": _("Replaced by the employee's own request {0}.").format(doc.name)},
		            update_modified=False)
	ticked = _check_aside(doc)
	add = None
	if held_day._has_time(doc):
		log_type, _label, when = derive(doc.employee, doc.from_date, doc.alvoraa_missing_time, ticked, row.shift)
		_check_not_a_repeat(doc, when, ticked)
		add = (when, log_type)
	expected = outcome(row, add, ticked)

	frappe.flags.in_punch_fix_apply = True
	try:
		# Set aside FIRST: the repeat-scan hook looks back from a new punch at the punches
		# that are still kept, and a ticked one next to the added time must not be one.
		for name in ticked:
			punch = frappe.get_doc(CHECKIN, name)
			punch.update({ASIDE: doc.name, ASIDE_BY: user, ASIDE_ON: now_datetime(), "skip_auto_attendance": 1})
			punch.save()
		if add:
			punch = frappe.get_doc({"doctype": CHECKIN, "employee": doc.employee, "time": add[0],
			                        "log_type": add[1], ADDED: doc.name, "skip_auto_attendance": 0})
			punch.insert()
			punch.reload()
			if get_datetime(punch.time) != add[0]:
				frappe.throw(_("The time could not be stored as typed. Ask a System Manager to check your "
				               "rights on punches."))
			if not punch.shift:
				frappe.throw(_("{0} is outside the shift's punch window. Check the time.").format(_hhmm(add[0])))
			if punch.skip_auto_attendance:
				frappe.throw(_("A punch within {0} minutes of another is not counted. Check the time.").format(
					DUPLICATE_PUNCH_MINUTES))
			# Linked after insert (stock sets the shift only while there is no link) and in the
			# same transaction, so Frappe's marking job can never take it for an unmarked punch.
			frappe.db.set_value(CHECKIN, punch.name, "attendance", row.name)
	finally:
		frappe.flags.in_punch_fix_apply = False

	# Read back from the real punches. A punch after midnight is on this day through its
	# `shift_start` (ALV-402), the same rule the engine, the card and `worked_out` use.
	actual = outcome(row)
	if any(actual[k] != expected[k] for k in ("status", "hours", "late", "early", "count")):
		frappe.throw(_("The day did not come out as the review card showed, so nothing was changed. "
		               "Open the card again."))
	result = (actual["status"], actual["hours"], actual["late"], actual["early"],
	          actual["in_time"], actual["out_time"])
	if was_held:
		held_day._write_release(row.name, row, result, "HR decision" if actual["status"] != held_day.HELD
		                        else None, user if actual["status"] != held_day.HELD else None)
	else:
		_write_day(row, result)
	frappe.db.set_value(ATTENDANCE, row.name, "attendance_request", doc.name)
	_engine_must_agree(row, actual)
	after = frappe._dict(row, status=actual["status"], working_hours=actual["hours"],
	                     late_entry=actual["late"], early_exit=actual["early"])
	doc.db_set({"alvoraa_fix_before": before, "alvoraa_fix_after": _snapshot(after)}, update_modified=False)
	frappe.flags.held_slip = held_day.refresh_draft_slip(doc.employee, row.attendance_date)
	access.security_logger().warning(
		"punch_fix approved request=%s attendance=%s approver=%s outcome=%s", doc.name, row.name, user,
		actual["status"])


def _write_day(row, outcome_tuple):
	status, hours, late, early, in_time, out_time = outcome_tuple
	frappe.db.set_value(ATTENDANCE, row.name, {
		"status": status, "working_hours": flt(hours, 3), "late_entry": cint(late),
		"early_exit": cint(early), "in_time": in_time, "out_time": out_time,
		"half_day_status": "Absent" if status == "Half Day" else None, "modify_half_day_status": 0})


def _engine_must_agree(row, actual):
	"""At a company with a pay rule set the engine decides what is paid. If it would
	still hold a day the approval just wrote as worked (or the other way round), the
	two disagree and nothing is changed (AC-54)."""
	from alvoraa_portal.payroll_rules_apply import evaluate_attendance

	verdict = evaluate_attendance(row.name)
	if verdict is not None and bool(verdict.held) != (actual["status"] == held_day.HELD):
		access.security_logger().warning("punch_fix engine disagrees attendance=%s", row.name)
		frappe.throw(_("The pay engine would still hold this day. Decline it and ask HR to look at it in "
		               "the Desk."))


# ── the marks on a punch (SEC-6) ─────────────────────────────────────────────

def guard_marks(doc, method=None):
	"""Employee Checkin validate and on_trash: the four marks are written by an
	approval and by nothing else, and a marked punch is never edited or deleted.
	Administrator is the one exception, and the change is logged by id."""
	if frappe.flags.get("in_punch_fix_apply") or not columns_ready():
		return
	before = None if doc.is_new() else doc.get_doc_before_save()
	was_marked = bool(before and (before.get(ADDED) or before.get(ASIDE)))
	trashing = method == "on_trash"
	moved = trashing and bool(doc.get(ADDED) or doc.get(ASIDE))
	if not trashing:
		moved = any(str(doc.get(f) or "") != str((before.get(f) if before else None) or "") for f in MARKS)
		if was_marked:
			moved = moved or any(str(doc.get(f) or "") != str(before.get(f) or "")
			                     for f in ("employee", "log_type", "skip_auto_attendance")) \
				or get_datetime(doc.time) != get_datetime(before.time)
	if not moved:
		return
	if frappe.session.user == "Administrator":
		access.security_logger().warning("punch_fix marked punch changed by Administrator checkin=%s", doc.name)
		return
	access.refuse(_("This punch was added or set aside by an approved fix, so it cannot be changed or "
	                "deleted. Raise a new request to change the day."), "SEC-6",
	              "Employee Checkin " + (method or "validate"), CHECKIN, doc.name)
