"""ALV-469: the name the portal shows at the top of the sidebar.

It used to be the site's `tenant_name` for everybody. A person in a different
company of the group, or placed by an agency, or a freelancer, saw the wrong
organisation. Surbhi's rules, 26 Nov 2026, first match wins:

    no Employee row for the user         the site's tenant_name
    employment type Gig Worker/Freelancer the person's own name
    Contract, with an agency set          the agency
    Contract, no agency                   the person's own name
    anything else                         the Employee's company

Any error gives the tenant_name, so a bad record can never break the page.

The agency and the category are two Employee fields. They replace DTC's own
`dtc_agency` and `dtc_employee_category`, which only exist on DTC. Their
choices are per site (DTC's agencies are not Grace's), so the fields are
created ONCE, with the old field's choices copied in, and are never touched
again: a fixture or `create_custom_fields` would put the choices back on every
migrate and undo what HR edited in Customize Form.
"""

import frappe

from alvoraa_portal.tenant_context import get_branding

EMPLOYEE = "Employee"
# The label reads the agency through this one name.
AGENCY_FIELD = "employment_agency"
CATEGORY_FIELD = "employee_category"
OWN_NAME_TYPES = ("Gig Worker", "Freelancer")
CONTRACT = "Contract"

# new field -> the DTC-only field it replaces
OLD_FIELD = {AGENCY_FIELD: "dtc_agency", CATEGORY_FIELD: "dtc_employee_category"}


def org_label(user=None):
	"""The organisation name to show for this user. Never raises."""
	fallback = get_branding()["tenant_name"]
	try:
		user = user or frappe.session.user
		fields = ["employment_type", "employee_name", "company"]
		if frappe.get_meta(EMPLOYEE).has_field(AGENCY_FIELD):
			fields.append(AGENCY_FIELD)
		# "Active" sorts before "Inactive", "Left" and "Suspended".
		rows = frappe.get_all(EMPLOYEE, filters={"user_id": user}, fields=fields,
		                      order_by="status asc", limit=1)
		if not rows:
			return fallback
		emp = rows[0]
		kind = emp.employment_type
		if kind in OWN_NAME_TYPES:
			return emp.employee_name or fallback
		if kind == CONTRACT:
			return emp.get(AGENCY_FIELD) or emp.employee_name or fallback
		return emp.company or fallback
	except Exception:
		frappe.log_error(title="org_label: showing the tenant name instead",
		                 message=frappe.get_traceback())
		return fallback


def _choices_from_old(new_field):
	"""Seed text for the new Select: the old field's choices, or, when the old
	field is not a Select, the values people already hold in it."""
	old = OLD_FIELD[new_field]
	df = frappe.get_meta(EMPLOYEE).get_field(old)
	if not df:
		return ""
	if df.fieldtype == "Select":
		return df.options or ""
	values = frappe.get_all(EMPLOYEE, filters={old: ["is", "set"]}, pluck=old, distinct=True)
	return "\n".join([""] + sorted(values))


def _make_field(fieldname, label, insert_after, depends_on=None):
	"""Create the Custom Field only if it is not there. Never updates one."""
	if frappe.db.exists("Custom Field", {"dt": EMPLOYEE, "fieldname": fieldname}):
		return False
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	create_custom_field(EMPLOYEE, {
		"fieldname": fieldname, "label": label, "fieldtype": "Select",
		"insert_after": insert_after, "options": _choices_from_old(fieldname),
		"depends_on": depends_on or "",
	})
	return True


def after_migrate():
	"""Wired into after_migrate AND after_install (a patch never runs on a new
	site). Makes the two fields if missing and the two Employment Types if
	missing. Safe to run twice."""
	if not frappe.db.exists("DocType", EMPLOYEE):
		return False

	made = _make_field(AGENCY_FIELD, "Employment Agency", "employment_type",
	                   'eval:doc.employment_type=="Contract"')
	made = _make_field(CATEGORY_FIELD, "Employee Category", AGENCY_FIELD) or made
	if made:
		frappe.clear_cache(doctype=EMPLOYEE)

	if frappe.db.exists("DocType", "Employment Type"):
		for name in OWN_NAME_TYPES:
			if not frappe.db.exists("Employment Type", name):
				frappe.get_doc({"doctype": "Employment Type", "employee_type_name": name}
				               ).insert(ignore_permissions=True)
	return True
