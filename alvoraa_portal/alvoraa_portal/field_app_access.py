"""Who may see a punch and its photo, and a record of who looked at a face.

Moved out of `field_checkin.py` unchanged. `hooks.py` still names
`alvoraa_portal.field_checkin.checkin_query_conditions`,
`...checkin_has_permission` and `...log_photo_view`; those names are imported
back into `field_checkin`, so every hook path still resolves.

The spec found NO row filter on Employee Checkin anywhere in Frappe HR or in
this app. The `Employee` role holds plain read on it, so the only thing
standing between a curious colleague and everybody's faces and coordinates was
whether ERPNext happened to create a User Permission row for each user. That
is a setting, not a control: one missing row and the whole tenant is readable.

Two hooks, because they answer different questions. The query condition filters
LISTS and reports; has_permission guards opening ONE record by name. A list
filter alone leaves /app/employee-checkin/EMP-CKIN-00042 wide open.
"""

import frappe
from frappe.utils import now, today

_HR_ROLES = {"HR Manager", "HR User", "System Manager", "Administrator"}

ACCESS_LOG = "Alvoraa Photo Access Log"


def _viewer(user=None):
	"""(is_hr, employee_id) for the user asking."""
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	is_hr = bool(_HR_ROLES & roles)
	emp = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
	return is_hr, emp


def checkin_query_conditions(user=None):
	"""Row filter for the Employee Checkin list.

	HR sees everything. A manager sees their own and their direct reports'. An
	employee sees their own. Anybody with no employee record sees nothing, which
	is deliberately stricter than "sees everything" - the failure mode of a
	permission rule should be silence, not disclosure.
	"""
	is_hr, emp = _viewer(user)
	if is_hr:
		return ""
	if not emp:
		return "1=0"

	esc = frappe.db.escape
	allowed = [esc(emp)]
	# A line manager legitimately needs their own team's attendance. Direct
	# reports only - not the whole tree - because that is what a manager acts on
	# and it keeps the list from quietly widening as an org chart deepens.
	allowed += [esc(e) for e in frappe.get_all(
		"Employee", filters={"reports_to": emp, "status": "Active"}, pluck="name")]

	return "`tabEmployee Checkin`.employee in ({0})".format(", ".join(allowed))


def checkin_has_permission(doc, user=None, permission_type=None):
	"""Guards ONE record, opened by name or through the API."""
	is_hr, emp = _viewer(user)
	if is_hr:
		return True
	if not emp:
		return False
	if doc.employee == emp:
		return True
	return bool(frappe.db.exists("Employee", {
		"name": doc.employee, "reports_to": emp, "status": "Active"}))


def log_photo_view(doc, method=None):
	"""Record that somebody opened a check-in carrying a photo.

	A face is the most sensitive thing this feature stores, and "who has looked
	at my photo" is a question an employee is entitled to ask. Without this the
	only honest answer is "we do not know".

	Deliberately narrow, because an access log that records everything is one
	nobody reads:
	  * only check-ins that actually HAVE a photo
	  * never the employee looking at their own
	  * one row per viewer per record per day, not one per page refresh
	"""
	if not doc.get("alvoraa_checkin_photo"):
		return
	if not frappe.db.exists("DocType", ACCESS_LOG):
		return

	user = frappe.session.user
	if user in ("Guest", "Administrator"):
		return

	is_hr, emp = _viewer(user)
	if emp and doc.employee == emp:
		return

	try:
		if frappe.db.exists(ACCESS_LOG, {
			"checkin": doc.name, "viewed_by": user, "viewed_on_date": today()}):
			return
		frappe.get_doc({
			"doctype": ACCESS_LOG,
			"checkin": doc.name,
			"employee": doc.employee,
			"employee_name": doc.employee_name,
			"viewed_by": user,
			"viewed_at": now(),
			"viewed_on_date": today(),
		}).insert(ignore_permissions=True)
		frappe.db.commit()
	except Exception:
		# Never let the log stop somebody doing their job.
		frappe.log_error(f"Could not record photo access on {doc.name}",
		                 "Field check-in access log")
