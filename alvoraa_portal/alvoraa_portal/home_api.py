"""Slice 042, Wave 2: everything Home draws, in one call.

Home is the tenant's landing page, so it is the page a shop-floor worker opens
between two customers. It makes **three** calls in total - `get_frame` and
`get_nav_counts` from the frame, and this one - and none of them waits on a
timer.

Four rules govern this module, each with a test that fails if it is broken.

**A fixed list of keys (SEC-12, 042 AC-5).** Wave 1's biggest security finding
was a start-up call that sent every caller their own date of birth, gender,
phone number, joining date, manager and branch, so that all of it was in every
screenshot and every browser error report. `get_home` returns exactly
`HOME_KEYS`, and the `me` block is exactly `frame_api.ME_FIELDS`. The payload is
the control, not the screen.

**No counts (042 AC-38, DevOps OPS-W2-6).** The frame already calls
`get_nav_counts` on every load. A panel that supplied its own badge number would
be a second source of the one number this whole slice exists to make single, and
it would count the six parts twice on every Home load - they are the most
expensive queries on the page. If Home ever needs the number it asks
`inbox_api`, like everything else.

**One card failing is one card failing (042 AC-32).** Every card is gathered
inside `_card`, which catches, logs without personal content, and returns
`{"error": True}`. A team query that throws must not take the check-in hero with
it.

**Presence, never the reason (042 AC-29, AC-30).** The team card carries three
numbers and no names, no photos, no per-person state, no leave types and no
absence reasons. Below a minimum group size it carries no numbers at all, and
where one category is suppressed the next smallest goes with it, so the
remaining numbers cannot be used to recover the hidden one.

**No `ignore_permissions`, and no module-level state that changes at run time**
(SEC-6, SEC-15). Every constant here is a tuple.

Guest is refused, and every function is live on production from the release that
carries it, whatever page calls it (SEC-2), so the Guest, wrong-persona and
scope tests ship in the same commit.

## What Wave 2 deliberately did NOT build

**The new-joiners card (D-8).** Listing the newest people in the building, by
name and job title, on four hundred colleagues' Home screens is the one new
disclosure in this slice, and it is about the people least able to object. The
product owner has not answered whether somebody may decline. **Until she does
the fail-closed default is built: the caller's own work anniversary, and no
joiners list at all.** `celebrations["joiners"]` is an empty tuple, and a test
asserts it stays empty rather than being filled by a query nobody reviewed.
"""

import frappe
from frappe import _
from frappe.utils import add_days, get_first_day, getdate, today

from alvoraa_portal.call_cache import close_cache, holiday_list_for, once, open_cache
from alvoraa_portal.frame_api import ME_FIELDS

# Every top-level key `get_home` returns, for every persona. The set does not
# change between callers - only the values do.
#
# `counts` is deliberately absent and must stay absent. See the module docstring.
HOME_KEYS = (
	"me",            # ME_FIELDS, or None for a caller with no Active Employee record
	"today",         # the site's date, the shift, the check-in, whether location is needed
	"needs",         # what needs this person - the caller's own facts only
	"leave",         # the caller's own leave left, from the ledger
	"holidays",      # the caller's OWN holiday list, never the company's
	"holiday_note",  # slice 035's sentence when no list is assigned
	"goals",         # the caller's own; for a manager or HR, the team summary too
	"team_today",    # counts only - never names, never reasons
	"celebrations",  # own work anniversary; joiners are not built (D-8)
)

# The keys the team card may carry. `suppressed` is here so the screen knows to
# draw the sentence without numbers rather than drawing three blanks - it says
# something about the group's size and nothing about any person in it.
TEAM_TODAY_KEYS = ("in", "away", "due", "basis", "suppressed")

# The smallest group whose numbers may be published at all (`01b` section 9,
# 042 AC-29 (b), D-7). Five is an ASSUMPTION: no source names a figure, and it
# is the fail-closed default until the product owner and the security engineer
# confirm one.
MIN_GROUP = 5

# The window the attendance-gap rule looks at: this month and the last one
# (042 section 11, D-5). Anything older belongs on the Time screen.
GAP_MONTHS = 2

# Every list on Home is capped at the same number as the Inbox's, and says so.
LIST_CAP = 50


def _card(name, fn, default=None):
	"""Run one card's query. A failure is that card's failure and nobody else's.

	The log line carries the card's name and the exception, never the caller's
	employee id or anything about a person: an error report is one of the places
	personal data leaks without anybody deciding to leak it (042 AC-43).
	"""
	try:
		return fn()
	except Exception:
		frappe.log_error(title="home_api: %s could not be built" % name,
		                 message=frappe.get_traceback())
		return {"error": True} if default is None else default


def _me(user):
	"""The caller's own Active Employee record, cut to ME_FIELDS.

	The same question `frame_api._me` and `inbox_api._my_employee` ask, with the
	same answer, so three parts of one page cannot describe two different people
	(042 AC-47).
	"""
	row = frappe.db.get_value(
		"Employee", {"user_id": user, "status": "Active"},
		["name", "employee_name", "designation", "department", "image", "company",
		 "date_of_joining", "branch", "reports_to", "default_shift"],
		as_dict=True)
	if not row:
		return None, None
	# `me` is cut to ME_FIELDS on the way out. The four extra fields above are
	# read because the gap rule, the peer card and the anniversary need them -
	# and they are used HERE and never put in the payload (AC-5).
	me = {
		"employee": row.get("name"),
		"employee_name": row.get("employee_name"),
		"designation": row.get("designation"),
		"department": row.get("department"),
		"image": row.get("image"),
		"company": row.get("company"),
	}
	return me, row


# ── The hero ─────────────────────────────────────────────────────────────────


def _shift_today(employee, default_shift, date_):
	"""The shift this person is on today, or None.

	Frappe HR's own precedence: a Shift Assignment covering today beats
	`Employee.default_shift`. None is a real answer - 009 design decision 6 says
	somebody with no shift gets **no hero at all**, not an empty one.

	"Covering today" is asked in ONE query, with the open-ended case
	(`end_date` not set) in it. The first version read the newest assignment by
	start date and then checked whether it had ended, which meant an assignment
	that finished last week hid one that is still running.
	"""
	rows = frappe.get_all(
		"Shift Assignment",
		filters={"employee": employee, "docstatus": 1,
		         "start_date": ["<=", date_]},
		fields=["shift_type", "start_date", "end_date"],
		order_by="start_date desc", limit_page_length=0)
	name = None
	for row in rows:
		if not row.end_date or getdate(row.end_date) >= getdate(date_):
			name = row.shift_type
			break
	if not name:
		name = default_shift
	if not name:
		return None
	times = frappe.db.get_value("Shift Type", name, ["start_time", "end_time"],
	                            as_dict=True)
	if not times:
		return None
	return {
		"name": name,
		"start": str(times.get("start_time")) if times.get("start_time") else None,
		"end": str(times.get("end_time")) if times.get("end_time") else None,
	}


def _checkin_today(employee, date_):
	"""The last check-in of the site's day, or None.

	`time` is the site's clock, not the browser's (042 AC-53).
	"""
	rows = frappe.get_all(
		"Employee Checkin",
		filters={"employee": employee, "time": [">=", str(date_) + " 00:00:00"]},
		fields=["log_type", "time"], order_by="time asc", limit_page_length=0)
	if not rows:
		return None
	last = rows[-1]
	return {"time": str(last.time), "type": last.log_type}


# ── The attendance-gap rule (042 section 11) ─────────────────────────────────


def _gap_days(employee, joined, date_):
	"""Days with no attendance that this person could still put right.

	The rule, written once and used by both the number and the Fix sheet
	(042 AC-22), so the two cannot disagree. A day is a gap when ALL of these
	are true:

	  1. it is on or after the employee's `date_of_joining` (042 AC-45);
	  2. it is in the past - not today, not the future;
	  3. it is not on the employee's OWN holiday list, and not a weekly off on
	     that list (042 AC-52 - the company's list is not the answer);
	  4. there is no Attendance record, or its status is Absent (042 AC-50);
	  5. it is not covered by an approved OR pending Leave Application
	     (042 AC-48, AC-49);
	  6. it is not covered by an Attendance Request that is waiting or approved.

	Four queries, whatever the window. Never one per day.
	"""
	date_ = getdate(date_)
	start = get_first_day(date_)
	for _i in range(GAP_MONTHS - 1):
		start = get_first_day(add_days(start, -1))
	if joined and getdate(joined) > start:
		start = getdate(joined)
	end = add_days(date_, -1)
	if end < start:
		return []

	# Rule 3 - the employee's OWN list, found the way payroll finds it.
	off = set()
	holiday_list = holiday_list_for(employee, date_)
	if holiday_list:
		off = {str(h.holiday_date) for h in frappe.get_all(
			"Holiday", filters={"parent": holiday_list,
			                    "holiday_date": ["between", [start, end]]},
			fields=["holiday_date"], limit_page_length=0)}

	# Rule 4.
	marked = {str(a.attendance_date): a.status for a in frappe.get_all(
		"Attendance",
		filters={"employee": employee, "docstatus": 1,
		         "attendance_date": ["between", [start, end]]},
		fields=["attendance_date", "status"], limit_page_length=0)}

	# Rules 5 and 6, expanded into a set of covered days.
	covered = set()
	for row in frappe.get_all(
		"Leave Application",
		filters={"employee": employee, "status": ["in", ["Open", "Approved"]],
		         "docstatus": ["<", 2], "from_date": ["<=", end],
		         "to_date": [">=", start]},
		fields=["from_date", "to_date"], limit_page_length=0,
	):
		covered |= _span(row.from_date, row.to_date, start, end)
	from alvoraa_portal.attendance_correction import DONE_STATES, REQUEST

	for row in frappe.get_all(
		REQUEST,
		filters={"employee": employee, "docstatus": ["<", 2],
		         "alvoraa_review_status": ["not in", list(DONE_STATES)],
		         "from_date": ["<=", end], "to_date": [">=", start]},
		fields=["from_date", "to_date"], limit_page_length=0,
	):
		covered |= _span(row.from_date, row.to_date, start, end)

	days = []
	day = start
	while day <= end:
		key = str(day)
		if key not in off and key not in covered:
			status = marked.get(key)
			if status is None or status == "Absent":
				days.append(key)
		day = add_days(day, 1)
	# **Newest first.** The list is capped at 50 and the correction flow is for
	# recent days (042 section 11), so the oldest-first order put the 50 days
	# furthest from today on the screen and hid the ones a person came to fix.
	# Found by the test, not by reading the code.
	days.reverse()
	return days


def _span(from_date, to_date, start, end):
	"""Every day between two dates, clipped to the window."""
	out = set()
	if not from_date or not to_date:
		return out
	day = max(getdate(from_date), getdate(start))
	last = min(getdate(to_date), getdate(end))
	while day <= last:
		out.add(str(day))
		day = add_days(day, 1)
	return out


# ── The team card: counts, and the minimum group size ────────────────────────


def _reports(employee):
	"""This person's active direct reports, asked once per call.

	`_team_today` and `_goals` both want the same list, and `_team_today` asked
	for it twice on its own - three identical statements on a manager's Home
	(measured, 044 D2). The memo lives for one `get_home` and no longer.
	"""
	return once(("reports", employee), lambda: frappe.get_all(
		"Employee", filters={"reports_to": employee, "status": "Active"},
		pluck="name", limit_page_length=0))


def _hr_scope():
	"""The people an HR caller looks after, through the shared definition.

	`permitted_employees()` is the one place that knows a store's HR person is a
	store's HR person (Wave 1 SEC-3, W1D-20). It is called, never re-derived.
	"""
	from hrms.alvoraa_hr_core.access import permitted_employees

	return once("hr_scope", lambda: sorted(permitted_employees() or set()))


def _filter_list(filters):
	"""A Frappe filter dict as a list of conditions, so two can be added together.

	A dict can only hold one condition per field, so "everyone HR may see" and
	"not me" cannot both be written on `name`. As a list they can, and
	`permitted_employee_filters()`' fail-closed `["name", "in", []]` survives
	the addition rather than being overwritten by it - which is the whole reason
	this is not a `dict.update()`.
	"""
	out = []
	for field, value in (filters or {}).items():
		if isinstance(value, (list, tuple)) and len(value) == 2:
			out.append([field, value[0], value[1]])
		else:
			out.append([field, "=", value])
	return out


def _scope_filters(me, me_row, is_hr):
	"""(basis, conditions) - the group whose presence this caller may see.

	The same three groups as before, said as **conditions on Employee** rather
	than as a list of names read into Python. That is what makes the card honest
	above a thousand people: see `_presence_counts`.
	"""
	if is_hr:
		from hrms.alvoraa_hr_core.access import permitted_employee_filters

		conds = _filter_list(permitted_employee_filters())
		conds += [["status", "=", "Active"], ["name", "!=", me["employee"]]]
		return "hr", conds
	if _reports(me["employee"]):
		return "team", [["reports_to", "=", me["employee"]], ["status", "=", "Active"]]
	if me_row.get("reports_to"):
		# The peer card: same manager, not me (D-3, AC-55). No department
		# fallback - somebody with no manager sees no card at all.
		return "peers", [["reports_to", "=", me_row["reports_to"]],
		                 ["status", "=", "Active"],
		                 ["name", "!=", me_row["name"]]]
	return "none", None


def _presence_counts(conds, date_):
	"""In, away and still to come - three numbers about a group of people.

	**Counted in the database, and never capped** (044 D6). The first version
	read every name in the group into Python and shipped them back as an
	`IN (...)`, capped at `LIST_CAP * 20` = 1,000 names. At 1,001 people that
	cap did not fail and it did not warn: it counted the first thousand and drew
	the answer as if it were the whole tenant. A quietly wrong number on a
	screen is worse than no number, because nobody goes looking for it.

	Two statements, whatever the headcount - the same two the old shape took,
	and the same two for twenty people as for fifty thousand:

	  1. how many people are in the group at all;
	  2. how many of them have an Attendance row today, by status.

	Still to come is the subtraction. **Which way round matters.** Driving from
	Attendance and its date index means the second statement touches only
	today's rows; driving from Employee and joining out to Attendance touches
	every person in the group. Measured on the 981-person fixture, as the System
	Manager: 12 ms this way, 52 ms the other way, and 53 ms for the old
	name-list shape. Flat, as well as fast - a company of 245 and a company of
	981 both take about 12 ms, because neither reads a row per person.

	Nothing about any one person leaves this function: the status is collapsed
	into three buckets, so a leave TYPE cannot reach a caller even by accident.
	"""
	from frappe.query_builder.functions import Count

	counts = {"in": 0, "away": 0, "due": 0}
	if not conds:
		return counts, 0

	group = int(frappe.qb.get_query(
		"Employee", fields=[Count("*")], filters=conds).run()[0][0] or 0)
	if not group:
		return counts, 0

	Att = frappe.qb.DocType("Attendance")
	rows = (
		frappe.qb.from_(Att)
		.where((Att.attendance_date == date_) & (Att.docstatus == 1)
		       & Att.employee.isin(frappe.qb.get_query(
			       "Employee", fields=["name"], filters=conds)))
		.select(Att.status, Count("*"))
		.groupby(Att.status)
	).run()
	marked = 0
	for status, n in rows:
		n = int(n or 0)
		marked += n
		if status in ("Present", "Work From Home"):
			counts["in"] += n
		else:                 # On Leave, Absent, Half Day - all just "away"
			counts["away"] += n
	# Never negative. One person cannot hold two submitted Attendance rows for
	# one day, so this should not fire - and a card that drew "-2 still to come"
	# because it did would be worse than a card that drew nothing.
	counts["due"] = max(0, group - marked)
	return counts, group


def _suppress(counts, group):
	"""The minimum-group rule and complementary suppression (042 AC-29, PRIV-2).

	**The group first.** Fewer than `MIN_GROUP` people and no number is
	published at all. In a team of four, "1 away" plus a look around the floor
	names the person.

	**Then each category.** A non-zero count below `MIN_GROUP` describes fewer
	than five people, so it is suppressed for the same reason the group is.

	**Then the complement.** Suppressing one of three categories is not enough
	when the reader can subtract: publish two of three and the third is
	arithmetic. So where one category is suppressed, the next smallest is
	suppressed with it.

	**An honest note about this function.** The spec's AC-29 (b) gives an
	example - a six-person team with one away and five in - that it says carries
	BOTH numbers, and the per-category rule above suppresses them. The two halves
	of AC-29 cannot both be satisfied by one threshold. This takes the
	fail-closed half, because that is the standing rule when a control is
	ambiguous, and D-7 is the decision that settles it.
	"""
	if group < MIN_GROUP:
		return {"in": None, "away": None, "due": None, "suppressed": True}
	hidden = {k for k, v in counts.items() if 0 < v < MIN_GROUP}
	# The complement is added only when exactly ONE of the three is hidden.
	# With three categories and a total the reader can guess, publishing two
	# pins the third by subtraction - so at most one may be published once
	# anything is hidden. Two already hidden means one published, which pins
	# neither, and adding a third would suppress a nineteen-person team's
	# numbers for no gain. Worked through rather than "hide one more to be
	# safe".
	if len(hidden) == 1:
		rest = sorted(((v, k) for k, v in counts.items() if k not in hidden))
		if rest:
			hidden.add(rest[0][1])
	out = {k: (None if k in hidden else v) for k, v in counts.items()}
	out["suppressed"] = bool(hidden)
	return out


def _team_today(me, me_row, is_hr, date_):
	"""The team card, for whichever kind of caller is asking.

	A manager sees their own reports. An HR caller sees the people they look
	after, through `permitted_employee_filters()` - the same rule
	`permitted_employees()` is built on, pushed into the query instead of read
	into a list. Everybody else sees their peers, and somebody with no manager
	sees nothing at all.
	"""
	basis, conds = _scope_filters(me, me_row, is_hr)
	counts, group = _presence_counts(conds, date_) if conds else ({}, 0)
	if not group:
		# Not an empty card frame and not a silent zero: nothing is drawn
		# (042 AC-33, AC-55).
		return {"in": None, "away": None, "due": None, "basis": "none",
		        "suppressed": False}
	shown = _suppress(counts, group)
	shown["basis"] = basis
	return {k: shown.get(k) for k in TEAM_TODAY_KEYS}


# ── What needs this person ───────────────────────────────────────────────────


def _self_review(employee):
	"""Is a self-review waiting, and when is the cycle's end?

	**Status only.** `performance_api.get_my_review` CREATES an extension record
	when it is read, so Home must never call it - drawing a page must not write
	a row (042 section 3).
	"""
	if not frappe.db.exists("DocType", "Appraisal"):
		return None
	# Appraisal itself has no `status` field - read in the doctype JSON, not
	# assumed. The state of a self-review lives on Alvoraa Appraisal Extension's
	# `review_status`, which is what `performance_api.get_my_appraisals` reads.
	row = frappe.db.get_value(
		"Appraisal",
		{"employee": employee, "docstatus": ["<", 2]},
		["name", "appraisal_cycle"], as_dict=True, order_by="modified desc")
	if not row:
		return None
	state = ""
	if frappe.db.exists("DocType", "Alvoraa Appraisal Extension"):
		state = frappe.db.get_value(
			"Alvoraa Appraisal Extension", {"appraisal": row["name"]},
			"review_status") or ""
	if state.lower() in ("completed", "closed", "frozen"):
		return None
	due = None
	if row.get("appraisal_cycle"):
		due = frappe.db.get_value("Appraisal Cycle", row["appraisal_cycle"], "end_date")
	return {"name": row["name"], "due": str(due) if due else None}


def _payslip_ready(employee, features):
	"""The "your payslip is ready" row, behind the REAL entitlement gate.

	`features` comes from `hr_api.get_available_features()`, which reads
	`subscription.has_feature` - the same gate the desk uses. Absent means
	hidden, never shown: a tenant that was never given payroll and an
	entitlement read that failed must look the same (Wave 1 AC-45).

	The row carries the period and nothing else. A take-home figure is the
	caller's own business and `_own_payslip` is the whole check for it
	(042 section 5).
	"""
	if not features.get("plan_payroll"):
		return None
	if not frappe.db.exists("DocType", "Salary Slip"):
		return None
	row = frappe.db.get_value(
		"Salary Slip", {"employee": employee, "docstatus": 1},
		["name", "start_date", "end_date"], as_dict=True, order_by="start_date desc")
	if not row:
		return None
	return {"name": row["name"], "period": str(row["start_date"])}


def _needs(me, me_row, features, date_):
	"""The "Needs you" list, most urgent first.

	The caller's own facts only. No approval rows here - those are the Inbox's,
	and putting them on Home as well would be a second place the same work is
	counted (042 D-1: the heading carries no number at all).
	"""
	out = []
	gaps = _gap_days(me["employee"], me_row.get("date_of_joining"), date_)
	if gaps:
		shown = gaps[:LIST_CAP]
		out.append({
			"id": "attendance_gap",
			"kind": "attendance_gap",
			"title": (_("{n} day has no attendance") if len(gaps) == 1
			          else _("{n} days have no attendance")).format(n=len(gaps)),
			# The number in the title equals the number of days the Fix sheet
			# lists, because both come from `_gap_days` (042 AC-22).
			# `from_date` and `to_date` bracket what the Fix sheet will show, and
			# `shown` is newest first, so they are min and max rather than first
			# and last.
			"detail": {"days": shown, "total": len(gaps),
			           "from_date": min(shown), "to_date": max(shown),
			           "capped": len(gaps) > len(shown)},
			"action": "fix_attendance",
			"route": "#time/fix",
		})
	review = _self_review(me["employee"])
	if review:
		out.append({
			"id": "self_review",
			"kind": "self_review",
			"title": _("Your self-review is waiting"),
			"detail": {"due": review["due"]},
			"action": "open_review",
			"route": "#growth/review",
		})
	payslip = _payslip_ready(me["employee"], features)
	if payslip:
		out.append({
			"id": "payslip",
			"kind": "payslip",
			"title": _("Your payslip is ready"),
			"detail": {"period": payslip["period"]},
			"action": "open_payslip",
			"route": "#pay",
		})
	return out


# ── Goals ────────────────────────────────────────────────────────────────────


def _goals(me, is_hr, features):
	"""The caller's own goals, and a team summary for a manager or HR.

	A colleague's goal percentage is never shown to a peer (042 section 5); the
	team summary is counts, and it follows the same minimum-group rule as the
	presence card.
	"""
	if not features.get("goals"):
		return {"mine": None, "team": None}
	if not frappe.db.exists("DocType", "Individual Goal"):
		return {"mine": None, "team": None}
	mine = frappe.get_all(
		"Individual Goal",
		filters={"employee": me["employee"], "status": ["!=", "Cancelled"],
		         "docstatus": ["!=", 2]},
		# `progress_pct`, read in the doctype JSON. There is no `progress`.
		fields=["name", "goal_name", "progress_pct"], order_by="modified desc",
		limit_page_length=LIST_CAP)
	summary = {"count": len(mine),
	           "rows": [{"name": r.name, "goal_name": r.goal_name,
	                     "progress": r.progress_pct} for r in mine]}
	team = None
	names = _hr_scope() if is_hr else _reports(me["employee"])
	names = [n for n in (names or []) if n != me["employee"]]
	if names:
		total = frappe.db.count(
			"Individual Goal",
			{"employee": ["in", names[:LIST_CAP]], "status": ["!=", "Cancelled"],
			 "docstatus": ["!=", 2]})
		team = {"people": len(names), "goals": total} if len(names) >= MIN_GROUP else {
			"people": len(names), "goals": None}
	return {"mine": summary, "team": team}


# ── Celebrations ─────────────────────────────────────────────────────────────


def _celebrations(me_row, date_):
	"""The caller's own work anniversary, and nothing about anybody else.

	**D-8 is not answered, so no joiners list is built.** `joiners` is an empty
	tuple and a test asserts it stays empty. Listing the newest people in the
	building by name on four hundred colleagues' screens is the one new
	disclosure in this slice; it waits for a decision rather than shipping with
	an opt-out bolted on later.
	"""
	years = None
	joined = me_row.get("date_of_joining")
	if joined:
		joined = getdate(joined)
		date_ = getdate(date_)
		if joined.month == date_.month and joined.day == date_.day and joined.year < date_.year:
			years = date_.year - joined.year
	return {"own_anniversary_years": years, "joiners": []}


# ── The call ─────────────────────────────────────────────────────────────────


@frappe.whitelist()
def get_home():
	"""Everything Home draws, for this caller and nobody else (042 US-1 to US-3).

	Guest is refused by `frappe.whitelist()` without `allow_guest`. The explicit
	line below is what still refuses if somebody ever adds it (SEC-2).

	A caller with no Active Employee record gets `me: None` and every card empty
	- one plain line on screen and **no errors** (042 AC-37). The scoped queries
	do not run: that is an explicit early return, not a filter that happened to
	be skipped.
	"""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please sign in."), frappe.PermissionError)

	# One memo, for this call and no longer (044 R1). Home asks four questions
	# more than once - the caller's holiday list, their company, their reports,
	# and for HR the permitted-employee list - and nothing inside this call
	# writes, so the answer cannot change between two of them. It is torn down
	# in the `finally` below whether this returns or raises: a scope that
	# outlived the call would be a permission bug, not a cache.
	open_cache()
	try:
		return _build_home(user)
	finally:
		close_cache()


def _build_home(user):
	"""Everything `get_home` returns. Split out only so the memo has a `finally`."""
	from alvoraa_portal.hr_api import (
		_ledger_leave_balances,
		_own_upcoming_holidays,
		checkin_needs_location,
		get_available_features,
	)

	date_ = today()
	me, me_row = _me(user)

	home = {
		"me": me,
		"today": {"date": str(date_), "shift": None, "checkin": None,
		          "needs_location": False},
		"needs": [],
		"leave": [],
		"holidays": [],
		"holiday_note": None,
		"goals": {"mine": None, "team": None},
		"team_today": {"in": None, "away": None, "due": None, "basis": "none",
		               "suppressed": False},
		"celebrations": {"own_anniversary_years": None, "joiners": []},
	}

	if not me:
		# Persona rule 6. Every key is already at its empty value, so the page
		# draws its one plain line from the same shape everybody else gets.
		return {key: home[key] for key in HOME_KEYS}

	features = _card("features", get_available_features, default={}) or {}
	# "HR" here means the same thing the corrections queue and the staff list
	# mean by it: somebody `permitted_companies()` gives a company to. Asked
	# through the shared helper rather than from a role list of our own, so a
	# store's HR person is a store's HR person on this page too (W1D-20).
	from hrms.alvoraa_hr_core.access import permitted_companies

	is_hr = bool(_card("hr_scope", permitted_companies, default=None))

	home["today"] = _card("today", lambda: {
		"date": str(date_),
		"shift": _shift_today(me["employee"], me_row.get("default_shift"), date_),
		"checkin": _checkin_today(me["employee"], date_),
		"needs_location": bool(checkin_needs_location()),
	}, default={"date": str(date_), "shift": None, "checkin": None,
	            "needs_location": False})

	home["needs"] = _card("needs", lambda: _needs(me, me_row, features, date_),
	                      default=[])
	home["leave"] = _card("leave", lambda: [
		{"leave_type": r.get("leave_type"), "total": r.get("total"),
		 "used": r.get("taken"), "left": r.get("balance")}
		for r in (_ledger_leave_balances(me["employee"], date_) or [])
	], default=[])

	def _holidays():
		rows, note = _own_upcoming_holidays(me["employee"], date_)
		return {"rows": [{"date": str(h.holiday_date),
		                  "description": h.description,
		                  "weekly_off": 0} for h in rows], "note": note}

	holidays = _card("holidays", _holidays,
	                 default={"rows": [], "note": None})
	if isinstance(holidays, dict) and not holidays.get("error"):
		home["holidays"] = holidays["rows"]
		home["holiday_note"] = holidays["note"]
	else:
		home["holidays"] = {"error": True}

	home["goals"] = _card("goals", lambda: _goals(me, is_hr, features))
	home["team_today"] = _card("team_today",
	                           lambda: _team_today(me, me_row, is_hr, date_))
	home["celebrations"] = _card("celebrations",
	                             lambda: _celebrations(me_row, date_))

	# The guarantee, enforced rather than described: whatever the code above
	# does, the payload leaves with exactly HOME_KEYS and nothing else. A new
	# field cannot reach a browser by accident (042 AC-5).
	return {key: home[key] for key in HOME_KEYS}
