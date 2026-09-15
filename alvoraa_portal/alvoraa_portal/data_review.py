"""Data to review: figures whose data looks wrong, found every morning (slice 012).

Push 1 of the leadership view. Three things live here:

  indexes           the eight indexes every scoped figure filters on
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

DOCTYPE = "Alvoraa Data Review Item"
SETTINGS = "Alvoraa Leader View Settings"

JOB_METHOD = "alvoraa_portal.data_review.run_morning_checks"
JOB_ID = "leader-data-checks"
FAILED_TITLE = "Leader data checks failed"

WINDOW_DAYS = 35           # how far back doubtful days are looked for
ABSENT_PCT = 95            # a day is doubtful at 95% or more marked absent...
CHECKED_IN_PCT = 5         # ...and fewer than 5% checked in
LEAVE_MONTHS_IN = 3        # leave used is judged from three months into the leave year
LEAVE_USED_PCT = 1         # below 1% of leave allocated looks unrecorded
DAILY_RULES = ("D6", "D18-1", "D18-2")

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
	("Attendance", ("alvoraa_branch", "attendance_date")),
)


def add_indexes():
	"""Create the eight indexes. Safe to run again: it changes nothing then."""
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
	for company in companies or frappe.get_all("Company", pluck="name", order_by="name asc"):
		stage = {"now": "start"}
		try:
			findings = company_findings(company, minimum, as_of, stage=stage)
			stage["now"] = "save"
			apply_findings(existing_items(company, as_of), findings, allow_create=True)
			frappe.db.commit()
		except Exception as e:
			frappe.db.rollback()
			failed = True
			_log_failure(company, stage["now"], e)

	if not failed:
		frappe.db.set_single_value(SETTINGS, "last_checks_run_on", now_datetime())
		frappe.db.commit()


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


def company_findings(company, minimum, as_of, rules=("D5",) + DAILY_RULES, branches=None, stage=None):
	"""{record name: finding} for the rules asked, for one company. Grouped queries only.

	`branches` limits D18-1 to those branches (location HR's page re-check).
	"""
	from alvoraa_portal import org_figures as of

	stage = stage if stage is not None else {}
	out = {}
	# A company with no attendance yet has "no figures", not figures to review (AC-30).
	if not frappe.db.sql("select 1 from `tabAttendance` where company = %s and docstatus = 1 limit 1",
	                     company):
		return out

	if "D5" in rules:
		stage["now"] = "doubtful days"
		out.update(_doubtful_days(company, minimum, as_of))

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


def _doubtful_days(company, minimum, as_of):
	"""D5 for every named branch and day in the window. Three queries for the company.

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
	if not days:
		return {}

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
		expected, absent = cint(d.expected), cint(d.absent)
		n = checked.get((d.branch, getdate(d.day)), 0)
		if any_checkins and n * 100 >= expected * CHECKED_IN_PCT:
			continue
		f = _finding("D5", "Doubtful day", company, d.branch, d.day,
		             expected_count=expected, absent_count=absent, checked_in_count=n)
		out[f["name"]] = f
	return out


def existing_items(company, as_of, rules=("D5",) + DAILY_RULES, branches=None):
	"""The records these rules are responsible for: doubtful days inside the window,
	and every leave and leavers record of the company."""
	fields = ["name", "status", "rule", *COUNT_FIELDS]
	out = {}
	base = {"company": company}
	if branches is not None:
		base["alvoraa_branch"] = ["in", list(branches) or [""]]
	if "D5" in rules:
		for r in frappe.get_all(DOCTYPE, filters={**base, "rule": "D5",
		                                          "check_date": [">=", add_days(as_of, -WINDOW_DAYS)]},
		                        fields=fields, limit_page_length=0):
			out[r.name] = r
	daily = [r for r in rules if r in DAILY_RULES]
	if daily:
		for r in frappe.get_all(DOCTYPE, filters={**base, "rule": ["in", daily]}, fields=fields,
		                        limit_page_length=0):
			out[r.name] = r
	return out


def apply_findings(existing, findings, allow_create):
	"""Write only the differences. Returns how many records changed.

	`allow_create` is False on HR's page re-check: creating a record there would
	need rights HR does not have, so new findings wait for the morning (D-5).
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
			except frappe.DuplicateEntryError:
				pass            # another run made it a moment ago
			continue
		if row.status == "Confirmed":
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
