"""Slice 042, Wave 2: this slice's own company, stores and people.

**Its own, on purpose.** Shared test fixtures cost Wave 1 time three times: a
company-wide Holiday List Assignment broke another file's fixture, and slice
030's store asserts an exact set of names so anybody added there breaks it.
Test data is shared state on one site, and the cheapest way to stop a fixture
being shared state is not to share it.

So everything here carries the tag **S042** and lives in a company of its own.
Nothing in this file touches slice 010's, 030's or 034's people, and no
company-wide record is created - every Holiday List Assignment is per employee.

The people, and why each exists (the spec's section 1 persona table):

    rahul     a plain employee, store A. No reports, not HR.
    sandeep   a manager, store A, with four reports. Not HR.
    priya     store HR, store A only, no reports. A Branch User Permission is
              what makes her a store's HR person.
    kamal     company-wide HR with reports.
    asha      a login with NO Employee record at all - persona rule 6.
    leaver    an Employee set to Left whose login still works.

    peers     four more people reporting to sandeep, so his team can cross the
              minimum group size of five and drop back below it.
"""

import frappe
from frappe.utils import add_days, nowdate

from alvoraa_goals.tests.utils import (
	_ensure_erpnext_company_prerequisites,
	ensure_gender,
)
from alvoraa_portal.tests.leave_fixtures import ensure_user

TAG = "S042"
COMPANY = "S042 Wave Two Company"
ABBR = "S42"
STORE_A = "S042 Store A"
STORE_B = "S042 Store B"
HOLIDAYS = "S042 Holidays"


def ensure_company():
	"""This slice's own company, so no other file's assertions move.

	`alvoraa_goals.tests.utils.ensure_company` returns whatever Company exists
	first, which on a shared site is somebody else's. Wave 2 needs its own, so
	it makes one and keeps the name.
	"""
	if frappe.db.exists("Company", COMPANY):
		return COMPANY
	_ensure_erpnext_company_prerequisites()
	doc = frappe.get_doc({
		"doctype": "Company",
		"company_name": COMPANY,
		"abbr": ABBR,
		"default_currency": "INR",
		"country": "India",
	})
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return COMPANY


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
	email = "s042.%s@example.com" % local
	name = ensure_user(email, roles=roles)
	frappe.db.set_value("User", name, "module_profile", None, update_modified=False)
	frappe.db.delete("Block Module", {"parent": name, "parenttype": "User"})
	frappe.clear_cache(user=name)
	return name


def employee(first, branch=None, reports_to=None, login=None, status="Active",
             joined="2024-01-01", designation=None):
	"""One S042 person. Saved through the document so the nested set follows."""
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
	doc.company = ensure_company()
	doc.date_of_joining = joined
	doc.status = status
	if status == "Left":
		# ERPNext refuses a Left employee with no relieving date. The leaver is
		# here to prove a live login finds nobody (SEC-14), so the date only has
		# to exist.
		doc.relieving_date = doc.relieving_date or nowdate()
	doc.branch = branch
	doc.reports_to = reports_to
	doc.user_id = login
	if designation is not None:
		if not frappe.db.exists("Designation", designation):
			frappe.get_doc({"doctype": "Designation",
			                "designation_name": designation}).insert(
				ignore_permissions=True)
		doc.designation = designation
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
	assignment, so one of those is the widest shared state a fixture can make -
	it broke another file's fixture in Wave 1.
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


def store_permission(login, branch=STORE_A):
	"""What makes an HR user a STORE's HR user. Given per test, taken away after."""
	if not frappe.db.exists("User Permission",
	                        {"user": login, "allow": "Branch", "for_value": branch}):
		frappe.get_doc({"doctype": "User Permission", "user": login,
		                "allow": "Branch", "for_value": branch,
		                "apply_to_all_doctypes": 1}).insert(ignore_permissions=True)
	frappe.clear_cache(user=login)
	frappe.db.commit()


def drop_store_permission(login):
	frappe.db.delete("User Permission", {"user": login, "allow": "Branch"})
	frappe.clear_cache(user=login)
	frappe.db.commit()
