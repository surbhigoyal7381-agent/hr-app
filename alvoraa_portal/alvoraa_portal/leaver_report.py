"""Slice 089: a manager reports that a direct report has left, and sees a little
more of their own team when the organisation allows it.

**The report is a request, never a fact.** Nothing here writes the Employee's
`status` or `relieving_date`. A report is one Frappe ToDo per person who can
confirm it; HR confirms by saving the Employee as Left, which closes the ToDos.

**Why the ToDo is made by hand and not with `assign_to.add` (read in Frappe
16.33.1, 22 Nov 2026).** `assign_to` shares the Employee record with the
assignee, emails the description unescaped, and - because it passes a
reference - makes `ToDo.on_update` write an "Assigned" Comment on the Employee
and the confirmers' user ids into the Employee's `_assign` column. Each of
those is something this slice must not do (SEC-7, SEC-11, OPS-19, PRIV-2). A
plain insert does none of them, and the ToDo carries the person in its own
field instead of a reference.

The one Custom Field, `alv_leaver_employee` (indexed, Surbhi 22 Nov: the locking read then touches one person's rows, not the whole ToDo table), is both the
marker ("this ToDo is a leaver report") and the person. The last working day is
the ToDo's own Due Date.
"""

import frappe
from frappe import _
from frappe.utils import add_days, escape_html, formatdate, getdate, nowdate

import hrms.alvoraa_org_structure.people_fields as people_fields
import hrms.alvoraa_org_structure.settings as org_settings
from alvoraa_portal.field_app_limits import SELF_KEY, _limited

FIELD = "alv_leaver_employee"
SEES_KEY = "alvoraa_manager_sees_team_details"
DAYS_BACK = 31
DAYS_AHEAD = 60
# The ToDo guard lets a ToDo carrying the marker in only while this is set, and
# only `send_leaver_report` sets it. A browser cannot send a server-side flag.
_FLAG = "alv_leaver_report"
_DATE_FORMAT = "dd MMM yyyy"

LEAVER_FIELD = [
	{"fieldname": FIELD, "fieldtype": "Data", "label": "Leaver report: employee",
	 "insert_after": "allocated_to", "hidden": 1, "read_only": 1, "no_copy": 1,
	 "search_index": 1},
]


def after_migrate():
	"""The Custom Field, the way slice 080 makes its field: in a hook that runs
	on migrate AND install, so a new tenant has it too. Writes only what is
	missing, so a second migrate adds nothing."""
	if not frappe.db.exists("DocType", "ToDo"):
		return False
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({"ToDo": LEAVER_FIELD})
	return True


def _day(value):
	return formatdate(value, _DATE_FORMAT)


def _name_of(user):
	return frappe.db.get_value("User", user, "full_name") or user


# ── who may see what of a team member ────────────────────────────────────────

def is_direct_active_report(employee_id, manager_employee):
	"""`reports_to` is the caller's own Active Employee and the person is
	Active. NOT `get_effective_manager`, whose HR-Manager fallback for a person
	with no manager must not open anybody's phone or address (SEC-2)."""
	row = frappe.db.get_value("Employee", employee_id, ["reports_to", "status"], as_dict=True)
	return bool(row and manager_employee and row.reports_to == manager_employee
	            and row.status == "Active" and employee_id != manager_employee)


def personal_details(employee_id, manager_employee):
	"""The ticked personal fields of a direct report, or {} (SEC-1, SEC-2).

	Both ends of the list are closed: the setter refuses an off-list name and
	`people_fields.allowed` intersects again here, so a value written straight
	into `DefaultValue` produces nothing. Read live on every call: no cache, so
	an untick hides the data on the next request.
	"""
	ticked = people_fields.allowed(SEES_KEY, frappe.db.get_default(SEES_KEY))
	if not ticked or not is_direct_active_report(employee_id, manager_employee):
		return {}
	return frappe.db.get_value("Employee", employee_id, list(ticked), as_dict=True) or {}


# ── the report itself ────────────────────────────────────────────────────────

def _refuse(message, rule, employee=None, endpoint="leaver_report.send_leaver_report"):
	from hrms.alvoraa_hr_core.access import refuse

	refuse(message, rule, endpoint, "Employee", employee)


@frappe.whitelist(methods=["POST"])
@_limited(SELF_KEY, "user", limit=10)
def send_leaver_report(employee: str | None = None, last_working_day: str | None = None):
	"""A manager reports that one direct report has left (US-1).

	POST, rate limited per user (OPS-12). It takes a person and a date and
	nothing else: no free text. One request, one transaction, no queue job.
	"""
	from alvoraa_portal.hr_api import _get_employee

	if frappe.session.user in ("Guest", ""):
		frappe.throw(_("Please sign in."), frappe.PermissionError)
	me = _get_employee()
	employee = (employee or "").strip()
	row = frappe.db.get_value(
		"Employee", employee,
		["name", "employee_name", "status", "reports_to", "company", "user_id", "date_of_joining"],
		as_dict=True) if employee else None
	# One sentence for "no such person", "not yours" and "yourself": the answer
	# must not tell a caller who exists. It names nobody.
	if not me or not row or row.name == me.name or row.reports_to != me.name:
		_refuse(_("This person does not report to you, so you cannot report this. Ask HR."),
		        "089-SEC-6", employee or None)
	if row.status != "Active":
		_refuse(_("This person is not active, so there is nothing to report. Ask HR."),
		        "089-SEC-6", employee)

	try:
		last_day = getdate(last_working_day)
	except Exception:
		last_day = None
	today = getdate(nowdate())
	if not last_day:
		_refuse(_("Give the last working day as a date."), "089-SEC-6", employee)
	if last_day < add_days(today, -DAYS_BACK) or (
			row.date_of_joining and last_day < getdate(row.date_of_joining)):
		_refuse(_("The last working day cannot be more than {0} days ago. Check the date.")
		        .format(DAYS_BACK), "089-SEC-6", employee)
	if last_day > add_days(today, DAYS_AHEAD):
		_refuse(_("The last working day cannot be more than {0} days ahead. Check the date.")
		        .format(DAYS_AHEAD), "089-SEC-6", employee)

	# Two taps at once: lock the person's row, then look, then write. The
	# second request waits here and then finds the first one's ToDos.
	frappe.db.get_value("Employee", employee, "name", for_update=True)
	# A locking read: a plain read here would use the snapshot taken before the
	# wait and miss the first request's committed ToDos (REPEATABLE READ).
	open_rows = frappe.db.get_values("ToDo", {FIELD: employee, "status": "Open"},
	                                 ["assigned_by", "creation"], as_dict=True, for_update=True)
	if open_rows:
		mine = [r for r in open_rows if r.assigned_by == frappe.session.user]
		if mine:
			_refuse(_("You already reported this person on {0}. It has not been confirmed yet.")
			        .format(_day(mine[0].creation)), "089-SEC-6", employee)
		_refuse(_("This person already has an open report. Ask HR."), "089-SEC-6", employee)

	recipients = _recipients(row)
	if not recipients:
		_refuse(_("Nobody can confirm this yet. Ask HR."), "089-SEC-7", employee)

	description = _("Confirm that {0} left. Last working day {1}. Reported by {2} on {3}.").format(
		'<a href="/app/employee/{0}">{1}</a>'.format(escape_html(row.name), escape_html(row.employee_name)),
		_day(last_day), escape_html(_name_of(frappe.session.user)), _day(today))

	frappe.db.savepoint("leaver_report")
	frappe.flags[_FLAG] = True
	try:
		for user in recipients:
			frappe.get_doc({
				"doctype": "ToDo", "allocated_to": user, "assigned_by": frappe.session.user,
				"description": description, "date": last_day, "status": "Open",
				"priority": "Medium", FIELD: row.name,
			}).insert()
	except Exception:
		frappe.db.rollback(save_point="leaver_report")
		frappe.log_error(f"leaver report failed for {row.name}", "089 leaver report")
		frappe.throw(_("The report could not be sent. Nothing was saved. Try again, or ask HR."))
	finally:
		frappe.flags[_FLAG] = False
	return {"ok": True, "last_working_day": str(last_day), "reported_on": str(today)}


def _recipients(row):
	"""Enabled holders of the confirming role who can save Left, whose company
	scope includes the person's company, minus the reporter and the person
	(SEC-7). The cap is checked on the role's whole holder list first, so the
	per-person company check below is at most `CONFIRMER_CAP` calls."""
	from hrms.alvoraa_hr_core.access import permitted_companies

	holders = org_settings.eligible_confirmers(org_settings.confirm_role())
	if len(holders) > org_settings.CONFIRMER_CAP:
		return []
	return [u for u in holders
	        if u not in (frappe.session.user, row.user_id)
	        and row.company in permitted_companies(u)
	        and frappe.has_permission("Employee", "write", doc=row.name, user=u)]


# ── what the screens read ────────────────────────────────────────────────────

def open_reports_by(employee_ids):
	"""{employee: {"last_day", "reported_on"}} for the open reports this user
	made, in ONE query whatever the number of people (AC-52)."""
	ids = [e for e in dict.fromkeys(employee_ids or []) if e]
	if not ids:
		return {}
	rows = frappe.get_all(
		"ToDo", filters={FIELD: ("in", ids), "status": "Open",
		                 "assigned_by": frappe.session.user},
		fields=[FIELD, "date", "creation"], order_by="creation desc", limit_page_length=0)
	out = {}
	for r in rows:
		out.setdefault(r.get(FIELD), {"last_day": str(r.date), "reported_on": str(r.creation)[:10]})
	return out


def open_report_about(employee_id):
	"""The line the person sees on My profile: who reported and the date. Never
	the confirmers (PRIV-2). One query, the caller's OWN record."""
	rows = frappe.get_all(
		"ToDo", filters={FIELD: employee_id, "status": "Open"},
		fields=["assigned_by", "date"], order_by="creation desc", limit=1)
	if not rows:
		return None
	return {"by": _name_of(rows[0].assigned_by), "last_day": str(rows[0].date)}


# ── hooks ────────────────────────────────────────────────────────────────────

def guard_todo(doc, method=None):
	"""doc_events `validate` and `on_trash` on ToDo (SEC-9).

	Only a ToDo carrying the marker is looked at; every other ToDo costs one
	attribute read. The reporter cannot edit or delete the notice after
	sending, and nobody can plant a marked ToDo by hand.
	"""
	if method == "on_trash":
		if doc.get(FIELD) and frappe.session.user == doc.assigned_by:
			_refuse(_("You cannot remove a leaver report. Ask HR."), "089-SEC-9",
			        doc.get(FIELD), "todo.on_trash")
		return
	if doc.is_new():
		if doc.get(FIELD) and not frappe.flags.get(_FLAG):
			_refuse(_("A leaver report can only be made with the Report button."),
			        "089-SEC-9", doc.get(FIELD), "todo.validate")
		return
	before = doc.get_doc_before_save()
	if not before or not (before.get(FIELD) or doc.get(FIELD)):
		return
	changed = (before.get(FIELD) != doc.get(FIELD)
	           or str(before.date or "") != str(doc.date or ""))
	if changed or frappe.session.user == before.assigned_by:
		_refuse(_("A leaver report cannot be changed by the person who sent it. Ask HR."),
		        "089-SEC-9", before.get(FIELD), "todo.validate")


def guard_share(doc, method=None):
	"""doc_events `validate` on DocShare (SEC-9, SEC-10): a leaver ToDo is never
	shared, with one login or with everyone. Role `All` holds the share right on
	ToDo and the reporter owns these rows, so without this a manager could open
	the notice to the whole tenant, or give someone write on it. Nothing in 089
	shares a ToDo (no assign_to), so there is no role that needs the exception.
	Every other share costs one attribute read."""
	if doc.share_doctype == "ToDo" and frappe.db.get_value("ToDo", doc.share_name, FIELD):
		_refuse(_("A leaver report cannot be shared. Ask HR."), "089-SEC-10",
		        None, "docshare.validate")


def _tell(user, todo, text):
	"""One bell line. Type "Alert" is in Frappe's `notification_skip_email_types`,
	so this never sends email (OPS-19). The portal bell lists it because
	`notices.LEAVER` is "ToDo" (M-1). `todo` is the name of one of the reporter's
	own leaver ToDos, so Desk's bell link opens a real page (r2-2). `text` is
	already escaped."""
	frappe.get_doc({"doctype": "Notification Log", "type": "Alert", "for_user": user,
	                "document_type": "ToDo", "document_name": todo,
	                "subject": text, "email_content": text}).insert(ignore_permissions=True)


def on_todo_update(doc, method=None):
	"""A confirmer closes a leaver ToDo while the person is not Left: the
	report was declined. Close the other confirmers' copies and tell the
	reporter once (AC-17). If the person IS Left, the Employee hook has
	already spoken."""
	if not (doc.get(FIELD) and doc.has_value_changed("status")
	        and doc.status in ("Closed", "Cancelled")):
		return
	person = frappe.db.get_value("Employee", doc.get(FIELD), ["status", "employee_name"], as_dict=True)
	if not person or person.status == "Left":
		return
	try:
		frappe.db.set_value("ToDo", {FIELD: doc.get(FIELD), "status": "Open"}, "status", "Closed")
		_tell(doc.assigned_by, doc.name, _(
			"The report about {0} was closed without being confirmed on {1}. "
			"{0} stays on your team. Ask HR why.").format(
				escape_html(person.employee_name), _day(nowdate())))
	except Exception:
		frappe.log_error(f"leaver report outcome failed for {doc.get(FIELD)}", "089 leaver report")


def on_employee_update(doc, method=None):
	"""doc_events `on_update` on Employee. Fires on every save of every
	employee, so the first line returns unless the status just became Left
	(zero queries on an ordinary save). Closes the open reports and tells each
	reporter once. Can never fail an Employee save."""
	if doc.status != "Left" or not doc.has_value_changed("status"):
		return
	try:
		rows = frappe.get_all("ToDo", filters={FIELD: doc.name, "status": "Open"},
		                      fields=["name", "assigned_by"], limit_page_length=0)
		if not rows:
			return
		frappe.db.set_value("ToDo", {FIELD: doc.name, "status": "Open"}, "status", "Closed")
		first = {}
		for r in rows:
			if r.assigned_by:
				first.setdefault(r.assigned_by, r.name)
		for reporter, todo in sorted(first.items()):
			_tell(reporter, todo, _("Confirmed: {0} left on {1}.").format(
				escape_html(doc.employee_name), _day(doc.relieving_date or nowdate())))
	except Exception:
		frappe.log_error(f"leaver report close failed for {doc.name}", "089 leaver report")


def on_employee_trash(doc, method=None):
	"""Deleting an Employee also deletes its leaver ToDos. Frappe removes ToDos
	by `reference_type`, which these do not carry, so without this a deleted
	person's name would stay behind in an orphan row. The outcome lines in the
	reporters' bells point at those ToDos, and Frappe's own link clean-up cannot
	find them once the ToDos are gone, so they go first (r2-1)."""
	try:
		todos = frappe.get_all("ToDo", filters={FIELD: doc.name}, pluck="name", limit_page_length=0)
		if todos:
			frappe.db.delete("Notification Log", {"document_type": "ToDo", "document_name": ("in", todos)})
		frappe.db.delete("ToDo", {FIELD: doc.name})
	except Exception:
		frappe.log_error(f"leaver report cleanup failed for {doc.name}", "089 leaver report")
