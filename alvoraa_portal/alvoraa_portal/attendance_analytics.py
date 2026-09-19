"""Attendance analytics: who is drifting, and whether it is them or the rota.

Three views over one calculation - your own record, your team, the whole
organisation. The view decides WHO is counted; it never changes what a number
means, so nobody has to learn two vocabularies.

The headline metric is hours shortfall: days somebody did not complete the hours
their shift expected. Two things make it worth showing.

FREQUENCY, NOT OCCURRENCE. On the tenant this was designed against, 370 of 403
people had at least one short day. A list of people who were ever short is a
list of the workforce. Twenty short days is a habit; one is a dentist
appointment. So every figure here is a rate or a repeat count.

A PERSON OR A ROTA. When a whole group runs short on one day of the week, that
is not people choosing to leave early - it is a shift definition or a closing
routine that does not match the roster. Managing individuals cannot fix it and
every conversation about it would be unfair. So the screen says which it is
looking at, in words, before it lists anybody's name.

That tenant turned out NOT to have such a day: 5.8% to 6.6% across every
weekday, which is no pattern at all. An earlier draft of this note claimed
Saturday ran 40% high, from comparing raw counts of short days rather than
rates - and there are simply more Saturdays worked. The screen compares rates
for exactly that reason, and stays silent here, which is the right answer.

Everything is derived on read. A stored count of anything drifts the first time
somebody resigns on a Friday.
"""

import json

import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, flt, getdate, nowdate

# The tolerance before a day counts as short is an ORGANISATION's decision, not
# ours. The same data gives 12.9% of days at no tolerance and 4.4% at an hour;
# a screen that hid that assumption would eventually be used to justify
# something it does not support.
TOLERANCE_KEY = "alvoraa_attendance_short_tolerance_mins"
DEFAULT_TOLERANCE_MINS = 30

# How many minutes after the shift starts before an arrival counts as late is
# the same kind of decision, and it is also the organisation's. It is stored
# the same way as the tolerance above - a Frappe default, read per request -
# so an existing tenant needs no migration to get one.
#
# Three places can answer, and they are tried in this order:
#   1. the Shift Type's own `late_entry_grace_period`, when it is set
#   2. this organisation-wide default
#   3. no grace at all
#
# A Shift Type's grace is an Int, so "not set" and "zero" look identical. A
# zero therefore falls through to the organisation's number. To allow nothing
# anywhere, set the organisation default to 0 and leave the shifts alone.
LATE_GRACE_KEY = "alvoraa_attendance_late_grace_mins"
DEFAULT_LATE_GRACE_MINS = 0

PRESENT = ("Present", "Work From Home")
ORG_ROLES_KEY = "alvoraa_attendance_org_roles"
DEFAULT_ORG_ROLES = "HR Manager,HR User,System Manager"


# ── who is asking, and who they may count ────────────────────────────────────

def _me():
	return frappe.db.get_value("Employee", {"user_id": frappe.session.user, "status": "Active"},
	                           ["name", "employee_name", "department", "branch", "company"],
	                           as_dict=True)


# Slice 012 Q6 (SEC-19): roles the organisation view is never given, whatever the
# stored setting says. Leadership sees totals only - listing it here would show
# every leader named people and leave types, the shortcut the brief refused.
# Employee-level roles would show that to everybody. All, Guest and Desk User are
# roles Frappe gives every user or visitor automatically.
NEVER_ORG_ROLES = frozenset({"Leadership", "Employee", "Employee Self Service",
                             "All", "Guest", "Desk User"})


def _org_roles():
	raw = frappe.db.get_default(ORG_ROLES_KEY) or DEFAULT_ORG_ROLES
	listed = {r.strip() for r in str(raw).split(",") if r.strip()}
	ignored = listed & NEVER_ORG_ROLES
	if ignored:
		# Role names only. Whoever stored them is found in the setting itself.
		try:
			frappe.logger("security").warning(json.dumps(
				{"event": "org_roles_ignored", "rule": "SEC-19", "roles": sorted(ignored)}))
		except Exception:
			pass
	return listed - NEVER_ORG_ROLES


def _may_see_organisation():
	return bool(_org_roles() & set(frappe.get_roles()))


def _reports_to(manager, deep):
	"""Direct reports, or everybody beneath them.

	Both, because a manager wants either at different moments: the team they
	speak to weekly, and the whole line they are accountable for.
	"""
	direct = frappe.get_all("Employee", filters={"reports_to": manager, "status": "Active"},
	                        pluck="name")
	if not deep:
		return direct
	seen, frontier = set(direct), list(direct)
	while frontier:
		nxt = frappe.get_all("Employee",
		                     filters={"reports_to": ("in", frontier), "status": "Active"},
		                     pluck="name")
		frontier = [n for n in nxt if n not in seen]
		seen.update(frontier)
	return sorted(seen)


@frappe.whitelist()
def views():
	"""Which views this person gets, so the page draws only what they have.

	A manager can see that an Organisation view exists and that they do not have
	it, rather than wondering whether the screen is broken.
	"""
	me = _me()
	has_team = bool(me and frappe.db.count("Employee",
	                                       {"reports_to": me.name, "status": "Active"}))
	return {
		"me": me,
		"mine": bool(me),
		"team": has_team,
		"organisation": _may_see_organisation(),
		"tolerance_mins": cint(frappe.db.get_default(TOLERANCE_KEY) or DEFAULT_TOLERANCE_MINS),
	}


def _population(view, depth, people, filters):
	"""The employees a view covers, and a refusal when it is not the caller's.

	Enforced here rather than in the page: the endpoint is whitelisted, and
	anybody who can open the portal can call it with any argument they like.
	"""
	me = _me()

	# Only the two views ABOUT somebody need that somebody to exist. An HR
	# administrator is often not on the payroll, and refusing them the
	# organisation view for want of an employee record would be absurd.
	if view in ("mine", "team") and not me:
		frappe.throw(_("Your user is not linked to an employee record, so there "
		               "is no personal or team view to show."),
		             frappe.PermissionError)

	if view == "mine":
		return [me.name], me

	if view == "team":
		team = _reports_to(me.name, deep=(depth == "all"))
		if not team:
			frappe.throw(_("Nobody reports to you, so there is no team to show."),
			             frappe.PermissionError)
		chosen = _chosen(people)
		if chosen:
			outside = sorted(set(chosen) - set(team))
			if outside:
				# The whole request is refused, not quietly trimmed. A silent
				# subset teaches nobody where the boundary is and hides a
				# permission bug for months.
				frappe.throw(
					_("{0} of the people you asked for are not in your team.")
					.format(len(outside)), frappe.PermissionError)
			return chosen, me
		return team, me

	if view == "organisation":
		if not _may_see_organisation():
			frappe.throw(_("Only HR and system administrators can see the whole "
			               "organisation."), frappe.PermissionError)
		f = {"status": "Active"}
		if me and me.company:
			f["company"] = me.company
		for field in ("department", "branch", "designation"):
			if filters.get(field):
				f[field] = filters[field]
		if filters.get("manager"):
			f["name"] = ("in", _reports_to(filters["manager"], deep=(depth == "all")) or [""])
		# DEF-8 (2026-09-16), the same rule as person() and filter_options: a
		# location HR person sees their own branches, and an employee with no
		# branch is outside them. Frappe's User Permissions are not strict here, so
		# an empty branch passed a Branch permission and this list returned
		# head-office colleagues with their names, days and leave types.
		linked = _linked_branches()
		if linked is not None:
			wanted = filters.get("branch")
			if wanted and wanted not in linked:
				from hrms.alvoraa_hr_core.access import refuse

				refuse(_("You can only see your own branches."), "SEC-17",
				       "attendance_analytics.summary")
			f["branch"] = ("in", [wanted] if wanted else linked)
		# HR: get_list, so the caller's User Permissions apply. A store's HR
		# person (Branch permission) sees their store; central HR, with none,
		# still sees everyone (slice 011). System Manager is treated as CXO for
		# now (slice 010 decision of 2026-09-14) and has no Employee read of its
		# own, so it keeps the unfiltered read.
		read = frappe.get_all if "System Manager" in frappe.get_roles() else frappe.get_list
		staff = read("Employee", filters=f, pluck="name")
		chosen = _chosen(people)
		if chosen:
			outside = sorted(set(chosen) - set(staff))
			if outside:
				frappe.throw(_("{0} of the people you asked for are outside this "
				               "filter or company.").format(len(outside)),
				             frappe.PermissionError)
			return chosen, me
		return staff, me

	frappe.throw(_("Unknown view '{0}'.").format(view))


def _chosen(people):
	if not people:
		return []
	if isinstance(people, str):
		people = frappe.parse_json(people) if people.strip().startswith("[") \
			else [p.strip() for p in people.split(",") if p.strip()]
	return [p for p in people if p]


# ── the arithmetic ───────────────────────────────────────────────────────────

def _shift_row(cache, shift):
	"""A Shift Type's start and end, read once per shift.

	The cache holds the ROW, not an answer derived from it. It used to hold a
	derived number, and two helpers derived different numbers under the same
	key: `_shift_minutes` stored the shift's LENGTH and `_shift_start` stored
	where it BEGINS. Whichever ran first won, and the other silently read its
	answer. On a 09:30-18:30 shift the length is 540 minutes, so the day was
	judged from 09:00 and every arrival looked half an hour later than it was.

	Caching the row instead makes that class of mistake impossible: there is
	one fact in the cache and each helper does its own arithmetic on it. It
	also costs one query per shift instead of two.
	"""
	if shift not in cache:
		cache[shift] = frappe.db.get_value(
			"Shift Type", shift,
			["start_time", "end_time", "late_entry_grace_period"], as_dict=True) or None
	return cache[shift]


def org_late_grace():
	"""The organisation's grace period, in minutes. Never negative."""
	return max(0, cint(frappe.db.get_default(LATE_GRACE_KEY) or DEFAULT_LATE_GRACE_MINS))


def _shift_grace(cache, shift):
	"""How many minutes late this shift forgives, in the order set out above."""
	row = _shift_row(cache, shift) if shift else None
	own = cint(row.late_entry_grace_period) if row else 0
	return own if own > 0 else org_late_grace()


def _shift_minutes(cache, shift):
	"""How long a shift is meant to last, in minutes."""
	row = _shift_row(cache, shift)
	if not row or row.start_time is None or row.end_time is None:
		return None
	start = row.start_time.total_seconds() / 60.0
	end = row.end_time.total_seconds() / 60.0
	if end <= start:            # a night shift crosses midnight
		end += 24 * 60
	return end - start


def _gather(employees, start, end):
	rows = frappe.get_all(
		"Attendance",
		filters={"employee": ("in", employees), "docstatus": 1,
		         "attendance_date": ("between", [start, end])},
		fields=["employee", "attendance_date", "status", "working_hours", "shift",
		        "late_entry", "early_exit", "leave_type"],
		limit_page_length=0)
	return rows


def _default_shift_of(employees):
	out = {}
	for e in frappe.get_all("Employee", filters={"name": ("in", employees)},
	                        fields=["name", "default_shift"]):
		out[e.name] = e.default_shift
	return out


def _analyse(employees, start, end, tolerance):
	"""Every number this screen shows, in one pass over the attendance rows."""
	if not employees:
		return {}, {}, {}

	shift_cache = {}
	default_shift = _default_shift_of(employees)
	per = {e: {"present": 0, "absent": 0, "leave": 0, "half": 0, "short_days": 0,
	           "hours_short": 0.0, "hours_worked": 0.0, "late": 0, "early": 0,
	           "expected_days": 0, "leave_by_type": {}, "short_dates": []}
	      for e in employees}
	by_weekday = {i: {"short": 0, "present": 0} for i in range(7)}
	by_month = {}

	for r in _gather(employees, start, end):
		p = per.get(r.employee)
		if p is None:
			continue
		d = getdate(r.attendance_date)
		month = d.strftime("%Y-%m")
		m = by_month.setdefault(month, {"short": 0, "present": 0})

		if r.status in PRESENT:
			p["present"] += 1
			p["expected_days"] += 1
			m["present"] += 1
			by_weekday[d.weekday()]["present"] += 1
			p["hours_worked"] += flt(r.working_hours)
			p["late"] += cint(r.late_entry)
			p["early"] += cint(r.early_exit)

			expected = _shift_minutes(shift_cache, r.shift or default_shift.get(r.employee))
			# No shift, no expectation. Counting a shortfall against a length
			# nobody defined would invent a problem.
			if expected:
				short_by = (expected - tolerance) - flt(r.working_hours) * 60.0
				if short_by > 0:
					p["short_days"] += 1
					p["hours_short"] += short_by / 60.0
					p["short_dates"].append(str(d))
					m["short"] += 1
					by_weekday[d.weekday()]["short"] += 1
		elif r.status == "Half Day":
			p["half"] += 1
			p["expected_days"] += 1
		elif r.status == "On Leave":
			p["leave"] += 1
			p["expected_days"] += 1
			if r.leave_type:
				p["leave_by_type"][r.leave_type] = p["leave_by_type"].get(r.leave_type, 0) + 1
		elif r.status == "Absent":
			p["absent"] += 1
			p["expected_days"] += 1

	return per, by_weekday, by_month


def _longest_run(dates):
	"""The longest run of consecutive short days.

	A run of five is a life event, not a discipline case, and the two should not
	look the same in a list.
	"""
	if not dates:
		return 0
	days = sorted(getdate(d) for d in dates)
	best = run = 1
	for a, b in zip(days, days[1:]):
		run = run + 1 if (b - a).days == 1 else 1
		best = max(best, run)
	return best


# ── the screen ───────────────────────────────────────────────────────────────

@frappe.whitelist()
def summary(view="mine", depth="direct", date_from=None, date_to=None,
            people=None, department=None, branch=None, designation=None,
            manager=None):
	"""The six metrics, the people behind them, and what the pattern suggests."""
	filters = {"department": department, "branch": branch,
	           "designation": designation, "manager": manager}
	employees, me = _population(view, depth, people, filters)

	end = getdate(date_to or nowdate())
	start = getdate(date_from) if date_from else add_days(end, -29)
	tolerance = cint(frappe.db.get_default(TOLERANCE_KEY) or DEFAULT_TOLERANCE_MINS)

	per, by_weekday, by_month = _analyse(employees, start, end, tolerance)
	names = {e.name: e.employee_name for e in frappe.get_all(
		"Employee", filters={"name": ("in", employees or [""])},
		fields=["name", "employee_name"])}

	rows = []
	for emp, p in per.items():
		present = p["present"]
		rows.append({
			"employee": emp,
			"name": names.get(emp, emp),
			"present": present,
			"absent": p["absent"],
			"leave": p["leave"],
			"leave_by_type": p["leave_by_type"],
			"half": p["half"],
			"short_days": p["short_days"],
			# The rate is what makes two people comparable when one was present
			# 12 days and the other 22.
			"short_rate": round(100.0 * p["short_days"] / present, 1) if present else 0.0,
			"hours_short": round(p["hours_short"], 1),
			"hours_worked": round(p["hours_worked"], 1),
			"late": p["late"], "early": p["early"],
			"longest_run": _longest_run(p["short_dates"]),
			"attendance_rate": round(100.0 * present / p["expected_days"], 1)
			if p["expected_days"] else 0.0,
		})

	rows.sort(key=lambda r: (-r["short_rate"], -r["hours_short"]))
	median = _median([r["short_rate"] for r in rows if r["present"]])

	return {
		"view": view,
		# Sent back so the page can name the group in words. "15 people" left a
		# reader asking whether their manager was one of the fifteen; only the
		# view and the depth together can answer that.
		"depth": depth,
		"from": str(start), "to": str(end),
		"tolerance_mins": tolerance,
		"people": len(rows),
		"headline": _headline(rows, median),
		"rows": rows,
		"median_short_rate": median,
		"weekday": _weekday_pattern(by_weekday),
		"months": [{"month": k, **v,
		            "rate": round(100.0 * v["short"] / v["present"], 1) if v["present"] else 0.0}
		           for k, v in sorted(by_month.items())],
		"leave_types": sorted({t for r in rows for t in r["leave_by_type"]}),
	}


def _median(values):
	if not values:
		return 0.0
	s = sorted(values)
	mid = len(s) // 2
	return round(s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2.0, 1)


def _headline(rows, median):
	present = sum(r["present"] for r in rows)
	short = sum(r["short_days"] for r in rows)
	return {
		"days_present": present,
		"short_days": short,
		"short_rate": round(100.0 * short / present, 1) if present else 0.0,
		"hours_short": round(sum(r["hours_short"] for r in rows), 1),
		"absences": sum(r["absent"] for r in rows),
		"leave_days": sum(r["leave"] for r in rows),
		"late": sum(r["late"] for r in rows),
		# Not "who was ever short" - almost everybody is. Who is short more than
		# twice as often as the middle of their own group.
		"above_median": len([r for r in rows
		                     if r["present"] and median and r["short_rate"] > median * 2]),
		"median_short_rate": median,
	}


WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _weekday_pattern(by_weekday):
	"""Short days by day of the week, and whether one day stands out.

	The most valuable thing this screen does. A day that runs well above the
	others across a whole group is a rota, a shift definition or a closing
	routine - not a group of people who all decided to leave early. Managing
	individuals cannot fix that, and every conversation about it would be
	unfair.
	"""
	days = []
	for i, label in enumerate(WEEKDAYS):
		v = by_weekday.get(i, {"short": 0, "present": 0})
		days.append({"day": label, "short": v["short"], "present": v["present"],
		             "rate": round(100.0 * v["short"] / v["present"], 1)
		             if v["present"] else 0.0})

	worked = [d for d in days if d["present"] >= 5]
	verdict = None
	if len(worked) >= 3:
		rates = sorted(d["rate"] for d in worked)
		mid = rates[len(rates) // 2]
		worst = max(worked, key=lambda d: d["rate"])
		# A third again as often as the middle day, and not a rounding artefact.
		#
		# When the middle day is clean, "a third again" can never be met - and a
		# group that is short only on Mondays is the strongest rota signal there
		# is, so that case has its own floor rather than being silently dropped.
		stands_out = (worst["rate"] >= mid * 1.35) if mid else (worst["rate"] >= 20)
		if stands_out and worst["short"] >= 5:
			verdict = {
				"day": worst["day"], "rate": worst["rate"], "median": mid,
				"message": _("Short days fall on {0} far more than any other day "
				             "({1}% against {2}% typical). Across a whole group that "
				             "usually means the rota, the shift times or a closing "
				             "routine - not the people."
				             ).format(worst["day"], worst["rate"], mid),
			}
	return {"days": days, "verdict": verdict}


@frappe.whitelist()
def filter_options():
	"""What the Organisation view may filter by - and only what exists.

	A dropdown with nothing in it is the clearest possible sign that a product
	was built for somebody else, so anything the tenant does not use is left
	out entirely.
	"""
	if not _may_see_organisation():
		frappe.throw(_("Only HR and system administrators can see the whole "
		               "organisation."), frappe.PermissionError)
	me = _me()
	base = {"status": "Active"}
	if me and me.company:
		base["company"] = me.company
	branches = _linked_branches()
	if branches is not None:
		# Same rule as person(): no-branch staff are outside a store HR's scope.
		base["branch"] = ("in", branches)
	# Slice 012 G3 (SEC-17): the same read the organisation list uses, so a
	# store's HR person gets their store's departments and managers, not every
	# store's manager names.
	read = _org_read()

	def distinct(field):
		vals = {r[field] for r in read("Employee", filters=base,
		                               fields=[field]) if r.get(field)}
		return sorted(vals)

	managers = read("Employee", filters=base, fields=["reports_to"])
	mgr_ids = sorted({m.reports_to for m in managers if m.reports_to})
	mgr_names = {e.name: e.employee_name for e in read(
		"Employee", filters={"name": ("in", mgr_ids or [""])},
		fields=["name", "employee_name"])}

	return {
		"department": distinct("department"),
		"branch": distinct("branch"),
		"designation": distinct("designation"),
		# Only managers the caller may read. A manager in another store stays out
		# rather than appearing as a bare employee id.
		"manager": [{"id": m, "name": mgr_names[m]} for m in mgr_ids if m in mgr_names],
	}


def _linked_branches(user=None):
	"""The branches a location HR person is limited to, or None for everyone else.

	Frappe's User Permissions are not strict on this site, so a record with an
	EMPTY branch passes a Branch permission. Employees with no branch - often
	head office - were therefore openable by a store's HR person, while HR
	Analytics leaves the same people out of their figures (decision D-8). The
	two screens now agree, and this one fails closed (DEF-6, 2026-09-16).

	Slice 030: the definition moved to hrms.alvoraa_hr_core.access so the review
	list, the calibration matrix and the KPI report answer "who may this HR
	person see" the same way as these screens. This name stays for the callers
	above; there is one definition.
	"""
	from hrms.alvoraa_hr_core.access import permitted_branches

	return permitted_branches(user)


def _org_read():
	"""get_list, so User Permissions apply - except for System Manager.

	System Manager is treated as CXO for now (slice 010 decision of 2026-09-14)
	and holds no Employee read of its own, so it keeps the unfiltered read.
	"""
	return frappe.get_all if "System Manager" in frappe.get_roles() else frappe.get_list


# Slice 012 AC-48: one person's days, at most a year at a time.
PERSON_MAX_MONTHS = 12


def _in_organisation(employee, me):
	"""Is this employee inside the organisation population `summary` builds for the caller?

	Same rule: the caller's own company, read with the caller's User Permissions.
	Leavers inside that population may still be opened (decision D-7), so there
	is no status filter. One indexed lookup, not the whole list.
	"""
	f = {"name": employee}
	if me and me.company:
		f["company"] = me.company
	branches = _linked_branches()
	if branches is not None:
		f["branch"] = ("in", branches)      # an empty branch is not one of them
	return bool(_org_read()("Employee", filters=f, pluck="name", limit=1))


@frappe.whitelist()
def person(employee, date_from=None, date_to=None):
	"""One person's days, for somebody who clicked a name.

	Same permission question as the list: a name is only openable by whoever
	could already see it in one of their views.
	"""
	me = _me()
	if not me:
		frappe.throw(_("Your user is not linked to an employee record."),
		             frappe.PermissionError)
	if not isinstance(employee, str) or not employee:
		frappe.throw(_("Choose a person to open."))
	allowed = (employee == me.name
	           or employee in _reports_to(me.name, deep=True)
	           or (_may_see_organisation() and _in_organisation(employee, me)))
	if not allowed:
		# Slice 012 G3 (SEC-17): being HR used to open ANY employee - another
		# store's, another company's - with every day's leave type. Now only
		# someone inside the population the organisation list shows this caller.
		from hrms.alvoraa_hr_core.access import refuse

		refuse(_("You cannot see that person's attendance."), "SEC-17",
		       "attendance_analytics.person", "Employee", employee)

	end = getdate(date_to or nowdate())
	start = getdate(date_from) if date_from else add_days(end, -29)
	# Cut, not refused: a long range is a mistake, not an attack.
	earliest = add_days(add_months(end, -PERSON_MAX_MONTHS), 1)
	if start < earliest:
		start = earliest
	tolerance = cint(frappe.db.get_default(TOLERANCE_KEY) or DEFAULT_TOLERANCE_MINS)

	shift_cache = {}
	default_shift = _default_shift_of([employee]).get(employee)
	days = []
	for r in sorted(_gather([employee], start, end),
	                key=lambda x: str(x.attendance_date), reverse=True):
		expected = _shift_minutes(shift_cache, r.shift or default_shift)
		worked = flt(r.working_hours)
		short_by = 0.0
		if r.status in PRESENT and expected:
			gap = (expected - tolerance) - worked * 60.0
			short_by = round(gap / 60.0, 2) if gap > 0 else 0.0
		days.append({
			"date": str(r.attendance_date),
			"weekday": WEEKDAYS[getdate(r.attendance_date).weekday()],
			"status": r.status,
			"hours": round(worked, 2),
			"expected_hours": round(expected / 60.0, 2) if expected else None,
			"short_by": short_by,
			"late": cint(r.late_entry), "early": cint(r.early_exit),
			"leave_type": r.leave_type,
		})
	return {"employee": employee,
	        "name": frappe.db.get_value("Employee", employee, "employee_name"),
	        "from": str(start), "to": str(end),
	        "tolerance_mins": tolerance, "days": days}
