"""The quarter-day late-coming rule, end to end on one employee.

Week of Monday 2026-08-17: late Tue and Thu (more than an hour), early exit Sat.
Rule: first violation free, 0.25 day per counted violation, 0.75 rounds to 1.0.
Expected: 3 violations, 2 counted, 0.5 day, taken from Casual Leave.
Then a 4-violation week with only 0.5 day of leave left: 0.5 from leave, 0.5 loss of pay.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate

from hrms.alvoraa_late_rules.late_rules import current_week_projection, process_week, violations_for, week_start_for

COMPANY_FILTER = {}


def _company():
	return frappe.get_all("Company", pluck="name", limit=1)[0]


def _ensure(doctype, name, **values):
	if name and frappe.db.exists(doctype, name):
		return frappe.get_doc(doctype, name)
	doc = frappe.get_doc({"doctype": doctype, **values})
	if name:
		doc.name = name                 # Prompt-named doctypes (Shift Type, Employee Grade) need it
		doc.set("__newname", name)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_mandatory=True)
	return doc


class TestLateRules(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = _company()
		cls.shift = _ensure("Shift Type", "Late Rule Test Shift", shift_type="Late Rule Test Shift",
		                    start_time="09:30:00", end_time="18:30:00")
		cls.component = _ensure("Salary Component", "Late Coming Deduction Test", salary_component="Late Coming Deduction Test",
		                        salary_component_abbr="LCDT", type="Deduction")
		for lt in ("Casual Leave", "Earned Leave"):
			_ensure("Leave Type", lt, leave_type_name=lt)
		existing = frappe.db.get_value("Employee", {"first_name": "Late", "last_name": "Tester"}, "name")
		cls.employee = frappe.get_doc("Employee", existing) if existing else _ensure(
			"Employee", None, first_name="Late", last_name="Tester", gender="Female", date_of_birth="1995-01-01",
			date_of_joining="2026-01-01", company=cls.company, status="Active", default_shift=cls.shift.name,
		)
		holiday_list = _ensure("Holiday List", "Late Rule Test Holidays", holiday_list_name="Late Rule Test Holidays",
		                       from_date="2026-01-01", to_date="2026-12-31")
		frappe.db.set_value("Employee", cls.employee.name, "holiday_list", holiday_list.name)
		if frappe.db.exists("DocType", "Holiday List Assignment") and not frappe.db.exists(
			"Holiday List Assignment", {"assigned_to": cls.employee.name, "docstatus": 1}
		):
			hla = frappe.get_doc({"doctype": "Holiday List Assignment", "applicable_for": "Employee",
			                      "assigned_to": cls.employee.name, "holiday_list": holiday_list.name,
			                      "from_date": "2026-01-01"})
			hla.insert(ignore_permissions=True)
			hla.submit()
		# 1 day of Casual Leave for the whole year
		if not frappe.db.exists("Leave Allocation", {"employee": cls.employee.name, "leave_type": "Casual Leave", "docstatus": 1}):
			alloc = frappe.get_doc({"doctype": "Leave Allocation", "employee": cls.employee.name, "leave_type": "Casual Leave",
			                        "from_date": "2026-01-01", "to_date": "2026-12-31", "new_leaves_allocated": 1,
			                        "company": cls.company})
			alloc.insert(ignore_permissions=True)
			alloc.submit()
		if not frappe.db.exists("Salary Structure", "Late Rule Test Structure"):
			ss = frappe.get_doc({"doctype": "Salary Structure", "name": "Late Rule Test Structure",
			                     "__newname": "Late Rule Test Structure", "company": cls.company, "currency": "INR",
			                     "payroll_frequency": "Monthly", "is_active": "Yes",
			                     "earnings": [{"salary_component": _ensure("Salary Component", "Basic Test", salary_component="Basic Test",
			                                                                 salary_component_abbr="BT", type="Earning").name,
			                                   "abbr": "BT", "amount": 31000}]})
			ss.insert(ignore_permissions=True)
			ss.submit()
		if not frappe.db.exists("Salary Structure Assignment", {"employee": cls.employee.name, "docstatus": 1}):
			ssa = frappe.get_doc({"doctype": "Salary Structure Assignment", "employee": cls.employee.name,
			                      "salary_structure": "Late Rule Test Structure", "company": cls.company,
			                      "currency": "INR", "from_date": "2026-01-01", "base": 31000})
			ssa.flags.ignore_permissions = True
			ssa.insert()
			ssa.submit()
		cls.rule = _ensure(
			"Attendance Deduction Rule", "Late Rule Test", rule_name="Late Rule Test", company=cls.company,
			shift_type=cls.shift.name, enabled=1, week_start_day="Monday", late_threshold_minutes=60,
			count_early_exit=1, early_exit_threshold_minutes=60, free_violations_per_week=1,
			deduction_per_violation_days=0.25, round_up_from_days=0.75, round_up_to_days=1.0,
			deduct_from_leave_first=1, leave_types=[{"leave_type": "Casual Leave", "priority": 1}],
			lwp_salary_component=cls.component.name, notify_employee=0, notify_manager=0,
		)
		if not frappe.db.exists("Shift Assignment", {"employee": cls.employee.name, "docstatus": 1}):
			sa = frappe.get_doc({"doctype": "Shift Assignment", "employee": cls.employee.name, "shift_type": cls.shift.name,
			                     "company": cls.company, "start_date": "2026-01-01", "status": "Active"})
			sa.insert(ignore_permissions=True)
			sa.submit()

	@classmethod
	def _clean_slate(cls):
		"""Whatever an earlier test or run left behind for this employee goes, so
		every test starts from one day of Casual Leave and no attendance, in any order."""
		emp = cls.employee.name
		for name in frappe.get_all("Attendance Deduction", {"employee": emp, "docstatus": ["!=", 2]}, pluck="name"):
			doc = frappe.get_doc("Attendance Deduction", name)
			if doc.docstatus == 1:
				doc.flags.ignore_permissions = True
				doc.cancel()
		for doctype, filters in (
			("Attendance Deduction", {"employee": emp}),
			("Additional Salary", {"employee": emp, "docstatus": ["!=", 1]}),
			("Leave Ledger Entry", {"employee": emp, "transaction_type": "Attendance Deduction"}),
		):
			for name in frappe.get_all(doctype, filters, pluck="name"):
				frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
		for name in frappe.get_all("Attendance", {"employee": emp, "docstatus": ["!=", 2]}, pluck="name"):
			doc = frappe.get_doc("Attendance", name)
			if doc.docstatus == 1:
				doc.flags.ignore_permissions = True
				doc.cancel()
			frappe.delete_doc("Attendance", name, ignore_permissions=True, force=True)

	def setUp(self):
		super().setUp()
		self._clean_slate()

	def _attendance(self, date, in_time, out_time):
		if frappe.db.exists("Attendance", {"employee": self.employee.name, "attendance_date": date, "docstatus": 1}):
			return
		att = frappe.get_doc({"doctype": "Attendance", "employee": self.employee.name, "attendance_date": date,
		                      "status": "Present", "shift": self.shift.name, "company": self.company,
		                      "in_time": f"{date} {in_time}", "out_time": f"{date} {out_time}"})
		att.flags.ignore_permissions = True
		att.insert()
		att.submit()

	def test_week_start(self):
		self.assertEqual(str(week_start_for("2026-08-20", "Monday")), "2026-08-17")
		self.assertEqual(str(week_start_for("2026-08-17", "Monday")), "2026-08-17")
		self.assertEqual(str(week_start_for("2026-08-16", "Monday")), "2026-08-10")
		self.assertEqual(str(week_start_for("2026-08-20", "Sunday")), "2026-08-16")

	def test_three_violations_take_half_a_day_from_leave(self):
		self._attendance("2026-08-17", "09:35:00", "18:40:00")   # fine
		self._attendance("2026-08-18", "10:47:00", "18:35:00")   # late, free
		self._attendance("2026-08-19", "09:20:00", "18:31:00")
		self._attendance("2026-08-20", "10:52:00", "18:45:00")   # late
		self._attendance("2026-08-22", "09:28:00", "17:05:00")   # early exit
		v = violations_for(self.rule, self.employee.name, getdate("2026-08-17"), getdate("2026-08-23"))
		self.assertEqual([x["violation_type"] for x in v], ["Late Arrival", "Late Arrival", "Early Exit"])

		result = process_week(self.rule, "2026-08-17", commit=False)
		self.assertEqual(result["created"], 1)
		ded = frappe.get_doc("Attendance Deduction", {"employee": self.employee.name, "week_start": "2026-08-17"})
		self.assertEqual(ded.docstatus, 1)
		self.assertEqual(ded.total_violations, 3)
		self.assertEqual(ded.counted_violations, 2)
		self.assertEqual(ded.deduction_days, 0.5)
		self.assertEqual(len(ded.leave_deductions), 1)
		self.assertEqual(ded.leave_deductions[0].days, 0.5)
		self.assertEqual(ded.lwp_days, 0)
		self.assertFalse(ded.additional_salary)
		ledger = frappe.db.get_value("Leave Ledger Entry", {"transaction_type": "Attendance Deduction",
		                                                    "transaction_name": ded.name}, "leaves")
		self.assertEqual(ledger, -0.5)
		# running the same week again changes nothing
		again = process_week(self.rule, "2026-08-17", commit=False)
		self.assertEqual(again["created"], 0)
		self.assertEqual(again["existing"], 1)

	def test_four_violations_round_up_and_spill_into_pay(self):
		self.test_three_violations_take_half_a_day_from_leave()      # leaves 0.5 day of Casual Leave
		self._attendance("2026-08-24", "10:40:00", "18:34:00")
		self._attendance("2026-08-25", "10:35:00", "18:40:00")
		self._attendance("2026-08-26", "09:30:00", "17:10:00")
		self._attendance("2026-08-28", "11:00:00", "19:04:00")
		process_week(self.rule, "2026-08-24", commit=False)
		ded = frappe.get_doc("Attendance Deduction", {"employee": self.employee.name, "week_start": "2026-08-24"})
		self.assertEqual(ded.total_violations, 4)
		self.assertEqual(ded.computed_days, 0.75)
		self.assertEqual(ded.deduction_days, 1.0)
		self.assertEqual(ded.leave_deductions[0].days, 0.5)
		self.assertEqual(ded.lwp_days, 0.5)
		self.assertTrue(ded.additional_salary)
		extra = frappe.get_doc("Additional Salary", ded.additional_salary)
		self.assertEqual(extra.docstatus, 1)
		self.assertEqual(extra.amount, 500)             # 31,000 / 31 days × 0.5
		self.assertEqual(str(extra.payroll_date), "2026-08-30")
		# cancel puts the leave and the pay back
		ded.cancel()
		self.assertFalse(frappe.db.exists("Leave Ledger Entry", {"transaction_name": ded.name}))
		self.assertEqual(frappe.db.get_value("Additional Salary", extra.name, "docstatus"), 2)

	def test_projection_for_the_portal(self):
		self._attendance("2026-08-31", "10:45:00", "18:40:00")
		p = current_week_projection(self.rule, self.employee.name, as_on="2026-09-02")
		self.assertEqual(p["week_start"], "2026-08-31")
		self.assertEqual(len(p["violations"]), 1)
		self.assertEqual(p["counted"], 0)
		self.assertEqual(p["projected_days"], 0)

	def test_exempt_grade_is_skipped(self):
		grade = _ensure("Employee Grade", "Late Rule Exempt Grade")
		frappe.db.set_value("Employee", self.employee.name, "grade", grade.name)
		self.rule.append("exempt_grades", {"employee_grade": grade.name})
		self.rule.save(ignore_permissions=True)
		try:
			self._attendance("2026-09-07", "11:00:00", "18:40:00")
			self._attendance("2026-09-08", "11:00:00", "18:40:00")
			result = process_week(self.rule, "2026-09-07", commit=False)
			self.assertEqual(result["created"], 0)
		finally:
			self.rule.set("exempt_grades", [])
			self.rule.save(ignore_permissions=True)
			frappe.db.set_value("Employee", self.employee.name, "grade", None)
