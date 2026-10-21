"""Replacement plans (slice 065): who may see one, and how it is erased.

A replacement plan is HR's private note that the person in a seat may need
replacing. It is a judgement about a named person, so three things matter
more than anything else here:

  * ONE GATE. Every door - desk lists, the form, REST, link search, counts and
    the Positions page - asks the same question, here (SEC-1).
  * NO COPIES. No change history, comments, assignments, shares, tags or
    attachments on a plan (PRIV-1, SEC-3).
  * A REAL ERASE. One erase path that leaves nothing behind, and a daily job
    that erases what has lapsed or whose person has left (PRIV-2, PRIV-3).

This is the only module that reads the plan table. A test fails if the
doctype's name appears anywhere else outside its own folder, `register.py`,
`hooks.py` and tests (SEC-7).

Nothing here logs a person's name, an employee id, a seat, an assignment or
the note. Log lines carry the plan's random name only (PRIV-4).
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, nowdate

import hrms.alvoraa_org_structure.register as register

DOCTYPE = "Replacement Plan"
TABLE = "`tabReplacement Plan`"

# Read that arrives only through one of these roles counts as no Read. A
# careless tick for "Employee" would otherwise give every login every plan
# (SEC-1 point 1; SEC-2 refuses the tick itself).
BROAD_ROLES = frozenset({"All", "Guest", "Desk User", "Employee", "Employee Self Service"})

# Never allowed on a plan, for anybody: each one makes a copy we cannot erase.
NEVER = frozenset({"print", "email", "export", "share", "report", "import"})

# A plan lasts this long from its last confirmation (Surbhi, 21 Oct 2026).
LIFE_DAYS = 90

# The optional note, counted on the server (PM-Q4 default).
NOTE_MAX = 200

# Set on the document by the erase function only. Any delete without it is
# refused, because Frappe's ordinary delete keeps a copy in Deleted Document.
ERASE_FLAG = "replacement_plan_erase"


def _refuse(message, endpoint):
	"""A refusal with no id in the log line: a plan's log must not point at a
	person, a seat or an assignment (PRIV-4)."""
	from hrms.alvoraa_hr_core.access import refuse

	refuse(message, "SEC-5", endpoint, DOCTYPE, None)


def _my_employees(user=None):
	"""(ids, any active) for the Employee records linked to this login."""
	rows = frappe.get_all(
		"Employee", filters={"user_id": user or frappe.session.user}, fields=["name", "status"]
	)
	return {r.name for r in rows}, any(r.status == "Active" for r in rows)


# ── the gate (SEC-1) ──────────────────────────────────────────────────────────


def _read_roles():
	"""Roles holding Read on plans, from the cached meta, which carries the
	tenant's own rows when it has any. No query."""
	return {p.role for p in frappe.get_meta(DOCTYPE).permissions if p.read and not cint(p.permlevel)}


def is_reader(user=None):
	"""Whether this person may see any plan at all. All must hold:

	1. Read on plans through a role that is not a broad one;
	2. they can open Positions (`may_view`);
	3. if their login is linked to an Employee, that Employee is Active - a
	   leaver whose login still works sees nothing, whatever their roles.

	Which plans they then see is `_condition`'s business.
	"""
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	if user != frappe.session.user:
		# `may_view` and `_scope` answer for the session's user only. Asked
		# about somebody else, fail closed rather than answer for the wrong one.
		return False
	if not (_read_roles() - BROAD_ROLES) & set(frappe.get_roles(user)):
		return False
	if not register.may_view():
		return False
	ids, active = _my_employees(user)
	return active or not ids


def _in(column, values):
	return "{0} in ({1})".format(column, ", ".join(frappe.db.escape(v) for v in sorted(values)))


def _condition(live=True, scoped=True):
	"""The ONE definition of which plans a reader sees, as a SQL condition on
	the plan table. Used for every list (the query hook) and for one record
	(`has_permission`), so the two cannot disagree.

	Scoped: the plan's seat is in the reader's companies (and branches, for a
	store-tied reader), worked out through the assignment's seat, and the plan
	is not about the reader. Live: the person is in the seat today and Active,
	the seat is not Closed, and the plan was confirmed within LIFE_DAYS - so a
	lapsed plan or a leaver's plan is hidden at once, whether or not the daily
	erase has run (PRIV-3). The scope stays inside the database: a sub-query,
	never a list of seat ids read into Python.
	"""
	today = nowdate()
	where = [f"a.name = {TABLE}.assignment"]
	if scoped:
		companies, branches = register._scope()
		if not companies:
			return "1=0"
		where.append(_in("p.company", companies))
		if branches is not None:
			where.append(_in("p.branch", branches))
		mine = _my_employees()[0]
		if mine:
			where.append("not " + _in("a.employee", mine))
	join_employee = ""
	if live:
		join_employee = " join `tabEmployee` e on e.name = a.employee"
		where += [
			"a.from_date <= {0}".format(frappe.db.escape(today)),
			"(a.to_date is null or a.to_date >= {0})".format(frappe.db.escape(today)),
			"e.status = 'Active'",
			"p.status != 'Closed'",
		]
	cond = (
		"exists (select 1 from `tabAlvoraa Position Assignment` a"
		" join `tabAlvoraa Position` p on p.name = a.position" + join_employee
		+ " where " + " and ".join(where) + ")"
	)
	if live:
		cond += " and {0}.confirmed_on >= {1}".format(
			TABLE, frappe.db.escape(str(add_days(today, -LIFE_DAYS))))
	return "(" + cond + ")"


def query_conditions(user=None, doctype=None):
	"""`permission_query_conditions`: every list, count, report view, link
	search and REST list of plans. Never "" for a reader - an empty condition
	means everybody. `1=0` for anyone outside the gate, which does not depend
	on the data, so a count is 0 whether plans exist or not."""
	user = user or frappe.session.user
	if user == "Administrator":
		return _condition(scoped=False)
	if not is_reader(user):
		return "1=0"
	return _condition()


def has_permission(doc, ptype=None, user=None):
	"""`has_permission`: one plan, opened by name, saved, deleted - and
	refused outright for print, email, export, share, report and import.

	Delete is the one right that does not need the plan to be live: an HR
	Manager setting a new plan on somebody whose old plan lapsed today must be
	able to erase the old one first (Surbhi, 22 Oct, question 4). It still
	needs the seat in scope and never the reader's own. Reading a hidden plan
	this way is impossible: the erase reads nothing back.

	Frappe only lets this hook refuse; it cannot grant what the role table
	did not (owners and the System Manager have Read only).
	"""
	user = user or frappe.session.user
	ptype = ptype or "read"
	if ptype in NEVER:
		return False
	if user == "Administrator":
		return True
	if not is_reader(user):
		return False
	if ptype == "create" or doc.is_new():
		return True  # the record's own rules decide the rest (check_assignment)
	cond = _condition(live=ptype != "delete")
	return bool(frappe.db.sql(f"select name from {TABLE} where name = %s and {cond}", doc.name))


# ── no side doors (SEC-3, SEC-2) ─────────────────────────────────────────────

# The records Frappe can hang on any document, and the field on each that
# names the document's type. Each one on a plan would be a copy (a comment and
# its @mention email; an assignment, which also shares the record and beats
# the permission hook; a share; a tag, whose name outlives the plan; a file).
SIDE_RECORDS = {
	"Comment": "reference_doctype",
	"ToDo": "reference_type",
	"DocShare": "share_doctype",
	"Tag Link": "document_type",
	"File": "attached_to_doctype",
}


def refuse_side_record(doc, method=None):
	"""`validate` on Comment, ToDo, DocShare, Tag Link and File. One
	comparison; reads nothing. Following a plan needs no rule: Frappe refuses
	to follow a record that keeps no change history."""
	field = SIDE_RECORDS.get(doc.doctype)
	if field and doc.get(field) == DOCTYPE:
		frappe.throw(
			_("A replacement plan cannot have comments, assignments, shares, tags or files: each "
			  "would be a copy that stays after the plan is erased. Talk to HR directly instead.")
		)


def refuse_careless_grant(doc, method=None):
	"""`validate` on Custom DocPerm - what Role Permissions Manager saves. For
	plans only, refuses any right for a broad role, and print, email, export,
	share, report or import for any role (SEC-2). Read, write, create and
	delete for other roles stay the tenant's choice, and are recorded as a
	Version by `register.record_permission_change`."""
	if doc.parent != DOCTYPE:
		return
	ticked = [df.fieldname for df in frappe.get_meta("Custom DocPerm").fields
	          if df.fieldtype == "Check" and doc.get(df.fieldname)]
	if doc.role in BROAD_ROLES and ticked:
		frappe.throw(
			_("Replacement plans cannot be given to the {0} role: that would show them to every "
			  "login. Give Read to the owners' own role instead.").format(doc.role)
		)
	never = sorted(NEVER & set(ticked))
	if never and doc.is_new():
		# Frappe ticks print, email, export, share and report on every new row
		# it adds, so adding the owners' role would always be refused. Untick
		# them instead: nobody chose them.
		for right in never:
			doc.set(right, 0)
		return
	if never:
		frappe.throw(
			_("Replacement plans cannot be printed, emailed, exported, shared, reported on or "
			  "imported, so these rights cannot be ticked: {0}.").format(", ".join(never))
		)


def check_assignment(assignment):
	"""The seat assignment a plan may be set or kept on: started, not ended,
	its person Active, its seat not Closed and inside the caller's scope, and
	not the caller's own (SEC-5; decision 9)."""
	a =frappe.db.get_value(
		register.ASSIGNMENT, assignment, ["employee", "position", "from_date", "to_date"], as_dict=True
	)
	if not a:
		frappe.throw(_("That person is no longer in this seat. Reload Positions and try again."))
	today = nowdate()
	if str(a.from_date) > today or (a.to_date and str(a.to_date) < today):
		frappe.throw(_("That person is not in this seat today. Reload Positions and try again."))
	if frappe.db.get_value("Employee", a.employee, "status") != "Active":
		frappe.throw(_("That person is no longer an active employee, so no plan is needed."))
	seat = frappe.db.get_value(register.POSITION, a.position, ["company", "branch", "status"], as_dict=True)
	if not seat or seat.status == "Closed":
		frappe.throw(_("This seat is closed, so no plan can be kept on it."))

	companies, branches = register._scope()
	if seat.company not in companies or (branches is not None and (seat.branch or "") not in branches):
		_refuse(_("This seat is outside the companies and branches you look after."), "plans.check_assignment")
	if a.employee in _my_employees()[0]:
		_refuse(_("Nobody can set or keep a replacement plan on their own seat."), "plans.check_assignment")
