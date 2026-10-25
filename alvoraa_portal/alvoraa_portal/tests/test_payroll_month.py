"""The monthly roll-up, tested against the client's own worked examples.

`summarise_month` touches no database, so these run as plain unit tests. Where
a case comes from the PP Jewellers rule-by-rule document or a decision recorded
in the addendum, the test says so and uses those figures.
"""

import unittest

from alvoraa_portal.payroll_month import summarise_month
from alvoraa_portal.payroll_rules import DayVerdict

# DTC's class A as set on 21 Oct 2026 (slice 063, 01e): the whole 4 days are
# given on the 1st and count once 15 days are attended - one 15-day period
# worth all four, counting stopping at 15. The 9 Oct accrual cadence
# (7.5 / 1 / 4 over a 30-day calendar) is still tested in test_payroll_rules.
CLASS_A = dict(period_days=15.0, credit_per_period=4.0, monthly_cap=4.0,
               threshold_days=15, accrual_month_days=15)
CLASS_B = dict(period_days=10.0, credit_per_period=1.0, monthly_cap=3.0,
               threshold_days=15, accrual_month_days=30)


def worked(quarters=0, reds=0, greens=0):
	v = DayVerdict()
	v.slab_quarters = quarters
	v.reds = reds
	v.greens = greens
	return v


def absent(quarters=4):
	v = DayVerdict()
	v.absent = True
	v.slab_quarters = quarters
	return v


def held():
	v = DayVerdict()
	v.held = True
	return v


def on_leave():
	v = DayVerdict()
	v.on_leave = True
	return v


def month(days, **kwargs):
	args = dict(basic=23000, month_days=30, free_reds=2, mark_rate=100)
	args.update(CLASS_A)
	args.update(kwargs)
	return summarise_month(days, **args)


class TestCounting(unittest.TestCase):
	def test_the_three_kinds_of_day_are_counted_apart(self):
		m = month([worked() for _ in range(20)] + [absent() for _ in range(5)] + [held() for _ in range(3)])
		self.assertEqual(m.days_with_record, 28)
		self.assertEqual(m.days_worked, 20)
		self.assertEqual(m.days_absent, 5)
		self.assertEqual(m.days_held, 3)

	def test_a_held_day_is_neither_paid_nor_deducted(self):
		"""ATT-06. It is released later as an Arrear, so netting it off here
		would settle a question nobody has answered."""
		without = month([worked() for _ in range(20)])
		with_held = month([worked() for _ in range(20)] + [held() for _ in range(5)])
		self.assertEqual(with_held.paid_days, without.paid_days)
		self.assertEqual(with_held.total_quarters, without.total_quarters)

	def test_the_held_days_are_called_out_in_the_notes(self):
		m = month([worked() for _ in range(20)] + [held() for _ in range(3)])
		self.assertIn("3 day(s) held", " ".join(m.notes))

	def test_marks_only_come_from_days_that_were_worked(self):
		m = month([worked(reds=1) for _ in range(10)] + [absent() for _ in range(5)] + [held() for _ in range(2)])
		self.assertEqual(m.reds, 10)


class TestPaidDays(unittest.TestCase):
	def test_a_perfect_month_earns_more_than_the_month_itself(self):
		"""GBL-06: there are no weekly offs, so the credits are payment for
		days the employee could have taken off and did not. 30 worked plus 4
		credits is 34 paid days in a 30-day month, which is correct and will
		still surprise somebody reading a payslip."""
		m = month([worked() for _ in range(30)])
		self.assertEqual(m.days_worked, 30)
		self.assertEqual(m.leave_credits_earned, 4.0)
		self.assertEqual(m.paid_days, 34.0)

	def test_a_partial_day_is_paid_for_the_part_that_was_worked(self):
		"""Correction C-1. A 70% day carrying one quarter pays 0.75, not zero,
		and is certainly not docked further."""
		m = month([worked(quarters=1)])
		self.assertEqual(m.days_worked, 1)
		self.assertEqual(m.day_credits, 0.75)

	def test_a_plain_absence_costs_exactly_one_day(self):
		"""Not two. The day is already unpaid by not being worked; charging
		four quarters as well would dock it twice."""
		m = month([worked() for _ in range(20)] + [absent(quarters=4)])
		self.assertEqual(m.day_credits, 20.0)

	def test_an_absence_on_a_special_day_costs_two(self):
		"""WSD-04. Doubled to eight quarters: four are 'above' the day itself,
		so one extra day comes off."""
		m = month([worked() for _ in range(20)] + [absent(quarters=8)])
		self.assertEqual(m.day_credits, 19.0)

	def test_a_few_days_in_a_month_pays_for_those_days_only(self):
		"""Surbhi, 9 October 2026. Ten days worked, under the 15-day gate."""
		m = month([worked() for _ in range(10)])
		self.assertEqual(m.leave_credits_earned, 0.0)
		self.assertEqual(m.paid_days, 10.0)
		self.assertAlmostEqual(m.earning_basic, 10 * (23000 / 30), places=2)
		self.assertIn("under the 15-day gate", " ".join(m.notes))


class TestApprovedLeaveDays(unittest.TestCase):
	"""An approved leave day is neither an absence nor a mystery.

	Before this, a leave day had no punches and was not marked absent, so it
	fell through to the held branch - which reads as "nobody can say what
	happened" about a day somebody had explicitly approved. It would then sit
	waiting for a manager to confirm a day that was never in doubt.
	"""

	def test_a_leave_day_is_counted_as_leave_not_held(self):
		m = month([worked() for _ in range(20)] + [on_leave() for _ in range(2)])
		self.assertEqual(m.days_on_leave, 2)
		self.assertEqual(m.days_held, 0)
		self.assertEqual(m.days_absent, 0)

	def test_a_leave_day_costs_no_quarters_and_earns_no_marks(self):
		m = month([worked() for _ in range(20)] + [on_leave() for _ in range(3)])
		self.assertEqual(m.total_quarters, 0)
		self.assertEqual(m.reds, 0)

	def test_a_leave_day_is_not_a_day_worked(self):
		"""It must not count towards the 15-day gate, or leave would earn the
		credit that pays for it."""
		m = month([worked() for _ in range(14)] + [on_leave() for _ in range(5)])
		self.assertEqual(m.days_worked, 14)
		self.assertEqual(m.leave_credits_earned, 0.0)

	def test_leave_taken_is_read_from_the_attendance_itself(self):
		"""Derived rather than passed in. A hand-entered figure can disagree
		with the records it is meant to describe."""
		m = month([worked() for _ in range(30)] + [on_leave()])
		self.assertEqual(m.days_on_leave, 1)
		self.assertEqual(m.leave_used_for_approved, 1.0)
		self.assertEqual(m.leave_encashed, 3.0)

	def test_an_explicit_figure_still_overrides(self):
		m = month([worked() for _ in range(30)], approved_leave_days=2)
		self.assertEqual(m.leave_used_for_approved, 2.0)


class TestEncashmentAgainstApprovedLeave(unittest.TestCase):
	"""LB-02 and LB-03. Credits cover approved leave first; the surplus is cash."""

	def test_no_leave_taken_means_every_credit_is_cash(self):
		m = month([worked() for _ in range(30)], approved_leave_days=0)
		self.assertEqual(m.leave_credits_earned, 4.0)
		self.assertEqual(m.leave_used_for_approved, 0.0)
		self.assertEqual(m.leave_encashed, 4.0)

	def test_one_leave_day_consumes_one_credit(self):
		"""The document's own example: 4 credits, 1 leave taken, 3 encashed.
		Thirty worked days plus one leave day is a real 31-day month."""
		m = month([worked() for _ in range(30)], month_days=31,
		          approved_leave_days=1)
		self.assertEqual(m.leave_credits_earned, 4.0)
		self.assertEqual(m.leave_used_for_approved, 1.0)
		self.assertEqual(m.leave_encashed, 3.0)

	def test_taking_leave_does_not_change_paid_days(self):
		"""A day covered by a credit is paid, and a surplus credit adds a day -
		both are worth one day. So the split between used and encashed is for
		the payslip to show, not something to subtract twice.

		FLAGGED FOR DTC: the document's Anil example leaves the leave day out of
		present days AND out of the encashment, which drops it unpaid. This
		follows correction C-1 instead."""
		none_taken = month([worked() for _ in range(29)], approved_leave_days=0)
		one_taken = month([worked() for _ in range(29)], approved_leave_days=1)
		self.assertEqual(one_taken.paid_days, none_taken.paid_days)

	def test_leave_beyond_the_credits_is_unpaid(self):
		"""Six days taken against 24 worked: the gate is met and the class
		gives 4. Four credits fund four of the days; the other two have
		nothing."""
		m = month([worked() for _ in range(24)], approved_leave_days=6)
		self.assertEqual(m.leave_credits_earned, 4.0)
		self.assertEqual(m.leave_used_for_approved, 4.0)
		self.assertEqual(m.leave_encashed, 0.0)
		self.assertEqual(m.approved_leave_unpaid, 2.0)
		self.assertIn("unpaid", " ".join(m.notes))

	def test_leave_cannot_be_funded_below_the_gate(self):
		"""No credits exist, so nothing covers the leave."""
		m = month([worked() for _ in range(10)], approved_leave_days=2)
		self.assertEqual(m.leave_credits_earned, 0.0)
		self.assertEqual(m.leave_used_for_approved, 0.0)
		self.assertEqual(m.approved_leave_unpaid, 2.0)


class TestMarks(unittest.TestCase):
	"""RED-01 and RED-03."""

	def test_two_reds_a_month_cost_nothing(self):
		m = month([worked(reds=1) for _ in range(2)])
		self.assertEqual(m.reds, 2)
		self.assertEqual(m.deductible_reds, 0)
		self.assertEqual(m.red_deduction, 0)

	def test_the_documents_red_example(self):
		"""Five reds, junior grade: 5 - 2 = 3 deductible, 3 x 100 = 300."""
		m = month([worked(reds=1) for _ in range(5)])
		self.assertEqual(m.deductible_reds, 3)
		self.assertEqual(m.red_deduction, 300)

	def test_a_senior_pays_double_for_the_same_reds(self):
		m = month([worked(reds=1) for _ in range(5)], mark_rate=200)
		self.assertEqual(m.red_deduction, 600)

	def test_greens_are_added_and_never_offset_reds(self):
		"""RED-06 and GRN-04: separate line items, never netted."""
		m = month([worked(reds=1) for _ in range(5)] + [worked(greens=1) for _ in range(3)])
		self.assertEqual(m.red_deduction, 300)
		self.assertEqual(m.green_earning, 300)
		self.assertEqual(m.gross, m.earning_basic + 300)

	def test_a_category_that_carries_no_marks_pays_neither(self):
		m = month([worked(reds=1, greens=1) for _ in range(20)], earns_marks=False)
		self.assertEqual(m.reds, 0)
		self.assertEqual(m.greens, 0)
		self.assertEqual(m.red_deduction, 0)
		self.assertEqual(m.green_earning, 0)


class TestContractStaff(unittest.TestCase):
	def test_quarters_still_reduce_pay_but_no_leave_is_earned(self):
		"""Settled 9 October 2026. Twenty days worked, four of them short by a
		quarter: paid for the days, docked for the time, no class."""
		m = month([worked() for _ in range(16)] + [worked(quarters=1) for _ in range(4)],
		          earns_leave_credits=False, earns_marks=False)
		self.assertEqual(m.leave_credits_earned, 0.0)
		self.assertEqual(m.paid_days, 19.0)
		self.assertIn("earns no leave class", " ".join(m.notes))


class TestTheWholeSlip(unittest.TestCase):
	def test_a_complete_month_end_to_end(self):
		"""Class A, basic 23,000, 30-day month. Twenty-four days worked of
		which two lost a quarter each, three full absences, one of them on a
		special day, two held days, four reds, one green, one approved leave
		day taken."""
		days = ([worked() for _ in range(22)] + [worked(quarters=1) for _ in range(2)]
		        + [absent(quarters=4) for _ in range(2)] + [absent(quarters=8)]
		        + [held() for _ in range(2)])
		days[0].reds = 1
		days[1].reds = 1
		days[2].reds = 1
		days[3].reds = 1
		days[4].greens = 1
		m = month(days, approved_leave_days=1)

		self.assertEqual(m.days_worked, 24)
		self.assertEqual(m.days_absent, 3)
		self.assertEqual(m.days_held, 2)

		# 24 worked less 2 quarters (0.5 day), less 1 extra day for the
		# special-day absence.
		self.assertEqual(m.day_credits, 22.5)
		self.assertEqual(m.leave_credits_earned, 4.0)       # gate met -> the whole class
		self.assertEqual(m.leave_used_for_approved, 1.0)
		self.assertEqual(m.leave_encashed, 3.0)
		self.assertEqual(m.paid_days, 26.5)

		daily = 23000 / 30
		self.assertAlmostEqual(m.earning_basic, 26.5 * daily, places=2)
		self.assertEqual(m.deductible_reds, 2)              # 4 reds less 2 free
		self.assertEqual(m.red_deduction, 200)
		self.assertEqual(m.green_earning, 100)
		self.assertAlmostEqual(m.gross, 26.5 * daily + 100, places=2)
		self.assertAlmostEqual(m.net, 26.5 * daily + 100 - 200, places=2)

	def test_an_incentive_is_added_whole_and_never_prorated(self):
		"""INC-04: a flat amount from an external system."""
		m = month([worked() for _ in range(20)], incentive=5000)
		self.assertAlmostEqual(m.gross, m.earning_basic + 5000, places=2)

	def test_the_daily_rate_uses_the_real_month_length(self):
		"""GBL-02. No fixed 30-day divisor."""
		self.assertAlmostEqual(month([worked()], month_days=31).daily_rate,
		                       23000 / 31, places=4)
		self.assertAlmostEqual(month([worked()], month_days=28).daily_rate,
		                       23000 / 28, places=4)

	def test_an_empty_month_produces_zero_rather_than_an_error(self):
		m = month([])
		self.assertEqual(m.paid_days, 0.0)
		self.assertEqual(m.net, 0.0)


if __name__ == "__main__":
	unittest.main(verbosity=2)
