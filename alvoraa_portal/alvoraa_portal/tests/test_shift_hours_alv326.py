"""ALV-326: only shift hours count, a break allowance, and a late limit.

Three rule-set settings, tested as plain unit tests against the pure engine - no
bench, no site. EVERY DAY HERE IS MADE UP: the shifts and punch times are
invented to exercise one rule each. No real person's attendance is in this
file, and none may be added (security review B1, 2026-11-11).

The rules (the `payroll_rules` docstring has the reasons):

  - Only time inside the shift counts. Within grace counts from the start.
  - Breaks (gap 2-3, 4-5, ...) up to the allowance a day are free; beyond is
    deducted. An odd punch count deducts no break: a punch is missing.
  - Past grace and up to the late limit: 1 red. Beyond it: the larger of
    1 quarter and the band's quarters, and no red. A late red and a band red
    are one red, except the two-red rule (no-quarter red band, late and early).
  - Greens and the 11:00-11:30 late window (ATT-04) read the real punches.
"""

import unittest

from alvoraa_portal.payroll_rules import (
	break_gaps,
	collapse_duplicate_punches,
	evaluate_day,
)
from alvoraa_portal.tests.test_payroll_rules import DTC_SLABS, hm

# The figures under test. They are inputs here, set on a rule set in real life -
# never in the engine.
GRACE = 6
LATE_LIMIT = 30
BREAK_ALLOWANCE = 40


def mins(clock):
	h, m = clock.split(":")
	return int(h) * 60 + int(m)


def day(shift, punches, status="Present", **extra):
	"""One day through the engine, as `payroll_rules_apply.judge` hands it over,
	with all three settings on, no late window and no doubling."""
	start, end = (mins(t) for t in shift.split("-"))
	p = collapse_duplicate_punches([mins(t) for t in punches.split()])
	args = dict(
		shift_start=start, shift_end=end,
		first_in=p[0] if p else None, last_out=p[-1] if p else None,
		punch_count=len(p), marked_absent=(status == "Absent"),
		grace_minutes=GRACE, slabs=DTC_SLABS, special_day_multiplier=2,
		night_green_eligible=True, break_gaps=break_gaps(p),
		shift_hours_only=True, late_quarter_after_minutes=LATE_LIMIT,
		break_allowance_minutes=BREAK_ALLOWANCE,
	)
	args.update(extra)
	return evaluate_day(**args)


# Invented days, one rule each. (what it shows, shift, status, punches,
# quarters, reds, greens). Worked by hand before the engine was asked.
INVENTED_DAYS = [
	("on time, full day", "08:30-18:30", "Present", "08:25 18:35", 0, 0, 0),
	("5 late is inside grace, counts from 08:30", "08:30-18:30", "Present", "08:35 18:30", 0, 0, 0),
	("14 late: 1 red, the band red is the same red", "08:30-18:30", "Present", "08:44 18:30", 0, 1, 0),
	("35 late: 1 quarter, no red", "08:30-18:30", "Present", "09:05 18:40", 1, 0, 0),
	("130 late, 63%: the band's 2 quarters", "08:30-18:30", "Present", "10:40 17:00", 2, 0, 0),
	("20 late, 73%: a quarter and a red", "08:30-18:30", "Present", "08:50 16:10", 1, 1, 0),
	("on time, out 40 early, 93%: band red", "08:30-18:30", "Present", "08:30 17:50", 0, 1, 0),
	("on time, 75%: band quarter", "08:30-18:30", "Present", "08:30 16:00", 1, 0, 0),
	("35-minute break: free", "08:30-18:30", "Present", "08:30 12:30 13:05 18:30", 0, 0, 0),
	("60-minute break: 20 over, 96.7%, red", "08:30-18:30", "Present", "08:30 12:30 13:30 18:30", 0, 1, 0),
	("odd punch count: no break deducted", "08:30-18:30", "Present", "08:30 12:30 18:30", 0, 0, 0),
	("2 hours early: morning green", "08:30-18:30", "Present", "06:20 18:30", 0, 0, 1),
	("an hour late out: night green", "08:30-18:30", "Present", "08:30 19:45", 0, 0, 1),
	("absent, no punches", "10:00-18:30", "Absent", "", 4, 0, 0),
	("a repeat scan is one punch", "10:00-18:30", "Present", "10:00 10:01 18:30", 0, 0, 0),
	("20 late on a 540-minute shift: red", "12:00-21:00", "Present", "12:20 21:00", 0, 1, 0),
	("31 late, stays late: still a quarter", "12:00-21:00", "Present", "12:31 21:30", 1, 0, 0),
	("10 late, 80%: a quarter and a red", "10:00-18:30", "Present", "10:10 17:00", 1, 1, 0),
	("10 late and 10 early, 96.7%: two reds", "08:30-18:30", "Present", "08:40 18:20", 0, 2, 0),
	("Half Day with no leave behind it: a full day's rules", "10:00-18:30", "Half Day", "10:00 14:30", 2, 0, 0),
]


class InventedDays(unittest.TestCase):
	def test_alv326_every_invented_day(self):
		for what, shift, status, punches, q, r, g in INVENTED_DAYS:
			with self.subTest(what=what):
				v = day(shift, punches, status)
				self.assertEqual((v.total_quarters, v.reds, v.greens), (q, r, g),
				                 " ".join(v.reasons))


class ShiftHoursOnly(unittest.TestCase):
	"""Only time inside the shift counts."""

	def test_alv326_staying_late_does_not_make_up_for_arriving_late(self):
		"""In 10:40 on 09:00-19:00: 500 of 600, 83.3%, 1 quarter, no red - out
		at 20:00 or 21:00 makes no difference."""
		for out in ("20:00", "21:00"):
			v = day("09:00-19:00", "10:40 " + out)
			self.assertAlmostEqual(v.attendance_percent, 83.33, places=2)
			self.assertEqual((v.total_quarters, v.reds), (1, 0))

	def test_alv326_a_night_green_and_a_late_quarter_both_stand(self):
		v = day("09:00-19:00", "10:40 20:00")
		self.assertEqual((v.total_quarters, v.greens), (1, 1))

	def test_alv326_arriving_early_does_not_make_up_for_leaving_early(self):
		"""08:50 to 18:05 counts 09:00 to 18:05: 545 of 600, 90.8%, 1 red."""
		v = day("09:00-19:00", "08:50 18:05")
		self.assertAlmostEqual(v.attendance_percent, 90.83, places=2)
		self.assertEqual((v.total_quarters, v.reds), (0, 1))

	def test_alv326_a_morning_green_still_reads_the_real_first_punch(self):
		v = day("10:30-20:30", "08:30 20:30")
		self.assertEqual(v.greens, 1)
		self.assertEqual(v.attendance_percent, 100.0)


class Breaks(unittest.TestCase):
	"""Up to the allowance a day is free; beyond is deducted."""

	def test_alv326_breaks_up_to_the_allowance_cost_nothing(self):
		for back in ("13:05", "13:20", "13:40"):
			v = day("09:00-19:00", "08:45 13:00 %s 19:05" % back)
			self.assertEqual(v.attendance_percent, 100.0)
			self.assertEqual((v.total_quarters, v.reds), (0, 0))

	def test_alv326_minutes_beyond_the_allowance_are_deducted(self):
		"""A 59-minute lunch: 19 over, 581 of 600, 96.8%, 1 red."""
		v = day("09:00-19:00", "09:00 13:00 13:59 19:00")
		self.assertAlmostEqual(v.attendance_percent, 581 / 6.0, places=2)
		self.assertEqual((v.total_quarters, v.reds), (0, 1))

	def test_alv326_the_allowance_is_for_the_whole_day(self):
		"""Two breaks of 25 minutes: 50 in all, 10 over."""
		v = day("09:00-19:00", "09:00 12:00 12:25 16:00 16:25 19:00")
		self.assertAlmostEqual(v.attendance_percent,
		                       (600 - (50 - BREAK_ALLOWANCE)) / 6.0, places=2)

	def test_alv326_a_gap_outside_the_shift_is_not_a_break(self):
		v = day("10:30-20:30", "08:00 08:10 09:30 20:30")
		self.assertEqual(v.attendance_percent, 100.0)

	def test_alv326_an_odd_punch_count_deducts_no_break_and_says_why(self):
		v = day("09:00-19:00", "09:00 12:00 19:00")
		self.assertEqual(v.attendance_percent, 100.0)
		self.assertIn("breaks could not be measured", " ".join(v.reasons))

	def test_alv326_a_two_punch_day_has_no_break_to_deduct(self):
		"""How a day with only a first and a last punch is judged."""
		self.assertEqual(day("09:00-19:00", "09:00 19:00").attendance_percent, 100.0)


class LateArrival(unittest.TestCase):
	"""Grace, then 1 red up to the limit, then a quarter."""

	def test_alv326_within_grace_counts_from_the_shift_start(self):
		"""6 minutes late on a 510-minute shift: no red. A plain clip would have
		given 98.8% and a red."""
		v = day("09:30-18:00", "09:36 18:00")
		self.assertFalse(v.late_arrival)
		self.assertEqual(v.attendance_percent, 100.0)
		self.assertEqual((v.total_quarters, v.reds), (0, 0))

	def test_alv326_seven_minutes_late_is_one_red(self):
		v = day("09:30-19:30", "09:37 19:30")
		self.assertEqual((v.total_quarters, v.reds), (0, 1))

	def test_alv326_at_the_limit_is_still_a_red(self):
		v = day("09:00-19:00", "09:30 19:00")
		self.assertEqual((v.total_quarters, v.reds), (0, 1))

	def test_alv326_one_minute_past_the_limit_is_a_quarter_and_no_red(self):
		"""The band alone would say 94.8% and a red."""
		v = day("09:00-19:00", "09:31 19:00")
		self.assertEqual((v.total_quarters, v.reds), (1, 0))

	def test_alv326_very_late_is_charged_by_the_band_not_one_quarter(self):
		"""130 minutes late, 63%: the band's 2 quarters - not 1, and not 3."""
		v = day("08:30-18:30", "10:40 17:00")
		self.assertEqual((v.total_quarters, v.reds), (2, 0))

	def test_alv326_late_and_early_is_a_quarter_and_a_red(self):
		for shift, punches in (("08:30-18:30", "08:50 16:10"),
		                       ("10:00-18:30", "10:10 17:00"),
		                       ("12:00-21:00", "12:25 18:30")):
			with self.subTest(punches=punches):
				v = day(shift, punches)
				self.assertEqual((v.total_quarters, v.reds), (1, 1))

	def test_alv326_late_and_a_little_early_is_still_two_reds(self):
		"""The two-red rule stands. 10 late, out 20 early: 570 of 600, 95% - no
		quarter, so both infractions are reds."""
		v = day("10:30-20:30", "10:40 20:10")
		self.assertEqual((v.total_quarters, v.reds), (0, 2))
		self.assertNotIn("same red", " ".join(v.reasons))

	def test_alv326_the_late_quarter_is_not_doubled_but_the_band_still_is(self):
		v = day("09:00-19:00", "09:40 19:00", is_special_day=True,
		        double_deduction_applies=True)
		self.assertEqual(v.total_quarters, 1)
		v = day("09:00-19:00", "09:40 16:00", is_special_day=True,
		        double_deduction_applies=True)
		self.assertEqual(v.total_quarters, 4)   # 63.3% is 2 quarters, doubled

	def test_alv326_staff_without_marks_lose_the_quarter_but_carry_no_red(self):
		v = day("09:00-19:00", "09:20 19:00", grace_minutes=15, earns_marks=False)
		self.assertEqual((v.total_quarters, v.reds), (0, 0))
		v = day("09:00-19:00", "09:40 19:00", grace_minutes=15, earns_marks=False)
		self.assertEqual((v.total_quarters, v.reds), (1, 0))


class TheWhyTextNeverShowsARedThatWasNotCharged(unittest.TestCase):
	"""Security M2: the reasons must match the stored count."""

	def test_alv326_a_late_red_on_a_red_band_says_it_is_one_red(self):
		v = day("08:30-18:30", "08:44 18:30")
		self.assertEqual(v.reds, 1)
		self.assertIn("same red", " ".join(v.reasons))

	def test_alv326_a_late_quarter_on_a_red_band_says_no_red(self):
		v = day("09:00-19:00", "09:31 19:00")
		self.assertEqual(v.reds, 0)
		self.assertIn("No red: the late quarter replaces the band's red",
		              " ".join(v.reasons))


class TheLateWindowStillWorks(unittest.TestCase):
	"""ATT-04 is unchanged in code. A rule set that clears it does not get it;
	a rule set that sets it still does, and it stacks."""

	def test_alv326_33_late_with_the_window_off_is_one_quarter(self):
		v = day("10:30-19:00", "11:03 17:30 18:00 19:00")
		self.assertEqual((v.total_quarters, v.reds), (1, 0))

	def test_alv326_with_the_window_set_it_still_stacks_its_quarter(self):
		v = day("10:30-19:00", "11:03 17:30 18:00 19:00",
		        late_window_from=hm(11, 0), late_window_to=hm(11, 30),
		        late_window_extra_quarters=1, late_window_flagged=True)
		self.assertTrue(v.late_window_hit)
		self.assertEqual(v.total_quarters, 2)


class ARuleSetThatSetsNoneOfThemIsUnchanged(unittest.TestCase):
	"""Every other tenant: the three settings off, the old arithmetic."""

	def plain(self, shift, punches):
		return day(shift, punches, shift_hours_only=False,
		           late_quarter_after_minutes=0, break_allowance_minutes=0)

	def test_alv326_staying_late_still_makes_up_for_arriving_late(self):
		v = self.plain("09:00-19:00", "10:40 21:00")
		self.assertEqual(v.attendance_percent, 100.0)
		self.assertEqual((v.total_quarters, v.reds), (0, 0))

	def test_alv326_a_long_break_is_not_deducted(self):
		self.assertEqual(self.plain("09:00-19:00", "09:00 12:00 14:00 19:00")
		                 .attendance_percent, 100.0)

	def test_alv326_forty_minutes_late_is_judged_by_the_band_alone(self):
		"""In 9:40, out 19:00: 560 of 600, 93.3%, a band red and no quarter."""
		v = self.plain("09:00-19:00", "09:40 19:00")
		self.assertEqual((v.total_quarters, v.reds), (0, 1))

	def test_alv326_each_setting_works_on_its_own(self):
		"""Only the break rule: a 59-minute lunch costs 19 minutes."""
		v = day("09:00-19:00", "09:00 13:00 13:59 19:00", shift_hours_only=False,
		        late_quarter_after_minutes=0)
		self.assertAlmostEqual(v.attendance_percent, 581 / 6.0, places=2)


class HalfDayLeave(unittest.TestCase):
	def test_alv326_the_worked_half_counts_only_shift_time(self):
		"""In 08:30, out 15:30 on 10:30-20:30: 300 of the 300-minute half."""
		v = day("10:30-20:30", "08:30 15:30", half_day_leave=True)
		self.assertEqual(v.attendance_percent, 100.0)
		v = day("10:30-20:30", "08:30 14:30", half_day_leave=True)
		self.assertAlmostEqual(v.attendance_percent, 80.0, places=2)


if __name__ == "__main__":
	unittest.main(verbosity=2)
