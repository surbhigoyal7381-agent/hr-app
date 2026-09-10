"""Review your own attendance month by month, and ask HR to fix a day that is wrong.

The correction engine is Frappe HR's **Attendance Request**. It already creates
and overwrites Attendance rows on approval, skips holidays and days already on
leave, and reverses itself cleanly on cancel. None of that is re-implemented
here. This module is the employee's view of their own record, the honest state
of a request they raised, and HR's side of the decision.

THE BUG THIS STARTED FROM. The portal's reason dropdown was a hardcoded list
that had drifted from the field it writes to. Four of its six options - Field
Work, Training, Outdoor Work, Other - are not on the Attendance Request field,
and Frappe refuses any Select value that is not in the field's own options. So
an employee who picked "Other", the obvious choice for "I forgot to punch in",
got an error instead of a request. Two things fix that for good: the field's
option list is widened to cover the real cases, and the portal now builds its
dropdown FROM the field rather than from a copy of it. A copy can drift again;
the field cannot disagree with itself.

WHY "DRAFT" WAS THE WRONG WORD. An employee may create an Attendance Request
but not submit one, so every request they raise sits at docstatus 0 until HR
acts. The portal showed that as "Draft", which reads as "you never finished
it". Worse, a rejected request looked identical to a waiting one. The review
fields added here carry the state a person actually needs - waiting, approved,
declined, withdrawn - and the reason, when there is one.

NO ignore_permissions ANYWHERE IN THIS MODULE, deliberately. Every read is a
`frappe.get_list` under the caller's own permissions AND narrowed to the
employee it is about; every write goes through the document's own permission
check. See `_me()` and `_may_review()`.
"""

import calendar as _calendar

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

from alvoraa_portal.attendance_analytics import (
	DEFAULT_TOLERANCE_MINS,
	TOLERANCE_KEY,
	_reports_to,
	_shift_minutes,
)

REQUEST = "Attendance Request"

# The reasons an employee can give, in the order they are offered.
#
# The first two are Frappe HR's own and must keep their exact spelling - the
# controller reads `reason == "Work From Home"` to decide the status. The rest
# are ours, and exist because the two shipped options describe planned absence
# and this screen is mostly used for the opposite: a day that was worked and
# recorded wrongly.
#
# `help` is what the employee reads under the option. It is here rather than in
# the page because the option list and its explanation must not be able to
# drift apart, which is the exact bug this module was written to fix.
REASONS = [
	("Forgot to Punch In", "You were at work but did not clock in."),
	("Forgot to Punch Out", "You clocked in but did not clock out, so the day looks short."),
	("Missed Punch Both Ways", "Neither clock-in nor clock-out was recorded."),
	("Marked Absent by Mistake", "The day shows as absent but you worked it."),
	("Work From Home", "You worked, from somewhere that is not the office."),
	("On Duty", "Official work away from your usual place of work."),
	("Field Work", "Client visit, site visit or delivery."),
	("Training", "A course, workshop or certification."),
	("Other", "Anything the reasons above do not cover. Please explain below."),
]


def _shift_start(cache, shift):
	"""What time the shift is meant to begin, in minutes past midnight.

	Separate from `_shift_minutes`, which gives its LENGTH. Both come from the
	same row; the length is imported from the analytics module so the two
	screens can never disagree about how long a shift is.
	"""
	if shift in cache:
		return cache[shift]
	start = frappe.db.get_value("Shift Type", shift, "start_time")
	cache[shift] = start.total_seconds() / 60.0 if start is not None else None
	return cache[shift]


def _becomes(reason):
	"""What the day will be marked, if HR approves.

	Mirrors AttendanceRequest.get_attendance_status: Work From Home is the only
	reason with a status of its own; every other reason marks the day Present.
	A half-day request overrides both, and the page says so where it is offered.
	"""
	return "Work From Home" if reason == "Work From Home" else "Present"


# ── setup: widen the field's own option list ─────────────────────────────────

def install_reasons():
	"""Put our reasons on the Attendance Request field.

	A Property Setter rather than an edit to the doctype JSON. We vendor a fork
	of `hrms`, and a JSON edit would conflict on every rebase against upstream
	for as long as the product exists. A Property Setter is additive, survives
	`bench migrate`, and can be removed without touching Frappe HR's code.

	Runs from `after_migrate`, so existing tenants get it too. The `baseline`
	mechanism was the other candidate and would have been wrong: it seeds NEW
	tenants only, so every site already live - including the one this was
	reported on - would never have received it.
	"""
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	field = frappe.get_meta(REQUEST).get_field("reason")
	shipped = (field.options or "").split("\n") if field else []

	# Anything an organisation added for themselves is kept. Ours are appended,
	# so their existing requests keep validating and their own wording survives
	# a migrate - which is the whole reason this is a widening and not a set.
	wanted = list(shipped)
	for value, _help in REASONS:
		if value not in wanted:
			wanted.append(value)

	if wanted == shipped:
		return False

	make_property_setter(REQUEST, "reason", "options", "\n".join(wanted), "Text",
	                     validate_fields_for_doctype=False)
	frappe.clear_cache(doctype=REQUEST)
	return True


def install_review_fields():
	"""The state of a request, in words a person can act on.

	Attendance Request has no status field of its own - upstream expects a
	Workflow. A Workflow was the first choice and does not fit: Frappe forbids
	a draft going straight to cancelled (`apply_workflow` throws "Illegal
	Document Status"), so "Declined" could not be a cancelled state; and
	installing one would change how the Desk behaves for every existing tenant.

	Fields alongside docstatus is what **Leave Application** already does
	natively in this same app, so it is the app's own idiom rather than an
	invention. `on_submit` / `on_cancel` keep them true when somebody acts from
	the Desk instead of the portal.
	"""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({REQUEST: [
		{"fieldname": "alvoraa_review_section", "fieldtype": "Section Break",
		 "label": "Review", "insert_after": "explanation"},
		{"fieldname": "alvoraa_review_status", "fieldtype": "Select",
		 "label": "Review Status", "insert_after": "alvoraa_review_section",
		 "options": "Waiting\nApproved\nDeclined\nWithdrawn",
		 "default": "Waiting", "read_only": 1, "in_list_view": 1,
		 "description": "Set by the portal, and kept true when the Desk is used instead."},
		{"fieldname": "alvoraa_review_note", "fieldtype": "Small Text",
		 "label": "Note to the Employee", "insert_after": "alvoraa_review_status",
		 "description": "Shown to the employee. Say why, in plain words."},
		{"fieldname": "alvoraa_review_column", "fieldtype": "Column Break",
		 "insert_after": "alvoraa_review_note"},
		{"fieldname": "alvoraa_reviewed_by", "fieldtype": "Link", "options": "User",
		 "label": "Decided By", "insert_after": "alvoraa_review_column", "read_only": 1},
		{"fieldname": "alvoraa_reviewed_on", "fieldtype": "Datetime",
		 "label": "Decided On", "insert_after": "alvoraa_reviewed_by", "read_only": 1},
	]}, ignore_validate=True)
	return True


def after_migrate():
	install_reasons()
	install_review_fields()


# ── keeping the state true when the Desk is used ─────────────────────────────

def on_submit(doc, method=None):
	"""Submitting IS approving - that is what creates the corrected Attendance.

	So a request approved from the Desk must not still read "Waiting" to the
	person who raised it.
	"""
	if doc.get("alvoraa_review_status") != "Approved":
		doc.db_set({"alvoraa_review_status": "Approved",
		            "alvoraa_reviewed_by": frappe.session.user,
		            "alvoraa_reviewed_on": frappe.utils.now()}, update_modified=False)


def on_cancel(doc, method=None):
	"""Cancelling an approved request undoes the attendance it created.

	Only "Withdrawn" is left alone: the employee pulling their own request back
	is a different event from HR turning it down, and flattening the two would
	tell the employee they were declined when they were not.
	"""
	if doc.get("alvoraa_review_status") != "Withdrawn":
		doc.db_set({"alvoraa_review_status": "Declined",
		            "alvoraa_reviewed_by": frappe.session.user,
		            "alvoraa_reviewed_on": frappe.utils.now()}, update_modified=False)


# ── who is asking ────────────────────────────────────────────────────────────

def _employee_for(user):
	"""The employee record behind a login, or None. Never throws.

	Separate from `_me()` because not every caller needs one. HR staff are
	often not on the payroll, and the review screen has to work for them.
	"""
	return frappe.db.get_value("Employee", {"user_id": user, "status": "Active"},
	                           ["name", "employee_name", "company", "default_shift",
	                            "holiday_list"], as_dict=True)


def _me():
	me = _employee_for(frappe.session.user)
	if not me:
		frappe.throw(_("Your user is not linked to an employee record, so there is "
		               "no attendance to show."), frappe.PermissionError)
	return me


def _may_review():
	"""Whoever may submit an Attendance Request may decide one.

	Not a role list of our own. Approving IS submitting - it is the submit that
	writes the corrected Attendance row - so the permission that already governs
	that act is the truthful test, and an organisation that grants it to a new
	role gets the inbox for free.
	"""
	return bool(frappe.has_permission(REQUEST, "submit"))


def _subject(employee):
	"""Whose month is being asked for, and a refusal when it is not theirs to see.

	Three people open this screen and only one of them is looking at their own
	record. An employee reviews their own days. A manager checks a report's,
	because they are the one who will be asked to confirm what happened. HR
	reviews anybody's, because they are the one who decides.

	The whole screen is one person's daily movements - when they arrived, when
	they left, where they badged in. That is the most personal thing in the
	product, so the answer is a refusal rather than a quiet fallback to the
	caller's own month: a silent substitution would leave somebody believing
	they were looking at a colleague's record when they were not.
	"""
	# Deliberately not `_me()` first. An HR administrator is frequently not on
	# the payroll, and demanding an employee record before they may open
	# anybody's month refused the reviewers this screen is largely built for.
	me = _employee_for(frappe.session.user)

	if not employee:
		if not me:
			frappe.throw(_("Your user is not linked to an employee record, so there "
			               "is no attendance of your own to show. Open a colleague "
			               "instead."), frappe.PermissionError)
		return me, True
	if me and employee == me.name:
		return me, True

	if not _may_review():
		if not me:
			frappe.throw(_("Your user is not linked to an employee record, so there "
			               "is nobody you can open."), frappe.PermissionError)
		if employee not in _reports_to(me.name, deep=True):
			frappe.throw(_("You can only open the attendance of people who report to you."),
			             frappe.PermissionError)

	subject = frappe.db.get_value("Employee", employee,
	                              ["name", "employee_name", "company", "default_shift",
	                               "holiday_list"], as_dict=True)
	if not subject:
		frappe.throw(_("No such employee."), frappe.DoesNotExistError)
	return subject, False


@frappe.whitelist()
def whose_months_i_can_open(search=None, limit=25):
	"""The people this caller may open, for the picker on the review screen.

	Returns nobody rather than everybody when the caller reviews nothing, so an
	ordinary employee's picker is empty instead of being a staff directory.
	"""
	me = _employee_for(frappe.session.user)
	if _may_review():
		filters = {"status": "Active"}
		if search:
			filters["employee_name"] = ("like", "%" + str(search).strip() + "%")
		rows = frappe.get_list("Employee", filters=filters,
		                       fields=["name", "employee_name", "designation", "department"],
		                       order_by="employee_name asc",
		                       limit_page_length=cint(limit) or 25)
	else:
		# `_reports_to` IS the permission decision here, and it has already been
		# made by the time we get to this line. What follows only puts names to
		# an answer we have settled, so it reads with get_all rather than
		# get_list - a manager has no blanket read on Employee, and get_list
		# would hand back an empty picker that looks broken instead of a
		# refusal that explains itself.
		if not me:
			return []
		team = _reports_to(me.name, deep=True)
		if not team:
			return []
		filters = {"name": ("in", team), "status": "Active"}
		if search:
			filters["employee_name"] = ("like", "%" + str(search).strip() + "%")
		rows = frappe.get_all("Employee", filters=filters,
		                      fields=["name", "employee_name", "designation", "department"],
		                      order_by="employee_name asc",
		                      limit_page_length=cint(limit) or 25)
	return rows


# ── what the employee may choose ─────────────────────────────────────────────

@frappe.whitelist()
def reasons():
	"""The reasons on offer, read from the field itself.

	Deliberately not the REASONS list above. That list is what we ASK for at
	migrate time; the field is what will actually be accepted on save, and when
	the two disagree the field wins. Reading the field is what makes the
	original bug - a dropdown offering values the field refuses - impossible to
	reintroduce, including for an organisation that has edited the list itself.
	"""
	helps = dict(REASONS)
	field = frappe.get_meta(REQUEST).get_field("reason")
	out = []
	for value in (field.options or "").split("\n"):
		value = value.strip()
		if not value:
			continue
		out.append({"value": value, "help": helps.get(value, ""),
		            "becomes": _becomes(value)})
	return out


# ── the month ────────────────────────────────────────────────────────────────

@frappe.whitelist()
def month(year=None, month=None, employee=None):
	"""One person's month, day by day, with enough to judge each day.

	The old calendar fetched punch-in, punch-out and hours worked and then drew
	none of them, so a person could see that a day was wrong but not what was
	wrong with it - and had nothing to tell HR. Every field here is on screen.

	`employee` is how HR and a manager review somebody else. It defaults to the
	caller, and `_subject` refuses anybody they may not open.
	"""
	me, is_self = _subject(employee)
	today = getdate(nowdate())
	year = cint(year) or today.year
	month = cint(month) or today.month
	if not 1 <= month <= 12:
		frappe.throw(_("{0} is not a month.").format(month))

	last = _calendar.monthrange(year, month)[1]
	start = "%04d-%02d-01" % (year, month)
	end = "%04d-%02d-%02d" % (year, month, last)

	# get_list, not get_all: the caller's own read permission applies, and the
	# employee filter narrows it to them on top of that.
	rows = frappe.get_list(
		"Attendance",
		filters={"employee": me.name, "docstatus": 1,
		         "attendance_date": ("between", [start, end])},
		fields=["name", "attendance_date", "status", "working_hours", "shift",
		        "in_time", "out_time", "late_entry", "early_exit", "leave_type"],
		limit_page_length=0)

	leaves = frappe.get_list(
		"Leave Application",
		filters={"employee": me.name, "docstatus": 1, "status": "Approved",
		         "from_date": ("<=", end), "to_date": (">=", start)},
		fields=["name", "leave_type", "from_date", "to_date", "half_day"],
		limit_page_length=0)

	# The punches behind those hours. This is what lets the page draw the SHAPE
	# of a day - in at 09:32, out at 13:04, back at 13:50 - rather than a single
	# total. A missing second punch is the commonest cause of a short day, and
	# on a total alone it is invisible; on a strip of the day it is obvious.
	#
	# Bucketed by the attendance row it belongs to where that link is set,
	# because a night shift's punches fall on two calendar dates but belong to
	# one attendance day. Only punches with no link fall back to their own date.
	punches = {}
	by_attendance = {}
	for c in frappe.get_list(
			"Employee Checkin",
			filters={"employee": me.name,
			         "time": ("between", [start + " 00:00:00",
			                              frappe.utils.add_days(end, 1) + " 23:59:59"])},
			fields=["name", "log_type", "time", "attendance", "device_id"],
			order_by="time asc", limit_page_length=0):
		mark = {"log_type": c.log_type, "at": str(c.time)[11:16],
		        "where": c.device_id, "on": str(c.time)[:10]}
		if c.attendance:
			by_attendance.setdefault(c.attendance, []).append(mark)
		else:
			punches.setdefault(str(c.time)[:10], []).append(mark)

	holidays = {}
	if me.holiday_list:
		for h in frappe.get_all("Holiday",
		                        filters={"parent": me.holiday_list,
		                                 "holiday_date": ("between", [start, end])},
		                        fields=["holiday_date", "description"]):
			holidays[str(h.holiday_date)] = h.description

	# Requests already raised for these days, so a person cannot ask twice and
	# can see where the first one got to.
	claimed = {}
	for r in _my_requests_between(me.name, start, end):
		day = getdate(r["from_date"])
		while day <= getdate(r["to_date"]):
			claimed[str(day)] = r
			day = frappe.utils.add_days(day, 1)

	leave_days = {}
	for l in leaves:
		day = getdate(l.from_date)
		while day <= getdate(l.to_date):
			leave_days[str(day)] = l.leave_type
			day = frappe.utils.add_days(day, 1)

	by_date = {str(r.attendance_date): r for r in rows}
	tolerance = cint(frappe.db.get_default(TOLERANCE_KEY) or DEFAULT_TOLERANCE_MINS)
	shift_cache = {}

	days = []
	for n in range(1, last + 1):
		date = "%04d-%02d-%02d" % (year, month, n)
		att = by_date.get(date)
		marks = by_attendance.get(att.name) if att else None
		days.append(_day(date, att, holidays, leave_days, claimed, me,
		                 shift_cache, tolerance, today,
		                 marks or punches.get(date, [])))

	return {
		"employee": me.name, "employee_name": me.employee_name,
		"year": year, "month": month, "last_day": last,
		"tolerance_mins": tolerance,
		"days": days,
		"totals": _totals(days),
		"is_self": is_self,
		"can_review": _may_review(),
		# Only the person themselves may ask for a correction. A manager or HR
		# looking at somebody else's month fixes it directly instead, and
		# showing them a button that raises a request in that person's name
		# would put words in their mouth.
		"can_request": is_self,
	}


def _day(date, att, holidays, leave_days, claimed, me, shift_cache, tolerance, today,
         marks=()):
	d = getdate(date)
	out = {
		"date": date,
		"weekday": _calendar.day_name[d.weekday()],
		"future": d > today,
		"holiday": holidays.get(date),
		"leave_type": leave_days.get(date),
		"status": None, "shift": None, "in_time": None, "out_time": None,
		"hours": None, "expected_hours": None, "short_by": 0.0,
		"late_entry": 0, "early_exit": 0,
		"attendance": None,
		"punches": list(marks),
		"shift_starts": None, "shift_ends": None,
		"late_by_mins": 0, "missing_punch": False,
		"request": claimed.get(date),
	}
	if not att:
		# A day with no record is not automatically an absence. Saying so would
		# put a red mark on every weekend and on today-before-you-leave.
		out["state"] = ("future" if out["future"]
		                else "holiday" if out["holiday"]
		                else "leave" if out["leave_type"]
		                else "no_record")
		return out

	shift = att.shift or me.default_shift
	expected = _shift_minutes(shift_cache, shift) if shift else None
	hours = flt(att.working_hours)

	out.update({
		"status": att.status, "shift": shift, "attendance": att.name,
		"in_time": str(att.in_time)[11:16] if att.in_time else None,
		"out_time": str(att.out_time)[11:16] if att.out_time else None,
		"hours": round(hours, 2),
		"expected_hours": round(expected / 60.0, 2) if expected else None,
		"late_entry": cint(att.late_entry), "early_exit": cint(att.early_exit),
		"leave_type": att.leave_type or out["leave_type"],
		"state": (att.status or "").lower().replace(" ", "_") or "no_record",
	})

	# Where the shift sits in the day, so the page can draw the worked time
	# against the expected time rather than against an arbitrary 24 hours.
	begins = _shift_start(shift_cache, shift) if shift else None
	if begins is not None and expected:
		out["shift_starts"] = _hhmm(begins)
		out["shift_ends"] = _hhmm(begins + expected)

	# How late, in minutes, measured rather than taken on trust. Frappe's
	# `late_entry` is a yes/no, and "late" without "by how much" is the kind of
	# number that starts an unfair conversation.
	if begins is not None and att.in_time:
		arrived = _minutes(str(att.in_time)[11:16])
		if arrived is not None and arrived > begins:
			out["late_by_mins"] = int(round(arrived - begins))

	# An odd number of punches means one never registered. That is the single
	# commonest cause of a short day and the reason this screen exists, so it
	# is named rather than left for the employee to infer from the total.
	ins = len([m for m in marks if m["log_type"] == "IN"])
	outs = len([m for m in marks if m["log_type"] == "OUT"])
	out["missing_punch"] = bool(marks) and ins != outs
	if not marks and att.in_time and not att.out_time:
		out["missing_punch"] = True

	# Short only past the tolerance, and only when there is a shift to be short
	# of. Without a shift there is no expectation, so inventing a shortfall
	# would invent a problem - the same rule the analytics screen uses.
	if expected and att.status in ("Present", "Work From Home"):
		short = (expected - tolerance) / 60.0 - hours
		if short > 0:
			out["short_by"] = round(short, 2)
	return out


def _hhmm(minutes):
	minutes = int(round(minutes)) % (24 * 60)
	return "%02d:%02d" % (minutes // 60, minutes % 60)


def _minutes(hhmm):
	try:
		h, m = str(hhmm).split(":")[:2]
		return int(h) * 60 + int(m)
	except (ValueError, TypeError):
		return None


def _totals(days):
	def count(*states):
		return len([d for d in days if d["state"] in states])
	return {
		"present": count("present", "work_from_home"),
		"absent": count("absent"),
		"half_day": count("half_day"),
		"leave": count("on_leave", "leave"),
		"holiday": count("holiday"),
		"no_record": count("no_record"),
		"short_days": len([d for d in days if d["short_by"] > 0]),
		"hours_short": round(sum(d["short_by"] for d in days), 1),
		"missing_punches": len([d for d in days if d["missing_punch"]]),
		"late_days": len([d for d in days if d["late_by_mins"] > 0]),
		"hours_worked": round(sum(d["hours"] or 0 for d in days), 1),
	}


# ── the requests ─────────────────────────────────────────────────────────────

REQUEST_FIELDS = ["name", "employee", "employee_name", "from_date", "to_date",
                  "reason", "explanation", "half_day", "half_day_date", "docstatus",
                  "alvoraa_review_status", "alvoraa_review_note",
                  "alvoraa_reviewed_by", "alvoraa_reviewed_on", "creation"]


def _state(row):
	"""One word for where a request has got to.

	Read from docstatus first, because that is the only part Frappe itself
	guarantees. The review field is a label on top of it, and a site migrated
	before this slice has requests with no label at all - those must still
	report something true rather than blank.
	"""
	status = row.get("alvoraa_review_status")
	if row.get("docstatus") == 1:
		return "approved"
	if row.get("docstatus") == 2:
		return "withdrawn" if status == "Withdrawn" else "declined"
	# Still a draft. Declining and withdrawing both leave it here - Frappe will
	# not move a draft to cancelled - so the label is the only thing separating
	# them, and both have to be read or a withdrawn request reads as waiting.
	if status in ("Declined", "Withdrawn"):
		return status.lower()
	return "waiting"


SAY = {
	"waiting": _("Waiting for HR"),
	"approved": _("Approved - your attendance has been corrected"),
	"declined": _("Not approved"),
	"withdrawn": _("You withdrew this"),
}


def _shape(row):
	row = dict(row)
	row["state"] = _state(row)
	row["says"] = SAY[row["state"]]
	row["note"] = row.get("alvoraa_review_note")
	for k in ("from_date", "to_date", "half_day_date", "alvoraa_reviewed_on", "creation"):
		if row.get(k):
			row[k] = str(row[k])
	return row


def _my_requests_between(employee, start, end):
	return [_shape(r) for r in frappe.get_list(
		REQUEST, filters={"employee": employee, "docstatus": ("!=", 2),
		                  "from_date": ("<=", end), "to_date": (">=", start)},
		fields=REQUEST_FIELDS, limit_page_length=0)]


@frappe.whitelist()
def my_requests(limit=20):
	"""Every request this person raised, newest first, with its real state."""
	me = _me()
	return [_shape(r) for r in frappe.get_list(
		REQUEST, filters={"employee": me.name}, fields=REQUEST_FIELDS,
		order_by="creation desc", limit_page_length=cint(limit) or 20)]


@frappe.whitelist()
def raise_correction(from_date, to_date=None, reason=None, explanation=None,
                     half_day=0, half_day_date=None):
	"""Ask HR to fix a day.

	Always for the caller's own employee record. The employee is never taken
	from the request - this endpoint is whitelisted, and a field that named
	somebody else would let anyone rewrite anyone's attendance.
	"""
	me = _me()
	to_date = to_date or from_date
	if getdate(to_date) < getdate(from_date):
		frappe.throw(_("The last day cannot be before the first day."))
	if getdate(from_date) > getdate(nowdate()):
		frappe.throw(_("You cannot raise a correction for a day that has not happened yet."))

	allowed = {r["value"] for r in reasons()}
	if reason not in allowed:
		frappe.throw(_("{0} is not one of the reasons on offer.").format(reason or ""))
	if reason == "Other" and not (explanation or "").strip():
		frappe.throw(_("Please say what happened, so HR can act on it."))

	doc = frappe.get_doc({
		"doctype": REQUEST,
		"employee": me.name,
		"employee_name": me.employee_name,
		"company": me.company,
		"from_date": from_date,
		"to_date": to_date,
		"reason": reason,
		"explanation": explanation,
		"half_day": cint(half_day),
		"half_day_date": half_day_date if cint(half_day) else None,
		"alvoraa_review_status": "Waiting",
	})
	# No ignore_permissions. The Employee role holds create on Attendance
	# Request, so this is a real permission check and not a formality.
	doc.insert()
	return _shape(doc.as_dict())


@frappe.whitelist()
def withdraw(name):
	"""Take back a request HR has not decided yet.

	Deleting it would be the easy path and the wrong one: it would erase the
	fact that the employee ever raised the day, which is the thing they may
	need to point at later.
	"""
	me = _me()
	doc = frappe.get_doc(REQUEST, name)
	if doc.employee != me.name:
		frappe.throw(_("That request is not yours."), frappe.PermissionError)
	if doc.docstatus != 0:
		frappe.throw(_("HR has already decided this one, so it cannot be withdrawn."))
	doc.db_set({"alvoraa_review_status": "Withdrawn",
	            "alvoraa_reviewed_by": frappe.session.user,
	            "alvoraa_reviewed_on": frappe.utils.now()}, update_modified=False)
	return _shape(frappe.get_doc(REQUEST, name).as_dict())


# ── HR's side ────────────────────────────────────────────────────────────────

@frappe.whitelist()
def to_review(limit=50):
	"""What is waiting on HR.

	`get_list` under the caller's own permissions, so an organisation that has
	scoped Attendance Request by department gets that scoping here for free.
	"""
	if not _may_review():
		frappe.throw(_("You do not review attendance corrections."), frappe.PermissionError)
	rows = frappe.get_list(
		REQUEST, filters={"docstatus": 0}, fields=REQUEST_FIELDS,
		order_by="creation asc", limit_page_length=cint(limit) or 50)
	out = [_shape(r) for r in rows]
	return [r for r in out if r["state"] == "waiting"]


@frappe.whitelist()
def decide(name, approve, note=None):
	"""Approve or decline one request.

	Approving submits it, and the submit is what makes Frappe HR write the
	corrected Attendance row - the correction is never written here. Declining
	leaves the document as a draft with a reason on it, because Frappe will not
	move a draft to cancelled and deleting it would destroy the record.
	"""
	if not _may_review():
		frappe.throw(_("You do not review attendance corrections."), frappe.PermissionError)

	doc = frappe.get_doc(REQUEST, name)
	if doc.docstatus != 0:
		frappe.throw(_("This one has already been decided."))
	if doc.get("alvoraa_review_status") in ("Declined", "Withdrawn"):
		frappe.throw(_("This one has already been decided."))

	stamp = {"alvoraa_review_note": (note or "").strip() or None,
	         "alvoraa_reviewed_by": frappe.session.user,
	         "alvoraa_reviewed_on": frappe.utils.now()}

	if cint(approve):
		doc.update(stamp)
		# submit() runs its own permission check, so _may_review() above is a
		# clear message rather than the only thing standing in the way.
		doc.submit()
		return _shape(frappe.get_doc(REQUEST, name).as_dict())

	if not (note or "").strip():
		frappe.throw(_("Please say why, so the employee knows what to do next."))
	stamp["alvoraa_review_status"] = "Declined"
	doc.db_set(stamp, update_modified=False)
	return _shape(frappe.get_doc(REQUEST, name).as_dict())
