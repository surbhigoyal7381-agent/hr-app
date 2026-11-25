"""Slice 091: overtime paid by the time of the last punch, for DTC.

The rule, settled by Surbhi on 24 Nov 2026 ("a milestone passed"): once the last
punch is AT OR AFTER 23:00 the day earns 1 quarter, at or after 01:00 it earns
2, at or after 03:00 it earns 4. These are TOTALS, so the steps are uneven on
purpose (+1, +2, +4). Nothing counts before shift end + 60 minutes, per person.

Times are minutes from the SHIFT DAY's midnight, the clock `punch_minutes` puts a
last punch on (ALV-402): 01:00 the next morning is 1500. These run as plain unit
tests, like `test_payroll_rules`, because the engine touches no database.
"""

import unittest

from alvoraa_portal.payroll_month import summarise_month
from alvoraa_portal.payroll_rules import evaluate_day, overtime_quarters_for

from alvoraa_portal.tests.test_payroll_rules import DTC_SLABS, SHIFT_END, SHIFT_START, hm

# DTC's table as prepare() hands it over: (edge in shift-day minutes, total quarters).
BANDS = [(hm(23), 1), (hm(25), 2), (hm(27), 4)]


def day(last_out, **kwargs):
	args = dict(shift_start=SHIFT_START, shift_end=SHIFT_END, first_in=SHIFT_START,
	            last_out=last_out, punch_count=2, grace_minutes=6, slabs=DTC_SLABS,
	            special_day_multiplier=2, overtime_bands=BANDS,
	            night_green_eligible=True, morning_green_eligible=True)
	args.update(kwargs)
	return evaluate_day(**args)


class TheBandEdges(unittest.TestCase):
	def test_each_edge_minute_pays_what_the_table_says(self):
		cases = [((22, 59), 0), ((23, 0), 1), ((23, 1), 1), ((24, 59), 1),
		         ((25, 0), 2), ((25, 1), 2), ((26, 59), 2),
		         ((27, 0), 4), ((27, 1), 4), ((28, 0), 4)]
		for (h, m), quarters in cases:
			self.assertEqual(day(hm(h, m)).overtime_quarters, quarters, "%02d:%02d" % (h % 24, m))

	def test_the_steps_are_the_uneven_ones_she_set(self):
		self.assertEqual([day(hm(h)).overtime_quarters for h in (23, 25, 27)], [1, 2, 4])

	def test_the_worked_examples_she_agreed_to(self):
		got = {t: day(hm(*t)).overtime_quarters
		       for t in ((21, 0), (23, 0), (24, 30), (25, 0), (26, 0), (27, 0), (28, 30))}
		self.assertEqual(got, {(21, 0): 0, (23, 0): 1, (24, 30): 1, (25, 0): 2,
		                       (26, 0): 2, (27, 0): 4, (28, 30): 4})

	def test_a_wall_clock_would_get_a_ten_past_one_punch_wrong(self):
		"""01:10 the next morning is minute 1510 of the shift day. Read as a wall
		clock it is minute 70, before every band, and pays nothing."""
		self.assertEqual(day(hm(25, 10)).overtime_quarters, 2)
		self.assertEqual(overtime_quarters_for(hm(1, 10), SHIFT_END, BANDS), 0)

	def test_the_order_of_the_rows_does_not_matter(self):
		self.assertEqual(overtime_quarters_for(hm(26, 20), SHIFT_END, list(reversed(BANDS))), 2)
		self.assertEqual(overtime_quarters_for(hm(28), SHIFT_END, [BANDS[2], BANDS[0], BANDS[1]]), 4)

	def test_an_empty_table_means_no_overtime(self):
		self.assertEqual(day(hm(26), overtime_bands=[]).overtime_quarters, 0)


class TheGateIsPerPerson(unittest.TestCase):
	def test_nothing_counts_before_shift_end_plus_sixty(self):
		# A 10:30-20:30 shift: gate 21:30. A low band proves the gate, not the table.
		low = [(hm(21), 1)]
		self.assertEqual(overtime_quarters_for(SHIFT_END + 59, SHIFT_END, low), 0)
		self.assertEqual(overtime_quarters_for(SHIFT_END + 60, SHIFT_END, low), 1)

	def test_the_night_green_and_overtime_share_the_same_gate(self):
		for minute, green, quarters in ((SHIFT_END + 59, 0, 0), (SHIFT_END + 60, 1, 0)):
			v = day(minute)
			self.assertEqual((v.greens, v.overtime_quarters), (green, quarters))
		v = day(hm(23, 5))
		self.assertEqual((v.greens, v.overtime_quarters), (1, 1), "both are paid")

	def test_a_ten_pm_shift_cannot_earn_before_eleven(self):
		self.assertEqual(day(hm(22, 59), shift_end=hm(22)).overtime_quarters, 0)
		self.assertEqual(day(hm(23, 0), shift_end=hm(22)).overtime_quarters, 1)


class WhoNeverEarnsIt(unittest.TestCase):
	def test_a_category_with_no_marks_earns_none(self):
		v = day(hm(26), earns_marks=False)
		self.assertEqual((v.overtime_quarters, v.greens), (0, 0))

	def test_a_permanent_day_still_earns(self):
		self.assertEqual(day(hm(26), earns_marks=True).overtime_quarters, 2)

	def test_a_time_a_person_typed_never_pays(self):
		"""One punch confirmed by HR at 01:30, and three punches the same."""
		one = day(None, first_in=SHIFT_START, punch_count=1, confirmed_out=hm(25, 30))
		three = day(hm(24), punch_count=3, confirmed_out=hm(25, 30))
		self.assertEqual((one.overtime_quarters, three.overtime_quarters), (0, 0))
		self.assertFalse(one.held or three.held)

	def test_a_time_a_person_typed_pays_no_night_green_either(self):
		"""Surbhi, 25 Nov 2026: neither the green nor overtime. A real punch at the
		same time pays both, so the guard is the typed time and nothing else."""
		one = day(None, first_in=SHIFT_START, punch_count=1, confirmed_out=hm(25, 30))
		three = day(hm(24), punch_count=3, confirmed_out=hm(25, 30))
		for v in (one, three):
			self.assertEqual((v.greens, v.overtime_quarters), (0, 0))
			self.assertIn("No night green", " ".join(v.reasons))
		real = day(hm(25, 30))
		self.assertEqual((real.greens, real.overtime_quarters), (1, 2))

	def test_a_held_absent_or_leave_day_earns_none(self):
		self.assertEqual(day(None, punch_count=1).overtime_quarters, 0)
		self.assertEqual(day(None, first_in=None, punch_count=0,
		                     marked_absent=True).overtime_quarters, 0)
		self.assertEqual(day(None, first_in=None, punch_count=0,
		                     marked_on_leave=True).overtime_quarters, 0)
		self.assertEqual(day(hm(26), half_day_leave=True).overtime_quarters, 0)


class OvertimeIsEarnedNotLost(unittest.TestCase):
	def test_it_is_not_inside_the_quarters_lost_and_day_credit_ignores_it(self):
		on_time = day(hm(20, 30))
		late_stay = day(hm(26))
		self.assertEqual(late_stay.total_quarters, on_time.total_quarters)
		self.assertEqual(late_stay.day_credit, on_time.day_credit)
		self.assertLessEqual(late_stay.day_credit, 1.0)

	def test_a_day_that_lost_a_quarter_and_earned_two_is_worth_one_and_a_quarter(self):
		# 11:30 arrival is 60 min late: one quarter lost on the late rule.
		v = day(hm(26), first_in=hm(11, 30), late_quarter_after_minutes=30,
		        shift_hours_only=True)
		self.assertEqual(v.total_quarters, 1)
		self.assertEqual(v.day_credit, 0.75)
		self.assertEqual(v.overtime_quarters, 2)
		self.assertEqual(v.day_credit + v.overtime_quarters / 4.0, 1.25)

	def test_a_special_day_never_doubles_it(self):
		v = day(hm(26), is_special_day=True, double_deduction_applies=True)
		self.assertEqual(v.overtime_quarters, 2)

	def test_the_reason_line_says_what_was_paid(self):
		self.assertIn("Overtime: last punch 01:10, 2 quarter(s)", " ".join(day(hm(25, 10)).reasons))


class TheMonthMoney(unittest.TestCase):
	BASIC, DAYS = 30000, 30

	def month(self, verdicts):
		return summarise_month(verdicts, basic=self.BASIC, month_days=self.DAYS)

	def test_gross_rises_by_exactly_the_overtime_and_net_adds_it_once(self):
		plain = [day(hm(20, 30)) for _ in range(3)]
		with_ot = [day(hm(20, 30)), day(hm(25, 10)), day(hm(27, 30))]
		a, b = self.month(plain), self.month(with_ot)
		self.assertEqual(b.overtime_quarters, 6)
		self.assertAlmostEqual(b.overtime_earning, 6 / 4.0 * 1000.0)
		# The night greens both days add green pay only if a mark rate is given: none here.
		self.assertAlmostEqual(b.gross - a.gross, b.overtime_earning)
		self.assertAlmostEqual(b.net - a.net, b.overtime_earning)
		self.assertEqual(b.paid_days, a.paid_days, "Basic earned does not move")
		self.assertEqual(b.total_quarters, a.total_quarters)

	def test_running_the_same_month_twice_gives_the_same_money(self):
		v = [day(hm(25, 10)), day(hm(24))]
		self.assertEqual(self.month(v).gross, self.month(v).gross)
		self.assertEqual(self.month(v).overtime_earning, self.month(v).overtime_earning)

	def test_a_person_with_no_overtime_has_none(self):
		m = self.month([day(hm(20, 30))])
		self.assertEqual((m.overtime_quarters, m.overtime_earning), (0, 0.0))


if __name__ == "__main__":
	unittest.main()
