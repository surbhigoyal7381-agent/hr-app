"""Slice 057 (A): a CRM lead or deal reaching a status creates that step's tasks.

The steps are rows of "Alvoraa CRM Step Task", keyed by (Lead or Deal, lead type,
status), filled in by a sales manager in the desk. On every save of a CRM Lead or
CRM Deal this returns at once, with no query, unless the status changed and the
record has a lead type. Then one query finds the matching steps, and each one
becomes a standard CRM Task - CRM itself assigns it and notifies the person.

A broken step never stops a salesperson changing a status: its error goes to the
Error Log with the record name only, and the status change goes through.

Also here: the "Lead / Deal" column on CRM Task (4 Oct). Every task, ours or made by
hand, carries a readable "<person> – <company>" for the lead or deal it is about, so the
CRM Tasks list can show it. One read of the lead or deal, and only when the task is new
or its reference changed.
"""
import frappe
from frappe.core.doctype.communication.email import make as make_email
from frappe.utils import add_days, today

RULE = "Alvoraa CRM Step Task"
# Made by Customize Form from the label "Lead Type"; the same name on lead and deal,
# so CRM copies it across when a lead is converted.
LEAD_TYPE_FIELD = "custom_lead_type"
DUE_TIME = "18:00:00"   # end of the working day, so a task due today is not overdue at 9 am
TASK_LABEL = "alvoraa_lead_deal"
TASK_LABEL_FIELD = {"fieldname": TASK_LABEL, "label": "Lead / Deal", "fieldtype": "Data", "read_only": 1,
					"in_list_view": 1, "in_standard_filter": 1, "insert_after": "reference_docname"}
NAME_FIELDS = ["name", "lead_name", "first_name", "last_name", "organization"]   # on both lead and deal


def on_status_change(doc, method=None):
	"""doc_events on_update for CRM Lead and CRM Deal (also runs on insert)."""
	if frappe.flags.in_import:
		return  # a Data Import loads history; steps start on the next real status change (M3)
	lead_type = doc.get(LEAD_TYPE_FIELD)
	if not lead_type or not doc.has_value_changed("status"):
		return
	steps = frappe.get_all(
		RULE,
		filters={"applies_to": doc.doctype, "lead_type": lead_type, "status": doc.status},
		fields=["name", "task_title", "assign_to", "due_in_days", "email_template"],
	)
	for step in steps:
		# Task and email each get their own savepoint: a failed email never takes the task with it.
		made = _guarded(doc, step, "crm_step", _make_task)
		if made and step.email_template and doc.get("email"):
			_guarded(doc, step, "crm_step_email", _send_email)


def _guarded(doc, step, savepoint, work):
	frappe.db.savepoint(savepoint)
	try:
		return work(doc, step)
	except Exception:  # noqa: BLE001 - a broken step must not block the status change
		frappe.db.rollback(save_point=savepoint)
		# Plain traceback: the default one carries the local variables, which hold
		# the lead's name and email address.
		frappe.log_error(title=f"CRM step {step.name} failed on {doc.doctype} {doc.name}",
						 message=frappe.get_traceback(with_context=False),
						 reference_doctype=doc.doctype, reference_name=doc.name)
		return None


def _make_task(doc, step):
	"""True when a task was made; False when an open one is already there."""
	if frappe.db.exists("CRM Task", {
		"reference_doctype": doc.doctype,
		"reference_docname": doc.name,
		"title": step.task_title,
		"status": ["not in", ["Done", "Canceled"]],
	}):
		return False  # moved back and forth: the open task is still there
	frappe.get_doc({
		"doctype": "CRM Task",
		"title": step.task_title,
		"assigned_to": step.assign_to,
		"status": "Todo",
		"priority": "Medium",
		"due_date": f"{add_days(today(), step.due_in_days or 0)} {DUE_TIME}",
		"description": frappe._("Step started when this record moved to {0}.").format(doc.status),
		"reference_doctype": doc.doctype,
		"reference_docname": doc.name,
	}).insert(ignore_permissions=True)   # a system action; the step row was approved by a manager
	# CRM's own assignment, so the person can open the record the task is about. The CRM
	# then makes them the Lead/Deal Owner; earlier owners keep access through their own
	# assignment (Surbhi, 2 Oct: option b).
	doc.assign_agent(step.assign_to)
	# The lead page's task list does not reload on a status change. CRM's own socket
	# listener reloads the cached resource with this key, for whoever has the page open
	# (Activities.vue joins this record's room, after a permission check).
	frappe.publish_realtime("refetch_resource", {"cache_key": ["activity", doc.name]},
							doctype=doc.doctype, docname=doc.name, after_commit=True)
	return True


def _send_email(doc, step):
	mail = frappe.get_doc("Email Template", step.email_template).get_formatted_email(doc.as_dict())
	# make() checks that the person changing the status may email this record.
	make_email(doctype=doc.doctype, name=doc.name, subject=mail["subject"], content=mail["message"],
			   recipients=doc.email, send_email=True, email_template=step.email_template)


# ── the "Lead / Deal" column on CRM Task ─────────────────────────────────────

def set_task_label(task, method=None):
	"""doc_events validate for CRM Task. Harmless before the field exists."""
	if not (task.is_new() or task.has_value_changed("reference_doctype")
			or task.has_value_changed("reference_docname")):
		return
	row = None
	if task.reference_doctype in ("CRM Lead", "CRM Deal") and task.reference_docname:
		row = frappe.db.get_value(task.reference_doctype, task.reference_docname, NAME_FIELDS, as_dict=True)
		# Only a record the person saving may open: otherwise anyone could point a task at
		# a guessed lead number and read its person and company off the task (review, 4 Oct).
		if row and not frappe.has_permission(task.reference_doctype, "read", doc=task.reference_docname):
			row = None
	task.set(TASK_LABEL, task_label(task.reference_doctype, row))


def refresh_task_labels(doc, method=None):
	"""doc_events on_update for CRM Lead and CRM Deal: a corrected or erased name or company
	reaches its tasks too. One update, only when one of those fields changed."""
	if not doc.get_doc_before_save() or not frappe.get_meta("CRM Task").has_field(TASK_LABEL):
		return  # new record (no tasks yet), or the column is not on this site yet
	if not any(doc.has_value_changed(f) for f in NAME_FIELDS[1:]):
		return
	frappe.db.set_value("CRM Task", {"reference_doctype": doc.doctype, "reference_docname": doc.name},
						TASK_LABEL, task_label(doc.doctype, doc), update_modified=False)


def task_label(reference_doctype, row):
	"""'<person> – <company>' for a lead, '<company> – <person>' for a deal; empty parts dropped."""
	if not row or reference_doctype not in ("CRM Lead", "CRM Deal"):
		return ""
	person = row.lead_name or " ".join(p for p in (row.first_name, row.last_name) if p)
	parts = [person, row.organization] if reference_doctype == "CRM Lead" else [row.organization, person]
	parts = [p for i, p in enumerate(parts) if p and p not in parts[:i]]   # CRM may copy the company into lead_name
	return (" – ".join(parts) or row.name)[:140]   # a Data column holds 140


def ensure_task_label_field():
	"""after_migrate: the column on every site with CRM; a no-op without it. Safe to run twice."""
	if not frappe.db.exists("DocType", "CRM Task"):
		return False
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
	# update=False: made where missing, never changed after - a choice HR makes in
	# Customize Form (say, hiding the column) is not undone by the next migrate.
	create_custom_fields({"CRM Task": [TASK_LABEL_FIELD]}, ignore_validate=True, update=False)
	return True


def on_app_install(app_name):
	"""after_app_install: the column arrives with CRM, not at the next migrate, so tasks
	made in between are labelled too (the backfill patch has already run by then)."""
	if app_name == "crm":
		ensure_task_label_field()


def backfill_task_labels(batch=500):
	"""Fill the column on tasks made before it existed. Writes only rows whose label differs."""
	last = ""
	while True:
		tasks = frappe.get_all("CRM Task", filters={"name": [">", last],
													 "reference_doctype": ["in", ["CRM Lead", "CRM Deal"]]},
							   fields=["name", "reference_doctype", "reference_docname", TASK_LABEL],
							   order_by="name asc", limit=batch)
		if not tasks:
			return
		rows = {}
		for dt in ("CRM Lead", "CRM Deal"):
			names = list({t.reference_docname for t in tasks if t.reference_doctype == dt and t.reference_docname})
			if names:
				for r in frappe.get_all(dt, filters={"name": ["in", names]}, fields=NAME_FIELDS):
					rows[(dt, r.name)] = r
		for t in tasks:
			label = task_label(t.reference_doctype, rows.get((t.reference_doctype, t.reference_docname)))
			if label != (t.get(TASK_LABEL) or ""):
				frappe.db.set_value("CRM Task", t.name, TASK_LABEL, label, update_modified=False)
		frappe.db.commit()
		last = tasks[-1].name
