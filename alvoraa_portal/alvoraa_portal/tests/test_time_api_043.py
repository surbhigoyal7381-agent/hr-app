"""Slice 043, Wave 3: the Time screen's one call, proved against real records.

**Its own company, stores, people and month** (tag `S043T`). Shared fixtures
have cost this project four slices; nothing here touches slice 010's, 030's,
034's, 042's or `fixtures_043`'s people.

**August 2026 is the month everything is asserted against**, because it is
entirely in the past, so "today" cannot move a single assertion. The one thing
that genuinely needs today - a future day not being drawn as absent - is tested
against the current month on purpose.

**The weekly offs are on THURSDAYS and the named holiday is on a SATURDAY.**
That is not decoration. The endpoint this slice retires,
`hr_api.get_attendance_calendar`, hard-coded Saturday and Sunday as the weekend,
so it was wrong for every tenant that does not work that way. A fixture with a
Saturday weekend would let that bug pass.
"""

import calendar
import re

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import time_api

TAG = "S043T"
COMPANY = "S043T Time Company"
ABBR = "S43T"
SHIFT = "S043T Day Shift"
HOLIDAYS = "S043T Holidays"
LEAVE_TYPE = "S043T Casual Leave"
RULE = "S043T Late Rule"
RULE_TWO = "S043T Other Rule"
COMPONENT = "S043T Loss Of Pay"

YEAR, MONTH = 2026, 8

# Weekly offs: every Thursday in August 2026. A named holiday on Saturday 15
# August. See the module docstring for why those two days and not the obvious
# ones.
THURSDAYS = ("2026-08-06", "2026-08-13", "2026-08-20", "2026-08-27")
NAMED_HOLIDAY = "2026-08-15"

# AC-4's table, exactly as the spec writes it: a 09:30 shift, 15 minutes of
# grace, four arrivals.
ARRIVALS = (
	("2026-08-03", "09:25:00", 0, False),
	("2026-08-04", "09:30:00", 0, False),
	("2026-08-05", "09:42:00", 12, False),
	("2026-08-07", "10:45:00", 75, True),
)
ABSENT_DAYS = ("2026-08-10", "2026-08-11", "2026-08-12")
LEAVE_DAY = "2026-08-17"


def _without_placeholders(message):
	"""`"more than {0} minutes"` -> `"more than  minutes"`.

	Only `{0}`, `{1}`, ... - a numbered hole a figure is poured into. Nothing
	else is touched, so a literal `60` in the copy still shows up.
	"""
	return re.sub(r"\{\d+\}", "", message)


def _features(names):
	frappe.local.conf["features"] = list(names)


def _clear_features():
	frappe.local.conf.pop("features", None)


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


def _user(local, roles=("Employee",)):
	email = "s043t.%s@example.com" % local
	if not frappe.db.exists("User", email):
		doc = frappe.get_doc({"doctype": "User", "email": email,
		                      "first_name": local.title(),
		                      "send_welcome_email": 0,
		                      "roles": [{"role": r} for r in roles]})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
	frappe.db.set_value("User", email, "module_profile", None,
	                    update_modified=False)
	frappe.db.delete("Block Module", {"parent": email, "parenttype": "User"})
	frappe.clear_cache(user=email)
	return email


def _employee(first, company, login, joined="2024-01-01", reports_to=None,
              default_shift=None):
	name = frappe.db.get_value("Employee",
	                           {"first_name": first, "last_name": TAG}, "name")
	doc = frappe.get_doc("Employee", name) if name else frappe.get_doc({
		"doctype": "Employee", "first_name": first, "last_name": TAG,
		"date_of_birth": "1990-01-01",
		"gender": frappe.get_all("Gender", pluck="name", limit=1)[0]})
	doc.company = company
	doc.date_of_joining = joined
	doc.status = "Active"
	doc.user_id = login
	doc.reports_to = reports_to
	doc.default_shift = default_shift
	# No automatic "Employee = self" User Permission: it narrows every list the
	# user sees, so a test about OUR rules would pass or fail because of it.
	doc.create_user_permission = 0
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)
	if login:
		frappe.db.delete("User Permission", {"user": login})
		frappe.clear_cache(user=login)
	frappe.db.commit()
	return doc.name


def _attendance(employee, date, status, in_time=None, shift=None,
                leave_type=None):
	existing = frappe.db.get_value("Attendance",
	                               {"employee": employee, "attendance_date": date,
	                                "docstatus": 1}, "name")
	if existing:
		return existing
	doc = frappe.get_doc({
		"doctype": "Attendance", "employee": employee, "attendance_date": date,
		"status": status, "company": COMPANY, "shift": shift,
		"leave_type": leave_type,
		"in_time": ("%s %s" % (date, in_time)) if in_time else None,
		"out_time": ("%s 18:30:00" % date) if in_time else None,
		"working_hours": 9 if in_time else 0,
	})
	doc.flags.ignore_permissions = True
	doc.flags.ignore_validate = True
	doc.insert(ignore_permissions=True, ignore_mandatory=True)
	doc.db_set("docstatus", 1, update_modified=False)
	return doc.name


class TimeFixture(FrappeTestCase):
	"""One month with every day state in it, and a rule that costs money."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = _ensure("Company", COMPANY, company_name=COMPANY,
		                      abbr=ABBR, default_currency="INR",
		                      country="India").name
		# 15 minutes of grace on the SHIFT, so AC-5's "set by" line has a
		# source to name and AC-4's 09:42 arrival is inside it.
		cls.shift = _ensure("Shift Type", SHIFT, shift_type=SHIFT,
		                    start_time="09:30:00", end_time="18:30:00",
		                    late_entry_grace_period=15).name
		_ensure("Leave Type", LEAVE_TYPE, leave_type_name=LEAVE_TYPE)
		cls.component = _ensure("Salary Component", COMPONENT,
		                        salary_component=COMPONENT,
		                        salary_component_abbr="S43TLP",
		                        type="Deduction").name

		cls.holidays = cls._holiday_list()

		cls.sandeep_login = _user("sandeep")
		cls.rahul_login = _user("rahul")
		cls.asha_login = _user("asha")
		cls.joiner_login = _user("joiner")
		cls.outsider_login = _user("outsider")

		cls.sandeep = _employee("Sandeep", cls.company, cls.sandeep_login)
		cls.rahul = _employee("Rahul", cls.company, cls.rahul_login,
		                      reports_to=cls.sandeep, default_shift=cls.shift)
		# Joined on 12 August 2026: the eleven days before that must not be
		# drawn as anything and must not be counted (AC-45).
		cls.joiner = _employee("Joiner", cls.company, cls.joiner_login,
		                       joined="2026-08-12", default_shift=cls.shift)
		# Nobody's report, in the same company, so "a month outside your line"
		# has somebody real to refuse (AC-37).
		cls.outsider = _employee("Outsider", cls.company, cls.outsider_login)
		# Asha deliberately has NO Employee record.

		cls._assign_holidays([cls.rahul, cls.sandeep, cls.joiner, cls.outsider])
		cls._assign_shift(cls.rahul)

		for date, in_time, _mins, _late in ARRIVALS:
			_attendance(cls.rahul, date, "Present", in_time=in_time,
			            shift=cls.shift)
		for date in ABSENT_DAYS:
			_attendance(cls.rahul, date, "Absent", shift=cls.shift)
		_attendance(cls.rahul, LEAVE_DAY, "On Leave", shift=cls.shift,
		            leave_type=LEAVE_TYPE)

		cls.rule = _ensure(
			"Attendance Deduction Rule", RULE, rule_name=RULE,
			company=cls.company, shift_type=cls.shift, enabled=1,
			week_start_day="Monday", late_threshold_minutes=60,
			count_early_exit=0, free_violations_per_week=1,
			deduction_per_violation_days=0.25, round_up_from_days=0.75,
			round_up_to_days=1.0, deduct_from_leave_first=0,
			lwp_salary_component=cls.component,
			notify_employee=0, notify_manager=0).name

		# A second rule with EVERY figure different, and a different week start
		# day. AC-12 asserts the words move with the record, which only means
		# something if there is a second record to move to.
		cls.rule_two = _ensure(
			"Attendance Deduction Rule", RULE_TWO, rule_name=RULE_TWO,
			company=cls.company, shift_type=cls.shift, enabled=0,
			week_start_day="Sunday", late_threshold_minutes=45,
			count_early_exit=1, early_exit_threshold_minutes=30,
			free_violations_per_week=2, deduction_per_violation_days=0.5,
			round_up_from_days=0.9, round_up_to_days=1.0,
			deduct_from_leave_first=1,
			leave_types=[{"leave_type": LEAVE_TYPE}],
			lwp_salary_component=cls.component,
			notify_employee=0, notify_manager=0).name

		# Two weeks of deductions. The second crosses a month boundary on
		# purpose: 29 September to 5 October is PAID in October, so AC-13 says
		# it belongs in October's row.
		cls.august_week = cls._deduction("2026-08-17", "2026-08-23", 1.0)
		cls.crossing_week = cls._deduction("2026-09-29", "2026-10-05", 0.5)

		cls._leave_allocation()
		cls._ledger_entry()
		frappe.db.commit()

	@classmethod
	def _holiday_list(cls):
		if not frappe.db.exists("Holiday List", HOLIDAYS):
			doc = frappe.get_doc({
				"doctype": "Holiday List", "holiday_list_name": HOLIDAYS,
				"from_date": "2026-01-01", "to_date": "2027-03-31",
				"holidays": (
					[{"holiday_date": d, "description": "Weekly Off",
					  "weekly_off": 1} for d in THURSDAYS]
					+ [{"holiday_date": NAMED_HOLIDAY,
					    "description": "Independence Day", "weekly_off": 0}]),
			})
			doc.flags.ignore_permissions = True
			doc.insert(ignore_permissions=True)
			frappe.db.commit()
		return HOLIDAYS

	@classmethod
	def _assign_holidays(cls, employees):
		"""Per employee, never company-wide.

		Frappe HR refuses a second overlapping company-wide assignment, so one
		of those is the widest piece of shared state a fixture can create.
		"""
		for name in employees:
			if frappe.db.exists("Holiday List Assignment",
			                    {"assigned_to": name, "holiday_list": HOLIDAYS,
			                     "docstatus": 1}):
				continue
			doc = frappe.get_doc({
				"doctype": "Holiday List Assignment", "holiday_list": HOLIDAYS,
				"applicable_for": "Employee", "assigned_to": name,
				"from_date": "2026-01-01"})
			doc.flags.ignore_permissions = True
			doc.insert(ignore_permissions=True)
			doc.submit()

	@classmethod
	def _assign_shift(cls, employee):
		if frappe.db.exists("Shift Assignment",
		                    {"employee": employee, "shift_type": cls.shift,
		                     "docstatus": 1}):
			return
		doc = frappe.get_doc({
			"doctype": "Shift Assignment", "employee": employee,
			"shift_type": cls.shift, "company": cls.company,
			"start_date": "2026-01-01", "status": "Active"})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		doc.submit()

	@classmethod
	def _deduction(cls, start, end, days):
		existing = frappe.db.get_value(
			"Attendance Deduction",
			{"employee": cls.rahul, "week_start": start}, "name")
		if existing:
			return existing
		doc = frappe.get_doc({
			"doctype": "Attendance Deduction", "employee": cls.rahul,
			"employee_name": frappe.db.get_value("Employee", cls.rahul,
			                                     "employee_name"),
			"company": cls.company, "rule": RULE,
			"week_start": start, "week_end": end,
			"computed_days": days, "deduction_days": days, "lwp_days": days,
			"total_violations": 4, "counted_violations": 3,
		})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_mandatory=True)
		# `Attendance Deduction.validate` RECOMPUTES `deduction_days` from the
		# violation rows (`attendance_deduction.py:33-35`), so a figure passed
		# to `insert` is thrown away and the row lands at zero. The first
		# version of this fixture did exactly that, and the year table then
		# summed to 0.0 while every assertion about it still passed - because
		# 0 equals 0. Written after the insert, which is also what the real
		# weekly job's figure is: stored, not recomputed on read.
		doc.db_set("deduction_days", days, update_modified=False)
		doc.db_set("computed_days", days, update_modified=False)
		doc.db_set("docstatus", 1, update_modified=False)
		return doc.name

	@classmethod
	def _leave_allocation(cls):
		"""8 days of Casual Leave, so the balance ring has a real figure.

		Without an allocation `_ledger_leave_balances` returns an EMPTY list
		and every assertion about a balance passes over nothing - a test that
		cannot fail. AC-14 is about the ring, the dropdown and the preview
		agreeing, and there has to be a number for them to agree on.
		"""
		if frappe.db.exists("Leave Allocation",
		                    {"employee": cls.rahul, "leave_type": LEAVE_TYPE,
		                     "docstatus": 1}):
			return
		doc = frappe.get_doc({
			"doctype": "Leave Allocation", "employee": cls.rahul,
			"leave_type": LEAVE_TYPE, "from_date": "2026-01-01",
			"to_date": "2026-12-31", "new_leaves_allocated": 8,
			"company": cls.company, "carry_forward": 0})
		doc.flags.ignore_permissions = True
		doc.flags.ignore_validate = True
		doc.insert(ignore_permissions=True, ignore_mandatory=True)
		doc.db_set("total_leaves_allocated", 8, update_modified=False)
		doc.db_set("docstatus", 1, update_modified=False)
		# The LEDGER is what `_ledger_leave_balances` reads (slice 035), not
		# the allocation document. Submitting the allocation properly would
		# write this row; this fixture skips `validate` because nothing in this
		# slice tests how leave is allocated, so the row is written here
		# instead. Without it the allocation exists and the balance is still
		# empty, which is the quietest way for this fixture to lie.
		entry = frappe.get_doc({
			"doctype": "Leave Ledger Entry", "employee": cls.rahul,
			"leave_type": LEAVE_TYPE, "company": cls.company,
			"transaction_type": "Leave Allocation",
			"transaction_name": doc.name,
			"from_date": "2026-01-01", "to_date": "2026-12-31",
			"leaves": 8, "is_carry_forward": 0, "is_expired": 0})
		entry.flags.ignore_permissions = True
		entry.insert(ignore_permissions=True, ignore_mandatory=True)
		entry.db_set("docstatus", 1, update_modified=False)

	@classmethod
	def _ledger_entry(cls):
		"""A day the LATE RULE took, straight out of the ledger.

		This is the row AC-15 exists for. It never was a Leave Application, so
		until Past leave listed it the balance and the history disagreed by
		exactly these days and a person had no way to find them.
		"""
		if frappe.db.exists("Leave Ledger Entry",
		                    {"employee": cls.rahul,
		                     "transaction_type": "Attendance Deduction"}):
			return
		doc = frappe.get_doc({
			"doctype": "Leave Ledger Entry", "employee": cls.rahul,
			"leave_type": LEAVE_TYPE, "company": cls.company,
			"transaction_type": "Attendance Deduction",
			"transaction_name": cls.august_week,
			"from_date": "2026-08-17", "to_date": "2026-08-17",
			"leaves": -1.0, "is_expired": 0})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True, ignore_mandatory=True)
		doc.db_set("docstatus", 1, update_modified=False)

	def setUp(self):
		_features(("portal", "leaves", "attendance", "expenses", "payroll"))
		frappe.set_user(self.rahul_login)

	def tearDown(self):
		frappe.set_user("Administrator")
		_clear_features()

	def time(self, **kwargs):
		kwargs.setdefault("year", YEAR)
		kwargs.setdefault("month", MONTH)
		return time_api.get_time(**kwargs)

	def day(self, date, payload=None):
		payload = payload or self.time()
		for row in payload["month"]["days"]:
			if row["date"] == date:
				return row
		raise AssertionError("no day %s in the payload" % date)


# ── who may call it ──────────────────────────────────────────────────────────

class TestWhoMayCallIt(TimeFixture):

	def test_guest_is_refused(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			self.time()

	def test_a_caller_with_no_employee_record_is_refused(self):
		"""Asha has a login and no Employee record.

		She is refused rather than shown an empty month: an empty calendar
		reads as "you did not work", which is the most expensive wrong message
		this screen can send.
		"""
		frappe.set_user(self.asha_login)
		with self.assertRaises(frappe.PermissionError):
			self.time()

	def test_a_month_outside_your_line_is_refused(self):
		"""AC-37. Sandeep may open Rahul, who reports to him, and nobody else."""
		frappe.set_user(self.sandeep_login)
		with self.assertRaises(frappe.PermissionError):
			self.time(employee=self.outsider)

	def test_a_manager_may_open_his_own_report(self):
		frappe.set_user(self.sandeep_login)
		payload = self.time(employee=self.rahul)
		self.assertEqual(payload["me"]["employee"], self.rahul)
		self.assertFalse(payload["is_self"])

	def test_an_employee_cannot_open_a_colleague(self):
		frappe.set_user(self.rahul_login)
		with self.assertRaises(frappe.PermissionError):
			self.time(employee=self.outsider)


class TestSomebodyElsesMonthCarriesNothingElse(TimeFixture):
	"""The one place this endpoint answers about another person.

	§5 says a manager never learns a report's leave balance, their pay, or what
	the late rule cost them. So the non-self branch returns the month and stops,
	and this class is what stops a later key being added to it by accident.
	"""

	def test_the_keys_are_the_short_list(self):
		frappe.set_user(self.sandeep_login)
		payload = self.time(employee=self.rahul)
		self.assertEqual(sorted(payload.keys()),
		                 sorted(time_api.SUBJECT_KEYS))

	def test_the_short_list_is_a_subset_of_the_full_one(self):
		self.assertTrue(set(time_api.SUBJECT_KEYS) <= set(time_api.TIME_KEYS))

	def test_no_leave_no_rule_and_no_pay_reach_a_manager(self):
		frappe.set_user(self.sandeep_login)
		payload = self.time(employee=self.rahul)
		for forbidden in ("leave", "rule", "record_this_year", "shift",
		                  "days_off"):
			self.assertNotIn(forbidden, payload)

	def test_the_subject_block_is_two_keys(self):
		frappe.set_user(self.sandeep_login)
		payload = self.time(employee=self.rahul)
		self.assertEqual(sorted(payload["me"].keys()),
		                 ["employee", "employee_name"])


# ── the month ────────────────────────────────────────────────────────────────

class TestTheMonthCalendar(TimeFixture):

	def test_the_payload_keys_are_the_fixed_list(self):
		self.assertEqual(sorted(self.time().keys()), sorted(time_api.TIME_KEYS))

	def test_every_day_of_the_month_is_there(self):
		days = self.time()["month"]["days"]
		self.assertEqual(len(days), calendar.monthrange(YEAR, MONTH)[1])

	def test_six_distinct_states_are_drawn(self):
		"""AC-1. A worked day, an absence, a weekly off, a public holiday, a
		leave day and a day with no record - six, told apart."""
		payload = self.time()
		states = set()
		for row in payload["month"]["days"]:
			if row["weekly_off"]:
				states.add("weekly_off")
			elif row["holiday"]:
				states.add("holiday")
			else:
				states.add(row["state"])
		for expected in ("present", "absent", "weekly_off", "holiday",
		                 "on_leave", "no_record"):
			self.assertIn(expected, states, "missing state %s" % expected)

	def test_a_weekly_off_is_not_drawn_as_a_public_holiday(self):
		"""AC-1. Both arrive as Holiday rows; only `weekly_off` tells them
		apart, and without it a person's week looks like a month of holidays."""
		for date in THURSDAYS:
			row = self.day(date)
			self.assertTrue(row["weekly_off"], date)
		named = self.day(NAMED_HOLIDAY)
		self.assertFalse(named["weekly_off"])
		self.assertEqual(named["holiday"], "Independence Day")

	def test_the_weekly_offs_are_thursdays_not_the_weekend(self):
		"""The regression guard for the endpoint this slice retires.

		`get_attendance_calendar` assumed Saturday and Sunday. Every Saturday
		and Sunday in this fixture is an ordinary day, and every Thursday is
		off, so a hard-coded weekend cannot pass here.
		"""
		payload = self.time()
		for row in payload["month"]["days"]:
			if row["weekday"] in ("Saturday", "Sunday"):
				self.assertFalse(row["weekly_off"], row["date"])

	def test_an_auto_marked_absent_day_is_a_real_absence(self):
		"""AC-2. The day reads as an absence - the words "Marked absent" are
		the screen's, and the fact behind them is the Attendance row's status,
		not an inference from a missing punch."""
		for date in ABSENT_DAYS:
			self.assertEqual(self.day(date)["state"], "absent", date)

	def test_a_day_with_no_record_is_not_an_absence(self):
		"""The old calendar marked every record-less weekday Absent. 18 August
		has no Attendance row at all and must not be red."""
		self.assertEqual(self.day("2026-08-18")["state"], "no_record")

	def test_a_future_day_is_marked_future_and_not_absent(self):
		"""AC-3, against the CURRENT month, because that is the only place a
		future day exists."""
		today = frappe.utils.getdate(frappe.utils.nowdate())
		last = calendar.monthrange(today.year, today.month)[1]
		if today.day >= last:
			self.skipTest("run on the last day of a month; no future day exists")
		payload = time_api.get_time(year=today.year, month=today.month)
		future = [d for d in payload["month"]["days"] if d["future"]]
		self.assertTrue(future)
		for row in future:
			self.assertNotEqual(row["state"], "absent", row["date"])
			self.assertEqual(row["state"], "future")


class TestTheDay(TimeFixture):

	def test_the_four_arrivals_from_the_spec(self):
		"""AC-4, the table exactly as written.

		The 09:25 row is the regression guard for the bug slice 017 fixed: a
		09:25 punch on a 09:30 shift was reported as 25 minutes late, because
		the cache held the shift's LENGTH where its START belonged.
		"""
		payload = self.time()
		for date, _in_time, minutes, is_late in ARRIVALS:
			row = self.day(date, payload)
			self.assertEqual(row["late_by_mins"], minutes, date)
			self.assertEqual(row["is_late"], is_late, date)

	def test_a_punch_before_the_shift_start_is_never_late(self):
		row = self.day("2026-08-03")
		self.assertEqual(row["late_by_mins"], 0)
		self.assertNotEqual(row["late_by_mins"], 25)

	def test_twelve_minutes_late_is_inside_the_grace_and_still_says_twelve(self):
		"""009 design decision 7: the minutes shown are always the TRUE
		minutes. The grace decides whether the day counts, not what it says."""
		row = self.day("2026-08-05")
		self.assertEqual(row["late_by_mins"], 12)
		self.assertFalse(row["is_late"])
		self.assertEqual(row["grace_mins"], 15)

	def test_the_grace_row_names_its_source(self):
		"""AC-5. The figure is the shift's own `late_entry_grace_period`, so
		the sheet can say which record it came from rather than guessing."""
		row = self.day("2026-08-05")
		self.assertEqual(row["grace_source"], "shift")

	def test_the_punches_are_on_the_day(self):
		row = self.day("2026-08-07")
		self.assertEqual(row["in_time"], "10:45")
		self.assertEqual(row["shift_starts"], "09:30")


class TestAMidMonthJoiner(TimeFixture):
	"""AC-45. Eleven days before somebody started are not their record."""

	def setUp(self):
		super().setUp()
		frappe.set_user(self.joiner_login)

	def test_the_days_before_joining_are_marked(self):
		payload = self.time()
		before = [d for d in payload["month"]["days"] if d["before_joining"]]
		self.assertEqual(len(before), 11)
		self.assertEqual(sorted(d["date"] for d in before)[-1], "2026-08-11")

	def test_they_are_not_drawn_as_absent(self):
		payload = self.time()
		for row in payload["month"]["days"]:
			if row["before_joining"]:
				self.assertNotEqual(row["state"], "absent", row["date"])

	def test_they_are_not_counted_in_any_total(self):
		payload = self.time()
		totals = payload["month"]["totals"]
		self.assertEqual(totals["before_joining"], 11)
		live = [d for d in payload["month"]["days"] if not d["before_joining"]]
		self.assertEqual(totals["no_record"],
		                 len([d for d in live if d["state"] == "no_record"]))

	def test_the_joining_date_is_on_the_payload(self):
		self.assertEqual(self.time()["month"]["joined_on"], "2026-08-12")

	def test_somebody_who_joined_long_ago_has_none(self):
		"""The guard that proves the check above can fail: Rahul joined in
		2024, so the same code must mark nothing."""
		frappe.set_user(self.rahul_login)
		payload = self.time()
		self.assertEqual(payload["month"]["totals"]["before_joining"], 0)


# ── totals equal their lists ─────────────────────────────────────────────────

class TestEveryTotalEqualsItsList(TimeFixture):
	"""AC-11 and §6. Where a total and a list could be worked out two ways,
	they are worked out once and the list is rendered from the same array."""

	def test_days_present_equals_the_present_rows(self):
		payload = self.time()
		days = payload["month"]["days"]
		self.assertEqual(
			payload["month"]["totals"]["present"],
			len([d for d in days if d["state"] in ("present", "work_from_home")]))
		self.assertEqual(payload["month"]["totals"]["present"], len(ARRIVALS))

	def test_days_absent_equals_the_rows_the_calendar_draws_red(self):
		payload = self.time()
		days = payload["month"]["days"]
		self.assertEqual(payload["month"]["totals"]["absent"],
		                 len([d for d in days if d["state"] == "absent"]))
		self.assertEqual(payload["month"]["totals"]["absent"], len(ABSENT_DAYS))

	def test_late_days_counts_only_days_past_the_grace(self):
		"""The total the deduction card has to agree with. A day inside the
		grace is on time as far as the organisation's policy goes, and counting
		it here is what made this figure disagree with the money."""
		payload = self.time()
		days = payload["month"]["days"]
		self.assertEqual(payload["month"]["totals"]["late_days"],
		                 len([d for d in days if d["is_late"]]))
		self.assertEqual(payload["month"]["totals"]["late_days"], 1)

	def test_weekly_offs_equals_the_weekly_off_rows(self):
		payload = self.time()
		days = payload["month"]["days"]
		self.assertEqual(payload["month"]["totals"]["weekly_offs"],
		                 len([d for d in days if d["weekly_off"]]))
		self.assertEqual(payload["month"]["totals"]["weekly_offs"],
		                 len(THURSDAYS))

	def test_named_holidays_and_weekly_offs_add_up_to_the_holiday_rows(self):
		payload = self.time()
		totals = payload["month"]["totals"]
		days = payload["month"]["days"]
		self.assertEqual(totals["named_holidays"] + totals["weekly_offs"],
		                 len([d for d in days if d["holiday"]]))
		self.assertEqual(totals["named_holidays"], 1)

	def test_the_year_total_equals_the_months_under_it(self):
		"""AC-11 and AC-13: the top figure equals the months, and each month
		equals the weeks listed under it."""
		record = self.time()["record_this_year"]
		self.assertEqual(
			record["total_days"],
			round(sum(m["days"] for m in record["months"]), 2))
		for bucket in record["months"]:
			self.assertEqual(bucket["days"],
			                 round(sum(w["days"] for w in bucket["weeks"]), 2))

	def test_a_capped_year_table_says_so(self):
		record = self.time()["record_this_year"]
		self.assertIn("capped", record)
		self.assertFalse(record["capped"])
		self.assertEqual(record["weeks_listed"],
		                 sum(len(m["weeks"]) for m in record["months"]))


class TestAWeekThatCrossesAMonth(TimeFixture):
	"""AC-13. 29 September to 5 October is PAID in October."""

	def test_it_lands_in_the_october_row(self):
		record = self.time()["record_this_year"]
		october = [m for m in record["months"] if m["month"] == "2026-10"]
		self.assertEqual(len(october), 1)
		weeks = october[0]["weeks"]
		self.assertEqual([w["week_start"] for w in weeks], ["2026-09-29"])

	def test_it_is_not_in_the_september_row(self):
		record = self.time()["record_this_year"]
		september = [m for m in record["months"] if m["month"] == "2026-09"]
		self.assertEqual(september, [])

	def test_the_august_week_is_in_august(self):
		"""The guard that proves the grouping is doing something: a week that
		does not cross a boundary lands where you would expect."""
		record = self.time()["record_this_year"]
		august = [m for m in record["months"] if m["month"] == "2026-08"]
		self.assertEqual(len(august), 1)
		self.assertEqual([w["week_start"] for w in august[0]["weeks"]],
		                 ["2026-08-17"])


# ── the shift card and days off ──────────────────────────────────────────────

class TestTheShiftCard(TimeFixture):

	def test_it_reads_todays_assignment(self):
		"""AC-10. A Shift Assignment covering today beats
		`Employee.default_shift`, which is Frappe HR's own precedence."""
		card = self.time()["shift"]
		self.assertEqual(card["shift"], SHIFT)
		self.assertEqual(card["starts"], "09:30")
		self.assertEqual(card["ends"], "18:30")
		self.assertEqual(card["source"], "assignment")
		self.assertIsNone(card["note"])

	def test_somebody_with_no_shift_gets_a_sentence_not_blank_times(self):
		"""AC-34. A card with empty times reads as "your shift is nothing",
		which is not a fact anybody can act on."""
		frappe.set_user(self.outsider_login)
		card = self.time()["shift"]
		self.assertIsNone(card["shift"])
		self.assertEqual(card["note"], "No shift is set for you. Ask HR.")

	def test_the_default_shift_is_used_when_there_is_no_assignment(self):
		frappe.set_user(self.joiner_login)
		card = self.time()["shift"]
		self.assertEqual(card["shift"], SHIFT)
		self.assertEqual(card["source"], "default")


class TestDaysOff(TimeFixture):

	def test_the_weekly_off_weekdays_come_from_the_list(self):
		"""AC-10. Thursdays, because that is what the records say - not
		Saturday and Sunday, which is what the retired endpoint assumed."""
		self.assertEqual(self.time()["days_off"]["weekly_off_weekdays"],
		                 ["Thursday"])

	def test_the_named_holidays_are_the_persons_own_list(self):
		off = self.time()["days_off"]
		self.assertIsNone(off["note"])
		dates = [h["date"] for h in off["holidays"]]
		self.assertNotIn("2026-08-06", dates, "a weekly off is not a day off ahead")

	def test_no_holiday_list_gives_slice_035s_sentence(self):
		"""AC-33's neighbour: a setup gap says so, and a quiet empty card
		would hide it."""
		frappe.set_user("Administrator")
		frappe.db.set_value("Holiday List Assignment",
		                    {"assigned_to": self.outsider}, "docstatus", 2)
		frappe.db.commit()
		try:
			frappe.set_user(self.outsider_login)
			off = self.time()["days_off"]
			self.assertEqual(
				off["note"],
				"No holiday list is assigned to you yet. Ask HR to set one up.")
			self.assertEqual(off["weekly_off_weekdays"], [])
		finally:
			frappe.set_user("Administrator")
			frappe.db.set_value("Holiday List Assignment",
			                    {"assigned_to": self.outsider}, "docstatus", 1)
			frappe.db.commit()


# ── leave ────────────────────────────────────────────────────────────────────

class TestLeave(TimeFixture):

	def test_past_leave_lists_the_days_the_rule_took(self):
		"""AC-15. The ledger row is why the balance is what it is, and until
		it was listed the balance and the history disagreed by exactly it."""
		rows = self.time()["leave"]["past"]
		by_rule = [r for r in rows if r["kind"] == "rule"]
		self.assertEqual(len(by_rule), 1)
		self.assertEqual(by_rule[0]["days"], 1.0)
		self.assertEqual(by_rule[0]["label"], "Taken by the late-coming rule")

	def test_a_rule_row_is_labelled_so_nobody_reads_it_as_leave_they_asked_for(self):
		rows = self.time()["leave"]["past"]
		for row in rows:
			if row["kind"] == "application":
				self.assertIsNone(row["label"])

	def test_the_days_taken_by_the_rule_are_shown_as_a_positive_number(self):
		"""The ledger stores days going out as a negative. A minus sign that
		means "taken" is a puzzle, not a fact."""
		rows = [r for r in self.time()["leave"]["past"] if r["kind"] == "rule"]
		self.assertGreater(rows[0]["days"], 0)

	def test_there_is_a_balance_to_read(self):
		"""The guard that stops every assertion below passing over an empty
		list. It did, until the fixture grew a Leave Ledger Entry for the
		allocation - the balance comes from the ledger, not from the
		allocation document."""
		self.assertTrue(self.time()["leave"]["balances"])

	def test_the_balance_block_names_what_is_left(self):
		block = self.time()["leave"]
		for row in block["balances"]:
			self.assertEqual(sorted(row.keys()),
			                 ["expired", "leave_type", "left", "pending",
			                  "taken", "total"])

	def test_the_day_the_rule_took_is_missing_from_the_balance(self):
		"""AC-14. 8 allocated, 1 taken by the late rule, 7 left - and the
		history below it lists that one day, so the two agree.

		This is the defect appendix C recorded at T-09: the ring said one
		thing, the apply-leave preview said another, and the day the rule took
		was the difference nobody could find.
		"""
		block = self.time()["leave"]
		mine = [r for r in block["balances"] if r["leave_type"] == LEAVE_TYPE]
		self.assertEqual(len(mine), 1)
		self.assertEqual(mine[0]["total"], 8.0)
		self.assertEqual(mine[0]["taken"], 1.0)
		self.assertEqual(mine[0]["left"], 7.0)
		by_rule = [r for r in block["past"] if r["kind"] == "rule"]
		self.assertEqual(sum(r["days"] for r in by_rule), mine[0]["taken"])


# ── the late rule, in words, from the record ─────────────────────────────────

class TestTheRuleIsExplainedFromTheRecord(TimeFixture):

	def test_it_is_covered_and_named(self):
		rule = self.time()["rule"]
		self.assertTrue(rule["covered"])
		self.assertEqual(rule["rule_name"], RULE)

	def test_every_figure_is_the_records_own(self):
		"""AC-12, rule one."""
		rule = self.time()["rule"]
		self.assertEqual(rule["late_threshold_minutes"], 60)
		self.assertEqual(rule["free_violations_per_week"], 1)
		self.assertEqual(rule["week_start_day"], "Monday")
		self.assertEqual(rule["week_end_day"], "Sunday")
		self.assertFalse(rule["counts_early_exit"])
		self.assertFalse(rule["deduct_from_leave_first"])

	def test_the_words_carry_the_records_numbers(self):
		joined = " ".join(self.time()["rule"]["clauses"])
		self.assertIn("60", joined)
		self.assertIn("Monday", joined)
		self.assertIn("Sunday", joined)

	def test_nothing_is_said_about_leaving_early_when_the_rule_does_not_count_it(self):
		joined = " ".join(self.time()["rule"]["clauses"]).lower()
		self.assertNotIn("before your shift ends", joined)

	def test_it_says_the_days_come_out_of_pay(self):
		joined = " ".join(self.time()["rule"]["clauses"])
		self.assertIn("out of your pay", joined)

	def test_every_figure_moves_when_the_record_moves(self):
		"""AC-12's real test. The same code against a second record with
		different numbers, a different week start and early exits counted -
		proving no sentence is a hard-coded one."""
		frappe.set_user("Administrator")
		frappe.db.set_value("Attendance Deduction Rule", RULE, "enabled", 0)
		frappe.db.set_value("Attendance Deduction Rule", RULE_TWO, "enabled", 1)
		frappe.clear_cache(doctype="Attendance Deduction Rule")
		try:
			frappe.set_user(self.rahul_login)
			rule = self.time()["rule"]
			self.assertEqual(rule["late_threshold_minutes"], 45)
			self.assertEqual(rule["free_violations_per_week"], 2)
			self.assertEqual(rule["week_start_day"], "Sunday")
			self.assertEqual(rule["week_end_day"], "Saturday")
			self.assertTrue(rule["counts_early_exit"])
			joined = " ".join(rule["clauses"])
			self.assertIn("45", joined)
			self.assertIn("Sunday", joined)
			self.assertIn("Saturday", joined)
			self.assertIn("before your shift ends", joined)
			self.assertIn("out of your leave balance first", joined)
			self.assertNotIn("60", joined)
		finally:
			frappe.set_user("Administrator")
			frappe.db.set_value("Attendance Deduction Rule", RULE, "enabled", 1)
			frappe.db.set_value("Attendance Deduction Rule", RULE_TWO,
			                    "enabled", 0)
			frappe.clear_cache(doctype="Attendance Deduction Rule")

	def test_the_two_rules_genuinely_differ(self):
		"""Without this the test above could pass by reading one record
		twice."""
		one = frappe.get_doc("Attendance Deduction Rule", RULE)
		two = frappe.get_doc("Attendance Deduction Rule", RULE_TWO)
		self.assertNotEqual(one.late_threshold_minutes,
		                    two.late_threshold_minutes)
		self.assertNotEqual(one.week_start_day, two.week_start_day)
		self.assertNotEqual(one.free_violations_per_week,
		                    two.free_violations_per_week)

	def test_somebody_no_rule_covers_gets_the_tab_and_a_sentence(self):
		"""AC-35. The tab exists and says so. Showing zeros would read as
		"the rule is satisfied", which is a different thing and the one
		nobody would query."""
		frappe.set_user(self.outsider_login)
		rule = self.time()["rule"]
		self.assertFalse(rule["covered"])
		self.assertEqual(rule["note"], "No late-coming rule applies to you.")

	def test_an_accountable_contact_is_always_offered(self):
		"""AC-60. Never blank, and never a sentence implying somebody looked
		at this person's week."""
		rule = self.time()["rule"]
		self.assertTrue(rule["accountable"])
		self.assertIn("accountable_named", rule)

	def test_the_fallback_does_not_imply_a_review(self):
		rule = self.time()["rule"]
		if not rule["accountable_named"]:
			lowered = rule["accountable"].lower()
			for claim in ("reviewed", "checked by", "approved by"):
				self.assertNotIn(claim, lowered)


# ── the copy holds no numbers of its own ─────────────────────────────────────

class TestNoFigureIsWrittenIntoTheCopy(TimeFixture):
	"""AC-5 and AC-12's static half.

	The rule explanation must hold no threshold, no day of the week and no
	leave type name. A sentence with a number in it is a sentence that goes on
	being wrong after somebody changes the setting, and nobody finds out.
	"""

	def source(self):
		import io
		import os

		import alvoraa_portal
		path = os.path.join(os.path.dirname(os.path.abspath(
			alvoraa_portal.__file__)), "time_api.py")
		return io.open(path, encoding="utf-8").read()

	def messages(self):
		"""Every translatable string in the module, comments excluded.

		Comments are where the reasons live and they legitimately name the
		numbers they are about - the `60` in "the code uses `>`" is an
		explanation, not copy. The strings are the copy.
		"""
		import ast
		found = []
		for node in ast.walk(ast.parse(self.source())):
			if (isinstance(node, ast.Call)
					and isinstance(node.func, ast.Name)
					and node.func.id == "_"):
				for arg in node.args:
					if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
						found.append(arg.value)
		return found

	def test_there_are_messages_to_check(self):
		"""The guard that stops this whole class passing on an empty list."""
		self.assertGreater(len(self.messages()), 6)

	def test_no_message_carries_a_number(self):
		"""A `{0}` is a hole for a figure; a `60` IS the figure.

		The first version of this check read the raw string and failed on its
		own placeholders - which would have pushed the next person to write the
		number in rather than fix the check. The placeholders are removed
		first, and `test_this_check_can_actually_fail` proves what is left
		still catches a real one.
		"""
		for message in self.messages():
			self.assertIsNone(re.search(r"\d", _without_placeholders(message)),
			                  "a figure is written into: %r" % message)

	def test_no_message_names_a_day_of_the_week(self):
		for message in self.messages():
			for day in calendar.day_name:
				self.assertNotIn(day, message,
				                 "%s is written into: %r" % (day, message))

	def test_no_message_names_a_leave_type(self):
		for message in self.messages():
			self.assertNotIn("Casual Leave", message)
			self.assertNotIn("Sick Leave", message)

	def test_this_check_can_actually_fail(self):
		"""A guard that cannot go red is not a guard.

		The same three rules, run against a sentence of the exact shape the
		check exists to catch - and through the same placeholder-stripping the
		real check uses, so a hole in that cannot hide a figure.
		"""
		bad = "Arriving more than 60 minutes late on a Monday costs Casual Leave."
		self.assertIsNotNone(re.search(r"\d", _without_placeholders(bad)))
		self.assertIn("Monday", bad)
		self.assertIn("Casual Leave", bad)

	def test_stripping_placeholders_does_not_swallow_a_real_figure(self):
		"""The strip is where this check could quietly stop working: a pattern
		that ate `{0}` and `60` alike would pass everything forever."""
		self.assertEqual(_without_placeholders("a {0} b {1} c"), "a  b  c")
		self.assertIn("60", _without_placeholders("more than 60 minutes"))


class TestNothingOnThisPathWrites(TimeFixture):
	"""AC-61's neighbour. Showing a person their own month must not create a
	record about them - no read log, no "seen" flag, nothing."""

	def test_a_full_call_writes_nothing(self):
		import alvoraa_portal.time_api as module

		writes = []
		real = frappe.db.sql

		def spy(query, *args, **kwargs):
			text = str(query).lstrip().lower()
			if text.startswith(("insert", "update", "delete", "replace")):
				writes.append(" ".join(str(query).split())[:120])
			return real(query, *args, **kwargs)

		frappe.db.sql = spy
		try:
			module.get_time(year=YEAR, month=MONTH)
		finally:
			frappe.db.sql = real
		self.assertEqual(writes, [])

	def test_the_spy_can_see_a_write(self):
		"""Proving the assertion above is capable of failing."""
		seen = []
		real = frappe.db.sql

		def spy(query, *args, **kwargs):
			if str(query).lstrip().lower().startswith("update"):
				seen.append(1)
			return real(query, *args, **kwargs)

		frappe.set_user("Administrator")
		frappe.db.sql = spy
		try:
			frappe.db.set_value("Employee", self.rahul, "designation", None)
		finally:
			frappe.db.sql = real
		self.assertTrue(seen)


class TestTheMemoDiesWithTheCall(TimeFixture):
	"""`call_cache` is a memo for one call, not a cache. If it outlived the
	call, a person moved to another holiday list at 10:00 would keep seeing the
	old one - which is a permission bug, not a stale number."""

	def test_no_memo_is_left_open_afterwards(self):
		from alvoraa_portal import call_cache
		self.time()
		self.assertFalse(call_cache.is_open())

	def test_the_memo_is_closed_even_when_the_call_fails(self):
		from alvoraa_portal import call_cache
		frappe.set_user(self.rahul_login)
		with self.assertRaises(frappe.PermissionError):
			time_api.get_time(year=YEAR, month=MONTH, employee=self.outsider)
		self.assertFalse(call_cache.is_open())
