"""Who may see, write or export a performance feedback record (ALV-117).

Frappe HR grants the plain `Employee` role read, write, create, submit, cancel,
export, print, share, report and email on the WHOLE `Employee Performance
Feedback` doctype, and registers no row filter of any kind for it. On a tenant
with 302 staff logins that means every one of them can list, open and export
every piece of feedback written about every colleague - and can edit, submit or
cancel criticism written about themselves.

Measured on production read-only on 2026-09-24: `dtc.alvoraa.co` has 302
Employee records, 4 enabled logins, zero feedback rows and no `Custom DocPerm`,
so the doctype's own permissions are in force unmodified. The staff load has
already happened; creating the remaining logins has not, and
`alvoraa_org_structure/dotted_line.py` starts inserting rows the first time a
manager scores an appraisal. This is a fault whose severity changes with no
commit at all, which is why it lands before the logins rather than after.

Two hooks, because they answer different questions. The query condition filters
LISTS, REPORTS and EXPORTS; has_permission guards opening ONE record by name,
and printing, emailing or sharing it. A list filter alone leaves
/app/employee-performance-feedback/HR-FDBK-0001 wide open at its own URL. This
is the same pair, and the same reasoning, as
`alvoraa_portal.field_app_access.checkin_query_conditions`.

The rule:

  * the AUTHOR may read, write, create, submit, cancel, print, email and share
    what they wrote - `reviewer` is one of the Employee records linked to their
    login;
  * the SUBJECT may READ what is about them, and nothing else. Not write, not
    submit, not cancel, not email, not share. Feedback the subject can edit or
    withdraw is not feedback, and this keeps SEC-10 - nobody acts on a document
    about themselves - true even for an HR Manager who is the subject;
  * a MANAGER may READ feedback about their own direct reports. Direct reports
    only, not the whole tree, and only while the manager's own record is Active;
  * HR sees within its own HR scope, which is `access.permitted_employees` - the
    same definition the rest of the product uses, so a store's HR person is held
    to their store here too (slice 030);
  * anybody else sees nothing.

A manager does NOT see feedback their report WROTE about somebody else. It is
not about their report, the subject never agreed to it, and a manager who can
read their team's outgoing opinions is how honest feedback stops being given.
The dotted-line flow makes that concrete: a report may be asked to review the
manager's own peer. (Decided 2026-09-24.)

Fails closed. A caller who is none of the above gets `1=0`, never an empty
string, because an empty condition in Frappe means everybody. Controller
permission hooks can only ever deny, so nothing here grants an action the
doctype's own permission rows did not already allow.

Nothing in this module logs a name, a rating or a word of feedback text.
"""

import frappe

from hrms.alvoraa_hr_core.access import HR_ROLES, permitted_employees

DOCTYPE = "Employee Performance Feedback"
TABLE = "`tabEmployee Performance Feedback`"

# What the person who wrote the feedback may do with it. `amend` and `delete`
# are left out on purpose: no role but System Manager holds them on this
# doctype, and if that ever changes the answer should be "no" until somebody
# decides otherwise.
AUTHOR_MAY = frozenset({"read", "write", "create", "submit", "cancel", "print", "email", "share"})

# What the person the feedback is about may do with it.
SUBJECT_MAY = frozenset({"read"})


def _sees_everything(user, roles):
	"""The CXO view. System Manager stands in for CXO until there is a CXO role."""
	return user == "Administrator" or "System Manager" in roles


def _my_employees(user):
	"""(all ids, active ids) for the Employee records linked to this login.

	One query. Both are needed: the author and subject rules hold for a leaver
	too - their own feedback is still their own data - but the manager rule does
	not, or an ex-manager with an enabled login would keep reading their old
	team's reviews.
	"""
	rows = frappe.get_all("Employee", filters={"user_id": user}, fields=["name", "status"])
	return {r.name for r in rows}, {r.name for r in rows if r.status == "Active"}


def _direct_reports(active_ids):
	if not active_ids:
		return set()
	return set(
		frappe.get_all(
			"Employee",
			filters={"reports_to": ["in", sorted(active_ids)], "status": "Active"},
			pluck="name",
		)
	)


def _in(column, names):
	values = ", ".join(frappe.db.escape(n) for n in sorted(names))
	return f"{TABLE}.{column} in ({values})"


def feedback_query_conditions(user=None, doctype=None):
	"""Row filter for every list, report and export of the doctype.

	Returns a SQL fragment, or "" for the callers who see everything. Never
	returns "" for anybody else: an empty condition means no filter at all.
	"""
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	if _sees_everything(user, roles):
		return ""

	clauses = []
	mine, active = _my_employees(user)
	if mine:
		clauses.append(_in("reviewer", mine))  # what I wrote
		clauses.append(_in("employee", mine))  # what is about me
		reports = _direct_reports(active)
		if reports:
			clauses.append(_in("employee", reports))  # what is about my team
	if HR_ROLES & roles:
		in_scope = permitted_employees(user)
		if in_scope:
			clauses.append(_in("employee", in_scope))

	if not clauses:
		return "1=0"
	return "(" + " or ".join(clauses) + ")"


def has_feedback_permission(doc, ptype=None, user=None):
	"""Guards ONE record: opened by name, printed, emailed, shared or written.

	The query condition cannot do this job - it never runs when a document is
	fetched by name - and this cannot do the query condition's job, because
	`export` and `report` are checked without any document at all.
	"""
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	if _sees_everything(user, roles):
		return True

	ptype = ptype or "read"
	subject = doc.get("employee")
	reviewer = doc.get("reviewer")
	mine, active = _my_employees(user)

	if subject and subject in mine:
		# Read only, and no fall-through to the HR branch: an HR Manager whose
		# own feedback this is asks another HR person, exactly as decision 34
		# already requires for the HR steps on a review.
		return ptype in SUBJECT_MAY

	if reviewer and reviewer in mine:
		return ptype in AUTHOR_MAY

	if ptype in SUBJECT_MAY and subject and subject in _direct_reports(active):
		return True

	if HR_ROLES & roles and subject and subject in permitted_employees(user):
		return True

	return False
