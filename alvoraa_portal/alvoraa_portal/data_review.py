"""Data to review: figures whose data looks wrong, found every morning (slice 012).

Push 1 of the leadership view. Three things live here:

  indexes           the nine indexes every scoped figure filters on
  morning checks    doubtful attendance days, leave that looks unrecorded,
                    leavers with no leaving date
  Data to review    HR's list of those findings, and their confirmations

Nothing here stores a figure. Findings hold counts and dates only - never an
employee, a name or a leave type.
"""

import json

import frappe
from frappe.utils import add_days, add_months, cint, flt, getdate, now_datetime, today

from alvoraa_portal.alvoraa_portal.doctype.alvoraa_data_review_item.alvoraa_data_review_item import (
	COUNT_FIELDS,
	item_name,
)
from alvoraa_portal.subscription import requires_feature

DOCTYPE = "Alvoraa Data Review Item"
SETTINGS = "Alvoraa Leader View Settings"

JOB_METHOD = "alvoraa_portal.data_review.run_morning_checks"
JOB_ID = "leader-data-checks"
FAILED_TITLE = "Leader data checks failed"

WINDOW_DAYS = 35           # how far back doubtful days are looked for
ABSENT_PCT = 95            # a day is doubtful at 95% or more marked absent...
CHECKED_IN_PCT = 5         # ...and fewer than 5% checked in

# ALV-440: a branch's punch feed judged against that branch's OWN normal for
# that weekday, rather than against a share of people marked absent. Why the
# weekday matters: a shop whose weekly off is Monday has no punches on Mondays,
# and a rule that does not know this either cries wolf every week or has to be
# set so loose it sees nothing. Learning the pattern from the branch's own data
# needs no holiday list to be right - and at DTC the Ambala Monday list is
# assigned to 1 employee of 63, so a rule that trusted it would be wrong.
FEED_BASELINE_WEEKS = 6    # how many earlier same-weekdays make "normal"
FEED_MIN_SAMPLES = 3       # ...of which at least this many must have data
FEED_MIN_NORMAL = 5        # a branch-weekday normally quieter than this is not judged
FEED_DROP_PCT = 40         # fires below 40% of that normal
HOLIDAY_MAJORITY_PCT = 50  # a day counts as the branch's holiday above this share
LEAVE_MONTHS_IN = 3        # leave used is judged from three months into the leave year
LEAVE_USED_PCT = 1         # below 1% of leave allocated looks unrecorded
DAILY_RULES = ("D6", "D18-1", "D18-2")
# Rules keyed by a branch and a day. They share one window, and a record of
# theirs still Open from before the window is looked at again so it can clear.
DAY_RULES = ("D5", "D20")

# More Open items than one scope can have: 25 branches x 35 days, plus a few per company.
MAX_ITEMS = 1000


def item_filters(scope, **extra):
	"""Filters limiting review records to an HR scope.

	The explicit branch filter matters for location HR: Frappe's User Permissions
	let a record with an EMPTY branch through, and a company-wide item carries
	company-wide counts that a store's HR person has no business reading.
	"""
	filters = {"company": ["in", list(scope.companies) or [""]], **extra}
	if scope.branches is not None:
		filters["alvoraa_branch"] = ["in", list(scope.branches) or [""]]
	return filters


def open_count_for_hr():
	"""How many figures need review in this HR user's scope, for the menu badge.

	One permission-checked read, only for a tenant whose plan includes analytics.
	Never raises: a badge is not worth breaking the portal for (DEF-3, AC-31).
	"""
	try:
		from alvoraa_portal import org_figures as of
		from alvoraa_portal.subscription import has_feature

		if not has_feature("analytics"):
			return 0
		scope = of.hr_scope()
		if scope.not_linked:
			return 0
		return len(frappe.get_list(DOCTYPE, filters=item_filters(scope, status="Open"),
		                           pluck="name", limit_page_length=MAX_ITEMS))
	except Exception:
		return 0


def review_summary(scope):
	"""How many figures need review in this scope, and which days look wrong (AC-17, AC-46).

	Read with get_list, so the caller's own permissions apply too.
	"""
	if scope.not_linked:
		return {"open_count": 0, "doubtful_dates": []}
	rows = frappe.get_list(DOCTYPE, filters=item_filters(scope, status="Open"),
	                       fields=["item_type", "check_date"], limit_page_length=MAX_ITEMS)
	dates = sorted({str(r.check_date) for r in rows if r.item_type == "Doubtful day" and r.check_date})
	return {"open_count": len(rows), "doubtful_dates": dates}


# ── indexes (US-1, OPS-52, OPS-70) ───────────────────────────────────────────
#
# One-column indexes need a Property Setter as well as the index. Frappe 16
# drops a single-column index on a standard table whenever it re-syncs that
# table and the field is not marked "indexed" (database/schema.py, the drop
# list). A re-sync happens on an ERPNext update, and also any time somebody
# saves a Custom Field on Employee. `add_index` would mark the field itself,
# but skips that step during migrate and install - exactly where this runs.
# Two-column indexes are never dropped that way, so they need no marker.

SINGLE_COLUMN_INDEXES = (
	("Employee", "company"),
	("Employee", "branch"),
	("Employee", "department"),
	("Employee", "date_of_joining"),
	("Employee", "relieving_date"),
	("Employee Checkin", "time"),
)

TWO_COLUMN_INDEXES = (
	("Employee Checkin", ("alvoraa_branch", "time")),
	# Added 2026-11-13 (ALV-337). punch_dedupe asks "has this employee a kept
	# punch in the last two minutes" on EVERY punch insert - about 9,000 a month
	# at DTC. The employee link index alone narrows to that person's whole
	# history, which only grows; this pair narrows to the two minutes.
	("Employee Checkin", ("employee", "time")),
	("Attendance", ("alvoraa_branch", "attendance_date")),
	# Added 2026-09-16 (DEF-7). OPS-55 said this one waits until EXPLAIN shows a
	# full scan: at 1,000 people it did. "Data up to" and the job's "has this
	# company any attendance" read the whole Attendance table without it, and both
	# run on every call.
	("Attendance", ("company", "attendance_date")),
)


def add_indexes():
	"""Create the nine indexes. Safe to run again: it changes nothing then."""
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	for doctype, field in SINGLE_COLUMN_INDEXES:
		marked = frappe.db.exists(
			"Property Setter",
			{"doc_type": doctype, "field_name": field, "property": "search_index"},
		)
		# Only when missing: writing it again deletes and re-inserts the row and
		# clears the doctype's cache on every migrate. `is_system_generated` stays
		# True, so "Reset to defaults" in Customize Form leaves it alone.
		if not marked:
			make_property_setter(doctype, field, "search_index", "1", "Check", for_doctype=False)
		frappe.db.add_index(doctype, [field])

	for doctype, fields in TWO_COLUMN_INDEXES:
		# The branch column comes from slice 011's installer, which runs just
		# before this one in the hook lists. Checked anyway, so a site where it
		# is missing still migrates.
		if all(frappe.db.has_column(doctype, f) for f in fields):
			frappe.db.add_index(doctype, list(fields))


def after_install():
	"""A site built with `bench install-app` (CI) never runs after_migrate.

	No first check here: a new site has no data to check.
	"""
	add_indexes()
	_ensure_settings()


def after_migrate():
	add_indexes()
	_ensure_settings()
	# OPS-72: check once at deploy, so HR's attendance figure changes once - not
	# on deploy day and again at 06:30 the next morning. Queued for the long
	# worker, which keeps running while migrate holds the scheduler. (Frappe runs
	# a job inline only if Redis cannot be reached during migrate.)
	try:
		enqueue_morning_checks()
	except Exception:
		frappe.log_error(title=FAILED_TITLE, message=json.dumps(
			{"company": None, "stage": "queue after migrate", "error": "could not queue"}))


def _ensure_settings():
	from alvoraa_portal.alvoraa_portal.doctype.alvoraa_leader_view_settings.alvoraa_leader_view_settings import (
		ensure_default,
	)

	ensure_default()


# ── morning checks (US-3, US-5, US-7, OPS-48 to OPS-50) ──────────────────────
#
# 06:30: a cron entry queues one job on the long queue (a cron entry itself runs
# on the default queue). The job looks at every company:
#
#   D5     a branch's day is doubtful when at least ABSENT_PCT of the people
#          expected are marked absent and fewer than CHECKED_IN_PCT checked in -
#          or, for a company with no check-ins at all, the absent test alone.
#          Only for groups of at least the minimum group size (PRIV-10).
#   D6     leave used under 1%, three months or more into the leave year
#   D18-1  people marked Left with no leaving date, per branch
#   D18-2  nobody in the company has a leaving date in the last 12 months
#
# Writes only what changed; never touches a Confirmed record; never deletes -
# a finding that stops firing is marked Cleared. Commits per company, so a
# failure keeps the companies already done.


def enqueue_morning_checks():
	"""The cron entry. Queues the job once; a second queue while it runs does nothing."""
	frappe.enqueue(JOB_METHOD, queue="long", timeout=900, job_id=JOB_ID, deduplicate=True)


def run_morning_checks(companies=None):
	"""Check every company, then stamp "last checked" only if all of them finished.

	`companies` narrows a run to some companies; the scheduled job passes none.
	"""
	from alvoraa_portal.alvoraa_portal.doctype.alvoraa_leader_view_settings.alvoraa_leader_view_settings import (
		min_group_size,
	)
	from alvoraa_portal.subscription import has_feature

	# D-9: a tenant whose plan has no analytics has no screen that uses these.
	if not has_feature("analytics"):
		return

	minimum = min_group_size()
	as_of = getdate(today())
	failed = False
	created = []
	for company in companies or frappe.get_all("Company", pluck="name", order_by="name asc"):
		stage = {"now": "start"}
		try:
			existing = existing_items(company, as_of)
			findings = company_findings(company, minimum, as_of, stage=stage,
			                            also_days=_open_day_rule_days(existing))
			stage["now"] = "save"
			apply_findings(existing, findings, allow_create=True, created=created)
			frappe.db.commit()
		except Exception as e:
			frappe.db.rollback()
			failed = True
			_log_failure(company, stage["now"], e)

	if not failed:
		frappe.db.set_single_value(SETTINGS, "last_checks_run_on", now_datetime())
		frappe.db.commit()

	# ALV-440: last, and after every commit. A finding nobody is told about is
	# not an alarm - four Pitampura findings sat Open on production from 16 to
	# 23 Nov 2026 while the branch's feed was dead (ALV-439). Never raises: the
	# findings are already saved and a mail must not undo them.
	if created:
		tell_hr_about(created)


def _log_failure(company, stage, error):
	"""Company, stage and the error's type. Never the traceback: its local values
	can hold counts and names (OPS-50, OPS-57)."""
	try:
		frappe.log_error(title=FAILED_TITLE, message=json.dumps(
			{"company": company, "stage": stage, "error": type(error).__name__}))
		frappe.db.commit()
	except Exception:
		pass


def _finding(rule, item_type, company, branch=None, check_date=None, **counts):
	return {"name": item_name(rule, company, branch, check_date), "rule": rule, "item_type": item_type,
	        "company": company, "alvoraa_branch": branch or None,
	        "check_date": getdate(check_date) if check_date else None,
	        **{f: counts.get(f, 0) for f in COUNT_FIELDS}}


def company_findings(company, minimum, as_of, rules=DAY_RULES + DAILY_RULES, branches=None,
                     stage=None, also_days=None):
	"""{record name: finding} for the rules asked, for one company. Grouped queries only.

	`branches` limits D18-1 to those branches (location HR's page re-check).
	`also_days` is (branch, day) pairs outside the 35-day window that must be
	looked at as well - the days of records still Open from an earlier run. Left
	out, they are read here; the job and the page pass the ones they already hold.
	"""
	from alvoraa_portal import org_figures as of

	stage = stage if stage is not None else {}
	out = {}
	# A company with no attendance yet has "no figures", not figures to review (AC-30).
	if not frappe.db.sql("select 1 from `tabAttendance` where company = %s and docstatus = 1 limit 1",
	                     company):
		return out

	holidays = frozenset()
	if any(r in rules for r in DAY_RULES):
		stage["now"] = "holidays"
		if also_days is None:
			also_days = _open_day_rule_days_before(company, add_days(as_of, -WINDOW_DAYS), branches)
		# Far enough back to cover the punch rule's baseline weeks as well, so a
		# festival is not counted as one of a branch's normal same-weekdays.
		holidays = _holiday_branch_days(
			company, add_days(as_of, -WINDOW_DAYS - 7 * FEED_BASELINE_WEEKS), as_of)

	if "D5" in rules:
		stage["now"] = "doubtful days"
		out.update(_doubtful_days(company, minimum, as_of, also_days=also_days, holidays=holidays))

	if "D20" in rules:
		stage["now"] = "punch feed"
		out.update(_punch_feed(company, minimum, as_of, holidays=holidays, also_days=also_days))

	if "D6" in rules or "D18-2" in rules:
		stage["now"] = "leave"
		ys, _ye = of.leave_year(company, as_of)
	if "D6" in rules:
		leave = of.leave_figures(of.Scope((company,), None), as_of)["by_company"][company]
		if (as_of >= getdate(add_months(ys, LEAVE_MONTHS_IN)) and leave["allocated"] > 0
		        and leave["taken"] * 100 < leave["allocated"] * LEAVE_USED_PCT):
			f = _finding("D6", "Leave used", company, None, ys, affected_count=leave["requests"],
			             people_count=leave["people"], days_allocated=flt(leave["allocated"], 2))
			out[f["name"]] = f

	if "D18-1" in rules:
		stage["now"] = "leavers"
		for row in frappe.db.sql("""
			select e.branch, count(*) as n from `tabEmployee` e
			where e.company = %s and e.status = 'Left' and e.relieving_date is null
			group by e.branch""", company, as_dict=True):
			if branches is not None and row.branch not in branches:
				continue
			f = _finding("D18-1", "Leavers", company, row.branch, None, affected_count=cint(row.n))
			out[f["name"]] = f

	if "D18-2" in rules:
		stage["now"] = "leavers"
		recent = frappe.db.sql("""
			select count(*) from `tabEmployee` e
			where e.company = %s and e.relieving_date between %s and %s""",
			(company, add_days(add_months(as_of, -12), 1), as_of))[0][0]
		if not cint(recent):
			f = _finding("D18-2", "Leavers", company, None, ys)
			out[f["name"]] = f
	return out


def _doubtful_days(company, minimum, as_of, also_days=(), holidays=frozenset()):
	"""D5 for every named branch and day in the window. Three queries for the company,
	and a fourth only when a record older than the window is still Open.

	Employees with no branch are not checked (decision D-12).
	"""
	start, end = add_days(as_of, -WINDOW_DAYS), add_days(as_of, -1)
	params = {"company": company, "start": start, "end": end, "minimum": minimum,
	          "end_next": add_days(end, 1)}
	days = frappe.db.sql("""
		select a.alvoraa_branch as branch, a.attendance_date as day,
		       sum(a.status != 'On Leave') as expected, sum(a.status = 'Absent') as absent
		from `tabAttendance` a
		where a.docstatus = 1 and a.company = %(company)s
		  and a.alvoraa_branch is not null and a.alvoraa_branch != ''
		  and a.attendance_date between %(start)s and %(end)s
		group by a.alvoraa_branch, a.attendance_date
		having expected >= %(minimum)s and absent * 100 >= expected * {absent_pct}
	""".format(absent_pct=ABSENT_PCT), params, as_dict=True)

	older = sorted({(b, getdate(d)) for b, d in also_days if b and getdate(d) < getdate(start)})
	if older:
		# The same rule, for named days only. A day whose data has since been fixed
		# does not come back, and its record is Cleared below.
		rows = frappe.db.sql("""
			select a.alvoraa_branch as branch, a.attendance_date as day,
			       sum(a.status != 'On Leave') as expected, sum(a.status = 'Absent') as absent
			from `tabAttendance` a
			where a.docstatus = 1 and a.company = %(company)s
			  and a.alvoraa_branch in %(old_branches)s
			  and a.attendance_date in %(old_days)s
			group by a.alvoraa_branch, a.attendance_date
			having expected >= %(minimum)s and absent * 100 >= expected * {absent_pct}
		""".format(absent_pct=ABSENT_PCT),
			{**params, "old_branches": sorted({b for b, _d in older}),
			 "old_days": sorted({d for _b, d in older})}, as_dict=True)
		days += [r for r in rows if (r.branch, getdate(r.day)) in older]

	if not days:
		return {}

	# Check-ins are read from the oldest day being looked at, so a re-checked
	# old day is judged on its own check-ins.
	params = {**params, "start": min([getdate(d.day) for d in days] + [getdate(start)])}
	any_checkins = frappe.db.sql("""
		select 1 from `tabEmployee Checkin` c
		join `tabEmployee` e on e.name = c.employee
		where e.company = %(company)s and c.time >= %(start)s and c.time < %(end_next)s
		limit 1""", params)
	checked = {}
	if any_checkins:
		for r in frappe.db.sql("""
			select c.alvoraa_branch as branch, date(c.time) as day, count(distinct c.employee) as n
			from `tabEmployee Checkin` c
			join `tabEmployee` e on e.name = c.employee
			where e.company = %(company)s
			  and c.alvoraa_branch in %(branches)s
			  and c.time >= %(start)s and c.time < %(end_next)s
			group by c.alvoraa_branch, date(c.time)""",
			{**params, "branches": sorted({d.branch for d in days})}, as_dict=True):
			checked[(r.branch, getdate(r.day))] = cint(r.n)

	out = {}
	for d in days:
		# ALV-440: a festival the whole branch shares is not a doubtful day. The
		# alarm has to be quiet on the days it should be, or the days it should
		# not be stop being read - which is how the Pitampura feed in ALV-439
		# went ten days with four findings already Open.
		if (d.branch, getdate(d.day)) in holidays:
			continue
		expected, absent = cint(d.expected), cint(d.absent)
		n = checked.get((d.branch, getdate(d.day)), 0)
		if any_checkins and n * 100 >= expected * CHECKED_IN_PCT:
			continue
		f = _finding("D5", "Doubtful day", company, d.branch, d.day,
		             expected_count=expected, absent_count=absent, checked_in_count=n)
		out[f["name"]] = f
	return out


def _holiday_branch_days(company, start, end):
	"""(branch, day) that is a holiday for MOST of that branch's active people.

	Most, not any, and the difference is load-bearing. At DTC the holiday list
	"Ambala Monday off" is on 1 employee of 63, so a rule that skipped a day
	because *some* list held it would let one mis-assigned record silence a whole
	branch's alarm for ever. Above half, and only the festivals everybody shares
	are skipped; Ambala's Mondays are made quiet by the weekday baseline in
	_punch_feed instead, which needs no list to be right.

	Two grouped queries for the company. Holiday rows carry no employee.
	"""
	heads = {}
	for r in frappe.db.sql("""
		select e.branch as branch, e.holiday_list as list, count(*) as n
		from `tabEmployee` e
		where e.company = %s and e.status = 'Active'
		  and e.branch is not null and e.branch != ''
		group by e.branch, e.holiday_list""", company, as_dict=True):
		heads.setdefault(r.branch, {})[r.list] = cint(r.n)

	lists = sorted({lst for per in heads.values() for lst in per if lst})
	if not lists:
		return frozenset()

	held = {}
	for r in frappe.db.sql("""
		select h.parent as list, h.holiday_date as day from `tabHoliday` h
		where h.parent in %(lists)s and h.holiday_date between %(start)s and %(end)s""",
		{"lists": lists, "start": getdate(start), "end": getdate(end)}, as_dict=True):
		held.setdefault(r.list, set()).add(getdate(r.day))

	out = set()
	for branch, per in heads.items():
		total = sum(per.values())
		if not total:
			continue
		covered = {}
		for lst, n in per.items():
			for day in held.get(lst, ()):
				covered[day] = covered.get(day, 0) + n
		out.update((branch, day) for day, n in covered.items()
		           if n * 100 > total * HOLIDAY_MAJORITY_PCT)
	return frozenset(out)


def _punch_feed(company, minimum, as_of, holidays=frozenset(), also_days=()):
	"""D20: a branch sending far fewer punches than it normally does on this weekday.

	`minimum` is the tenant's own minimum group size (PRIV-10). A branch whose
	normal is smaller than that is never judged, so a finding never describes a
	group too small to be anonymous - the same floor every other rule here keeps.

	The rule that would have caught ALV-439 on the day it began. Pitampura went
	from thirty-odd people punching to nought or two overnight, and D5 did not
	see five of those nine days because they measured 92.7, 92.2, 94.1, 94.2 and
	94.2% absent against a 95% bar. Asking "did this branch send what it normally
	sends?" sees all nine, and does not care how big the branch is.

	What it deliberately does NOT catch, because it is a branch-level rule: a
	handful of people at a healthy branch who stop punching one or two at a time.
	Replayed against DTC's real November, this stayed silent on DTC Delhi, which
	sent me back to look again - and the 19 people there had last punches spread
	over six days, which is people leaving and never being marked as leavers, not
	a device. A dead reader stops everybody at once. See the correction on
	ALV-439; unrecorded leavers need their own rule and nothing covers them yet.

	"Normal" is the median of the branch's own punchers on up to
	FEED_BASELINE_WEEKS earlier SAME weekdays, counting only the same-weekdays it
	actually punched on. So a shop closed every Monday has no Monday samples and
	is never judged on a Monday, with no holiday list involved - and a branch
	that closes for good stops being judged once its last samples age out, rather
	than nagging for ever.

	Two grouped queries for the company. Counts and dates only, never a name.
	"""
	from statistics import median

	start, end = add_days(as_of, -WINDOW_DAYS), add_days(as_of, -1)
	older = {(b, getdate(d)) for b, d in also_days if b and getdate(d) < getdate(start)}
	first = min([getdate(start)] + [d for _b, d in older])
	read_from = add_days(first, -7 * FEED_BASELINE_WEEKS)

	punched = {}
	for r in frappe.db.sql("""
		select c.alvoraa_branch as branch, date(c.time) as day, count(distinct c.employee) as n
		from `tabEmployee Checkin` c
		join `tabEmployee` e on e.name = c.employee
		where e.company = %(company)s
		  and c.alvoraa_branch is not null and c.alvoraa_branch != ''
		  and c.time >= %(read_from)s and c.time < %(end_next)s
		group by c.alvoraa_branch, date(c.time)""",
		{"company": company, "read_from": read_from, "end_next": add_days(end, 1)}, as_dict=True):
		punched[(r.branch, getdate(r.day))] = cint(r.n)
	if not punched:
		# No punches anywhere: this tenant does not take attendance from devices,
		# so there is no feed to lose. D5 still watches the absences.
		return {}

	# A branch-day is judged only while the branch is in use, which its own
	# attendance says. Days before the window are judged only when a record of
	# theirs is still Open, so it can clear.
	clauses = ["a.attendance_date between %(start)s and %(end)s"]
	params = {"company": company, "start": getdate(start), "end": getdate(end)}
	if older:
		clauses.append("a.attendance_date in %(old_days)s")
		params["old_days"] = sorted({d for _b, d in older})
	expected = {}
	for r in frappe.db.sql("""
		select a.alvoraa_branch as branch, a.attendance_date as day,
		       sum(a.status != 'On Leave') as expected
		from `tabAttendance` a
		where a.docstatus = 1 and a.company = %(company)s
		  and a.alvoraa_branch is not null and a.alvoraa_branch != ''
		  and ({clauses})
		group by a.alvoraa_branch, a.attendance_date
	""".format(clauses=" or ".join(clauses)), params, as_dict=True):
		expected[(r.branch, getdate(r.day))] = cint(r.expected)

	out = {}
	for (branch, day), exp in sorted(expected.items()):
		if day < getdate(start) and (branch, day) not in older:
			continue
		if (branch, day) in holidays:
			continue
		samples = []
		for w in range(1, FEED_BASELINE_WEEKS + 1):
			back = getdate(add_days(day, -7 * w))
			if (branch, back) in holidays:
				continue
			if (branch, back) in punched:
				samples.append(punched[(branch, back)])
		if len(samples) < FEED_MIN_SAMPLES:
			continue
		normal = int(median(samples))
		if normal < max(cint(minimum), FEED_MIN_NORMAL):
			continue
		n = punched.get((branch, day), 0)
		if n * 100 >= normal * FEED_DROP_PCT:
			continue
		f = _finding("D20", "Punch feed", company, branch, day,
		             expected_count=exp, checked_in_count=n, people_count=normal)
		out[f["name"]] = f
	return out


def existing_items(company, as_of, rules=DAY_RULES + DAILY_RULES, branches=None):
	"""The records these rules are responsible for: doubtful days inside the window,
	and every leave and leavers record of the company."""
	fields = ["name", "status", "rule", *COUNT_FIELDS]
	out = {}
	base = {"company": company}
	if branches is not None:
		base["alvoraa_branch"] = ["in", list(branches) or [""]]
	day_rules = [r for r in rules if r in DAY_RULES]
	if day_rules:
		# Inside the window, plus every Open record older than it. Without the
		# second half, a doubtful day HR fixed after 35 days stayed Open for ever:
		# on their list, in the "needs review" count, and clearable only by saying
		# the absence was real, which would be untrue.
		for r in frappe.get_all(
			DOCTYPE, filters={**base, "rule": ["in", day_rules]},
			or_filters=[["check_date", ">=", add_days(as_of, -WINDOW_DAYS)], ["status", "=", "Open"]],
			fields=[*fields, "alvoraa_branch", "check_date"], limit_page_length=0):
			out[r.name] = r
	daily = [r for r in rules if r in DAILY_RULES]
	if daily:
		for r in frappe.get_all(DOCTYPE, filters={**base, "rule": ["in", daily]}, fields=fields,
		                        limit_page_length=0):
			out[r.name] = r
	return out


def _open_day_rule_days_before(company, start, branches=None):
	"""(branch, day) of day-rule records still Open from before the window."""
	filters = {"company": company, "rule": ["in", list(DAY_RULES)], "status": "Open",
	           "check_date": ["<", start]}
	if branches is not None:
		filters["alvoraa_branch"] = ["in", list(branches) or [""]]
	return [(r.alvoraa_branch, r.check_date) for r in frappe.get_all(
		DOCTYPE, filters=filters, fields=["alvoraa_branch", "check_date"], limit_page_length=0)]


def _open_day_rule_days(existing):
	"""(branch, day) of every day-rule record still Open, so a day outside the
	window is looked at again and can clear."""
	return [(r.get("alvoraa_branch"), r.get("check_date")) for r in existing.values()
	        if r.get("rule") in DAY_RULES and r.get("status") == "Open" and r.get("check_date")]


def apply_findings(existing, findings, allow_create, created=None):
	"""Write only the differences. Returns how many records changed.

	`allow_create` is False on HR's page re-check: creating a record there would
	need rights HR does not have, so new findings wait for the morning (D-5).

	`created`, when a list is passed, collects the names of the records this call
	made - what ALV-440 tells HR about. A record that only had its counts changed
	is deliberately not in it: HR has already been told about that finding.
	"""
	changed = 0
	for name, f in findings.items():
		row = existing.get(name)
		if row is None:
			if not allow_create:
				continue
			doc = frappe.get_doc({"doctype": DOCTYPE, **{k: v for k, v in f.items() if k != "name"},
			                      "status": "Open", "first_found_on": now_datetime()})
			doc.flags.via_rule_check = True
			try:
				doc.insert()
				changed += 1
				if created is not None:
					created.append(doc.name)
			except frappe.DuplicateEntryError:
				pass            # another run made it a moment ago
			continue
		if row.status == "Confirmed":
			continue
		if row.status == "Cleared" and not allow_create:
			# Decision D-5: HR opening the page clears records; it never brings one
			# back. A finding that fires again is re-opened by the morning run.
			continue
		counts_differ = any(flt(row.get(k), 2) != flt(f[k], 2) for k in COUNT_FIELDS)
		if row.status == "Cleared" or counts_differ:
			doc = frappe.get_doc(DOCTYPE, name)
			doc.update({k: f[k] for k in COUNT_FIELDS})
			doc.status = "Open"
			doc.flags.via_rule_check = True
			doc.save(ignore_version=False)
			changed += 1

	for name, row in existing.items():
		if name not in findings and row.status == "Open":
			doc = frappe.get_doc(DOCTYPE, name)
			doc.status = "Cleared"
			doc.flags.via_rule_check = True
			doc.save(ignore_version=False)
			changed += 1
	return changed


# ── Telling HR a finding is new (ALV-440) ────────────────────────────────────

# How many findings a mail spells out before it says "and N more". The first
# morning after this ships, every day of a long-running outage becomes a new
# finding at once - at DTC that is ten Pitampura days plus whatever else - and a
# mail with fifty bullet points is not read any more carefully than no mail.
MAX_IN_MAIL = 12

NOTIFY_FIELDS = ("item_type", "rule", "company", "alvoraa_branch", "check_date",
                 "expected_count", "absent_count", "checked_in_count", "people_count",
                 "affected_count")


def _weekday_date(day):
	"""'Fri 13 Nov'. The weekday is named because the feed rule judges by weekday.

	Built by hand rather than with formatdate, which needs frappe.local.lang: a
	date that raised in here would swallow the whole mail in the guard below.
	"""
	d = getdate(day)
	return "{0} {1} {2}".format(d.strftime("%a"), d.day, d.strftime("%b"))


def _line(r):
	"""One plain sentence for one finding. Counts, dates and place names only."""
	from frappe import _

	where = r.get("alvoraa_branch") or r.get("company")
	if r.rule == "D20":
		return _("{0}, {1}: {2} people punched. This branch normally has about {3} "
		         "on a {4}.").format(where, _weekday_date(r.check_date),
		                             cint(r.checked_in_count), cint(r.people_count),
		                             getdate(r.check_date).strftime("%A"))
	if r.rule == "D5":
		return _("{0}, {1}: {2} of the {3} people expected are marked absent, and {4} "
		         "punched.").format(where, _weekday_date(r.check_date), cint(r.absent_count),
		                            cint(r.expected_count), cint(r.checked_in_count))
	if r.rule == "D6":
		return _("{0}: only {1} leave requests have been entered this leave year.").format(
			where, cint(r.affected_count))
	if r.rule == "D18-1":
		return _("{0}: {1} people are marked as left with no leaving date.").format(
			where, cint(r.affected_count))
	return _("{0}: nobody has a leaving date in the last 12 months.").format(where)


def _hr_managers():
	"""Enabled HR Managers with an email address. A handful per tenant, not headcount."""
	out = []
	for user in frappe.get_all("Has Role", filters={"role": "HR Manager", "parenttype": "User"},
	                           pluck="parent", distinct=True):
		if user in ("Administrator", "Guest"):
			continue
		row = frappe.db.get_value("User", user, ["email", "enabled"], as_dict=True)
		if row and row.enabled and row.email:
			out.append((user, row.email))
	return sorted(set(out))


def tell_hr_about(names):
	"""Mail every HR Manager the findings that are NEW this morning (ALV-440).

	Three rules, each with a test:

	  * **Only what is new.** A mail that arrives every morning whether or not
	    anything happened is filtered within a week, and then the one that
	    mattered is filtered too. A finding whose counts merely changed is not
	    re-sent, and there is no daily "all clear".
	  * **Only what that person may read.** Each HR Manager gets the findings
	    Frappe's own permission check lets them read, so a branch HR person is
	    never told another branch's counts (SEC-7). Somebody with nothing
	    readable is not mailed at all.
	  * **Nothing about a person.** Counts, dates, company and branch names.
	    Never an employee, a name or a device (SEC-13, AC-36) - the same rule the
	    findings themselves follow.

	Never raises. It runs after the findings are committed, and a mail that
	cannot be queued must not undo them.
	"""
	from frappe import _
	from frappe.permissions import has_permission

	try:
		rows = frappe.get_all(DOCTYPE, filters={"name": ["in", list(names)]},
		                      fields=["name", *NOTIFY_FIELDS], limit_page_length=0)
		if not rows:
			return
		for user, email in _hr_managers():
			mine = [r for r in rows
			        if has_permission(DOCTYPE, "read", doc=r.name, user=user, print_logs=False)]
			if not mine:
				continue
			mine.sort(key=lambda r: (r.rule, str(r.get("alvoraa_branch") or ""),
			                         str(r.get("check_date") or "")))
			feed_here = [r for r in mine if r.rule == "D20"]
			if feed_here:
				# The punch feed leads the subject wherever it appears: of
				# everything here it is the one that is still going wrong now.
				places = sorted({r.get("alvoraa_branch") or r.company for r in feed_here})
				subject = _("{0} may have stopped sending punches").format(", ".join(places[:3]))
			elif len(mine) == 1:
				subject = _("1 new thing to check in Data to review")
			else:
				subject = _("{0} new things to check in Data to review").format(len(mine))
			shown, extra = mine[:MAX_IN_MAIL], max(0, len(mine) - MAX_IN_MAIL)
			body = "<p>" + _("Alvora's morning check found this. Open <b>Data to review</b> "
			                 "in the portal to see it in full.") + "</p><ul>" + "".join(
				"<li>" + frappe.utils.escape_html(_line(r)) + "</li>" for r in shown) + "</ul>"
			if extra:
				body += "<p>" + _("And {0} more in Data to review.").format(extra) + "</p>"
			if feed_here:
				body += "<p>" + _("A branch that sends far fewer punches than usual is "
				                  "normally a device that has stopped, not people staying "
				                  "away. Until it is fixed, those days are marked absent "
				                  "and will reach pay.") + "</p>"
			_queue(email, subject, body, mine[0].name)
	except Exception as exc:
		# Type only. A traceback's local values hold counts, and could hold a
		# branch name for a scope this log is read outside (OPS-50, OPS-57).
		try:
			frappe.log_error(title="Data to review alert failed",
			                 message=json.dumps({"error": type(exc).__name__,
			                                     "findings": len(list(names))}))
		except Exception:
			pass


def _queue(email, subject, body, name):
	"""One Notification Log row - the desk bell, and an email where that person
	has email on in their own notification settings."""
	frappe.enqueue(
		"frappe.desk.doctype.notification_log.notification_log.make_notification_logs",
		queue="short",
		doc={"type": "Alert", "subject": subject, "email_content": body,
		     "document_type": DOCTYPE, "document_name": name,
		     "from_user": frappe.session.user},
		users=[email],
		now=frappe.in_test,
		enqueue_after_commit=not frappe.in_test,
	)


# ── Data to review: HR's page (US-4, US-6, SEC-7, SEC-13) ────────────────────

HR_ROLES = frozenset({"HR Manager", "HR User"})
MAX_CONFIRM_ITEMS = 40
CONFIRMS_PER_HOUR = 30     # per user (OPS-40); Frappe's own limiter counts per IP address
# The read half of OPS-40. Opening the page re-checks leave and leavers and saves
# what changed, so it is a write as well as a read - it must not be callable in a
# loop. Generous on purpose: normal use is a handful of opens an hour.
READS_PER_HOUR = 120
STALE_HOURS = 26

ACTIONS = {
	# action -> (what the record says afterwards, the kinds of record it may confirm)
	"absence_real": ("Absence was real", {("Doubtful day", "D5")}),
	# D-2: of the leavers rules, only "nobody left in a year" can be right as it stands.
	"figure_right": ("Figure is right", {("Leave used", "D6"), ("Leavers", "D18-2")}),
}


def _require_hr(endpoint):
	from frappe import _

	from hrms.alvoraa_hr_core.access import refuse

	user = frappe.session.user
	if user == "Guest" or (user != "Administrator" and not HR_ROLES & set(frappe.get_roles())):
		refuse(_("Only HR can open Data to review."), "SEC-7", endpoint)
	try:
		frappe.local.response_headers.set("Cache-Control", "no-store")
	except Exception:
		pass


def _within_hourly_limit(endpoint, per_hour):
	"""A per-user counter in Frappe's cache, for one hour. Cache trouble never blocks HR."""
	from frappe import _

	bucket = now_datetime().strftime("%Y%m%d%H")
	try:
		key = frappe.cache.make_key(f"alvoraa:limit:{endpoint}:{frappe.session.user}:{bucket}")
		used = frappe.cache.incr(key)
		if used == 1:
			frappe.cache.expire(key, 3600)
	except Exception:
		return
	if used > per_hour:
		frappe.throw(_("Too many requests. Wait a minute and try again."),
		             frappe.exceptions.TooManyRequestsError)


def recheck(scope, as_of=None):
	"""OPS-49: re-run the leave and leavers rules for the caller's scope, and save what changed.

	Clears and updates records; never creates one (D-5) - new findings appear at
	06:30. Location HR re-checks only their branches' leavers. Saves go through
	the caller's own permissions.
	"""
	as_of = getdate(as_of or today())
	rules = DAILY_RULES if scope.branches is None else ("D18-1",)
	for company in scope.companies:
		existing = existing_items(company, as_of, rules=rules, branches=scope.branches)
		findings = company_findings(company, 0, as_of, rules=rules, branches=scope.branches,
		                            also_days=_open_day_rule_days(existing))
		apply_findings(existing, findings, allow_create=False)


def _figures_for_confirming(scope):
	"""The month's attendance without Open doubtful days, and what each one would add back.

	Three queries, however many records there are.
	"""
	from alvoraa_portal import org_figures as of

	period = of.period(scope)
	if not period:
		return None, dict(of.NO_ATTENDANCE), {}
	# Only the percentage is shown here, so the same cheap read as HR Analytics.
	return (period, of.attendance_figures(scope, *period, detail=False),
	        of.open_doubtful_counts(scope, *period))


@frappe.whitelist(methods=["POST"])
@requires_feature("analytics")
def data_review_items():
	"""Figures in the caller's scope that leaders see as "Needs review" or left out.

	Counts, dates, company and branch names only - never an employee (AC-36).
	"""
	import time

	from alvoraa_portal import org_figures as of

	started = time.monotonic()
	_require_hr("data_review.data_review_items")
	_within_hourly_limit("data_review.data_review_items", READS_PER_HOUR)
	scope = of.hr_scope()
	if scope.not_linked:
		return {"not_linked": True}

	try:
		recheck(scope)
	except Exception as e:
		# The re-check only clears records; if it fails, HR still gets the list as
		# the morning left it. Error type only, as for the job.
		frappe.log_error(title="Data to review re-check failed",
		                 message=json.dumps({"stage": "page re-check", "error": type(e).__name__}))

	rows = frappe.get_list(
		DOCTYPE, filters=item_filters(scope, status="Open"),
		fields=["name", "item_type", "rule", "company", "alvoraa_branch", "check_date", "first_found_on",
		        *COUNT_FIELDS],
		order_by="check_date asc", limit_page_length=MAX_ITEMS)

	period, base, left_out = _figures_for_confirming(scope)
	leave = of.leave_figures(scope) if any(r.rule == "D6" for r in rows) else {"by_company": {}}
	whole_company = scope.branches is None

	cards = []
	# Doubtful days: one card per company and set of dates, naming the branches.
	by_branch = {}
	for r in rows:
		if r.rule == "D5":
			by_branch.setdefault((r.company, r.alvoraa_branch), []).append(r)
	by_dates = {}
	for (company, branch), items in sorted(by_branch.items()):
		dates = tuple(str(i.check_date) for i in items)
		by_dates.setdefault((company, dates), []).append((branch, items))
	for (company, dates), groups in by_dates.items():
		items = [i for _branch, group in groups for i in group]
		absent = [100.0 * i.absent_count / i.expected_count for i in items if i.expected_count]
		checked = [100.0 * i.checked_in_count / i.expected_count for i in items if i.expected_count]
		cards.append({
			"kind": "doubtful", "company": company, "branches": [b for b, _group in groups],
			"dates": list(dates), "items": [i.name for i in items],
			"absent_pct": [flt(min(absent), 0), flt(max(absent), 0)] if absent else None,
			"checked_in_pct": flt(max(checked), 0) if checked else None,
			"found_on": str(min(i.first_found_on for i in items)),
			"figure_without": base["rate"],
			"figure_with": of.rate_with(base, [left_out[i.name] for i in items if i.name in left_out]),
			"can_confirm": True,
		})
	# ALV-440: one card per branch whose feed looks dead, naming its days.
	by_feed = {}
	for r in rows:
		if r.rule == "D20":
			by_feed.setdefault((r.company, r.alvoraa_branch), []).append(r)
	for (company, branch), items in sorted(by_feed.items()):
		items.sort(key=lambda i: i.check_date)
		cards.append({
			"kind": "feed", "company": company, "branch": branch,
			"dates": [str(i.check_date) for i in items], "items": [i.name for i in items],
			"punched": max(cint(i.checked_in_count) for i in items),
			"normal": max(cint(i.people_count) for i in items),
			"expected": max(cint(i.expected_count) for i in items),
			"found_on": str(min(i.first_found_on for i in items)),
			"can_confirm": False,
		})

	for r in rows:
		if r.rule == "D6":
			cards.append({
				"kind": "leave", "company": r.company, "items": [r.name],
				"requests": r.affected_count, "people": r.people_count, "days_allocated": r.days_allocated,
				"used_pct": (leave["by_company"].get(r.company) or {}).get("used_pct"),
				"found_on": str(r.first_found_on), "can_confirm": whole_company,
			})
		elif r.rule in ("D18-1", "D18-2"):
			cards.append({
				"kind": "leavers", "rule": r.rule, "company": r.company, "branch": r.alvoraa_branch,
				"items": [r.name], "people": r.affected_count, "found_on": str(r.first_found_on),
				"can_confirm": r.rule == "D18-2" and whole_company,
			})

	last = frappe.db.get_single_value(SETTINGS, "last_checks_run_on", cache=False)
	stale = not last or (now_datetime() - frappe.utils.get_datetime(last)).total_seconds() > STALE_HOURS * 3600
	of.log_if_slow("data_review_items", scope, started)
	return {
		"not_linked": False,
		"scope": scope.kind,
		"whole_company": whole_company,
		"open_count": len(rows),
		"last_checked": str(last) if last else None,
		"stale": bool(stale),
		"period": {"from": str(period[0]), "to": str(period[1])} if period else None,
		"cards": cards,
	}


@frappe.whitelist(methods=["POST"])
@requires_feature("analytics")
def data_review_confirm(items=None, action=None):
	"""HR confirms that an absence was real, or that a figure is right (US-4, SEC-13).

	All or nothing: every record must be Open, in the caller's scope, writable by
	them and of the kind the action is for - otherwise nothing is saved. Rows are
	locked while they are checked, so two HR people confirming at once cannot both
	succeed. Each saved record keeps who, when, and the figure before and after.
	"""
	import time

	from frappe import _

	from alvoraa_portal import org_figures as of
	from hrms.alvoraa_hr_core.access import refuse

	endpoint = "data_review.data_review_confirm"
	started = time.monotonic()
	_require_hr(endpoint)

	if isinstance(items, str):
		items = frappe.parse_json(items) if items.strip().startswith("[") else [items]
	if (not isinstance(items, list) or not items or len(items) > MAX_CONFIRM_ITEMS
	        or not all(isinstance(i, str) and i for i in items) or action not in ACTIONS):
		frappe.throw(_("Choose what you are confirming, then try again."))
	_within_hourly_limit(endpoint, CONFIRMS_PER_HOUR)

	scope = of.hr_scope()

	def refused():
		# One message whether the record is missing, someone else's or the wrong
		# kind: the answer must not reveal what exists outside the caller's scope.
		refuse(_("You cannot confirm this item. It may belong to another branch or company."),
		       "SEC-13", endpoint, DOCTYPE)

	if scope.not_linked:
		refused()

	confirmation, kinds = ACTIONS[action]
	docs = []
	for name in sorted(set(items)):       # one lock order, so two requests cannot deadlock
		if not frappe.db.exists(DOCTYPE, name):
			refused()
		doc = frappe.get_doc(DOCTYPE, name, for_update=True)
		if doc.company not in scope.companies:
			refused()
		if scope.branches is not None and doc.alvoraa_branch not in scope.branches:
			# Location HR: their branches only, and never a company-wide record.
			refused()
		if not frappe.has_permission(DOCTYPE, "write", doc=doc):
			refused()
		if (doc.item_type, doc.rule) not in kinds:
			refused()
		if doc.status != "Open":
			frappe.throw(_("This has already been confirmed, or the data was fixed. "
			               "Open Data to review again to see what is left."))
		docs.append(doc)

	figures = {}
	if action == "absence_real":
		_period, base, left_out = _figures_for_confirming(scope)
		with_all = of.rate_with(base, [left_out[d.name] for d in docs if d.name in left_out])
		figures = {d.name: (base["rate"], with_all) for d in docs}
	elif any(d.rule == "D6" for d in docs):
		by_company = of.leave_figures(scope)["by_company"]
		figures = {d.name: (None, (by_company.get(d.company) or {}).get("used_pct"))
		           for d in docs if d.rule == "D6"}

	now = now_datetime()
	for doc in docs:
		without, with_ = figures.get(doc.name, (None, None))
		doc.update({"status": "Confirmed", "confirmation": confirmation,
		            "confirmed_by": frappe.session.user, "confirmed_on": now,
		            "figure_without": without, "figure_with": with_})
		doc.flags.via_confirm = True
		doc.save(ignore_version=False)

	of.log_if_slow("data_review_confirm", scope, started, items=len(docs))
	return {"ok": True, "confirmed": len(docs)}
