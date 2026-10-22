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

A manager raising a correction for a report is permitted by the permission
system rather than past it: `manager_scope` grants one User Permission per
manager, per report, scoped to four doctypes and never to all of them.
"""

import calendar as _calendar
from datetime import datetime, time, timedelta

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, getdate, nowdate

from alvoraa_portal.call_cache import holiday_list_for
from alvoraa_portal.attendance_analytics import (
	DEFAULT_TOLERANCE_MINS,
	TOLERANCE_KEY,
	_reports_to,
	_shift_grace,
	_shift_minutes,
	_shift_row,
	org_late_grace,
)

REQUEST = "Attendance Request"

# Who files punches for the biometric machines (ALV-210): DTC's hand-made
# `biometric.sync@...` account and the product's own `attendance.sync@<site>`
# (slice 041). Administrator runs the imports. Anybody else filed it by hand.
MACHINE_OWNERS = ("biometric.sync@", "attendance.sync@")

# ALV-211. Surbhi's rule: every client's shift accepts punches 3 hours before
# it starts and 3 hours after it ends. Frappe's 1-hour default left a late
# out-punch unlinked, the day counted 0 hours and was marked Absent (DTC, 535
# days).
SHIFT_WINDOW_MINS = 180

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

	Separate from `_shift_minutes`, which gives its LENGTH. Both read the same
	cached row through `_shift_row`, so the two screens can never disagree
	about a shift - and neither can read the other's answer by mistake, which
	is what used to happen and is why a 09:30 shift was judged from 09:00.
	"""
	row = _shift_row(cache, shift)
	if not row or row.start_time is None:
		return None
	return row.start_time.total_seconds() / 60.0


def _becomes(reason):
	"""What the day will be marked, if HR approves.

	Mirrors AttendanceRequest.get_attendance_status: Work From Home is the only
	reason with a status of its own; every other reason marks the day Present.
	A half-day request overrides both, and the page says so where it is offered.
	"""
	return "Work From Home" if reason == "Work From Home" else "Present"


# ── setup: widen the field's own option list ─────────────────────────────────

def default_shift_window(doc, method=None):
	"""Shift Type before_insert (ALV-211): Frappe's 60-minute default, or an
	empty field, becomes SHIFT_WINDOW_MINS. Any other figure somebody typed is
	kept."""
	for field in ("begin_check_in_before_shift_start_time",
	              "allow_check_out_after_shift_end_time"):
		if doc.get(field) in (None, "") or cint(doc.get(field)) == 60:
			doc.set(field, SHIFT_WINDOW_MINS)


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
		# 045 AC-82 / SEC-19. WHO decided is already recorded. This records in
		# WHAT CAPACITY, and no existing field can carry it.
		#
		# The alternative was to work the capacity out at read time, by asking
		# whether the decider was the employee's `reports_to` user. It was
		# rejected: `reports_to` changes, so the same record would answer
		# differently next year - and the year in question is exactly the year
		# somebody raises a grievance about this approval.
		#
		# **No default, and no backfill.** Every request decided before this
		# ships keeps an EMPTY value, which the screen reads as "not recorded".
		# Defaulting it to "Manager" would put a claim in the record that
		# nobody made.
		{"fieldname": "alvoraa_decided_as", "fieldtype": "Select",
		 "label": "Decided As", "insert_after": "alvoraa_reviewed_on",
		 "options": "\nManager\nHR", "read_only": 1,
		 "description": "The capacity the decision was made in. Empty means it "
		                "was decided before this was recorded."},
	]}, ignore_validate=True)
	return True


def after_migrate():
	"""Wired to BOTH after_migrate and after_install.

	after_migrate alone was not enough, and CI caught it: a site is built with
	`bench install-app`, which never runs a migrate, so the columns were simply
	absent and every write to them failed with "Unknown column". That was not a
	CI quirk - a brand new tenant would have been missing them in exactly the
	same way.

	Guarded on the doctype existing because install order is not ours to
	choose. A site that installs this app before Frappe HR gets nothing here
	and picks it up on the next migrate, rather than failing the install.
	"""
	if not frappe.db.exists("DocType", REQUEST):
		return False
	install_reasons()
	install_review_fields()
	return True


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

	`search` matches the two things a person is known by - their name and their
	employee ID - because HR knows half the company by ID and nobody knows 403
	people by name. Frappe ANDs `or_filters` with `filters` as one bracketed
	group, so the Active-and-in-my-line narrowing below still holds for every
	row a search returns: a manager cannot type their way out of their own
	reporting line.
	"""
	me = _employee_for(frappe.session.user)
	term = str(search or "").strip()
	named = ({"employee_name": ("like", "%" + term + "%"),
	          "name": ("like", "%" + term + "%")} if term else None)
	if _may_review():
		rows = frappe.get_list("Employee", filters={"status": "Active"},
		                       or_filters=named,
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
		rows = frappe.get_all("Employee", filters={"name": ("in", team), "status": "Active"},
		                      or_filters=named,
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
	# Whoever is asking, when that is not the subject. Only `can_request`
	# below needs it, so somebody's own month does not pay for the read.
	asker = None if is_self else _employee_for(frappe.session.user)
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
	# ALV-210. A punch HR typed in carries the person's own badge number as its
	# "device" (HR-EMP-00171 on 14 Oct showed "830"), which reads as a machine
	# nobody owns. Such a punch, or one filed by somebody other than the
	# machines and the person themselves, says "added by HR" instead.
	own = frappe.db.get_value("Employee", me.name,
	                          ["attendance_device_id", "user_id"], as_dict=True) or {}
	for c in frappe.get_list(
			"Employee Checkin",
			filters={"employee": me.name,
			         "time": ("between", [start + " 00:00:00",
			                              frappe.utils.add_days(end, 1) + " 23:59:59"])},
			fields=["name", "log_type", "time", "attendance", "device_id", "owner"],
			order_by="time asc", limit_page_length=0):
		by_hand = ((c.device_id and c.device_id == own.get("attendance_device_id"))
		           or (c.owner not in ("Administrator", own.get("user_id"))
		               and not (c.owner or "").startswith(MACHINE_OWNERS)))
		mark = {"log_type": c.log_type, "at": str(c.time)[11:16],
		        "where": _("added by HR") if by_hand else c.device_id,
		        "on": str(c.time)[:10]}
		if c.attendance:
			by_attendance.setdefault(c.attendance, []).append(mark)
		else:
			punches.setdefault(str(c.time)[:10], []).append(mark)

	# `weekly_off` tells a Sunday apart from Diwali (043 AC-1). Both arrive as
	# Holiday rows on the same list and only this flag says which is which, so
	# without it the calendar has to draw them the same - and a person's week
	# then looks like a month of public holidays. It is read here, beside the
	# rest of the day, rather than derived from the weekday somewhere else: a
	# tenant whose staff are off on Thursdays is the reason this is data.
	holidays = {}
	weekly_offs = set()
	# WHICH list, and why this changed (043). This read used `me.holiday_list`
	# - the field on the Employee record. Frappe HR does not: it answers
	# "which holiday list is this person on" from Holiday List Assignment, and
	# `hr_api._own_upcoming_holidays` was moved onto that in slice 035 after
	# store staff at PP Jewellers were shown Head Office's holidays.
	#
	# So the calendar and the days-off card beside it could draw two different
	# lists for one person, and the calendar's was the one payroll ignores. The
	# assignment wins now; `me.holiday_list` is the fallback, so a tenant that
	# only ever set the Employee field keeps exactly the calendar it had.
	holiday_list = holiday_list_for(me.name, end) or me.holiday_list
	if holiday_list:
		for h in frappe.get_all("Holiday",
		                        filters={"parent": holiday_list,
		                                 "holiday_date": ("between", [start, end])},
		                        fields=["holiday_date", "description", "weekly_off"]):
			holidays[str(h.holiday_date)] = h.description
			if cint(h.weekly_off):
				weekly_offs.add(str(h.holiday_date))

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
		                 marks or punches.get(date, []), weekly_offs))

	# DIRECT REPORTS, FOR EVERYBODY - HR INCLUDED (18 Oct 2026). `can_request`
	# has always been "their own day, or a direct report's", and HR gets it only
	# where they genuinely are somebody's manager. `team_days` disagreed: it
	# handed HR the button on every row, so one HR user got no button here and a
	# button on all of them there. Settled THIS way, not the other:
	#
	#   * the raiser should not be the decider. `decide` refuses a person
	#     deciding their OWN record, not a person deciding what they themselves
	#     raised, so the only thing keeping HR's two hats apart is not offering
	#     the button;
	#   * HR loses nothing. They already decide every request, and their own
	#     route - the Attendance Request itself - is deliberately outside this
	#     window, which is the way round for an old day;
	#   * one rule instead of two. `team_days` now computes the same answer with
	#     the same call, so the two screens cannot drift apart again.
	can_request = is_self or bool(
		asker and me.name in _reports_to(asker.name, deep=False))
	# The tenant's switch. Never applied to somebody's own day: neither setting
	# may narrow what a person asks about their own attendance.
	if can_request and not is_self and not manager_on_behalf_on():
		can_request = False

	# Only a MANAGER filing for somebody else is bound by the window. Their own
	# month is not - `raise_for_report` says the same, and this must not invent
	# a limit the guard would not enforce. None, which blank now gives, means
	# the screen hides nothing.
	filing_from, filing_basis = None, None
	if can_request and not is_self:
		filing_from, filing_basis = manager_filing_from(me.name)
	return {
		"employee": me.name, "employee_name": me.employee_name,
		"year": year, "month": month, "last_day": last,
		"tolerance_mins": tolerance,
		"late_grace_mins": org_late_grace(),
		"days": days,
		"totals": _totals(days),
		"is_self": is_self,
		"can_review": _may_review(),
		# Who may ask HR to fix a day on this record: the person themselves, or
		# their DIRECT manager.
		#
		# This was `is_self` alone, under a comment saying that a manager
		# raising one in somebody's name would put words in their mouth.
		# Surbhi settled the question the other way on 15 Oct 2026 - "let's get
		# the manager request the changes and the HR to confirm or reject it" -
		# and `raise_for_report` stamps "Raised by X on behalf of the employee"
		# on what it creates, so HR reads a request that says who is vouching
		# for the day instead of one that looks like the employee's own. The
		# words are no longer in anybody's mouth, so the reason for the old
		# answer has gone.
		#
		# DIRECT reports only, the same bound `raise_for_report` enforces
		# (Surbhi, 17 Oct 2026: "direct reports only"). It is worked out with
		# the same call for that reason: a flag that disagreed with the guard
		# would show a button that refuses when pressed. READING still reaches
		# the whole line, so a skip-level month opens as before - it is simply
		# read-only, and the screen says whose job it is.
		#
		# HR is NOT given it. They decide corrections; a reviewer who could
		# raise one as well would be deciding their own request, which SEC-9
		# forbids and `decide` already refuses.
		#
		# `asker` is read only on the path that needs it, so an employee
		# opening their own month still costs exactly the queries it did.
		"can_request": can_request,
		# THE OLDEST DAY THAT CALLER MAY FILE FOR, or None where no window
		# binds them. Returned so the screen can stop OFFERING a day it would
		# then refuse.
		#
		# `can_request` answers "may this person raise here at all", which is
		# a question about the MONTH. The filing window is a question about
		# the DAY, and the two were not the same: the form appeared on every
		# day of a report's month and the server refused the old ones with a
		# 417 - correctly, and invisibly, so it read as a dead button.
		# Surbhi, 18 Oct 2026: "if that is the case manager shouldn't be
		# allowed to raise request for that day, meaning the form shouldn't
		# be visible to them."
		#
		# One value, not a flag per day: the window is a single boundary, so
		# the screen compares each date against it. Worked out with the SAME
		# call the guard uses, for the same reason `can_request` is - a
		# boundary that disagreed with the guard would just move the dead
		# button rather than remove it.
		"can_request_from": filing_from,
		"can_request_basis": filing_basis,
		# Whether the TENANT allows the on-behalf path at all. Sent so the day
		# detail can say "your organisation does not allow this" instead of
		# "only this person or their manager can ask" - which would be untrue
		# with the switch off, because then their manager cannot either.
		"on_behalf_enabled": manager_on_behalf_on(),
	}


def _day(date, att, holidays, leave_days, claimed, me, shift_cache, tolerance, today,
         marks=(), weekly_offs=()):
	d = getdate(date)
	out = {
		"date": date,
		"weekday": _calendar.day_name[d.weekday()],
		"future": d > today,
		"holiday": holidays.get(date),
		# True for a weekly off, False for a named public holiday. Kept beside
		# `holiday` rather than replacing it: `state` stays exactly what it was,
		# so the review screen and every existing test still read the same day
		# the same way, and the calendar gains the one fact it was missing.
		"weekly_off": date in weekly_offs,
		"leave_type": leave_days.get(date),
		"status": None, "shift": None, "in_time": None, "out_time": None,
		"hours": None, "expected_hours": None, "short_by": 0.0,
		"late_entry": 0, "early_exit": 0, "is_late": False, "grace_mins": 0,
		# WHERE the grace came from (043 AC-5). The day sheet says "15 minutes
		# of grace, set by <name>", and it can only say that truthfully if it
		# knows whether the figure is this shift's own or the organisation's
		# default. Without it the screen would have to guess, and a screen that
		# guesses at a number is the thing this wave exists to stop.
		"grace_source": None,
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
	#
	# `late_by_mins` stays the plain fact: minutes past the shift start. Whether
	# the day COUNTS as late is a separate question, because the organisation
	# forgives the first few minutes, and the two must not be confused. The
	# month total and the chip count `is_late`; the day itself still shows the
	# true minutes, with the grace named beside them.
	if begins is not None and att.in_time:
		out["grace_mins"] = _shift_grace(shift_cache, shift)
		out["grace_source"] = _grace_source(shift_cache, shift)
		arrived = _minutes(str(att.in_time)[11:16])
		if arrived is not None and arrived > begins:
			out["late_by_mins"] = int(round(arrived - begins))
			out["is_late"] = out["late_by_mins"] > out["grace_mins"]

	# An odd number of punches means one never registered. That is the single
	# commonest cause of a short day and the reason this screen exists, so it
	# is named rather than left for the employee to infer from the total.
	#
	# ALV-210. DTC's biometric sync sends no In/Out at all, so every punch read
	# as "Out" and a clean in-and-out day was called a missing punch. Where any
	# punch of the day has no label, the day is read in order - first In, next
	# Out - the same way the shift itself pairs them ("Alternating entries"),
	# and a missing punch is simply an odd count.
	if any(not m["log_type"] for m in marks):
		marks = [dict(m, log_type="IN" if i % 2 == 0 else "OUT")
		         for i, m in enumerate(marks)]
		out["punches"] = marks
		out["missing_punch"] = len(marks) % 2 == 1
	else:
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


def _grace_source(cache, shift):
	"""Which record the grace figure came from: this shift, or the organisation.

	Exactly the order `attendance_analytics._shift_grace` uses to pick the
	number - the shift's own `late_entry_grace_period` where it is set above
	zero, otherwise the organisation default - so the two can never name
	different sources for one figure. Returns None when there is no grace at
	all, which the day sheet says in words rather than showing "0 minutes of
	grace, set by nobody".
	"""
	row = _shift_row(cache, shift) if shift else None
	if row and cint(row.late_entry_grace_period) > 0:
		return "shift"
	return "organisation" if org_late_grace() > 0 else None


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
		# Only days past the grace period. A day inside it is on time as far as
		# the organisation's policy is concerned, and counting it here is what
		# made this total disagree with the deduction card beside it.
		"late_days": len([d for d in days if d["is_late"]]),
		"hours_worked": round(sum(d["hours"] or 0 for d in days), 1),
	}


# ── the requests ─────────────────────────────────────────────────────────────

REQUEST_FIELDS = ["name", "employee", "employee_name", "from_date", "to_date",
                  "reason", "explanation", "half_day", "half_day_date", "docstatus",
                  "alvoraa_review_status", "alvoraa_review_note",
                  "alvoraa_reviewed_by", "alvoraa_reviewed_on", "creation"]


def request_fields():
	"""REQUEST_FIELDS, plus the capacity column when the site actually has it.

	045 AC-82 / the migration risk the `07` raised. `alvoraa_decided_as`
	installs from `after_migrate`, so a deploy that skips migrations leaves the
	column absent - and a `fields` list naming a column that is not there makes
	the READ fail, not just the write. Every screen that lists corrections would
	go blank.

	Asking the schema costs one cached lookup and means the queue degrades to
	"capacity not recorded" instead of to an error page.
	"""
	try:
		if frappe.db.has_column(REQUEST, "alvoraa_decided_as"):
			return REQUEST_FIELDS + ["alvoraa_decided_as"]
	except Exception:
		pass
	return list(REQUEST_FIELDS)


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
	# 045 AC-82(e). What the record says about the capacity, said in words the
	# screen can print without working anything out. An empty value is "not
	# recorded" and never "Manager" - it belongs to a decision made before this
	# field existed, and guessing backwards would put a claim in the record
	# that nobody made.
	row["decided_as"] = row.get("alvoraa_decided_as") or None
	return row


def _my_requests_between(employee, start, end):
	return [_shape(r) for r in frappe.get_list(
		REQUEST, filters={"employee": employee, "docstatus": ("!=", 2),
		                  "from_date": ("<=", end), "to_date": (">=", start)},
		fields=request_fields(), limit_page_length=0)]


@frappe.whitelist()
def my_requests(limit=20):
	"""Every request this person raised, newest first, with its real state."""
	me = _me()
	return [_shape(r) for r in frappe.get_list(
		REQUEST, filters={"employee": me.name}, fields=request_fields(),
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

# The states that mean a correction has stopped waiting. `_state` reads them
# too; they are named here so a query can ask the same question the screen asks
# without re-deriving it row by row.
DONE_STATES = ("Declined", "Withdrawn")


def review_queue_filters(user=None):
	"""The filters for "corrections waiting on this caller" (W1D-05, SEC-5).

	One definition, used by the queue itself and by the frame's count, so the
	bell and the screen can never disagree (AC-51, AC-52).

	Two things it gets right that a hand-written filter dict would not:

	**Waiting is asked in the database, not in Python.** `to_review` used to
	read 50 rows by creation date and then drop the ones that were declined or
	withdrawn, so the screen could show 41 of a "50". Asking for
	`alvoraa_review_status not in (Declined, Withdrawn)` puts the state filter
	below the cap, where it belongs. A row that was never labelled - NULL or
	empty, on a site migrated before that field existed - is still waiting;
	Frappe coalesces the column for a `not in`, and a test pins it.

	**The scope depends on the caller, on purpose.** For an HR caller the queue
	is `permitted_employees()` minus themselves, so a store's HR person gets
	their store and not head office. For a reviewer who is NOT HR - a Shift
	Supervisor a tenant has given the submit permission to - nothing is
	narrowed, because they hold no HR entitlement, so an HR filter would return
	the empty set and silently kill a working flow (W1D-14, AC-52 row 4).

	Returns (filters, is_hr_scope). `filters` is never empty of conditions.
	"""
	user = user or frappe.session.user
	filters = {"docstatus": 0, "alvoraa_review_status": ["not in", list(DONE_STATES)]}
	me = _employee_for(user)
	my_name = me.name if me else None
	if my_name:
		# Your own request is not yours to decide, so it is not in your queue.
		filters["employee"] = ["!=", my_name]

	from hrms.alvoraa_hr_core.access import permitted_companies, permitted_employees

	if not permitted_companies(user):
		# Not an HR caller. Today's scope, unchanged.
		return filters, False

	names = permitted_employees(user)
	if my_name:
		names = names - {my_name}
	if not names:
		# Entitled to nobody. An empty `in` list matches nothing, which is the
		# fail-closed answer; it is NEVER left as "no condition" (SEC-4).
		filters["employee"] = ["in", []]
		return filters, True
	filters["employee"] = ["in", sorted(names)]
	return filters, True


# ── who may decide, in what capacity, and from when (045 D-12) ──────────────
#
# 042's D-2 was never built: Wave 2 left "who may decide an attendance
# correction, and from when" open, and the fail-closed behaviour shipped - HR
# was offered nothing on a covered row at all. Surbhi answered it on
# 24 September 2026, and this is the answer:
#
#   * **HR sees a covered person's correction from day one.** They already did,
#     through `review_queue_filters`' HR scope; what was missing was the
#     labelling, so the row now says who it is with and until when.
#   * **HR may act from day three**, counted as two working days on the
#     REQUESTER'S OWN holiday list - not the decider's, and not the company's
#     default. A shop assistant in a store that closes Tuesdays gets their own
#     Tuesdays, because the clock is about how long their manager has had.
#   * **When HR acts, the record says HR decided**, not the manager.

HR_WAIT_WORKING_DAYS = 2


def _working_days_away(employee, start, days, step):
	"""Walk `days` working days from `start` - forward (step 1) or back (step -1).

	ONE counter, two callers: the HR wait walks forward from the day a request
	was raised, the manager's filing window walks back from today. A second
	counter is how the two would come to disagree about what a working day is.

	Working days are counted on the EMPLOYEE'S OWN holiday list, which in Frappe
	carries the weekly offs as Holiday rows too - so a store that closes on
	Tuesdays gets its own Tuesdays, and a weekend is never assumed to be
	Saturday and Sunday.

	**When the employee has no readable holiday list** the count falls back to
	calendar days and says so through `basis`, rather than throwing or quietly
	borrowing the company default. Walking back, that fallback is the TIGHTER
	answer - skipping a day can only push the far end further away - so missing
	configuration narrows the window rather than opening it.

	Returns (date string, basis).
	"""
	start = getdate(start)
	# Far enough that a run of holidays cannot leave the loop short, and a hard
	# stop so a holiday list full of holidays cannot spin for ever.
	span = days * 2 + 30
	edge = frappe.utils.add_days(start, span * step)
	first, last = sorted([str(start), str(getdate(edge))])
	holidays = set()
	basis = _("calendar days, because this person has no holiday list")
	try:
		# This app's own cached helper, so a screen that asks twice pays once.
		# `raise_exception=False` inside it is what stops an unset store making
		# a correction undecidable.
		hlist = holiday_list_for(employee, start)
		if hlist:
			holidays = {
				str(getdate(d)) for d in frappe.get_all(
					"Holiday",
					filters={"parent": hlist, "parenttype": "Holiday List",
					         "holiday_date": ["between", [first, last]]},
					pluck="holiday_date",
				)
			}
			basis = _("working days on this person's own holiday list")
	except Exception:
		# A missing or malformed holiday list must not make a correction
		# undecidable. Logged WITHOUT personal content: the document name is
		# enough for an authorised human to open it, and no name, id or reason
		# goes into a log line.
		frappe.log_error(
			title="attendance_correction: holiday list unreadable",
			message=f"employee={employee} while counting a working-day window",
		)

	counted, day, walked = 0, start, 0
	while counted < days and walked < span:
		day = frappe.utils.add_days(day, step)
		walked += 1
		if str(getdate(day)) not in holidays:
			counted += 1
	return str(getdate(day)), basis


def hr_may_act_from(doc):
	"""The date an HR caller may first decide somebody else's manager's request.

	Two WORKING days after the request was raised, counted on the requester's
	own holiday list. Returns (date string, basis).
	"""
	return _working_days_away(doc.employee, doc.get("creation") or nowdate(),
	                          HR_WAIT_WORKING_DAYS, 1)


# ── may a MANAGER file at all, and how far back (SEC-9a, SEC-10, SEC-11) ────
#
# Surbhi, 15 Oct 2026: "let's keep it a customizable window default to 48 hrs.
# else HR will do the manual adjustments themselves in case of some genuine
# case." Settled that day as two whole working days, per tenant.
#
# **REVERSED ON 18 OCT 2026, after she tested it live.** Her words:
#
# "it should be a setting per tenant in the organisation setting. First
# setting: allow manager to approve request for attendance and leaves on behalf
# of their reporting [staff]. with sub setting - how many working days is
# allowed for manager to raise approval request, default to blank meaning no
# limit. this will keep it flexible for an organisation to decide."
#
# So the switch answers "may a manager do this at all", and the window - which
# shipped first, as the only control - becomes its sub-setting, with blank
# meaning no limit.
#
# NAMED FOR THE CAPABILITY, NOT FOR ATTENDANCE. The switch covers attendance
# corrections today and leave when that is built, which is what she asked for;
# a key with "attendance" in it would need a second switch beside it and two
# answers to one question.
#
# Stored as a Frappe default and read per request - the idiom
# `alvoraa_attendance_late_grace_mins` already uses, so there is no migration
# and no new DocType, and an existing tenant needs nobody to touch their site.
#
# WHO IT BINDS, AND WHO IT MUST NOT. The window is on the MANAGER's filing path
# only. HR's own manual route is deliberately not bounded by it, because that
# route is the way out when a day is older than the window - which is what
# Surbhi's answer says. An employee raising their OWN day (`raise_correction`)
# is not bounded by it either: narrowing what somebody may ask about their own
# attendance was never asked for, and would take away something they have now.
MANAGER_ON_BEHALF_KEY = "alvoraa_manager_on_behalf_enabled"
MANAGER_FILING_WINDOW_KEY = "alvoraa_manager_filing_window_days"


def manager_on_behalf_on():
	"""May a manager raise a request for a direct report on this tenant?

	**UNSET MEANS ON, deliberately.** This capability already ships and DTC's
	managers use it, so a switch that failed closed would take it away from
	every existing tenant the moment it was added, silently, with nobody having
	chosen that. `org_features.org_switch` is the idiom next door and it fails
	closed on purpose - right for a rule that deducts pay and starts off, wrong
	for a capability people already have. Hence a reader of its own.

	Anything other than "0" is on, so a value nobody can read cannot quietly
	remove a working screen.
	"""
	return str(frappe.db.get_default(MANAGER_ON_BEHALF_KEY) or "").strip() != "0"


def manager_filing_window_days():
	"""How many working days back a manager may file for - or None for no limit.

	**Blank is the default and it means NO LIMIT** (Surbhi, 18 Oct 2026). The
	tenant decides; the product no longer imposes two days on an organisation
	that never asked for a limit.

	NOT read as `get_default(KEY) or DEFAULT`, which is the idiom next door and
	the trap here: a stored "0" is falsy, so it would fall through the `or` and
	become the unset answer - and blank and 0 are now at OPPOSITE ends of this
	setting. Blank is no limit at all; 0 is the tightest window there is, today
	only. They must never be confused for each other.
	"""
	raw = frappe.db.get_default(MANAGER_FILING_WINDOW_KEY)
	if raw is None or str(raw).strip() == "":
		return None
	return max(0, cint(raw))


def manager_filing_from(employee):
	"""The oldest day a manager may file for about this person, or (None, None).

	ONE derivation for the guard and for both screens. A boundary worked out
	twice is a boundary that eventually disagrees with the refusal, and then
	the screen offers a day the server throws on.
	"""
	days = manager_filing_window_days()
	if days is None:
		return None, None
	earliest, basis = _working_days_away(employee, nowdate(), days, -1)
	return str(earliest), basis


def _refuse_outside_filing_window(employee, from_date):
	"""Refuse a manager-filed day that is older than the tenant's window.

	BLANK MEANS NO LIMIT, so there is nothing to check and any past day goes
	through. 0 MEANS "TODAY ONLY". Walking back zero working days from today
	lands on today, so the oldest filable day is today - the tightest setting on
	offer, and the reading that cannot be arrived at by accident. If 0 meant "no
	limit" the tightest-looking number would be the loosest behaviour, which is
	how a control gets switched off by somebody trying to tighten it.
	"""
	days = manager_filing_window_days()
	if days is None:
		return
	earliest, basis = _working_days_away(employee, nowdate(), days, -1)
	if getdate(from_date) >= getdate(earliest):
		return
	if days == 0:
		frappe.throw(_("Your organisation only lets a manager file for today. "
		               "Ask HR to correct an earlier day."))
	frappe.throw(
		_("This day is more than {0} working days old, so it is outside the "
		  "filing window - ask HR to correct it. The oldest day you can file "
		  "for is {1}, counted in {2}.").format(
			days, frappe.utils.formatdate(earliest), basis))


def _manager_user_for(employee):
	"""The login of this employee's own `reports_to`, or None.

	`reports_to` is the single source of truth for who somebody's manager is
	(045 AC-25). The org chart is not asked, and neither is
	`get_effective_manager`, which falls back to the first active HR Manager
	when `reports_to` is empty - a helper written to answer "who do we notify"
	must not decide "who may read" (045 AC-83 / SEC-7).
	"""
	if not employee:
		return None
	mgr = frappe.db.get_value("Employee", employee, "reports_to")
	return frappe.db.get_value("Employee", mgr, "user_id") if mgr else None


def _manager_name_for(employee):
	"""What to call this person's manager on screen, or None.

	**A refusal that names nobody is a bad refusal.** "This is still with their
	manager" tells an HR person to wait for somebody the product will not name,
	and nobody can chase a blank. So the name is read from the manager's own
	Employee row first - that is the name the rest of the product prints - and
	from the login's full name second.

	Only the manager's NAME comes back. No contact detail, no id, nothing else
	off that row: a refusal needs one word, not a record.
	"""
	mgr = frappe.db.get_value("Employee", employee, "reports_to")
	if not mgr:
		return None
	row = frappe.db.get_value("Employee", mgr, ["employee_name", "user_id"],
	                          as_dict=True) or {}
	return (row.get("employee_name")
	        or frappe.db.get_value("User", row.get("user_id"), "full_name")
	        or None)


def decided_as(doc, user=None):
	"""`Manager`, `HR`, or **None** - derived by the server, never declared.

	045 SEC-19. The value is worked out here from the caller's real
	relationship to the employee at the moment of the decision. There is no
	argument for it on any endpoint, and a `decided_as` in a request body
	changes nothing - a test supplies one and asserts the stored value is
	unmoved.

	The order matters: being the employee's own manager wins. Somebody who is
	both a manager and HR, deciding their own report's request, decided as the
	manager - that is the act they performed.
	"""
	user = user or frappe.session.user
	if user and user == _manager_user_for(doc.employee):
		return "Manager"

	# **Not everybody who is not the manager is HR.** W1D-14: a tenant may give
	# the submit permission on Attendance Request to a Shift Supervisor, who
	# holds no HR entitlement at all and whose queue is deliberately NOT
	# narrowed. Calling them "HR" would be a false claim in an audit field, and
	# - worse - it would put them behind the two-working-day wait and silently
	# kill a flow that works today. Wave 4 was not asked to narrow that.
	#
	# So they get None, which reads as "not recorded". That is the honest
	# answer: the record does not know in what capacity they acted, because the
	# product has never had a word for it.
	from hrms.alvoraa_hr_core.access import permitted_companies

	return "HR" if permitted_companies(user) else None


def _decided_as_is_storable():
	"""Is there a column to write the capacity into?

	**This is the difference between a degraded feature and a broken one.**
	`alvoraa_decided_as` installs from `after_migrate`, so a deploy that skips
	migrations leaves the column absent. Writing to it then fails with "Unknown
	column" - and because that write is on the path EVERY decision takes, every
	attendance correction would fail, managers included, not only HR overrides.

	So the write is guarded. With no column the approval still works and only
	the capacity is lost, which reads afterwards as "not recorded" - the same
	thing a pre-existing record says.
	"""
	try:
		return bool(frappe.db.has_column(REQUEST, "alvoraa_decided_as"))
	except Exception:
		return False


def not_yours_yet(doc, capacity):
	"""Why this caller may not decide this request today, in words, or None.

	ONE ANSWER FOR `decide` AND FOR EVERY ROW THAT OFFERS THE BUTTONS. DTC,
	22 Oct 2026: HR pressed Approve on a request inside the wait below, and
	the server refused with a 403. The refusal was right; offering the button
	was not. So the row now asks this same function and draws the sentence
	instead of the buttons - the screen holds no copy of the rule.

	`capacity` is `decided_as(doc)` for the caller; passed in because both
	callers already have it.
	"""
	# **The wait applies only where there is a manager who could act.**
	#
	# 045 AC-81, the no-manager clause. The two working days exist to give
	# the employee's own manager first refusal. Somebody with no
	# `reports_to`, or whose `reports_to` has no login, has nobody to give
	# it to - so there is nothing to wait for, and HR decides straight
	# away, which is what HR does today. Most people in a shop have no
	# manager recorded; without this clause the window stops a working flow
	# for all of them and tells them to wait for a person the product
	# cannot name.
	#
	# **This restores what HR does today. It is not a new policy.** The
	# answer behind the window was "HR sees from day one, acts from day
	# three", and it was about waiting for a MANAGER. It was never about
	# waiting for nobody.
	#
	# `_manager_user_for` is the same derivation `decided_as` uses, so the
	# two cannot drift: whoever counts as the manager for the capacity is
	# exactly whoever the wait is for.
	if capacity != "HR":
		return None
	mgr_user = _manager_user_for(doc.employee)
	if not mgr_user:
		return None
	may_act_from, basis = hr_may_act_from(doc)
	if getdate(nowdate()) >= getdate(may_act_from):
		return None
	mgr = _manager_name_for(doc.employee)
	# Says what happened, why, and what to do next - never "not allowed".
	# **And it names the person.** Where the record holds no name at all it
	# says plainly who to go to, instead of an anonymous "their manager".
	if mgr:
		return _("This is still with {0} until {1}. You can decide it as HR "
		         "from then, counted as two {2}.").format(
			mgr, frappe.utils.formatdate(may_act_from), basis)
	return _("This is still with the manager on this person's record until "
	         "{0} - the record has no name for them. You can decide it as HR "
	         "from then, counted as two {1}. To act sooner, ask HR to check "
	         "who this person reports to.").format(
		frappe.utils.formatdate(may_act_from), basis)


def _with_decide_flag(rows):
	"""Add `can_decide` and `not_yet` to each waiting row, from `not_yours_yet`.

	Asked once per person and day raised, not once per row: everything the
	answer depends on is the employee, the day it was raised and the caller.
	"""
	seen = {}
	for r in rows:
		key = (r.get("employee"), str(r.get("creation") or "")[:10])
		if key not in seen:
			doc = frappe._dict(r)
			seen[key] = not_yours_yet(doc, decided_as(doc))
		r["not_yet"] = seen[key]
		r["can_decide"] = not seen[key]
	return rows


@frappe.whitelist()
def to_review(limit=50):
	"""What is waiting on this caller to decide.

	`get_list` under the caller's own permissions, so an organisation that has
	scoped Attendance Request by department gets that scoping here for free,
	on top of the scope in `review_queue_filters`.

	The return shape is unchanged - a plain list - because today's page reads it
	as one. The frame's bell counts the SAME filters without the cap, so when
	there are more waiting than the cap, the bell's number is the true total and
	the new Inbox page says "showing the first 50 of 60" beside it (N3).
	"""
	if not _may_review():
		frappe.throw(_("You do not review attendance corrections."), frappe.PermissionError)
	filters, _is_hr = review_queue_filters()
	rows = frappe.get_list(
		REQUEST, filters=filters, fields=request_fields(),
		order_by="creation asc", limit_page_length=cint(limit) or 50)
	# The state filter is in the query now, so nothing should fall out here.
	# The line stays as a second lock: `_state` is the screen's own definition
	# of waiting, and if the two ever disagree the screen must win.
	return _with_decide_flag(
		[r for r in (_shape(x) for x in rows) if r["state"] == "waiting"])


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
	# Approve and decline alike: deciding your own correction is not a review.
	# The before_submit hook repeats this for the desk and the REST API.
	from hrms.alvoraa_hr_core.access import refuse_own_decision
	refuse_own_decision(doc.employee, REQUEST, doc.name, "attendance_correction.decide")
	if doc.docstatus != 0:
		frappe.throw(_("This one has already been decided."))
	if doc.get("alvoraa_review_status") in ("Declined", "Withdrawn"):
		frappe.throw(_("This one has already been decided."))

	# 045 AC-81 / AC-82 / D-12. The capacity is derived here, from the caller's
	# real relationship to the employee at this moment. Nothing in the request
	# body can influence it - `decide()` takes no `decided_as` argument, and
	# adding one later would be a change somebody has to make on purpose.
	capacity = decided_as(doc)
	not_yet = not_yours_yet(doc, capacity)
	if not_yet:
		frappe.throw(not_yet, frappe.PermissionError)

	stamp = {"alvoraa_review_note": (note or "").strip() or None,
	         "alvoraa_reviewed_by": frappe.session.user,
	         "alvoraa_reviewed_on": frappe.utils.now()}
	# Guarded on the column existing. A deploy that skipped migrations must
	# lose the capacity, not the approval - see `_decided_as_is_storable`.
	#
	# `capacity` is None for a reviewer who is neither the manager nor HR - a
	# Shift Supervisor a tenant has given the submit permission to (W1D-14).
	# Nothing is written for them, so the record says "not recorded" rather
	# than making a claim the product has no word for.
	if capacity and _decided_as_is_storable():
		stamp["alvoraa_decided_as"] = capacity

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


# ── a manager's whole team, one page ─────────────────────────────────────────
#
# Surbhi, 17 Oct 2026: "we would need one page with filter for all the
# reporting persons first", and "only attendance facts".
#
# ATTENDANCE FACTS ONLY. No quarters, no marks, no money. A manager confirming
# what happened on a Tuesday does not need to know what their team earns, and
# putting it on the screen would hand every manager their reports' pay as a
# side effect of a correction workflow.
#
# The day's SHAPE is what a manager needs: who has no clock-out, who is absent
# on a day they badged in, who is simply absent. Those three are the whole job.

# What a day needs, worst first. The order IS the value of the page: a manager
# opening it should meet the days somebody must act on, not scroll to them.
#
# ALV-211 split "absent but badged in" in two, because they need different
# answers. "absent_not_counted": a punch fell outside the shift's window (or
# was never linked to a shift), so the system did not count it - a setup
# fault. "absent_short": every punch counted and the hours were still under
# the shift's absent threshold - a real short day.
NEEDS = ("no_clock_out", "absent_not_counted", "absent_short", "absent", "short", "ok")


def _flag(row, punches, shift):
	"""What is wrong with this day, in one word.

	Judged from the attendance record, the day's punches and the shift row,
	NOT from the pay engine - this screen reads the same whether or not a rule
	set is switched on.
	"""
	status = (row.get("status") or "").strip()
	if len(punches) == 1:
		# ATT-06. One punch is not a short day, it is an unfinished one, and it
		# is the single commonest thing a manager is asked about.
		return "no_clock_out"
	if status == "Absent":
		if not punches:
			return "absent"
		if any(not p.shift_start for p in punches):
			return "absent_not_counted"
		if shift and shift.start_time is not None and shift.end_time is not None:
			# The shift's own window: from its start less the early allowance to
			# its end plus the late one. A night shift ends the next day.
			day = datetime.combine(getdate(row.get("attendance_date")), time())
			opens = day + shift.start_time - timedelta(
				minutes=cint(shift.begin_check_in_before_shift_start_time))
			closes = day + shift.end_time + timedelta(
				minutes=cint(shift.allow_check_out_after_shift_end_time))
			if shift.end_time <= shift.start_time:
				closes += timedelta(days=1)
			if any(not opens <= get_datetime(p.time) <= closes for p in punches):
				return "absent_not_counted"
		return "absent_short"
	if status == "Half Day":
		return "short"
	return "ok"


def _punches_by_day(people_ids, from_date, to_date):
	"""Each person's punches on each day, in one read.

	One punch is the signal this page exists for, and it cannot be read off the
	Attendance row: a day with one punch and a day with none both show no
	out-time and nought hours, and they need opposite answers from a manager.
	`shift_start` says whether Frappe linked the punch to a shift at all.
	"""
	days = {}
	if not people_ids:
		return days
	for p in frappe.get_all(
			"Employee Checkin",
			filters={"employee": ("in", people_ids),
			         "time": ("between", [str(from_date) + " 00:00:00",
			                              str(to_date) + " 23:59:59"])},
			fields=["employee", "time", "shift_start"], limit_page_length=0):
		days.setdefault((p.employee, str(p.time)[:10]), []).append(p)
	return days


@frappe.whitelist()
def team_days(from_date=None, to_date=None, employee=None, only=None,
              depth="direct", department=None, branch=None,
              start=0, page_length=50, limit=2000):
	"""Every day across the caller's team, with what needs a look first.

	`employee` narrows to one person. `only` keeps a single flag, for the
	filter chips. `department` and `branch` narrow the people.

	`depth` is "direct" or "all". Surbhi, 17 Oct 2026: a manager may only ACT
	for a direct report, so the page opens on the people they can actually do
	something about. "all" shows the whole line they are accountable for, which
	is the same choice Attendance Insights already offers. HR sees everybody
	either way, so it does nothing for them.

	ONE PAGE AT A TIME. HR opens this across the whole company - 363 people on
	DTC - so `start` and `page_length` return a slice, and `total` says how many
	there were. The counts are deliberately for the WHOLE period and not the
	page: a chip reading "4 need a look" has to mean four altogether, or a
	manager stops at the end of page one believing they are done.

	Paging bounds the payload, NOT the server's reading. The flags depend on
	punch counts worked out after the query, so the window has to be read and
	flagged before it can be sliced. What bounds the reading is the period: a
	fortnight by default, three months at most.

	PERMISSION IS DECIDED HERE, NOT LEFT TO A FILTER. A manager holds no
	blanket read on Attendance, so a `get_list` would return an empty page that
	looks broken rather than a refusal that explains itself - the same reason
	`whose_months_i_can_open` reads with `get_all` once it has settled who the
	caller may see. The team is settled first, every row is inside it, and the
	read is explicit.
	"""
	me = _employee_for(frappe.session.user)
	may_review = _may_review()
	if may_review:
		team = None                       # HR: anybody, narrowed below if asked
	else:
		if not me:
			frappe.throw(_("Your user is not linked to an employee record, so "
			               "there is nobody you can open."), frappe.PermissionError)
		team = _reports_to(me.name, deep=(str(depth) == "all"))
		if not team:
			return {"people": [], "rows": [], "counts": {}, "nobody": True,
			        "total": 0, "start": 0, "page_length": cint(page_length) or 50,
			        "from_date": str(getdate(from_date or nowdate())),
			        "to_date": str(getdate(to_date or nowdate()))}

	if employee:
		# One person: the same gate the month view uses, so a manager cannot
		# reach outside their tree by naming somebody.
		subject, _is_self = _subject(employee)
		people_ids = [subject.name]
	elif team is None:
		people_ids = frappe.get_all("Employee", filters={"status": "Active"},
		                            pluck="name", limit_page_length=0)
	else:
		people_ids = list(team)

	today = getdate(nowdate())
	to_date = getdate(to_date or today)
	from_date = getdate(from_date or frappe.utils.add_days(to_date, -13))
	if from_date > to_date:
		frappe.throw(_("The last day cannot be before the first day."))
	if (to_date - from_date).days > 92:
		frappe.throw(_("Please choose a period of three months or less."))

	# Narrowed on the PEOPLE rather than on their days, so a department filter
	# empties the person picker too and the page stays self-consistent.
	who_filters = {"name": ("in", people_ids or [""])}
	if department:
		who_filters["department"] = department
	if branch:
		who_filters["branch"] = branch
	people = {p.name: p for p in frappe.get_all(
		"Employee", filters=who_filters,
		fields=["name", "employee_name", "designation", "department", "branch"],
		order_by="employee_name asc", limit_page_length=0)}
	if department or branch:
		people_ids = list(people.keys())

	rows = frappe.get_all(
		"Attendance",
		filters={"employee": ("in", people_ids or [""]), "docstatus": 1,
		         "attendance_date": ("between", [str(from_date), str(to_date)])},
		fields=["name", "employee", "attendance_date", "status", "working_hours",
		        "shift", "in_time", "out_time", "late_entry", "early_exit"],
		order_by="attendance_date desc", limit_page_length=0)

	punches_on = _punches_by_day(people_ids, from_date, to_date)
	# Every shift on these rows, read once - never once per row.
	shifts = {s.name: s for s in frappe.get_all(
		"Shift Type",
		filters={"name": ("in", list({r.shift for r in rows if r.shift}) or [""])},
		fields=["name", "start_time", "end_time",
		        "begin_check_in_before_shift_start_time",
		        "allow_check_out_after_shift_end_time",
		        "working_hours_threshold_for_absent"],
		limit_page_length=0)}

	# Which rows this caller may actually ACT on, answered with the same two
	# questions `month()` asks and the same two the guard enforces.
	#
	# WHAT CHANGED, 18 Oct 2026. This said `can_raise_all = bool(may_review)`,
	# so HR got the button on every row while `month()` gave them none - the
	# same user, two answers, found by pressing it live. Acting now stops at
	# the DIRECT reports for everybody, HR included; the reasoning is on
	# `can_request` in `month()`.
	#
	# An empty set when the tenant has switched the capability off, so a
	# switched-off tenant sees no buttons rather than buttons that refuse.
	direct_ids = set()
	if me and manager_on_behalf_on():
		direct_ids = set(_reports_to(me.name, deep=False))

	# The window, per person, because it is counted on the EMPLOYEE'S OWN
	# holiday list - a store that shuts on Tuesdays gets its own Tuesdays.
	# Worked out only for the people this caller can act for and only when a
	# window is set, so the common cases - no limit, or nobody to act for -
	# cost nothing, and HR opening 363 people costs nothing either.
	filing_from = {}
	if direct_ids and manager_filing_window_days() is not None:
		for emp in direct_ids.intersection(people_ids):
			filing_from[emp] = manager_filing_from(emp)[0]

	out, counts = [], {}
	for r in rows:
		who = people.get(r.employee)
		if not who:
			continue
		day_punches = punches_on.get((r.employee, str(r.attendance_date)), [])
		n = len(day_punches)
		shift = shifts.get(r.shift)
		flag = _flag(r, day_punches, shift)
		counts[flag] = counts.get(flag, 0) + 1
		if only and flag != only:
			continue
		out.append({
			"attendance": r.name,
			"employee": r.employee,
			"employee_name": who.employee_name,
			"designation": who.designation,
			"department": who.department,
			"branch": who.branch,
			"date": str(r.attendance_date),
			"status": r.status,
			"hours": flt(r.working_hours, 2),
			"shift": r.shift,
			"in_time": str(r.in_time)[11:16] if r.in_time else None,
			"out_time": str(r.out_time)[11:16] if r.out_time else None,
			"punches": n,
			"flag": flag,
			# The hours below which the shift marks a day Absent, so the
			# screen can say "under 2 hours worked". None when the shift sets
			# none.
			"absent_under": (flt(shift.working_hours_threshold_for_absent) or None
			                 if flag == "absent_short" and shift else None),
			"late": bool(r.late_entry),
			"early": bool(r.early_exit),
			# The day as well as the person: a day older than the window
			# would be refused, and a button that dies when pressed is worse
			# than no button.
			"can_raise": (r.employee in direct_ids
			              and (r.employee not in filing_from
			                   or str(r.attendance_date) >= filing_from[r.employee])),
		})

	order = {f: i for i, f in enumerate(NEEDS)}
	out.sort(key=lambda d: (order.get(d["flag"], 99), d["date"], d["employee_name"]))

	# The page. `limit` stays as the outer safety net it always was; a caller
	# cannot ask for a page bigger than it.
	total = len(out)
	size = min(cint(page_length) or 50, cint(limit) or 2000)
	begin = max(0, cint(start))
	page = out[begin:begin + size]

	return {
		"from_date": str(from_date),
		"to_date": str(to_date),
		"people": sorted(people.values(), key=lambda p: p.employee_name or ""),
		"rows": page,
		"counts": counts,
		"total": total,
		"start": begin,
		"page_length": size,
		# HR sees everybody, so `depth` does nothing for them. Said here so the
		# screen can leave out a control that would change nothing - an option
		# that visibly does nothing reads as a broken page.
		"everybody": bool(may_review),
		"depth": "all" if str(depth) == "all" else "direct",
	}


@frappe.whitelist()
def raise_for_report(employee=None, from_date=None, to_date=None, reason=None,
                     explanation=None, half_day=0, half_day_date=None):
	"""A manager asks HR to fix a day for somebody who reports to them.

	Surbhi, 15 Oct 2026: "let's get the manager request the changes and the HR
	to confirm or reject it." The manager raises; HR decides. This endpoint
	does the first half and nothing more - it creates a request in the same
	Waiting state an employee's own request starts in, and `decide` is
	unchanged.

	WHY THIS IS NOT A PARAMETER ON `raise_correction`. That endpoint says, in
	its own docstring, that the employee is never taken from the request
	because "a field that named somebody else would let anyone rewrite anyone's
	attendance". That is right, and it stays right. The difference here is that
	the named employee is CHECKED: `_subject` refuses anybody outside the
	caller's reporting tree before a document is built.

	WHO ASKED IS RECORDED, in the explanation, so HR reads a request that says
	who is vouching for the day rather than one that appears to have come from
	the employee themselves.
	"""
	# A CALL THAT ARRIVES WITH NOTHING GETS A SENTENCE, NOT A CRASH.
	#
	# On 18 Oct 2026 the ppj.dev error log held two entries 35ms apart: a
	# correct refusal, and a second call with no body at all, which Frappe
	# answered with "missing 2 required positional arguments". The second,
	# uglier error is the one that reached the screen, so a correct refusal
	# read as a crash.
	#
	# Checked BEFORE `_subject`, which would read a missing employee as "my own
	# month" and send a bodyless call down the employee's own path. An empty
	# request must do nothing at all.
	if not employee or not from_date:
		frappe.throw(_("That request was incomplete, so nothing was sent. "
		               "Reload the page and try again."))

	subject, is_self = _subject(employee)
	if is_self:
		# Their own day: the ordinary endpoint, with its ordinary rules.
		return raise_correction(from_date, to_date, reason, explanation,
		                        half_day, half_day_date)

	# ── ACTING STOPS AT THE DIRECT REPORTS ───────────────────────────────────
	#
	# Surbhi, 17 Oct 2026, asked whether a manager may act for somebody two
	# levels down: "direct reports only."
	#
	# `_subject` allows the whole line, because READING a month is a different
	# question and managers already have that - narrowing it there would take
	# away a screen they use today. Acting is narrowed here instead.
	#
	# It also closes a real gap. `manager_scope` grants the Frappe permission
	# for DIRECT reports only, so a request for somebody further down passed
	# this function and then failed on the document's own permission check -
	# a confusing refusal, and only ever for skip-level reports, which is
	# exactly the case nobody tries by hand. Now the refusal is here, in words
	# that say what to do instead.
	if not _may_review():
		me_now = _employee_for(frappe.session.user)
		direct = _reports_to(me_now.name, deep=False) if me_now else []
		if subject.name not in direct:
			frappe.throw(
				_("{0} does not report directly to you, so this is their own "
				  "manager's to raise. You can still open their attendance to "
				  "see what happened.").format(subject.employee_name or subject.name),
				frappe.PermissionError)

	to_date = to_date or from_date
	if getdate(to_date) < getdate(from_date):
		frappe.throw(_("The last day cannot be before the first day."))
	if getdate(from_date) > getdate(nowdate()):
		frappe.throw(_("You cannot raise a correction for a day that has not "
		               "happened yet."))

	allowed = {r["value"] for r in reasons()}
	if reason not in allowed:
		frappe.throw(_("{0} is not one of the reasons on offer.").format(reason or ""))
	if reason == "Other" and not (explanation or "").strip():
		frappe.throw(_("Please say what happened, so HR can act on it."))

	# The tenant's two settings (SEC-9a). Checked AFTER the shape of the
	# request, so a manager who got the reason wrong is told about the reason,
	# and the window is checked on `from_date` because that is the oldest day
	# being asked about.
	#
	# The switch refuses in plain words that say what to do next. HR's own
	# route is not this endpoint - it is the Attendance Request itself - so
	# switching this off closes the manager's shortcut and nothing else.
	if not manager_on_behalf_on():
		frappe.throw(_("Your organisation does not let a manager ask for somebody "
		               "else's attendance to be fixed. Ask HR to correct this day."),
		             frappe.PermissionError)
	_refuse_outside_filing_window(subject.name, from_date)

	me = _employee_for(frappe.session.user)
	note = (explanation or "").strip()
	if me:
		stamp = _("Raised by {0} on behalf of the employee.").format(
			me.employee_name or me.name)
		note = (note + "\n\n" + stamp).strip() if note else stamp

	doc = frappe.get_doc({
		"doctype": REQUEST,
		"employee": subject.name,
		"employee_name": subject.employee_name,
		"company": subject.company,
		"from_date": from_date,
		"to_date": to_date,
		"reason": reason,
		"explanation": note,
		"half_day": cint(half_day),
		"half_day_date": half_day_date if cint(half_day) else None,
		"alvoraa_review_status": "Waiting",
	})
	# No ignore_permissions. A manager raising this for a report is allowed by
	# the permission system itself: `manager_scope` holds one User Permission
	# per manager, per report, scoped to Attendance Request and three other
	# doctypes. So Frappe permits the insert because the manager genuinely is
	# permitted, and the decision lives in data somebody can list rather than
	# in a line of Python nobody can audit.
	#
	# An earlier version called `insert(ignore_permissions=True)` after
	# checking the reporting line here. It worked, and
	# `NoQuietBypass.test_this_module_never_ignores_permissions` caught it -
	# which is exactly what that test is for.
	doc.insert()
	return _shape(doc.as_dict())
