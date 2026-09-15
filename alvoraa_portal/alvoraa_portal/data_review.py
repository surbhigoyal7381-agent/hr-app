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
from alvoraa_portal.subscription import requires_feature

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


# ── Data to review: HR's page (US-4, US-6, SEC-7, SEC-13) ────────────────────

HR_ROLES = frozenset({"HR Manager", "HR User"})
MAX_CONFIRM_ITEMS = 40
CONFIRMS_PER_HOUR = 30     # per user (OPS-40); Frappe's own limiter counts per IP address
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
		findings = company_findings(company, 0, as_of, rules=rules, branches=scope.branches)
		existing = existing_items(company, as_of, rules=rules, branches=scope.branches)
		apply_findings(existing, findings, allow_create=False)


def _figures_for_confirming(scope):
	"""The month's attendance without Open doubtful days, and what each one would add back.

	Three queries, however many records there are.
	"""
	from alvoraa_portal import org_figures as of

	period = of.period(scope)
	if not period:
		return None, dict(of.NO_ATTENDANCE), {}
	return period, of.attendance_figures(scope, *period), of.open_doubtful_counts(scope, *period)


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
	scope = of.hr_scope()
	if scope.not_linked:
		return {"not_linked": True}

	recheck(scope)

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
