"""Slice 063: the pay engine's half-day leave rule, E6, and OD-1 remedy (iv).

Pure functions, no site. Each test names the decision it pins, so a bad merge
that drops the rule fails here rather than on a payslip.

Surbhi, 21 Oct 2026 (01d D1-D5, the final answers, OD-1 answered):
- a half-day leave counts as 0.5 leave; the other half is measured by punches
  against HALF the shift, losing at most two quarters before any doubling;
- no late, early or late-window charge and no green mark on that day;
- no complete pair of punches: the other half is absent, doubled on a special
  day - unless HR approved a half-day correction, which counts it as worked;
- approved Paid Leaves days count toward the 15-day gate (E6);
- an automatic "Half Day" with no leave behind it is judged as before.
"""

import unittest

from alvoraa_portal.payroll_month import summarise_month
from alvoraa_portal.payroll_rules import DayVerdict, evaluate_day
from alvoraa_portal.tests.test_payroll_rules import (
	DTC_SLABS,
	SHIFT_END,
	SHIFT_START,
	WINDOW_FROM,
	WINDOW_TO,
	hm,
)


def half(**kwargs):
	"""A half-day leave day on DTC's standing configuration (10:30-20:30)."""
	args = dict(
		shift_start=SHIFT_START,
		shift_end=SHIFT_END,
		punch_count=2,
		grace_minutes=6,
		slabs=DTC_SLABS,
		special_day_multiplier=2,
		double_deduction_applies=True,
		late_window_from=WINDOW_FROM,
		late_window_to=WINDOW_TO,
		late_window_extra_quarters=1,
		late_window_flagged=True,
		night_green_eligible=True,
		half_day_leave=True,
	)
	args.update(kwargs)
	return evaluate_day(**args)


class TestTheOtherHalfIsMeasuredByPunches(unittest.TestCase):
	def test_a_full_worked_half_loses_nothing_and_pays_half_a_day(self):
		"""Morning off, in at 15:30, out at 20:30: 300 of 300 minutes."""
		v = half(first_in=hm(15, 30), last_out=hm(20, 30))
		self.assertTrue(v.half_leave)
		self.assertEqual(v.total_quarters, 0)
		self.assertEqual(v.reds, 0)
		self.assertEqual(v.day_credit, 0.5)

	def test_arriving_late_or_leaving_early_is_not_charged(self):
		"""D3: either may be the leave itself. In at 11:15 (inside the late
		window, past grace) and out at 16:15 - a full half, nothing charged."""
		v = half(first_in=hm(11, 15), last_out=hm(16, 15))
		self.assertFalse(v.late_arrival)
		self.assertFalse(v.early_departure)
		self.assertFalse(v.late_window_hit)
		self.assertEqual(v.extra_quarters, 0)
		self.assertEqual(v.total_quarters, 0)

	def test_no_green_mark_on_a_half_day_leave_day(self):
		"""D4: even when the punches would earn both greens on a full day."""
		v = half(first_in=hm(8, 0), last_out=hm(22, 0))
		self.assertEqual(v.greens, 0)

	def test_a_short_half_is_charged_from_the_slab_on_half_the_shift(self):
		"""150 of 300 minutes is 50%: the 50-65% row, 2 quarters, no red."""
		v = half(first_in=hm(15, 30), last_out=hm(18, 0))
		self.assertAlmostEqual(v.attendance_percent, 50.0)
		self.assertEqual(v.slab_quarters, 2)
		self.assertEqual(v.day_credit, 0.0)

	def test_a_half_never_loses_more_than_two_quarters(self):
		"""30 of 300 minutes is 10%: the slab says 4, a half is worth 2."""
		v = half(first_in=hm(15, 30), last_out=hm(16, 0))
		self.assertEqual(v.slab_quarters, 2)
		self.assertEqual(v.day_credit, 0.0)

	def test_a_red_comes_only_from_the_slab(self):
		"""66% of the half lands in the 65-68% red row: one quarter, one red."""
		v = half(first_in=hm(15, 30), last_out=hm(15, 30) + 198)
		self.assertEqual(v.slab_quarters, 1)
		self.assertEqual(v.reds, 1)

	def test_contract_staff_take_no_red_on_the_half_either(self):
		v = half(first_in=hm(15, 30), last_out=hm(15, 30) + 198, earns_marks=False)
		self.assertEqual(v.reds, 0)
		self.assertEqual(v.slab_quarters, 1)


class TestAMissingPunch(unittest.TestCase):
	def test_no_punches_means_the_other_half_is_absent(self):
		"""D5: 0.5 leave and 0.5 absent - unpaid, nothing charged on top."""
		v = half(first_in=None, last_out=None, punch_count=0)
		self.assertTrue(v.absent)
		self.assertEqual(v.slab_quarters, 2)
		self.assertEqual(v.day_credit, 0.0)

	def test_one_punch_is_absent_too_not_held(self):
		"""E-b, confirmed 21 Oct: unlike a full one-punch day, which is held."""
		v = half(first_in=hm(15, 30), last_out=None, punch_count=1)
		self.assertTrue(v.absent)
		self.assertFalse(v.held)

	def test_an_absent_half_on_a_special_day_costs_half_a_day_more(self):
		"""Doubled to 4 quarters: 2 are 'above' the half itself."""
		v = half(first_in=None, last_out=None, punch_count=0, is_special_day=True)
		self.assertTrue(v.doubled)
		self.assertEqual(v.slab_quarters, 4)
		self.assertEqual(v.day_credit, -0.5)

	def test_contract_staff_are_not_doubled(self):
		v = half(first_in=None, last_out=None, punch_count=0, is_special_day=True,
		         double_deduction_applies=False)
		self.assertFalse(v.doubled)
		self.assertEqual(v.day_credit, 0.0)

	def test_a_short_half_on_a_special_day_is_capped_then_doubled(self):
		"""E-a: cap at 2 first, so the worst worked half equals an absent one."""
		v = half(first_in=hm(15, 30), last_out=hm(16, 0), is_special_day=True)
		self.assertEqual(v.slab_quarters, 4)
		self.assertEqual(v.day_credit, -0.5)


class TestOD1RemedyFour(unittest.TestCase):
	"""Surbhi, 21 Oct 2026: 'just by half day attendance regularization, if
	feasible, no attendance punches required.'"""

	def test_an_approved_correction_counts_the_half_as_worked(self):
		v = half(first_in=None, last_out=None, punch_count=0, other_half_regularised=True)
		self.assertFalse(v.absent)
		self.assertEqual(v.total_quarters, 0)
		self.assertEqual(v.day_credit, 0.5)
		self.assertEqual(v.greens, 0)

	def test_it_also_lifts_the_special_day_charge(self):
		v = half(first_in=hm(15, 30), last_out=None, punch_count=1, is_special_day=True,
		         other_half_regularised=True)
		self.assertFalse(v.doubled)
		self.assertEqual(v.day_credit, 0.5)

	def test_it_does_not_override_punches_that_are_there(self):
		"""Two punches are measured as usual; the correction is for a MISSING
		punch, not a way to erase a short half."""
		v = half(first_in=hm(15, 30), last_out=hm(18, 0), other_half_regularised=True)
		self.assertEqual(v.slab_quarters, 2)


class TestAHalfDayWithNoLeaveIsUnchanged(unittest.TestCase):
	def test_without_the_flag_the_day_is_judged_as_a_full_day(self):
		"""An automatic 'Half Day' from a short shift (DTC has 22 such rows):
		the engine reads it as a short working day, exactly as before."""
		v = half(first_in=hm(10, 30), last_out=hm(15, 30), half_day_leave=False)
		self.assertFalse(v.half_leave)
		self.assertAlmostEqual(v.attendance_percent, 50.0)
		self.assertEqual(v.slab_quarters, 2)


# ── the month ────────────────────────────────────────────────────────────────

CLASS_A = dict(period_days=15.0, credit_per_period=4.0, monthly_cap=4.0,
               threshold_days=15, accrual_month_days=15)


def worked():
	return DayVerdict()


def half_day(**kwargs):
	return half(first_in=hm(15, 30), last_out=hm(20, 30), **kwargs)


def month(days, **kwargs):
	args = dict(basic=31000, month_days=31)
	args.update(CLASS_A)
	args.update(kwargs)
	return summarise_month(days, **args)


class TestHalvesInTheMonth(unittest.TestCase):
	def test_a_half_day_leave_is_half_worked_and_half_leave(self):
		m = month([worked() for _ in range(20)] + [half_day()])
		self.assertEqual(m.days_worked, 20.5)
		self.assertEqual(m.days_on_leave, 0.5)
		self.assertEqual(m.day_credits, 20.5)

	def test_an_absent_half_is_counted_as_half_absent(self):
		m = month([worked() for _ in range(20)]
		          + [half(first_in=None, last_out=None, punch_count=0)])
		self.assertEqual(m.days_absent, 0.5)
		self.assertEqual(m.days_worked, 20)

	def test_the_gate_reads_halves(self):
		"""D2: a half-day leave is 0.5 attended. 14 + a half = 14.5, under 15."""
		under = month([worked() for _ in range(14)] + [half_day()])
		self.assertEqual(under.leave_credits_earned, 0.0)
		met = month([worked() for _ in range(14)] + [half_day(), half_day()])
		self.assertEqual(met.days_for_gate, 15.0)
		self.assertEqual(met.leave_credits_earned, 4.0)

	def test_a_half_day_lwp_pays_the_same_as_a_half_day_paid_leave(self):
		"""The engine is type-blind on the day; only the used split differs."""
		lwp = month([worked() for _ in range(20)] + [half_day()], approved_leave_days=0)
		paid = month([worked() for _ in range(20)] + [half_day()], approved_leave_days=0.5)
		self.assertEqual(lwp.paid_days, paid.paid_days)
		self.assertEqual(paid.leave_used_for_approved, 0.5)
		self.assertEqual(lwp.leave_used_for_approved, 0.0)


class TestE6(unittest.TestCase):
	"""E6, Surbhi 21 Oct 2026: approved Paid Leaves days count toward the 15."""

	def test_thirteen_worked_and_two_approved_paid_leaves_reach_the_gate(self):
		m = month([worked() for _ in range(13)], approved_leave_days=2)
		self.assertEqual(m.days_for_gate, 15)
		self.assertEqual(m.leave_credits_earned, 4.0)
		self.assertEqual(m.leave_used_for_approved, 2.0)
		self.assertEqual(m.leave_encashed, 2.0)
		self.assertEqual(m.paid_days, 13 + 4)

	def test_open_requests_do_not_count(self):
		"""An Open request has no attendance and is not passed in."""
		m = month([worked() for _ in range(13)], approved_leave_days=0)
		self.assertEqual(m.leave_credits_earned, 0.0)

	def test_a_person_with_no_paid_leaves_is_paid_as_before(self):
		before = month([worked() for _ in range(20)])
		after = month([worked() for _ in range(20)], approved_leave_days=0)
		self.assertEqual(before.paid_days, after.paid_days)


if __name__ == "__main__":
	unittest.main()
