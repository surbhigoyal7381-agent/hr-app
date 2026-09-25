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
from frappe.utils import add_days, flt, nowdate

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


# ── The browser check's data (043 review F5) ─────────────────────────────────


def seed_deduction_for_browser_check(login=None):
	"""One real loss-of-pay line with a real Attendance Deduction behind it.

	`scripts/browser_check_time_pay.js` is the only check that renders the Why?
	sheet in a real browser engine. It used to print SKIP and exit 0 when the
	site had no such line, so its seven assertions may never have run at all -
	the review's F5, and lesson 2 again: *ask what must be true in the data for
	the claim to be observable.* The script now exits 2 instead, and this is the
	function its error message tells you to run.

	It builds the whole chain the sheet follows, because a break anywhere in it
	produces the same empty screen:

	    Salary Detail.additional_salary
	      -> Additional Salary.ref_doctype / ref_docname
	        -> Attendance Deduction
	          -> its violation rows and its rule

	Safe to run twice: everything is looked up before it is made.

	Run it as:
	    bench --site <site> execute \
	      alvoraa_portal.tests.fixtures_043.seed_deduction_for_browser_check
	"""
	ensure_company()
	ensure_branches()

	if login:
		# A login was named - almost always the browser check's own probe user,
		# which the script's docstring insists must NOT be a fixture person.
		# Use the Employee record it already has; never move a login onto one of
		# this file's people, which is how a probe run once gave a fixture
		# employee System Manager and broke two unrelated tests.
		employee_name = frappe.db.get_value(
			"Employee", {"user_id": login, "status": "Active"}, "name")
		if not employee_name:
			frappe.throw(
				"%s has no Active Employee record. Give the probe user one "
				"before seeding - this function will not take one of the S043 "
				"fixture people and point it at your login." % login)
	else:
		login = user("rahul", ["Employee"])
		employee_name = employee("Rahul", branch=STORE_A, login=login)

	component = salary_component("S043 Late Coming Deduction", kind="Deduction")
	rule = _browser_check_rule(component)
	deduction = _browser_check_deduction(employee_name, rule)
	extra = _browser_check_additional_salary(employee_name, component, deduction)
	slip = _browser_check_slip(employee_name, component, extra)

	frappe.db.commit()
	print("seeded: deduction %s -> additional salary %s -> payslip %s"
	      % (deduction, extra, slip))
	print("Sign in as %s and open /hrms-employee-next#pay." % login)
	return {"deduction": deduction, "additional_salary": extra, "payslip": slip}


def _browser_check_rule(component):
	name = "S043 Browser Check Rule"
	if frappe.db.exists("Attendance Deduction Rule", name):
		return name
	frappe.get_doc({
		"doctype": "Attendance Deduction Rule",
		"rule_name": name,
		"company": COMPANY_A,
		"enabled": 1,
		# The browser check asserts the week-start day came from the RECORD and
		# not from the copy, so this has to be a real value it can find.
		"week_start_day": "Monday",
		"late_threshold_minutes": 10,
		"free_violations_per_week": 1,
		"deduction_per_violation_days": 0.5,
		# The rule's own validate() refuses "deduct from leave first" with no
		# leave types on it. The browser check is about the Why? SHEET, not
		# about leave, so the simplest honest rule is one that goes straight to
		# loss of pay.
		"deduct_from_leave_first": 0,
		"lwp_salary_component": component,
	}).insert(ignore_permissions=True)
	return name


def _browser_check_deduction(employee_name, rule):
	"""A SUBMITTED Attendance Deduction with violations on it.

	Two things here are deliberate and both are lessons this slice already paid
	for.

	**`validate()` computes the days; this fixture does not.** Passing
	`deduction_days` in would be thrown away - that is how slice 043's own year
	table summed to 0.0 while every assertion passed, because 0 equalled 0
	(`03-implementation-notes.md` section 16, finding 6). The violations are the
	input; the days are the rule's answer; the fixture asserts afterwards that
	the answer is not zero, so a rule change that values this week at nothing
	fails here rather than producing an empty Why? sheet.

	**`db_set("docstatus", 1)` rather than `submit()`.** `on_submit` values the
	loss of pay, which needs a Salary Structure Assignment, and this fixture is
	about the explanation rather than the valuation. The same shape
	`test_why_sheet_043._deduction` already uses, for the same reason.
	"""
	existing = frappe.db.get_value(
		"Attendance Deduction",
		{"employee": employee_name, "rule": rule, "docstatus": 1}, "name")
	if existing:
		return existing

	week_start = add_days(nowdate(), -45)
	doc = frappe.get_doc({
		"doctype": "Attendance Deduction",
		"employee": employee_name,
		"company": COMPANY_A,
		"rule": rule,
		"week_start": week_start,
		"week_end": add_days(week_start, 6),
		"violations": [
			{"attendance_date": add_days(week_start, 1), "violation_type": "Late Arrival",
			 "expected_time": "09:30:00", "actual_time": "10:05:00", "minutes": 35},
			{"attendance_date": add_days(week_start, 2), "violation_type": "Late Arrival",
			 "expected_time": "09:30:00", "actual_time": "10:12:00", "minutes": 42},
			{"attendance_date": add_days(week_start, 3), "violation_type": "Late Arrival",
			 "expected_time": "09:30:00", "actual_time": "10:40:00", "minutes": 70},
		],
	})
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True, ignore_mandatory=True)
	doc.db_set("docstatus", 1, update_modified=False)
	doc.reload()
	if not flt(doc.deduction_days):
		frappe.throw(
			"the rule valued this week at 0 days, so the Why? sheet would open "
			"on an empty week and the browser check would prove nothing. "
			"Deduction %s, rule %s." % (doc.name, rule))
	return doc.name


def _browser_check_additional_salary(employee_name, component, deduction):
	existing = frappe.db.get_value(
		"Additional Salary",
		{"employee": employee_name, "ref_doctype": "Attendance Deduction",
		 "ref_docname": deduction, "docstatus": 1}, "name")
	if existing:
		return existing
	doc = frappe.get_doc({
		"doctype": "Additional Salary",
		"employee": employee_name,
		"company": COMPANY_A,
		"salary_component": component,
		"amount": 500.0,
		"payroll_date": add_days(nowdate(), -31),
		"currency": "INR",
		"overwrite_salary_structure_amount": 0,
		"ref_doctype": "Attendance Deduction",
		"ref_docname": deduction,
	})
	doc.flags.ignore_permissions = True
	doc.flags.ignore_validate = True
	doc.insert(ignore_permissions=True, ignore_mandatory=True)
	doc.db_set("docstatus", 1)
	return doc.name


def _browser_check_slip(employee_name, component, extra):
	"""The newest slip, carrying the deduction line the Why? button hangs off.

	`get_pay` shows the NEWEST slip in full, so this one is dated this month -
	otherwise the screen would open on a slip with no deduction line and the
	check would still find no `[data-why]`.
	"""
	start = add_days(nowdate(), -30)
	name = salary_slip(employee_name, start=start, end=nowdate())
	slip = frappe.get_doc("Salary Slip", name)
	already = [r for r in (slip.deductions or [])
	           if r.get("additional_salary") == extra]
	if already:
		return name
	slip.append("deductions", {
		"salary_component": component,
		"amount": 500.0,
		"additional_salary": extra,
	})
	slip.flags.ignore_validate = True
	slip.flags.ignore_permissions = True
	slip.db_set({"gross_pay": 30000.0, "total_deduction": 500.0,
	             "net_pay": 29500.0, "rounded_total": 29500.0},
	            update_modified=False)
	for row in slip.deductions:
		row.db_insert() if not row.name or not frappe.db.exists(
			row.doctype, row.name) else row.db_update()
	return name
