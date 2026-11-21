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
from frappe.utils import add_days, cint, flt, get_datetime, getdate, now_datetime

import alvoraa_portal.held_day as held_day
import hrms.alvoraa_hr_core.access as access
from alvoraa_portal.payroll_rules import DUPLICATE_PUNCH_MINUTES

REQUEST = "Attendance Request"
ATTENDANCE = "Attendance"
CHECKIN = "Employee Checkin"

ADDED = "alvoraa_fix_added_request"
ASIDE = "alvoraa_fix_aside_request"
ASIDE_BY = "alvoraa_fix_aside_by"
ASIDE_ON = "alvoraa_fix_aside_on"
MARKS = (ADDED, ASIDE, ASIDE_BY, ASIDE_ON)
HR_ROLES = {"HR User", "HR Manager", "System Manager"}

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
		return bool(frappe.db.has_column(CHECKIN, ASIDE) and frappe.db.has_column(REQUEST, "alvoraa_set_aside"))
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

def day_row(employee, date, for_update=False):
	return frappe.db.get_value(
		ATTENDANCE, {"employee": employee, "attendance_date": getdate(date), "docstatus": 1},
		["name", "employee", "attendance_date", "shift", "status", "company", "in_time",
		 "owner", "attendance_request", "leave_application", "creation", "working_hours",
		 "late_entry", "early_exit"], as_dict=True, for_update=for_update)


def day_state(employee, date, row=None, emp=None):
	"""None when the day can be fixed, else one word: left, unmarked, slip, leave,
	hand, noshift. ONE answer, asked at raise and again at approval (SEC-5). A caller that
	has the employee's status and the day's row already passes them in (the card does)."""
	status = emp.status if emp else frappe.db.get_value("Employee", employee, "status")
	if status != "Active":
		return "left"
	row = row or day_row(employee, date)
	if not row:
		return "unmarked"
	# A day that was Held keeps 085's arrear path (Surbhi, 21 Nov): approval goes through even on a
	# final slip, the slip is never touched, and the day is flagged released-after-final-slip.
	if row.status != held_day.HELD and held_day.is_in_final_slip(employee, date):
		return "slip"
	if row.status == "On Leave" or frappe.db.exists("Leave Application", {
			"employee": employee, "docstatus": 1, "status": "Approved",
			"from_date": ("<=", getdate(date)), "to_date": (">=", getdate(date))}):
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
	return [r for r in rows if getdate(r.shift_start or r.time) == date]


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


def _check_aside(doc):
	"""Each punch to set aside must be this employee's, on this day, and still counting."""
	names = aside_names(doc)
	for name in names:
		row = frappe.db.get_value(CHECKIN, name, ["employee", "time", "shift_start", "skip_auto_attendance", ASIDE],
		                          as_dict=True)
		if not row or row.employee != doc.employee or getdate(row.shift_start or row.time) != getdate(doc.from_date):
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
	# PRIV-2: no note on a Held day (085's rule, kept by Surbhi on 21 Nov).
	if (note or "").strip() and held_day._held_row(me.name, date):
		frappe.throw(_("A held day takes only the time. Leave the note empty."))
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
			        "alvoraa_reviewed_on"], order_by="creation desc", limit_page_length=5):
		if is_punch_fix(r):
			state = ac._state(r)
			out["request"] = {
				"name": r.name, "state": state, "sent_at": str(r.creation)[11:16],
				"time": frappe.utils.get_time(r.alvoraa_missing_time).strftime("%H:%M") if held_day._has_time(r) else None,
				"log_type": r.alvoraa_missing_log, "aside": aside_names(r), "note": r.explanation,
				"hr_note": r.alvoraa_review_note if state in ("declined", "approved") else None,
				"decided_on": str(r.alvoraa_reviewed_on)[:10] if r.alvoraa_reviewed_on else None}
			break
	return out


# ── the card HR reads (the same `outcome` the approval runs) ─────────────────

def card(row):
	"""Now and If approved for one waiting punch fix, plus the token to send back. About eight
	queries a card: each read is made once and handed on (AC-35)."""
	if not columns_ready():
		return {}
	doc = frappe._dict(row)
	req = frappe.db.get_value(REQUEST, doc.name, ["modified", "alvoraa_missing_time", "alvoraa_set_aside"], as_dict=True)
	emp = frappe.db.get_value("Employee", doc.employee, ["status", "user_id"], as_dict=True)
	day = day_row(doc.employee, doc.from_date)
	punches = day_punches(doc.employee, doc.from_date)
	out = {"blocked": day_state(doc.employee, doc.from_date, day, emp), "seen": _token(req.modified, punches),
	       "own_day": bool(emp and emp.user_id == frappe.session.user)}
	if not day:
		return out
	ticked = aside_names(req)
	out["now"] = {"status": day.status, "hours": flt(day.working_hours, 2),
	              "shift": _shift_line(day.shift) if day.shift else None,
	              "punches": [{"time": _hhmm(p.time), "m": _mins(p.time, doc.from_date), "log_type": p.log_type,
	                           "source": _source(p), "aside": bool(p.name in ticked or p.skip_auto_attendance or p.get(ASIDE)),
	                           "ticked": p.name in ticked, "name": p.name} for p in punches]}
	# Q6: HR is told in words when the punch to set aside came from a machine.
	out["sets_aside_machine"] = any(p["ticked"] and p["source"] == _("Machine") for p in out["now"]["punches"])
	if out["blocked"] or not day.shift:
		return out
	logs = held_day._day_logs(doc.employee, doc.from_date, day.shift, ticked)
	add = None
	if held_day._has_time(req):
		log_type, label, when = derive(doc.employee, doc.from_date, req.alvoraa_missing_time, ticked, day.shift, logs)
		add = (when, log_type)
		out["kind"] = label
	try:
		after = outcome(day, add, ticked, logs)
	except Exception:
		return out
	# If approved: what counts, the added punch, and the ticked ones struck through (AC-27).
	shown = ([{"time": _hhmm(x.time), "m": _mins(x.time, doc.from_date), "added": False} for x in logs]
	         + ([{"time": _hhmm(add[0]), "m": _mins(add[0], doc.from_date), "added": True}] if add else [])
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
	ticked = _check_aside(doc)
	user = frappe.session.user
	add = None
	if held_day._has_time(doc):
		log_type, _label, when = derive(doc.employee, doc.from_date, doc.alvoraa_missing_time, ticked, row.shift)
		_check_not_a_repeat(doc, when, ticked)
		add = (when, log_type)
	expected = outcome(row, add, ticked)
	before = _snapshot(row)
	was_held = row.status == held_day.HELD

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
	frappe.logger("alvoraa_portal").info(
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
		frappe.logger("alvoraa_portal").info("punch_fix engine disagrees attendance=%s", row.name)
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
		frappe.logger("alvoraa_portal").info("punch_fix marked punch changed by Administrator checkin=%s", doc.name)
		return
	access.refuse(_("This punch was added or set aside by an approved fix, so it cannot be changed or "
	                "deleted. Raise a new request to change the day."), "SEC-6",
	              "Employee Checkin " + (method or "validate"), CHECKIN, doc.name)
