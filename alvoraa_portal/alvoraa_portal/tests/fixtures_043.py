"""Slice 043, Wave 3: this slice's own company, stores, people and pay records.

**Its own, on purpose.** Shared fixtures have cost four slices time on this
project: a company-wide Holiday List Assignment broke another file's fixture in
Wave 1, and slice 030's store asserts an exact set of names, so anybody added
there breaks it. Test data is shared state on one site, and the cheapest way to
stop a fixture being shared state is not to share it.

Everything here carries the tag **S043** and lives in companies of its own.
Nothing in this file touches slice 010's, 030's, 034's or 042's people, and no
company-wide record is created - every Holiday List Assignment is per employee.

The people, and why each exists:

    rahul     a plain employee in company A, store A. The person every screen
              in this wave is drawn for.
    sandeep   rahul's manager. He is here to NOT learn things (AC-17).
    asha      a login with NO Employee record at all.
    leaver    an Employee set to Left whose login still works.
    bhavna    an employee in **company B**. She exists so the shift-type scope
              has a second company to fail to leak (AC-52).

Pay records: one submitted Salary Slip for rahul, so the payslip list has
something true to refuse or return, and a Salary Structure Assignment so an
Attendance Deduction can be valued at all.
"""

import frappe
from frappe.utils import add_days, nowdate

from alvoraa_goals.tests.utils import (
	_ensure_erpnext_company_prerequisites,
	ensure_gender,
)
from alvoraa_portal.tests.leave_fixtures import ensure_user

TAG = "S043"
COMPANY_A = "S043 Wave Three Company"
ABBR_A = "S43A"
COMPANY_B = "S043 Other Company"
ABBR_B = "S43B"
STORE_A = "S043 Store A"
STORE_B = "S043 Store B"
HOLIDAYS = "S043 Holidays"

SHIFT_A = "S043 Day Shift"
SHIFT_B = "S043 Night Shift"
SHIFT_UNUSED = "S043 Unused Shift"


def ensure_company(name=COMPANY_A, abbr=ABBR_A):
	"""This slice's own company, so no other file's assertions move.

	`alvoraa_goals.tests.utils.ensure_company` returns whatever Company exists
	first, which on a shared site is somebody else's.
	"""
	if frappe.db.exists("Company", name):
		return name
	_ensure_erpnext_company_prerequisites()
	doc = frappe.get_doc({
		"doctype": "Company",
		"company_name": name,
		"abbr": abbr,
		"default_currency": "INR",
		"country": "India",
	})
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return name


def ensure_branches():
	for branch in (STORE_A, STORE_B):
		if not frappe.db.exists("Branch", branch):
			frappe.get_doc({"doctype": "Branch", "branch": branch}).insert(
				ignore_permissions=True)


def user(local, roles):
	"""A login with the given roles, and nothing the site's plan would block.

	`module_access` points every new user at the site's plan profile. On a test
	site with no plan that profile blocks every Alvoraa module, so a test about
	OUR rules would pass or fail because of the plan.
	"""
	email = "s043.%s@example.com" % local
	name = ensure_user(email, roles=roles)
	frappe.db.set_value("User", name, "module_profile", None, update_modified=False)
	frappe.db.delete("Block Module", {"parent": name, "parenttype": "User"})
	frappe.clear_cache(user=name)
	return name


def employee(first, branch=None, reports_to=None, login=None, status="Active",
             joined="2024-01-01", company=None, default_shift=None):
	"""One S043 person. Saved through the document so the nested set follows."""
	name = frappe.db.get_value("Employee", {"first_name": first, "last_name": TAG}, "name")
	if name:
		doc = frappe.get_doc("Employee", name)
	else:
		doc = frappe.get_doc({
			"doctype": "Employee",
			"first_name": first,
			"last_name": TAG,
			"gender": ensure_gender(),
			"date_of_birth": "1990-01-01",
		})
	doc.company = company or ensure_company()
	doc.date_of_joining = joined
	doc.status = status
	if status == "Left":
		# ERPNext refuses a Left employee with no relieving date.
		doc.relieving_date = doc.relieving_date or nowdate()
	doc.branch = branch
	doc.reports_to = reports_to
	doc.user_id = login
	doc.default_shift = default_shift
	# No automatic "Employee = self" User Permission. It narrows every list the
	# user sees, so a test about OUR rules would pass or fail because of it.
	doc.create_user_permission = 0
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)
	if login:
		frappe.db.delete("User Permission", {"user": login})
		frappe.clear_cache(user=login)
	frappe.db.commit()
	return doc.name


def holiday_list(employees):
	"""A Holiday List assigned PER EMPLOYEE.

	Never company-wide. Frappe HR refuses a second overlapping company-wide
	assignment, so one of those is the widest shared state a fixture can make.
	"""
	if not frappe.db.exists("Holiday List", HOLIDAYS):
		frappe.get_doc({
			"doctype": "Holiday List", "holiday_list_name": HOLIDAYS,
			"from_date": add_days(nowdate(), -2000), "to_date": add_days(nowdate(), 1200),
		}).insert(ignore_permissions=True)
	for name in employees:
		if frappe.db.exists("Holiday List Assignment",
		                    {"assigned_to": name, "holiday_list": HOLIDAYS,
		                     "docstatus": 1}):
			continue
		frappe.get_doc({
			"doctype": "Holiday List Assignment", "holiday_list": HOLIDAYS,
			"applicable_for": "Employee", "assigned_to": name,
			"from_date": add_days(nowdate(), -2000),
		}).insert(ignore_permissions=True).submit()
	frappe.db.commit()
	return HOLIDAYS


# ── Shifts ───────────────────────────────────────────────────────────────────
#
# Shift Type has NO `company` field (checked in
# hrms/hrms/hr/doctype/shift_type/shift_type.json), which is why 043 AC-52 was
# rewritten: "the caller's company's shift types" has nothing to filter on. The
# scope comes from Shift Assignment, which does carry a company. These three
# exist so a test can prove the difference:
#
#   SHIFT_A       assigned in company A  -> company A's people see it
#   SHIFT_B       assigned in company B  -> company A's people must NOT see it
#   SHIFT_UNUSED  assigned nowhere       -> nobody sees it

def ensure_shift(name, start="09:30:00", end="18:30:00"):
	if not frappe.db.exists("Shift Type", name):
		frappe.get_doc({
			"doctype": "Shift Type", "__newname": name, "name": name,
			"start_time": start, "end_time": end,
		}).insert(ignore_permissions=True)
		frappe.db.commit()
	return name


def assign_shift(employee_name, shift, company, start=None):
	"""A submitted Shift Assignment, which is what puts a shift "in use"."""
	start = start or add_days(nowdate(), -30)
	existing = frappe.db.exists("Shift Assignment", {
		"employee": employee_name, "shift_type": shift, "docstatus": 1})
	if existing:
		return existing
	doc = frappe.get_doc({
		"doctype": "Shift Assignment", "employee": employee_name,
		"shift_type": shift, "company": company, "start_date": start,
		"status": "Active",
	})
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	doc.submit()
	frappe.db.commit()
	return doc.name


# ── Pay ──────────────────────────────────────────────────────────────────────

def salary_component(name, kind="Earning", company=COMPANY_A):
	if not frappe.db.exists("Salary Component", name):
		frappe.get_doc({
			"doctype": "Salary Component", "salary_component": name,
			"type": kind, "salary_component_abbr": name[:5].replace(" ", ""),
		}).insert(ignore_permissions=True)
		frappe.db.commit()
	return name


def salary_slip(employee_name, company=COMPANY_A, start=None, end=None, submit=True):
	"""One Salary Slip for this employee.

	Built by hand rather than through a Salary Structure, because every test in
	this slice reads a slip and none of them tests how a slip is calculated.
	Frappe HR's own calculation is not what Wave 3 shows or changes.
	"""
	start = start or add_days(nowdate(), -60)
	end = end or add_days(nowdate(), -31)
	existing = frappe.db.get_value("Salary Slip", {
		"employee": employee_name, "start_date": start}, "name")
	if existing:
		return existing
	doc = frappe.get_doc({
		"doctype": "Salary Slip",
		"employee": employee_name,
		"company": company,
		"start_date": start,
		"end_date": end,
		"posting_date": end,
		"currency": "INR",
		"payroll_frequency": "Monthly",
	})
	doc.flags.ignore_permissions = True
	# Salary Slip's own validate() pulls the employee's holiday list and the
	# salary structure, because it is there to CALCULATE a slip. Nothing in this
	# slice calculates one - every test reads a slip that payroll already made -
	# so the fixture skips the calculation and stores the fields the portal
	# actually returns. Building a real structure, assignment and payroll period
	# for each of them would make the fixture the thing most likely to break.
	doc.flags.ignore_validate = True
	doc.insert(ignore_permissions=True, ignore_mandatory=True)
	if submit:
		doc.db_set("docstatus", 1)
	frappe.db.commit()
	return doc.name
