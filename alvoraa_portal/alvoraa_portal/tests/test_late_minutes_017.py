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

from alvoraa_portal import attendance_analytics as aa
from alvoraa_portal import attendance_correction as ac
from alvoraa_portal import hr_api
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


class _MoneyBase(FrappeTestCase):
	"""Shared fixture for the tests that move pay. Holds no tests of its own.

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

	def _day(self, employee, date, in_time, out_time="18:35:00", shift=SHIFT):
		a = frappe.get_doc({
			"doctype": "Attendance", "employee": employee, "attendance_date": date,
			"status": "Present", "shift": shift, "company": self.company,
			"in_time": "%s %s" % (date, in_time), "out_time": "%s %s" % (date, out_time),
		})
		a.flags.ignore_permissions = True
		a.insert()
		a.submit()

	def _day_span(self, employee, date, in_time, out_date, out_time,
	              shift=SHIFT, in_at=None):
		"""A day whose clock-out (or clock-in) falls on a different date.

		Frappe stores both as full datetimes, which is what makes the shift
		window comparable at all. These tests exist because the old code threw
		the dates away and compared times of day.
		"""
		in_stamp = None
		if in_at:
			in_stamp = "%s %s" % in_at
		elif in_time:
			in_stamp = "%s %s" % (date, in_time)
		a = frappe.get_doc({
			"doctype": "Attendance", "employee": employee, "attendance_date": date,
			"status": "Present", "shift": shift, "company": self.company,
			"in_time": in_stamp, "out_time": "%s %s" % (out_date, out_time),
		})
		a.flags.ignore_permissions = True
		a.insert()
		a.submit()


class TheMoneyThatFollows(_MoneyBase):
	"""The late-coming rule, pinned to the true shift start."""

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


class TheGracePeriod(LateCase):
	"""Grace is the organisation's decision, and it is configurable.

	Resolution order, and each step of it pinned: the shift's own
	`late_entry_grace_period` when it is set, then the organisation's default,
	then nothing.
	"""

	def tearDown(self):
		frappe.db.set_default(aa.LATE_GRACE_KEY, "")
		frappe.db.set_value("Shift Type", SHIFT, "late_entry_grace_period", 0)
		super().tearDown()

	def test_the_shifts_own_grace_wins_when_it_is_set(self):
		frappe.db.set_default(aa.LATE_GRACE_KEY, "30")
		frappe.db.set_value("Shift Type", SHIFT, "late_entry_grace_period", 15)
		self.assertEqual(aa._shift_grace({}, SHIFT), 15)

	def test_the_organisation_grace_applies_when_the_shift_has_none(self):
		frappe.db.set_default(aa.LATE_GRACE_KEY, "20")
		frappe.db.set_value("Shift Type", SHIFT, "late_entry_grace_period", 0)
		self.assertEqual(aa._shift_grace({}, SHIFT), 20)

	def test_no_grace_anywhere_means_no_grace(self):
		frappe.db.set_default(aa.LATE_GRACE_KEY, "")
		frappe.db.set_value("Shift Type", SHIFT, "late_entry_grace_period", 0)
		self.assertEqual(aa._shift_grace({}, SHIFT), 0)

	def test_a_day_inside_the_grace_shows_the_minutes_but_is_not_marked_late(self):
		"""Both halves of the decision in one test. The employee still sees
		exactly how late they were; the day does not count against them."""
		frappe.db.set_default(aa.LATE_GRACE_KEY, "15")
		p, email = self.person("LMInGrace")
		self.day(p, self.d(3), 9.0, in_time=self.d(3) + " 09:40:00")
		frappe.set_user(email)
		day = self.my_day(email, 3)
		self.assertEqual(day["late_by_mins"], 10)
		self.assertEqual(day["grace_mins"], 15)
		self.assertFalse(day["is_late"])

	def test_a_day_past_the_grace_is_marked_late(self):
		frappe.db.set_default(aa.LATE_GRACE_KEY, "15")
		p, email = self.person("LMPastGrace")
		self.day(p, self.d(3), 9.0, in_time=self.d(3) + " 09:50:00")
		frappe.set_user(email)
		day = self.my_day(email, 3)
		self.assertEqual(day["late_by_mins"], 20)
		self.assertTrue(day["is_late"])

	def test_arriving_exactly_on_the_grace_is_forgiven(self):
		"""Fifteen minutes' grace forgives the fifteenth minute. Anything else
		makes a liar of the words on the screen."""
		frappe.db.set_default(aa.LATE_GRACE_KEY, "15")
		p, email = self.person("LMOnGrace")
		self.day(p, self.d(3), 9.0, in_time=self.d(3) + " 09:45:00")
		frappe.set_user(email)
		self.assertFalse(self.my_day(email, 3)["is_late"])

	def test_the_month_total_counts_only_the_days_past_the_grace(self):
		"""The number that has to agree with the deduction card beside it."""
		frappe.db.set_default(aa.LATE_GRACE_KEY, "15")
		p, email = self.person("LMGraceTotals")
		self.day(p, self.d(3), 9.0, in_time=self.d(3) + " 09:40:00")   # 10 late, forgiven
		self.day(p, self.d(4), 9.0, in_time=self.d(4) + " 10:05:00")   # 35 late, counted
		frappe.set_user(email)
		y, m = self.ym(3)
		month = ac.month(y, m)
		self.assertEqual(month["totals"]["late_days"], 1)
		self.assertEqual(month["late_grace_mins"], 15)


class ConfiguringTheGracePeriod(FrappeTestCase):
	"""HR sets the number, and nothing else can be smuggled through the call."""

	def setUp(self):
		self.caller = frappe.session.user
		frappe.set_user("Administrator")
		email = "hrgrace.lm017@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc({"doctype": "User", "email": email, "first_name": "HRGrace",
			                "send_welcome_email": 0}).insert(ignore_permissions=True)
		frappe.get_doc("User", email).add_roles("HR Manager")
		self.hr = email

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.set_default(aa.LATE_GRACE_KEY, "")
		frappe.set_user(self.caller)

	def test_hr_can_set_and_read_the_grace_period(self):
		frappe.set_user(self.hr)
		self.assertEqual(hr_api.set_org_setting(aa.LATE_GRACE_KEY, "15"), {"ok": True})
		self.assertEqual(hr_api.get_org_setting(aa.LATE_GRACE_KEY), "15")
		self.assertEqual(aa.org_late_grace(), 15)

	def test_zero_is_a_real_answer_and_saves(self):
		"""Turning grace off is a decision, not a missing value."""
		frappe.set_user(self.hr)
		hr_api.set_org_setting(aa.LATE_GRACE_KEY, "0")
		self.assertEqual(aa.org_late_grace(), 0)

	def test_anything_that_is_not_whole_minutes_in_range_is_refused(self):
		"""Refused, not quietly clamped. A threshold that silently became
		something else is worse than an error nobody can miss."""
		frappe.set_user(self.hr)
		hr_api.set_org_setting(aa.LATE_GRACE_KEY, "10")
		for bad in ("15.5", "abc", "-5", " 15", "15 ", "999", "", "1e2", "٥"):
			with self.subTest(bad=bad), self.assertRaises(frappe.PermissionError):
				hr_api.set_org_setting(aa.LATE_GRACE_KEY, bad)
		# and the good value is still there, untouched by the refusals
		self.assertEqual(aa.org_late_grace(), 10)

	def test_the_yes_no_setting_is_still_validated_as_a_yes_no(self):
		"""Adding a numeric key must not have loosened the existing one."""
		frappe.set_user(self.hr)
		with self.assertRaises(frappe.PermissionError):
			hr_api.set_org_setting("kra_link_mandatory", "2")
		self.assertEqual(hr_api.set_org_setting("kra_link_mandatory", "1"), {"ok": True})
		frappe.db.set_default("kra_link_mandatory", "0")


class MidnightAndTheMoney(_MoneyBase):
	"""Punches either side of midnight, on the path that moves pay.

	Comparing times of day wrapped at midnight, and the wrap cost real money in
	both directions: it invented early exits for people who worked late, and it
	hid late arrivals on night shifts.
	"""

	def _early_exit_on(self):
		"""The rule counts early exits for these tests only."""
		frappe.db.set_value("Attendance Deduction Rule", "LM Rule 017",
		                    {"count_early_exit": 1, "early_exit_threshold_minutes": 60})
		frappe.clear_document_cache("Attendance Deduction Rule", "LM Rule 017")
		self.rule = frappe.get_doc("Attendance Deduction Rule", "LM Rule 017")

	def tearDown(self):
		frappe.db.set_value("Attendance Deduction Rule", "LM Rule 017",
		                    {"count_early_exit": 0, "early_exit_threshold_minutes": 0})
		frappe.clear_document_cache("Attendance Deduction Rule", "LM Rule 017")
		super().tearDown()

	def test_working_past_midnight_is_not_an_early_exit_and_costs_nothing(self):
		"""The live bug. Clocking out at 00:30 after an 18:30 shift is four
		hours of extra work. It read as 1,080 minutes EARLY, three times over,
		and took half a day's pay."""
		from hrms.alvoraa_late_rules.late_rules import process_week, violations_for

		emp = self._employee("LMPastMidnight")
		for day, nxt in (("2026-08-17", "2026-08-18"), ("2026-08-18", "2026-08-19"),
		                 ("2026-08-19", "2026-08-20")):
			self._day_span(emp, day, "09:35:00", nxt, "00:30:00")
		self._early_exit_on()
		self.assertEqual(
			violations_for(self.rule, emp, getdate("2026-08-17"), getdate("2026-08-23")), [])
		self.assertEqual(process_week(self.rule, "2026-08-17", commit=False)["created"], 0)
		self.assertFalse(frappe.db.exists("Additional Salary", {"employee": emp}))

	def test_a_real_early_exit_still_costs_the_exact_amount(self):
		"""The other direction. Leaving at 17:00 from an 18:30 shift is 90
		minutes early, three times, first free, two counted = 0.5 day = 500."""
		from hrms.alvoraa_late_rules.late_rules import process_week

		emp = self._employee("LMRealEarly")
		for day in ("2026-08-17", "2026-08-18", "2026-08-19"):
			self._day(emp, day, "09:35:00", out_time="17:00:00")
		self._early_exit_on()
		process_week(self.rule, "2026-08-17", commit=False)
		ded = frappe.get_doc("Attendance Deduction",
		                     {"employee": emp, "week_start": "2026-08-17"})
		self.assertEqual([v.violation_type for v in ded.violations],
		                 ["Early Exit"] * 3)
		self.assertEqual(ded.deduction_days, 0.5)
		self.assertEqual(ded.lwp_amount, 500.0)
		self.assertEqual(sorted({v.minutes for v in ded.violations}), [90])

	def test_a_night_shift_arrival_after_midnight_is_counted(self):
		"""The hidden half. A 22:00 shift clocked into at 00:10 is 130 minutes
		late. It came out as minus 1,310 and counted as on time."""
		from hrms.alvoraa_late_rules.late_rules import violations_for

		emp = self._employee("LMNightLate")
		_shift(NIGHT, "22:00:00", "06:00:00")
		self._day_span(emp, "2026-08-17", None, "2026-08-18", "06:05:00",
		               shift=NIGHT, in_at=("2026-08-18", "00:10:00"))
		found = violations_for(self.rule, emp, getdate("2026-08-17"), getdate("2026-08-23"))
		self.assertEqual([v["violation_type"] for v in found], ["Late Arrival"])
		self.assertEqual(found[0]["minutes"], 130)


class WhoTheRuleActuallyCovers(_MoneyBase):
	"""The portal must answer the same question the weekly job answers.

	It used to answer a different one, so an employee could be shown days that
	were never going to be taken off them.
	"""

	def test_an_exempt_grade_is_shown_nothing_rather_than_a_threat(self):
		from hrms.alvoraa_late_rules.late_rules import current_week_projection

		emp = self._employee("LMExempt")
		if not frappe.db.exists("Employee Grade", "LM Exempt Grade 017"):
			g = frappe.get_doc({"doctype": "Employee Grade",
			                    "__newname": "LM Exempt Grade 017"})
			g.name = "LM Exempt Grade 017"
			g.insert(ignore_permissions=True)
		frappe.db.set_value("Employee", emp, "grade", "LM Exempt Grade 017")
		self.rule.append("exempt_grades", {"employee_grade": "LM Exempt Grade 017"})
		self.rule.save(ignore_permissions=True)
		try:
			for day in ("2026-08-17", "2026-08-18", "2026-08-19"):
				self._day(emp, day, "10:45:00")
			p = current_week_projection(self.rule, emp, as_on="2026-08-19")
			self.assertFalse(p["covered"])
			self.assertEqual(p["violations"], [])
			self.assertEqual(p["projected_days"], 0)
			self.assertIsNone(hr_api._late_rule_for(emp))
		finally:
			self.rule.set("exempt_grades", [])
			self.rule.save(ignore_permissions=True)

	def test_a_week_before_the_rule_starts_is_not_projected(self):
		from hrms.alvoraa_late_rules.late_rules import current_week_projection

		emp = self._employee("LMBeforeStart")
		frappe.db.set_value("Attendance Deduction Rule", "LM Rule 017",
		                    "process_from", "2026-09-01")
		frappe.clear_document_cache("Attendance Deduction Rule", "LM Rule 017")
		rule = frappe.get_doc("Attendance Deduction Rule", "LM Rule 017")
		try:
			for day in ("2026-08-17", "2026-08-18", "2026-08-19"):
				self._day(emp, day, "10:45:00")
			p = current_week_projection(rule, emp, as_on="2026-08-19")
			self.assertFalse(p["covered"])
			self.assertEqual(p["projected_days"], 0)
		finally:
			frappe.db.set_value("Attendance Deduction Rule", "LM Rule 017",
			                    "process_from", None)
			frappe.clear_document_cache("Attendance Deduction Rule", "LM Rule 017")

	def test_somebody_who_joined_after_the_week_is_not_projected(self):
		from hrms.alvoraa_late_rules.late_rules import current_week_projection

		emp = self._employee("LMNewJoiner")
		frappe.db.set_value("Employee", emp, "date_of_joining", "2026-09-15")
		for day in ("2026-08-17", "2026-08-18", "2026-08-19"):
			self._day(emp, day, "10:45:00")
		p = current_week_projection(self.rule, emp, as_on="2026-08-19")
		self.assertFalse(p["covered"])
		self.assertEqual(p["projected_days"], 0)


SHIFT_B = "LM Test Shift 017 B"


class TheTeamList(_MoneyBase):
	"""A manager's list, with each report judged by their own rule.

	It used to take the FIRST report's rule and apply it to everybody. A team
	split across shifts was therefore measured against one person's thresholds.
	"""

	def _second_rule(self):
		"""A second shift and rule, forgiving half as much as the first."""
		_shift(SHIFT_B, "09:30:00", "18:30:00")
		if not frappe.db.exists("Attendance Deduction Rule", "LM Rule 017 B"):
			doc = frappe.get_doc({
				"doctype": "Attendance Deduction Rule", "rule_name": "LM Rule 017 B",
				"company": self.company, "shift_type": SHIFT_B, "enabled": 1,
				"week_start_day": "Monday", "late_threshold_minutes": 30,
				"count_early_exit": 0, "early_exit_threshold_minutes": 0,
				"free_violations_per_week": 1, "deduction_per_violation_days": 0.25,
				"round_up_from_days": 0.75, "round_up_to_days": 1.0,
				"deduct_from_leave_first": 0, "lwp_salary_component": "LM LWP 017",
				"notify_employee": 0, "notify_manager": 0,
			})
			doc.name = "LM Rule 017 B"
			doc.set("__newname", "LM Rule 017 B")
			doc.insert(ignore_permissions=True)

	def _report(self, first, manager, shift):
		email = "%s.lm017t@example.com" % first.lower()
		if not frappe.db.exists("User", email):
			frappe.get_doc({"doctype": "User", "email": email, "first_name": first,
			                "send_welcome_email": 0}).insert(ignore_permissions=True)
		e = frappe.get_doc({
			"doctype": "Employee", "first_name": first, "employee_name": first,
			"company": self.company, "date_of_birth": "1990-01-01",
			"date_of_joining": "2015-01-01",
			"gender": frappe.db.get_value("Gender", {}, "name") or "Male",
			"status": "Active", "default_shift": shift, "user_id": email,
			"holiday_list": self.holidays, "reports_to": manager,
		}).insert(ignore_permissions=True)
		return e.name, email

	def test_each_report_is_judged_by_their_own_rule(self):
		"""Both arrive 45 minutes late. One rule forgives 60 minutes, the other
		30. The forgiving one must not be applied to the person it does not
		belong to."""
		self._second_rule()
		mgr, mgr_email = self._report("LMTeamBoss", None, SHIFT)
		a, _ea = self._report("LMTeamA", mgr, SHIFT)      # threshold 60
		b, _eb = self._report("LMTeamB", mgr, SHIFT_B)    # threshold 30
		for emp, shift in ((a, SHIFT), (b, SHIFT_B)):
			for day in ("2026-08-17", "2026-08-18", "2026-08-19"):
				self._day(emp, day, "10:15:00", shift=shift)

		frappe.set_user(mgr_email)
		try:
			out = hr_api.get_team_late_list(weeks=1)
		finally:
			frappe.set_user("Administrator")
		rows = {r["employee"]: r for r in out["team"]}
		self.assertEqual(rows[a]["violations"], 0,
		                 "45 minutes against a 60-minute threshold is not a violation")
		self.assertEqual(rows[b]["violations"], 3,
		                 "45 minutes against a 30-minute threshold is three violations")
		# The rows carry no grade, joining date or pay: the extra Employee fields
		# the batching reads must stay on the server (slice 010, PRIV-3).
		for r in out["team"]:
			for leaked in ("grade", "date_of_joining", "company", "default_shift",
			               "lwp_amount", "status"):
				self.assertNotIn(leaked, r)
