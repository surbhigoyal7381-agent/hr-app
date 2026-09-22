"""The access rules that the portal, goals and org-chart code all need.

Kept in one place so they cannot drift apart:

  refuse_own_decision(employee)  nobody approves or declines their own request
  refuse_own_rating(employee)    nobody rates or closes their own review
  refuse_hr_step_in_line(employee)  nobody above the subject does HR's steps
  permitted_companies(user)      which companies an HR user acts for
  permitted_branches(user)       which branches a store's HR person is limited to
  permitted_employees(user)      which Employee records an HR user may see
  permitted_employee_filters(user)  the same rule as query filters, never {}

It lives in hrms because every one of our apps can import hrms, and hrms must
not import them.

Refusals are written to the "security" log as one JSON line: who, which
endpoint, which document, which rule. Never a field value, a name or a reason.
"""

import json

import frappe
from frappe import _

HR_ROLES = frozenset({"HR Manager", "HR User"})


def log_refusal(rule, endpoint, doctype=None, name=None):
	"""One structured line per refusal, so misuse can be found later (SEC-17).

	Document names and user ids only. Logging must never stop the refusal itself.
	"""
	try:
		frappe.logger("security").warning(
			json.dumps(
				{
					"event": "refused",
					"at": str(frappe.utils.now_datetime()),
					"user": frappe.session.user,
					"endpoint": endpoint,
					"doctype": doctype,
					"name": name,
					"rule": rule,
				}
			)
		)
	except Exception:
		pass


def refuse(message, rule, endpoint, doctype=None, name=None):
	log_refusal(rule, endpoint, doctype, name)
	frappe.throw(message, frappe.PermissionError)


def is_own_record(employee, user=None):
	"""Is this employee record the caller's own login?"""
	if not employee:
		return False
	user = user or frappe.session.user
	return frappe.db.get_value("Employee", employee, "user_id") == user


def refuse_own_decision(employee, doctype=None, name=None, endpoint=None):
	"""Stop anyone deciding a request that is about themselves (SEC-9).

	No role is exempt. An HR Manager, owner or System Manager who raised a
	request must have someone else approve it.
	"""
	if is_own_record(employee):
		refuse(
			_("You cannot decide your own request. Someone else must approve it."),
			"SEC-9",
			endpoint,
			doctype,
			name,
		)


def refuse_own_rating(employee, doctype=None, name=None, endpoint=None):
	"""Stop anyone rating, calibrating or closing their own review (SEC-10).

	The same check as refuse_own_decision, logged as its own rule. No role is
	exempt: an HR Manager or System Manager whose own review it is must leave
	it to their manager and to another HR person.
	"""
	if is_own_record(employee):
		refuse(
			_("You cannot rate or decide anything in your own review. Your manager and HR do that."),
			"SEC-10",
			endpoint,
			doctype,
			name,
		)


# How far up a reporting line is walked. Real lines are a handful of levels;
# the cap only stops a broken tree from running forever.
MAX_LINE_DEPTH = 50


def subjects_in_my_line(employees, user=None, stand_in=None):
	"""Which of these employees the caller is above: their manager, that
	manager's manager, and so on up (decision 34).

	One walk up `reports_to` for all of them together: one query per level,
	at most MAX_LINE_DEPTH levels, and a loop in the tree ends that person's
	walk. `stand_in` is a function returning the employee who acts as manager
	for someone with no manager of their own
	(alvoraa_goals.permissions.get_hr_manager_employee); it is called at most
	once, and only when such a subject is met. For that subject the stand-in
	counts as in the line.

	Fails closed: a line still going at the depth cap counts as in the line.
	Every Employee record linked to the login counts as the caller.
	"""
	user = user or frappe.session.user
	subjects = {e for e in (employees or []) if e}
	if not subjects or not user or user == "Guest":
		return set()
	mine = set(frappe.get_all("Employee", filters={"user_id": user}, pluck="name"))
	if not mine:
		return set()

	manager_of = {}
	stand_in_emp = []
	at = {s: s for s in subjects}
	seen = {s: {s} for s in subjects}
	found = set()
	for depth in range(MAX_LINE_DEPTH):
		need = sorted({node for node in at.values() if node not in manager_of})
		if need:
			rows = frappe.get_all(
				"Employee", filters={"name": ["in", need]}, fields=["name", "reports_to"]
			)
			manager_of.update({r.name: r.reports_to for r in rows})
			for node in need:
				manager_of.setdefault(node, None)
		moved = {}
		for subject, node in at.items():
			manager = manager_of.get(node)
			if not manager:
				if depth == 0 and stand_in:
					if not stand_in_emp:
						stand_in_emp.append(stand_in())
					if stand_in_emp[0] in mine:
						found.add(subject)
				continue
			if manager in mine:
				found.add(subject)
			elif manager not in seen[subject]:
				seen[subject].add(manager)
				moved[subject] = manager
		at = moved
		if not at:
			break
	else:
		found.update(at)
	return found


def refuse_hr_step_in_line(employee, doctype=None, name=None, endpoint=None, stand_in=None):
	"""Stop anyone in the subject's reporting line doing the HR steps on their
	review, whatever roles they hold (security review M3, decision 34).

	The HR steps are calibration, HR removal of review items, HR's answer to a
	rating question, sending a review back from HR Review, and completing it.
	The manager steps stay with the manager; a different HR person does these.
	"""
	if employee and employee in subjects_in_my_line([employee], stand_in=stand_in):
		company = frappe.db.get_value("Employee", employee, "company") or ""
		refuse(
			_(
				"You are in this person's reporting line, so you cannot do the HR steps on their review. "
				"Ask another HR person in {0} to do this step."
			).format(company),
			"D34",
			endpoint,
			doctype,
			name,
		)


def refuse_own_submit(doc, method=None):
	"""doc_events before_submit: the desk, REST and imports get the same rule.

	Submitting a Leave Application or an Attendance Request is what approves it,
	so a submit by the person the document is about is a self-approval.
	"""
	refuse_own_decision(doc.get("employee"), doc.doctype, doc.name, endpoint=f"{doc.doctype} submit")


def permitted_companies(user=None):
	"""Companies this user may act for as HR. Fails closed.

	- System Manager (treated as CXO for now) and Administrator: every company.
	- HR Manager / HR User: the companies in their User Permissions on Company;
	  with none, the company on their own active Employee record; with neither,
	  nothing.
	- Anyone else: nothing.
	"""
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	if user == "Administrator" or "System Manager" in roles:
		return frappe.get_all("Company", pluck="name", order_by="name asc")
	if not HR_ROLES & roles:
		return []

	from frappe.core.doctype.user_permission.user_permission import get_user_permissions

	companies = sorted({d.get("doc") for d in get_user_permissions(user).get("Company", []) if d.get("doc")})
	if companies:
		return companies
	own = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "company")
	return [own] if own else []


def permitted_branches(user=None):
	"""The branches a location HR person is limited to, or None for everyone else.

	Read from the user's User Permissions on Branch (the ones that apply to every
	record type, or to Employee). One definition for every screen (slice 030):
	attendance_analytics._linked_branches is a wrapper around this.

	Frappe's User Permissions are not strict on this site, so a record with an
	EMPTY branch passes a Branch permission in a desk list. Every reader of this
	list therefore treats an employee with no branch as outside it - head office
	is not a store's business (DEF-6, 2026-09-16). No role is exempt here; the
	role rules live in permitted_employees.
	"""
	from frappe.core.doctype.user_permission.user_permission import get_user_permissions

	branches = sorted({p.get("doc") for p in get_user_permissions(user or frappe.session.user).get("Branch", [])
	                   if p.get("doc") and p.get("applicable_for") in (None, "", "Employee")})
	return branches or None


# The refusal. Frappe reads an EMPTY filter dict as "no conditions", which means
# EVERY record - so a filter-shaped helper that returned {} would fail OPEN,
# the exact opposite of permitted_employees(), which fails closed by returning
# an empty set. This dict matches nothing, in every Frappe query builder, and
# it is never {} (SEC-4, security note N1, AC-73).
NO_EMPLOYEES = {"name": ["in", []]}

# "Everyone", written as a real condition rather than as no condition at all.
# Employee is named, so `name` is never empty; "!=" is the plainest operator
# that is true for every row. Written this way so that NOTHING this helper
# returns can ever be an empty dict.
ALL_EMPLOYEES = {"name": ["!=", ""]}


def permitted_employee_filters(user=None):
	"""permitted_employees(), as Frappe filters instead of a set of names.

	One definition, two shapes: permitted_employees() is built on this, and a
	caller that wants to filter a query in the database - rather than read every
	permitted name into Python first - uses these filters directly (SEC-4).

	It NEVER returns an empty or partial dict. A caller with no HR entitlement
	gets NO_EMPLOYEES, which matches nothing. See NO_EMPLOYEES above for why
	that matters: {} would mean everybody.

	The rules are permitted_employees()' rules, unchanged:

	- System Manager and Administrator: everyone.
	- HR Manager / HR User with no Branch permission: their companies.
	- HR Manager / HR User with one (a store's HR person): their companies,
	  narrowed to those branches. An employee with no branch is outside it.
	- Anyone else - a plain employee, a plain manager, a Vendor User: refused.

	Every status, not only Active. A caller that needs Active people adds
	"status": "Active" itself, so that nobody loses a leaver's history by
	accident.
	"""
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	if user == "Administrator" or "System Manager" in roles:
		return dict(ALL_EMPLOYEES)
	companies = permitted_companies(user)
	if not companies:
		return dict(NO_EMPLOYEES)
	filters = {"company": ["in", companies]}
	branches = permitted_branches(user)
	if branches is not None:
		filters["branch"] = ["in", branches]
	return filters


def permitted_employees(user=None):
	"""The Employee records this user may see as HR, as a set of names. Fails closed.

	The companies from permitted_companies, narrowed to the branches from
	permitted_branches when the user holds a Branch User Permission:

	- System Manager (treated as CXO for now) and Administrator: everyone.
	- HR Manager / HR User with no Branch permission: everyone in their companies.
	- HR Manager / HR User with one (a store's HR person): everyone in their
	  companies who is in one of those branches. An employee with no branch is
	  outside it. A store's HR person sees only their store's reviews and
	  calibration; company-wide calibration is for HR with company-wide
	  permission (decision 2, slice 030).
	- Anyone else: nobody.

	Every status, not only Active: a leaver's reviews and KPIs still belong to
	the store that had them. One query; the caller filters with
	["employee", "in", sorted(names) or [""]].
	"""
	return set(frappe.get_all("Employee", filters=permitted_employee_filters(user), pluck="name"))
