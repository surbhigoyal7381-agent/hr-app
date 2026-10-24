"""A month of days, added up into the figures a salary slip needs.

`payroll_rules.evaluate_day` judges one day. This adds a month of those
judgments together, applies the rules that only exist at month level - the
leave gate, the free red allowance, encashment against approved leave - and
hands back paid days and money.

Pure, like the daily engine: numbers in, numbers out, no database. The month's
arithmetic is where a payslip is either right or wrong, so it has to be
testable without a site.

THE SALARY FORMULA, as the client states it (SAL):

    daily rate   = Basic / actual days in the month        (GBL-02)
    paid days    = day credits + leave credits
    earning basic= paid days x daily rate
    gross        = earning basic + greens + incentive
    red deduction= max(0, reds - free allowance) x mark rate
    net          = gross - deductions

TWO PLACES THIS DEPARTS FROM THE DOCUMENT'S WORKED EXAMPLES, both following
corrections the client has already made:

  A held day is excluded from everything (ATT-06). It is not a present day, it
  is not an absence, and it must not be netted off - it is released later as an
  Arrear. Counting it either way would settle a question nobody has answered.

  An approved leave day is PAID, funded by a credit (LB-02). The document's
  Anil example leaves such a day out of present days and also out of the
  encashment, so the day falls through the floor unpaid. Under correction C-1 -
  "every day an employee is owed salary for, they get" - a day covered by a
  credit is owed. So paid days come to day credits plus the whole credit
  entitlement, and the split between "used for leave" and "encashed" is
  reporting, not arithmetic. FLAGGED FOR DTC: it is worth one day's pay per
  leave day taken.

  Leave taken beyond the credits is simply unpaid. There is no credit left to
  fund it, and nothing here invents one.
"""

from dataclasses import dataclass, field

from alvoraa_portal.payroll_rules import leave_credits_for_month


@dataclass
class MonthSummary:
	"""Everything a salary slip needs, and the workings behind it."""

	# attendance
	days_with_record: int = 0
	# Decimals since slice 063: a half-day leave day is half worked (or half
	# absent, or half held) and half on leave.
	days_worked: float = 0
	days_held: float = 0
	days_absent: float = 0
	days_on_leave: float = 0
	# Days worked plus approved Paid Leaves days: what the 15-day gate reads (E6).
	days_for_gate: float = 0
	total_quarters: int = 0

	# leave
	leave_credits_earned: float = 0.0
	leave_used_for_approved: float = 0.0
	leave_encashed: float = 0.0
	approved_leave_unpaid: float = 0.0

	# days and money
	day_credits: float = 0.0
	paid_days: float = 0.0
	daily_rate: float = 0.0
	earning_basic: float = 0.0

	# marks
	reds: int = 0
	greens: int = 0
	free_reds: int = 0
	deductible_reds: int = 0
	mark_rate: float = 0.0
	red_deduction: float = 0.0
	green_earning: float = 0.0

	# grooming reds (slice 066): days marked, the money, and whether the legal
	# limit cut it
	grooming_days: int = 0
	grooming_deduction: float = 0.0
	grooming_capped: bool = False

	incentive: float = 0.0
	gross: float = 0.0
	other_deductions: float = 0.0
	net: float = 0.0

	notes: list = field(default_factory=list)

	@property
	def quarter_days(self) -> float:
		return self.total_quarters / 4.0


def summarise_month(
	verdicts,
	*,
	basic=0.0,
	month_days=30,
	approved_leave_days=None,
	# leave class, as the rule set holds it
	earns_leave_credits=True,
	period_days=0.0,
	credit_per_period=0.0,
	monthly_cap=0.0,
	threshold_days=15,
	accrual_month_days=30,
	# marks
	earns_marks=True,
	free_reds=0,
	mark_rate=0.0,
	grooming_days=0,
	# things that arrive from outside the attendance system
	incentive=0.0,
	other_deductions=0.0,
) -> MonthSummary:
	"""Add a month of daily verdicts together.

	`verdicts` is a list of `DayVerdict`, one per attendance record in the
	period. Days with no attendance record at all are not represented and are
	not paid - which is correct, because the client works a seven-day week and
	an unrecorded day is an unworked one.
	"""
	m = MonthSummary()
	m.days_with_record = len(verdicts)

	for v in verdicts:
		m.total_quarters += v.total_quarters
		m.day_credits += v.day_credit
		if v.half_leave:
			m.days_on_leave += 0.5
			if v.held:
				m.days_held += 0.5
			elif v.absent:
				m.days_absent += 0.5
			else:
				m.days_worked += 0.5
				m.reds += v.reds
			continue
		if v.held:
			m.days_held += 1
			continue
		if v.on_leave:
			m.days_on_leave += 1
			continue
		if v.absent:
			m.days_absent += 1
			continue
		m.days_worked += 1
		m.reds += v.reds
		m.greens += v.greens

	if m.days_held:
		m.notes.append(
			"{0} day(s) held for a missing check-out. Neither paid nor deducted "
			"here; each is released as an Arrear once a manager confirms it."
			.format(m.days_held))

	# ── the leave gate, then the credit, on days attended ────────────────────
	# E6 (Surbhi, 21 Oct 2026): approved Paid Leaves days count toward the gate,
	# so taking your own leave properly never costs you all of it. They arrive
	# as `approved_leave_days` - the caller counts them from the attendance
	# (payroll_slip.month_summary). A caller that passes nothing gets the
	# gate on days worked alone, as before.
	m.days_for_gate = m.days_worked + max(0.0, float(approved_leave_days or 0))
	if earns_leave_credits:
		m.leave_credits_earned = leave_credits_for_month(
			m.days_for_gate, period_days, credit_per_period, monthly_cap,
			threshold_days=threshold_days, month_days=accrual_month_days)
		if m.days_for_gate < threshold_days and period_days:
			m.notes.append(
				"{0} days attended is under the {1}-day gate, so no leave credit. "
				"Paid for the days worked and nothing else."
				.format(m.days_for_gate, threshold_days))
	else:
		m.notes.append("This category earns no leave class.")

	# ── LB-02: credits cover approved leave first, the surplus is cash ───────
	# Leave days come from the attendance itself unless the caller overrides.
	# Deriving it is the safer default: a figure passed in by hand can disagree
	# with the records it is meant to describe. Since slice 063 the caller
	# passes approved Paid Leaves days only (U1): a Leave Without Pay day is not
	# "used" from the credits, it is simply unpaid.
	approved = (float(approved_leave_days) if approved_leave_days is not None
	            else float(m.days_on_leave))
	approved = max(0.0, approved)
	m.leave_used_for_approved = min(m.leave_credits_earned, approved)
	m.leave_encashed = m.leave_credits_earned - m.leave_used_for_approved
	m.approved_leave_unpaid = approved - m.leave_used_for_approved
	if m.approved_leave_unpaid:
		m.notes.append(
			"{0} approved leave day(s) had no credit left to fund them and are "
			"unpaid.".format(m.approved_leave_unpaid))

	# A day covered by a credit is paid, and a surplus credit adds a day. Both
	# are worth one day, so paid days need the WHOLE entitlement, not just the
	# encashed part. The split above is for the payslip to show, not to
	# subtract twice.
	m.paid_days = m.day_credits + m.leave_credits_earned

	# ── money ────────────────────────────────────────────────────────────────
	m.daily_rate = (float(basic) / month_days) if month_days else 0.0
	m.earning_basic = m.paid_days * m.daily_rate

	m.free_reds = int(free_reds or 0)
	m.mark_rate = float(mark_rate or 0)
	if not earns_marks:
		m.reds = 0
		m.greens = 0
	m.deductible_reds = max(0, m.reds - m.free_reds)
	m.red_deduction = m.deductible_reds * m.mark_rate
	m.green_earning = m.greens * m.mark_rate

	# ── grooming reds (slice 066): every marked day at the grade's rate, no
	# free allowance, and never above 3% of the month's earned Basic - the
	# back-stop behind the stop at marking (SEC-10, D2). Pending counsel on
	# what "wages payable" is; the earned Basic is the smaller figure, so it
	# errs toward the employee.
	m.grooming_days = int(grooming_days or 0) if earns_marks else 0
	full = m.grooming_days * m.mark_rate
	limit = round(0.03 * m.earning_basic, 2)
	m.grooming_deduction = min(full, limit)
	m.grooming_capped = full > limit
	if m.grooming_capped:
		m.notes.append("{0} grooming reds at ₹{1:,.0f}, capped at ₹{2:,.0f} by the legal "
		               "limit.".format(m.grooming_days, m.mark_rate, limit))
	elif m.grooming_days:
		m.notes.append("{0} grooming reds at ₹{1:,.0f}.".format(m.grooming_days, m.mark_rate))

	m.incentive = float(incentive or 0)
	m.other_deductions = float(other_deductions or 0)
	m.gross = m.earning_basic + m.green_earning + m.incentive
	m.net = m.gross - m.red_deduction - m.grooming_deduction - m.other_deductions
	return m
