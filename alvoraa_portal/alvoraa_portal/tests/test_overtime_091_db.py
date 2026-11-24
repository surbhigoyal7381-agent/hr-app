"""Slice 091 on a real site: the rule set table, the night green tick, the card,
and a night judged from real punches past midnight.

The arithmetic is in `test_overtime_091` (no database). This file proves the
wiring: that the table a person types becomes the edges the engine reads, that
"Night Green For Everyone" opens the night green and nothing else, and that the
card does not offer a green to somebody who can never earn one.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, nowdate

from alvoraa_portal.day_marks import _green
from alvoraa_portal.payroll_rules_apply import (
	_employee_flags, day_rules_on, judge, prepare,
)
from alvoraa_portal.tests.test_payroll_flags import (  # noqa: F401
	COMPANY, _employee, _rule_set, setUpModule,
)

BANDS = [{"last_punch_at": "23:00:00", "next_day": 0, "total_quarters": 1},
         {"last_punch_at": "01:00:00", "next_day": 1, "total_quarters": 2},
         {"last_punch_at": "03:00:00", "next_day": 1, "total_quarters": 4}]
CONTRACT = {"category": "Contract", "grace_minutes": 15, "earns_marks": 0,
            "earns_leave_credits": 0, "doubles_deduction": 0}
SHIFT = "OT091 10:30-20:30"


def _grant(employee, eligibility):
	g = frappe.get_doc({"doctype": "Alvoraa Green Eligibility", "employee": employee,
	                    "from_date": "2026-01-01", "eligibility": eligibility,
	                    "reason": "overtime 091 test"})
	g.flags.ignore_permissions = True
	g.insert()


class TheTableThePersonTypes(FrappeTestCase):
	def test_the_rows_become_edges_on_the_shift_day_clock(self):
		rs = _rule_set(overtime_bands=BANDS)
		day = getdate(nowdate())
		self.assertEqual(prepare(rs, day, day)["overtime_bands"],
		                 [(1380, 1), (1500, 2), (1620, 4)])

	def test_the_rows_may_be_typed_in_any_order(self):
		rs = _rule_set(overtime_bands=list(reversed(BANDS)))
		day = getdate(nowdate())
		self.assertEqual(prepare(rs, day, day)["overtime_bands"],
		                 [(1380, 1), (1500, 2), (1620, 4)])

	def test_no_table_means_no_overtime_and_saves_fine(self):
		rs = _rule_set()
		day = getdate(nowdate())
		self.assertEqual(prepare(rs, day, day)["overtime_bands"], [])

	def test_a_later_row_that_pays_no_more_is_refused(self):
		bad = [BANDS[0], dict(BANDS[1], total_quarters=1)]
		with self.assertRaises(frappe.ValidationError):
			_rule_set(overtime_bands=bad)

	def test_more_than_a_day_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			_rule_set(overtime_bands=[dict(BANDS[0], total_quarters=5)])

	def test_two_rows_with_the_same_time_are_refused(self):
		with self.assertRaises(frappe.ValidationError):
			_rule_set(overtime_bands=[BANDS[0], dict(BANDS[0], total_quarters=2)])


class NightGreenForEveryone(FrappeTestCase):
	"""D1, option C. The night green opens to everyone; the morning green stays
	exactly as the field and the dated grants say."""

	def setUp(self):
		self.date = getdate(nowdate())

	def _flags(self, grant, tick):
		rs = _rule_set(green_eligibility_field="dtc_green_eligibility",
		               night_green_for_everyone=1 if tick else 0)
		emp = _employee("Permanent")
		if grant:
			_grant(emp, grant)
		return _employee_flags(emp, self.date, prepare(rs, self.date, self.date))

	def test_the_tick_opens_the_night_green_to_somebody_barred_from_it(self):
		for grant in ("None", "Morning Green"):
			self.assertFalse(self._flags(grant, 0)["night_green_eligible"], grant)
			self.assertTrue(self._flags(grant, 1)["night_green_eligible"], grant)

	def test_the_morning_green_is_exactly_what_it_was_with_the_tick_on(self):
		for grant in ("None", "Morning Green", "Night Green", "Both", None):
			self.assertEqual(self._flags(grant, 1)["morning_green_eligible"],
			                 self._flags(grant, 0)["morning_green_eligible"], grant)
		# And the dated grants still decide it: barred stays barred.
		self.assertFalse(self._flags("Night Green", 1)["morning_green_eligible"])
		self.assertTrue(self._flags("Morning Green", 1)["morning_green_eligible"])

	def test_with_the_tick_off_nothing_changed(self):
		self.assertTrue(self._flags("Both", 0)["night_green_eligible"])
		self.assertFalse(self._flags("Morning Green", 0)["night_green_eligible"])
		self.assertFalse(self._flags(None, 0)["night_green_eligible"],
		                 "a blank value earns a morning green and not a night one, as before")


class TheTickKeepsItsPromise(FrappeTestCase):
	"""The label says "who earn marks", so staff who do not (Contract) earn no
	green of any kind with the tick on, on the engine and on the card."""

	def test_the_label_and_description_say_who_is_left_out(self):
		field = frappe.get_meta("Alvoraa Payroll Rule Set").get_field("night_green_for_everyone")
		self.assertIn("Earn Marks", field.label)
		self.assertIn("Contract", field.description)

	def test_with_the_tick_on_a_contract_person_earns_no_green_at_all(self):
		rs = _rule_set(night_green_for_everyone=1, categories=[CONTRACT],
		               overtime_bands=BANDS)
		day = getdate(nowdate())
		flags = _employee_flags(_employee("Contract"), day, prepare(rs, day, day))
		self.assertFalse(flags["earns_marks"])
		from alvoraa_portal.payroll_rules import evaluate_day
		v = evaluate_day(shift_start=630, shift_end=1230, first_in=500, last_out=1510,
		                 punch_count=2, slabs=prepare(rs, day, day)["slabs"], **flags)
		self.assertEqual((v.greens, v.overtime_quarters), (0, 0))


class TheCardDoesNotOfferWhatCannotBeEarned(FrappeTestCase):
	def _green(self, employment_type):
		day = getdate(nowdate())
		rs = _rule_set(night_green_for_everyone=1, categories=[CONTRACT])
		emp = _employee(employment_type)
		return _green(day_rules_on(emp, day, rs), 630, 1230, [])

	def test_a_contract_person_sees_no_green(self):
		self.assertFalse(self._green("Contract")["eligible"])

	def test_a_permanent_person_sees_the_night_green(self):
		out = self._green("Permanent")
		self.assertTrue(out["eligible"])
		self.assertEqual(out["night"]["after"], "21:30")


class ANightJudgedFromRealPunches(FrappeTestCase):
	"""Punches on two calendar dates, one shift day. A wall clock would read the
	01:10 punch as minute 70."""

	def setUp(self):
		if not frappe.db.exists("Shift Type", SHIFT):
			frappe.get_doc({"doctype": "Shift Type", "name": SHIFT,
			                "start_time": "10:30:00", "end_time": "20:30:00"}
			               ).insert(ignore_permissions=True)
		self.d1 = getdate(add_days(nowdate(), -20))
		self.d2 = add_days(self.d1, 1)

	def _punch(self, emp, when, shift_start):
		doc = frappe.get_doc({"doctype": "Employee Checkin", "employee": emp,
		                      "time": when, "log_type": ""})
		doc.insert(ignore_permissions=True)
		frappe.db.set_value("Employee Checkin", doc.name, "shift_start", shift_start,
		                    update_modified=False)

	def _night(self, employment_type, out):
		rs = _rule_set(overtime_bands=BANDS, night_green_for_everyone=1,
		               categories=[CONTRACT])
		emp = _employee(employment_type)
		start = "{0} 10:30:00".format(self.d1)
		self._punch(emp, "{0} 10:30:00".format(self.d1), start)
		self._punch(emp, out, start)
		att = frappe._dict(name="X", employee=emp, attendance_date=self.d1,
		                   status="Present", shift=SHIFT)
		return judge(att, prepare(rs, self.d1, self.d2))

	def test_a_ten_past_one_punch_on_the_next_date_pays_two_quarters(self):
		v = self._night("Permanent", "{0} 01:10:00".format(self.d2))
		self.assertFalse(v.held)
		self.assertEqual((v.overtime_quarters, v.greens), (2, 1))
		# The reason names the clock time the engine read: only true if the next-date
		# punch reached it as minute 1510, not 70.
		self.assertIn("last punch 01:10, 2 quarter(s)", " ".join(v.reasons))

	def test_ten_past_three_pays_the_full_four(self):
		v = self._night("Permanent", "{0} 03:10:00".format(self.d2))
		self.assertEqual(v.overtime_quarters, 4)
		self.assertIn("last punch 03:10, 4 quarter(s)", " ".join(v.reasons))

	def test_the_daily_report_row_carries_the_day_s_overtime(self):
		from alvoraa_portal.alvoraa_portal.report.daily_attendance_workings import (
			daily_attendance_workings as daily)
		rs = _rule_set(overtime_bands=BANDS, night_green_for_everyone=1)
		emp = _employee("Permanent")
		start = "{0} 10:30:00".format(self.d1)
		self._punch(emp, start, start)
		self._punch(emp, "{0} 01:10:00".format(self.d2), start)
		ctx = prepare(rs, self.d1, self.d2)
		att = frappe._dict(name="X", employee=emp, attendance_date=self.d1, status="Present",
		                   shift=SHIFT, company=COMPANY)
		att.get = lambda k, d=None: att[k] if k in att else d
		who = frappe._dict(name=emp, employee_name="T", company=COMPANY, default_shift=SHIFT,
		                   date_of_joining=None, relieving_date=None)
		row = daily._day(str(self.d1), who, att, ctx, {}, {})
		self.assertEqual(row["overtime"], 2)

	def test_a_contract_person_who_stays_that_late_earns_nothing_extra(self):
		v = self._night("Contract", "{0} 01:10:00".format(self.d2))
		self.assertFalse(v.held)
		self.assertEqual((v.overtime_quarters, v.greens), (0, 0))

	def test_leaving_at_ten_pm_earns_a_green_but_no_overtime(self):
		v = self._night("Permanent", "{0} 22:00:00".format(self.d1))
		self.assertEqual((v.overtime_quarters, v.greens), (0, 1))


class TheReportsCarryTheFigures(FrappeTestCase):
	"""A blank Overtime pay column beside a Gross that contains it is the worst way
	this can fail, so the values are asserted, not only the column names."""

	def test_the_salary_row_carries_both_overtime_figures(self):
		from alvoraa_portal.alvoraa_portal.report.salary_components_and_workings import (
			salary_components_and_workings as salary)
		from alvoraa_portal.payroll_month import MonthSummary
		emp = frappe._dict(name="E", employee_name="T", branch="B", department="D",
		                   employment_type="Permanent")
		row = salary._row(emp, MonthSummary(overtime_quarters=6, daily_rate=1000.0,
		                                    overtime_earning=1500.0))
		self.assertEqual(row["overtime_quarters"], 6)
		self.assertEqual(row["overtime_earning"], 1500.0)

	def test_the_daily_month_row_carries_the_total(self):
		from alvoraa_portal.alvoraa_portal.report.daily_attendance_workings import (
			daily_attendance_workings as daily)
		from alvoraa_portal.payroll_month import MonthSummary
		total = daily._totals([], MonthSummary(overtime_quarters=6))
		self.assertEqual(total["overtime"], 6)


class TheReportsCarryTheColumns(FrappeTestCase):
	def test_both_workings_reports_have_their_overtime_columns(self):
		from alvoraa_portal.alvoraa_portal.report.daily_attendance_workings import (
			daily_attendance_workings as daily)
		from alvoraa_portal.alvoraa_portal.report.salary_components_and_workings import (
			salary_components_and_workings as salary)
		self.assertIn("overtime", [c["fieldname"] for c in daily._columns()])
		names = [c["fieldname"] for c in salary._columns()]
		self.assertIn("overtime_quarters", names)
		self.assertIn("overtime_earning", names)
