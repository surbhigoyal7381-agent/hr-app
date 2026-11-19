"""Slice 085 (ALV-392), AC-3 and AC-4: a Held day costs a day's pay on a REAL slip.

Real draft Salary Slips, built through Frappe HR's own calculation, at a company
with no pay rule set (the path `held_day.deduct_held_days` serves). The same two
days are compared as Present and as Held, under both settings of
`consider_unmarked_attendance_as`: a Held row is a marked row, so it must not
fall back to "unmarked" and be paid under either.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, get_first_day, get_last_day, getdate, nowdate

from alvoraa_portal import held_day
from alvoraa_portal.tests.utils import ensure_fiscal_years

COMPANY = "ALV085 Slip Co"
ABBR = "A85S"
HOLIDAYS = "ALV085 Slip Holidays"
SHIFT = "ALV085 Slip Shift"
BASIC = "ALV085 Basic"
STRUCTURE = "ALV085 Slip Structure"
BASE = 30000.0

START = getdate(get_first_day(add_months(nowdate(), -1)))
END = getdate(get_last_day(START))


def _insert(d, submit=False):
	doc = frappe.get_doc(d)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	if submit:
		doc.submit()
	return doc


def setUpModule():
	held_day.after_migrate()
	ensure_fiscal_years(START, END, nowdate())
	frappe.set_user("Administrator")
	if not frappe.db.exists("Holiday List", HOLIDAYS):
		_insert({"doctype": "Holiday List", "holiday_list_name": HOLIDAYS,
		         "from_date": add_days(START, -400), "to_date": add_days(END, 400)})
	if not frappe.db.exists("Company", COMPANY):
		_insert({"doctype": "Company", "company_name": COMPANY, "abbr": ABBR,
		         "default_currency": "INR", "country": "India"})
	frappe.db.set_value("Company", COMPANY, "default_holiday_list", HOLIDAYS)
	if not frappe.db.exists("Holiday List Assignment", {"assigned_to": COMPANY, "docstatus": 1}):
		_insert({"doctype": "Holiday List Assignment", "applicable_for": "Company",
		         "assigned_to": COMPANY, "holiday_list": HOLIDAYS,
		         "from_date": add_days(START, -390)}, submit=True)
	if not frappe.db.exists("Shift Type", SHIFT):
		_insert({"doctype": "Shift Type", "name": SHIFT, "start_time": "10:00:00", "end_time": "18:00:00"})
	if not frappe.db.exists("Salary Component", BASIC):
		_insert({"doctype": "Salary Component", "salary_component": BASIC,
		         "salary_component_abbr": "A85B", "type": "Earning",
		         "depends_on_payment_days": 1, "is_tax_applicable": 0})
	if not frappe.db.exists("Salary Structure", STRUCTURE):
		_insert({"doctype": "Salary Structure", "name": STRUCTURE, "company": COMPANY,
		         "payroll_frequency": "Monthly", "currency": "INR", "is_active": "Yes",
		         "earnings": [{"salary_component": BASIC, "amount_based_on_formula": 1,
		                       "formula": "base", "depends_on_payment_days": 1}]}, submit=True)
	frappe.db.commit()


class RealSlip(FrappeTestCase):
	_slot = 0

	def setUp(self):
		frappe.set_user("Administrator")
		RealSlip._slot += 1
		frappe.db.set_single_value("Payroll Settings", "payroll_based_on", "Attendance")

	def _employee(self):
		emp = _insert({"doctype": "Employee", "first_name": "Slipper%d" % RealSlip._slot,
		               "last_name": "A085", "company": COMPANY, "status": "Active",
		               "gender": frappe.db.get_value("Gender", {}, "name") or "Male",
		               "date_of_birth": "1990-01-01", "date_of_joining": add_days(START, -200),
		               "default_shift": SHIFT, "holiday_list": HOLIDAYS,
		               "create_user_permission": 0}).name
		_insert({"doctype": "Salary Structure Assignment", "employee": emp,
		         "salary_structure": STRUCTURE, "company": COMPANY, "currency": "INR",
		         "from_date": add_days(START, -150), "base": BASE}, submit=True)
		return emp

	def _present(self, emp, day):
		return _insert({"doctype": "Attendance", "employee": emp, "company": COMPANY,
		                "attendance_date": str(day), "status": "Present", "shift": SHIFT}, submit=True).name

	def _payment_days(self, emp):
		slip = _insert({"doctype": "Salary Slip", "employee": emp, "company": COMPANY,
		                "start_date": START, "end_date": END, "posting_date": END,
		                "payroll_frequency": "Monthly", "currency": "INR"})
		return slip.payment_days

	def test_two_held_days_cost_two_days_under_both_unmarked_settings(self):
		for setting in ("Present", "Absent"):
			frappe.db.set_single_value("Payroll Settings", "consider_unmarked_attendance_as", setting)
			emp = self._employee()
			rows = [self._present(emp, add_days(START, 1)), self._present(emp, add_days(START, 2))]
			as_present = self._payment_days(emp)
			for r in rows:
				frappe.db.set_value("Attendance", r, "status", "Held")
			frappe.db.delete("Salary Slip", {"employee": emp})
			as_held = self._payment_days(emp)
			self.assertEqual(as_present - as_held, 2, "consider_unmarked_attendance_as=" + setting)
