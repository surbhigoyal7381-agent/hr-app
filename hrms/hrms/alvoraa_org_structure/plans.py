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


# ── set, confirm, remove, and the one erase (SEC-5, PRIV-2, PRIV-4) ──────────


def _changed():
	return _("Someone else changed this plan a moment ago. Here is the latest.")


def _log(reason, name):
	"""One security-log line per set, confirm, remove and erase, in the shape
	of every other refusal and change. The plan's random name and a reason
	word only: never the note, the person, the seat or the assignment, because
	these lines outlive the plan (PRIV-4)."""
	import json

	try:
		frappe.logger("security").warning(json.dumps({
			"event": "replacement_plan",
			"at": str(frappe.utils.now_datetime()),
			"user": frappe.session.user,
			"doctype": DOCTYPE,
			"name": name,
			"reason": reason,
		}))
	except Exception:
		pass


def erase(name, reason):
	"""THE ONLY WAY A PLAN IS DELETED. Leaves nothing behind in the database.

	- `delete_permanently`: no copy in Deleted Document, which Frappe
	  otherwise keeps for ever, note included.
	- the flag: the record's `on_trash` refuses every delete without it.
	- `delete_dynamic_links` now, in this transaction: Frappe only queues it
	  for after the commit, which in production depends on a worker.
	- the record sets `no_feed_on_delete`, so no "Deleted" comment either.
	Tags, files and the global-search row go inside `delete_doc` itself.

	Runs as whoever calls it, with that person's own Delete right: the HR
	Manager who removes a plan, or the scheduler (Administrator).
	"""
	from frappe.model.delete_doc import delete_dynamic_links

	frappe.delete_doc(DOCTYPE, name, delete_permanently=True, flags={ERASE_FLAG: True})
	delete_dynamic_links(DOCTYPE, name)
	_log(reason, name)


def _visible(plan):
	"""Whether the caller can see this plan now, through the gate. A plan
	that lapsed, or whose person left, is not visible - so the answer to a
	stale screen is "here is the latest", not an error that confirms it."""
	return bool(frappe.get_list(DOCTYPE, filters={"name": str(plan or "")}, pluck="name"))


@frappe.whitelist(methods=["POST"])
def set_plan(assignment, note=None):
	"""Plan a replacement for the person in one seat assignment.

	POST only, so the note never sits in a URL or an access log. Runs as the
	user; the record's own rules and the gate decide (SEC-5)."""
	assignment = str(assignment or "").strip()
	note = str(note or "").strip() or None
	if not is_reader() or not frappe.has_permission(DOCTYPE, "create"):
		_refuse(_("Only HR Managers can plan a replacement."), "plans.set_plan")
	if note and len(note) > NOTE_MAX:
		frappe.throw(_("The note can be at most {0} characters. Shorten it and save again.").format(NOTE_MAX))
	check_assignment(assignment)

	# A plan that lapsed today may still be waiting for the daily erase. One
	# plan per assignment is a unique index, so it goes first.
	for row in _due(assignment):
		erase(row.name, row.reason)

	try:
		doc = frappe.get_doc({"doctype": DOCTYPE, "assignment": assignment, "note": note}).insert()
	except (frappe.UniqueValidationError, frappe.DuplicateEntryError):
		# Two HR Managers saved at the same moment; the first one won.
		frappe.throw(_changed())
	_log("set", doc.name)
	return {"name": doc.name, "confirmed_on": str(doc.confirmed_on),
	        "lapses_on": str(add_days(doc.confirmed_on, LIFE_DAYS))}


@frappe.whitelist(methods=["POST"])
def confirm_plan(plan):
	"""Keep a live plan for 90 days from today. No dialog; refused once the
	plan has lapsed or its person has left."""
	if not _visible(plan):
		frappe.throw(_changed())
	if not frappe.has_permission(DOCTYPE, "write", doc=plan):
		_refuse(_("Only HR Managers can confirm a plan."), "plans.confirm_plan")
	doc = frappe.get_doc(DOCTYPE, plan)
	doc.confirmed_on = nowdate()
	doc.save()
	_log("confirmed", doc.name)
	return {"name": doc.name, "confirmed_on": str(doc.confirmed_on),
	        "lapses_on": str(add_days(doc.confirmed_on, LIFE_DAYS))}


@frappe.whitelist(methods=["POST"])
def remove_plan(plan):
	"""Remove a plan: erased at once, nothing kept in the system."""
	if not _visible(plan):
		frappe.throw(_changed())
	if not frappe.has_permission(DOCTYPE, "delete", doc=plan):
		_refuse(_("Only HR Managers can remove a plan."), "plans.remove_plan")
	erase(plan, "removed")
	return {"ok": True}


# ── what is due for erasing (PRIV-3) ─────────────────────────────────────────


def _why_due(row, today):
	"""The reason word a plan must go, or None while it is live. The same
	rule as `_condition(live=True)`, read the other way round."""
	if not row.a or (row.from_date and str(row.from_date) > today) or (
			row.to_date and str(row.to_date) < today):
		return "left seat"
	if row.emp_status != "Active":
		return "left company"
	if row.seat_status == "Closed":
		return "seat closed"
	if str(row.confirmed_on) < str(add_days(today, -LIFE_DAYS)):
		return "lapsed"
	return None


def _due(assignment=None):
	"""Every plan that must be erased, with its reason, in ONE query.

	This and the erase are the only reads of the plan table that do not go
	through the gate: they must find plans nobody may see any more. Names,
	dates and statuses only - never the note, so no error here can carry it.
	"""
	rp = frappe.qb.DocType(DOCTYPE)
	a = frappe.qb.DocType(register.ASSIGNMENT)
	p = frappe.qb.DocType(register.POSITION)
	e = frappe.qb.DocType("Employee")
	q = (frappe.qb.from_(rp)
	     .left_join(a).on(a.name == rp.assignment)
	     .left_join(p).on(p.name == a.position)
	     .left_join(e).on(e.name == a.employee)
	     .select(rp.name, rp.confirmed_on, a.name.as_("a"), a.from_date, a.to_date,
	             e.status.as_("emp_status"), e.relieving_date, p.status.as_("seat_status")))
	if assignment:
		q = q.where(rp.assignment == assignment)
	today = nowdate()
	out = []
	for row in q.run(as_dict=True):
		row.reason = _why_due(row, today)
		if row.reason:
			out.append(row)
	return out


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
