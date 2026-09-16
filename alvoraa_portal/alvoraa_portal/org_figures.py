"""One calculation for attendance, leave and people figures (slice 012, US-2).

HR Analytics uses it now; the leader view uses it in push 2. Two screens that
count the same thing two ways end in an argument about whose number is right,
so there is one definition, here:

  attendance %   (Present + Work From Home + half of Half Day)
                 / (Present + Work From Home + Half Day + Absent)
                 Submitted records only. On Leave is in neither part. Rows on a
                 branch's Open doubtful days are left out.
  late           Present, Work From Home or Half Day rows marked late
  short day      Present or Work From Home row where (shift length - tolerance)
                 is more than the hours worked. No shift, never short.
  leave used %   approved, submitted leave starting in the company's leave year
                 / leave allocated for periods overlapping that leave year
  headcount      Active employees who have joined by the day asked about

Figures are counts from grouped SQL, never loaded row by row. Nothing here
returns a name, an employee id or a leave type.

Scope values reach the database only as query parameters. Column and table names
in the SQL are constants in this file; no argument a caller sends picks one.
"""

from collections import namedtuple

import frappe
from frappe.utils import add_days, add_years, cint, flt, get_first_day, getdate, today

# PRIV-13. These totals are for operational oversight. They must never become an
# input to a rating, a KPI, pay or a disciplinary record - that is a different
# purpose and needs its own review. Appraisal attendance scores keep their own
# formula in hrms/alvoraa_hr_core/attendance_score.py on purpose.
PURPOSE = "operational-oversight-only"

# Changes when a definition above changes, so a cached answer from the old
# formula can never be served (push 2's cache key carries it).
FORMULA_VERSION = 1

COUNTED = ("Present", "Work From Home", "Half Day", "Absent")


class Scope(namedtuple("Scope", ["companies", "branches"])):
	"""Companies, and optionally the only branches inside them.

	`branches` None means every branch of those companies. A branch is always
	matched together with its company: one Branch record can be used by two
	companies, because ERPNext's Branch has no company.
	"""

	@property
	def not_linked(self):
		return not self.companies

	@property
	def kind(self):
		return "branch" if self.branches is not None else "company"


def hr_scope(user=None):
	"""What an HR user's figures cover. Fails closed.

	Companies from `permitted_companies` (their Company permissions, else their
	own Employee's company, else nothing). Narrowed to their Branch permissions
	when they have any that apply to Employee - location HR. Employees with no
	branch are then outside their scope (decision D-8).
	"""
	from frappe.core.doctype.user_permission.user_permission import get_user_permissions

	from hrms.alvoraa_hr_core.access import permitted_companies

	user = user or frappe.session.user
	companies = tuple(permitted_companies(user))
	if not companies:
		return Scope((), None)
	branches = sorted({
		p.get("doc") for p in get_user_permissions(user).get("Branch", [])
		if p.get("doc") and p.get("applicable_for") in (None, "", "Employee")
	})
	return Scope(companies, tuple(branches) if branches else None)


def condition(scope, alias, branch_field):
	"""(SQL, params) limiting `alias` to the scope. alias and field are constants.

	One value is written as `=`, not `in (one value)`. MariaDB only uses the first
	column of a two-column index for an `IN` list, so `company in (x)` with a date
	range read every one of that company's rows; `company = x` uses both columns.
	Measured at 1,000 people: the month's attendance query went from 292 ms to 29 ms.
	"""
	companies = list(scope.companies) or [""]
	if len(companies) == 1:
		sql = f"{alias}.company = %(scope_company)s"
		params = {"scope_company": companies[0]}
	else:
		sql = f"{alias}.company in %(scope_companies)s"
		params = {"scope_companies": companies}
	if scope.branches is not None:
		branches = list(scope.branches) or [""]
		if len(branches) == 1:
			sql += f" and {alias}.{branch_field} = %(scope_branch)s"
			params["scope_branch"] = branches[0]
		else:
			sql += f" and {alias}.{branch_field} in %(scope_branches)s"
			params["scope_branches"] = branches
	return sql, params


def employee_condition(scope, alias="e"):
	return condition(scope, alias, "branch")


# ── attendance ───────────────────────────────────────────────────────────────

_OPEN_DOUBTFUL = """
	select 1 from `tabAlvoraa Data Review Item` r
	where r.item_type = 'Doubtful day' and r.status = 'Open'
	  and r.company = a.company and r.alvoraa_branch = a.alvoraa_branch
	  and r.check_date = a.attendance_date
"""


def _tolerance():
	from alvoraa_portal.attendance_analytics import DEFAULT_TOLERANCE_MINS, TOLERANCE_KEY

	return cint(frappe.db.get_default(TOLERANCE_KEY) or DEFAULT_TOLERANCE_MINS)


def rate(counts):
	"""Attendance % from counts, one decimal. None when nobody was expected."""
	present = flt(counts.get("present")) + flt(counts.get("wfh"))
	half = flt(counts.get("half"))
	expected = present + half + flt(counts.get("absent"))
	if not expected:
		return None
	return flt((present + half / 2.0) / expected * 100.0, 1)


NO_ATTENDANCE = {"present": 0, "wfh": 0, "half": 0, "absent": 0, "on_leave": 0,
                 "late": 0, "short": 0, "people": 0, "rate": None}


def attendance_figures(scope, start, end, detail=True):
	"""Attendance counts and % for the scope and dates. One query.

	Open doubtful days of each branch are left out; a Confirmed one ("the absence
	was real") counts again.

	`detail` False leaves out late arrivals, short days and the number of people
	inside the figure - and with them the join to Employee and Shift Type and the
	distinct count. HR Analytics shows none of the three, and at 1,000 people they
	were most of the query: measured 158 ms with them and 23 ms without, over a
	month of a whole company. The leader view asks for them (it needs the people
	count for the small-group rule), so the default keeps them.
	"""
	empty = dict(NO_ATTENDANCE)
	if scope.not_linked:
		return empty
	where, params = condition(scope, "a", "alvoraa_branch")
	params.update({"start": getdate(start), "end": getdate(end), "tolerance": _tolerance()})
	extra, joins = "", ""
	if detail:
		extra = """
			, coalesce(sum(a.late_entry = 1
				and a.status in ('Present', 'Work From Home', 'Half Day')), 0) as late
			, coalesce(sum(a.status in ('Present', 'Work From Home')
				and st.start_time is not null and st.end_time is not null
				and ((time_to_sec(st.end_time) - time_to_sec(st.start_time)
				      + case when st.end_time <= st.start_time then 86400 else 0 end) / 60
				     - %(tolerance)s) - coalesce(a.working_hours, 0) * 60 > 0), 0) as short
			, count(distinct case when a.status in %(counted)s then a.employee end) as people
		"""
		joins = """
			left join `tabEmployee` e on e.name = a.employee
			left join `tabShift Type` st on st.name = coalesce(nullif(a.shift, ''), e.default_shift)
		"""
	row = frappe.db.sql(f"""
		select
			coalesce(sum(a.status = 'Present'), 0) as present,
			coalesce(sum(a.status = 'Work From Home'), 0) as wfh,
			coalesce(sum(a.status = 'Half Day'), 0) as half,
			coalesce(sum(a.status = 'Absent'), 0) as absent,
			coalesce(sum(a.status = 'On Leave'), 0) as on_leave
			{extra}
		from `tabAttendance` a
		{joins}
		where a.docstatus = 1
		  and a.attendance_date between %(start)s and %(end)s
		  and {where}
		  and not exists ({_OPEN_DOUBTFUL})
	""", {**params, "counted": list(COUNTED)}, as_dict=True)[0]
	# Whatever was not asked for stays zero, as it is for a scope with no rows.
	out = {k: cint(row.get(k)) for k in empty if k != "rate"}
	out["rate"] = rate(out)
	return out


def open_doubtful_counts(scope, start, end):
	"""Per Open doubtful-day record in scope: the attendance rows left out. One query.

	Lets a screen say what the figure would be with some of those days counted,
	without a query per day or per branch.
	"""
	if scope.not_linked:
		return {}
	where, params = condition(scope, "a", "alvoraa_branch")
	params.update({"start": getdate(start), "end": getdate(end)})
	rows = frappe.db.sql(f"""
		select r.name,
			coalesce(sum(a.status = 'Present'), 0) as present,
			coalesce(sum(a.status = 'Work From Home'), 0) as wfh,
			coalesce(sum(a.status = 'Half Day'), 0) as half,
			coalesce(sum(a.status = 'Absent'), 0) as absent
		from `tabAttendance` a
		join `tabAlvoraa Data Review Item` r
		  on r.item_type = 'Doubtful day' and r.status = 'Open'
		 and r.company = a.company and r.alvoraa_branch = a.alvoraa_branch
		 and r.check_date = a.attendance_date
		where a.docstatus = 1
		  and a.attendance_date between %(start)s and %(end)s
		  and {where}
		group by r.name
	""", params, as_dict=True)
	return {r.name: {k: cint(r[k]) for k in ("present", "wfh", "half", "absent")} for r in rows}


def rate_with(base, extra_counts):
	"""Attendance % once some left-out days are counted again."""
	total = {k: cint(base.get(k)) for k in ("present", "wfh", "half", "absent")}
	for counts in extra_counts:
		for k in total:
			total[k] += cint(counts.get(k))
	return rate(total)


def data_up_to(scope):
	"""The last day with submitted attendance in scope, or None.

	One query per company, reading the newest row through the index and stopping
	there. MAX() over the same rows does not: on a tenant with one company every
	Attendance row is that company's, so the optimiser reads the whole table
	(measured: 267,724 rows at 1,000 people, on every HR Analytics and Data to
	review open). Companies in scope are one or two, never a crowd.
	"""
	if scope.not_linked:
		return None
	days = []
	for company in scope.companies:
		single = Scope((company,), scope.branches)
		where, params = condition(single, "a", "alvoraa_branch")
		value = frappe.db.sql(
			f"""select a.attendance_date from `tabAttendance` a
			    where a.docstatus = 1 and {where}
			    order by a.attendance_date desc limit 1""", params)
		if value and value[0][0]:
			days.append(getdate(value[0][0]))
	return max(days) if days else None


def period(scope):
	"""The month of "data up to", from day 1 to that day (decision D-13). None with no data."""
	up_to = data_up_to(scope)
	if not up_to:
		return None
	return get_first_day(up_to), up_to


# ── leave ────────────────────────────────────────────────────────────────────

def leave_year(company, as_of=None):
	"""(first day, last day) of the company's leave year containing `as_of`."""
	from alvoraa_portal.hr_api import _leave_year_start

	start = getdate(_leave_year_start(as_of or today(), company))
	return start, add_days(add_years(start, 1), -1)


def leave_figures(scope, as_of=None):
	"""Leave used this leave year, per company and added up. Two queries in all.

	Each company's own leave year: two companies can have different fiscal years.
	Allocations count when their period overlaps the leave year; leave counts in
	the year its first day falls in.
	"""
	as_of = getdate(as_of or today())
	out = {"by_company": {}, "allocated": 0.0, "taken": 0.0, "requests": 0, "people": 0,
	       "used_pct": None}
	if scope.not_linked:
		return out

	years = {c: leave_year(c, as_of) for c in scope.companies}
	alloc_or, apply_or, params = [], [], {}
	for i, (company, (ys, ye)) in enumerate(sorted(years.items())):
		params.update({f"c{i}": company, f"ys{i}": ys, f"ye{i}": ye})
		alloc_or.append(f"(x.company = %(c{i})s and x.from_date <= %(ye{i})s and x.to_date >= %(ys{i})s)")
		apply_or.append(f"(x.company = %(c{i})s and x.from_date between %(ys{i})s and %(ye{i})s)")
	branch = ""
	if scope.branches is not None:
		branch = " and x.alvoraa_branch in %(scope_branches)s"
		params["scope_branches"] = list(scope.branches) or [""]

	allocations = frappe.db.sql(f"""
		select x.company, coalesce(sum(x.total_leaves_allocated), 0) as allocated,
		       count(distinct x.employee) as people
		from `tabLeave Allocation` x
		where x.docstatus = 1 and ({' or '.join(alloc_or)}){branch}
		group by x.company
	""", params, as_dict=True)
	applications = frappe.db.sql(f"""
		select x.company,
		       coalesce(sum(case when x.docstatus = 1 and x.status = 'Approved'
		                         then x.total_leave_days end), 0) as taken,
		       count(*) as requests
		from `tabLeave Application` x
		where x.docstatus < 2 and ({' or '.join(apply_or)}){branch}
		group by x.company
	""", params, as_dict=True)

	alloc = {r.company: r for r in allocations}
	apps = {r.company: r for r in applications}
	for company, (ys, ye) in years.items():
		a, p = alloc.get(company) or {}, apps.get(company) or {}
		allocated, taken = flt(a.get("allocated")), flt(p.get("taken"))
		out["by_company"][company] = {
			"year_start": ys, "year_end": ye, "allocated": allocated, "taken": taken,
			"requests": cint(p.get("requests")), "people": cint(a.get("people")),
			"used_pct": flt(taken / allocated * 100.0, 1) if allocated else None,
		}
		out["allocated"] += allocated
		out["taken"] += taken
		out["requests"] += cint(p.get("requests"))
		out["people"] += cint(a.get("people"))
	if out["allocated"]:
		out["used_pct"] = flt(out["taken"] / out["allocated"] * 100.0, 1)
	return out


# ── observability ────────────────────────────────────────────────────────────

SLOW_SECONDS = 1.0


def log_if_slow(endpoint, scope, started, **extra):
	"""One line when a call takes more than a second (OPS-56).

	Endpoint, scope kind, how many branches, duration. Never a figure, a name,
	a company or a branch name (OPS-57).
	"""
	import json
	import time

	elapsed = time.monotonic() - started
	if elapsed <= SLOW_SECONDS:
		return
	try:
		frappe.logger("leader_view").info(json.dumps({
			"event": "slow_call", "endpoint": endpoint, "scope": scope.kind,
			"branches": len(scope.branches) if scope.branches is not None else None,
			"duration_ms": int(elapsed * 1000),
			**{k: v for k, v in extra.items() if isinstance(v, int | float | bool)},
		}))
	except Exception:
		pass


# ── people ───────────────────────────────────────────────────────────────────

def people_figures(scope, as_of=None, joined_from=None, joined_to=None):
	"""Headcount, all records, and joiners between two dates. One query."""
	as_of = getdate(as_of or today())
	joined_from = getdate(joined_from or get_first_day(as_of))
	joined_to = getdate(joined_to or as_of)
	if scope.not_linked:
		return {"active": 0, "total": 0, "joiners": 0}
	where, params = employee_condition(scope)
	params.update({"as_of": as_of, "jf": joined_from, "jt": joined_to})
	row = frappe.db.sql(f"""
		select coalesce(sum(e.status = 'Active' and e.date_of_joining <= %(as_of)s), 0) as active,
		       count(*) as total,
		       coalesce(sum(e.date_of_joining between %(jf)s and %(jt)s), 0) as joiners
		from `tabEmployee` e
		where {where}
	""", params, as_dict=True)[0]
	return {k: cint(row.get(k)) for k in ("active", "total", "joiners")}
