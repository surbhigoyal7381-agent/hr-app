"""Slice 066: the grooming red mark.

A store manager (or HR) records, on the day, that somebody came to work not in
uniform. The month's marks become one deduction line on the payslip, never more
than the legal limit, and the person is told the same day.

ONE DEFINITION OF EVERY RULE, IN THIS FILE.

  `may_mark`          who may mark whom, on which day (SEC-1, SEC-3, SEC-6,
                      SEC-7, SEC-10). The record's own controller calls it, so
                      the desk, REST, imports and the portal all meet it; every
                      screen calls the same function to decide its buttons, so a
                      button and the guard cannot disagree.
  `may_read`          who may read a mark (SEC-4). The record's has_permission
                      and permission_query_conditions hooks are built on it, and
                      so are the screens.
  `flag_for`          "Grooming review pending", worked out from the marks and
                      the review record, never stored.

Nothing here uses `ignore_permissions` (SEC-12). The mark is created, submitted,
cancelled and updated as the signed-in user: the DocPerm gives the right and the
controller narrows it. The few reads that do not run under the caller's own
permission are named where they happen - each answers a rule about ONE subject
and returns a yes, a no or a date, never another person's mark.

Logs carry document names and rule codes only (PRIV-7): `refuse()` writes the
security log, and a failed notice names the mark and nothing else.
"""

import calendar
import json
import re

import frappe
from frappe import _
from frappe.utils import add_months, cint, flt, get_first_day, get_last_day, getdate, now_datetime, nowdate
from frappe.utils.caching import request_cache

import hrms.alvoraa_hr_core.access as access
from alvoraa_portal.payroll_rules_apply import rule_set_for

MARK = "Grooming Mark"
REVIEW = "Grooming Review"

# SEC-11. Clothing only, and fixed in code: the controller accepts nothing else,
# so an option added in Customize Form is refused, not offered. The Select
# options on the doctype equal this tuple (a test says so). Changing it is a
# code change with Surbhi's and counsel's approval recorded in the slice folder.
REASONS = ("Not in uniform", "Uniform incomplete", "No name badge", "Wrong footwear", "Other")

# "Other" (Surbhi, 24 Oct 2026): the marker types a short reason of their own.
# Kept on the mark only - never in a notice, the Inbox or a report, which say
# the fixed word "Other". Words that are about a person rather than their
# clothes are refused; the list is a floor, not a filter that makes free text
# safe, and it goes to the security review and counsel with the slice.
OTHER = "Other"
OTHER_MAX = 100
OTHER_HINT = "Clothing or grooming only. Nothing about health or family."
#
# THE ONE LIST (architect review M-4, 25 Oct 2026). Used by the "Other" check
# below AND by the test that pins the fixed reasons, so the two cannot drift.
# It refuses words that put SENSITIVE INFORMATION about a person on a fine -
# religion and the marks of a religion, caste, race, health, disability,
# pregnancy, family, gender and sexuality. It does NOT refuse clothing or
# grooming words (dirty, head, hair, beard, jewellery): a grooming red is about
# how someone came to work, and Surbhi accepted the free text for that.
# An entry ending in "*" matches any word starting with it; the rest match
# whole words only. It is a floor, not a control. COUNSEL TO REVIEW the list.
NOT_ABOUT_CLOTHES = (
	# religion, and items that name a religion
	"religio*", "hindu*", "muslim*", "islam*", "sikh*", "christian*", "jain*", "buddhis*",
	"parsi*", "jew", "jews", "jewish", "god", "gods", "puja", "namaz", "prayer*",
	"temple*", "mosque*", "church*", "gurdwara*", "fasting", "roza", "ramzan*",
	"ramadan*", "navratri*", "turban*", "pagdi*", "pagri*", "patka*", "hijab*", "burqa*",
	"burka*", "niqab*", "tilak*", "bindi*", "sindoor*", "kara", "kada", "mangalsutra*",
	"rudraksh*", "janeu*",
	# caste, race, region
	"caste*", "dalit*", "brahmin*", "race", "racial*", "ethnic*", "tribe*", "tribal*",
	# health, disability, pregnancy
	"health*", "sick*", "illness*", "disease*", "medical*", "medicine*", "doctor*",
	"hospital*", "injur*", "disab*", "handicap*", "blind*", "deaf*", "pregnan*",
	"period", "periods", "menstru*", "mental*", "depress*", "diabet*", "allerg*",
	# family and relationships
	"family", "families", "husband*", "wife", "wives", "child*", "kids", "mother*",
	"father*", "marri*", "divorc*", "widow*",
	# gender and sexuality
	"gender*", "sex", "sexual*", "transgender*", "gay", "lesbian*",
)
_NOT_ABOUT_CLOTHES_RE = re.compile(r"\b(?:" + "|".join(
	w[:-1] + r"\w*" if w.endswith("*") else w + r"\b" for w in NOT_ABOUT_CLOTHES) + ")")


def about_the_person(text):
	"""True when the text names something about the person, not their clothes."""
	return bool(_NOT_ABOUT_CLOTHES_RE.search(str(text or "").lower()))


def clean_other(text):
	"""The typed reason, tidied, or a refusal saying what to do next."""
	text = " ".join(str(text or "").split())
	if not text:
		frappe.throw(_("Write what was wrong first."))
	if len(text) > OTHER_MAX:
		frappe.throw(_("Keep your reason to {0} characters.").format(OTHER_MAX))
	if about_the_person(text):
		frappe.throw(_("Keep the reason to clothing or grooming. Nothing about health, family, "
		               "religion or the person's body."))
	return text


def reason_words(m):
	"""How a mark's reason reads on a screen that may read the mark."""
	if m.reason == OTHER and m.get("other_reason"):
		return _("Other: {0}").format(m.other_reason)
	return _(m.reason)

# PRIV-3. Why a mark was withdrawn. A manager's undo has no sheet, so it is
# always the first one.
REMOVAL_REASONS = ("Marked by mistake", "Marked on the wrong person",
                   "The employee showed it was wrong")
UNDO_REASON = REMOVAL_REASONS[0]

# At most 3 live marks per person per calendar month, for everyone; the
# review flag rises at the 3rd, and the manager is told no more can be marked
# (Surbhi, 24 Oct 2026). The legal limit below stays as a backstop: a Senior
# at 3 x Rs 200 passes 3% of a Basic under Rs 20,000, so for them the stop and
# the flag come at the mark after which one more would pass it.
MONTH_MAX = 3

# SEC-10, interim until counsel says what "wages payable" is (Q-C1): fines in a
# month may not pass 3% of the wages. The stop uses the full monthly Basic; the
# back-stop on the slip uses the month's earned Basic (payroll_month).
LIMIT_SHARE = 0.03

# The slip line the month's grooming total goes on (payroll_slip.ENGINE_LINES).
COMPONENT = "Grooming Red Value"


@request_cache
def is_on():
	"""Grooming's own switch (pre-push review P-1; Surbhi, 25 Oct 2026, option 2).

	On only while the "Grooming Red Value" Salary Component exists and its
	Disabled box is clear. Missing or disabled means off: no screens, no new
	marks, no changes to old ones, no slip line, no notices, no flag. Old marks
	are kept and stay readable. The payroll rule set prices the marks but never
	switches grooming on by itself. One read per request.
	"""
	disabled = frappe.db.get_value("Salary Component", COMPONENT, "disabled")
	return disabled is not None and not cint(disabled)


def refuse_if_off(doc, where):
	"""Old marks and reviews stay as they are while grooming is off."""
	if not is_on():
		access.refuse(_("Grooming reds are switched off, so nothing on them can be changed now."),
		              "R1", where, doc.doctype, doc.name)


# ── small things ─────────────────────────────────────────────────────────────

def _day(d):
	"""'Sat 24 Oct' - the way every screen and notice names a day."""
	d = getdate(d)
	return "{0} {1} {2}".format(_(d.strftime("%a")), d.day, _(d.strftime("%b")))


def _month_name(d):
	return _(calendar.month_name[getdate(d).month])


def _rupees(amount):
	"""'₹1,000', Indian grouping, no paise (every figure here is whole rupees)."""
	n = int(round(flt(amount)))
	s, neg = str(abs(n)), n < 0
	if len(s) > 3:
		head, tail = s[:-3], s[-3:]
		groups = []
		while len(head) > 2:
			groups.insert(0, head[-2:])
			head = head[:-2]
		if head:
			groups.insert(0, head)
		s = ",".join(groups + [tail])
	return ("-" if neg else "") + "₹" + s


def _first(row):
	return (row.get("first_name") or (row.get("employee_name") or "").split(" ")[0]
	        or row.get("name"))


def _active_employee(user):
	"""The caller's own Active Employee id, or None."""
	return frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")


def _limit(base):
	return flt(LIMIT_SHARE * flt(base), 2)


def _month_bounds(d):
	d = getdate(d)
	return getdate(get_first_day(d)), getdate(get_last_day(d))


def _rate(rule_set, emp):
	"""(rupees per mark, earns marks, grade) for one employee under a rule set.

	The same rule set fields the engine reads (`grade_field`, `category_field`,
	`mark_rates`, the category's `earns_marks`), never the word "Contract" in
	code. An unlisted category earns marks, as in `payroll_slip.month_summary`.
	"""
	grade = str(emp.get("_grade") or "").strip()
	category = str(emp.get("_category") or "").strip().lower()
	cat = next((c for c in rule_set.categories
	            if (c.category or "").strip().lower() == category), None)
	rate = next((r for r in rule_set.mark_rates if (r.grade or "").strip() == grade), None)
	return flt(rate.amount_per_mark if rate else 0), bool(cat.earns_marks if cat else True), grade


def _with_rule_fields(rows, rule_sets):
	"""Put each employee's grade and category on its row, read through the
	fields its own company's rule set names. One query for the lot."""
	fields = set()
	for rs in rule_sets.values():
		if rs:
			fields |= {f for f in (rs.grade_field, rs.category_field) if f}
	values = {}
	if fields and rows:
		for r in frappe.get_all("Employee", filters={"name": ("in", [r.name for r in rows])},
		                        fields=["name"] + sorted(fields)):
			values[r.name] = r
	for r in rows:
		rs = rule_sets.get(r.company)
		v = values.get(r.name, {})
		r._grade = v.get(rs.grade_field) if rs and rs.grade_field else None
		r._category = v.get(rs.category_field) if rs and rs.category_field else None
	return rows


SUBJECT_FIELDS = ["name", "employee_name", "first_name", "status", "date_of_joining",
                  "company", "reports_to", "user_id"]


def _subjects(employees):
	rows = frappe.get_all("Employee", filters={"name": ("in", list(employees) or [""])},
	                      fields=SUBJECT_FIELDS)
	# With grooming off no company has a rule set here, so every rule (R1), the
	# Today card, the month, the flag and the pending report all say "off".
	on = is_on()
	rule_sets = {c: rule_set_for(c) if on else None for c in {r.company for r in rows}}
	return {r.name: r for r in _with_rule_fields(rows, rule_sets)}, rule_sets


# ── who is HR for whom ───────────────────────────────────────────────────────

def hr_scope(user, employees):
	"""Of these employees, the ones this user may act on as HR. Fails closed.

	HR means: holds HR Manager or HR User (System Manager alone is NOT HR -
	`permitted_employees` gives a System Manager everyone, so the role check is
	what keeps the owner out, Q3), the subject is inside `permitted_employees`,
	and, if the login is linked to an Employee, that Employee is Active. An owner
	who also holds an HR role counts as HR (D7). One query, or none.
	"""
	employees = [e for e in employees if e]
	if not employees or not (access.HR_ROLES & set(frappe.get_roles(user))):
		return set()
	linked = frappe.get_all("Employee", filters={"user_id": user}, pluck="status")
	if linked and "Active" not in linked:
		return set()
	filters = access.permitted_employee_filters(user)
	if filters.get("name") == ["in", []]:
		return set()
	where = [["Employee", k, v[0], v[1]] if isinstance(v, (list, tuple)) else ["Employee", k, "=", v]
	         for k, v in filters.items()]
	where.append(["Employee", "name", "in", employees])
	return set(frappe.get_all("Employee", filters=where, pluck="name"))


def _hr_sql(user):
	"""HR's reach as one SQL condition on an `employee` column, or None.

	The same rules as `hr_scope`, written as a sub-query so a list of 445 names
	is never sent back as IN (...). Values go through frappe.db.escape.
	"""
	if not (access.HR_ROLES & set(frappe.get_roles(user))):
		return None
	linked = frappe.get_all("Employee", filters={"user_id": user}, pluck="status")
	if linked and "Active" not in linked:
		return None
	filters = access.permitted_employee_filters(user)
	if filters.get("name") == ["in", []]:
		return None
	if filters.get("name") == ["!=", ""]:
		return "1=1"
	esc = frappe.db.escape
	parts = []
	for key in ("company", "branch"):
		if key in filters:
			parts.append("`{0}` in ({1})".format(
				key, ", ".join(esc(v) for v in filters[key][1]) or "''"))
	return "employee in (select name from `tabEmployee` where {0})".format(
		" and ".join(parts) or "1=0")


# ── the facts the rules need, read once for many people ─────────────────────

def _facts(employees, from_date, to_date, user, locking=False):
	"""Everything `_decide` reads, for these people over these days, in a flat
	number of queries (about eleven whether it is 1 person or 60).

	Reads that do not run under the caller's permission, by design: the rules
	need the subject's punches, leave, slips, marks and Basic, which a manager
	may not read. Nothing from here leaves the server except a yes, a no and
	the refusal sentence.
	"""
	f = frappe._dict(user=user, today=getdate(nowdate()))
	f.subjects, f.rule_sets = _subjects(employees)
	ids = list(f.subjects) or [""]
	f.me = _active_employee(user)
	f.hr = hr_scope(user, ids)
	m_from, _end = _month_bounds(from_date)
	_start, m_to = _month_bounds(to_date)

	users = [s.user_id for s in f.subjects.values() if s.user_id]
	f.enabled = set(frappe.get_all("User", filters={"name": ("in", users or [""]), "enabled": 1},
	                               pluck="name"))

	f.punches = {}
	for p in frappe.get_all("Employee Checkin",
	                        filters={"employee": ("in", ids),
	                                 "time": ("between", [str(from_date) + " 00:00:00",
	                                                      str(to_date) + " 23:59:59"])},
	                        fields=["employee", "time"], order_by="time asc"):
		f.punches.setdefault((p.employee, str(p.time)[:10]), str(p.time)[11:16])

	f.leave = {(a.employee, str(a.attendance_date)): a.leave_type for a in frappe.get_all(
		"Attendance", filters={"employee": ("in", ids), "docstatus": 1, "status": "On Leave",
		                       "attendance_date": ("between", [from_date, to_date])},
		fields=["employee", "attendance_date", "leave_type"])}

	f.slips = frappe.get_all("Salary Slip",
	                         filters={"employee": ("in", ids), "docstatus": 1,
	                                  "start_date": ("<=", to_date), "end_date": (">=", from_date)},
	                         fields=["employee", "start_date", "end_date"])

	# `locking` when the record itself is being saved (security M1, second
	# look): a locking read sees every COMMITTED mark, not the snapshot MariaDB
	# froze at this transaction's first read - which was taken before the
	# person's row lock was granted, so a mark committed while we waited was
	# invisible and a 4th got through.
	f.marks = frappe.db.get_values(MARK, {"employee": ("in", ids), "docstatus": ("<", 2),
	                                      "mark_date": ("between", [m_from, m_to])},
	                               ["name", "employee", "mark_date", "docstatus"], as_dict=True,
	                               for_update=locking)

	f.bases = {}
	for a in frappe.get_all("Salary Structure Assignment",
	                        filters={"employee": ("in", ids), "docstatus": 1,
	                                 "from_date": ("<=", m_to)},
	                        fields=["employee", "base", "from_date"], order_by="from_date asc"):
		f.bases.setdefault(a.employee, []).append(a)
	return f


def _base_on(f, employee, month_end):
	"""The latest submitted assignment's Basic with from_date <= month end (the
	query `payroll_slip.month_summary` uses). None means nothing to price on."""
	base = 0
	for a in f.bases.get(employee, []):
		if getdate(a.from_date) <= getdate(month_end):
			base = flt(a.base)
	return base


def _closed_by(slips, employee, d):
	"""The submitted slip that covers this day, or None."""
	d = getdate(d)
	return next((s for s in slips if s.employee == employee
	             and getdate(s.start_date) <= d <= getdate(s.end_date)), None)


def _no(code, message, **extra):
	return frappe._dict(ok=False, code=code, message=message, **extra)


def _decide(f, employee, d, told_in_person=None, exclude=None):
	"""R1-R13 of the spec, in the order a refusal should be explained.

	Capacity is settled BEFORE anything about the person is said, so somebody
	with no business here learns nothing - not even that a colleague is Contract.
	`told_in_person` is None when a screen asks (the tick is the sheet's), and
	the stored value when the record is saved (R13).
	"""
	d = getdate(d)
	s = f.subjects.get(employee)
	if not s:
		return _no("R3", _("No such employee."))
	first = _first(s)
	rs = f.rule_sets.get(s.company)
	if not rs:
		return _no("R1", _("Grooming reds are not switched on for this company."))
	if f.user == "Administrator" or s.user_id == f.user or (f.me and f.me == employee):
		return _no("R2", _("You cannot mark yourself."))

	if f.me and s.reports_to == f.me:
		capacity = "Manager"
	elif employee in f.hr:
		capacity = "HR"
	else:
		return _no("R6", _("Only {0}'s current manager or HR can mark {0}.").format(first))
	hr = capacity == "HR"
	out = dict(capacity=capacity, first=first)

	if s.status != "Active" or (s.date_of_joining and d < getdate(s.date_of_joining)):
		return _no("R3", _("{0} is not an active employee on this day.").format(
			s.employee_name or first), **out)

	rate, earns, grade = _rate(rs, s)
	if not earns:
		return _no("R4", _("{0} is Contract staff. Contract staff are not given grooming reds, "
		                   "so there is nothing to mark.").format(first) if hr
		           else _("Contract staff are not given grooming reds."), **out)

	slip = _closed_by(f.slips, employee, d)
	if slip:
		month = _month_name(slip.start_date)
		return _no("R11", _("{0}'s pay slip for {1} is submitted, so grooming reds for {1} are "
		                    "closed. They cannot be added or removed now.").format(first, month), **out)

	m_start, m_end = _month_bounds(d)
	if not hr and d != f.today:
		return _no("R7", _("A manager can mark only today."), **out)
	if d > f.today:
		return _no("R7", _("A day still to come cannot be marked."), **out)
	if d < getdate(get_first_day(f.today)):
		month = _month_name(d)
		return _no("R7", _("Marks can be added only for days in this month. A {0} mark that already "
		                   "exists can still be removed until {0}'s pay slip is submitted.").format(month),
		           **out)

	if rate <= 0:
		return _no("R5", _("{0}'s grade is not set, so a grooming red would cost nothing and cannot "
		                   "be marked. Set {0}'s grade on {0}'s employee record first.").format(first) if hr
		           else _("{0}'s grade is not set, so a grooming red cannot be priced. Ask HR to "
		                  "set it.").format(first), **out)

	leave = f.leave.get((employee, str(d)))
	if leave:
		return _no("R9", _("{0} was on leave all day ({1}), so there is nothing to mark.").format(
			first, leave) if hr else _("{0} was on leave all day, so there is nothing to mark.").format(first),
			**out)
	if (employee, str(d)) not in f.punches:
		return _no("R8", _("{0} has no punch on this day, so there is nothing to mark. A grooming "
		                   "red is only for a day somebody came to work.").format(first), **out)

	if any(m.employee == employee and getdate(m.mark_date) == d and m.name != exclude for m in f.marks):
		return _no("R10", _("{0} already has a grooming red today.").format(first) if d == f.today
		           else _("{0} already has a grooming red on this day.").format(first), **out)

	live = len({getdate(m.mark_date) for m in f.marks if m.employee == employee
	            and m.docstatus == 1 and m.name != exclude and m_start <= getdate(m.mark_date) <= m_end})
	base = _base_on(f, employee, m_end)
	limit = _limit(base)
	# The manager's warning ends by offering "Raise it with HR" (may_raise),
	# which asks for a conversation and never for a 4th mark - HR included.
	warn = " " + _("HR has been told and will talk to {0}. If it carries on, you can raise it "
	               "with HR.").format(first)
	if live >= MONTH_MAX:
		if hr:
			return _no("R12", _("{0} has had 3 grooming reds this month, the most allowed, so no "
			                    "more can be marked.").format(first), **out)
		stop = _("{0} has had 3 grooming reds this month, the most allowed.").format(first)
		return _no("R12", stop + warn, stop=stop, **out)
	if (live + 1) * rate > limit:
		stop = _("{0} has reached the most grooming reds the law allows this month, so this one "
		         "cannot be marked.").format(first)
		if hr:
			return _no("R12", stop + " " + _("(limit {0} = 3% of Basic {1})").format(
				_rupees(limit), _rupees(base)), **out)
		return _no("R12", stop + warn, stop=stop, **out)

	has_login = bool(s.user_id and s.user_id in f.enabled and s.status == "Active")
	if told_in_person is not None and not has_login and not cint(told_in_person):
		return _no("R13", _("Tick the box to confirm you told {0} in person.").format(first), **out)

	return frappe._dict(ok=True, code=None, message=None, has_login=has_login,
	                    rate=rate, grade=grade, live=live, limit=limit, base=base, **out)


def may_mark(employee, date, user=None, told_in_person=None, exclude=None, locking=False):
	"""May `user` mark `employee` for `date`? The only definition (SEC-1).

	Returns a dict: `ok`, `capacity` ("Manager" or "HR") when there is one,
	`code` and `message` when refused, and `has_login` when allowed.
	"""
	user = user or frappe.session.user
	f = _facts([employee], date, date, user, locking=locking)
	return _decide(f, employee, date, told_in_person=told_in_person, exclude=exclude)


# ── who may read a mark (SEC-4) ──────────────────────────────────────────────

def may_read(doc, user=None):
	"""Subject, marker, current direct manager on the day, or HR in scope.
	Anybody else: no."""
	user = user or frappe.session.user
	me = _active_employee(user)
	# The marker reads their own marks only while they are an Active employee:
	# ERPNext keeps a leaver's login enabled (security verification M2). HR who
	# are not on the payroll still read through hr_scope below.
	if me and doc.get("owner") == user:
		return True
	if me and doc.employee == me:
		return True
	if me and getdate(doc.mark_date) == getdate(nowdate()) and frappe.db.get_value(
			"Employee", doc.employee, "reports_to") == me:
		return True
	return doc.employee in hr_scope(user, [doc.employee])


def mark_has_permission(doc, ptype=None, user=None):
	"""has_permission hook. A hook can only deny, never grant beyond DocPerm.

	Create is the controller's to decide (`may_mark`), because a new mark has
	no reader yet. Everything else - read, write, submit, cancel - starts with
	the read gate, so nobody can even attempt an action on a mark they cannot
	see.
	"""
	if ptype == "create":
		return True
	if may_read(doc, user):
		return True
	# "Raise it with HR" writes three fields on the mark that reached the limit,
	# which the manager may not be able to read (HR made it on another day).
	# Only `raise_with_hr` sets this flag - it lives on the document object in
	# memory, so no REST, client or form call can set it - and that endpoint
	# returns the mark's name and nothing else. Every other door, including an
	# empty save through set_value or PUT, meets the read gate above
	# (security verification B1).
	if ptype in ("write", "submit") and doc.flags.get(RAISE_FLAG):
		me = _active_employee(user or frappe.session.user)
		return bool(me and frappe.db.get_value("Employee", doc.employee, "reports_to") == me)
	return False


RAISE_FLAG = "grooming_raise_with_hr"


def mark_query_conditions(user=None):
	"""permission_query_conditions hook: the same gate, as SQL. Never empty
	for a tenant user - with no reach it matches no rows."""
	user = user or frappe.session.user
	if user == "Administrator":
		return ""
	esc = frappe.db.escape
	me = _active_employee(user)
	conds = ["1=0"]
	if me:
		conds.append("`tabGrooming Mark`.owner = {0}".format(esc(user)))
		conds.append("`tabGrooming Mark`.employee = {0}".format(esc(me)))
		conds.append("(`tabGrooming Mark`.mark_date = {0} and `tabGrooming Mark`.employee in "
		             "(select name from `tabEmployee` where reports_to = {1}))".format(
		                 esc(nowdate()), esc(me)))
	hr = _hr_sql(user)
	if hr:
		conds.append("`tabGrooming Mark`." + hr if hr != "1=1" else hr)
	return "(" + " or ".join(conds) + ")"


def review_has_permission(doc, ptype=None, user=None):
	"""HR in scope, and the person's current Active direct manager (Surbhi,
	24 Oct 2026: shown to the manager, as prototype v2 draws it). Never the
	subject. Create is the controller's; nobody has write or delete."""
	if ptype == "create":
		return True
	user = user or frappe.session.user
	me = _active_employee(user)
	if me == doc.employee:
		return False
	if me and frappe.db.get_value("Employee", doc.employee, "reports_to") == me:
		return True
	return doc.employee in hr_scope(user, [doc.employee])


def review_query_conditions(user=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return ""
	esc = frappe.db.escape
	me = _active_employee(user)
	conds = []
	hr = _hr_sql(user)
	if hr:
		conds.append("`tabGrooming Review`." + hr if hr != "1=1" else hr)
	if me:
		# The current direct manager reads the review of their own reports.
		conds.append("`tabGrooming Review`.employee in (select name from `tabEmployee` where "
		             "reports_to = {0})".format(esc(me)))
	if not conds:
		return "1=0"
	cond = "(" + " or ".join(conds) + ")"
	if me:
		cond = "({0} and `tabGrooming Review`.employee != {1})".format(cond, esc(me))
	return cond


def refuse_side_record(doc, method=None):
	"""doc_events validate on Comment, ToDo, DocShare, File and Tag Link (SEC-8):
	no comment, assignment, share, attachment or tag on a mark or a review, on
	any door. Files and tags added 25 Oct 2026 (security verification B2): a
	file can be public and a tag is free text the whole site sees.

	Frappe's assign_to will create a ToDo - and share the record - even for
	somebody who cannot read it (seen on the bench, 24 Oct 2026), so DocPerm
	alone does not stop it. One name comparison for every other row.
	"""
	ref = {"Comment": "reference_doctype", "ToDo": "reference_type", "DocShare": "share_doctype",
	       "File": "attached_to_doctype", "Tag Link": "document_type"}.get(doc.doctype)
	if ref and doc.get(ref) in (MARK, REVIEW):
		frappe.throw(_("A grooming red or a grooming review cannot be commented on, assigned, "
		               "shared, tagged or have files attached."), frappe.PermissionError)


# ── the review flag (US-14) ──────────────────────────────────────────────────

def _raise_point(dated, rate, base):
	"""Given live marks as (date, creation) in the order they were made, the
	mark that raised the flag: (count, creation, "max" or "limit"), or None.

	Raised at the 3rd live mark (the most allowed), or earlier at the mark
	after which one more would pass the legal limit - the mark after which no
	more can be made, whichever way.
	"""
	limit = _limit(base)
	for k, (_d, creation) in enumerate(dated, 1):
		if k >= MONTH_MAX:
			return k, creation, "max"
		if (k + 1) * rate > limit:
			return k, creation, "limit"
	return None


def _live_dated(marks):
	"""Distinct dates, each at the moment its first live mark was made."""
	first = {}
	for m in sorted(marks, key=lambda m: m.creation):
		first.setdefault(getdate(m.mark_date), m.creation)
	return sorted(first.items(), key=lambda kv: kv[1])


def _live_raise(raises, subject):
	"""The month's manager raise, if it still stands: the person is Active and
	the manager who raised it is still their manager (brief, Decisions (3))."""
	r = raises[0] if raises else None
	if not r or not subject or subject.status != "Active" or not subject.reports_to:
		return None
	manager_user = frappe.db.get_value("Employee", subject.reports_to, "user_id")
	return r if manager_user == r.raised_by else None


def flag_for(employee, month_start, rate, base, with_note=False):
	"""The review flag for one person and one calendar month, or None.

	Worked out, never stored. It rises at the mark that reaches the 3-mark
	limit or the legal limit, whichever comes first. A Grooming Review clears
	it; it never rises again from marks that month. A manager's "Raise it with
	HR" (one a month) puts it back to pending until HR records a review after
	the raise. Read with get_all after the caller passed the read gate - only a
	state, dates and (for HR) the note and the raise reason leave here.
	"""
	start, end = _month_bounds(month_start)
	marks = frappe.get_all(MARK, filters={"employee": employee, "docstatus": 1,
	                                      "mark_date": ("between", [start, end])},
	                       fields=["mark_date", "creation", "owner", "raised_on", "raised_by",
	                               "raised_reason"])
	fields = ["creation", "owner"] + (["review_note"] if with_note else [])
	reviews = frappe.get_all(REVIEW, filters={"employee": employee, "review_month": start},
	                         fields=fields, order_by="creation asc")
	dated = _live_dated(marks)
	out = frappe._dict(month=start, live=len(dated), owners={m.owner for m in marks},
	                   limit=_limit(base), base=base, rate=rate)
	subject = frappe.db.get_value("Employee", employee, ["status", "reports_to"], as_dict=True)
	raise_ = _live_raise(sorted([m for m in marks if m.raised_on], key=lambda m: m.raised_on),
	                     subject)
	answered = bool(raise_) and any(r.creation > raise_.raised_on for r in reviews)
	if raise_:
		out.update(raise_on=raise_.raised_on, raise_by=raise_.raised_by,
		           raise_reason=raise_.raised_reason)
	if raise_ and not answered:
		out.update(state="pending", why="raised", count=len(dated), raised_on=raise_.raised_on)
		return out
	if reviews:
		out.update(state="cleared", review=reviews[-1])
		return out
	point = _raise_point(dated, rate, base)
	if not point:
		return None
	out.update(state="pending", count=point[0], raised_on=point[1], why=point[2])
	return out


def pending_reviews(user, month_start):
	"""Every person in this HR user's scope whose review is pending in a month,
	oldest first - from the marks, or from a manager's raise not yet answered.

	For the "Grooming review pending" report and the Inbox. Flat: one query
	each for scope, marks, reviews, people, their managers and Basic, whatever
	the headcount.
	"""
	start, end = _month_bounds(month_start)
	if not _hr_sql(user):
		return []
	marks = frappe.get_all(MARK, filters={"docstatus": 1, "mark_date": ("between", [start, end])},
	                       fields=["employee", "mark_date", "creation", "raised_on", "raised_by"])
	if not marks:
		return []
	people = {m.employee for m in marks}
	scope = hr_scope(user, list(people))
	me = _active_employee(user)
	people = {p for p in people if p in scope and p != me}
	if not people:
		return []
	reviews = {}
	for r in frappe.get_all(REVIEW, filters={"employee": ("in", list(people)), "review_month": start},
	                        fields=["employee", "creation"]):
		reviews.setdefault(r.employee, []).append(r.creation)
	subjects, rule_sets = _subjects(people)
	managers = {e.name: e.user_id for e in frappe.get_all(
		"Employee", filters={"name": ("in", [s.reports_to for s in subjects.values()
		                                     if s.reports_to] or [""])}, fields=["name", "user_id"])}
	bases = {}
	for a in frappe.get_all("Salary Structure Assignment",
	                        filters={"employee": ("in", list(people) or [""]), "docstatus": 1,
	                                 "from_date": ("<=", end)},
	                        fields=["employee", "base"], order_by="from_date asc"):
		bases[a.employee] = flt(a.base)
	out = []
	for emp, s in subjects.items():
		rs = rule_sets.get(s.company)
		if not rs:
			continue
		mine = [m for m in marks if m.employee == emp]
		live = len({m.mark_date for m in mine})
		raised = [m for m in mine if m.raised_on and s.status == "Active"
		          and managers.get(s.reports_to) == m.raised_by]
		if raised and not any(c > raised[0].raised_on for c in reviews.get(emp, [])):
			out.append(frappe._dict(employee=emp, employee_name=s.employee_name, count=live,
			                        raised_on=raised[0].raised_on, why="raised", live=live,
			                        raised_by=_person(raised[0].raised_by)))
			continue
		if reviews.get(emp):
			continue
		rate, earns, _grade = _rate(rs, s)
		point = _raise_point(_live_dated(mine), rate, bases.get(emp, 0))
		if point:
			out.append(frappe._dict(employee=emp, employee_name=s.employee_name, count=point[0],
			                        raised_on=point[1], why=point[2], live=live))
	out.sort(key=lambda r: r.raised_on)
	return out


# ── Raise it with HR (brief, Decisions 24 Oct 2026 (3), option A) ────────────
#
# A manager whose report has reached the limit, and keeps coming in not
# groomed, asks HR for a conversation. It never adds a fine and never lets
# anybody add a 4th mark. Stored as three fields on the mark that reached the
# limit - the same shape as the employee's "Ask HR" - so there is no new record
# and nothing on the Employee profile. One raise per person per month.

RAISE_REASONS = tuple(r for r in REASONS if r != OTHER)
RAISE_FIELDS = ("raised_on", "raised_by", "raised_reason")


def may_raise(employee, user=None):
	"""May `user` raise this person's grooming with HR this month? Returns a
	dict: `ok` and the `mark` to write on, or `code` and `message`."""
	user = user or frappe.session.user
	day = getdate(nowdate())
	start, end = _month_bounds(day)
	me = _active_employee(user)
	s = frappe.db.get_value("Employee", employee, ["name", "first_name", "employee_name",
	                                               "status", "reports_to", "company"], as_dict=True)
	if not s or not me or s.reports_to != me or s.status != "Active":
		return _no("RAISE1", _("Only the person's current manager can raise this with HR."))
	if not is_on() or not rule_set_for(s.company):
		return _no("R1", _("Grooming reds are not switched on for this company."))
	# Removed marks too: a raise written on a mark HR later removed still
	# counts as this month's one raise (architect review M-2, AC-83).
	marks = frappe.get_all(MARK, filters={"employee": employee, "docstatus": ("in", [1, 2]),
	                                      "mark_date": ("between", [start, end])},
	                       fields=["name", "mark_date", "creation", "raised_on", "docstatus"])
	first = _first(s)
	code, limit_mark = _raise_verdict(marks, _rate_now(employee), _base(employee, end))
	if code == "RAISE2":
		return _no("RAISE2", _("{0}'s grooming has already been raised with HR this "
		                       "month.").format(first))
	if code:
		return _no("RAISE3", _("{0} has not reached the limit this month, so there is nothing to "
		                       "raise.").format(first))
	return frappe._dict(ok=True, code=None, message=None, mark=limit_mark, first=first)


def _raise_verdict(marks, rate, base):
	"""The one rule for a raise, on one person's marks this month (live and
	removed): ("RAISE2", None) once raised, ("RAISE3", None) before the limit,
	else (None, the live mark that reached the limit)."""
	if any(m.raised_on for m in marks):
		return "RAISE2", None
	live = [m for m in marks if m.docstatus == 1]
	point = _raise_point(_live_dated(live), rate, base)
	if not point:
		return "RAISE3", None
	return None, next(m.name for m in live if m.creation == point[1])


@frappe.whitelist(methods=["POST"])
def raise_with_hr(employee, reason):
	"""The manager's "Raise it with HR". One fixed reason, no free text. The
	controller checks it all again on the save."""
	if reason not in RAISE_REASONS:
		frappe.throw(_("Choose a reason first."))
	v = may_raise(employee)
	if not v.ok:
		access.refuse(v.message, v.code, "raise_with_hr", MARK, None)
	doc = frappe.get_doc(MARK, v.mark)
	doc.flags[RAISE_FLAG] = True
	doc.raised_reason = reason
	doc.raised_by = frappe.session.user
	doc.raised_on = now_datetime()
	doc.save()
	return {"name": doc.name}


# ── notices (US-7, PRIV-2) ───────────────────────────────────────────────────

def _notify(doc, users, text, for_hr=False):
	"""One desk bell each, built in code (not an editable Notification record).
	Never blocks the mark: a failure is logged with the mark's name only.

	The bell's `link` opens the portal's Attendance month at that day (AC-34):
	the person's own month, or for HR the person's. Ids only, no words."""
	try:
		emails = frappe.get_all("User", filters={"name": ("in", list(users) or [""]), "enabled": 1},
		                        pluck="email")
		if not emails:
			return
		from frappe.desk.doctype.notification_log.notification_log import make_notification_logs

		make_notification_logs(frappe._dict({
			"type": "Alert", "document_type": doc.doctype, "document_name": doc.name,
			"subject": text, "email_content": text, "from_user": frappe.session.user,
			"link": "/hrms-employee?grooming={0}{1}".format(
				getdate(doc.get("mark_date") or doc.get("review_month")),
				"&who=" + doc.employee if for_hr else ""),
		}), emails)
	except Exception:
		frappe.log_error(title="Grooming notice not sent for {0}".format(doc.name),
		                 message=frappe.get_traceback())


def _subject_user(employee):
	"""The subject's own login, only if it is enabled and the Employee Active."""
	e = frappe.db.get_value("Employee", employee, ["user_id", "status"], as_dict=True)
	if not e or e.status != "Active" or not e.user_id:
		return None
	return e.user_id if frappe.db.get_value("User", e.user_id, "enabled") else None


def _hr_users_for(employee):
	"""Enabled HR users who may act on this person as HR, minus the person."""
	users = set(frappe.get_all("Has Role", filters={"role": ("in", list(access.HR_ROLES)),
	                                                "parenttype": "User"}, pluck="parent"))
	users = set(frappe.get_all("User", filters={"name": ("in", list(users) or [""]), "enabled": 1},
	                           pluck="name"))
	own = frappe.db.get_value("Employee", employee, "user_id")
	return [u for u in sorted(users) if u != own and u != "Administrator"
	        and employee in hr_scope(u, [employee])]


def _marker_words(doc):
	"""'Ravi Kumar, your manager,' or 'Ritika Mehra (HR)'."""
	name = _person(doc.owner)
	return (_("{0}, your manager,").format(name) if doc.marked_as == "Manager"
	        else _("{0} (HR)").format(name))


def notify_marked(doc, raised=None):
	user = _subject_user(doc.employee)
	if not user:
		return
	rate = _rate_now(doc.employee)
	if doc.reason == OTHER:
		# Prototype v3, Z5 (spec N1-O): the typed words stay on the day.
		if doc.marked_as == "Manager":
			text = _("{0} marked a grooming red for you today ({1}). Open the day in your Attendance "
			         "month to read the reason. It takes {2} off your {3} pay.")
		else:
			text = _("{0} marked a grooming red for you on {1}. Open the day in your Attendance "
			         "month to read the reason. It takes {2} off your {3} pay.")
		text = text.format(_marker_words(doc), _day(doc.mark_date), _rupees(rate),
		                   _month_name(doc.mark_date))
	else:
		if doc.marked_as == "Manager":
			text = _("{0} marked a grooming red for you today ({1}): {2}. It takes {3} off your {4} "
			         "pay.")
		else:
			text = _("{0} marked a grooming red for you on {1}: {2}. It takes {3} off your {4} pay.")
		text = text.format(_marker_words(doc), _day(doc.mark_date), _(doc.reason), _rupees(rate),
		                   _month_name(doc.mark_date))
	text += " " + _("If you think it is wrong, open the day and tap “Ask HR to look at this”.")
	if raised == "max":
		text += " " + _("This is your 3rd grooming red this month, the most allowed. HR will talk "
		                "to you about it.")
	elif raised == "limit":
		text += " " + _("You have reached this month's legal limit for grooming reds, so HR will "
		                "talk to you about it.")
	_notify(doc, [user], text)


def notify_removed(doc):
	user = _subject_user(doc.employee)
	if not user:
		return
	name = _person(frappe.session.user)
	if doc.owner == frappe.session.user and doc.marked_as == "Manager" and doc.removal_reason == UNDO_REASON \
			and getdate(doc.mark_date) == getdate(nowdate()):
		first = name.split(" ")[0]
		text = _("{0}, your manager, removed the grooming red {1} marked for you today ({2}). "
		         "Nothing will come off your pay for it.").format(name, first, _day(doc.mark_date))
	else:
		text = _("{0} (HR) removed the grooming red on {1}: {2}. Nothing will come off your pay "
		         "for it.").format(name, _day(doc.mark_date), _(doc.removal_reason))
	_notify(doc, [user], text)


def notify_kept(doc):
	user = _subject_user(doc.employee)
	if not user:
		return
	text = _("{0} (HR) checked the grooming red on {1} and kept it. {2} still comes off your {3} "
	         "pay.").format(_person(frappe.session.user), _day(doc.mark_date),
	                        _rupees(_rate_now(doc.employee)), _month_name(doc.mark_date))
	_notify(doc, [user], text)


def notify_asked(doc):
	# N5 never carries the reason: HR reads it on the day.
	text = _("{0} asked HR to look at a grooming red on {1}.").format(
		doc.employee_name or doc.employee, _day(doc.mark_date))
	_notify(doc, _hr_users_for(doc.employee), text, for_hr=True)


def notify_raised(doc):
	"""The employee is told, in fixed words, who raised it and that it adds no
	fine; HR in scope get the flag back. Never the reason in the employee's."""
	name = _person(doc.raised_by)
	user = _subject_user(doc.employee)
	if user:
		_notify(doc, [user], _("{0}, your manager, has asked HR to talk to you about grooming. "
		                       "This adds no fine.").format(name))
	_notify(doc, _hr_users_for(doc.employee), for_hr=True, text=
	        _("Grooming review pending for {0}: {1}, the manager, raised it with HR on {2}.").format(
		        doc.employee_name or doc.employee, name, _day(doc.raised_on)))


def notify_review_recorded(review):
	"""The person and their current manager are told the review is done, with
	the date and nothing else - never the note (D6; Surbhi 25 Oct 2026)."""
	on = _day(review.creation)
	user = _subject_user(review.employee)
	if user:
		_notify(review, [user], _("HR recorded a grooming review with you. Action agreed on "
		                          "{0}.").format(on))
	manager = frappe.db.get_value("Employee", review.employee, "reports_to")
	m_user = frappe.db.get_value("Employee", {"name": manager, "status": "Active"}, "user_id") \
		if manager else None
	if m_user:
		_notify(review, [m_user], _("HR recorded the grooming review for {0}. Action agreed on "
		                            "{1}.").format(frappe.db.get_value("Employee", review.employee,
		                                                              "employee_name"), on),
		        for_hr=True)


def audit_other_text(doc):
	"""Every "Other" text is audit-logged (Surbhi, 25 Oct 2026): one security
	log line - who wrote it, on which mark, when, how long - and NEVER the words
	(PRIV-7: no personal content in logs). The words themselves stay on the mark,
	which nobody can edit or delete after it is made, so the line points at the
	only copy."""
	if doc.reason != OTHER:
		return
	try:
		frappe.logger("security").info(json.dumps({
			"event": "grooming_other_text", "at": str(now_datetime()), "user": frappe.session.user,
			"doctype": MARK, "name": doc.name, "employee": doc.employee,
			"length": len(doc.other_reason or "")}))
	except Exception:
		pass


# ── The live portal's bell (Surbhi, 24-25 Oct 2026) ──────────────────────────
#
# The portal's bell panel lists goal approvals. These two calls add the
# grooming notices to it: the person's own Notification Log rows for a mark or
# a review, nothing else. The words are the fixed sentences the notices were
# built with - no "Other" text ever reaches one - and a row is shown only while
# its reader may still read what it is about (the mark's own gate; for a review
# the subject, their current manager or HR in scope).

@frappe.whitelist()
def my_notices(limit=20):
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please sign in."), frappe.PermissionError)
	rows = frappe.get_all("Notification Log",
	                      filters={"for_user": user, "document_type": ("in", [MARK, REVIEW])},
	                      fields=["name", "subject", "link", "creation", "read", "document_type",
	                              "document_name"],
	                      order_by="creation desc", limit_page_length=50)
	allowed = _readable(user, rows)
	shown = [r for r in rows if (r.document_type, r.document_name) in allowed]
	# Off: old notices stay readable, but open nothing - the month they point
	# at has no grooming section while off (switch review S-3).
	on = is_on()
	return {"unread": sum(1 for r in shown if not r.read),
	        "items": [{"text": r.subject, "link": r.link if on and str(r.link or "").startswith(
	                       "/hrms-employee?grooming=") else None,
	                   "when": "{0} {1}".format(_day(r.creation), str(r.creation)[11:16]),
	                   "read": int(r.read or 0)} for r in shown[:max(1, min(cint(limit), 50))]]}


@frappe.whitelist(methods=["POST"])
def my_notices_seen():
	"""Opening the bell marks the caller's own grooming notices read."""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please sign in."), frappe.PermissionError)
	frappe.db.set_value("Notification Log", {"for_user": user, "read": 0,
	                                          "document_type": ("in", [MARK, REVIEW])}, "read", 1)
	return {"ok": 1}


def _readable(user, rows):
	"""Which of these notices' documents the user may read now, in a flat
	number of queries: the marks' gate (may_read) and the review's gate."""
	marks = {r.document_name for r in rows if r.document_type == MARK}
	reviews = {r.document_name for r in rows if r.document_type == REVIEW}
	docs = {}
	if marks:
		for m in frappe.get_all(MARK, filters={"name": ("in", list(marks))},
		                        fields=["name", "employee", "mark_date", "owner"]):
			docs[(MARK, m.name)] = m
	if reviews:
		for r in frappe.get_all(REVIEW, filters={"name": ("in", list(reviews))},
		                        fields=["name", "employee"]):
			docs[(REVIEW, r.name)] = r
	if not docs:
		return set()
	me = _active_employee(user)
	people = list({d.employee for d in docs.values()})
	managers = {e.name: e.reports_to for e in frappe.get_all(
		"Employee", filters={"name": ("in", people)}, fields=["name", "reports_to"])}
	hr = hr_scope(user, people)
	today = getdate(nowdate())
	out = set()
	for key, d in docs.items():
		mine = bool(me and d.employee == me)
		manager = bool(me and managers.get(d.employee) == me)
		if key[0] == MARK:
			ok = (mine or d.employee in hr or (me and d.owner == user)
			      or (manager and getdate(d.mark_date) == today))
		else:
			ok = mine or manager or (d.employee in hr and not mine)
		if ok:
			out.add(key)
	return out


def notify_flag(doc, why):
	month = _month_name(doc.mark_date)
	who = doc.employee_name or doc.employee
	if why == "max":
		text = _("Grooming review pending for {0}: 3 grooming reds in {1}, the most "
		         "allowed.").format(who, month)
	else:
		text = _("Grooming review pending for {0}: the legal limit for grooming reds in {1} is "
		         "reached.").format(who, month)
	_notify(doc, _hr_users_for(doc.employee), text, for_hr=True)


def _rate_now(employee):
	subjects, rule_sets = _subjects([employee])
	s = subjects.get(employee)
	rs = rule_sets.get(s.company) if s else None
	return _rate(rs, s)[0] if rs else 0


def _base(employee, month_end):
	"""The Basic the legal limit is worked from: the latest submitted assignment
	with from_date <= month end, the same query `payroll_slip.month_summary` uses."""
	return flt(frappe.db.get_value("Salary Structure Assignment",
	                               {"employee": employee, "docstatus": 1, "from_date": ("<=", month_end)},
	                               "base", order_by="from_date desc"))


def raised_by(doc):
	"""Did THIS mark raise the month's flag? "max", "limit" or None.

	Called from the mark's on_submit, inside the same transaction.
	"""
	start, end = _month_bounds(doc.mark_date)
	if frappe.db.exists(REVIEW, {"employee": doc.employee, "review_month": start}):
		return None
	rate, base = _rate_now(doc.employee), _base(doc.employee, end)
	marks = frappe.get_all(MARK, filters={"employee": doc.employee, "docstatus": 1,
	                                      "mark_date": ("between", [start, end])},
	                       fields=["name", "mark_date", "creation"])
	dated = _live_dated(marks)
	point = _raise_point(dated, rate, base)
	if not point:
		return None
	before = _raise_point([x for x in dated if x[0] != getdate(doc.mark_date)], rate, base)
	return None if before else point[2]


# ── the endpoints the screens call ──────────────────────────────────────────

def _load(name):
	"""A mark the caller may read, or a refusal that says nothing about it."""
	if not name or not frappe.db.exists(MARK, name):
		frappe.throw(_("That grooming red no longer exists."), frappe.DoesNotExistError)
	doc = frappe.get_doc(MARK, name)
	doc.check_permission("read")
	return doc


@frappe.whitelist(methods=["POST"])
def mark(employee, reason, told_in_person=0, date=None, other_reason=None):
	"""Make and submit one mark, as the signed-in user. The controller applies
	every rule; `marked_as` is set by the server and never read from here."""
	doc = frappe.get_doc({"doctype": MARK, "employee": employee, "reason": reason,
	                      "mark_date": getdate(date or nowdate()),
	                      "told_in_person": 1 if cint(told_in_person) else 0,
	                      "other_reason": other_reason})
	doc.insert()
	doc.submit()
	return {"name": doc.name}


@frappe.whitelist(methods=["POST"])
def undo(name):
	"""A manager takes back their own mark, the same day. No sheet: the reason
	is always "Marked by mistake", set by the controller."""
	doc = _load(name)
	doc.cancel()
	return {"name": doc.name}


@frappe.whitelist(methods=["POST"])
def remove(name, reason):
	"""HR removes a mark with one of the fixed reasons. Cancel, never delete."""
	doc = _load(name)
	if reason not in REMOVAL_REASONS:
		frappe.throw(_("Choose why you are removing it."))
	doc.removal_reason = reason
	doc.cancel()
	return {"name": doc.name}


@frappe.whitelist(methods=["POST"])
def ask(name):
	"""The marked person asks HR to look at it. Once per mark, no text."""
	doc = _load(name)
	doc.asked_on = now_datetime()
	doc.save()
	return {"name": doc.name}


@frappe.whitelist(methods=["POST"])
def keep(name):
	"""HR answers an ask by keeping the mark. The person is told."""
	doc = _load(name)
	doc.kept_by = frappe.session.user
	doc.kept_on = now_datetime()
	doc.save()
	return {"name": doc.name}


@frappe.whitelist(methods=["POST"])
def record_review(employee, month, note):
	"""HR records the review that clears a pending flag. Insert-only: nobody
	has write or delete on the record, so it cannot be changed afterwards."""
	doc = frappe.get_doc({"doctype": REVIEW, "employee": employee,
	                      "review_month": get_first_day(getdate(month)),
	                      "review_note": (note or "").strip()})
	doc.insert()
	return {"name": doc.name}


def _names(users):
	"""How people are named to each other: the name HR keeps on the Employee
	record, or the login's own name for somebody with none (an HR user who is
	not on the payroll). Two queries for any number of people."""
	users = [u for u in users if u]
	out = {u.name: u.full_name for u in frappe.get_all(
		"User", filters={"name": ("in", users or [""])}, fields=["name", "full_name"])}
	for e in frappe.get_all("Employee", filters={"user_id": ("in", users or [""])},
	                        fields=["user_id", "employee_name"], order_by="status asc"):
		out[e.user_id] = e.employee_name or out.get(e.user_id)
	return out


def _person(user):
	return _names([user]).get(user) or user


@frappe.whitelist()
def today():
	"""The manager's Today card: direct reports who have punched in today.

	Flat in queries for 5 or 400 reports: the rules read their facts for the
	whole team at once (`_facts`), never per row.
	"""
	user = frappe.session.user
	me = _active_employee(user)
	if not me:
		return {"show": False}
	team = frappe.get_all("Employee", filters={"reports_to": me, "status": "Active"},
	                      fields=["name", "employee_name", "designation"], order_by="employee_name asc")
	if not team:
		return {"show": False}
	day = getdate(nowdate())
	f = _facts([t.name for t in team], day, day, user)
	if not any(f.rule_sets.values()):
		return {"show": False}

	todays = frappe.get_all(MARK, filters={"employee": ("in", [t.name for t in team]),
	                                       "mark_date": day, "docstatus": 1},
	                        fields=["name", "employee", "reason", "other_reason", "owner", "creation",
	                                "marked_as", "told_in_person"])
	names = _names({m.owner for m in todays})
	# "Half-day leave this afternoon", never the leave type (the manager
	# approves leave, so they know it; the type is HR's). One read, not per row.
	half = set(frappe.get_all("Leave Application",
	                          filters={"employee": ("in", [t.name for t in team]), "docstatus": 1,
	                                   "status": "Approved", "half_day": 1, "half_day_date": day},
	                          pluck="employee"))
	m_start, _m_end = _month_bounds(day)
	count = frappe.db.count(MARK, {"owner": user, "docstatus": 1,
	                               "mark_date": ("between", [m_start, day])})
	rows, not_in, at_limit = [], [], []
	for t in team:
		s = f.subjects.get(t.name)
		if not s or not f.rule_sets.get(s.company):
			continue
		at = f.punches.get((t.name, str(day)))
		if not at:
			not_in.append(t.employee_name)
			continue
		row = {"employee": t.name, "employee_name": t.employee_name, "first": _first(s),
		       "designation": t.designation, "in_at": at, "half_day": t.name in half}
		m = next((x for x in todays if x.employee == t.name), None)
		if m:
			row["mark"] = {"name": m.name, "reason": reason_words(m), "at": str(m.creation)[11:16],
			               "mine": m.owner == user, "by": names.get(m.owner) or m.owner,
			               "marked_as": m.marked_as, "has_login": bool(s.user_id in f.enabled)}
		else:
			v = _decide(f, t.name, day)
			row["can_mark"] = bool(v.ok)
			row["why_not"] = None if v.ok else v.message
			row["why_code"] = v.code
			row["has_login"] = bool(s.user_id in f.enabled)
			if v.code == "R12" and not hr_only(v):
				row["stop"] = v.get("stop")
				at_limit.append(row)
			row["needs_told_tick"] = bool(v.ok and not v.has_login)
		rows.append(row)
	states = _raise_states(f, [r["employee"] for r in at_limit])
	for r in at_limit:
		r["raise"] = states.get(r["employee"], {"can": False})
		if not r["raise"]["can"] and r.get("stop"):
			# Prototype v3, Z8: once raised (or when no raise is possible) the row
			# says the stop alone - never "you can raise it" above "Raised with HR".
			r["why_not"] = r["stop"]
		r.pop("stop", None)
	return {"show": True, "day": _day(day), "rows": rows, "not_in": not_in, "count": count,
	        "reasons": list(REASONS), "other_max": OTHER_MAX, "other_hint": _(OTHER_HINT),
	        "raise_reasons": list(RAISE_REASONS)}


def hr_only(v):
	return v.get("capacity") == "HR"


def _raise_states(f, employees):
	"""For the Today card's rows at the limit, all at once (architect review
	m-6: it was ~8 queries per row): may the manager raise it, or when they did
	and when HR answered. Two queries whatever the number of rows; rate and
	Basic come from the facts already read. The caller is these people's
	manager (they are the Today card's direct reports)."""
	if not employees:
		return {}
	start, end = _month_bounds(getdate(nowdate()))
	marks = frappe.get_all(MARK, filters={"employee": ("in", employees), "docstatus": ("in", [1, 2]),
	                                      "mark_date": ("between", [start, end])},
	                       fields=["name", "employee", "mark_date", "creation", "raised_on",
	                               "docstatus"])
	reviews = frappe.get_all(REVIEW, filters={"employee": ("in", employees), "review_month": start},
	                         fields=["employee", "creation"])
	out = {}
	for e in employees:
		s = f.subjects[e]
		mine = [m for m in marks if m.employee == e]
		code, _mark = _raise_verdict(mine, _rate(f.rule_sets[s.company], s)[0], _base_on(f, e, end))
		if not code:
			out[e] = {"can": True}
			continue
		if code != "RAISE2":
			out[e] = {"can": False}
			continue
		raised = min(m.raised_on for m in mine if m.raised_on)
		after = sorted(r.creation for r in reviews if r.employee == e and r.creation > raised)
		out[e] = {"can": False, "raised_on": _day(raised),
		          "reviewed_on": _day(after[0]) if after else None}
	return out


def month_lines(employee, start, end):
	"""The `grooming` key of the Attendance month, or None.

	None - no key at all - for anybody the read gate refuses, for a company
	with grooming or its rule set off, and for Contract staff looking at their own month
	(AC-40). A manager never gets a rupee figure (AC-30).
	"""
	user = frappe.session.user
	subjects, rule_sets = _subjects([employee])
	s = subjects.get(employee)
	rs = rule_sets.get(s.company) if s else None
	if not rs:
		return None
	me = _active_employee(user)
	is_self = bool(me and me == employee)
	is_manager = bool(me and not is_self and s.reports_to == me)
	is_hr = not is_self and employee in hr_scope(user, [employee])
	rate, earns, grade = _rate(rs, s)
	start, end = getdate(start), getdate(end)
	day = getdate(nowdate())

	marks = frappe.get_all(MARK, filters={"employee": employee, "docstatus": 1,
	                                      "mark_date": ("between", [start, end])},
	                       fields=["name", "mark_date", "reason", "other_reason", "owner", "creation",
	                               "marked_as", "told_in_person", "asked_on", "kept_by", "kept_on"],
	                       order_by="mark_date asc")
	owns = any(m.owner == user for m in marks)
	if not (is_self or is_manager or is_hr or owns):
		return None
	if not earns and not is_hr:
		return None
	if is_self or is_hr:
		visible = marks
	else:
		visible = [m for m in marks if m.owner == user or (is_manager and getdate(m.mark_date) == day)]

	slips = frappe.get_all("Salary Slip", filters={"employee": employee, "docstatus": 1,
	                                               "start_date": ("<=", end), "end_date": (">=", start)},
	                       fields=["employee", "start_date", "end_date"])
	names = _names({m.owner for m in visible} | {m.kept_by for m in visible if m.kept_by})
	first = _first(s)
	has_login = bool(s.user_id and frappe.db.get_value("User", s.user_id, "enabled"))
	out = {"first": first, "name": s.employee_name, "viewer": "self" if is_self else
	       ("hr" if is_hr else ("manager" if is_manager else "marker")),
	       "has_login": has_login, "has_manager": bool(s.reports_to), "days": {}}
	out["month_name"] = _month_name(start)
	if is_self or is_hr:
		# The employee's own pay, and HR's Keep sheet (HR sees it in the pay
		# report anyway). Never a manager.
		out["rate_words"] = _rupees(rate)
		out["grade"] = grade

	for m in visible:
		closed = bool(_closed_by(slips, employee, m.mark_date))
		d = {"name": m.name, "reason": reason_words(m), "marked_as": m.marked_as,
		     "by": names.get(m.owner) or m.owner, "by_me": m.owner == user,
		     "on": _day(m.mark_date), "at": str(m.creation)[11:16],
		     "told_in_person": cint(m.told_in_person),
		     "asked_on": (_day(m.asked_on) + " at " + str(m.asked_on)[11:16]) if m.asked_on else None,
		     "kept_by": names.get(m.kept_by) if m.kept_by else None,
		     "kept_by_me": m.kept_by == user,
		     "kept_on": _day(m.kept_on) if m.kept_on else None,
		     "can_undo": bool(m.owner == user and m.marked_as == "Manager"
		                      and getdate(m.mark_date) == day and not closed),
		     "can_remove": bool(is_hr and not closed),
		     "can_ask": bool(is_self and not m.asked_on and not closed),
		     "can_keep": bool(is_hr and m.asked_on and not m.kept_on and not closed)}
		out["days"][str(m.mark_date)] = {"mark": d}

	if is_self:
		# A day whose only mark was removed says so, on the person's own record.
		for d in frappe.get_all(MARK, filters={"employee": employee, "docstatus": 2,
		                                       "mark_date": ("between", [start, end])},
		                        pluck="mark_date"):
			out["days"].setdefault(str(d), {"removed": True})
	if is_hr:
		f = _facts([employee], start, min(end, max(day, start)), user)
		d = start
		while d <= end:
			key = str(d)
			if key not in out["days"]:
				v = _decide(f, employee, d)
				out["days"][key] = {"can_mark": bool(v.ok), "why_not": None if v.ok else v.message,
				                    "why_code": v.code, "needs_told_tick": bool(v.ok and not v.has_login)}
			d = frappe.utils.add_days(d, 1)
		slip = _closed_by(slips, employee, start)
		out["closed_month"] = _month_name(start) if slip else None

	if is_self and marks:
		n = len({m.mark_date for m in marks})
		amount = n * rate
		charged = _slip_line(employee, start, end)
		out["tile"] = {"n": n, "amount": _rupees(charged if charged is not None else amount),
		               "would_be": _rupees(amount),
		               "capped": charged is not None and flt(charged) < flt(amount),
		               "month": _month_name(start)}

	# The flag for this month, and - on the current month only - last month's
	# if it is still waiting (AC-59). Older ones stop showing (Question 6).
	flags = []
	this_flag = flag_for(employee, start, rate, _base(employee, end), with_note=is_hr or is_manager)
	if this_flag:
		flags.append((this_flag, False))
	if start == getdate(get_first_day(day)):
		prev = getdate(add_months(start, -1))
		pf = flag_for(employee, prev, rate, _base(employee, get_last_day(prev)))
		if pf and pf.state == "pending":
			flags.insert(0, (pf, True))
	out["review"] = [r for r in (_review_payload(fl, carried, is_self, is_manager, is_hr, user, first)
	                             for fl, carried in flags) if r]
	return out


def _slip_line(employee, start, end):
	"""What a slip for this month charges on the grooming line, or None when
	there is no slip yet. The tile follows the slip once one exists."""
	slip = frappe.get_all("Salary Slip", filters={"employee": employee, "docstatus": ("<", 2),
	                                              "start_date": ("<=", end), "end_date": (">=", start)},
	                      pluck="name", order_by="docstatus desc, modified desc", limit_page_length=1)
	if not slip:
		return None
	return flt(frappe.db.get_value("Salary Detail", {"parent": slip[0], "parenttype": "Salary Slip",
	                                                 "salary_component": COMPONENT}, "amount"))


def _review_payload(fl, carried, is_self, is_manager, is_hr, user, first):
	"""What each reader of the flag may see (spec 7.6, D6): the subject a state
	and a date; the direct manager the note too (prototype v2); HR the figures,
	the note and the button."""
	if not (is_self or is_manager or is_hr or user in fl.owners):
		return None
	out = {"state": fl.state, "month": _month_name(fl.month), "month_start": str(fl.month),
	       "carried": carried, "live": fl.live}
	if fl.state == "cleared":
		out["on"] = _day(fl.review.creation)
		# Prototype v3, Z16: after the raise's review nothing can raise it again
		# this month; before a raise, the manager still can, once.
		out["after_raise"] = bool(fl.get("raise_on"))
		if is_hr or is_manager:
			out["note"] = fl.review.review_note
			out["by"] = _person(fl.review.owner)
			out["by_me"] = fl.review.owner == user
		return out
	out["why"] = fl.why
	out["count"] = fl.count
	if fl.get("raise_on"):
		out["raise_on"] = _day(fl.raise_on)
		out["raise_by"] = _person(fl.raise_by)
		out["raise_by_me"] = fl.raise_by == user
		if is_hr:
			out["raise_reason"] = _(fl.raise_reason or "")
	if is_hr:
		out["raised_on"] = _day(fl.raised_on)
		out["limit"] = _rupees(fl.limit)
		out["base"] = _rupees(fl.base)
		out["can_record"] = True
	elif is_self:
		out["amount"] = _rupees(fl.live * fl.rate)
		out["limit"] = _rupees(fl.limit)
	return out
