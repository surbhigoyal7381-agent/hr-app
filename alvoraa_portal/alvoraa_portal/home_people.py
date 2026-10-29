"""Slice 076, Part C: birthdays and work anniversaries on Home.

Who sees what (PRIV-5, PRIV-7): people in the viewer's own company AND branch,
Active, with a birthday or a joining day this month, who have not hidden
themselves. Each row is the full name, the kind, the day and the month, and for
an anniversary the completed years. Never an id, a date, a year or an age.

Date of birth and date of joining are field-rights level 2, so a plain employee
cannot read them through Frappe. `_month_rows` reads them on the server on
purpose, with one query-builder query that runs without Frappe's permission
check, and nothing but the fixed keys leaves this file.

The organisation switch (`alvoraa_birthdays_on_home` on HR Settings) ships OFF.
Off means an empty answer before any Employee query (PRIV-6). It is saved
through the HR Settings document, so Frappe's own history says who changed it.

The opt-out (`alvoraa_hide_birthday` on Employee) is set only by the person,
through `set_birthday_hide`, which takes no employee argument. Any other save of
that field - desk, REST, import - is put back by `keep_hide_birthday`.
"""

import calendar

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.query_builder.functions import Extract
from frappe.utils import cint, getdate, today

from hrms.alvoraa_hr_core.access import refuse

SWITCH = "alvoraa_birthdays_on_home"
HIDE = "alvoraa_hide_birthday"
HR_ROLES = {"HR Manager", "System Manager"}
CARD_ROWS = 5

FIELDS = {
	"HR Settings": [{
		"fieldname": SWITCH, "fieldtype": "Check", "default": "0",
		"label": "Birthdays and anniversaries on Home",
		"insert_after": "send_work_anniversary_reminders",
		"description": "Staff see people in their own branch who have a birthday or work "
		               "anniversary this month: name, day, and years of service. Never age.",
	}],
	"Employee": [{
		"fieldname": HIDE, "fieldtype": "Check", "default": "0", "read_only": 1,
		"label": "Hidden from birthdays on Home", "insert_after": "date_of_joining",
		"description": "Set only by the employee, in the portal's My profile.",
	}],
	"Expense Claim": [{
		"fieldname": "alvoraa_decline_reason", "fieldtype": "Small Text", "read_only": 1,
		"label": "Decline reason", "insert_after": "approval_status",
		"description": "Written by the approver when they decline the claim in the portal.",
	}],
}


def after_migrate():
	"""The three Custom Fields. Safe to run twice."""
	create_custom_fields(FIELDS, ignore_validate=True)


def keep_hide_birthday(doc, method=None):
	"""Employee validate: nobody but the person changes their opt-out (AC-105).
	The person's own endpoint writes the column directly, so it never comes here."""
	if doc.is_new() or not doc.has_value_changed(HIDE):
		return
	before = doc.get_doc_before_save()
	doc.set(HIDE, cint(before.get(HIDE)) if before else 0)


def _switch_on():
	return bool(cint(frappe.db.get_single_value("HR Settings", SWITCH)))


def _me(user):
	return frappe.db.get_value("Employee", {"user_id": user, "status": "Active"},
	                           ["name", "company", "branch", HIDE], as_dict=True)


def _refuse_guest():
	if frappe.session.user == "Guest":
		frappe.throw(_("Please sign in."), frappe.PermissionError)


def _day(month, day, year):
	"""29 Feb shows on 28 Feb in a year that has no 29 Feb."""
	return min(day, calendar.monthrange(year, month)[1])


def _month_rows(company, branch):
	"""One query: the branch's Active, not hidden people with a date this month."""
	now = getdate(today())
	E = frappe.qb.DocType("Employee")
	people = (
		frappe.qb.from_(E)
		.select(E.employee_name, E.date_of_birth, E.date_of_joining)
		.where((E.status == "Active") & (E.company == company) & (E.branch == branch)
		       & ((E[HIDE] == 0) | E[HIDE].isnull()))
		.where((Extract("month", E.date_of_birth) == now.month)
		       | (Extract("month", E.date_of_joining) == now.month))
	).run(as_dict=True)
	rows = []
	for p in people:
		dob, doj = p.date_of_birth, p.date_of_joining
		if dob and dob.month == now.month:
			rows.append({"name": p.employee_name, "kind": "birthday",
			             "day": _day(now.month, dob.day, now.year), "month": now.month})
		if doj and doj.month == now.month and now.year - doj.year >= 1:
			rows.append({"name": p.employee_name, "kind": "anniversary",
			             "day": _day(now.month, doj.day, now.year), "month": now.month,
			             "years": now.year - doj.year})
	# Today and the days to come first, then the earlier days, latest first.
	rows.sort(key=lambda r: (r["day"] < now.day, r["day"] if r["day"] >= now.day else -r["day"],
	                         r["name"] or ""))
	return rows


@frappe.whitelist()
def birthdays_this_month(see_all=0):
	"""The Home card and its See all sheet; My profile reads `on` and `hidden`.

	Off: `{"on": 0}` and no Employee query at all. No Active Employee or no
	branch: an empty list (fail closed)."""
	_refuse_guest()
	if not _switch_on():
		return {"on": 0}
	me = _me(frappe.session.user)
	if not me:
		return {"on": 1, "hidden": 0, "total": 0, "rows": []}
	rows = _month_rows(me.company, me.branch) if me.branch else []
	return {"on": 1, "hidden": cint(me.get(HIDE)), "total": len(rows),
	        "rows": rows if cint(see_all) else rows[:CARD_ROWS]}


@frappe.whitelist(methods=["POST"])
def set_birthday_hide(value):
	"""The person's own tick, and nobody else's: there is no employee argument."""
	_refuse_guest()
	me = _me(frappe.session.user)
	if not me:
		frappe.throw(_("Your login is not linked to an active employee record. Ask HR to link it."),
		             frappe.PermissionError)
	frappe.db.set_value("Employee", me.name, HIDE, 1 if cint(value) else 0)
	return {"hidden": 1 if cint(value) else 0}


def _require_hr(endpoint):
	_refuse_guest()
	if not HR_ROLES & set(frappe.get_roles()):
		refuse(_("Only an HR Manager can change this."), "076-PRIV-6", endpoint)


def _last_change():
	v = frappe.get_all("Version", filters={"ref_doctype": "HR Settings", "docname": "HR Settings",
	                                       "data": ["like", "%" + SWITCH + "%"]},
	                   fields=["owner", "creation"], order_by="creation desc", limit=1)
	if not v:
		return {"changed_by": "", "changed_on": ""}
	return {"changed_by": frappe.db.get_value("User", v[0].owner, "full_name") or "",
	        "changed_on": str(v[0].creation)[:10]}


@frappe.whitelist()
def birthdays_switch_state():
	"""Organisation settings: the switch, who last changed it and when, and how
	many people Home changes for (the confirm before switching off)."""
	_require_hr("birthdays_switch_state")
	return dict({"on": 1 if _switch_on() else 0,
	             "people": frappe.db.count("Employee", {"status": "Active"})}, **_last_change())


@frappe.whitelist(methods=["POST"])
def set_birthdays_switch(value):
	"""HR Manager or System Manager. Saved through the document, so the change is
	in HR Settings' own history (AC-103)."""
	_require_hr("set_birthdays_switch")
	settings = frappe.get_doc("HR Settings")
	settings.set(SWITCH, 1 if cint(value) else 0)
	settings.save(ignore_version=False)  # the Version row is "last changed by" (tests too)
	return birthdays_switch_state()
