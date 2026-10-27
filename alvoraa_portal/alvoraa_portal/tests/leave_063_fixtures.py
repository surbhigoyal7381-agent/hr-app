"""The world slice 063's site tests need: a company whose pay rule set is ON.

Spec 11 calls it the "DTC fixture". Built once per module, named so nothing
else on the test site collides with it, and repaired rather than trusted when it
already exists. Every name starts with L063.

People (Reports To in brackets):
  Priya  - class A, named leave approver Sunil, branch North  (-> Sunil)
  Rohit  - class A, approver Sunil, branch North               (-> Sunil)
  Manoj  - Contract (earns no leave), no login                 (-> Sunil)
  Sunil  - store manager, Leave Approver                       (-> Kavita)
  Kavita - top of the chain                                    (none)
  Ritika - HR Manager, company-wide, approver Kavita           (-> Kavita)
  Anil   - HR User limited to branch South (so NOT Priya's)
"""

import frappe
from frappe.utils import add_days, get_first_day, get_last_day, getdate, nowdate

from alvoraa_portal.tests.test_payroll_rules import DTC_SLABS
from alvoraa_portal.tests.utils import ensure_fiscal_years

COMPANY = "L063 Rules Co"
ABBR = "L063R"
OTHER_COMPANY = "L063 Plain Co"     # no rule set at all
OFF_COMPANY = "L063 Off Co"         # rule set present but switched off (DTC today)
HOLIDAYS = "L063 Holidays"
SPECIAL = "L063 Special Days"
SHIFT = "L063 Shift"
PAID = "Paid Leaves"
HK = "L063 Table Staff"       # the designation whose leave comes from the table
PANTRY = "L063 Other Staff"
DOMAIN = "l063.test"


def user(first):
	return "%s@%s" % (first.lower(), DOMAIN)


def _insert(d):
	doc = frappe.get_doc(d)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	return doc


def _holiday_list(name, holidays=()):
	start, end = getdate(add_days(nowdate(), -400)), getdate(add_days(nowdate(), 400))
	if not frappe.db.exists("Holiday List", name):
		_insert({"doctype": "Holiday List", "holiday_list_name": name,
		         "from_date": start, "to_date": end,
		         "holidays": [{"holiday_date": h, "description": d} for h, d in holidays]})
	return name


def _company(name, abbr):
	if not frappe.db.exists("Company", name):
		_insert({"doctype": "Company", "company_name": name, "abbr": abbr,
		         "default_currency": "INR", "country": "India"})
	frappe.db.set_value("Company", name, "default_holiday_list", HOLIDAYS)
	return name


def _named(doctype, name, field):
	if not frappe.db.exists(doctype, name):
		_insert({"doctype": doctype, field: name})
	return name


def _gender():
	g = frappe.db.get_value("Gender", {}, "name")
	return g or _insert({"doctype": "Gender", "gender": "Other"}).name


def ensure_user(email, roles, first, employee=None):
	"""The login with exactly these roles.

	`employee` is linked BEFORE the roles are saved. ERPNext's User validate
	(validate_employee_role) silently drops the Employee role from a user no
	Employee points at, so on a fresh site - where the user is new - Priya
	used to end up with no roles at all and every permission-checked call she
	made failed (CI run 39714021470). A second run passed only because the
	link already existed by then.
	"""
	if frappe.db.exists("User", email):
		u = frappe.get_doc("User", email)
	else:
		u = frappe.get_doc({"doctype": "User", "email": email, "first_name": first,
		                    "send_welcome_email": 0, "enabled": 1})
		u.flags.ignore_permissions = True
		u.insert(ignore_permissions=True)
	if employee:
		frappe.db.set_value("Employee", employee, "user_id", email)
	u.enabled = 1
	u.set("roles", [])
	for r in roles:
		u.append("roles", {"role": r})
	u.flags.ignore_permissions = True
	u.save(ignore_permissions=True)
	return u.name


def ensure_employee(first, company=COMPANY, grade=None, category=None, branch=None,
                    reports_to=None, approver=None, login_roles=None, designation=None):
	name = frappe.db.get_value("Employee", {"first_name": first, "last_name": "L063"}, "name")
	values = {"company": company, "grade": grade, "employment_type": category,
	          "branch": branch, "reports_to": reports_to, "leave_approver": approver,
	          "status": "Active", "default_shift": SHIFT, "designation": designation}
	if not name:
		doc = _insert(dict({"doctype": "Employee", "first_name": first, "last_name": "L063",
		                    "gender": _gender(), "date_of_birth": "1990-01-01",
		                    "date_of_joining": add_days(nowdate(), -380),
		                    "create_user_permission": 0}, **values))
		name = doc.name
	else:
		frappe.db.set_value("Employee", name, values)
	if login_roles is not None:
		email = ensure_user(user(first), login_roles, first, employee=name)
		# Staff get a User Permission on their own record, as DTC's 7 staff
		# logins do; HR do not (DTC's 3 HR logins have none, SEC-8 note).
		own = {"user": email, "allow": "Employee", "for_value": name}
		hr = bool({"HR Manager", "HR User"} & set(login_roles))
		if not hr and not frappe.db.exists("User Permission", own):
			_insert(dict(own, doctype="User Permission", apply_to_all_doctypes=1))
		if hr:
			frappe.db.delete("User Permission", own)
	else:
		frappe.db.set_value("Employee", name, "user_id", None)
	return name


def ensure_world():
	"""Build or repair everything. Returns a dict of the employee ids."""
	ensure_fiscal_years()
	frappe.set_user("Administrator")
	_holiday_list(HOLIDAYS)
	_holiday_list(SPECIAL)
	for name, abbr in ((COMPANY, ABBR), (OTHER_COMPANY, "L063P"), (OFF_COMPANY, "L063O")):
		_company(name, abbr)
		# This hrms reads holidays from a submitted Holiday List Assignment only.
		if not frappe.db.exists("Holiday List Assignment", {"assigned_to": name, "docstatus": 1}):
			a = frappe.get_doc({"doctype": "Holiday List Assignment", "applicable_for": "Company",
			                    "assigned_to": name, "holiday_list": HOLIDAYS,
			                    "from_date": add_days(nowdate(), -390)})
			a.flags.ignore_permissions = True
			a.insert(ignore_permissions=True)
			a.submit()
	if not frappe.db.exists("Shift Type", SHIFT):
		_insert({"doctype": "Shift Type", "name": SHIFT,
		         "start_time": "10:30:00", "end_time": "20:30:00"})
	for g in ("L063-A", "L063-B", "L063-NoLeave"):
		_named("Employee Grade", g, "__newname")
	_named("Employment Type", "L063 Contract", "employee_type_name")
	for b in ("L063 North", "L063 South"):
		_named("Branch", b, "branch")
	for d in (HK, PANTRY):
		_named("Designation", d, "designation_name")

	_rule_set(COMPANY, enabled=1)
	_rule_set(OFF_COMPANY, enabled=0)

	if not frappe.db.exists("Leave Type", PAID):
		_insert({"doctype": "Leave Type", "leave_type_name": PAID, "is_lwp": 0,
		         "allow_negative": 1, "include_holiday": 1, "allow_encashment": 0,
		         "is_carry_forward": 0, "is_earned_leave": 0})
	if not frappe.db.get_value("Leave Type", "Leave Without Pay", "is_lwp"):
		if frappe.db.exists("Leave Type", "Leave Without Pay"):
			frappe.db.set_value("Leave Type", "Leave Without Pay", "is_lwp", 1)
		else:
			_insert({"doctype": "Leave Type", "leave_type_name": "Leave Without Pay",
			         "is_lwp": 1, "include_holiday": 1})

	p = {}
	p["kavita"] = ensure_employee("Kavita", login_roles=["Employee"])
	kav = user("Kavita")
	p["sunil"] = ensure_employee("Sunil", reports_to=p["kavita"],
	                             login_roles=["Employee", "Leave Approver"])
	sun = user("Sunil")
	p["priya"] = ensure_employee("Priya", grade="L063-A", branch="L063 North",
	                             reports_to=p["sunil"], approver=sun, login_roles=["Employee"])
	p["rohit"] = ensure_employee("Rohit", grade="L063-A", branch="L063 North",
	                             reports_to=p["sunil"], approver=sun, login_roles=["Employee"])
	p["manoj"] = ensure_employee("Manoj", category="L063 Contract", branch="L063 North",
	                             reports_to=p["sunil"], approver=sun)
	p["ritika"] = ensure_employee("Ritika", grade="L063-B", reports_to=p["kavita"], approver=kav,
	                              login_roles=["Employee", "HR Manager"])
	p["anil"] = ensure_employee("Anil", branch="L063 South", reports_to=p["kavita"], approver=kav,
	                            login_roles=["Employee", "HR User"])
	anil = user("Anil")
	if not frappe.db.exists("User Permission", {"user": anil, "allow": "Branch",
	                                            "for_value": "L063 South"}):
		_insert({"doctype": "User Permission", "user": anil, "allow": "Branch",
		         "for_value": "L063 South", "apply_to_all_doctypes": 1})
	# The days-present table (slice 063): Housekeeping-shaped staff, all without a login.
	p["geeta"] = ensure_employee("Geeta", grade="L063-A", category="L063 Contract", branch="L063 North",
	                             reports_to=p["sunil"], approver=sun, designation=HK)
	p["sushila"] = ensure_employee("Sushila", grade="L063-NoLeave", category="L063 Contract",
	                               branch="L063 North", reports_to=p["sunil"], approver=sun,
	                               designation=HK)
	p["hari"] = ensure_employee("Hari", grade="L063-A", branch="L063 North", reports_to=p["sunil"],
	                            approver=sun, designation=HK)
	p["pooja"] = ensure_employee("Pooja", grade="L063-A", category="L063 Contract",
	                             branch="L063 North", reports_to=p["sunil"], approver=sun,
	                             designation=PANTRY)
	p["plain"] = ensure_employee("Plain", company=OTHER_COMPANY, login_roles=["Employee"])
	p["off"] = ensure_employee("Offco", company=OFF_COMPANY, grade="L063-A",
	                           login_roles=["Employee"])
	frappe.db.commit()
	return p


HK_ROWS = [("30-31", 0, 5, 0), ("30-31", 6, 12, 1), ("30-31", 13, 18, 2), ("30-31", 19, 25, 3),
           ("30-31", 26, 31, 4), ("28-29", 0, 4, 0), ("28-29", 5, 11, 1), ("28-29", 12, 17, 2),
           ("28-29", 18, 24, 3), ("28-29", 25, 29, 4)]


def credit_rows(designation=HK):
	"""DTC's ten days-present rows (spec 7.1), for the designation given."""
	return [{"designation": designation, "month_length": m, "days_from": a, "days_to": b, "credits": c}
	        for m, a, b, c in HK_ROWS]


def _rule_set(company, enabled):
	name = frappe.db.get_value("Alvoraa Payroll Rule Set", {"company": company}, "name")
	if name:
		frappe.db.set_value("Alvoraa Payroll Rule Set", name, "enabled", enabled)
		if company == COMPANY and not frappe.db.exists(
				"Alvoraa Leave Credit Row", {"parent": name, "designation": HK}):
			rs = frappe.get_doc("Alvoraa Payroll Rule Set", name)
			rs.set("leave_credit_rows", credit_rows())
			rs.flags.ignore_permissions = True
			rs.save()
		frappe.clear_document_cache("Alvoraa Payroll Rule Set", name)
		return name
	doc = frappe.get_doc({
		"doctype": "Alvoraa Payroll Rule Set", "company": company, "enabled": enabled,
		"grace_minutes": 6, "free_reds_per_month": 2, "special_day_multiplier": 2,
		"special_day_holiday_list": SPECIAL, "leave_threshold_days": 15,
		"accrual_month_days": 15, "leave_class_field": "grade",
		"category_field": "employment_type",
		"slabs": [{"percent_from": s.percent_from, "percent_to": s.percent_to,
		           "quarters_off": s.quarters_off, "raises_red": s.raises_red}
		          for s in DTC_SLABS],
		"leave_classes": [
			{"leave_class": "L063-A", "period_days": 15, "credit_per_period": 4,
			 "monthly_credits": 4},
			{"leave_class": "L063-B", "period_days": 15, "credit_per_period": 3,
			 "monthly_credits": 3}],
		"categories": [{"category": "L063 Contract", "earns_leave_credits": 0,
		                "earns_marks": 0, "doubles_deduction": 0}],
		"mark_rates": [{"grade": "L063-A", "amount_per_mark": 100}],
		"leave_credit_rows": credit_rows() if company == COMPANY else [],
	})
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


def leave_world(people):
	"""Undo what this module switched on, so DTC's rules cannot reach a later
	test module: the people's leave, and the two L063 rule sets. The companies
	stay; with no rule set they are ordinary companies. ensure_world() puts the
	rule sets back for the next module that needs them."""
	clear_leave(*people)
	for name in frappe.get_all("Alvoraa Payroll Rule Set",
	                           filters={"company": ["in", [COMPANY, OFF_COMPANY]]}, pluck="name"):
		frappe.delete_doc("Alvoraa Payroll Rule Set", name, force=True, ignore_permissions=True)
	frappe.clear_cache(doctype="Alvoraa Payroll Rule Set")
	frappe.db.commit()


def set_special_day(day, description="Festive sale"):
	"""Make `day` the one special day (replacing any other)."""
	doc = frappe.get_doc("Holiday List", SPECIAL)
	doc.set("holidays", [{"holiday_date": getdate(day), "description": description}])
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)


def clear_leave(*employees):
	"""Remove every Leave Application and the leave's attendance for these
	people. The endpoints commit, so a rollback alone would not undo them."""
	frappe.set_user("Administrator")
	names = frappe.get_all("Leave Application", filters={"employee": ["in", list(employees) or [""]]},
	                       pluck="name")
	if names:
		frappe.db.delete("Notification Log", {"document_type": "Leave Application",
		                                      "document_name": ["in", names]})
	for emp in employees:
		for la in frappe.get_all("Leave Application", filters={"employee": emp},
		                         fields=["name", "docstatus"]):
			if la.docstatus == 1:
				doc = frappe.get_doc("Leave Application", la.name)
				doc.flags.ignore_permissions = True
				doc.cancel()
			frappe.delete_doc("Leave Application", la.name, force=True, ignore_permissions=True)
		for table in ("Attendance", "Employee Checkin", "Attendance Request"):
			for name in frappe.get_all(table, filters={"employee": emp}, pluck="name"):
				frappe.db.delete(table, {"name": name})
	frappe.db.commit()


def month_day(n):
	"""Day n of the current month, or None when the month has no such day."""
	first = get_first_day(nowdate())
	d = add_days(first, n - 1)
	return str(d) if getdate(d) <= get_last_day(nowdate()) else None


def future_day(k=1):
	"""k days ahead, still inside this month; None near the month end."""
	d = getdate(add_days(nowdate(), k))
	return str(d) if d <= get_last_day(nowdate()) else None


def past_day(k=1):
	"""k days back, still inside this month; None near the 1st."""
	d = getdate(add_days(nowdate(), -k))
	return str(d) if d >= get_first_day(nowdate()) else None


def apply_as(email, **kw):
	from alvoraa_portal import hr_api

	frappe.set_user(email)
	try:
		return hr_api.apply_leave(**kw)
	finally:
		frappe.set_user("Administrator")


def approve(name, by="Administrator", action="approve"):
	from alvoraa_portal import hr_api

	frappe.set_user(by)
	try:
		return hr_api.action_leave(name, action)
	finally:
		frappe.set_user("Administrator")
