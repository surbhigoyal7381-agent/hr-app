"""Attendance in the appraisal score, on one employee and one two-week cycle.

Window 1 to 14 June 2026, Sundays 7 and 14 June are holidays: 12 scheduled days.
Attendance: 10 present (2 of them late), 1 absent, 1 loss-of-pay leave.
reliability = 1 - 2/12 = 83.33%, punctuality = 1 - 2/10 = 80%
base = 5 x (0.6 x 0.8333 + 0.4 x 0.8) = 4.10
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate

from hrms.alvoraa_hr_core.attendance_score import (
	attendance_numbers,
	build_formula,
	precompute,
	score_for,
)
from hrms.alvoraa_hr_core.setup import make_custom_fields

START, END = "2026-06-01", "2026-06-14"
HOLIDAYS = ("2026-06-07", "2026-06-14")


def _company():
	return frappe.get_all("Company", pluck="name", limit=1)[0]


def _ensure(doctype, name, **values):
	if name and frappe.db.exists(doctype, name):
		return frappe.get_doc(doctype, name)
	doc = frappe.get_doc({"doctype": doctype, **values})
	if name:
		doc.name = name
		doc.set("__newname", name)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_mandatory=True)
	return doc


class TestAttendanceScore(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_custom_fields()
		frappe.clear_cache()
		cls.company = _company()
		existing = frappe.db.get_value("Employee", {"first_name": "Score", "last_name": "Tester"}, "name")
		cls.employee = frappe.get_doc("Employee", existing) if existing else _ensure(
			"Employee", None, first_name="Score", last_name="Tester", gender="Female", date_of_birth="1995-01-01",
			date_of_joining="2026-01-01", company=cls.company, status="Active",
		)
		holiday_list = _ensure(
			"Holiday List", "Score Test Holidays", holiday_list_name="Score Test Holidays",
			from_date="2026-01-01", to_date="2026-12-31",
			holidays=[{"holiday_date": d, "description": "Sunday"} for d in HOLIDAYS],
		)
		if not frappe.db.exists("Holiday List Assignment", {"assigned_to": cls.employee.name, "docstatus": 1}):
			hla = frappe.get_doc({"doctype": "Holiday List Assignment", "applicable_for": "Employee",
			                      "assigned_to": cls.employee.name, "holiday_list": holiday_list.name,
			                      "from_date": "2026-01-01"})
			hla.insert(ignore_permissions=True)
			hla.submit()
		cls.lwp = _ensure("Leave Type", "Score Test LWP", leave_type_name="Score Test LWP", is_lwp=1)
		cls.paid = _ensure("Leave Type", "Score Test Paid Leave", leave_type_name="Score Test Paid Leave")
		cls.grade = _ensure("Employee Grade", "Score Test Exempt Grade")
		cls.cycle = _ensure(
			"Appraisal Cycle", "Attendance Score Test Cycle", cycle_name="Attendance Score Test Cycle",
			company=cls.company, start_date=START, end_date=END, kra_evaluation_method="Manual Rating",
			include_attendance_score=1, goal_weight=50, feedback_weight=30, attendance_weight=20,
			attendance_reliability_weight=60, attendance_punctuality_weight=40, attendance_deduction_penalty=0.25,
			attendance_when_no_data="Give full marks",
		)

	def setUp(self):
		super().setUp()
		for name in frappe.get_all("Appraisal", {"employee": self.employee.name}, pluck="name"):
			frappe.delete_doc("Appraisal", name, ignore_permissions=True, force=True)
		for name in frappe.get_all("Attendance", {"employee": self.employee.name, "docstatus": ["!=", 2]}, pluck="name"):
			doc = frappe.get_doc("Attendance", name)
			if doc.docstatus == 1:
				doc.flags.ignore_permissions = True
				doc.cancel()
			frappe.delete_doc("Attendance", name, ignore_permissions=True, force=True)
		frappe.db.set_value("Employee", self.employee.name, "grade", None)
		frappe.local.attendance_score_cache = {}

	def _attendance(self, date, status, late=0, leave_type=None):
		att = frappe.get_doc({"doctype": "Attendance", "employee": self.employee.name, "attendance_date": date,
		                      "status": status, "company": self.company, "late_entry": late, "leave_type": leave_type})
		att.flags.ignore_permissions = True
		att.insert()
		att.submit()

	def _two_weeks(self):
		day = getdate(START)
		absent, lwp, late = {"2026-06-03"}, {"2026-06-10"}, {"2026-06-02", "2026-06-09"}
		while day <= getdate(END):
			d = str(day)
			if d not in HOLIDAYS:
				if d in absent:
					self._attendance(d, "Absent")
				elif d in lwp:
					self._attendance(d, "On Leave", leave_type=self.lwp.name)
				else:
					self._attendance(d, "Present", late=1 if d in late else 0)
			day = add_days(day, 1)

	def _appraisal(self):
		ap = frappe.new_doc("Appraisal")
		ap.employee = self.employee.name
		ap.appraisal_cycle = self.cycle.name
		ap.company = self.company
		ap.start_date = START
		ap.end_date = END
		ap.rate_goals_manually = 1
		ap.flags.ignore_permissions = True
		ap.insert()
		return ap

	def test_cycle_writes_the_formula_from_its_weights(self):
		self.assertEqual(self.cycle.final_score_formula,
		                 "goal_score * 0.5 + average_feedback_score * 0.3 + attendance_score * 0.2")
		self.assertEqual(self.cycle.calculate_final_score_based_on_formula, 1)

	def test_weights_must_total_100(self):
		cycle = frappe.copy_doc(self.cycle)
		cycle.cycle_name = "Attendance Score Bad Weights"
		cycle.attendance_weight = 30
		self.assertRaises(frappe.ValidationError, cycle.insert)

	def test_formula_without_attendance(self):
		self.assertEqual(build_formula(frappe._dict(include_attendance_score=0, goal_weight=50, feedback_weight=30)),
		                 "goal_score")
		self.assertEqual(build_formula(frappe._dict(include_attendance_score=0, goal_weight=70, feedback_weight=30)),
		                 "goal_score * 0.7 + average_feedback_score * 0.3")

	def test_numbers(self):
		self._two_weeks()
		n = attendance_numbers(self.employee.name, START, END)
		self.assertEqual(n.scheduled_days, 12)
		self.assertEqual(n.present_days, 10)
		self.assertEqual(n.late_days, 2)
		self.assertEqual(n.absent_days, 1)
		self.assertEqual(n.lwp_days, 1)
		self.assertEqual(n.reliability_pct, 83.33)
		self.assertEqual(n.punctuality_pct, 80)

	def test_paid_leave_only_counts_when_the_cycle_says_so(self):
		self._attendance("2026-06-01", "On Leave", leave_type=self.paid.name)
		self._attendance("2026-06-02", "Present")
		self.assertEqual(attendance_numbers(self.employee.name, START, END).absent_days, 0)
		self.assertEqual(attendance_numbers(self.employee.name, START, END, True).absent_days, 1)

	def test_score_and_penalty(self):
		self._two_weeks()
		n = attendance_numbers(self.employee.name, START, END)
		score, summary = score_for(self.cycle, n)
		self.assertEqual(score, 4.1)
		self.assertIn("reliability 83.33%", summary)
		n.deduction_days = 0.5
		score, summary = score_for(self.cycle, n)
		self.assertAlmostEqual(score, 3.975, delta=0.01)   # 4.10 - 0.125
		self.assertIn("late-coming rule", summary)

	def test_appraisal_gets_the_snapshot_and_the_final_score_uses_it(self):
		self._two_weeks()
		ap = self._appraisal()
		self.assertEqual(ap.attendance_score, 4.1)
		self.assertEqual(ap.attendance_reliability_pct, 83.33)
		self.assertEqual(ap.attendance_punctuality_pct, 80)
		self.assertTrue(ap.attendance_summary)
		# goal and feedback scores are 0 here, so only the attendance term is left
		self.assertEqual(ap.final_score, 0.82)

	def test_exempt_grade_gets_full_marks(self):
		self._two_weeks()
		frappe.db.set_value("Employee", self.employee.name, "grade", self.grade.name)
		self.cycle.set("attendance_exempt_grades", [{"employee_grade": self.grade.name}])
		self.cycle.save(ignore_permissions=True)
		try:
			ap = self._appraisal()
			self.assertEqual(ap.attendance_score, 5)
			self.assertIn("Exempt", ap.attendance_summary)
		finally:
			self.cycle.set("attendance_exempt_grades", [])
			self.cycle.save(ignore_permissions=True)

	def test_no_data_follows_the_cycle_setting(self):
		ap = self._appraisal()
		self.assertEqual(ap.attendance_score, 5)
		self.assertIn("No attendance records", ap.attendance_summary)

	def test_precompute_is_used_by_the_hook(self):
		self._two_weeks()
		precompute(self.cycle, [self.employee.name])
		cache = frappe.local.attendance_score_cache
		self.assertIn((self.employee.name, START, END), cache)
		cache[(self.employee.name, START, END)].deduction_days = 2   # prove the hook reads the cache
		ap = self._appraisal()
		self.assertEqual(ap.attendance_deduction_days, 2)
		self.assertEqual(ap.attendance_score, 3.6)
