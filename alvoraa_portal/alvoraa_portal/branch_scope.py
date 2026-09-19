"""Store HR see their own store: a branch on the HR records that lack one.

A location HR person holds HR User plus a User Permission on their Branch. Frappe
applies that permission only to record types with a Link to Branch. Employee and
Salary Slip have one; attendance, check-ins, leave, claims and the rest do not, so
a store's HR person saw every store's records there.

The fix is the one Frappe HR already uses on Salary Slip: a read-only branch
copied from the employee when the record is saved. No permission code - the
User Permissions organisations already set start to apply by themselves.

A record keeps the branch it was saved with. When somebody moves store, their
old records stay with the old store and central HR still sees everything. That
is deliberate (decided 2026-09-14): history should say where the work happened.
"""

import frappe

FIELD = "alvoraa_branch"

# record type -> (link the branch is copied through, field on that link, field to sit after)
SOURCES = {
	"Attendance": ("employee", "branch", "department"),
	"Employee Checkin": ("employee", "branch", "employee_name"),
	"Leave Application": ("employee", "branch", "department"),
	"Leave Allocation": ("employee", "branch", "department"),
	"Expense Claim": ("employee", "branch", "department"),
	"Employee Advance": ("employee", "branch", "department"),
	"Salary Structure Assignment": ("employee", "branch", "department"),
	"Attendance Request": ("employee", "branch", "department"),
	"Shift Assignment": ("employee", "branch", "department"),
	"Appraisal": ("employee", "branch", "department"),
	# No employee yet - the store is the one the job opening is for.
	"Job Applicant": ("job_title", "location", "job_title"),
}

LINKED = {"employee": "Employee", "job_title": "Job Opening"}


def after_migrate():
	"""Add the branch field, on migrate AND on install.

	Both, for the reason in `attendance_correction.after_migrate`: a site built
	with `bench install-app` never runs a migrate. Safe to run again.
	"""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields({
		dt: [{
			"fieldname": FIELD,
			"label": "Branch",
			"fieldtype": "Link",
			"options": "Branch",
			"fetch_from": f"{link}.{source}",
			"insert_after": after,
			"read_only": 1,
			"search_index": 1,
			"in_standard_filter": 1,
			"description": "Copied when the record is saved. Limits what location HR can see.",
		}]
		for dt, (link, source, after) in SOURCES.items()
		if frappe.db.exists("DocType", dt)
	})


def fill_existing():
	"""Give records saved before the field existed their branch.

	One update per record type, straight in the database: most of these records
	are submitted and cannot be saved again. Only empty values are filled, so a
	second run never moves a record that already has its branch.
	"""
	for dt, (link, source, _after) in SOURCES.items():
		if not frappe.db.has_column(dt, FIELD):
			continue
		record = frappe.qb.DocType(dt)
		linked = frappe.qb.DocType(LINKED[link])
		(
			frappe.qb.update(record)
			.join(linked).on(record[link] == linked.name)
			.set(record[FIELD], linked[source])
			.where((record[FIELD].isnull()) | (record[FIELD] == ""))
			.where(linked[source].isnotnull() & (linked[source] != ""))
		).run()
