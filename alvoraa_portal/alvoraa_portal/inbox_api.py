"""Slice 034 Wave 1, extended by slice 042 Wave 2: one honest number, and the
list it links to.

Wave 1 built this file with the **counts only** and said in this docstring that
Wave 2 would extend it rather than replace it. Wave 2 has, and the extension is
one idea:

    **A part has one filter expression and two uses of it.**

        part.count()          -> int        the same filters, counted
        part.rows(limit=n)    -> [rows]     the same filters, ordered, limited

`get_nav_counts` (the bell, the menu entry, the bottom-bar button) and
`get_inbox` (the screen) both call `parts()`. Neither writes a filter of its
own. The day somebody writes a second filter "just for the badge" is the day the
number stops matching the list, so there is nowhere to put one.

Four rules govern this module, each with a test that fails if it is broken.

**A count must equal the list it links to (034 AC-51, 042 AC-8).** Not "about
equal". Where a screen is capped the count is not - it is the true total, and
the screen says "Showing the first 50 of 60" rather than quietly showing fewer.
No part ever shows "50+", because a "50+" cannot be added into one honest total.

**Every part declares its scope as data, and no filter helper returns `{}`
(042 SEC-3, SEC-4, AC-8).** A `Part` built without a non-empty `scope` string
raises at import, so a part added later with no scope is a test failure rather
than a runtime default meaning "everybody". And in Frappe an empty filter dict
means **every record**, so a caller entitled to nobody gets `no_rows()` -
filters that match nothing - never "no condition". The assertion is on the
**return value**, not on the rows: an unscoped query that happened to return
nothing looks identical from the outside, and that is the fail-open shape.

**Nobody gets an error instead of a count (034 AC-63, 042 AC-37).** A platform
operator with no Employee record, and a leaver whose login still works, get
every part at zero and a total of zero - and the scoped queries **do not run at
all**. The refusal is an explicit early return, not a filter that happened to be
skipped.

**No `ignore_permissions`, and no module-level state that changes at run time**
(SEC-6 / AC-71, SEC-15 / AC-70). Every constant here is a tuple. One worker
serves several sites.

Guest is refused, and the refusal is the decorator plus an explicit line, the
same belt-and-braces as `frame_api.get_frame` (SEC-2). Every function here is
live on production from the release that carries it, whatever page calls it, so
the Guest, wrong-persona and scope tests ship in the same commit.

## What Wave 2 deliberately did NOT build

**D-2 - who may decide an attendance correction, and from when.** The approved
design says the manager decides and HR steps in after two working days. The code
sends every correction to whoever holds the **submit permission** on Attendance
Request (`attendance_correction._may_review`) - a permission, not a role. That
is a permission change wearing a routing change's clothes, and it is with the
product owner. **The fail-closed default is built here: no new decider.** The
corrections part reads `review_queue_filters` exactly as Wave 1 left it. There
is no two-working-day rule and no "visible but not actionable" state, because
the code has no such state and inventing one quietly would be the worst of the
three options.
"""

import frappe
from frappe import _
from frappe.utils import get_build_version

# The parts, in the order the Inbox page lists them. Wave 1's section 5 table,
# and the routes are its section 4's. A tuple of tuples: nothing here is
# appended to at run time (SEC-15).
#
# `my_requests` is the one route that is not a single screen - Wave 2's Inbox
# shows all three kinds (leave, attendance fixes and shift changes) in one tab,
# so the route is the Inbox's own "my requests" tab.
PARTS = (
	("leave_approvals", "#team"),
	("goal_updates", "#growth"),
	("attendance_fixes", "#time/fix"),
	("shift_requests", "#time/shift"),
	("policies", "#company/policies"),
	("my_requests", "#time"),
)

# Which parts add up to "approvals waiting". The total is
# approvals + policies + my own open requests (Wave 1 AC-20, Wave 2 section 6.2),
# so the three groups are named rather than left as an arithmetic accident.
APPROVAL_PARTS = ("leave_approvals", "goal_updates", "attendance_fixes", "shift_requests")

# The attendance corrections screen reads at most this many rows
# (`attendance_correction.to_review`'s default). The COUNT is not capped, so the
# bell can say 60 while the screen shows 50 and says so (Wave 1 section 5, N3).
CORRECTIONS_CAP = 50

# Every list in the Inbox is capped at the same number, for the same reason
# (Wave 2 section 6.1 rule 2, section 13).
LIST_CAP = 50

# The keys a row may carry, per part. Enforced on the way out of `rows()`, the
# same discipline as `frame_api.FRAME_KEYS`: a field cannot reach a browser by
# accident, and adding one is a deliberate act somebody reviews.
#
# What is NOT here matters more than what is. No absence reason, anywhere. No
# decision note belonging to somebody else. No document id in any count.
# A tuple of tuples, not a dict: one worker serves several sites, and SEC-15
# forbids any module-level mutable here. `row_keys()` below is the lookup.
ROW_KEYS = (
	# The named approver is deciding this document, so they see whose it is and
	# what kind of leave it is - it is on the page they would open anyway. The
	# CONTEXT LINE is the thing that carries no colleague name and no leave
	# type (042 AC-28), and it is built in `_leave_contexts`, not here.
	("leave_approvals", ("name", "employee_name", "from_date", "to_date",
	                     "leave_type", "total_days", "context", "action")),
	# No colleague name for a goal or KPI update? There is one, and there has to
	# be: an approver cannot approve "somebody's" progress. What is absent is the
	# number's provenance and any note about the person.
	("goal_updates", ("name", "kind", "employee_name", "subject", "logged_on",
	                  "value", "action")),
	("attendance_fixes", ("name", "employee_name", "from_date", "to_date",
	                      "reason", "context", "action")),
	("shift_requests", ("name", "employee_name", "from_date", "to_date",
	                    "shift_type", "action")),
	# A policy is a document, not a person. No employee field at all.
	("policies", ("name", "title", "version", "action")),
	# My own requests are mine, so the state sentence and the reason I was given
	# are mine to read. No approver's name beyond the one the state sentence
	# already says, and never anybody else's row (042 AC-20).
	#
	# `title` is a TRANSLATED WORD, added by the 042 review (F2). These rows
	# carry no `employee_name` - they are the caller's own - so the screen used
	# to fall back to `kind` and head an employee's own rows with the raw
	# internal keys `attendance_fix` and `shift_request`, untranslated.
	("my_requests", ("name", "kind", "title", "from_date", "to_date", "state",
	                 "says", "note", "can_withdraw", "action")),
)


def row_keys(key):
	"""The keys a row of this part may carry. Raises for an unknown part, so a
	new part cannot quietly ship with no key list at all."""
	for name, fields in ROW_KEYS:
		if name == key:
			return fields
	raise PartDefinitionError("no row key list for part %r" % (key,))


class PartDefinitionError(frappe.ValidationError):
	"""A part was built without a scope, or with an empty filter dict.

	Raised when the part is constructed, not when it is read, so a mistake is a
	failure in every test that touches `parts()` rather than a silent "everybody"
	on one tenant at month end.
	"""


def no_rows():
	"""Filters that match nothing (SEC-4).

	`{}` in Frappe means **every record**. A caller entitled to nobody must get
	a filter that matches nothing, and it must be visible in the return value -
	the test asserts on what this returns, not on how many rows came back.
	"""
	return {"name": ["in", []]}


def _has_doctype(name):
	"""Is this doctype on the site, asked once per site per release?

	Three parts of this call are guarded by "does this doctype exist" - KPI,
	Shift Request and Policy Document - because a bench without the goals app
	or the policy library must not throw. Asked directly that is three database
	queries on a call whose whole job is to be cheap, and the answer changes
	only at a migration, which clears this cache.

	The build version is in the key (review finding F8, 2026-09-24). A migration
	clears the cache and so does a deploy, so the normal path was already safe -
	but the path that skips both is one this project uses: copying a file onto a
	running container changes nothing for up to a day. With the version in the
	key, a new build cannot read the last build's answer. If the goals app is
	installed on a live tenant and nothing clears the cache, the Inbox would
	otherwise count KPI approvals as zero until tomorrow.
	"""
	key = "inbox_api:doctype:%s:%s" % (get_build_version(), name)
	seen = frappe.cache().get_value(key)
	if seen is None:
		seen = 1 if frappe.db.exists("DocType", name) else 0
		frappe.cache().set_value(key, seen, expires_in_sec=24 * 60 * 60)
	return bool(seen)


def _my_employee(user):
	"""The caller's own ACTIVE Employee record id, or None.

	The same "who am I" question `frame_api._me` asks, and the same answer, so
	the bell and the menu cannot describe two different people. None is a real
	answer here, not a failure: a platform operator never had an Employee
	record, and a leaver's is no longer Active (SEC-14). A rehire with two rows,
	one Left and one Active, gets the Active one - one helper, one answer
	(042 AC-47).
	"""
	return frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")


# ── The part ─────────────────────────────────────────────────────────────────


class Part:
	"""One row of the Inbox: one filter expression, counted and listed.

	`count_fn` and `rows_fn` are both handed `self.filters`. They cannot be
	handed anything else, which is the whole mechanism: there is no seam where a
	second filter could be written for the badge.

	`available` is False for a part this caller does not have at all - no
	Employee record, no review permission, the doctype is not installed. An
	unavailable part counts 0 and lists nothing **without running a query**
	(042 AC-37). That is an explicit early return, not a filter that matched
	nothing.
	"""

	__slots__ = ("key", "route", "scope", "cap", "filters", "_count_fn", "_rows_fn",
	             "available", "label_one", "label_many")

	def __init__(self, key, route, scope, filters, count_fn, rows_fn,
	             cap=LIST_CAP, available=True, label_one="", label_many=""):
		if not isinstance(scope, str) or not scope.strip():
			raise PartDefinitionError(
				"Part %r was built with no scope declaration. Every part says, as "
				"data and not as a comment, whose records it may read." % (key,))
		if isinstance(filters, dict) and not filters:
			raise PartDefinitionError(
				"Part %r was built with an empty filter dict. In Frappe that means "
				"every record. Use no_rows() to match nothing." % (key,))
		self.key = key
		self.route = route
		self.scope = scope
		self.cap = cap
		self.filters = filters
		self._count_fn = count_fn
		self._rows_fn = rows_fn
		self.available = bool(available)
		self.label_one = label_one
		self.label_many = label_many

	def count(self):
		"""The true total. Never capped - see the module docstring."""
		if not self.available:
			return 0
		return int(self._count_fn(self.filters) or 0)

	def rows(self, limit=LIST_CAP):
		"""The same filters, ordered, and cut to `limit`. `None` means all of them.

		The returned rows are cut to `row_keys(self.key)` here rather than in
		each `rows_fn`, so the key list is one list in one place.
		"""
		if not self.available:
			return []
		allowed = row_keys(self.key)
		out = []
		for row in self._rows_fn(self.filters, limit):
			out.append({k: row.get(k) for k in allowed})
		return out

	def label(self, n):
		"""The row's wording, as a whole phrase with a placeholder (042 AC-26).

		Never a sentence built by joining fragments: Hindi and Punjabi put the
		number and the noun in a different order.
		"""
		return (self.label_one if n == 1 else self.label_many).format(n=n)


# ── The six parts ────────────────────────────────────────────────────────────
#
# Each builder returns ONE Part. Each is handed the same context, computed once
# per call, so `parts()` asks "who am I" once rather than six times.


class _Who:
	"""Who is asking, worked out once. Not module state - one per call.

	There is deliberately no `is_hr` here. "HR" means two different things in
	this codebase - `goals_api._is_hr` reads the goals app's role set, and the
	corrections queue reads `permitted_companies()` - and a single flag would
	quietly pick one of them for both. Each part asks the question its own
	source asks, through that source's own helper.
	"""

	__slots__ = ("user", "employee")

	def __init__(self, user):
		self.user = user
		self.employee = _my_employee(user)


def _count_rows(doctype):
	"""A counter that asks the database, under the caller's own permissions.

	`get_list`, not `get_all`: a tenant that has scoped a doctype by department
	gets that scoping in the count as well as on the screen. `pluck` with no
	page length is a single query returning one column.
	"""

	def counter(filters):
		return len(frappe.get_list(doctype, filters=filters, pluck="name",
		                           limit_page_length=0))

	return counter


def _leave_contexts(rows):
	"""How many OTHER people in the same team are away on those days - numbers.

	042 AC-28. The payload carries no colleague name and no leave type: an
	approver deciding Tuesday off needs to know two other people are already
	away, and nothing whatever about who they are or why.

	**One query for the whole page, not one per row.** The first version asked
	the database once per drawn row, which is fifty queries at the list cap and
	breaks AC-15's budget of twenty-five for the whole call. This reads every
	overlapping leave in the departments on the page, once, and counts in Python
	- and the count it produces is identical, because the filter is the same.

	Returns {leave application name: sentence or None}.
	"""
	from frappe.utils import getdate

	wanted = [r for r in rows if r.get("department") and r.get("from_date")
	          and r.get("to_date")]
	if not wanted:
		return {}
	departments = sorted({r["department"] for r in wanted})
	start = min(getdate(r["from_date"]) for r in wanted)
	end = max(getdate(r["to_date"]) for r in wanted)
	others = frappe.get_all(
		"Leave Application",
		filters={
			"department": ["in", departments],
			"status": ["in", ["Open", "Approved"]],
			"docstatus": ["<", 2],
			"from_date": ["<=", end],
			"to_date": [">=", start],
		},
		# `employee` is read to exclude the row's own subject and to count
		# PEOPLE rather than applications; it never leaves this function, and
		# no name and no leave type is read at all.
		fields=["name", "employee", "department", "from_date", "to_date"],
		limit_page_length=0)
	# `get_all` rather than `get_list`, and deliberately. What the approver
	# receives is an AGGREGATE they are entitled to - "2 other people are away
	# on those days" - and under `get_list` a plain employee who happens to be a
	# named approver would read 0 because they may not see a colleague's leave
	# row. A wrong number is worse than no number, and the number is the only
	# thing that leaves this function.

	out = {}
	for row in wanted:
		row_from = getdate(row["from_date"])
		row_to = getdate(row["to_date"])
		people = {
			other.employee for other in others
			if other.department == row["department"]
			and other.employee != row["employee"]
			and getdate(other.from_date) <= row_to
			and getdate(other.to_date) >= row_from
		}
		out[row["name"]] = (
			_("{n} other people in this team are away on those days").format(
				n=len(people))
			if people else None)
	return out


def _part_leave_approvals(who):
	"""Leave applications waiting on this person as the named approver.

	Anybody can be named a leave approver, so there is no role test here and
	there should not be one.

	`employee != my own` is the rule that keeps 042 AC-9 true: a person who is
	their own leave approver is counted **once**, under "my requests", never
	here. Without it one open application would add two to one total.
	"""
	filters = no_rows()
	if who.employee:
		filters = {
			"leave_approver": who.user,
			"status": "Open",
			"docstatus": 0,
			"employee": ["!=", who.employee],
		}

	def rows_fn(filters, limit):
		rows = frappe.get_list(
			"Leave Application", filters=filters,
			fields=["name", "employee", "employee_name", "department", "leave_type",
			        "from_date", "to_date", "total_leave_days"],
			order_by="from_date asc", limit_page_length=limit or 0)
		# One query for every context line on the page, not one per row.
		contexts = _leave_contexts(rows)
		out = []
		for r in rows:
			out.append({
				"name": r.name,
				"employee_name": r.employee_name,
				"from_date": str(r.from_date) if r.from_date else None,
				"to_date": str(r.to_date) if r.to_date else None,
				"leave_type": r.leave_type,
				"total_days": r.total_leave_days,
				"context": contexts.get(r.name),
				"action": "leave",
			})
		return out

	return Part(
		"leave_approvals", "#team",
		scope="leave applications where this caller is the named leave_approver, "
		      "minus their own",
		filters=filters,
		count_fn=_count_rows("Leave Application"),
		rows_fn=rows_fn,
		available=bool(who.employee),
		label_one=_("{n} leave request to approve"),
		label_many=_("{n} leave requests to approve"),
	)


def _part_goal_updates(who):
	"""KPI and goal progress updates this caller may approve.

	The filter expression here is the **employee scope** -
	`goals_api._pending_approvals_scope`, which is the definition of who a
	manager or an HR person may approve for. It is called, never copied: a
	future change to that rule has one place to land.

	Both the count and the rows walk that one list, set-based. Neither calls
	`goals_api.get_pending_approvals`, which walks one employee at a time and
	took 16.4 seconds for an HR caller (042 AC-16).
	"""
	scope = None
	available = bool(who.employee) and _has_doctype("KPI")
	if available:
		# `_is_hr` is imported rather than re-derived: it is the definition
		# `get_pending_approvals_count` uses, and the scope helper is built for
		# that definition. Asking the question a second way is how two screens
		# come to disagree about who HR is.
		from alvoraa_portal.goals_api import _is_hr, _pending_approvals_scope_query

		# **A subquery, not a list of names** (044 R4). This used to read every
		# permitted employee id into Python - 981 of them on the measured
		# fixture, uncapped - and ship them back inside each `IN (...)`. The
		# scope now stays in the database, so the statement is the same size
		# whatever the tenant's headcount.
		scope = _pending_approvals_scope_query(who.employee, _is_hr(who.user))

	# The one filter expression. `no_rows()` rather than `{}` for a caller
	# entitled to nobody (SEC-4) - and the test reads this value, not the rows.
	#
	# `employee_not` is belt as well as braces for 042 AC-25: the scope query
	# already excludes the caller, and this is what still excludes them if it
	# ever stops. It lives IN the filters, not in a closure, so `count_fn` and
	# `rows_fn` still cannot be handed anything the badge was not counted with.
	filters = ({"employee": ["in", scope], "employee_not": who.employee}
	           if scope is not None else no_rows())

	def _pending(field):
		return (field == "Pending") | (field == "") | field.isnull()

	def _scope_of(filters):
		"""(scope subquery, the employee it must exclude), or (None, None).

		Read out of `filters` rather than closed over, so `count_fn` and
		`rows_fn` still cannot be handed anything the badge was not counted
		with. `no_rows()` carries a plain list, which is the "nobody" case.
		"""
		got = filters.get("employee")
		if (isinstance(got, (list, tuple)) and got[0] == "in"
				and not isinstance(got[1], (list, tuple))):
			return got[1], filters.get("employee_not")
		return None, None

	def count_fn(filters):
		from frappe.query_builder.functions import Count

		scope, not_me = _scope_of(filters)
		if scope is None:
			return 0
		KPI = frappe.qb.DocType("KPI")
		KPILog = frappe.qb.DocType("KPI Progress Log")
		kpi_total = (
			frappe.qb.from_(KPILog)
			.join(KPI).on(KPILog.parent == KPI.name)
			.where(KPI.employee.isin(scope) & (KPI.employee != not_me)
			       & (KPI.status != "Cancelled"))
			.where(_pending(KPILog.approval_status))
			.select(Count("*"))
		).run()[0][0]
		Goal = frappe.qb.DocType("Individual Goal")
		GoalUpd = frappe.qb.DocType("Goal Progress Update")
		goal_total = (
			frappe.qb.from_(GoalUpd)
			.join(Goal).on(GoalUpd.parent == Goal.name)
			.where(Goal.employee.isin(scope) & (Goal.employee != not_me)
			       & (Goal.status != "Cancelled") & (Goal.docstatus != 2))
			.where(_pending(GoalUpd.approval_status))
			.select(Count("*"))
		).run()[0][0]
		return int(kpi_total) + int(goal_total)

	def rows_fn(filters, limit):
		scope, not_me = _scope_of(filters)
		if scope is None:
			return []
		out = []
		KPI = frappe.qb.DocType("KPI")
		KPILog = frappe.qb.DocType("KPI Progress Log")
		kpi_rows = (
			frappe.qb.from_(KPILog)
			.join(KPI).on(KPILog.parent == KPI.name)
			.where(KPI.employee.isin(scope) & (KPI.employee != not_me)
			       & (KPI.status != "Cancelled"))
			.where(_pending(KPILog.approval_status))
			.select(KPILog.name, KPI.kpi_name, KPI.employee, KPILog.value,
			        KPILog.creation)
			.orderby(KPILog.creation)
		).run(as_dict=True)
		Goal = frappe.qb.DocType("Individual Goal")
		GoalUpd = frappe.qb.DocType("Goal Progress Update")
		goal_rows = (
			frappe.qb.from_(GoalUpd)
			.join(Goal).on(GoalUpd.parent == Goal.name)
			.where(Goal.employee.isin(scope) & (Goal.employee != not_me)
			       & (Goal.status != "Cancelled") & (Goal.docstatus != 2))
			.where(_pending(GoalUpd.approval_status))
			.select(GoalUpd.name, Goal.goal_name, Goal.employee, GoalUpd.value,
			        GoalUpd.creation)
			.orderby(GoalUpd.creation)
		).run(as_dict=True)
		merged = ([("kpi", r, r.get("kpi_name")) for r in kpi_rows]
		          + [("goal", r, r.get("goal_name")) for r in goal_rows])
		merged.sort(key=lambda t: t[1].get("creation") or "")
		if limit:
			merged = merged[:limit]
		# One name lookup for every employee on the page, not one per row.
		emp_ids = sorted({r.get("employee") for _k, r, _s in merged if r.get("employee")})
		names_by_id = {}
		if emp_ids:
			names_by_id = {
				e.name: e.employee_name
				for e in frappe.get_all("Employee", filters={"name": ["in", emp_ids]},
				                        fields=["name", "employee_name"])
			}
		for kind, r, subject in merged:
			out.append({
				"name": r.get("name"),
				"kind": kind,
				"employee_name": names_by_id.get(r.get("employee")),
				"subject": subject,
				"logged_on": str(r.get("creation")) if r.get("creation") else None,
				"value": r.get("value"),
				"action": "goal_update",
			})
		return out

	return Part(
		"goal_updates", "#growth",
		scope="employees inside goals_api._pending_approvals_scope for this caller, "
		      "minus themselves",
		filters=filters,
		count_fn=count_fn,
		rows_fn=rows_fn,
		available=available,
		label_one=_("{n} goal or KPI update to approve"),
		label_many=_("{n} goal or KPI updates to approve"),
	)


def _part_attendance_fixes(who):
	"""Attendance corrections waiting for this caller to decide.

	**D-2 is not built here.** Who may see this queue is not a role -
	`attendance_correction._may_review` tests the submit permission on
	Attendance Request, so a tenant can hand the queue to a Shift Supervisor.
	That function is called, not re-implemented, and `review_queue_filters` is
	read exactly as Wave 1 left it. The approved design's "the manager decides,
	HR after two working days" is a **permission change** and is with the
	product owner; until it is answered the queue stays as it is today.

	**The count is not capped, and the screen is.** `to_review` reads 50 rows.
	This counts every waiting row in the caller's scope, so the bell can say 60
	while the screen shows 50 and says so.
	"""
	from alvoraa_portal.attendance_correction import (
		REQUEST, _may_review, review_queue_filters,
	)

	available = bool(who.employee) and bool(_may_review())
	filters, is_hr_scope = (review_queue_filters(who.user) if available
	                        else (no_rows(), False))

	def rows_fn(filters, limit):
		rows = frappe.get_list(
			REQUEST, filters=filters,
			fields=["name", "employee_name", "from_date", "to_date", "reason",
			        "half_day"],
			order_by="creation asc", limit_page_length=limit or 0)
		out = []
		for r in rows:
			out.append({
				"name": r.name,
				"employee_name": r.employee_name,
				"from_date": str(r.from_date) if r.from_date else None,
				"to_date": str(r.to_date) if r.to_date else None,
				"reason": r.reason,
				# A correction's own "reason" is the category the employee picked
				# ("I was at work", "the machine did not read my card"), not a
				# reason for an absence. It is the thing being decided.
				"context": _("Half day") if r.half_day else None,
				"action": "attendance_fix",
			})
		return out

	part = Part(
		"attendance_fixes", "#time/fix",
		scope=("attendance_correction.review_queue_filters for this caller - "
		       "HR: permitted_employees() minus self; a non-HR reviewer: their "
		       "whole queue, unchanged (W1D-14). D-2 not built"),
		filters=filters,
		count_fn=_count_rows(REQUEST),
		rows_fn=rows_fn,
		cap=CORRECTIONS_CAP,
		available=available,
		label_one=_("{n} attendance fix to decide"),
		label_many=_("{n} attendance fixes to decide"),
	)
	# The Inbox page's wording for a capped corrections list differs for an HR
	# caller and a non-HR reviewer, because their scopes differ (W1D-14).
	return part, is_hr_scope


def _part_shift_requests(who):
	"""Shift changes waiting on this person as the named approver.

	`employee != my own` for the same reason as leave: a person who approves
	their own shift changes is counted once, under "my requests" (042 AC-9's
	rule, applied to part 4 as section 6.2 asks).
	"""
	available = bool(who.employee) and _has_doctype("Shift Request")
	filters = no_rows()
	if available:
		filters = {
			"approver": who.user,
			"docstatus": 0,
			"employee": ["!=", who.employee],
		}

	def rows_fn(filters, limit):
		rows = frappe.get_list(
			"Shift Request", filters=filters,
			fields=["name", "employee_name", "from_date", "to_date", "shift_type"],
			order_by="from_date asc", limit_page_length=limit or 0)
		return [{
			"name": r.name,
			"employee_name": r.employee_name,
			"from_date": str(r.from_date) if r.from_date else None,
			"to_date": str(r.to_date) if r.to_date else None,
			"shift_type": r.shift_type,
			"action": "shift_request",
		} for r in rows]

	return Part(
		"shift_requests", "#time/shift",
		scope="shift requests where this caller is the named approver, minus their own",
		filters=filters,
		count_fn=_count_rows("Shift Request"),
		rows_fn=rows_fn,
		available=available,
		label_one=_("{n} shift change to approve"),
		label_many=_("{n} shift changes to approve"),
	)


def _part_policies(who):
	"""Policies this person may read and has not acknowledged for its version.

	The same answer `hr_api.get_my_policies()["pending"]` gives, in two queries
	rather than one per policy. The definition is
	`policy_document.acknowledgement_status`: a policy needs acknowledging when
	it is set to be acknowledged on joining or on a new version, and it is done
	when there is an acknowledgement for the policy AND its current version.

	The filter expression is the list of (policy, version) pairs still needed.
	Both uses read that one list, so the count and the screen cannot drift.
	"""
	available = bool(who.employee) and _has_doctype("Policy Document")
	needed = []
	if available:
		# `get_list`, so this is what the caller may READ - the same set
		# `readable_policy_names` returns, through the same permission path.
		policies = frappe.get_list(
			"Policy Document", filters={"status": "Published"},
			fields=["name", "title", "current_version", "acknowledge_on_joining",
			        "acknowledge_on_new_version"],
			order_by="title asc", limit_page_length=0)
		wanted = [p for p in policies
		          if p.acknowledge_on_joining or p.acknowledge_on_new_version]
		if wanted:
			done = {
				(a.policy_document, int(a.version or 0))
				for a in frappe.get_all(
					"Policy Acknowledgement",
					filters={"employee": who.employee,
					         "policy_document": ["in", [p.name for p in wanted]]},
					fields=["policy_document", "version"], limit_page_length=0)
			}
			needed = [
				{"name": p.name, "title": p.title,
				 "version": int(p.current_version or 0), "action": "policy"}
				for p in wanted
				if (p.name, int(p.current_version or 0)) not in done
			]

	# A list, not a dict: the "filter expression" for this part really is the
	# set of outstanding pairs. `no_rows()` is not used here because an empty
	# list already matches nothing, and the Part guard only refuses an empty
	# **dict** - which is the shape that means "everything".
	filters = tuple(needed)

	return Part(
		"policies", "#company/policies",
		scope="published policies this caller may READ (get_list), minus the ones "
		      "they have acknowledged at the current version",
		filters=filters,
		count_fn=lambda f: len(f),
		rows_fn=lambda f, limit: list(f[:limit] if limit else f),
		available=available,
		label_one=_("{n} policy to read and accept"),
		label_many=_("{n} policies to read and accept"),
	)


def _part_my_requests(who):
	"""This person's own requests that are still waiting on somebody else.

	Leave, attendance corrections and shift changes, their own **Active**
	Employee record only (042 AC-20). A person who is their own leave approver
	sees their request here and NOT under approvals, which is why this is
	counted from the employee and the approvals are counted from the approver.
	"""
	from alvoraa_portal.attendance_correction import DONE_STATES, REQUEST

	available = bool(who.employee)
	filters = {"employee": who.employee} if available else no_rows()
	has_shift = _has_doctype("Shift Request")

	def _collect(filters, limit):
		"""All three kinds, newest first. One query each, never one per row."""
		employee = filters.get("employee")
		if not employee:
			return []
		out = []
		for r in frappe.get_list(
			"Leave Application",
			filters={"employee": employee, "status": "Open", "docstatus": 0},
			fields=["name", "from_date", "to_date", "creation"],
			order_by="creation desc", limit_page_length=0,
		):
			out.append({
				"name": r.name, "kind": "leave", "title": _("Leave request"),
				"from_date": str(r.from_date) if r.from_date else None,
				"to_date": str(r.to_date) if r.to_date else None,
				"state": "waiting", "says": _("Waiting for your approver"),
				"note": None, "can_withdraw": False, "action": "my_leave",
				"creation": r.creation,
			})
		for r in frappe.get_list(
			REQUEST,
			filters={"employee": employee, "docstatus": 0,
			         "alvoraa_review_status": ["not in", list(DONE_STATES)]},
			fields=["name", "from_date", "to_date", "alvoraa_review_note", "creation"],
			order_by="creation desc", limit_page_length=0,
		):
			out.append({
				"name": r.name, "kind": "attendance_fix",
				"title": _("Attendance correction"),
				"from_date": str(r.from_date) if r.from_date else None,
				"to_date": str(r.to_date) if r.to_date else None,
				"state": "waiting", "says": _("Waiting to be decided"),
				"note": r.alvoraa_review_note,
				# `attendance_correction.withdraw` allows it exactly while the
				# document is still a draft. Same condition, named once.
				"can_withdraw": True, "action": "my_attendance_fix",
				"creation": r.creation,
			})
		if has_shift:
			for r in frappe.get_list(
				"Shift Request",
				filters={"employee": employee, "docstatus": 0},
				fields=["name", "from_date", "to_date", "creation"],
				order_by="creation desc", limit_page_length=0,
			):
				out.append({
					"name": r.name, "kind": "shift_request",
					"title": _("Shift change request"),
					"from_date": str(r.from_date) if r.from_date else None,
					"to_date": str(r.to_date) if r.to_date else None,
					"state": "waiting", "says": _("Waiting for your approver"),
					"note": None, "can_withdraw": False, "action": "my_shift_request",
					"creation": r.creation,
				})
		out.sort(key=lambda r: r.get("creation") or "", reverse=True)
		return out[:limit] if limit else out

	return Part(
		"my_requests", "#time",
		scope="this caller's own Active Employee record, and nobody else's",
		filters=filters,
		count_fn=lambda f: len(_collect(f, None)),
		rows_fn=_collect,
		available=available,
		label_one=_("{n} of your requests is waiting"),
		label_many=_("{n} of your requests are waiting"),
	)


def parts(user=None):
	"""The six parts, in order, for this caller (042 section 6.1).

	The one helper. `get_nav_counts` and `get_inbox` both call it and neither
	writes a filter of its own.

	Returns (parts, corrections_hr_scope).
	"""
	who = _Who(user or frappe.session.user)
	fixes, corrections_hr_scope = _part_attendance_fixes(who)
	built = (
		_part_leave_approvals(who),
		_part_goal_updates(who),
		fixes,
		_part_shift_requests(who),
		_part_policies(who),
		_part_my_requests(who),
	)
	# The order and the membership of PARTS is the contract; this proves the
	# builders above still match it rather than assuming they do.
	if tuple(p.key for p in built) != tuple(k for k, _route in PARTS):
		raise PartDefinitionError(
			"parts() built %r but PARTS names %r"
			% ([p.key for p in built], [k for k, _r in PARTS]))
	return built, corrections_hr_scope


# ── The two calls ────────────────────────────────────────────────────────────


def _refuse_guest():
	"""Guest is refused by `frappe.whitelist()` without `allow_guest`. This line
	is what still refuses if somebody ever adds it (SEC-2)."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please sign in."), frappe.PermissionError)


@frappe.whitelist()
def get_nav_counts():
	"""The frame's second and last start-up call (Wave 1 US-6, AC-7, AC-20, AC-24).

	Returns counts and nothing else - no names, no reasons, no document ids
	(PRIV-4). A number tells somebody to go and look; the screen they go to is
	where the permission checks that matter live.

	**The six parts are computed here and only here** (042 AC-38, DevOps
	OPS-W2-6). `get_home` deliberately carries no `counts` key: the frame calls
	this on every load, so a panel supplying its own badge number would be a
	second source of the one number this slice exists to make single.
	"""
	_refuse_guest()

	built, corrections_hr_scope = parts()
	counts = {p.key: p.count() for p in built}

	approvals = sum(counts[key] for key in APPROVAL_PARTS)
	total = approvals + counts["policies"] + counts["my_requests"]

	return {
		"total": total,
		"approvals_total": approvals,
		"has_employee": bool(_my_employee(frappe.session.user)),
		"parts": [
			{
				"key": p.key,
				"count": counts[p.key],
				"route": p.route,
				# The screen this row links to shows at most `cap` rows. The
				# Inbox page uses it to say "Showing the first 50 of 60" instead
				# of showing 50 and calling it the whole list (N3).
				"cap": CORRECTIONS_CAP if p.key == "attendance_fixes" else None,
				"capped": bool(p.key == "attendance_fixes"
				               and counts[p.key] > CORRECTIONS_CAP),
			}
			for p in built
		],
		"corrections_hr_scope": corrections_hr_scope,
	}


@frappe.whitelist()
def get_inbox():
	"""The Inbox screen: the same six parts, with their rows (042 US-4, AC-8 to AC-16).

	Every number here comes from `part.count()` and every row from
	`part.rows()`, on the same filter expression. `shown` is what the screen
	draws and `count` is the truth, so a capped part can say
	"Showing the first 50 of 60" rather than quietly showing fewer.

	A part with nothing in it carries `count: 0` and no rows; the screen draws
	no row for it and, when every part is empty, says "All clear." A part is
	never hidden by throwing.
	"""
	_refuse_guest()

	built, corrections_hr_scope = parts()
	out = []
	total = 0
	approvals = 0
	for p in built:
		n = p.count()
		rows = p.rows(limit=p.cap) if n else []
		total += n
		if p.key in APPROVAL_PARTS:
			approvals += n
		out.append({
			"key": p.key,
			"route": p.route,
			"count": n,
			"shown": len(rows),
			"cap": p.cap,
			"capped": n > len(rows),
			"label": p.label(n),
			"rows": rows,
		})

	return {
		"total": total,
		"approvals_total": approvals,
		"has_employee": bool(_my_employee(frappe.session.user)),
		"parts": out,
		"corrections_hr_scope": corrections_hr_scope,
	}
