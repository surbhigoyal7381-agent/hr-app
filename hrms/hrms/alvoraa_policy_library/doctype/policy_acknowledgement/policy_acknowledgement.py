import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, now_datetime


class PolicyAcknowledgement(Document):
	def validate(self):
		if not self.acknowledged_on:
			self.acknowledged_on = now_datetime()
		if not self.user:
			self.user = frappe.db.get_value("Employee", self.employee, "user_id") or frappe.session.user
		dup = frappe.db.exists(
			"Policy Acknowledgement",
			{
				"policy_document": self.policy_document,
				"version": cint(self.version),
				"employee": self.employee,
				"name": ["!=", self.name],
			},
		)
		if dup:
			frappe.throw(
				_("{0} has already acknowledged version {1} of {2}.").format(self.employee, self.version, self.policy_document)
			)

	def after_insert(self):
		complete_onboarding_task(self.employee)


def complete_onboarding_task(employee):
	"""Onboarding link: the "policy acknowledgement" activity closes by itself
	once every joining policy is acknowledged."""
	try:
		pending = frappe.get_all(
			"Policy Document", filters={"status": "Published", "acknowledge_on_joining": 1}, fields=["name", "current_version"]
		)
		for pol in pending:
			if not frappe.db.exists(
				"Policy Acknowledgement",
				{"policy_document": pol.name, "version": cint(pol.current_version), "employee": employee},
			):
				return
		for onb in frappe.get_all(
			"Employee Onboarding", filters={"employee": employee, "docstatus": 1, "boarding_status": ["!=", "Completed"]}, pluck="name"
		):
			for act in frappe.get_all(
				"Employee Boarding Activity",
				filters={"parent": onb, "parenttype": "Employee Onboarding", "activity_name": ["like", "%olic%"]},
				fields=["task"],
			):
				if act.task and frappe.db.get_value("Task", act.task, "status") != "Completed":
					task = frappe.get_doc("Task", act.task)
					task.status = "Completed"
					task.flags.ignore_permissions = True
					task.save()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Policy acknowledgement: onboarding task update failed")
