"""Key Result Areas: what an employee's objectives are allowed to hang under.

The industry pattern, and the one Frappe HR already implements:

    KRA                      the library - "Revenue Growth", "Team Development"
    Appraisal Template       groups KRAs for a ROLE, each with a weightage
    Appraisal Template Goal  one KRA + its per_weightage
    Appraisal / Appraisee    assigns a template to a person for a cycle

KRAs belong to the JOB, not the person: two Sales Managers share them. They are
written once by HR with the function head, reviewed yearly, and carry weightages
summing to 100. Objectives change every cycle; KRAs rarely do.

So nothing new is invented here. An employee's KRAs are read from the template
they have been assigned, which is the only honest answer to "has HR defined KRAs
for this person yet".

Making the link mandatory is the control that stops goal-setting drifting away
from the role - somebody doing excellent work on something nobody asked for.
"""

import frappe
from frappe import _

from alvoraa_portal.subscription import requires_feature

# Whether an objective may be SUBMITTED without a KRA. Stored the same way as
# every other org-level switch on this site.
MANDATORY_KEY = "kra_link_mandatory"


def is_mandatory():
	return str(frappe.db.get_default(MANDATORY_KEY) or "0") in ("1", "true", "True")


def _employee_template(employee):
	"""The Appraisal Template assigned to this employee, or None.

	Looked up in the order the assignment actually happens: an Appraisal exists
	once a cycle is under way, and before that the Appraisal Cycle's `appraisees`
	table carries the intended template. Neither means HR has not set this person
	up yet - which is the case the portal has to explain rather than fail on.
	"""
	if not employee:
		return None

	if frappe.db.table_exists("Appraisal"):
		tpl = frappe.db.get_value(
			"Appraisal",
			{"employee": employee, "appraisal_template": ["is", "set"]},
			"appraisal_template", order_by="creation desc")
		if tpl:
			return tpl

	if frappe.db.table_exists("Appraisee"):
		tpl = frappe.db.get_value(
			"Appraisee",
			{"employee": employee, "appraisal_template": ["is", "set"]},
			"appraisal_template", order_by="creation desc")
		if tpl:
			return tpl

	return None


def kras_for_employee(employee):
	"""KRAs this employee may hang an objective under, with their weightages.

	Filtered to their own template on purpose. Offering every KRA on the site
	would let someone in Finance file objectives under a Sales area, which is
	precisely what the link exists to prevent.
	"""
	template = _employee_template(employee)
	if not template or not frappe.db.table_exists("Appraisal Template Goal"):
		return []

	rows = frappe.get_all(
		"Appraisal Template Goal",
		filters={"parent": template, "parenttype": "Appraisal Template"},
		fields=["key_result_area", "per_weightage"],
		order_by="idx asc")

	out = []
	for r in rows:
		if not r.key_result_area:
			continue
		out.append({
			"kra": r.key_result_area,
			"title": frappe.db.get_value("KRA", r.key_result_area, "title")
			or r.key_result_area,
			"description": frappe.db.get_value("KRA", r.key_result_area, "description") or "",
			"weightage": r.per_weightage or 0,
		})
	return out


@frappe.whitelist()
@requires_feature("goals")
def get_my_kras(employee=None):
	"""What the objective form should offer, and what to say when it can offer nothing.

	Returns `available: False` rather than an empty list plus a guess, so the
	portal can show the employee a clear explanation instead of an empty dropdown
	that looks broken.
	"""
	from alvoraa_portal.hr_api import _get_employee

	emp = employee or _get_employee()
	if not emp:
		frappe.throw(_("No employee record is linked to this account."))

	kras = kras_for_employee(emp)
	return {
		"employee": emp,
		"kras": kras,
		"available": bool(kras),
		"mandatory": is_mandatory(),
		"template": _employee_template(emp),
		# The total is worth showing: weightages are meant to sum to 100, and a
		# template that does not is a setup mistake HR would want to see.
		"total_weightage": sum(k["weightage"] for k in kras),
	}


@frappe.whitelist()
@requires_feature("goals")
def report_missing_kra(message=None):
	"""Tell HR that this employee cannot set objectives yet.

	A dead end with no way out is the worst version of a mandatory field, so the
	dialog that blocks the employee also gives them this. It reaches HR through
	Frappe's own Notification Log, which is what puts it in their bell - not a
	parallel inbox nobody checks.
	"""
	from alvoraa_portal.hr_api import _get_employee

	emp = _get_employee()
	emp_name = frappe.db.get_value("Employee", emp, "employee_name") if emp else None
	who = emp_name or frappe.session.user

	recipients = _hr_users()
	if not recipients:
		# Better to say so than to accept the click and drop it silently.
		frappe.throw(_("No HR user is set up on this site to receive the request."))

	subject = _("{0} cannot set objectives - no KRAs assigned").format(who)
	body = _(
		"{0} tried to create an objective, but has no Key Result Areas available.\n\n"
		"They have no appraisal template assigned, or the template has no KRAs in it.\n\n"
		"Assign an appraisal template with KRAs so they can continue."
	).format(who)
	if message:
		body += "\n\n" + _("They added:") + "\n" + str(message)[:1000]

	sent = []
	for user in recipients:
		doc = frappe.get_doc({
			"doctype": "Notification Log",
			"for_user": user,
			"type": "Alert",
			"subject": subject,
			"email_content": body,
			"document_type": "Employee",
			"document_name": emp,
		})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		sent.append(user)

	frappe.db.commit()
	return {"ok": True, "notified": len(sent)}


def _hr_users():
	"""Enabled users holding an HR role. Deduplicated, Administrator excluded."""
	rows = frappe.get_all(
		"Has Role",
		filters={"role": ["in", ["HR Manager", "HR User"]], "parenttype": "User"},
		fields=["parent"])
	users = {r.parent for r in rows if r.parent and r.parent != "Administrator"}
	if not users:
		return []
	enabled = frappe.get_all("User", filters={"name": ["in", list(users)], "enabled": 1},
	                         pluck="name")
	return sorted(enabled)


def validate_goal_kra(doc, method=None):
	"""Refuse to ACTIVATE an objective with no KRA, when HR has made it mandatory.

	Draft is deliberately still allowed. Blocking outright would stop everyone
	writing objectives the moment HR forgets a template, and the point of the
	setting is to keep goals tied to the role - not to hold people hostage to a
	configuration gap. They can write it now and attach the KRA when it exists.
	"""
	if not is_mandatory():
		return
	if getattr(doc, "kra", None):
		return
	if (getattr(doc, "status", "") or "").lower() == "draft":
		return

	frappe.throw(
		_("This objective needs a Key Result Area before it can be activated. "
		  "Your organisation requires every objective to sit under one. "
		  "Save it as a draft, or ask HR to assign your appraisal template."),
		title=_("Key Result Area required"),
	)
