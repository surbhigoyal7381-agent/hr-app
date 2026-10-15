"""The payroll rules engine, tested against the client's own worked examples.

`payroll_rules.evaluate_day` touches no database, so these run as plain unit
tests - no bench, no site, no fixtures. That matters more than it sounds: these
cases ARE the client's rules. If one of them ever fails, either the engine
broke or the rules changed, and both are things somebody has to be told about.

Where a case comes from the PP Jewellers rule-by-rule document or the 8 October
addendum, the test says so and uses the document's own figures.
"""

import unittest

from alvoraa_portal.payroll_rules import (
	collapse_duplicate_punches,
	evaluate_day,
	find_slab,
	leave_credits_for_month,
)


class Slab:
	"""Stands in for an `Alvoraa Attendance Slab` child row."""

	def __init__(self, percent_from, percent_to, quarters_off, raises_red=0):
		self.percent_from = percent_from
		self.percent_to = percent_to
		self.quarters_off = quarters_off
		self.raises_red = raises_red


# DTC's 12-row table, with the two gaps closed to the neighbouring "No" row as
# decided on 8 October (addendum C-2): 69->68 and 99->98.9.
DTC_SLABS = [
	Slab(0, 20, 4, 0),
	Slab(20, 24, 3, 1),
	Slab(24, 25, 3, 0),
	Slab(25, 40, 3, 0),
	Slab(40, 44, 2, 1),
	Slab(44, 50, 2, 0),
	Slab(50, 65, 2, 0),
	Slab(65, 68, 1, 1),
	Slab(68, 75, 1, 0),
	Slab(75, 90, 1, 0),
	Slab(90, 98.9, 0, 1),
	Slab(98.9, 100, 0, 0),
]


def hm(hours, minutes=0):
	"""A clock time as minutes from midnight, so the tests read like a roster."""
	return hours * 60 + minutes


# The common DTC shift: 10:30 to 20:30, 600 gross minutes including the break.
SHIFT_START = hm(10, 30)
SHIFT_END = hm(20, 30)

# ATT-04's window, exactly as the client wrote it: a clock time, not an offset.
WINDOW_FROM = hm(11, 0)
WINDOW_TO = hm(11, 30)


def judge(**kwargs):
	"""evaluate_day with DTC's standing configuration already filled in."""
	args = dict(
		shift_start=SHIFT_START,
		shift_end=SHIFT_END,
		punch_count=2,
		grace_minutes=6,
		slabs=DTC_SLABS,
		special_day_multiplier=2,
	)
	args.update(kwargs)
	return evaluate_day(**args)


class TestSlabLookup(unittest.TestCase):
	def test_every_whole_percent_finds_exactly_one_row(self):
		"""A gap here pays a day in full by accident, so check all of them."""
		for pct in range(0, 101):
			with self.subTest(pct=pct):
				self.assertIsNotNone(find_slab(DTC_SLABS, pct),
				                     "no slab row covers {0}%".format(pct))

	def test_a_full_day_matches_the_top_row_not_nothing(self):
		"""percent_to is exclusive everywhere except the very top of the table."""
		row = find_slab(DTC_SLABS, 100)
		self.assertEqual(row.quarters_off, 0)
		self.assertFalse(row.raises_red)

	def test_the_two_closed_gaps_resolve_to_the_no_red_row(self):
		"""Addendum C-2. 68.5% and 98.95% had no row in the client's table."""
		self.assertFalse(find_slab(DTC_SLABS, 68.5).raises_red)
		self.assertEqual(find_slab(DTC_SLABS, 68.5).quarters_off, 1)
		self.assertFalse(find_slab(DTC_SLABS, 98.95).raises_red)
		self.assertEqual(find_slab(DTC_SLABS, 98.95).quarters_off, 0)


class TestDuplicatePunches(unittest.TestCase):
	"""A reader that scans twice in a second has not recorded a day of work."""

	def test_the_real_case_collapses_to_one_punch(self):
		"""HR-EMP-00031, 1 October 2026: punches at 10:09:00 and 10:09:01."""
		times = [hm(10, 9), hm(10, 9) + 1 / 60.0]
		self.assertEqual(len(collapse_duplicate_punches(times)), 1)

	def test_a_run_of_scans_collapses_to_one(self):
		"""HR-EMP-00031, 7 October: 20:37:32, :35, :38, then 21:38:09."""
		times = [hm(20, 37) + 32 / 60.0, hm(20, 37) + 35 / 60.0,
		         hm(20, 37) + 38 / 60.0, hm(21, 38) + 9 / 60.0]
		self.assertEqual(len(collapse_duplicate_punches(times)), 2)

	def test_punches_further_apart_are_left_alone(self):
		times = [hm(10, 30), hm(10, 35), hm(20, 30)]
		self.assertEqual(len(collapse_duplicate_punches(times)), 3)

	def test_it_keeps_the_first_of_a_cluster(self):
		times = [hm(10, 9), hm(10, 10), hm(20, 30)]
		self.assertEqual(collapse_duplicate_punches(times)[0], hm(10, 9))

	def test_the_day_that_would_have_cost_a_full_day_is_held_instead(self):
		"""Read literally, two punches a second apart give 0% and four quarters
		off - a whole day's pay for a double-read. Collapsed, it is one punch,
		which ATT-06 holds."""
		raw = [hm(10, 9), hm(10, 9) + 1 / 60.0]
		naive = judge(first_in=raw[0], last_out=raw[-1], punch_count=len(raw))
		self.assertEqual(naive.slab_quarters, 4)

		distinct = collapse_duplicate_punches(raw)
		fixed = judge(first_in=distinct[0], last_out=distinct[-1],
		              punch_count=len(distinct))
		self.assertTrue(fixed.held)
		self.assertEqual(fixed.slab_quarters, 0)

	def test_an_empty_day_stays_empty(self):
		self.assertEqual(collapse_duplicate_punches([]), [])


class TestRahulTheDocumentsWorkedExample(unittest.TestCase):
	"""Rule-by-rule document, ATT-04 worked example, page 5.

	Rahul, flagged for the 11 AM rule, in at 11:00 and out at 17:42 on a
	10:30-20:30 shift. The document states: 67%, 1 slab quarter, 1 ATT-04
	quarter, 2 quarters total, 1 red.
	"""

	def setUp(self):
		self.v = judge(
			first_in=hm(11, 0),
			last_out=hm(17, 42),
			late_window_from=WINDOW_FROM,
			late_window_to=WINDOW_TO,
			late_window_extra_quarters=1,
			late_window_flagged=True,
		)

	def test_attendance_is_sixty_seven_percent(self):
		self.assertAlmostEqual(self.v.attendance_percent, 67.0, places=1)

	def test_the_slab_gives_one_quarter(self):
		self.assertEqual(self.v.slab_quarters, 1)

	def test_the_late_window_adds_one_more(self):
		self.assertTrue(self.v.late_window_hit)
		self.assertEqual(self.v.extra_quarters, 1)

	def test_two_quarters_in_total(self):
		self.assertEqual(self.v.total_quarters, 2)

	def test_one_red_even_though_he_was_late_and_left_early(self):
		"""GBL-09. The band already deducted a quarter for the missing minutes,
		so a second red for the same minutes would charge them twice."""
		self.assertTrue(self.v.late_arrival)
		self.assertTrue(self.v.early_departure)
		self.assertEqual(self.v.reds, 1)


class TestRedCounting(unittest.TestCase):
	"""Her ruling of 8 October: at most two reds, and never two rules at once."""

	def test_two_reds_when_both_happened_and_no_quarter_was_charged(self):
		"""Sangeeta Kaundal, 7 Oct 2026 - the one real case in 2,642 days.
		In 10:39, out 19:45. 91%, which is the only red band with no quarter."""
		v = judge(first_in=hm(10, 39), last_out=hm(19, 45))
		self.assertAlmostEqual(v.attendance_percent, 91.0, places=1)
		self.assertEqual(v.slab_quarters, 0)
		self.assertEqual(v.reds, 2)

	def test_one_red_when_a_quarter_already_charged_the_minutes(self):
		"""22%: three quarters off. The quarters cover both infractions."""
		v = judge(first_in=hm(10, 45), last_out=hm(13, 0))
		self.assertEqual(v.slab_quarters, 3)
		self.assertTrue(v.late_arrival and v.early_departure)
		self.assertEqual(v.reds, 1)

	def test_one_red_when_only_one_infraction_happened(self):
		"""On time, left early, 91%. One infraction, so one red at most."""
		v = judge(first_in=hm(10, 30), last_out=hm(19, 36))
		self.assertFalse(v.late_arrival)
		self.assertTrue(v.early_departure)
		self.assertEqual(v.reds, 1)

	def test_no_red_in_a_band_that_raises_none(self):
		"""45% is a no-red band, so both infractions still give zero reds."""
		v = judge(first_in=hm(11, 30), last_out=hm(16, 0))
		self.assertEqual(v.slab_quarters, 2)
		self.assertTrue(v.late_arrival and v.early_departure)
		self.assertEqual(v.reds, 0)

	def test_a_full_day_earns_no_red_and_loses_no_quarter(self):
		v = judge(first_in=hm(10, 30), last_out=hm(20, 30))
		self.assertEqual(v.reds, 0)
		self.assertEqual(v.total_quarters, 0)

	def test_grace_means_six_minutes_late_is_not_late(self):
		"""GBL-04."""
		v = judge(first_in=hm(10, 36), last_out=hm(20, 30))
		self.assertFalse(v.late_arrival)
		self.assertEqual(v.reds, 0)


class TestHeldDays(unittest.TestCase):
	"""ATT-06. A missing check-out holds the day; it does not deduct it."""

	def test_one_punch_is_held_not_judged(self):
		v = judge(first_in=hm(10, 30), last_out=None, punch_count=1)
		self.assertTrue(v.held)
		self.assertEqual(v.total_quarters, 0)
		self.assertEqual(v.reds, 0)

	def test_a_held_day_never_reaches_the_slab_table(self):
		"""HR-EMP-00110, 30 Sep. Without this he lost a day's pay - 1,667 rupees
		- for a missed button press, having worked the day."""
		v = judge(first_in=hm(10, 30), last_out=None, punch_count=1)
		self.assertEqual(v.attendance_percent, 0.0)
		self.assertEqual(v.slab_quarters, 0)

	def test_no_punches_and_marked_absent_is_a_real_absence(self):
		"""0% here IS a measurement. The slab charges the full day."""
		v = judge(first_in=None, last_out=None, punch_count=0, marked_absent=True)
		self.assertFalse(v.held)
		self.assertEqual(v.attendance_percent, 0.0)
		self.assertEqual(v.slab_quarters, 4)
		self.assertEqual(v.reds, 0)

	def test_a_full_absence_on_a_special_day_doubles(self):
		"""WSD-04, reached through the no-punch path rather than a short day."""
		v = judge(first_in=None, last_out=None, punch_count=0, marked_absent=True,
		          is_special_day=True, double_deduction_applies=True)
		self.assertEqual(v.slab_quarters, 8)
		self.assertEqual(v.days_deducted, 2.0)

	def test_an_absence_earns_no_green(self):
		v = judge(first_in=None, last_out=None, punch_count=0, marked_absent=True,
		          night_green_eligible=True)
		self.assertEqual(v.greens, 0)

	def test_no_punches_but_marked_present_is_held_not_deducted(self):
		"""Somebody marked this day by hand. Deducting contradicts them; paying
		it in full makes a hand-marked day the cheapest way to skip one."""
		v = judge(first_in=None, last_out=None, punch_count=0, marked_absent=False)
		self.assertTrue(v.held)
		self.assertEqual(v.total_quarters, 0)
		self.assertIn("by hand", " ".join(v.reasons))

	def test_one_punch_is_held_even_when_marked_absent(self):
		"""ATT-06 wins over the absence marking: somebody did turn up."""
		v = judge(first_in=hm(10, 30), last_out=None, punch_count=1,
		          marked_absent=True)
		self.assertTrue(v.held)
		self.assertEqual(v.slab_quarters, 0)

	def test_a_confirmed_time_releases_the_day_and_measures_it(self):
		"""ATT-06, settled 9 October 2026. Confirming supplies the missing
		time; it does not pay the day in full.

		In at 10:30, no check-out. HR confirms he left at 17:42 - which is
		67% of the shift, so one quarter and one red, exactly as if he had
		punched it himself."""
		v = judge(first_in=hm(10, 30), last_out=None, punch_count=1,
		          confirmed_out=hm(17, 42))
		self.assertFalse(v.held)
		self.assertAlmostEqual(v.attendance_percent, 72.0, places=1)
		self.assertEqual(v.slab_quarters, 1)
		self.assertTrue(v.early_departure)
		self.assertIn("confirmed afterwards", " ".join(v.reasons))

	def test_confirming_a_full_day_costs_nothing(self):
		"""The honest case: he did work the whole day and forgot to clock out."""
		v = judge(first_in=hm(10, 30), last_out=None, punch_count=1,
		          confirmed_out=hm(20, 30))
		self.assertFalse(v.held)
		self.assertEqual(v.attendance_percent, 100.0)
		self.assertEqual(v.total_quarters, 0)
		self.assertEqual(v.reds, 0)

	def test_a_forgotten_punch_is_not_better_than_an_honest_early_exit(self):
		"""The reason the rule is this way round. Somebody who leaves at 17:42
		and clocks out, and somebody who leaves at 17:42 and does not, must end
		up in the same place - or people learn which is cheaper."""
		honest = judge(first_in=hm(10, 30), last_out=hm(17, 42))
		forgot = judge(first_in=hm(10, 30), last_out=None, punch_count=1,
		               confirmed_out=hm(17, 42))
		self.assertEqual(honest.total_quarters, forgot.total_quarters)
		self.assertEqual(honest.reds, forgot.reds)
		self.assertEqual(honest.day_credit, forgot.day_credit)

	def test_without_a_confirmed_time_it_stays_held(self):
		v = judge(first_in=hm(10, 30), last_out=None, punch_count=1)
		self.assertTrue(v.held)

	def test_an_approved_leave_day_is_not_held(self):
		"""It has no punches and is not marked absent, so without its own case
		it falls into the held branch - and waits for a manager to confirm a
		day nobody ever doubted."""
		v = judge(first_in=None, last_out=None, punch_count=0,
		          marked_on_leave=True)
		self.assertFalse(v.held)
		self.assertFalse(v.absent)
		self.assertTrue(v.on_leave)
		self.assertEqual(v.total_quarters, 0)
		self.assertEqual(v.reds, 0)
		self.assertEqual(v.day_credit, 0.0)
		self.assertIn("Approved leave", " ".join(v.reasons))

	def test_leave_wins_over_an_absence_marking(self):
		"""If a day is both, somebody approved it and that is the better
		answer: an approved absence is leave."""
		v = judge(first_in=None, last_out=None, punch_count=0,
		          marked_absent=True, marked_on_leave=True)
		self.assertTrue(v.on_leave)
		self.assertFalse(v.absent)
		self.assertEqual(v.total_quarters, 0)

	def test_a_broken_shift_is_held_rather_than_guessed_at(self):
		v = judge(shift_start=hm(10, 30), shift_end=hm(10, 30),
		          first_in=hm(10, 30), last_out=hm(20, 30))
		self.assertTrue(v.held)

	def test_a_gap_in_the_rule_set_holds_the_day(self):
		"""The controller refuses to save a table with a hole, but a fixture or
		a direct database edit can still write one. Holding is the only safe
		answer: paying in full is a silent gift, deducting is silent theft."""
		holed = [Slab(0, 50, 4, 0), Slab(60, 100, 0, 0)]
		# 330 of 600 minutes is 55%, which lands in the 50-60 hole.
		v = judge(first_in=hm(13, 0), last_out=hm(18, 30), slabs=holed)
		self.assertAlmostEqual(v.attendance_percent, 55.0, places=1)
		self.assertTrue(v.held)
		self.assertEqual(v.total_quarters, 0)


class TestSpecialDays(unittest.TestCase):
	"""WSD-01, WSD-02, WSD-05, and her ruling of 8 October on ATT-04."""

	def test_slab_quarters_are_multiplied(self):
		"""The document's Priya example: 60% on a Saturday, 2 quarters -> 4."""
		v = judge(first_in=hm(10, 30), last_out=hm(16, 30),
		          is_special_day=True, double_deduction_applies=True)
		self.assertEqual(v.slab_quarters, 4)
		self.assertTrue(v.doubled)

	def test_a_full_absence_on_a_special_day_costs_two_days(self):
		"""WSD-04. 4 quarters doubled is 8, which is two whole days."""
		v = judge(first_in=hm(10, 30), last_out=hm(11, 0),
		          is_special_day=True, double_deduction_applies=True)
		self.assertEqual(v.slab_quarters, 8)
		self.assertEqual(v.days_deducted, 2.0)

	def test_reds_are_never_multiplied(self):
		"""WSD-02. A red on a Sunday is one red, same as a Monday."""
		plain = judge(first_in=hm(10, 39), last_out=hm(19, 45))
		special = judge(first_in=hm(10, 39), last_out=hm(19, 45),
		                is_special_day=True, double_deduction_applies=True)
		self.assertEqual(special.reds, plain.reds)

	def test_an_employee_flagged_single_takes_the_single_deduction(self):
		"""WSD-05 and WSD-06. Field staff and exempt categories."""
		v = judge(first_in=hm(10, 30), last_out=hm(16, 30),
		          is_special_day=True, double_deduction_applies=False)
		self.assertEqual(v.slab_quarters, 2)
		self.assertFalse(v.doubled)

	def test_the_late_window_quarter_is_not_multiplied(self):
		"""Confirmed 8 October 2026: single only. WSD-01 doubles the quarters
		from the slab table, and the ATT-04 quarter does not come from it."""
		v = judge(first_in=hm(11, 0), last_out=hm(17, 42),
		          is_special_day=True, double_deduction_applies=True,
		          late_window_from=WINDOW_FROM, late_window_to=WINDOW_TO,
		          late_window_extra_quarters=1, late_window_flagged=True)
		self.assertEqual(v.slab_quarters, 2)      # 1 from the slab, doubled
		self.assertEqual(v.extra_quarters, 1)     # untouched
		self.assertEqual(v.total_quarters, 3)


class TestLateWindow(unittest.TestCase):
	"""ATT-04, including the shifts the rule as written would misfire on."""

	def window(self, **kwargs):
		args = dict(
			first_in=hm(11, 0), last_out=hm(17, 42),
			late_window_from=WINDOW_FROM, late_window_to=WINDOW_TO,
			late_window_extra_quarters=1, late_window_flagged=True,
		)
		args.update(kwargs)
		return judge(**args)

	def test_an_unflagged_employee_is_never_charged(self):
		v = self.window(late_window_flagged=False)
		self.assertFalse(v.late_window_hit)
		self.assertEqual(v.extra_quarters, 0)

	def test_arriving_after_the_window_closes_does_not_charge(self):
		"""The rule is a window, not a threshold. 11:35 is later than 11:05 and
		costs less, which is odd but is what the client wrote."""
		v = self.window(first_in=hm(11, 35))
		self.assertFalse(v.late_window_hit)

	def test_arriving_before_the_window_opens_does_not_charge(self):
		v = self.window(first_in=hm(10, 45))
		self.assertFalse(v.late_window_hit)

	def test_a_punctual_employee_on_an_eleven_oclock_shift_is_not_charged(self):
		"""The misfire. One DTC shift starts at 11:00, so arriving 11:00 is on
		time - and the rule as written would still take a quarter."""
		v = self.window(shift_start=hm(11, 0), shift_end=hm(20, 30),
		                first_in=hm(11, 0), last_out=hm(20, 30))
		self.assertFalse(v.late_arrival)
		self.assertFalse(v.late_window_hit)
		self.assertEqual(v.extra_quarters, 0)

	def test_an_early_employee_on_a_half_eleven_shift_is_not_charged(self):
		"""Two more DTC shifts start at 11:30 and 12:00. Arriving 11:00 there
		is early, and the window would have charged it."""
		v = self.window(shift_start=hm(11, 30), shift_end=hm(21, 30),
		                first_in=hm(11, 0), last_out=hm(21, 30))
		self.assertFalse(v.late_window_hit)

	def test_it_still_fires_on_the_shifts_the_rule_was_written_for(self):
		"""The 10:30 shift, which is most of the company."""
		self.assertTrue(self.window().late_window_hit)

	def test_it_does_not_suppress_the_red(self):
		"""GBL-09: the window charges the act of arriving, the red charges the
		threshold missed. The document says both stand."""
		v = self.window()
		self.assertEqual(v.reds, 1)
		self.assertEqual(v.extra_quarters, 1)


class TestGreens(unittest.TestCase):
	"""GRN-02 and GRN-03."""

	def test_morning_green_is_open_to_everyone(self):
		v = judge(first_in=hm(8, 30), last_out=hm(20, 30))
		self.assertEqual(v.greens, 1)

	def test_morning_green_needs_a_full_two_hours(self):
		v = judge(first_in=hm(8, 31), last_out=hm(20, 30))
		self.assertEqual(v.greens, 0)

	def test_night_green_is_for_nominated_staff_only(self):
		late_out = dict(first_in=hm(10, 30), last_out=hm(21, 30))
		self.assertEqual(judge(night_green_eligible=False, **late_out).greens, 0)
		self.assertEqual(judge(night_green_eligible=True, **late_out).greens, 1)

	def test_both_greens_can_land_on_one_day(self):
		v = judge(first_in=hm(8, 30), last_out=hm(21, 30),
		          night_green_eligible=True)
		self.assertEqual(v.greens, 2)

	def test_a_green_and_a_red_do_not_cancel(self):
		"""RED-06 and GRN-04: they are separate line items, never netted.
		In two hours early, then gone by 15:00 - 65%, so a green and a red."""
		v = judge(first_in=hm(8, 30), last_out=hm(15, 0))
		self.assertAlmostEqual(v.attendance_percent, 65.0, places=1)
		self.assertEqual(v.greens, 1)
		self.assertEqual(v.reds, 1)

	def test_hours_banked_early_count_towards_the_percentage(self):
		"""Not a rule the client wrote, so worth pinning down: attendance is
		last punch minus first punch over the shift length, which means two
		hours in early can cover an early finish. The percentage caps at 100,
		so nobody earns a surplus - but they are not docked either.

		In 08:30, out 19:40 on a 10:30-20:30 shift: 670 minutes against a
		600-minute shift. Fifty minutes before shift end, yet nothing is owed."""
		v = judge(first_in=hm(8, 30), last_out=hm(19, 40))
		self.assertEqual(v.attendance_percent, 100.0)
		self.assertTrue(v.early_departure)
		self.assertEqual(v.total_quarters, 0)
		self.assertEqual(v.reds, 0)
		self.assertEqual(v.greens, 1)


class TestLeaveCredits(unittest.TestCase):
	"""LB-01, settled 9 October 2026: a gate at 15 days, then an accrual.

	    A - 1 day every 7.5 days attended, up to 4
	    B - 1 day every 10 days attended,  up to 3
	    C - half a day every 7.5 days,     up to 2

	The accrual runs on days PRESENT, not days elapsed. Accruing on calendar
	time would credit somebody for a month they never worked.
	"""

	A = dict(period_days=7.5, credit_per_period=1.0, monthly_cap=4.0)
	B = dict(period_days=10.0, credit_per_period=1.0, monthly_cap=3.0)
	C = dict(period_days=7.5, credit_per_period=0.5, monthly_cap=2.0)

	def test_below_the_gate_earns_nothing(self):
		"""However many periods the accrual would otherwise have closed."""
		for days in (0, 7, 8, 14):
			with self.subTest(days=days):
				self.assertEqual(leave_credits_for_month(days, **self.A), 0.0)
				self.assertEqual(leave_credits_for_month(days, **self.B), 0.0)
				self.assertEqual(leave_credits_for_month(days, **self.C), 0.0)

	def test_full_attendance_still_earns_the_whole_class(self):
		"""The headline 4/3/2 must survive, or the cadence is wrong."""
		for days in (30, 31):
			with self.subTest(days=days):
				self.assertEqual(leave_credits_for_month(days, **self.A), 4.0)
				self.assertEqual(leave_credits_for_month(days, **self.B), 3.0)
				self.assertEqual(leave_credits_for_month(days, **self.C), 2.0)

	def test_class_A_scales_with_attendance_above_the_gate(self):
		for days, expected in [(15, 2.0), (22, 2.0), (23, 3.0), (29, 3.0), (30, 4.0)]:
			with self.subTest(days=days):
				self.assertEqual(leave_credits_for_month(days, **self.A), expected)

	def test_class_B_scales_with_attendance_above_the_gate(self):
		for days, expected in [(15, 1.0), (19, 1.0), (20, 2.0), (29, 2.0), (30, 3.0)]:
			with self.subTest(days=days):
				self.assertEqual(leave_credits_for_month(days, **self.B), expected)

	def test_class_C_scales_in_half_days(self):
		for days, expected in [(15, 1.0), (22, 1.0), (23, 1.5), (30, 2.0)]:
			with self.subTest(days=days):
				self.assertEqual(leave_credits_for_month(days, **self.C), expected)

	def test_the_step_at_the_gate_is_three_days_not_five(self):
		"""The reason this rule changed. A flat class credit made the fifteenth
		day of attendance worth five days' pay - 4,167 rupees on a 25,000 basic
		in a 30-day month. The accrual halves it. Pinned so the smoothing is not
		undone without a decision."""
		daily = 25000 / 30
		at_14 = 14 + leave_credits_for_month(14, **self.A)
		at_15 = 15 + leave_credits_for_month(15, **self.A)
		self.assertEqual(at_14, 14.0)
		self.assertEqual(at_15, 17.0)
		self.assertAlmostEqual((at_15 - at_14) * daily, 2500.0, places=2)

	def test_a_few_days_in_a_month_pays_for_those_days_only(self):
		"""Surbhi, 9 October 2026: "if anyone has come only a few days in a
		month he get the salary for those days only"."""
		basic, month_days, days_present = 25000, 31, 10
		self.assertEqual(leave_credits_for_month(days_present, **self.A), 0.0)
		paid_days = days_present + leave_credits_for_month(days_present, **self.A)
		self.assertEqual(paid_days, 10)
		self.assertAlmostEqual(paid_days * (basic / month_days), 8064.52, places=2)

	def test_a_new_joiner_cannot_reach_the_gate(self):
		"""Joined on the 21st, so at most 10 days are available. Paid for the
		days worked and nothing more. Flagged for DTC, not worked around."""
		self.assertEqual(leave_credits_for_month(10, **self.A), 0.0)

	def test_the_cap_holds_if_the_cadence_overruns(self):
		"""Belt and braces. The rule set refuses to save a cadence whose total
		disagrees with the class, but a fixture or a direct edit can."""
		greedy = dict(period_days=5.0, credit_per_period=1.0, monthly_cap=4.0)
		self.assertEqual(leave_credits_for_month(30, **greedy), 4.0)

	def test_a_contract_employee_with_no_class_earns_nothing(self):
		self.assertEqual(leave_credits_for_month(
			30, period_days=0, credit_per_period=1, monthly_cap=4), 0.0)
		self.assertEqual(leave_credits_for_month(
			30, period_days=None, credit_per_period=1, monthly_cap=4), 0.0)

	def test_both_the_gate_and_the_cadence_are_configurable(self):
		"""Tenant numbers, not constants in this file."""
		self.assertEqual(leave_credits_for_month(10, threshold_days=10, **self.A), 1.0)
		self.assertEqual(leave_credits_for_month(10, threshold_days=20, **self.A), 0.0)


class TestContractStaff(unittest.TestCase):
	"""Settled 9 October 2026: quarters yes, marks no, fifteen minutes' grace."""

	def contract(self, **kwargs):
		args = dict(grace_minutes=15, earns_marks=False,
		            night_green_eligible=True, morning_green_eligible=True)
		args.update(kwargs)
		return judge(**args)

	def test_quarters_still_apply(self):
		"""Half days and quarters are applicable. 67% loses a quarter."""
		v = self.contract(first_in=hm(11, 0), last_out=hm(17, 42))
		self.assertAlmostEqual(v.attendance_percent, 67.0, places=1)
		self.assertEqual(v.slab_quarters, 1)

	def test_no_red_even_in_a_red_band(self):
		"""Same day, same band. A regular employee takes a red here."""
		regular = judge(first_in=hm(11, 0), last_out=hm(17, 42))
		self.assertEqual(regular.reds, 1)
		self.assertEqual(self.contract(first_in=hm(11, 0), last_out=hm(17, 42)).reds, 0)

	def test_no_red_in_the_two_red_band_either(self):
		v = self.contract(first_in=hm(10, 45), last_out=hm(19, 45))
		self.assertEqual(v.reds, 0)

	def test_no_green_however_early_they_arrive(self):
		v = self.contract(first_in=hm(8, 30), last_out=hm(21, 30))
		self.assertEqual(v.greens, 0)

	def test_fifteen_minutes_grace_not_six(self):
		"""In at 10:44 on a 10:30 shift: late for a regular employee, on time
		for contract staff."""
		late_in = dict(first_in=hm(10, 44), last_out=hm(20, 30))
		self.assertTrue(judge(**late_in).late_arrival)
		self.assertFalse(self.contract(**late_in).late_arrival)

	def test_sixteen_minutes_is_late_even_for_them(self):
		v = self.contract(first_in=hm(10, 46), last_out=hm(20, 30))
		self.assertTrue(v.late_arrival)

	def test_a_held_day_is_still_held(self):
		"""ATT-06 does not care what category somebody is in."""
		v = self.contract(first_in=hm(10, 30), last_out=None, punch_count=1)
		self.assertTrue(v.held)

	def test_a_full_absence_still_costs_a_day(self):
		v = self.contract(first_in=None, last_out=None, punch_count=0,
		                  marked_absent=True)
		self.assertEqual(v.slab_quarters, 4)
		self.assertEqual(v.reds, 0)

	def test_special_day_doubling_still_applies(self):
		v = self.contract(first_in=hm(10, 30), last_out=hm(16, 30),
		                  is_special_day=True, double_deduction_applies=True)
		self.assertEqual(v.slab_quarters, 4)
		self.assertEqual(v.reds, 0)

	def test_the_verdict_says_why_there_is_no_red(self):
		v = self.contract(first_in=hm(11, 0), last_out=hm(17, 42))
		self.assertIn("carries no marks", " ".join(v.reasons))


class TestTheVerdictExplainsItself(unittest.TestCase):
	def test_every_judged_day_carries_its_reasons(self):
		"""A disputed payslip is answered by reading these back to the employee."""
		v = judge(first_in=hm(11, 0), last_out=hm(17, 42),
		          late_window_from=WINDOW_FROM, late_window_to=WINDOW_TO,
		          late_window_extra_quarters=1, late_window_flagged=True)
		joined = " ".join(v.reasons)
		self.assertIn("67.0%", joined)
		self.assertIn("quarter", joined)
		self.assertTrue(len(v.reasons) >= 4)

	def test_a_held_day_says_why_it_is_held(self):
		v = judge(first_in=hm(10, 30), last_out=None, punch_count=1)
		self.assertIn("one punch", " ".join(v.reasons))


if __name__ == "__main__":
	unittest.main(verbosity=2)
