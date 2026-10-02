"""Slice 057 (A): a CRM lead or deal reaching a status creates that step's tasks.

The steps are rows of "Alvoraa CRM Step Task", keyed by (Lead or Deal, lead type,
status), filled in by a sales manager in the desk. On every save of a CRM Lead or
CRM Deal this returns at once, with no query, unless the status changed and the
record has a lead type. Then one query finds the matching steps, and each one
becomes a standard CRM Task - CRM itself assigns it and notifies the person.

A broken step never stops a salesperson changing a status: its error goes to the
Error Log with the record name only, and the status change goes through.
"""
import frappe
from frappe.core.doctype.communication.email import make as make_email
from frappe.utils import add_days, today

RULE = "Alvoraa CRM Step Task"
# Made by Customize Form from the label "Lead Type"; the same name on lead and deal,
# so CRM copies it across when a lead is converted.
LEAD_TYPE_FIELD = "custom_lead_type"
DUE_TIME = "18:00:00"   # end of the working day, so a task due today is not overdue at 9 am


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
	return True


def _send_email(doc, step):
	mail = frappe.get_doc("Email Template", step.email_template).get_formatted_email(doc.as_dict())
	# make() checks that the person changing the status may email this record.
	make_email(doctype=doc.doctype, name=doc.name, subject=mail["subject"], content=mail["message"],
			   recipients=doc.email, send_email=True, email_template=step.email_template)
