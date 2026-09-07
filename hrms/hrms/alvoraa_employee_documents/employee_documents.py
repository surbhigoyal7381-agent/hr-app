"""The employee document checklist.

Every Employee carries a table of the documents HR expects from them, one row
per Employee Document Type that applies to their grade. A row moves from
Pending to Received when a file is attached, to Verified when someone with a
verifier role signs it off, and to Expired when its expiry date passes. The
counts are kept on the Employee and mirrored onto the Employee Onboarding.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, today

from hrms.alvoraa_hr_core.features import feature_enabled

FEATURE = "employee_documents"
STATUSES = ("Pending", "Received", "Verified", "Rejected", "Expired")
OPEN_STATUSES = ("Pending", "Rejected", "Expired")


def applicable_types(grade=None, designation=None):
	"""Document types that apply to an employee of this grade or designation.
	A type with no grades and no designations applies to everyone."""
	types = frappe.get_all(
		"Employee Document Type",
		fields=["name", "mandatory_for_joining", "has_expiry"],
		order_by="category, name",
	)
	grades, designations = {}, {}
	for row in frappe.get_all("Employee Document Type Grade", fields=["parent", "employee_grade"]):
		grades.setdefault(row.parent, set()).add(row.employee_grade)
	for row in frappe.get_all("Employee Document Type Designation", fields=["parent", "designation"]):
		designations.setdefault(row.parent, set()).add(row.designation)
	out = []
	for t in types:
		if t.name not in grades and t.name not in designations:
			out.append(t)
		elif (grade and grade in grades.get(t.name, ())) or (designation and designation in designations.get(t.name, ())):
			out.append(t)
	return out


# ── Employee hooks ──────────────────────────────────────────────────────────
def fill_checklist(doc, method=None):
	"""Employee after_insert: one Pending row per applicable document type."""
	if not feature_enabled(FEATURE) or doc.get("employee_documents"):
		return
	for t in applicable_types(doc.get("grade"), doc.get("designation")):
		row = doc.append("employee_documents", {"document_type": t.name, "status": "Pending"})
		row.db_insert()
	if doc.get("employee_documents"):
		doc.documents_summary = summary_text(doc.employee_documents)
		doc.db_set("documents_summary", doc.documents_summary, update_modified=False)


@frappe.whitelist()
def backfill_checklists(employees=None):
	"""Give every active employee the rows they are missing. For a tenant that
	switches the feature on with staff already on the books, and for a new
	document type added later. Returns how many employees gained rows."""
	if frappe.session.user != "Administrator" and not (
		{"HR Manager", "System Manager"} & set(frappe.get_roles())
	):
		frappe.throw(_("Only HR Managers can fill document checklists."), frappe.PermissionError)
	if isinstance(employees, str):
		employees = frappe.parse_json(employees)
	filters = {"status": "Active"}
	if employees:
		filters["name"] = ["in", list(employees)]
	have = {}
	for r in frappe.get_all("Employee Document", filters={"parenttype": "Employee"}, fields=["parent", "document_type"]):
		have.setdefault(r.parent, set()).add(r.document_type)
	touched = 0
	for emp in frappe.get_all("Employee", filters=filters, fields=["name", "grade", "designation"]):
		missing = [t for t in applicable_types(emp.grade, emp.designation) if t.name not in have.get(emp.name, ())]
		if not missing:
			continue
		doc = frappe.get_doc("Employee", emp.name)
		for t in missing:
			doc.append("employee_documents", {"document_type": t.name, "status": "Pending"}).db_insert()
		refresh_summary(emp.name)
		touched += 1
	return touched


def validate_documents(doc, method=None):
	"""Employee validate: keep the row statuses honest and the summary current."""
	rows = doc.get("employee_documents") or []
	if not rows:
		if doc.get("documents_summary"):
			doc.documents_summary = ""
		return
	before = {}
	if not doc.is_new():
		old = doc.get_doc_before_save()
		if old:
			before = {r.name: r for r in (old.get("employee_documents") or [])}
	user = frappe.session.user
	for row in rows:
		old_row = before.get(row.name)
		if row.attachment and row.status == "Pending":
			row.status = "Received"
		if row.status == "Received" and not row.received_on:
			row.received_on = today()
			row.received_by = user
		if row.status == "Verified":
			if not old_row or old_row.status != "Verified":
				check_can_verify(row.document_type)
				row.verified_on = today()
				row.verified_by = user
		else:
			row.verified_on = None
			row.verified_by = None
		if row.expiry_date and getdate(row.expiry_date) < getdate(today()) and row.status in ("Received", "Verified"):
			row.status = "Expired"
	doc.documents_summary = summary_text(rows)


def sync_onboarding_summary(doc, method=None):
	"""Employee on_update: mirror the counts onto the onboarding record."""
	if not doc.get("employee_documents") and not doc.get("documents_summary"):
		return
	for name in frappe.get_all(
		"Employee Onboarding", filters={"employee": doc.name, "docstatus": ["!=", 2]}, pluck="name"
	):
		frappe.db.set_value(
			"Employee Onboarding", name, "documents_summary", doc.get("documents_summary") or "", update_modified=False
		)


def check_can_verify(document_type):
	roles = frappe.get_all("Employee Document Verifier Role", filters={"parent": document_type}, pluck="role")
	if not roles or frappe.session.user == "Administrator":
		return
	if not set(roles) & set(frappe.get_roles()):
		frappe.throw(
			_("Only {0} can mark {1} as Verified.").format(", ".join(roles), document_type),
			frappe.PermissionError,
		)


def summary_text(rows):
	counts = {}
	for r in rows:
		counts[r.status] = counts.get(r.status, 0) + 1
	parts = [f"{counts[s]} {s.lower()}" for s in STATUSES if counts.get(s)]
	return " · ".join(parts)


def refresh_summary(employee):
	rows = frappe.get_all("Employee Document", filters={"parent": employee, "parenttype": "Employee"}, fields=["status"])
	text = summary_text(rows)
	frappe.db.set_value("Employee", employee, "documents_summary", text, update_modified=False)
	for name in frappe.get_all("Employee Onboarding", filters={"employee": employee, "docstatus": ["!=", 2]}, pluck="name"):
		frappe.db.set_value("Employee Onboarding", name, "documents_summary", text, update_modified=False)
	return text


# ── Portal helpers ──────────────────────────────────────────────────────────
def attach_document(row_name, file_url, employee, user=None):
	"""Set the file on one of the employee's own rows and mark it Received.
	Only rows collected from the employee can be filled this way."""
	row = frappe.get_doc("Employee Document", row_name)
	if row.parenttype != "Employee" or row.parent != employee:
		frappe.throw(_("That document row does not belong to you."), frappe.PermissionError)
	collect_from = frappe.db.get_value("Employee Document Type", row.document_type, "collect_from")
	if collect_from != "Employee":
		frappe.throw(_("{0} is collected by {1}, not uploaded by the employee.").format(row.document_type, collect_from))
	row.attachment = file_url
	row.received_on = today()
	row.received_by = user or frappe.session.user
	if row.status in OPEN_STATUSES:
		row.status = "Received"
	row.verified_on = None
	row.verified_by = None
	row.db_update()
	refresh_summary(employee)
	return row


def employees_missing_mandatory(branch=None):
	"""Active employees who need attention: a mandatory document not yet
	Verified, or any document that has Expired. Returns one entry per employee
	with the rows behind it."""
	mandatory = frappe.get_all("Employee Document Type", filters={"mandatory_for_joining": 1}, pluck="name")
	rows = frappe.get_all(
		"Employee Document",
		filters={"parenttype": "Employee", "status": ["!=", "Verified"]},
		fields=["parent", "document_type", "status", "expiry_date"],
	)
	rows = [r for r in rows if r.document_type in mandatory or r.status == "Expired"]
	if not rows:
		return []
	filters = {"name": ["in", list({r.parent for r in rows})], "status": "Active"}
	if branch:
		filters["branch"] = branch
	employees = {
		e.name: e
		for e in frappe.get_all(
			"Employee", filters=filters, fields=["name", "employee_name", "branch", "designation", "date_of_joining"]
		)
	}
	out = {}
	for r in rows:
		emp = employees.get(r.parent)
		if not emp:
			continue
		entry = out.setdefault(
			r.parent,
			{
				"employee": emp.name,
				"employee_name": emp.employee_name,
				"branch": emp.branch or "",
				"designation": emp.designation or "",
				"date_of_joining": str(emp.date_of_joining) if emp.date_of_joining else "",
				"missing": [],
			},
		)
		entry["missing"].append({"document_type": r.document_type, "status": r.status})
	return sorted(out.values(), key=lambda e: (e["branch"], e["employee_name"]))


# ── Daily job ───────────────────────────────────────────────────────────────
def expire_documents():
	"""Move rows past their expiry date to Expired and send the reminders that
	fall due today (reminder_days_before_expiry on the document type)."""
	if not feature_enabled(FEATURE):
		return
	today_ = getdate(today())
	expired = frappe.get_all(
		"Employee Document",
		filters={"parenttype": "Employee", "expiry_date": ["<", today_], "status": ["in", ["Received", "Verified"]]},
		fields=["name", "parent", "document_type"],
	)
	for r in expired:
		frappe.db.set_value("Employee Document", r.name, "status", "Expired", update_modified=False)
	for parent in {r.parent for r in expired}:
		refresh_summary(parent)
	if expired:
		_notify(expired, _("Employee document expired"), _("These documents have passed their expiry date and need renewing:"))

	due = []
	for t in frappe.get_all("Employee Document Type", filters={"has_expiry": 1}, fields=["name", "reminder_days_before_expiry"]):
		days = cint(t.reminder_days_before_expiry) or 30
		due += frappe.get_all(
			"Employee Document",
			filters={
				"parenttype": "Employee",
				"document_type": t.name,
				"expiry_date": add_days(today_, days),
				"status": ["in", ["Received", "Verified"]],
			},
			fields=["name", "parent", "document_type", "expiry_date"],
		)
	if due:
		_notify(due, _("Employee document expiring soon"), _("These documents expire soon and need renewing:"))
	frappe.db.commit()
	return {"expired": len(expired), "reminded": len(due)}


def _notify(rows, subject, lead):
	by_employee = {}
	for r in rows:
		by_employee.setdefault(r.parent, []).append(r)
	hr_users = frappe.get_all("Has Role", filters={"role": "HR Manager", "parenttype": "User"}, pluck="parent")
	hr_users = [u for u in set(hr_users) if u not in ("Administrator", "Guest") and frappe.db.get_value("User", u, "enabled")]
	for employee, emp_rows in by_employee.items():
		emp = frappe.db.get_value("Employee", employee, ["employee_name", "user_id"], as_dict=True) or frappe._dict()
		lines = "".join(
			f"<li>{frappe.utils.escape_html(r.document_type)}"
			+ (f" (expires {frappe.format(r.expiry_date, 'Date')})" if r.get("expiry_date") else "")
			+ "</li>"
			for r in emp_rows
		)
		recipients = [u for u in [emp.user_id, *hr_users] if u]
		if not recipients:
			continue
		try:
			frappe.sendmail(
				recipients=list(dict.fromkeys(recipients)),
				subject=f"{subject}: {emp.employee_name or employee}",
				message=f"<p>{lead}</p><ul>{lines}</ul>",
				reference_doctype="Employee",
				reference_name=employee,
			)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Employee document reminder failed")
