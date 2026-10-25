"""The payroll rules engine: one day of attendance in, a verdict out.

Written once, for every tenant. The rules themselves are data, held in an
`Alvoraa Payroll Rule Set` record per company, so a client with a different slab
table needs a new record and not a new branch of this code.

`evaluate_day` is a pure function. It takes numbers and flags, touches no
database, and returns a `DayVerdict`. That is deliberate: every rule below came
from a client document with worked examples, and a pure function is the only
way to hold those examples as tests that still pass a year from now.

THE RULES, and where each comes from (PP Jewellers rule-by-rule, 7 Oct 2026,
plus the addendum of 8 Oct 2026):

  GBL-03/ATT-01  The denominator is the employee's own gross shift length. The
                 40-minute break is NOT subtracted. Shifts run 510 to 660
                 minutes, so a flat 600 would mis-rate most of the company.

  GBL-04         Six minutes' grace on arrival.

  ATT-02/ATT-03  The slab table turns the percentage into quarters off and a
                 red. A quarter is a quarter of a day's pay.

  ATT-03 + the   At most two reds in a day: one for arriving late, one for
  8 Oct ruling   leaving early. The band supplies the first. The second appears
                 only when both happened AND the band deducted no quarters -
                 because a quarter already charges for the missing minutes, and
                 charging them again as a red is the double penalty GBL-09
                 forbids. In practice two reds are reachable only in the
                 90-98.9% band, which is the one red band with zero quarters.

  ATT-04         An employee checking in inside the late window loses an extra
                 quarter. It applies to everybody (15 Oct 2026); whether it
                 bites depends on their own shift, below. GBL-09 says plainly this is NOT an overlap: it
                 charges the window of arrival, not the minutes missed, so it
                 stacks on the slab quarter and suppresses no red. It is never
                 doubled on a special day (confirmed 8 Oct 2026).

                 The window is a clock time, not an offset, exactly as the
                 client wrote it. That breaks on shifts starting at or after
                 the window: arriving 11:00 on an 11:00 shift is on time, and
                 the rule as written would still charge it. `_window_applies`
                 refuses to fire in that case. A punctual employee is never
                 charged.

  ATT-06         A present day with one punch is HELD - not paid, not
                 penalised - until somebody supplies the missing time. 0% is
                 not a measurement here, it is the absence of one, and feeding
                 it to the slab table would deduct a full day for a missed
                 button press.

                 Confirming does NOT pay the day in full. It supplies the
                 check-out time, and the day is then measured from that like
                 any other (settled 9 October 2026). Paying in full would make
                 a forgotten punch better than an honest early departure.

  WSD-01/02      On a special day the SLAB quarters are multiplied. Reds are
                 never multiplied, and neither is the ATT-04 quarter.

  WSD-05/06      Doubling applies to everybody except contract staff, who take
                 the single deduction (15 Oct 2026). It is read from the
                 employee's CATEGORY, so it follows employment type rather than
                 a box kept in step by hand.

  GRN-02/03      Morning green: in two hours or more early, open to everyone.
                 Night green: out an hour or more late, flagged staff only.
"""

from dataclasses import dataclass, field

# A day is four quarters. Used to cap a doubled deduction description, never to
# cap the deduction itself - a fully absent employee on a special day really
# does lose two days (WSD-04).
QUARTERS_PER_DAY = 4

# Half a day is two quarters. A half-day leave's worked half can never lose more
# than that before any special-day doubling (slice 063, 01d D1 and E-a).
HALF_DAY_QUARTERS = 2

# GRN-02 and GRN-03 thresholds, in minutes. Not configurable yet: no tenant has
# asked for a different figure, and a knob nobody turns is a knob to maintain.
MORNING_GREEN_EARLY_MINUTES = 120
NIGHT_GREEN_LATE_MINUTES = 60

# Punches closer together than this are the same event, not an in and an out.
# Readers double-read: HR-EMP-00031 on 1 October 2026 has punches at 10:09:00
# and 10:09:01. Read literally that is a one-second working day, 0% attendance
# and a whole day's pay gone - the ATT-06 problem wearing a different hat. Two
# minutes is comfortably longer than any double-read and shorter than any real
# shift anybody would work, so collapsing inside it cannot hide a genuine day.
DUPLICATE_PUNCH_MINUTES = 2


def collapse_duplicate_punches(times, window_minutes=DUPLICATE_PUNCH_MINUTES):
	"""Fold a reader's repeat scans into one punch each.

	`times` is minutes from midnight, in order. Returns the distinct punches.
	A day that collapses to a single punch is then held by ATT-06, which is the
	right answer: somebody arrived and no departure was ever recorded.
	"""
	distinct = []
	for t in sorted(times):
		if distinct and t - distinct[-1] <= window_minutes:
			continue
		distinct.append(t)
	return distinct


@dataclass
class DayVerdict:
	"""What the engine decided about one employee on one day, and why.

	`reasons` is not decoration. A disputed payslip is answered by reading this
	back to the employee, so every number that moved has a line explaining it.
	"""

	held: bool = False
	absent: bool = False
	on_leave: bool = False
	attendance_percent: float = 0.0
	slab_quarters: int = 0
	extra_quarters: int = 0
	doubled: bool = False
	reds: int = 0
	greens: int = 0
	late_arrival: bool = False
	early_departure: bool = False
	late_window_hit: bool = False
	# Slice 063: half of this day is approved leave (Frappe's "Half Day" with a
	# leave application behind it). Everything else on the verdict then
	# describes the OTHER half only.
	half_leave: bool = False
	reasons: list = field(default_factory=list)

	@property
	def total_quarters(self) -> int:
		"""Every quarter lost on the day, doubling already applied."""
		return self.slab_quarters + self.extra_quarters

	@property
	def days_deducted(self) -> float:
		return self.total_quarters / QUARTERS_PER_DAY

	@property
	def day_credit(self) -> float:
		"""What this one day is worth in paid days.

		Three shapes, and the difference between them is the whole of ATT-06
		and correction C-1:

		  HELD      0. Neither paid nor deducted. Released as an Arrear when a
		            manager confirms it, so it must not be netted off here.

		  ABSENT    0, and only the quarters ABOVE four are deducted. The day is
		            already unpaid by not being worked; charging four quarters
		            as well would dock the same day twice. On a special day the
		            doubling gives eight quarters, four are 'above', and one
		            extra day comes off - which is exactly the two-day penalty
		            WSD-04 asks for, and nothing more.

		  WORKED    1, less a quarter of a day for each quarter lost. A 70% day
		            carrying one quarter pays 0.75. That is correction C-1:
		            every day an employee is owed salary for, they get.
		"""
		if self.held:
			return 0.0
		if self.half_leave:
			# Half the day is leave, funded at month level like a full leave
			# day, so it adds nothing here. The other half is worth 0.5, less a
			# quarter-day per quarter lost; absent, it is unpaid and only the
			# quarters above its own two are charged (the full-day rule, halved).
			if self.absent:
				return -max(0, self.total_quarters - HALF_DAY_QUARTERS) / QUARTERS_PER_DAY
			return 0.5 - self.total_quarters / QUARTERS_PER_DAY
		if self.on_leave:
			# Approved leave. The day itself is funded by a leave credit at
			# month level (LB-02), so it contributes nothing here - and it is
			# certainly not an absence to be charged for.
			return 0.0
		if self.absent:
			return -max(0, self.total_quarters - QUARTERS_PER_DAY) / QUARTERS_PER_DAY
		return 1.0 - self.total_quarters / QUARTERS_PER_DAY


# How many days a regular employee must attend before the month's leave class
# is credited at all. Below it they are paid for the days they worked and
# nothing else (LB-01, as settled on 9 October 2026).
LEAVE_THRESHOLD_DAYS = 15


# The accrual calendar is 30 days by policy, whatever the real month holds, so
# a 31-day month grants no extra period.
ACCRUAL_MONTH_DAYS = 30

# Period lengths are typed by a person, and a figure like 7.33 would not divide
# cleanly in binary. A period counts as closed if it is within this of closing,
# so nobody loses a credit to a rounding error.
PERIOD_EPSILON = 1e-9


def leave_credits_for_month(days_present, period_days, credit_per_period,
							monthly_cap, threshold_days=LEAVE_THRESHOLD_DAYS,
							month_days=ACCRUAL_MONTH_DAYS):
	"""Compensatory leave: a gate, then an accrual on days actually attended.

	Settled by Surbhi, 9 October 2026, after seeing what a flat credit did at
	the boundary.

		Below `threshold_days` present  ->  nothing. Paid for the days worked.
		At or above it                  ->  one credit per completed period of
											attendance, capped at the class.

	The cadence as first set for DTC on 9 October 2026:

		A - 1 day every 7.5 days attended, up to 4
		B - 1 day every 10 days attended,  up to 3
		C - half a day every 7.5 days,     up to 2

	SUPERSEDED for DTC on 21 October 2026 (slice 063, 01e): the whole class
	figure is given on the 1st and counts once 15 days are attended. That is
	settings, not code - one 15-day period worth the whole class (A 15/4/4,
	B 15/3/3, C 15/2/2, `accrual_month_days` 15). The function is unchanged.

	THE INPUT IS DAYS PRESENT, NOT DAYS ELAPSED. An earlier version accrued on
	calendar time, which would credit an absent employee for a month they never
	worked. Here the periods are periods of attendance, so the credit tracks
	what somebody actually did.

	WHY BOTH A GATE AND A SLOPE.

	A flat class credit made the threshold brutally sharp: on a 25,000 basic the
	fifteenth day of attendance was worth 4,167 rupees - five days' pay for one
	day's work, on a predictable date. Accruing above the gate halves that to
	three days while leaving the principle intact: come only a few days and you
	are paid for those days only. Dropping the gate entirely would smooth it
	further but would start paying credit at eight days attended, which is the
	principle DTC did not want.

	LB-05 is why a credit behaves like pay rather than leave: nothing carries
	forward and every credit is encashed in the same month.

	Full attendance still earns the full class - four periods of 7.5 days close
	inside 30. The cap is belt and braces for a cadence and class total that
	disagree; the rule set refuses to save such a pair anyway.

	A NEW JOINER CANNOT REACH THE GATE in their first part-month, so they earn
	nothing and are paid for the days they worked. That follows from the rule as
	stated, and is flagged for DTC rather than quietly worked around.
	"""
	if not period_days or period_days <= 0:
		return 0.0
	if not credit_per_period or credit_per_period <= 0:
		return 0.0
	if days_present < threshold_days:
		return 0.0
	attended = max(0.0, min(float(days_present), float(month_days)))
	periods = int((attended + PERIOD_EPSILON) // float(period_days))
	earned = periods * float(credit_per_period)
	cap = float(monthly_cap or 0)
	return min(earned, cap) if cap > 0 else earned


def find_slab(slabs, percent):
	"""The one row covering this percentage.

	`slabs` is a list of objects with percent_from, percent_to, quarters_off and
	raises_red - the child rows of a rule set, or anything shaped like them.

	percent_to is exclusive so the rows meet without overlapping, with one
	exception: the last row has to include 100 itself, or a full day's
	attendance would match nothing. The rule set controller has already
	refused to save a table with a gap or an overlap, so exactly one row
	matches and returning the first is not a tie-break.
	"""
	ordered = sorted(slabs, key=lambda r: float(r.percent_from))
	for row in ordered:
		lo, hi = float(row.percent_from), float(row.percent_to)
		if lo <= percent < hi:
			return row
	# The top of the table, inclusive.
	if ordered and percent >= float(ordered[-1].percent_from):
		return ordered[-1]
	return None


def _window_applies(window_from, window_to, shift_start, grace_minutes):
	"""Whether the late window can honestly be called late for this shift.

	ATT-04 is written as a clock time (11:00-11:30), which only means "late" on
	a shift starting before it. DTC run shifts starting 08:30 to 12:00. On the
	11:00 shift, arriving 11:00 is on time; on the 11:30 and 12:00 shifts it is
	early. The rule as written would charge all three.

	Returning False leaves those employees alone rather than quietly inventing
	a different rule for them. If DTC want the window to follow the shift, that
	is a change to the rule, not something to guess at here.

	CONFIRMED by Surbhi on 15 October 2026, shift by shift: on an 08:30 shift
	arriving 11:00 is late and charges; on an 11:00 shift it is on time and the
	rule is skipped; on an 11:30 or 12:00 shift it is early and the rule is
	skipped. So this is a settled decision, not an open question.

	All times are minutes from midnight.
	"""
	if window_from is None or window_to is None:
		return False
	return window_from > shift_start + grace_minutes


def _judge_other_half(v, shift_minutes, first_in, last_out, punch_count, regularised,
                      slabs, doubles, multiplier, earns_marks):
	"""The worked half of a half-day leave day (slice 063; 01d D1-D5, OD-1 iv).

	Surbhi, 21 Oct 2026. Frappe does not record WHICH half was the leave, so
	arriving "late" or leaving "early" may be the leave itself: no late, early or
	late-window charge, and no green mark (D4). The other half is measured
	against HALF the shift on the same slab table, losing at most two quarters
	before any special-day doubling. Reds come only from the slab.

	Fewer than two punches: absent (doubled on a special day), unless HR has
	approved a half-day correction for that half - then it counts as worked in
	full, with no punch needed (OD-1 remedy iv). A full day corrected with no
	punches is still HELD by the rules above; this difference is hers, by name.
	"""
	v.half_leave = True
	v.reasons.append("Half-day leave: half the day is approved leave, funded at month level.")

	if punch_count >= 2 and first_in is not None and last_out is not None:
		half = shift_minutes / 2.0
		worked = max(0, last_out - first_in)
		percent = min(100.0, worked / half * 100.0)
		v.attendance_percent = percent
		v.reasons.append(
			"Other half: present {0:.0f} of {1:.0f} minutes (half the shift), {2:.1f}%."
			.format(worked, half, percent))
		row = find_slab(slabs, percent)
		if row is None:
			v.held = True
			v.reasons.append(
				"Held: no slab row covers {0:.1f}%. The rule set has a gap and cannot "
				"judge this half.".format(percent))
			return v
		quarters = min(HALF_DAY_QUARTERS, int(row.quarters_off or 0))
		v.reds = 1 if (row.raises_red and earns_marks) else 0
		v.reasons.append("Slab {0}-{1}%: {2} quarter(s) off, at most 2 on a half day{3}."
		                 .format(row.percent_from, row.percent_to, quarters,
		                         ", 1 red" if v.reds else ", no red"))
	elif regularised:
		v.attendance_percent = 100.0
		v.reasons.append(
			"Other half: a punch is missing, and HR approved a half-day correction, so "
			"the half counts as worked in full.")
		return v
	else:
		v.absent = True
		quarters = HALF_DAY_QUARTERS
		v.reasons.append(
			"Other half: no complete pair of punches and no approved correction, so it "
			"counts as absent.")

	if doubles and quarters:
		v.reasons.append("Special day: {0} quarter(s) multiplied by {1} to {2}."
		                 .format(quarters, multiplier, quarters * multiplier))
		quarters = quarters * multiplier
		v.doubled = True
	v.slab_quarters = quarters
	v.reasons.append("No late, early or late-window charge and no green mark on a "
	                 "half-day leave day.")
	return v


def evaluate_day(
	*,
	shift_start,
	shift_end,
	first_in,
	last_out,
	punch_count,
	marked_absent=False,
	marked_on_leave=False,
	confirmed_out=None,
	grace_minutes=0,
	slabs=None,
	is_special_day=False,
	special_day_multiplier=1,
	double_deduction_applies=False,
	late_window_from=None,
	late_window_to=None,
	late_window_extra_quarters=0,
	late_window_flagged=False,
	night_green_eligible=False,
	morning_green_eligible=True,
	earns_marks=True,
	half_day_leave=False,
	other_half_regularised=False,
) -> DayVerdict:
	"""Judge one employee on one day.

	Every time is minutes from midnight. `first_in` and `last_out` may be None
	on a day with no usable punches.

	`half_day_leave` (slice 063): half of the day is approved leave. The other
	half is judged by `_judge_other_half`. `other_half_regularised` says HR
	approved a half-day correction for that half (OD-1 remedy iv).
	"""
	v = DayVerdict()
	slabs = slabs or []

	shift_minutes = shift_end - shift_start
	if shift_minutes <= 0:
		v.held = True
		v.reasons.append(
			"Held: the shift has no length, so attendance cannot be measured as a "
			"percentage of it. Fix the shift before this day can be judged.")
		return v

	if half_day_leave:
		return _judge_other_half(
			v, shift_minutes, first_in, last_out, punch_count, other_half_regularised,
			slabs, is_special_day and double_deduction_applies and special_day_multiplier > 1,
			special_day_multiplier, earns_marks)

	# ── A genuine absence, versus a day nobody can measure ───────────────────
	# Three cases look alike from a distance and must not be treated alike.
	#
	#   No punches, marked absent. A real absence. 0% is a measurement here,
	#   the slab charges the full day, and a special day doubles it (WSD-04).
	#
	#   One punch (ATT-06). Somebody came in and the check-out is missing. 0%
	#   would be the absence of a measurement, not a measurement of absence,
	#   and feeding it to the slab would dock a day's pay for a missed button.
	#
	#   No punches at all, yet marked present. Somebody marked this by hand.
	#   Deducting would contradict the person who marked it; paying it in full
	#   would make a hand-marked day the cheapest way to skip one. Held, so a
	#   human decides.
	# ── Approved leave is not an absence, and not a mystery ─────────────────
	# Without this a leave day falls into the no-punch branch below and is
	# HELD - which reads as "nobody can say what happened" when in fact
	# somebody approved it. It would then sit waiting for a manager to confirm
	# a day that was never in doubt.
	if marked_on_leave:
		v.on_leave = True
		v.reasons.append(
			"Approved leave. No quarters, no marks; the day is funded by a "
			"leave credit in the monthly total.")
		return v

	if punch_count == 1:
		# ATT-06, as settled on 9 October 2026. A confirmation does NOT pay the
		# day in full - it supplies the missing time. Whoever confirms it says
		# when the employee actually left, and the day is then measured from
		# that like any other.
		#
		# That is the stricter reading and the right one. Paying in full would
		# make a forgotten punch better than an honest early departure, and
		# people learn rules like that.
		if confirmed_out is None:
			v.held = True
			v.reasons.append(
				"Held: only one punch, so there is no way to tell when the "
				"employee left. Neither paid nor deducted until somebody "
				"confirms the time.")
			return v
		last_out = confirmed_out
		punch_count = 2
		v.reasons.append(
			"Check-out missing and confirmed afterwards as {0:02d}:{1:02d}. "
			"The day is measured from that time, not paid in full."
			.format(int(confirmed_out) // 60, int(confirmed_out) % 60))

	if first_in is None or last_out is None:
		if marked_absent:
			percent = 0.0
			v.absent = True
			v.reasons.append("Marked absent with no punches: 0% of the shift.")
		else:
			v.held = True
			v.reasons.append(
				"Held: no punches at all, yet the day is not marked absent. "
				"Somebody marked this day by hand and only they can say what it "
				"should pay.")
			return v
	else:
		# ── ATT-01: the employee's own gross shift is the denominator ────────
		worked = max(0, last_out - first_in)
		percent = min(100.0, worked / shift_minutes * 100.0)
		v.reasons.append(
			"Present {0:.0f} of {1:.0f} shift minutes, {2:.1f}% of the shift."
			.format(worked, shift_minutes, percent))

		# ── GBL-04: the two infractions ──────────────────────────────────────
		v.late_arrival = first_in > shift_start + grace_minutes
		v.early_departure = last_out < shift_end
		if v.late_arrival:
			v.reasons.append(
				"Arrived {0:.0f} minutes after shift start, past the {1} minute grace."
				.format(first_in - shift_start, grace_minutes))
		if v.early_departure:
			v.reasons.append(
				"Left {0:.0f} minutes before shift end.".format(shift_end - last_out))

	v.attendance_percent = percent

	# ── ATT-03: the slab ─────────────────────────────────────────────────────
	row = find_slab(slabs, percent)
	if row is None:
		# The controller refuses to save a table with a hole, so this means the
		# rule set was written round it - by a fixture, a patch or a direct
		# database edit. Holding is the only safe answer: paying the day in
		# full is a silent gift and deducting it is a silent theft.
		v.held = True
		v.reasons.append(
			"Held: no slab row covers {0:.1f}%. The rule set has a gap and cannot "
			"judge this day.".format(percent))
		return v

	slab_quarters = int(row.quarters_off or 0)
	slab_red = bool(row.raises_red)
	v.reasons.append(
		"Slab {0}-{1}%: {2} quarter(s) off{3}."
		.format(row.percent_from, row.percent_to, slab_quarters,
		        ", 1 red" if slab_red else ", no red"))

	# ── WSD-01/02: the special day multiplier, on slab quarters only ─────────
	if is_special_day and double_deduction_applies and special_day_multiplier > 1:
		doubled = slab_quarters * special_day_multiplier
		if doubled != slab_quarters:
			v.reasons.append(
				"Special day: {0} quarter(s) multiplied by {1} to {2}. Reds are not "
				"multiplied.".format(slab_quarters, special_day_multiplier, doubled))
		slab_quarters = doubled
		v.doubled = True
	elif is_special_day and not double_deduction_applies:
		v.reasons.append(
			"Special day, but this employee takes the single deduction, so the "
			"quarters are not multiplied.")
	v.slab_quarters = slab_quarters

	# ── ATT-03 + the 8 Oct ruling: how many reds ─────────────────────────────
	# The band supplies the first red. The second needs both infractions AND no
	# slab quarter - a quarter already charges the missing minutes, so a second
	# red for the same minutes is the double penalty GBL-09 forbids. The
	# comparison is against the slab quarters BEFORE doubling, because doubling
	# changes the size of a deduction, not whether one happened.
	v.reds = 1 if slab_red else 0
	if slab_red and v.late_arrival and v.early_departure:
		if int(row.quarters_off or 0) == 0:
			v.reds = 2
			v.reasons.append(
				"Two reds: late in and early out, and the band deducted no quarters, "
				"so neither infraction has been charged for yet.")
		else:
			v.reasons.append(
				"One red, not two: late in and early out, but the band already "
				"deducted {0} quarter(s) for the missing time. Charging a second red "
				"for the same minutes would be a double penalty."
				.format(int(row.quarters_off or 0)))

	# ── ATT-04: the late window ──────────────────────────────────────────────
	# A separate dimension from the slab (GBL-09), so it stacks on the quarters
	# and suppresses no red. Never multiplied on a special day.
	if first_in is not None and late_window_flagged and _window_applies(
			late_window_from, late_window_to, shift_start, grace_minutes):
		if late_window_from <= first_in <= late_window_to:
			v.late_window_hit = True
			v.extra_quarters = int(late_window_extra_quarters or 0)
			v.reasons.append(
				"Late window: checked in inside the window, so {0} extra quarter(s). "
				"This charges the window of arrival, not the minutes missed, so it "
				"stands alongside the slab and is never doubled."
				.format(v.extra_quarters))

	# ── Contract staff carry no marks ────────────────────────────────────────
	# Settled 9 October 2026: pantry, driver, housekeeping and the like lose
	# quarters for time missed exactly as anyone else does - half days and
	# quarters apply - but they neither lose reds nor earn greens. Their grace
	# period is longer too, and that arrives as `grace_minutes`, so by this
	# point lateness has already been judged on their own terms.
	if not earns_marks:
		if v.reds:
			v.reasons.append(
				"No red: this category carries no marks. The quarters above still "
				"charge the time that was missed.")
		v.reds = 0
		return v

	# ── GRN-02/03: greens ────────────────────────────────────────────────────
	# Nobody earns a green on a day they did not turn up for.
	if first_in is None or last_out is None:
		return v

	if morning_green_eligible and first_in <= shift_start - MORNING_GREEN_EARLY_MINUTES:
		v.greens += 1
		v.reasons.append(
			"Morning green: in {0:.0f} minutes early.".format(shift_start - first_in))
	if night_green_eligible and last_out >= shift_end + NIGHT_GREEN_LATE_MINUTES:
		v.greens += 1
		v.reasons.append(
			"Night green: out {0:.0f} minutes late.".format(last_out - shift_end))

	return v
