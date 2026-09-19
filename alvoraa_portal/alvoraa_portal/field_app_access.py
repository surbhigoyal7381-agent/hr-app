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


# ── who may see a phone record (slice 013 step 2, C-11c) ─────────────────────
#
# `Alvoraa Field Device` links Employee and nothing else - no Company. Frappe's
# User Permissions only follow link fields that are ON the doctype, so an HR
# user restricted to one company could list every company's phones: employee
# name, device model, last punch, check-in count. The step-1 probe found it;
# it had been open since slice 008. These two hooks close it the way the punch
# is closed above: the query condition filters lists and reports, has_permission
# guards opening one record by name.
#
# The scope is the shared one every HR endpoint already uses,
# `hrms.alvoraa_hr_core.access.permitted_companies`: a System Manager sees every
# company; an HR Manager or HR User sees the companies in their Company User
# Permissions, or failing that their own employee record's company, or failing
# that nothing. Nobody else has a role on this doctype, and if one ever appears
# the fallback here is "nothing", not "everything".

DEVICE = "Alvoraa Field Device"
INVITE = "Alvoraa App Invite"
ACKNOWLEDGEMENT = "Alvoraa Notice Acknowledgement"


def _device_companies(user):
	"""The companies whose phones this user may see, or None for every company."""
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	if user == "Administrator" or "System Manager" in roles:
		return None
	if not (_HR_ROLES & roles):
		return []
	from hrms.alvoraa_hr_core.access import permitted_companies
	return permitted_companies(user)


def _scoped_by_employee_company(doctype, user):
	"""Row filter for a doctype that links Employee and nothing else."""
	companies = _device_companies(user)
	if companies is None:
		return ""
	if not companies:
		return "1=0"
	allowed = ", ".join(frappe.db.escape(c) for c in companies)
	return (f"`tab{doctype}`.employee in (select name from `tabEmployee` "
	        f"where company in ({allowed}))")


def _one_row_by_employee_company(doc, user):
	"""Guards ONE record of such a doctype, opened by name or through the API."""
	companies = _device_companies(user)
	if companies is None:
		return True
	if not companies or not doc.get("employee"):
		return False
	company = frappe.db.get_value("Employee", doc.employee, "company")
	return bool(company) and company in companies


def device_query_conditions(user=None):
	"""Row filter for the phone list and every report on it."""
	return _scoped_by_employee_company(DEVICE, user)


def device_has_permission(doc, user=None, permission_type=None):
	"""Guards ONE phone record, opened by name or through the API."""
	return _one_row_by_employee_company(doc, user)


# The code record and the acknowledgement record (slice 013 step 3) link only
# Employee too, so they get the same pair, for the same reason.

def invite_query_conditions(user=None):
	return _scoped_by_employee_company(INVITE, user)


def invite_has_permission(doc, user=None, permission_type=None):
	return _one_row_by_employee_company(doc, user)


def acknowledgement_query_conditions(user=None):
	return _scoped_by_employee_company(ACKNOWLEDGEMENT, user)


def acknowledgement_has_permission(doc, user=None, permission_type=None):
	return _one_row_by_employee_company(doc, user)


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
