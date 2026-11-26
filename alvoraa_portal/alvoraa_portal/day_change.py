# Copyright (c) 2026, Alvoraa and contributors
# For license information, please see license.txt

"""Slice 088d - a reason for every change a person makes to a day's attendance record.

Counsel's condition is the same one 088c answers for punches: the employee is told of every
manual change, each with a reason. Here the thing changed is the Attendance row (the day's
record). The reason is taken at the point of entry and copied into the same append-only log,
`Alvoraa Punch Change` (one log, not two: the notice already reads it).

**A day record is written by the software all the time, so "who is logged in" cannot tell a
person from the system.** The scheduler runs as Administrator (`frappe.connect` sets it), and
a leave approval, a request approval, the Shift Type button and Reprocess all write Attendance
inside a person's own web request. So the test is the DOOR (`at_a_door`): was the request or
job addressed to the Attendance itself? Anything else, however it got here, is the system's
work or another record's, and passes untouched. Each path is pinned by `test_day_change_088d`.

**Which acts are listed** (only a SUBMITTED row is a day record: payroll reads docstatus 1):
a person REPLACING a day's record, a person changing a submitted row, a person cancelling one.
Marking a day that never had a record is not listed (Surbhi, 26 Nov: it is the record being made). Drafts are never listed or refused. It applies only while the
organisation's notice switch is on, like 088c.

**Cancel carries no field values** (Desk sends only the name), so the reason has to be on the
row first: pick the reason, click Update, then Cancel.
"""

import json

import frappe
from frappe import _
from frappe.model import no_value_fields
from frappe.utils import cint, getdate

import alvoraa_portal.punch_change as pc

ATTENDANCE = "Attendance"
FIELD, TEXT = pc.FIELD, pc.TEXT_FIELD
_STASH = "day_change_pending"

#: The three hrms tools that mark days with nowhere to ask a reason, and the one that imports.
BULK_MARK = "hrms.hr.doctype.attendance.attendance.mark_bulk_attendance"
TOOL_MARK = "hrms.hr.doctype.employee_attendance_tool.employee_attendance_tool.mark_employee_attendance"
UPLOAD = "hrms.hr.doctype.upload_attendance.upload_attendance.upload"
UPLOAD_JOB = "hrms.hr.doctype.upload_attendance.upload_attendance.import_attendances"
#: Desk and `frappe.client` entry points that name a document type (`doctype`, `doc` or `docs`).
#: `run_doc_method` (and its old name `runserverobj`) is what a form's `frm.call` and a plain API
#: call use to run a whitelisted method on a document, `submit` and `cancel` included (05d P1-1).
#: It names the document in `dt` or in `docs`. The Shift Type "Mark Attendance" click uses the
#: very same command with a Shift Type in `docs`, which is why the doctype is compared exactly.
_FORM_CMDS = ("frappe.desk.form.save.savedocs", "frappe.desk.form.save.cancel",
              "frappe.desk.form.save.discard", "run_doc_method", "runserverobj",
              "frappe.desk.doctype.bulk_update.bulk_update.submit_cancel_or_update_docs")
_IMPORT_CMD = "frappe.core.doctype.data_import.data_import.form_start_import"
_REST = ("/api/resource/", "/api/v2/document/")


# ── is a person at a door? ───────────────────────────────────────────────────

def _doctypes(*values):
	"""Every doctype named in a form value: a name, a document, or a list of documents."""
	found = set()
	for v in values:
		if isinstance(v, str):
			try:
				v = json.loads(v)
			except ValueError:
				found.add(v)
				continue
		for item in (v if isinstance(v, list) else [v]):
			if isinstance(item, dict):
				found.add(item.get("doctype"))
			elif isinstance(item, str):
				found.add(item)
	return found


def _import_is_attendance(name):
	return bool(name) and frappe.db.get_value("Data Import", name, "reference_doctype") == ATTENDANCE


def at_a_door():
	"""True when this request or job was addressed to the Attendance itself. In memory only,
	so a system write costs nothing here."""
	job = getattr(frappe.local, "job", None)
	if job:
		method, kwargs = job.get("method") or "", job.get("kwargs") or {}
		if method.endswith("bulk_update._bulk_action"):
			return kwargs.get("doctype") == ATTENDANCE
		if method.endswith("data_import.start_import"):
			return _import_is_attendance(kwargs.get("data_import"))
		return method == UPLOAD_JOB
	form = frappe.form_dict
	cmd = form.get("cmd") or ""
	if cmd:
		if cmd in _FORM_CMDS or cmd.startswith("frappe.client."):
			return ATTENDANCE in _doctypes(form.get("doctype"), form.get("doc"), form.get("docs"),
			                               form.get("dt"))
		if cmd == _IMPORT_CMD:
			return _import_is_attendance(form.get("data_import"))
		return cmd in (UPLOAD, BULK_MARK, TOOL_MARK)
	request = getattr(frappe.local, "request", None)
	path = getattr(request, "path", "") or ""
	if path == "/api/v2/method/run_doc_method":                    # v2 carries no `cmd`
		return ATTENDANCE in _doctypes(form.get("document"))
	return any(path == p + ATTENDANCE or path.startswith(p + ATTENDANCE + "/") for p in _REST)


def _person_at_a_door(doc):
	return at_a_door() and pc._is_a_persons_change(doc.employee)


# ── the words the paper uses ─────────────────────────────────────────────────

def _status(value):
	return "held (not yet decided)" if value == "Held" else (value or "no record")


_PAY_FIELDS = (("leave_type", "leave type"), ("half_day_status", "half day"), ("shift", "shift"))


def _was(doc):
	"""The earlier record of this day, if there was one: the row this one amends, else the
	latest cancelled row for the same person and day. The fields that move pay, not only the
	status (05d P2-1)."""
	fields = ["status"] + [f for f, _label in _PAY_FIELDS]
	if doc.get("amended_from"):
		return frappe.db.get_value(ATTENDANCE, doc.amended_from, fields, as_dict=True)
	rows = frappe.get_all(ATTENDANCE, filters={"employee": doc.employee, "attendance_date": doc.attendance_date,
	                                           "docstatus": 2, "name": ("!=", doc.name or "")},
	                      fields=fields, order_by="modified desc", limit=1, ignore_permissions=True)
	return rows[0] if rows else None


def _submit_sentence(doc, was):
	if was.status != doc.status:
		return "Day changed from %s to %s" % (_status(was.status), _status(doc.status))
	moved = [label for f, label in _PAY_FIELDS if (doc.get(f) or "") != (was.get(f) or "")]
	if moved:
		return "Day changed: %s" % ", ".join(moved)
	return "Day record replaced, still %s" % _status(doc.status)


def _changed(doc, before):
	"""The fields of a submitted row that differ from the saved copy, reasons excluded. After
	submit only the `allow_on_submit` fields can differ at all, so no list of fields is kept."""
	return [df.fieldname for df in doc.meta.fields
	        if df.fieldtype not in no_value_fields and df.fieldname not in (FIELD, TEXT)
	        and not pc.same(df, doc.get(df.fieldname), before.get(df.fieldname))]


def _update_sentence(doc, fields):
	if "alvoraa_held_confirmed" in fields or "alvoraa_confirmed_out_time" in fields:
		t = str(doc.get("alvoraa_confirmed_out_time") or "")[:5]
		if cint(doc.get("alvoraa_held_confirmed")) and t:
			return "Out time confirmed as %s for a day with a missing punch" % t
	return "Day record changed"


def _refuse(message, rule, doc):
	pc.access.log_refusal(rule, "Attendance " + rule, ATTENDANCE, doc.name)
	frappe.throw(message)


def _demand(doc, what):
	"""The reason on the row, validated, or a refusal. Returns the stash the writer reads."""
	reason, text = doc.get(FIELD), doc.get(TEXT)
	if not reason:
		_refuse(_("Pick a reason for this change. It is printed on the employee's monthly "
		          "notice. (If you are importing or calling the API, put it in the 'Reason For "
		          "This Change' column, {0}, on every row.)").format(FIELD), "088d-reason", doc)
	problem = pc.reason_problem(reason, text)
	if problem:
		_refuse(problem, "088d-reason-list", doc)
	return {"reason": reason, "text": text, "what": what}


def _write(doc):
	pending = doc.flags.pop(_STASH, None)
	if pending:
		pc.add_row(doc.employee, getdate(doc.attendance_date), pending["reason"], pending["text"],
		           pending["what"], attendance=doc.name)
		pc.access.security_logger().info("day_change logged attendance=%s user=%s", doc.name,
		                                 frappe.session.user)


# ── the handlers (Attendance doc_events) ─────────────────────────────────────

def before_validate(doc, method=None):
	"""Runs for save and submit. A draft is not a day record yet, so only a row being
	submitted is judged. **Only a change to a day that already had a record is listed** (Surbhi,
	26 Nov 2026): a day with no earlier record being marked for the first time is the record
	being made, so it is neither asked about nor listed, and Mark Attendance keeps working.
	The reason is blanked once it is taken, so it never sits on the row."""
	if cint(doc.docstatus) != 1 or not _person_at_a_door(doc):
		return
	was = _was(doc)
	if was is not None:
		doc.flags[_STASH] = _demand(doc, _submit_sentence(doc, was))
	doc.set(FIELD, None)
	doc.set(TEXT, None)


def on_submit(doc, method=None):
	_write(doc)


def before_update_after_submit(doc, method=None):
	"""A person changes a submitted row. A save that changes nothing but the reason is the
	first step of a cancel and is left alone, so the reason stays on the row."""
	if not _person_at_a_door(doc):
		return
	before = doc.get_doc_before_save()
	fields = _changed(doc, before) if before else []
	if not fields:
		return
	doc.flags[_STASH] = _demand(doc, _update_sentence(doc, fields))
	doc.set(FIELD, None)
	doc.set(TEXT, None)


def on_update_after_submit(doc, method=None):
	_write(doc)


def before_cancel(doc, method=None):
	if not _person_at_a_door(doc):
		return
	if not doc.get(FIELD):
		_refuse(_("Pick a reason first: open this day, choose 'Reason For This Change', click "
		          "Update, then cancel it. The reason is printed on the employee's notice and "
		          "Cancel cannot carry one."), "088d-cancel", doc)
	doc.flags[_STASH] = _demand(doc, "Day record reset so it is worked out again from your "
	                                 "punches (was %s)" % _status(doc.status))


def on_cancel(doc, method=None):
	"""Whoever cancelled, a reason left sitting on the row is cleared (05d P3-10): a person may
	have saved one and then the system cancelled the day. No reason on the row, no query."""
	_write(doc)
	if doc.get(FIELD) or doc.get(TEXT):
		frappe.db.set_value(ATTENDANCE, doc.name, {FIELD: None, TEXT: None}, update_modified=False)


# ── the two tools with nowhere to ask for a reason ───────────────────────────

def _refuse_the_tool(name, why):
	"""Refused up front, loudly. Stock `mark_bulk_attendance` swallows every error inside its
	loop and then says "Attendance marked successfully", so a refusal left to the per-row rule
	would never reach the person."""
	frappe.throw(_("'{0}' cannot do this while change notices are on: {1} Open the Attendance "
	               "form, pick a reason, save and submit.").format(name, why))


def _replaces_a_record(employees, days):
	"""A day that had a record, now cancelled, would be replaced: that change needs a reason."""
	people = [e for e in employees if e and pc._is_a_persons_change(e)]
	return bool(people and days and frappe.db.exists(
		ATTENDANCE, {"employee": ("in", people), "attendance_date": ("in", days), "docstatus": 2}))


@frappe.whitelist()
def mark_bulk_attendance(data: str | dict):
	from hrms.hr.doctype.attendance.attendance import mark_bulk_attendance as stock

	frappe.has_permission(ATTENDANCE, "write", throw=True)    # before anything observable (05d P2-3)
	payload = (json.loads(data) if isinstance(data, str) else data) or {}
	if _replaces_a_record([payload.get("employee")], payload.get("unmarked_days") or []):
		_refuse_the_tool("Mark Attendance", "one of these days had a record that was cancelled, and "
		                 "putting a new one in its place is a change that needs a reason.")
	return stock(data)


@frappe.whitelist()
def mark_employee_attendance(
	employee_list: list | str,
	status: str,
	date: str,
	leave_type: str | None = None,
	company: str | None = None,
	late_entry: int | None = None,
	early_exit: int | None = None,
	shift: str | None = None,
	mark_half_day: bool | None = False,
	half_day_status: str | None = None,
	half_day_employee_list: list | str | None = None,
):
	"""Refuses the half-day tick, which rewrites existing rows with `qb.update` and so fires no
	hook at all (A24), and a replacement of a cancelled day. A first mark passes."""
	from hrms.hr.doctype.employee_attendance_tool.employee_attendance_tool import (
		mark_employee_attendance as stock,
	)

	def names(v):
		return json.loads(v) if isinstance(v, str) else (v or [])

	frappe.has_permission(ATTENDANCE, "write", throw=True)    # before anything observable (05d P2-3)
	if mark_half_day and any(pc._is_a_persons_change(e) for e in names(half_day_employee_list) if e):
		_refuse_the_tool("Employee Attendance Tool", "the half-day tick changes days that already "
		                 "have a record, and it cannot ask for a reason.")
	if _replaces_a_record(names(employee_list), [date]):
		_refuse_the_tool("Employee Attendance Tool", "one of these days had a record that was "
		                 "cancelled, and putting a new one in its place is a change that needs a reason.")
	return stock(employee_list, status, date, leave_type, company, late_entry, early_exit, shift,
	             mark_half_day, half_day_status, half_day_employee_list)


# ── install ──────────────────────────────────────────────────────────────────

def after_migrate():
	"""The two fields on Attendance where a person gives the reason. `allow_on_submit`, because
	a cancel carries nothing and the reason has to be on the submitted row first. In both hook
	lists, like the punch's: a site built with `bench install-app` never runs a migrate."""
	if not (frappe.db.exists("DocType", ATTENDANCE) and frappe.db.exists("DocType", pc.LOG)):
		return False
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	options = frappe.get_meta(pc.LOG).get_field("reason_code").options
	create_custom_fields({ATTENDANCE: [{
		"fieldname": FIELD, "fieldtype": "Select", "label": "Reason For This Change",
		"options": "\n" + options, "insert_after": "attendance_date", "allow_on_submit": 1,
		"no_copy": 1, "print_hide": 1,
		"description": "Needed when you mark or change a day for somebody else, if your "
		               "organisation prints change notices. To cancel a day: pick it, click "
		               "Update, then cancel. Printed on the employee's notice. Blank once saved.",
	}, {
		"fieldname": TEXT, "fieldtype": "Data", "label": "Reason Text", "length": pc.TEXT_MAX,
		"insert_after": FIELD, "allow_on_submit": 1, "no_copy": 1, "print_hide": 1,
		"depends_on": "eval:doc.%s=='Other'" % FIELD,
		"description": "Only with the reason 'Other'. Printed on the employee's notice. Do not "
		               "write medical details or the names of other people.",
	}]})
	return True
