"""Slice 066: the grooming red mark.

A store manager (or HR) records, on the day, that somebody came to work not in
uniform. The month's marks become one deduction line on the payslip, never more
than the legal limit, and the person is told the same day.

ONE DEFINITION OF EVERY RULE, IN THIS FILE.

  `may_mark`          who may mark whom, on which day (SEC-1, SEC-3, SEC-6,
                      SEC-7). The record's own controller calls it, so
                      the desk, REST, imports and the portal all meet it; every
                      screen calls the same function to decide its buttons, so a
                      button and the guard cannot disagree.
  `may_read`          who may read a mark (SEC-4). The record's has_permission
                      and permission_query_conditions hooks are built on it, and
                      so are the screens.

Nothing here uses `ignore_permissions` (SEC-12). The mark is created, submitted,
cancelled and updated as the signed-in user: the DocPerm gives the right and the
controller narrows it. The few reads that do not run under the caller's own
permission are named where they happen - each answers a rule about ONE subject
and returns a yes, a no or a date, never another person's mark.

Logs carry document names and rule codes only (PRIV-7): `refuse()` writes the
security log, and a failed notice names the mark and nothing else.
"""

import calendar
import re

import frappe
from frappe import _
from frappe.utils import cint, flt, get_first_day, get_last_day, getdate, now_datetime, nowdate

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
NOT_ABOUT_CLOTHES = ("health", "sick", "illness", "disease", "pregnan", "period",
                     "medical", "family", "husband", "wife", "child", "religio", "caste",
                     "turban", "hijab", "burqa", "veil", "tilak", "bindi", "sindoor", "kara",
                     "skin", "weight", "fat", "body")


def clean_other(text):
	"""The typed reason, tidied, or a refusal saying what to do next."""
	text = " ".join(str(text or "").split())
	if not text:
		frappe.throw(_("Write your reason in a few words."))
	if len(text) > OTHER_MAX:
		frappe.throw(_("Keep your reason to {0} characters.").format(OTHER_MAX))
	if re.search(r"\b(" + "|".join(NOT_ABOUT_CLOTHES) + ")", text.lower()):
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
	rule_sets = {c: rule_set_for(c) for c in {r.company for r in rows}}
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

def _facts(employees, from_date, to_date, user):
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

	f.marks = frappe.get_all(MARK, filters={"employee": ("in", ids), "docstatus": ("<", 2),
	                                        "mark_date": ("between", [m_from, m_to])},
	                         fields=["name", "employee", "mark_date", "docstatus"])
	return f


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

	has_login = bool(s.user_id and s.user_id in f.enabled and s.status == "Active")
	if told_in_person is not None and not has_login and not cint(told_in_person):
		return _no("R13", _("Tick the box to confirm you told {0} in person.").format(first), **out)

	return frappe._dict(ok=True, code=None, message=None, has_login=has_login,
	                    rate=rate, grade=grade, **out)


def may_mark(employee, date, user=None, told_in_person=None, exclude=None):
	"""May `user` mark `employee` for `date`? The only definition (SEC-1).

	Returns a dict: `ok`, `capacity` ("Manager" or "HR") when there is one,
	`code` and `message` when refused, and `has_login` when allowed.
	"""
	user = user or frappe.session.user
	f = _facts([employee], date, date, user)
	return _decide(f, employee, date, told_in_person=told_in_person, exclude=exclude)


# ── who may read a mark (SEC-4) ──────────────────────────────────────────────

def may_read(doc, user=None):
	"""Subject, marker, current direct manager on the day, or HR in scope.
	Anybody else: no."""
	user = user or frappe.session.user
	if doc.get("owner") == user:
		return True
	me = _active_employee(user)
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
	return may_read(doc, user)


def mark_query_conditions(user=None):
	"""permission_query_conditions hook: the same gate, as SQL. Never empty
	for a tenant user - with no reach it matches no rows."""
	user = user or frappe.session.user
	if user == "Administrator":
		return ""
	esc = frappe.db.escape
	conds = ["`tabGrooming Mark`.owner = {0}".format(esc(user))]
	me = _active_employee(user)
	if me:
		conds.append("`tabGrooming Mark`.employee = {0}".format(esc(me)))
		conds.append("(`tabGrooming Mark`.mark_date = {0} and `tabGrooming Mark`.employee in "
		             "(select name from `tabEmployee` where reports_to = {1}))".format(
		                 esc(nowdate()), esc(me)))
	hr = _hr_sql(user)
	if hr:
		conds.append("`tabGrooming Mark`." + hr if hr != "1=1" else hr)
	return "(" + " or ".join(conds) + ")"


def refuse_side_record(doc, method=None):
	"""doc_events validate on Comment, ToDo and DocShare (SEC-8): no comment,
	assignment or share on a mark or a review, on any door.

	Frappe's assign_to will create a ToDo - and share the record - even for
	somebody who cannot read it (seen on the bench, 24 Oct 2026), so DocPerm
	alone does not stop it. One name comparison for every other row.
	"""
	ref = doc.get("reference_doctype") or doc.get("reference_type") or doc.get("share_doctype")
	if ref in (MARK, REVIEW):
		frappe.throw(_("A grooming red or a grooming review cannot be commented on, assigned "
		               "or shared."), frappe.PermissionError)


# ── the review flag (US-14) ──────────────────────────────────────────────────

# ── notices (US-7, PRIV-2) ───────────────────────────────────────────────────

def _notify(doc, users, text):
	"""One desk bell each, built in code (not an editable Notification record).
	Never blocks the mark: a failure is logged with the mark's name only."""
	try:
		emails = frappe.get_all("User", filters={"name": ("in", list(users) or [""]), "enabled": 1},
		                        pluck="email")
		if not emails:
			return
		from frappe.desk.doctype.notification_log.notification_log import make_notification_logs

		make_notification_logs(frappe._dict({
			"type": "Alert", "document_type": MARK, "document_name": doc.name,
			"subject": text, "email_content": text, "from_user": frappe.session.user,
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


def notify_marked(doc):
	user = _subject_user(doc.employee)
	if not user:
		return
	rate = _rate_now(doc.employee)
	if doc.marked_as == "Manager":
		text = _("{0} marked a grooming red for you today ({1}): {2}. It takes {3} off your {4} pay.")
	else:
		text = _("{0} marked a grooming red for you on {1}: {2}. It takes {3} off your {4} pay.")
	text = text.format(_marker_words(doc), _day(doc.mark_date), _(doc.reason), _rupees(rate),
	                   _month_name(doc.mark_date))
	text += " " + _("If you think it is wrong, open the day and tap “Ask HR to look at this”.")
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
	_notify(doc, _hr_users_for(doc.employee), text)


def _rate_now(employee):
	subjects, rule_sets = _subjects([employee])
	s = subjects.get(employee)
	rs = rule_sets.get(s.company) if s else None
	return _rate(rs, s)[0] if rs else 0


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
	rows, not_in = [], []
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
			row["needs_told_tick"] = bool(v.ok and not v.has_login)
		rows.append(row)
	return {"show": True, "day": _day(day), "rows": rows, "not_in": not_in, "count": count,
	        "reasons": list(REASONS), "other_max": OTHER_MAX, "other_hint": _(OTHER_HINT)}


def month_lines(employee, start, end):
	"""The `grooming` key of the Attendance month, or None.

	None - no key at all - for anybody the read gate refuses, for a company
	with the rule set off, and for Contract staff looking at their own month
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
		out["tile"] = {"n": n, "amount": _rupees(n * rate), "month": _month_name(start)}

	return out

