"""Fixtures for the leave tests.

Frappe HR's leave rules only mean anything against real Leave Types, a real
Holiday List and real Leave Allocations. Building those correctly in one place
keeps the tests about behaviour instead of about setup - the same lesson the
goals suite learned with `ensure_employee`.
"""

# alvoraa_goals owns the Employee fixture. Both apps are always installed
# together (sites/apps.txt), and duplicating a full Employee builder is how the
# original one drifted out of date.
from alvoraa_goals.tests.utils import ensure_company, ensure_employee

import frappe
from frappe.utils import add_days, today

# Fixed, verified dates. Tests assert exact day counts, so these must not drift.
HOLIDAY = "2026-09-16"   # Wednesday
WEEK_MON = "2026-09-14"  # Monday
WEEK_TUE = "2026-09-15"  # Tuesday
WEEK_FRI = "2026-09-18"  # Friday


def ensure_holiday_list(name="Alvoraa Test Holidays"):
	"""A holiday list with one known holiday, so holiday handling is testable.

	The holiday is deliberately a fixed, far-future date: a weekday chosen at
	random could collide with a weekend and make a test pass for the wrong reason.
	"""
	if frappe.db.exists("Holiday List", name):
		# Do not trust "it exists" - a list left by an older run can hold different
		# dates, and the tests assert exact day counts. Repair it instead.
		doc = frappe.get_doc("Holiday List", name)
		changed = False
		if str(doc.to_date) < "2027-12-31":
			doc.to_date = "2027-12-31"
			changed = True
		if not any(str(h.holiday_date) == HOLIDAY for h in doc.holidays):
			doc.append("holidays", {"holiday_date": HOLIDAY, "description": "Alvoraa Test Holiday"})
			changed = True
		if changed:
			doc.flags.ignore_permissions = True
			doc.save(ignore_permissions=True)
			frappe.db.commit()
		return name

	doc = frappe.get_doc(
		{
			"doctype": "Holiday List",
			"holiday_list_name": name,
			"from_date": "2026-01-01",
			"to_date": "2027-12-31",
			"holidays": [
				# Verified a Wednesday, so it cannot be mistaken for a weekly off,
				# and in the future so leave applications using it are not
				# back-dated. The list holds NO weekly offs, which keeps day counts
				# predictable: only this one date is skipped.
				{"holiday_date": HOLIDAY, "description": "Alvoraa Test Holiday"},
			],
		}
	)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return doc.name


def ensure_leave_type(name, allow_negative=0, is_lwp=0, include_holiday=0):
	"""Create (or reuse) a Leave Type with the flags a given test needs."""
	if frappe.db.exists("Leave Type", name):
		return name

	doc = frappe.get_doc(
		{
			"doctype": "Leave Type",
			"leave_type_name": name,
			"allow_negative": allow_negative,
			"is_lwp": is_lwp,
			"include_holiday": include_holiday,
			"max_continuous_days_allowed": 0,
		}
	)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return doc.name


def assign_holiday_list(employee, holiday_list=None):
	"""Assign the test holiday list to an employee, the way this hrms version reads it.

	The assignment must be SUBMITTED (docstatus 1) and start on or before the dates
	under test - get_assigned_holiday_list filters on both.
	"""
	holiday_list = holiday_list or ensure_holiday_list()
	existing = frappe.get_all(
		"Holiday List Assignment",
		filters={"assigned_to": employee, "holiday_list": holiday_list, "docstatus": 1},
		limit=1,
	)
	if existing:
		return existing[0].name

	doc = frappe.get_doc(
		{
			"doctype": "Holiday List Assignment",
			"applicable_for": "Employee",
			"assigned_to": employee,
			"holiday_list": holiday_list,
			"from_date": "2026-01-01",
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	doc.submit()
	frappe.db.commit()
	return doc.name


def reset_leave_applications(employee):
	"""Remove any Leave Applications this employee already has.

	`hr_api.apply_leave` calls frappe.db.commit(), so applications created by a test
	survive the rollback in tearDown and the next run fails with OverlapError.

	Cancel before deleting: submitting a Leave Application writes Leave Ledger
	Entries that consume balance. Deleting the row directly would leave those behind
	and quietly corrupt every balance assertion that follows.
	"""
	for la in frappe.get_all("Leave Application", filters={"employee": employee}, fields=["name", "docstatus"]):
		doc = frappe.get_doc("Leave Application", la.name)
		if doc.docstatus == 1:
			doc.flags.ignore_permissions = True
			doc.cancel()
		frappe.delete_doc("Leave Application", la.name, force=True, ignore_permissions=True)
	frappe.db.commit()


def ensure_employee_with_leave(first_name, leave_type, days=10, last_name="Employee"):
	"""An employee holding `days` of `leave_type`, ready to apply for leave.

	Returns the employee id. Allocation is submitted (docstatus 1) because an
	unsubmitted allocation grants no balance at all.
	"""
	emp = ensure_employee(first_name, last_name)

	# This hrms version resolves holidays through a submitted "Holiday List
	# Assignment", NOT the old Employee.holiday_list field. Setting that field
	# leaves get_holiday_list_for_employee() throwing "No Holiday List was found
	# ... Please assign through Holiday List Assignment", which is what it did.
	assign_holiday_list(emp)


	existing = frappe.get_all(
		"Leave Allocation",
		filters={"employee": emp, "leave_type": leave_type, "docstatus": 1},
		limit=1,
	)
	if not existing and days:
		alloc = frappe.get_doc(
			{
				"doctype": "Leave Allocation",
				"employee": emp,
				"leave_type": leave_type,
				"from_date": add_days(today(), -180),
				"to_date": add_days(today(), 180),
				"new_leaves_allocated": days,
				"carry_forward": 0,
			}
		)
		alloc.flags.ignore_permissions = True
		alloc.insert(ignore_permissions=True)
		alloc.submit()
		frappe.db.commit()

	reset_leave_applications(emp)

	return emp


def ensure_company_holiday_default():
	"""Point the company at the test holiday list, for employees without their own."""
	company = ensure_company()
	hl = ensure_holiday_list()
	if not frappe.db.get_value("Company", company, "default_holiday_list"):
		frappe.db.set_value("Company", company, "default_holiday_list", hl)
	return company


def ensure_user(email, roles=(), first_name=None):
	"""Create (or reuse) an enabled User with exactly the roles given.

	Roles are reset each time rather than added to: a user left over from an
	earlier run could still carry HR Manager, which would make a
	"non-HR cannot do this" test pass for the wrong reason.
	"""
	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
	else:
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": first_name or email.split("@")[0].title(),
				"send_welcome_email": 0,
				"enabled": 1,
			}
		)
		user.flags.ignore_permissions = True
		user.insert(ignore_permissions=True)

	user.set("roles", [])
	for r in roles:
		if frappe.db.exists("Role", r):
			user.append("roles", {"role": r})
	user.flags.ignore_permissions = True
	user.save(ignore_permissions=True)
	frappe.db.commit()
	return user.name


def link_user_to_employee(employee, email):
	"""Point an Employee at a User so hr_api._get_employee() resolves the session."""
	if frappe.db.get_value("Employee", employee, "user_id") != email:
		frappe.db.set_value("Employee", employee, "user_id", email)
		frappe.db.commit()
	return email
