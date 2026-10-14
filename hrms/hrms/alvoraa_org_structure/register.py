"""The position register, as a list somebody can actually work with.

The chart answers "what does this company look like". This answers "what seats
do we have, which are empty, and what do I need to change" - and that is a
table, not a tree. Eighty-nine seats across six stores sort and scan in a list;
in a tree you hunt.

It is also where seats are created and re-parented, because that is awkward on
a chart and obvious in a row.

WHO MAY CHANGE IT IS A SETTING, not a hard-coded role. At the first customer the
owners maintain the structure themselves and HR does not; at the next it will be
the other way round. `alvoraa_org_position_editor_roles` decides, and like the
other keys that hand out privilege it can only be changed by a System Manager,
and leaves a record when it is.

READING IS SCOPED THE SAME WAY AS EVERY OTHER HR READER (slice 030): the
companies somebody may act for, and their branches if they are tied to a store.
A branch head reads their own store and changes nothing unless the setting says
they may.
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate

from hrms.alvoraa_org_structure import settings

EDITOR_ROLES_KEY = "alvoraa_org_position_editor_roles"


def _scope():
	"""The companies and branches this reader may act for.

	Returns (companies, branches). `branches` is None for somebody who is not
	tied to a store, which means "every branch" rather than "no branch".
	"""
	from hrms.alvoraa_hr_core.access import permitted_branches, permitted_companies

	return permitted_companies(), permitted_branches()


def _may_read():
	"""Anybody who may see the whole chart, and any manager, may read the list.

	Deliberately wider than who may change it. A branch head planning next
	month's cover needs to see the empty seats in their store; letting them
	change the company's structure is a different decision.
	"""
	from hrms.alvoraa_org_structure.api import reach

	return bool(reach().get("unlimited"))


def may_edit():
	"""Whether this person may create or change a seat.

	Read from a setting rather than fixed in code, because who owns the shape of
	the organisation differs by customer. At DTC it is the owners; elsewhere it
	will be HR.
	"""
	allowed = {r.strip() for r in str(settings.get(EDITOR_ROLES_KEY)).split(",") if r.strip()}
	return bool(allowed & set(frappe.get_roles()))


def _refuse(endpoint, name=None):
	from hrms.alvoraa_hr_core.access import refuse

	refuse(
		_("You can look at the position list, but changing it is not yours to do. "
		  "Ask whoever maintains the structure in your organisation."),
		"SEC-8", endpoint, "Alvoraa Position", name)


@frappe.whitelist()
def position_table(branch=None, department=None, as_at=None):
	"""Every seat this person may see, with how full it is.

	One query for the seats, one for the people in them. Not one per row: at
	eighty-nine seats that is eighty-nine round trips for a table that renders
	in a single screen.
	"""
	if not _may_read():
		_refuse("register.position_table")
	as_at = as_at or nowdate()
	companies, branches = _scope()

	filters = {"status": ("!=", "Closed"), "company": ("in", companies)}
	if branches is not None:
		# A seat with no branch is outside every store (DEF-6), the same rule
		# every other reader follows.
		filters["branch"] = ("in", branches)
	if branch:
		asked = branch if isinstance(branch, list) else [branch]
		if branches is not None:
			asked = [b for b in asked if b in branches]
		filters["branch"] = ("in", asked)
	if department:
		filters["department"] = department

	seats = frappe.get_all(
		"Alvoraa Position", filters=filters,
		fields=["name", "position_title", "status", "is_key_position", "seats",
		        "reports_to_position", "branch", "department", "designation",
		        "grade", "company", "effective_from", "effective_to"],
		order_by="branch asc, department asc, position_title asc",
		limit_page_length=0)
	if not seats:
		return {"rows": [], "may_edit": may_edit(), "as_at": as_at}

	names = [s.name for s in seats]
	filled, people = {}, {}
	for a in frappe.get_all(
			"Alvoraa Position Assignment",
			filters={"position": ("in", names), "from_date": ("<=", as_at)},
			fields=["position", "employee", "employee_name", "weight",
			        "assignment_type", "to_date"],
			limit_page_length=0):
		if a.to_date and str(a.to_date) < str(as_at):
			continue
		filled[a.position] = filled.get(a.position, 0.0) + flt(a.weight) / 100.0
		people.setdefault(a.position, []).append({
			"employee": a.employee, "name": a.employee_name,
			"weight": flt(a.weight),
			"covering": (a.assignment_type or "Permanent") != "Permanent"})

	titles = {s.name: s.position_title for s in seats}
	rows = []
	for s in seats:
		got = filled.get(s.name, 0.0)
		rows.append({
			"id": s.name,
			"title": s.position_title,
			"branch": s.branch or "",
			"department": s.department or "",
			"designation": s.designation or "",
			"grade": s.grade or "",
			"company": s.company,
			"status": s.status,
			"key": bool(s.is_key_position),
			"seats": flt(s.seats),
			"filled": got,
			# What the table is for. Half-seats are real: two people at 50% of a
			# one-seat role leave nothing open, one of them leaves half.
			"open": max(0.0, flt(s.seats) - got),
			"reports_to": s.reports_to_position or "",
			# The parent's title, so the table reads without a second lookup.
			# Blank when the parent sits outside what this reader may see.
			"reports_to_title": titles.get(s.reports_to_position, ""),
			"people": people.get(s.name, []),
		})
	return {"rows": rows, "may_edit": may_edit(), "as_at": as_at}


@frappe.whitelist()
def save_position(name=None, position_title=None, reports_to_position=None,
                  branch=None, department=None, designation=None, grade=None,
                  seats=None, is_key_position=None, status=None, company=None):
	"""Create a seat, or change one. The hierarchy is `reports_to_position`.

	An empty seat is not a special kind of record - it is a seat with nobody
	assigned to it, which is what makes "we are recruiting for this" visible on
	the chart instead of living in a spreadsheet.
	"""
	if not may_edit():
		_refuse("register.save_position", name)

	companies, branches = _scope()
	doc = frappe.get_doc("Alvoraa Position", name) if name \
		else frappe.new_doc("Alvoraa Position")

	if name:
		# Changing a seat outside your own companies or stores is refused for
		# the same reason reading one is.
		if doc.company not in companies:
			_refuse("register.save_position", name)
		if branches is not None and (doc.branch or "") not in branches:
			_refuse("register.save_position", name)

	fields = {
		"position_title": position_title, "reports_to_position": reports_to_position,
		"branch": branch, "department": department, "designation": designation,
		"grade": grade, "seats": seats, "is_key_position": is_key_position,
		"status": status, "company": company,
	}
	for key, value in fields.items():
		if value is not None:
			doc.set(key, value)

	if not doc.company:
		doc.company = companies[0] if companies else None
	if doc.company not in companies:
		_refuse("register.save_position", name)
	if branches is not None and (doc.branch or "") not in branches:
		# Creating a seat in somebody else's store is the same mistake as
		# editing one, and is refused in the same breath.
		_refuse("register.save_position", name)
	if doc.reports_to_position and doc.reports_to_position == doc.name:
		frappe.throw(_("A position cannot report to itself."))

	doc.flags.ignore_permissions = True
	doc.save() if name else doc.insert()
	return {"ok": True, "name": doc.name, "title": doc.position_title}
