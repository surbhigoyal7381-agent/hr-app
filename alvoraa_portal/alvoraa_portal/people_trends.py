"""People trends (slice 090): joiners, leavers, attendance and leave over five periods.

For a leader. Totals only: no name, no employee id, no date of a person, no reason.
A figure about a group too small to be shown is not sent at all (the key is
missing and a reason is sent), so nothing hidden can be read from the page.

The rule that hides small groups (01c section 5, parts A to D), in plain words:

  A  One filter at a time, inside one company.
  B  A figure is shown for a group only if the group has 0 people, or at least
     the minimum, in EVERY one of nine stretches of the last two years. Then it
     is shown on all five periods, or on none.
  C  Hidden siblings (including "none set", and companies under "All companies")
     must not add up to a figure that could be got by subtraction: the next
     smallest sibling is hidden too until the hidden ones together pass.
  D  Leave types are named only at the top, and only if the people who took them
     pass; the rest are called "Other".

Attendance and leave days use the same rows and the same formula as
`org_figures` (one definition of "left out" and of the rate). Nothing here writes
except the leader's chosen period.
"""

import json
import time
from collections import namedtuple
from datetime import date

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, today

from alvoraa_portal import org_figures as of
from alvoraa_portal.subscription import requires_feature

ENDPOINT = "people_trends"
ROLE = "Leadership"
# The two HR roles, as `hrms.alvoraa_hr_core.access.HR_ROLES` (the integrity check reads only
# functions and classes from that module, so the constant is not imported).
HR_ROLES = frozenset({"HR Manager", "HR User"})
PERIODS = (7, 30, 90, 180, 365)
DEFAULT_PERIOD = 90
PERIOD_KEY = "alvoraa_people_trends_period"
# Days back from the last data day. Stretch i is the dates [END - b + 1, END - a].
STRETCHES = ((0, 7), (7, 14), (14, 30), (30, 60), (60, 90), (90, 180), (180, 360), (360, 365), (365, 730))
LEAVE_STRETCHES = ((0, 7), (7, 30), (30, 90), (90, 180), (180, 365))
COHORT_STRETCHES = ((7, 30), (30, 90), (90, 180), (180, 365))
EARLY_WITHIN = (7, 30, 90)
SLOW_SECONDS = 2.0
DIMS = ("branch", "department", "employment_type")


# ── the role ─────────────────────────────────────────────────────────────────

def make_role():
	"""The Leadership role: no document permissions, and no Desk access.

	Giving it must not turn a leader into a Desk user (the 012 tests make it with
	Desk access on, which is why an existing role is corrected, as the notice
	sender's role is). Safe to run twice."""
	if frappe.db.exists("Role", ROLE):
		frappe.db.set_value("Role", ROLE, "desk_access", 0)
	else:
		frappe.get_doc({"doctype": "Role", "role_name": ROLE, "desk_access": 0}).insert()


after_migrate = make_role


# ── one call: the clock, the statement count and the one log line ────────────

class Call:
	"""Counts the statements this module sends, and writes the one line per call (SEC-9)."""

	def __init__(self):
		self.started = time.monotonic()
		self.statements = 0
		self.role_class = "none"
		self.period = None
		self.rule = None

	def sql(self, query, params=None):
		self.statements += 1
		return frappe.db.sql(query, params, as_dict=True)

	def log(self, outcome):
		"""Endpoint, user, role class, period, duration, outcome. No figure, name,
		company, branch or filter value. Through the logger that is proven to write."""
		ms = int((time.monotonic() - self.started) * 1000)
		line = {"event": ENDPOINT, "at": str(frappe.utils.now_datetime()), "user": frappe.session.user,
		        "role": self.role_class, "period": self.period, "ms": ms, "outcome": outcome,
		        "statements": self.statements}
		if self.rule:
			line["rule"] = self.rule
		try:
			from hrms.alvoraa_hr_core.access import security_logger

			log = security_logger()
			(log.warning if ms > SLOW_SECONDS * 1000 else log.info)(json.dumps(line))
		except Exception:
			pass

	def refuse(self, message, rule):
		"""A refusal: one log line (rule id only), then PermissionError."""
		self.rule = rule
		self.log("refused")
		frappe.throw(message, frappe.PermissionError)


# ── who is asking ────────────────────────────────────────────────────────────

def leader_scope(user):
	"""Companies, and the branches inside them, a Leadership user may see. None = not set up.

	From the user's Company and Branch User Permissions that apply to every record
	type or to Employee. A permission narrowed to another record type grants
	nothing, and a narrowed Branch permission means "not set up" rather than
	"the whole company" (SQ-3). A branch counts only together with its company.
	"""
	from frappe.core.doctype.user_permission.user_permission import get_user_permissions

	perms = get_user_permissions(user)

	def usable(p):
		return bool(p.get("doc")) and p.get("applicable_for") in (None, "", "Employee")

	companies = sorted({p["doc"] for p in perms.get("Company", []) if usable(p)})
	if not companies:
		return None
	branch_rows = perms.get("Branch", [])
	if any(p.get("doc") and not usable(p) for p in branch_rows):
		return None
	branches = sorted({p["doc"] for p in branch_rows if usable(p)})
	return of.Scope(tuple(companies), tuple(branches) if branches else None)


def _caller(call):
	"""(scope, own employee record or None). Refuses anyone who may not open the page.

	Worked out on every call and never cached (SEC-6). HR roles are off in the
	first release (BQ-2), including a person who holds an HR role and Leadership.
	"""
	user = frappe.session.user
	if user == "Guest":
		call.refuse(_("Sign in to see People trends."), "PT-GUEST")
	roles = set(frappe.get_roles(user))
	if user == "Administrator":
		call.role_class = "admin"
		return of.Scope(tuple(frappe.get_all("Company", pluck="name", order_by="name asc")), None), None
	if ROLE not in roles:
		call.refuse(_("You do not have access to People trends."), "PT-ROLE")
	if roles & HR_ROLES:
		call.refuse(_("People trends is not open to HR roles yet."), "PT-HR-OFF")
	call.role_class = "leadership"

	mine = frappe.get_all("Employee", filters={"user_id": user},
	                      fields=["name", "status", "company", "branch", "department", "employment_type",
	                              "date_of_joining", "relieving_date"], limit_page_length=5)
	if mine and not any(r.status == "Active" for r in mine):
		call.refuse(_("People trends is not open to a former employee."), "PT-LEFT")
	own = next((r for r in mine if r.status == "Active"), None)
	return leader_scope(user), own


# ── dates ────────────────────────────────────────────────────────────────────

def _end():
	"""The last complete day, worked out once per call (BQ-3)."""
	return add_days(getdate(today()), -1)


def _stretch_dates(end, a, b):
	return add_days(end, -b + 1), add_days(end, -a)


def _bin_lengths(days):
	"""Bins counted back from the last data day, oldest first. They sum to `days`."""
	return {7: [1] * 7, 30: [8, 8, 7, 7], 90: [6] + [7] * 12, 180: [30] * 6, 365: [31] * 5 + [30] * 7}[days]


def _bins(end, days, start):
	"""(first day, last day) of each bin inside [start, end], oldest first."""
	out, cursor = [], add_days(end, -days)
	for length in _bin_lengths(days):
		first, last = add_days(cursor, 1), add_days(cursor, length)
		cursor = last
		first = max(first, start)
		if first <= last:
			out.append((first, last))
	return out


# ── the people, as grouped rows ──────────────────────────────────────────────

Unit = namedtuple("Unit", "key w company branch department employment_type mask")
Person = namedtuple("Person", "company branch department employment_type status joined relieved n")


def _norm(v):
	return v or None


def _people(call, scope):
	"""Employee rows grouped by everything the page needs and nothing that names a person.

	One query. Rows are combinations of company, branch, department, type, status
	and the two dates, with a count: they grow with distinct combinations, never
	into names or ids."""
	where, params = of.employee_condition(scope)
	rows = call.sql(f"""
		select e.company, e.branch, e.department, e.employment_type, e.status,
		       e.date_of_joining as joined, e.relieving_date as relieved, count(*) as n
		from `tabEmployee` e
		where {where}
		group by e.company, e.branch, e.department, e.employment_type, e.status,
		         e.date_of_joining, e.relieving_date
	""", params)
	return [Person(r.company, _norm(r.branch), _norm(r.department), _norm(r.employment_type),
	               r.status, r.joined and getdate(r.joined), r.relieved and getdate(r.relieved), cint(r.n))
	        for r in rows]


def _counted(p):
	"""Active, or Left with a relieving date that is not before the joining date."""
	if not p.joined:
		return False
	if p.status == "Active":
		return True
	return p.status == "Left" and bool(p.relieved) and p.relieved >= p.joined


def _on_roll(p, t):
	return p.joined <= t and not (p.status == "Left" and p.relieved <= t)


def _on_roll_between(p, first, last):
	"""On the roll on at least one day of [first, last]."""
	t = max(first, p.joined)
	return t <= last and not (p.status == "Left" and p.relieved <= t)


def _people_units(people, end):
	"""One unit per grouped row, with a bit for each stretch it was on the roll in."""
	spans = [_stretch_dates(end, a, b) for a, b in STRETCHES]
	out = []
	for i, p in enumerate(people):
		mask = sum(1 << k for k, (f, last) in enumerate(spans) if _on_roll_between(p, f, last))
		out.append(Unit(("p", i), p.n, p.company, p.branch, p.department, p.employment_type, mask))
	return out


def _cohort_units(people, end):
	"""Joiners by the four cohort stretches (early leavers)."""
	spans = [_stretch_dates(end, a, b) for a, b in COHORT_STRETCHES]
	out = []
	for i, p in enumerate(people):
		mask = sum(1 << k for k, (f, last) in enumerate(spans) if f <= p.joined <= last)
		if mask:
			out.append(Unit(("c", i), p.n, p.company, p.branch, p.department, p.employment_type, mask))
	return out


def _mask(own, spans, test):
	return sum(1 << k for k, (f, last) in enumerate(spans) if test(own, f, last))


# ── the small-group rule ─────────────────────────────────────────────────────

def _matcher(company=None, dim=None, value=None):
	def match(u):
		if company is not None and u.company != company:
			return False
		return dim is None or getattr(u, dim) == value
	return match


def _pop(units, match, bit, own_key=None, minus=None):
	"""Distinct people in the cut for one stretch. The caller's own record is left out
	(of the pass test only: shown totals stay exact)."""
	seen = {}
	for u in units:
		if u.mask >> bit & 1 and u.key != own_key and match(u):
			seen[u.key] = u.w
	total = sum(seen.values())
	if minus is not None and minus.mask >> bit & 1 and match(minus):
		total -= 1
	return max(total, 0)


class Rule:
	"""The hiding rule for one family of figures (people, attendance, leave types)."""

	def __init__(self, units, nbits, minimum, sizes, own_key=None, minus=None):
		self.units, self.nbits, self.minimum, self.sizes = units, nbits, minimum, sizes
		self.own_key, self.minus = own_key, minus
		self._hidden = {}

	def pops(self, match):
		return [_pop(self.units, match, b, self.own_key, self.minus) for b in range(self.nbits)]

	def passes(self, match):
		return all(p == 0 or p >= self.minimum for p in self.pops(match))

	def empty(self, match):
		return not any(self.pops(match))

	def self_reason(self, match):
		"""None when the group passes in every stretch, else "few" or "subtraction"."""
		pops = self.pops(match)
		if all(p == 0 or p >= self.minimum for p in pops):
			return None
		return "few" if 0 < pops[0] < self.minimum else "subtraction"

	def hidden(self, dim, company=None):
		"""{sibling value: reason} for the siblings along `dim` ("company" or a filter).

		Part B for each sibling, then part C: keep hiding the next smallest until
		at least two are hidden and the hidden ones together pass."""
		key = (dim, company)
		if key in self._hidden:
			return self._hidden[key]
		if dim == "company":
			values = sorted({u.company for u in self.units}, key=str)
			make = lambda v: _matcher(company=v)  # noqa: E731
		else:
			values = sorted({getattr(u, dim) for u in self.units if u.company == company}, key=lambda v: (v is None, str(v)))
			make = lambda v: _matcher(company, dim, v)  # noqa: E731
		hidden = {v: self.self_reason(make(v)) for v in values}
		hidden = {v: r for v, r in hidden.items() if r}
		if hidden:
			rest = sorted((v for v in values if v not in hidden),
			              key=lambda v: (self.sizes.get((dim, company, v), 0), str(v)))

			def together():
				return self.passes(lambda u: any(make(v)(u) for v in hidden))

			while len(hidden) < 2 or not together():
				if not rest:
					break
				hidden[rest.pop(0)] = "subtraction"
		self._hidden[key] = hidden
		return hidden

	def verdict(self, company, dim=None, value=None, several_companies=False):
		"""None when the cut is shown, else the reason it is not ("few" or "subtraction")."""
		if dim is not None:
			return self.hidden(dim, company).get(value)
		if company is None:
			return self.self_reason(lambda u: True)
		if several_companies:
			return self.hidden("company").get(company)
		return self.self_reason(_matcher(company=company))


def _sizes(people, end, companies):
	"""Headcount on the last day for every sibling, used only to order the siblings."""
	sizes = {}
	for p in people:
		if _counted(p) and _on_roll(p, end):
			for dim in DIMS:
				k = (dim, p.company, getattr(p, dim))
				sizes[k] = sizes.get(k, 0) + p.n
			k = ("company", None, p.company)
			sizes[k] = sizes.get(k, 0) + p.n
	return sizes


# ── figures from the grouped people ──────────────────────────────────────────

def _window(people, start, end):
	"""Headcount at the start and the end, joined and left, for the people given."""
	hc_end = hc_start = joined = left = 0
	before = add_days(start, -1)
	for p in people:
		if _on_roll(p, end):
			hc_end += p.n
		if _on_roll(p, before):
			hc_start += p.n
		if start <= p.joined <= end:
			joined += p.n
		if p.status == "Left" and p.joined <= p.relieved and start <= p.relieved <= end:
			left += p.n
	return {"headcount": hc_end, "headcount_start": hc_start, "joined": joined, "left": left}


def _attrition(w):
	average = (w["headcount_start"] + w["headcount"]) / 2.0
	return flt(w["left"] / average * 100.0, 1) if average else None


def _people_block(people, start, end, compare, share_left=True):
	"""The People tiles. `share_left` False drops everything worked out from Left (PRIV-7)."""
	w = _window(people, start, end)
	out = {"headcount": w["headcount"], "joined": w["joined"]}
	if share_left:
		out.update(left=w["left"], net=w["joined"] - w["left"], headcount_start=w["headcount_start"],
		           attrition=_attrition(w))
	if compare:
		c = _window(people, *compare)
		then = {"headcount": c["headcount"], "joined": c["joined"]}
		if share_left:
			then.update(left=c["left"], net=c["joined"] - c["left"], attrition=_attrition(c))
		out["before"] = then
	return out


def _early(people, start, end):
	"""Joiners who left within 1 week, 1 month, 3 months, counting only those who finished the stretch."""
	cells = []
	for within in EARLY_WITHIN:
		cutoff = add_days(end, -within)
		cohort = left = 0
		inside = 0
		for p in people:
			if not start <= p.joined <= end:
				continue
			if p.joined > cutoff:
				inside += p.n
				continue
			cohort += p.n
			if p.status == "Left" and (p.relieved - p.joined).days <= within:
				left += p.n
		cells.append({"within": within, "cohort": cohort, "left": left, "inside": inside})
	return cells


def _chart(people, bins):
	"""One point per bin. Sent whole or not at all by the caller."""
	points, net = [], 0
	for first, last in bins:
		joined = sum(p.n for p in people if first <= p.joined <= last)
		left = sum(p.n for p in people if p.status == "Left" and p.joined <= p.relieved and first <= p.relieved <= last)
		net += joined - left
		points.append({"start": str(first), "joined": joined, "left": left, "net": net})
	return points


# ── attendance and leave, from the attendance table ──────────────────────────

def _interval(prefix, edges):
	"""`interval(to_days(date), e0, e1, ...)` with the edges as parameters."""
	names = [f"{prefix}{i}" for i in range(len(edges))]
	return "interval(to_days(a.attendance_date), " + ", ".join(f"%({n})s" for n in names) + ")", dict(zip(names, edges))


def _to_days(d):
	return d.toordinal() + 365


def _attendance_bins(call, scope, company, dim, value, first, last, edges):
	"""Attendance counts per company and per bin. One query. Bin 0 is before the first edge."""
	cut_scope = of.Scope((company,), scope.branches) if company else scope
	where, params = of.condition(cut_scope, "a", "alvoraa_branch")
	join, extra = "", ""
	if dim == "branch":
		extra = " and a.alvoraa_branch = %(cut_value)s"
	elif dim in ("department", "employment_type"):
		join = "join `tabEmployee` e on e.name = a.employee"
		extra = f" and e.{dim} = %(cut_value)s"
	if dim:
		params["cut_value"] = value
	k_sql, k_params = _interval("pb", [_to_days(d) for d in edges])
	params.update(k_params)
	params.update({"first": first, "last": last})
	rows = call.sql(f"""
		select a.company, {k_sql} as k,
		       coalesce(sum(a.status = 'Present'), 0) as present,
		       coalesce(sum(a.status = 'Work From Home'), 0) as wfh,
		       coalesce(sum(a.status = 'Half Day'), 0) as half,
		       coalesce(sum(a.status = 'Absent'), 0) as absent,
		       coalesce(sum(a.status = 'On Leave'), 0) as on_leave
		from `tabAttendance` a {join}
		where a.docstatus = 1 and a.attendance_date between %(first)s and %(last)s
		  and {where}{extra}
		  and not exists ({of._OPEN_DOUBTFUL})
		group by a.company, k
	""", params)
	return [{"company": r.company, "k": cint(r.k), **{f: cint(r[f]) for f in ("present", "wfh", "half", "absent", "on_leave")}}
	        for r in rows]


def _sum_counts(rows):
	return {f: sum(r[f] for r in rows) for f in ("present", "wfh", "half", "absent", "on_leave")}


def _absent_pct(counts):
	rate = of.rate(counts)
	return None if rate is None else flt(100 - rate, 1)


def _leave_units(call, scope, end):
	"""On Leave rows per person, leave type and stretch (five stretches). One query."""
	where, params = of.condition(scope, "a", "alvoraa_branch")
	edges = [_to_days(_stretch_dates(end, a, b)[0]) for a, b in reversed(LEAVE_STRETCHES)]
	k_sql, k_params = _interval("pl", edges)
	params.update(k_params)
	params.update({"first": _stretch_dates(end, 0, 365)[0], "last": end})
	rows = call.sql(f"""
		select a.employee, coalesce(a.leave_type, '') as leave_type, {k_sql} as k, count(*) as days
		from `tabAttendance` a
		where a.docstatus = 1 and a.status = 'On Leave'
		  and a.attendance_date between %(first)s and %(last)s and {where}
		  and not exists ({of._OPEN_DOUBTFUL})
		group by a.employee, a.leave_type, k
	""", params)
	return [(r.employee, r.leave_type, len(LEAVE_STRETCHES) - cint(r.k), cint(r.days)) for r in rows]


def _leave_types(rows, days, minimum, own_key):
	"""Part D. Named types (same on every period), the rest as Other. None = total only.

	`rows` are (person, type, stretch index, days). A type is named only if the
	people who took it pass in each of the five stretches, the caller left out."""
	by_type = {}
	for person, kind, k, n in rows:
		by_type.setdefault(kind, []).append((person, k, n))

	def pops(kinds):
		out = []
		for k in range(len(LEAVE_STRETCHES)):
			out.append(len({p for kind in kinds for p, kk, _n in by_type.get(kind, ()) if kk == k and p != own_key}))
		return out

	def ok(kinds):
		return all(p == 0 or p >= minimum for p in pops(kinds))

	def window_days(kinds):
		limit = LEAVE_STRETCHES.index(next(s for s in LEAVE_STRETCHES if s[1] >= days)) if days else 0
		return sum(n for kind in kinds for _p, kk, n in by_type.get(kind, ()) if kk <= limit)

	named = [t for t in by_type if t and ok([t])]
	other = [t for t in by_type if t not in named]
	named.sort(key=lambda t: (-window_days([t]), t))
	while other and not ok(other):
		if not named:
			return None
		other.append(named.pop())
	out = [{"type": t, "days": window_days([t])} for t in named if window_days([t])]
	rest = window_days(other)
	if rest:
		out.append({"type": None, "days": rest})
	return out


def _pending(call, scope, company, dim, value):
	cut_scope = of.Scope((company,), scope.branches) if company else scope
	where, params = of.condition(cut_scope, "l", "alvoraa_branch")
	join, extra = "", ""
	if dim == "branch":
		extra = " and l.alvoraa_branch = %(cut_value)s"
	elif dim in ("department", "employment_type"):
		join = "join `tabEmployee` e on e.name = l.employee"
		extra = f" and e.{dim} = %(cut_value)s"
	if dim:
		params["cut_value"] = value
	return cint(call.sql(f"""
		select count(*) as n from `tabLeave Application` l {join}
		where l.status = 'Open' and l.docstatus = 0 and {where}{extra}
	""", params)[0].n)


# ── words ────────────────────────────────────────────────────────────────────

def _chip(d):
	return {7: _("1 week"), 30: _("1 month"), 90: _("3 months"), 180: _("6 months"), 365: _("1 year")}[d]


def _chip_before(d):
	return {7: _("the 7 days before"), 30: _("the 30 days before"), 90: _("the 3 months before"),
	        180: _("the 6 months before"), 365: _("the year before")}[d]


def _headline(period, people, early, att, leave, minimum):
	"""Built from the figures that were sent, and nothing else. A clause whose figure
	is withheld is left out (PRIV-3)."""
	parts = []
	if "net" in people:
		net = people["net"]
		move = _("up {0}").format(net) if net > 0 else _("down {0}").format(-net) if net < 0 else _("no change")
		parts.append(_("Headcount {0}, {1} in {2}.").format(people["headcount"], move, _chip(period)))
		parts.append(_("{0} joined, {1} left.").format(people["joined"], people["left"]))
	else:
		parts.append(_("Headcount {0}.").format(people["headcount"]))
		parts.append(_("Joiners and leavers are not shared for this group in this period."))
	cell = next((c for c in (early or {}).get("cells", []) if c["within"] == 30), None)
	if cell and cell["cohort"] >= minimum:
		parts.append(_("Of those who joined and have passed their first month, {0} of {1} left within it.")
		             .format(cell["left"], cell["cohort"]))
	if att.get("shared") and att.get("absent_pct") is not None:
		before = (att.get("before") or {}).get("absent_pct")
		tail = ""
		if before is not None:
			diff = flt(att["absent_pct"] - before, 1)
			tail = (_(", the same as {0}").format(_chip_before(period)) if not diff else
			        _(", {0} {1} points on {2}").format(_("up") if diff > 0 else _("down"), abs(diff), _chip_before(period)))
		parts.append(_("Absent on {0}% of expected days{1}.").format(att["absent_pct"], tail))
	if leave.get("shared"):
		top = next(iter(leave.get("types") or []), None)
		kind = f", {top['type']} {_('the most')}" if top and top["type"] else ""
		parts.append(_("{0} leave days taken{1}.").format(leave["days"], kind))
	return " ".join(parts)


# ── the endpoint ─────────────────────────────────────────────────────────────

def _no_store():
	try:
		frappe.local.response_headers.set("Cache-Control", "private, no-store")
	except Exception:
		pass


def _period(call, value):
	if value is None:
		saved = frappe.defaults.get_user_default(PERIOD_KEY)
		return cint(saved) if cint(saved) in PERIODS else DEFAULT_PERIOD
	if not str(value).isdigit() or cint(value) not in PERIODS:
		call.refuse(_("Choose one of the five periods on the page."), "PT-PERIOD")
	return cint(value)


@frappe.whitelist(methods=["POST"])
@requires_feature("analytics")
def get_people_trends(period=None, company=None, branch=None, department=None, employment_type=None):
	"""One call behind the page. See the module note for the rules."""
	call = Call()
	_no_store()
	try:
		scope, own = _caller(call)
		call.period = _period(call, period)
		if scope is None or scope.not_linked:
			call.log("not set up")
			return {"state": "not_set_up"}
		out = _build(call, scope, own, call.period, company, branch, department, employment_type)
		call.log("shown" if out["state"] == "ok" else out["state"])
		return out
	except (frappe.PermissionError, frappe.ValidationError):
		raise
	except Exception as e:
		# The type of the error only: a traceback can carry a branch name or a figure.
		frappe.log_error(title="People trends could not load", message=f"PT-LOAD {type(e).__name__}")
		call.log("error")
		frappe.throw(_("We could not load People trends. Try again. If it keeps happening, tell HR and quote Code PT-LOAD."),
		             frappe.ValidationError)


@frappe.whitelist(methods=["POST"])
def save_people_trends_period(period=None):
	"""Remember the leader's chosen period. The only thing this module writes."""
	call = Call()
	_no_store()
	_caller(call)
	call.period = _period(call, period if period is not None else "x")
	frappe.defaults.set_user_default(PERIOD_KEY, call.period)
	call.log("saved")
	return {"period": call.period}


def _build(call, scope, own, period, company, branch, department, employment_type):
	from alvoraa_portal.alvoraa_portal.doctype.alvoraa_leader_view_settings.alvoraa_leader_view_settings import (
		min_group_size,
	)

	minimum = min_group_size()
	end = _end()
	several = len(scope.companies) > 1

	people = _people(call, scope)
	if not people:
		return {"state": "no_people", "period": period}

	# ── the filters: refused, never trimmed (SEC-2) ──
	given = [(d, v) for d, v in (("branch", branch), ("department", department),
	                             ("employment_type", employment_type)) if v not in (None, "")]
	if len(given) > 1:
		call.refuse(_("Choose one filter at a time."), "PT-FILTERS")
	dim, value = given[0] if given else (None, None)
	if company in (None, ""):
		company = None if several else scope.companies[0]
		if several and dim:
			call.refuse(_("Choose a company first."), "PT-SCOPE")
	elif company not in scope.companies:
		call.refuse(_("That view is not available to you."), "PT-SCOPE")
	if dim and not any(getattr(p, dim) == value and p.company == company for p in people):
		call.refuse(_("That view is not available to you."), "PT-SCOPE")

	here = [p for p in people if company is None or p.company == company]
	counted = [p for p in here if _counted(p)]
	cut = [p for p in counted if dim is None or getattr(p, dim) == value]

	# ── windows ──
	records_start = min((p.joined for p in counted), default=end)
	start = add_days(end, -period + 1)
	clipped = start < records_start
	if clipped:
		start = records_start
	days = (end - start).days + 1
	compare = None
	if not clipped and add_days(start, -period) >= records_start:
		compare = (add_days(start, -period), add_days(start, -1))
	window = {"start": str(start), "end": str(end), "days": days, "clipped": clipped, "records_start": str(records_start),
	          "compare": {"start": str(compare[0]), "end": str(compare[1])} if compare else None}

	# ── the rule, for people ──
	units = _people_units([p for p in people if _counted(p)], end)
	counted_all = [p for p in people if _counted(p)]
	sizes = _sizes(counted_all, end, scope.companies)
	own_unit = None
	if own:
		own_p = Person(own.company, _norm(own.branch), _norm(own.department), _norm(own.employment_type), "Active",
		               own.date_of_joining and getdate(own.date_of_joining), own.relieving_date and getdate(own.relieving_date), 1)
		if _counted(own_p):
			spans = [_stretch_dates(end, a, b) for a, b in STRETCHES]
			own_unit = Unit(None, 1, own_p.company, own_p.branch, own_p.department, own_p.employment_type,
			                _mask(own_p, spans, lambda p, f, last: _on_roll_between(p, f, last)))
	rule = Rule(units, len(STRETCHES), minimum, sizes, minus=own_unit)

	filters = _filter_lists(counted if company else counted_all, rule, company, dim, here, scope)
	base = {"period": period, "window": window, "filters": filters,
	        "scope": {"company": company, "branch": branch if dim == "branch" else None,
	                  "department": department if dim == "department" else None,
	                  "employment_type": employment_type if dim == "employment_type" else None,
	                  "branches_only": scope.branches is not None, "several_companies": several}}

	match = _matcher(company, dim, value)
	if rule.empty(match):
		return {"state": "no_match", **base}
	reason = rule.verdict(company, dim, value, several)
	if reason:
		return {"state": "not_shared", "reason": reason, "minimum": minimum, **base}

	# ── people ──
	people_block = _people_block(cut, start, end, compare)
	bins = _bins(end, period, start)

	# chart: whole series or none (part B at bin level, PRIV-4)
	chart = {"shared": True, "points": _chart(cut, bins)}
	bin_rule = Rule(_bin_units(counted_all, bins), len(bins), minimum, sizes, minus=_bin_minus(own_unit, own, bins))
	if not bin_rule.passes(match):
		chart = {"shared": False, "reason": "few", "total": {"joined": people_block["joined"], "left": people_block["left"]}}

	# ── early leavers: whole company only, four stretches ──
	whole = bool(company) and dim is None and scope.branches is None
	early = {"shared": False, "reason": "whole_company_only"}
	if whole:
		c_units = _cohort_units(counted_all, end)
		c_own = None
		if own_unit:
			c_own = Unit(None, 1, own_p.company, own_p.branch, own_p.department, own_p.employment_type,
			             _mask(own_p, [_stretch_dates(end, a, b) for a, b in COHORT_STRETCHES],
			                   lambda p, f, last: f <= p.joined <= last))
		c_rule = Rule(c_units, len(COHORT_STRETCHES), minimum, {}, minus=c_own)
		if c_rule.passes(_matcher(company=company)):
			early = {"shared": True, "cells": _early(cut, start, end)}
		else:
			early = {"shared": False, "reason": "few"}

	# ── attendance and leave ──
	# The people who stand behind the attendance figures are the people on the
	# roll (OPS-28 fallback: one Employee query, not a two-year Attendance scan),
	# so attendance is shown exactly when the people figures are.
	edges = [start] + [b[0] for b in bins[1:]]
	edges = ([compare[0]] if compare else []) + edges
	first = compare[0] if compare else start
	rows = _attendance_bins(call, scope, company, dim, value, first, end, edges + [add_days(end, 1)])
	offset = 1 if compare else 0
	cur_rows = [r for r in rows if r["k"] >= offset + 1]
	cmp_rows = [r for r in rows if compare and r["k"] == 1]
	counts = _sum_counts(cur_rows)
	series = []
	for i in range(len(bins)):
		series.append(_absent_pct(_sum_counts([r for r in rows if r["k"] == offset + 1 + i])))
	left_out = sum(sum(v.values()) for v in of.open_doubtful_counts(
		of.Scope((company,), scope.branches) if company else scope, start, end).values())
	call.statements += 1
	up_to = of.data_up_to(of.Scope((company,), scope.branches) if company else scope)
	call.statements += 1 if company else len(scope.companies)
	attendance = {"shared": True, "absent_pct": _absent_pct(counts), "series": series, "left_out_days": left_out}
	if compare:
		attendance["before"] = {"absent_pct": _absent_pct(_sum_counts(cmp_rows))}

	leave = {"shared": True, "days": counts["on_leave"], "series": [
		sum(r["on_leave"] for r in rows if r["k"] == offset + 1 + i) for i in range(len(bins))],
		"pending": _pending(call, scope, company, dim, value)}
	if compare:
		leave["before"] = {"days": _sum_counts(cmp_rows)["on_leave"]}
	leave["types"] = None
	if dim is None and (company or not several):
		l_rows = _leave_units(call, of.Scope((company,), scope.branches) if company else scope, end)
		leave["types"] = _leave_types(l_rows, period, minimum, own.name if own else None)

	by_company = None
	if several and company is None and dim is None:
		by_company = _by_company(call, scope, rule, counted_all, start, end, several)

	note = _data_quality(here, dim, scope, company, minimum)
	out = {"state": "ok", **base, "data_up_to": str(up_to) if up_to else None, "people": people_block,
	       "early": early, "chart": chart, "attendance": attendance, "leave": leave,
	       "by_company": by_company, "data_quality": note, "minimum": minimum}
	out["headline"] = _headline(period, people_block, early, attendance, leave, minimum)
	return out


def _bin_units(counted, bins):
	units = []
	for i, p in enumerate(counted):
		mask = sum(1 << k for k, (f, last) in enumerate(bins) if _on_roll_between(p, f, last))
		units.append(Unit(("b", i), p.n, p.company, p.branch, p.department, p.employment_type, mask))
	return units


def _bin_minus(own_unit, own, bins):
	if not own_unit:
		return None
	p = Person(own.company, _norm(own.branch), _norm(own.department), _norm(own.employment_type), "Active",
	           getdate(own.date_of_joining), own.relieving_date and getdate(own.relieving_date), 1)
	return Unit(None, 1, p.company, p.branch, p.department, p.employment_type,
	            sum(1 << k for k, (f, last) in enumerate(bins) if _on_roll_between(p, f, last)))


def _filter_lists(counted, rule, company, dim, here, scope):
	"""What the leader may pick, from people inside the scope only (SEC-3).

	A hidden branch is listed as such. "None set" is counted but never listed."""
	def listing(name):
		if company is None:
			return []
		hidden = rule.hidden(name, company)
		values = sorted({getattr(p, name) for p in counted if p.company == company and getattr(p, name)})
		return [{"value": v, "shared": v not in hidden} for v in values]

	companies = []
	if len(scope.companies) > 1:
		hidden = rule.hidden("company")
		companies = [{"value": c, "shared": c not in hidden} for c in sorted({p.company for p in here} | set(scope.companies))
		             if c in scope.companies]
	return {"companies": companies, "branches": listing("branch"), "departments": listing("department"),
	        "employment_types": listing("employment_type")}


def _by_company(call, scope, rule, counted_all, start, end, several):
	"""One block per company, alphabetical, no ranking."""
	out = []
	for c in sorted(scope.companies):
		mine = [p for p in counted_all if p.company == c]
		if not mine:
			continue
		reason = rule.verdict(c, several_companies=several)
		if reason:
			out.append({"company": c, "shared": False, "reason": reason})
			continue
		w = _people_block(mine, start, end, None)
		block = {"company": c, "shared": True, "headcount": w["headcount"], "net": w["net"], "left": w["left"]}
		rows = _attendance_bins(call, scope, c, None, None, start, end, [start, add_days(end, 1)])
		block["absent_pct"] = _absent_pct(_sum_counts(rows))
		out.append(block)
	return out


def _data_quality(here, dim, scope, company, minimum):
	"""Leavers with no relieving date: only at the top of scope, and only 5 or more (PRIV-10)."""
	if dim is not None:
		return None
	n = sum(p.n for p in here if p.status == "Left" and not p.relieved)
	return {"no_relieving": n} if n >= minimum else None
