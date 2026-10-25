"""Who may change which Employee field (ALV-215, slice 063 SEC-17).

WHY THIS FILE EXISTS. Frappe HR gives "Employee Self Service" write on the
employee's own Employee record. So an employee could change their own
designation, manager, leave approver, company or pay-rule fields over the REST
API - and, once DTC's rule set is on, raise their own leave credit. Frappe's
field permission levels stop that; this file applies them on every site.

THREE LEVELS
  0  the employee's own details (phone, address, emergency contact) - as today.
  2  job, pay settings, approvers, identity, and every Employee field a pay rule
     set names. HR User, HR Manager and System Manager write; every role that
     reads Employee also reads these, so no screen loses a field.
  1  bank, statutory IDs and salary (the 13 PPJ already locked). HR Manager only
     (Surbhi, D2 and D3, 25 Oct 2026): no other role keeps a level-1 row.

WHY A MIGRATE FUNCTION, NOT A FIXTURE OR A PATCH. A patch never runs on a new
install (Frappe marks every patch done), so new tenants would ship open. A
Custom DocPerm fixture replaces a tenant's own rows by name. This runs on every
migrate and every install, writes only what is missing, and puts the rules back
if someone resets Employee permissions by hand.

AND ONE RULE NO SETTING CAN SAY: nobody changes these fields on their own
record, HR included (R4). `refuse_own_locked_change` below. It reads the level
from each field, so it needs no second list.
"""

import frappe
from frappe import _
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.permissions import add_permission, update_permission_property

from hrms.alvoraa_hr_core.access import is_own_record, refuse

EMPLOYEE = "Employee"
RULE_SET = "Alvoraa Payroll Rule Set"

# Job, pay settings, approvers and identity. 01g section 3.1 and 04c section 1.
LEVEL_2 = (
	"designation", "employment_type", "reports_to", "leave_approver", "company",
	"department", "branch", "grade", "expense_approver", "shift_request_approver",
	"holiday_list", "default_shift", "attendance_device_id", "date_of_joining",
	"relieving_date", "status", "user_id", "first_name", "middle_name", "last_name",
	"gender", "date_of_birth",
)

# Bank, statutory IDs and salary - the 13 PPJ already holds at level 1.
LEVEL_1 = (
	"bank_ac_no", "bank_name", "iban", "ifsc_code", "micr_code", "ctc", "salary_mode",
	"salary_currency", "pan_number", "esi_number", "provident_fund_account",
	"payroll_cost_center", "employee_advance_account",
)

LEVEL_2_WRITERS = ("HR User", "HR Manager", "System Manager")
LEVEL_1_ROLE = "HR Manager"


def apply():
	"""Lock the fields and add the rows. Safe to run twice: writes only what is missing.

	Run as Administrator (migrate, install): add_permission saves its row with
	the caller's own permissions.
	"""
	if not frappe.db.exists("DocType", EMPLOYEE):
		return

	changed = lock_fields()
	rows =frappe.get_all("Custom DocPerm", filters={"parent": EMPLOYEE, "if_owner": 0},
	                      fields=["name", "role", "permlevel", "read", "write"])
	if not rows:
		# Standard rows only. add_permission copies them in first, so nobody loses access.
		rows = frappe.get_all("DocPerm", filters={"parent": EMPLOYEE, "if_owner": 0},
		                      fields=["name", "role", "permlevel", "read", "write"])
	at = {(r.role, r.permlevel): r for r in rows}

	for r in [r for r in rows if r.permlevel == 0 and (r.read or r.write)]:
		writes = r.write and r.role in LEVEL_2_WRITERS
		have = at.get((r.role, 2))
		if not have:
			add_permission(EMPLOYEE, r.role, 2)  # read
			changed = True
		if writes and not (have and have.write):
			update_permission_property(EMPLOYEE, r.role, 2, "write", 1)
			changed = True

	if (LEVEL_1_ROLE, 0) in at:
		have = at.get((LEVEL_1_ROLE, 1))
		if not have:
			add_permission(EMPLOYEE, LEVEL_1_ROLE, 1)
			changed = True
		if not (have and have.write):
			update_permission_property(EMPLOYEE, LEVEL_1_ROLE, 1, "write", 1)
			changed = True

	# D2: PPJ's Payroll Users (and anyone else) lose level 1. Custom rows only -
	# a standard DocPerm row cannot be deleted, and Employee ships none at level 1.
	for r in rows:
		if r.permlevel == 1 and r.role != LEVEL_1_ROLE and frappe.db.exists("Custom DocPerm", r.name):
			frappe.delete_doc("Custom DocPerm", r.name, ignore_permissions=True, force=True)
			changed = True

	if changed:
		frappe.clear_cache(doctype=EMPLOYEE)


def lock_fields():
	"""Property Setters only, so an HR Manager saving a rule set can run it too."""
	meta = frappe.get_meta(EMPLOYEE)
	wanted = dict.fromkeys(LEVEL_2 + rule_set_fields(), 2)
	wanted.update(dict.fromkeys(LEVEL_1, 1))
	changed = False
	for fieldname, level in wanted.items():
		df = meta.get_field(fieldname)
		# Never lower a field that is already above 0 (PPJ's 13 stay at 1).
		if df and not df.permlevel:
			make_property_setter(EMPLOYEE, fieldname, "permlevel", level, "Int",
			                     validate_fields_for_doctype=False)
			changed = True
	if changed:
		frappe.clear_cache(doctype=EMPLOYEE)
	return changed


def rule_set_fields():
	"""Every Employee field any pay rule set names in one of its `*_field` settings."""
	if not frappe.db.table_exists(RULE_SET):
		return ()
	settings = [df.fieldname for df in frappe.get_meta(RULE_SET).fields if df.fieldname.endswith("_field")]
	names = set()
	for row in frappe.get_all(RULE_SET, fields=settings):
		names.update(v.strip() for v in row.values() if v and v.strip())
	return tuple(sorted(names))


def after_migrate():
	apply()


def refuse_own_locked_change(doc, method=None):
	"""Employee validate (R4): nobody changes a locked field on their own record.

	Frappe has already put back any locked field the caller may not write, so a
	change still showing here comes from someone who holds that level - HR.
	"""
	if doc.is_new() or not doc.get_doc_before_save():
		return
	if not any(doc.has_value_changed(df.fieldname) for df in doc.meta.get_high_permlevel_fields()):
		return
	if is_own_record(doc.name):
		refuse(
			_("You cannot change your own job, pay or bank details. Ask another HR person to make this change."),
			"SEC-17",
			"Employee save",
			doc.doctype,
			doc.name,
		)


def refuse_import_of_locked_columns(doc, method=None):
	"""Data Import validate: say so, instead of Frappe silently dropping the column.

	A sheet with a bank, PAN, ESI or PF column imported by an HR User would
	"succeed" with those values quietly thrown away.
	"""
	if doc.reference_doctype != EMPLOYEE or not (doc.import_file or doc.google_sheets_url):
		return
	can_write = set(frappe.get_meta(EMPLOYEE).get_permlevel_access("write"))
	locked = [
		col.df.label
		for col in doc.get_importer().import_file.columns
		if col.df and col.df.parent == EMPLOYEE and (col.df.permlevel or 0) not in can_write
	]
	if locked:
		frappe.throw(
			_("This file has columns you are not allowed to change: {0}. Remove them from the file, "
			  "or ask an HR Manager to run this import.").format(", ".join(locked)),
			frappe.PermissionError,
		)


@frappe.whitelist()
def get_employee_field_property(employee: str, fieldname: str):
	"""Replaces hrms.hr.utils.get_employee_field_property (step B, override_whitelisted_methods).

	The Promotion and Transfer field picker calls it. Upstream checks the caller
	may read the Employee, then returns ANY field, ignoring field levels - so an
	HR User could read a bank account number this file hides on the form.
	Check the level, then hand over to upstream unchanged.
	"""
	from hrms.hr.utils import get_employee_field_property as upstream

	field = frappe.get_meta(EMPLOYEE).get_field(fieldname) if fieldname else None
	if employee and field and field.permlevel:
		doc = frappe.get_doc(EMPLOYEE, employee, check_permission=True)
		if not doc.has_permlevel_access_to(fieldname, df=field, permission_type="read"):
			refuse(_("You do not have access to this field."), "SEC-17",
			       "get_employee_field_property", EMPLOYEE, employee)
	return upstream(employee, fieldname)
