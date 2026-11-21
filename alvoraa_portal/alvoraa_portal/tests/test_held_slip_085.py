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
		self.last_slip = slip
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
			# AC-6: the payslip payload names the two held days, and no held day when none.
			from alvoraa_portal import hr_api
			self.assertEqual(hr_api._payslip_payload(self.last_slip)["held_dates"],
			                 [str(add_days(START, 1)), str(add_days(START, 2))])
			self.assertEqual(hr_api._payslip_payload(
				frappe._dict(self.last_slip.as_dict(), earnings=[], deductions=[]))["held_dates"][:0], [])


class SubmitKeepsTheHold(RealSlip):
	"""Review B-1: Frappe validates again when a slip is submitted and counts every
	day as paid. The hold must run in that validate too, or every slip that goes
	through Payroll Entry pays its Held days."""

	def test_a_real_submit_keeps_payment_days_and_net_pay_from_the_draft(self):
		frappe.db.set_single_value("Payroll Settings", "consider_unmarked_attendance_as", "Present")
		emp = self._employee()
		rows = [self._present(emp, add_days(START, 1)), self._present(emp, add_days(START, 2))]
		whole = self._payment_days(emp)
		for r in rows:
			frappe.db.set_value("Attendance", r, "status", "Held")
		frappe.db.delete("Salary Slip", {"employee": emp})
		slip = _insert({"doctype": "Salary Slip", "employee": emp, "company": COMPANY,
		                "start_date": START, "end_date": END, "posting_date": END,
		                "payroll_frequency": "Monthly", "currency": "INR"})
		draft = (slip.payment_days, slip.absent_days, slip.net_pay)
		self.assertEqual(whole - draft[0], 2)
		slip = frappe.get_doc("Salary Slip", slip.name)
		slip.flags.ignore_permissions = True
		slip.submit()
		after = frappe.db.get_value("Salary Slip", slip.name,
		                            ["payment_days", "absent_days", "net_pay", "docstatus"], as_dict=True)
		self.assertEqual(after.docstatus, 1)
		self.assertEqual((after.payment_days, after.absent_days, after.net_pay), draft)
		# The Salary Register reads these two columns of the submitted slip.
		self.assertEqual(frappe.db.get_value("Salary Slip", slip.name, "absent_days"), draft[1])


class ReleaseAndTheSlip(RealSlip):
	"""AC-16 and AC-18 on real slips: a release re-prices a DRAFT slip, and leaves a
	SUBMITTED one alone while HR is told to use Additional Salary."""

	def _hr(self):
		email = "hr%d.slip085@example.com" % RealSlip._slot
		u = frappe.get_doc({"doctype": "User", "email": email, "first_name": "HrSlip%d" % RealSlip._slot,
		                    "send_welcome_email": 0}).insert(ignore_permissions=True)
		u.add_roles("HR Manager")
		_insert({"doctype": "Employee", "first_name": "HrSlip%d" % RealSlip._slot, "last_name": "A085",
		         "company": COMPANY, "status": "Active", "user_id": email,
		         "gender": frappe.db.get_value("Gender", {}, "name") or "Male",
		         "date_of_birth": "1990-01-01", "date_of_joining": add_days(START, -200),
		         "create_user_permission": 0})
		return email

	def _held_day_and_request(self, emp):
		"""Day 2 is a Held day with one punch; a request carries 18:00 Out for it."""
		day = add_days(START, 2)
		self._present(emp, add_days(START, 1))
		att = self._present(emp, day)
		frappe.get_doc({"doctype": "Employee Checkin", "employee": emp, "log_type": "IN",
		                "time": "%s 10:00:00" % day}).insert(ignore_permissions=True)
		frappe.db.set_value("Attendance", att, "status", "Held")
		req = frappe.get_doc({"doctype": "Attendance Request", "employee": emp, "from_date": str(day),
		                      "to_date": str(day), "reason": "Forgot to Punch Out",
		                      "alvoraa_missing_time": "18:00:00", "alvoraa_missing_log": "OUT",
		                      "alvoraa_review_status": "Waiting"}).insert(ignore_permissions=True)
		return att, req.name

	def _approve(self, req, user):
		from alvoraa_portal import attendance_correction as ac
		from alvoraa_portal import punch_fix
		seen = punch_fix.seen_token(frappe.get_doc("Attendance Request", req))
		frappe.set_user(user)
		try:
			ac.decide(req, 1, None, seen)
		finally:
			frappe.set_user("Administrator")

	def test_ac16_a_release_re_prices_that_employees_draft_slip(self):
		frappe.db.set_single_value("Payroll Settings", "consider_unmarked_attendance_as", "Absent")
		emp = self._employee()
		att, req = self._held_day_and_request(emp)
		slip = _insert({"doctype": "Salary Slip", "employee": emp, "company": COMPANY,
		                "start_date": START, "end_date": END, "posting_date": END,
		                "payroll_frequency": "Monthly", "currency": "INR"})
		before = slip.payment_days
		self.assertEqual(frappe.db.get_value("Attendance", att, "status"), "Held")
		self._approve(req, self._hr())
		self.assertEqual(frappe.db.get_value("Attendance", att, "alvoraa_release_how"), "HR decision")
		self.assertEqual(frappe.db.get_value("Salary Slip", slip.name, "payment_days") - before, 1)

	def test_ac18_after_the_slip_is_submitted_nothing_changes_and_hr_is_told(self):
		from alvoraa_portal import attendance_correction as ac
		frappe.db.set_single_value("Payroll Settings", "consider_unmarked_attendance_as", "Absent")
		emp = self._employee()
		att, req = self._held_day_and_request(emp)
		slip = _insert({"doctype": "Salary Slip", "employee": emp, "company": COMPANY,
		                "start_date": START, "end_date": END, "posting_date": END,
		                "payroll_frequency": "Monthly", "currency": "INR"})
		before = slip.payment_days
		slip = frappe.get_doc("Salary Slip", slip.name)
		slip.flags.ignore_permissions = True
		slip.submit()  # a real submit, so validate runs (review B-1)
		self.assertEqual(frappe.db.get_value("Salary Slip", slip.name, "payment_days"), before)
		hr = self._hr()
		frappe.set_user(hr)
		try:
			from alvoraa_portal import punch_fix
			# Slice 087 (SEC-5, AC-33): a day on a final slip is refused at approval, in words, and
			# nothing is written. 085 released it and told HR; the intent that the submitted slip is
			# never touched (AC-18, Q4) holds, and the day is not released either.
			with self.assertRaises(frappe.ValidationError) as cm:
				ac.decide(req, approve=1, seen=punch_fix.seen_token(frappe.get_doc("Attendance Request", req)))
			self.assertIn("already final", str(cm.exception))
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Attendance", att, "status"), "Held")
		self.assertFalse(frappe.db.get_value("Attendance", att, "alvoraa_release_how"))
		self.assertEqual(frappe.db.get_value("Salary Slip", slip.name, "payment_days"), before)
