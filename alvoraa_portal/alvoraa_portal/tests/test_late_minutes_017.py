"""How late somebody was, and the money that follows from it.

Slice 017. The Time screen used to judge every day from the wrong time. Two
helpers cached different things under the same key in one dictionary - one
stored where a shift BEGINS, the other stored how LONG it lasts - so whichever
ran first won and the other read its answer. On PP Jewellers' 09:30-18:30 shift
the length is 540 minutes, so the screen judged the day from 09:00 and called
all 22,570 punched days late.

Every fixture here uses a shift whose start and length are DIFFERENT numbers.
That is the whole point. The older tests in `test_attendance_correction.py` use
a 09:00-18:00 shift, where the start (540) and the length (540) happen to be
equal, and that coincidence is why the bug shipped and stayed.

The deduction tests are here because this figure sits next to money. The
late-coming rule reads the shift start for itself and was never wrong, and
these tests exist to keep it that way: if anyone ever "tidies up" by feeding
the screen's figure into pay, the rupee amounts below stop matching.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, nowdate

from alvoraa_portal import attendance_correction as ac
from alvoraa_portal.attendance_analytics import _shift_minutes, _shift_row

# Start 09:30 = 570 minutes past midnight. Length = 540 minutes. The two must
# never be swappable, so they are deliberately different here.
SHIFT = "LM Test Shift 017"
NIGHT = "LM Night Shift 017"          # 22:00-06:00: start 1320, length 480
HOLIDAYS = "LM Test Holidays 017"


def setUpModule():
	ac.after_migrate()
	frappe.clear_cache(doctype=ac.REQUEST)


def _company():
	return frappe.db.get_value("Company", {}, "name")


def _shift(name, start, end):
	if not frappe.db.exists("Shift Type", name):
		frappe.get_doc({"doctype": "Shift Type", "name": name,
		                "start_time": start, "end_time": end}
		               ).insert(ignore_permissions=True)
	return name


def _holiday_list(company):
	if not frappe.db.exists("Holiday List", HOLIDAYS):
		frappe.get_doc({
			"doctype": "Holiday List", "holiday_list_name": HOLIDAYS,
			"from_date": add_days(nowdate(), -2000), "to_date": add_days(nowdate(), 400),
		}).insert(ignore_permissions=True)
	if not frappe.db.exists("Holiday List Assignment",
	                        {"assigned_to": company, "holiday_list": HOLIDAYS,
	                         "docstatus": 1}):
		frappe.get_doc({
			"doctype": "Holiday List Assignment", "holiday_list": HOLIDAYS,
			"applicable_for": "Company", "assigned_to": company,
			"from_date": add_days(nowdate(), -2000),
		}).insert(ignore_permissions=True).submit()
	return HOLIDAYS


class LateCase(FrappeTestCase):
	# A window per test, for the same reason the correction tests have one:
	# Frappe rolls the data back but not the naming counter, so two tests can be
	# handed the same employee id and one test's days land in another's month.
	_slot = 0

	def setUp(self):
		self.company = _company()
		self.caller = frappe.session.user
		frappe.set_user("Administrator")
		LateCase._slot += 1
		self.offset = 900 + LateCase._slot * 40
		_shift(SHIFT, "09:30:00", "18:30:00")
		_shift(NIGHT, "22:00:00", "06:00:00")
		self.holidays = _holiday_list(self.company)

	def tearDown(self):
		frappe.set_user(self.caller)

	def d(self, i=0):
		return add_days(nowdate(), -(self.offset + i))

	def ym(self, i=0):
		day = getdate(self.d(i))
		return day.year, day.month

	def person(self, first, shift=SHIFT):
		email = "%s.lm017@example.com" % first.lower()
		if not frappe.db.exists("User", email):
			frappe.get_doc({"doctype": "User", "email": email, "first_name": first,
			                "send_welcome_email": 0}).insert(ignore_permissions=True)
		e = frappe.get_doc({
			"doctype": "Employee", "first_name": first, "company": self.company,
			"date_of_birth": "1990-01-01", "date_of_joining": "2015-01-01",
			"gender": frappe.db.get_value("Gender", {}, "name") or "Male",
			"status": "Active", "default_shift": shift, "user_id": email,
			"holiday_list": self.holidays,
		}).insert(ignore_permissions=True)
		frappe.get_doc({
			"doctype": "Shift Assignment", "employee": e.name, "shift_type": shift,
			"company": self.company, "start_date": add_days(nowdate(), -2000),
			"end_date": add_days(nowdate(), 400),
		}).insert(ignore_permissions=True).submit()
		return e.name, email

	def day(self, employee, date, hours, shift=SHIFT, status="Present",
	        in_time=None, out_time=None):
		a = frappe.get_doc({
			"doctype": "Attendance", "employee": employee, "attendance_date": date,
			"status": status, "working_hours": hours, "shift": shift,
			"in_time": in_time, "out_time": out_time,
			"company": self.company}).insert(ignore_permissions=True)
		a.submit()
		return a.name

	def my_day(self, email, i):
		y, m = self.ym(i)
		return [d for d in ac.month(y, m)["days"] if d["date"] == self.d(i)][0]


class WhereTheDayIsJudgedFrom(LateCase):
	"""The arithmetic, at the level where it broke."""

	def test_the_two_helpers_do_not_read_each_others_answers(self):
		"""The defect itself, in three lines.

		Both helpers take the same cache. Before the fix, asking for the length
		first poisoned the start, because the length was sitting under the key
		the start was about to use. Either order must now give both answers.
		"""
		for order in ("length first", "start first"):
			cache = {}
			if order == "length first":
				length = _shift_minutes(cache, SHIFT)
				start = ac._shift_start(cache, SHIFT)
			else:
				start = ac._shift_start(cache, SHIFT)
				length = _shift_minutes(cache, SHIFT)
			self.assertEqual(start, 570.0,
			                 "%s: a 09:30 shift must begin at 570 minutes past "
			                 "midnight, not %s" % (order, start))
			self.assertEqual(length, 540.0, "%s: nine hours is 540 minutes" % order)

	def test_the_cache_holds_the_row_not_a_derived_number(self):
		"""Why the fix is safe rather than lucky. One fact in, each helper does
		its own sum. Nothing derived is ever stored under the shift's name."""
		cache = {}
		_shift_minutes(cache, SHIFT)
		self.assertEqual(list(cache), [SHIFT])
		self.assertEqual(cache[SHIFT].start_time.total_seconds() / 60.0, 570.0)

	def test_a_shift_that_does_not_exist_is_not_late(self):
		"""Fail safe. No shift means no expectation, so no accusation."""
		cache = {}
		self.assertIsNone(ac._shift_start(cache, "LM No Such Shift 017"))
		self.assertIsNone(_shift_minutes(cache, "LM No Such Shift 017"))


class WhatTheEmployeeIsTold(LateCase):
	def test_late_is_counted_from_the_shift_start_not_its_length(self):
		"""The reported bug. 09:47 on a 09:30 shift is 17 minutes late.

		Before the fix this said 47, because the day was judged from 09:00.
		"""
		p, email = self.person("LMLate")
		self.day(p, self.d(3), 8.0, in_time=self.d(3) + " 09:47:00")
		frappe.set_user(email)
		self.assertEqual(self.my_day(email, 3)["late_by_mins"], 17)

	def test_arriving_before_the_shift_starts_is_not_late_at_all(self):
		"""The worst of it. 09:10 is twenty minutes EARLY, and the screen used
		to call it ten minutes late - on every employee, on every punched day."""
		p, email = self.person("LMEarly")
		self.day(p, self.d(3), 9.0, in_time=self.d(3) + " 09:10:00")
		frappe.set_user(email)
		self.assertEqual(self.my_day(email, 3)["late_by_mins"], 0)

	def test_the_month_does_not_count_an_early_arrival_as_a_late_day(self):
		"""The total under the calendar is what people argue about."""
		p, email = self.person("LMTotals")
		self.day(p, self.d(3), 9.0, in_time=self.d(3) + " 09:15:00")
		self.day(p, self.d(4), 9.0, in_time=self.d(4) + " 09:20:00")
		frappe.set_user(email)
		y, m = self.ym(3)
		self.assertEqual(ac.month(y, m)["totals"]["late_days"], 0)

	def test_the_strip_shows_the_shift_the_employee_actually_works(self):
		"""The drawn day was 09:00-18:00 on a 09:30-18:30 shift, so the bar and
		the punch times disagreed on screen."""
		p, email = self.person("LMStrip")
		self.day(p, self.d(3), 9.0, in_time=self.d(3) + " 09:31:00")
		frappe.set_user(email)
		day = self.my_day(email, 3)
		self.assertEqual(day["shift_starts"], "09:30")
		self.assertEqual(day["shift_ends"], "18:30")

	def test_a_night_shift_is_judged_from_when_it_begins(self):
		"""A 22:00 shift has a length of 480 minutes, which reads as 08:00.
		Clocking in at 22:05 was reported as fourteen hours late."""
		p, email = self.person("LMNight", shift=NIGHT)
		self.day(p, self.d(3), 8.0, shift=NIGHT, in_time=self.d(3) + " 22:05:00")
		frappe.set_user(email)
		day = self.my_day(email, 3)
		self.assertEqual(day["late_by_mins"], 5)
		self.assertEqual(day["shift_starts"], "22:00")
		self.assertEqual(day["shift_ends"], "06:00")


class TheMoneyThatFollows(FrappeTestCase):
	"""The late-coming rule, pinned to the true shift start.

	These are not proof of the bug - the rule reads the shift start for itself
	and has always been right. They are here so that it stays right. The
	arrivals below are chosen to tell the two readings apart: 10:15 is 45
	minutes past 09:30 and costs nothing, but it is 75 minutes past 09:00 and
	would cost a quarter day if anybody ever fed the screen's figure into pay.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = _company()
		_shift(SHIFT, "09:30:00", "18:30:00")
		cls.holidays = _holiday_list(cls.company)
		if not frappe.db.exists("Salary Component", "LM LWP 017"):
			frappe.get_doc({"doctype": "Salary Component", "salary_component": "LM LWP 017",
			                "salary_component_abbr": "LMLWP017", "type": "Deduction"}
			               ).insert(ignore_permissions=True)
		# Leave is NOT consumed first, so the whole deduction lands in pay and
		# the test can assert an exact rupee amount.
		if not frappe.db.exists("Attendance Deduction Rule", "LM Rule 017"):
			doc = frappe.get_doc({
				"doctype": "Attendance Deduction Rule", "rule_name": "LM Rule 017",
				"company": cls.company, "shift_type": SHIFT, "enabled": 1,
				"week_start_day": "Monday", "late_threshold_minutes": 60,
				"count_early_exit": 0, "early_exit_threshold_minutes": 0,
				"free_violations_per_week": 1, "deduction_per_violation_days": 0.25,
				"round_up_from_days": 0.75, "round_up_to_days": 1.0,
				"deduct_from_leave_first": 0, "lwp_salary_component": "LM LWP 017",
				"notify_employee": 0, "notify_manager": 0,
			})
			doc.name = "LM Rule 017"
			doc.set("__newname", "LM Rule 017")
			doc.insert(ignore_permissions=True)
		cls.rule = frappe.get_doc("Attendance Deduction Rule", "LM Rule 017")

	def setUp(self):
		self.caller = frappe.session.user
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user(self.caller)

	def _employee(self, first):
		e = frappe.get_doc({
			"doctype": "Employee", "first_name": first, "company": self.company,
			"date_of_birth": "1990-01-01", "date_of_joining": "2015-01-01",
			"gender": frappe.db.get_value("Gender", {}, "name") or "Male",
			"status": "Active", "default_shift": SHIFT, "holiday_list": self.holidays,
		}).insert(ignore_permissions=True)
		frappe.get_doc({
			"doctype": "Shift Assignment", "employee": e.name, "shift_type": SHIFT,
			"company": self.company, "start_date": "2015-01-01",
		}).insert(ignore_permissions=True).submit()
		# 31,000 over a 31-day month is 1,000 a day, so the arithmetic below is
		# readable rather than a rounded guess.
		if not frappe.db.exists("Salary Structure", "LM Structure 017"):
			basic = frappe.db.exists("Salary Component", "LM Basic 017") or frappe.get_doc(
				{"doctype": "Salary Component", "salary_component": "LM Basic 017",
				 "salary_component_abbr": "LMB017", "type": "Earning"}
			).insert(ignore_permissions=True).name
			ss = frappe.get_doc({
				"doctype": "Salary Structure", "name": "LM Structure 017",
				"__newname": "LM Structure 017", "company": self.company,
				"currency": "INR", "payroll_frequency": "Monthly", "is_active": "Yes",
				"earnings": [{"salary_component": basic, "abbr": "LMB017", "amount": 31000}],
			})
			ss.insert(ignore_permissions=True)
			ss.submit()
		ssa = frappe.get_doc({
			"doctype": "Salary Structure Assignment", "employee": e.name,
			"salary_structure": "LM Structure 017", "company": self.company,
			"currency": "INR", "from_date": "2015-01-01", "base": 31000,
		})
		ssa.flags.ignore_permissions = True
		ssa.insert()
		ssa.submit()
		return e.name

	def _day(self, employee, date, in_time, out_time="18:35:00"):
		a = frappe.get_doc({
			"doctype": "Attendance", "employee": employee, "attendance_date": date,
			"status": "Present", "shift": SHIFT, "company": self.company,
			"in_time": "%s %s" % (date, in_time), "out_time": "%s %s" % (date, out_time),
		})
		a.flags.ignore_permissions = True
		a.insert()
		a.submit()

	def test_the_rule_measures_lateness_from_the_shift_start(self):
		"""45 minutes past 09:30 is not a violation. 75 minutes past 09:00 would
		be. The rule must read 09:30."""
		from hrms.alvoraa_late_rules.late_rules import violations_for

		emp = self._employee("LMRuleStart")
		for day in ("2026-08-17", "2026-08-18", "2026-08-19"):
			self._day(emp, day, "10:15:00")
		found = violations_for(self.rule, emp, getdate("2026-08-17"), getdate("2026-08-23"))
		self.assertEqual(found, [], "arriving at 10:15 on a 09:30 shift is 45 "
		                           "minutes late and the threshold is 60")

	def test_no_deduction_and_no_rupee_leaves_pay_for_a_45_minute_arrival(self):
		"""The figure next to the money. Judged from 09:00 this week would have
		cost half a day; judged from 09:30 it costs nothing."""
		from hrms.alvoraa_late_rules.late_rules import process_week

		emp = self._employee("LMRuleNoPay")
		for day in ("2026-08-17", "2026-08-18", "2026-08-19"):
			self._day(emp, day, "10:15:00")
		result = process_week(self.rule, "2026-08-17", commit=False)
		self.assertEqual(result["created"], 0)
		self.assertFalse(frappe.db.exists("Attendance Deduction",
		                                  {"employee": emp, "week_start": "2026-08-17"}))
		self.assertFalse(frappe.db.exists("Additional Salary", {"employee": emp}))

	def test_a_real_late_week_costs_the_exact_amount_it_should(self):
		"""The other side of the same coin: when lateness is real, the money is
		right. Three arrivals 75 minutes past 09:30, first one free, two counted
		at a quarter day = 0.5 day. 31,000 over 31 days is 1,000 a day, so 500.
		"""
		from hrms.alvoraa_late_rules.late_rules import process_week

		emp = self._employee("LMRulePays")
		for day in ("2026-08-17", "2026-08-18", "2026-08-19"):
			self._day(emp, day, "10:45:00")
		process_week(self.rule, "2026-08-17", commit=False)
		ded = frappe.get_doc("Attendance Deduction",
		                     {"employee": emp, "week_start": "2026-08-17"})
		self.assertEqual(ded.total_violations, 3)
		self.assertEqual(ded.counted_violations, 2)
		self.assertEqual(ded.deduction_days, 0.5)
		self.assertEqual(ded.lwp_days, 0.5)
		self.assertEqual(ded.lwp_amount, 500.0)
		extra = frappe.get_doc("Additional Salary", ded.additional_salary)
		self.assertEqual(extra.amount, 500.0)
		# Every violation is stored with the minutes it was judged by, so an
		# employee asking "why" gets the same number twice.
		self.assertEqual(sorted({v.minutes for v in ded.violations}), [75])
