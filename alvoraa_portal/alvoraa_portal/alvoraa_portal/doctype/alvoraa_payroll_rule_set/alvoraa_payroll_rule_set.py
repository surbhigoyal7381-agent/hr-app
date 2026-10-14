"""One tenant's payroll rules, held as data.

The engine that reads this lives in `payroll_rules.py` and is the same code for
every tenant. What differs per tenant is this record. That is the whole point:
DTC's slab table, grace period and mark rates are configuration, so a second
client with a different table needs a second record and no second branch.

Everything below exists because a wrong rule set is silent. A gap in the slab
table does not raise an error at payroll time - it just returns no row, and
somebody is paid as though they worked a full day. So the checks run here, at
save, where a person is watching:

  The slabs must tile 0 to 100 exactly. No gap, no overlap. A gap pays by
  accident; an overlap means two rows match and the answer depends on row
  order, which nobody intended to be a rule.

  A grade may appear once in the rates. Twice and a red is worth two amounts.

  The special day list must not be anybody's holiday list. Special days are
  high-footfall days that carry a DOUBLE deduction - the opposite of a day off.
  Attached as a holiday list it would make them non-working, and the deduction
  would never fire.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from alvoraa_portal.payroll_rules import leave_credits_for_month


# Where the slab table has to start and stop. Attendance is a percentage, and
# the engine clamps to this range before it looks a row up, so a table that
# does not cover it has a hole the engine cannot report.
PCT_FLOOR = 0.0
PCT_CEIL = 100.0

# Float equality is not safe on figures a person typed - 98.9 does not round
# trip. Two edges within this many percentage points are treated as meeting.
TOUCHING = 0.001


class AlvoraaPayrollRuleSet(Document):
	def validate(self):
		self._normalise()
		self._check_slabs()
		self._check_rates()
		self._check_late_window()
		self._check_leave()
		self._check_categories()
		self._check_special_day_list()

	def _normalise(self):
		"""Blank number fields arrive as None, not 0.

		Frappe only fills a default when the field declares one, and a None
		reaching an arithmetic comparison raises a TypeError the user sees as an
		internal server error with no hint which field was left empty.
		"""
		self.grace_minutes = cint(self.grace_minutes)
		self.free_reds_per_month = cint(self.free_reds_per_month)
		self.special_day_multiplier = cint(self.special_day_multiplier) or 1
		self.late_window_extra_quarters = cint(self.late_window_extra_quarters)
		self.grade_field = (self.grade_field or "").strip()
		self.late_window_employee_field = (self.late_window_employee_field or "").strip()

		if self.grace_minutes < 0:
			frappe.throw(_("Grace minutes cannot be negative."))
		if self.free_reds_per_month < 0:
			frappe.throw(_("Free reds per month cannot be negative."))
		if self.special_day_multiplier < 1:
			frappe.throw(_("The special day multiplier has to be 1 or more. "
			               "1 means special days are treated like any other day."))

	def _check_slabs(self):
		if not self.slabs:
			frappe.throw(_("A rule set needs a slab table. Without one the engine has "
			               "no way to turn an attendance percentage into a deduction."))

		rows = []
		for row in self.slabs:
			row.percent_from = flt(row.percent_from)
			row.percent_to = flt(row.percent_to)
			row.quarters_off = cint(row.quarters_off)
			if row.percent_to <= row.percent_from:
				frappe.throw(
					_("Row {0}: the band ends at {1}% but starts at {2}%. "
					  "A band has to move forwards.")
					.format(row.idx, row.percent_to, row.percent_from))
			if not 0 <= row.quarters_off <= 4:
				frappe.throw(
					_("Row {0}: {1} quarters. A day is four quarters, so the figure "
					  "has to be between 0 and 4.")
					.format(row.idx, row.quarters_off))
			rows.append(row)

		rows.sort(key=lambda r: r.percent_from)

		if abs(rows[0].percent_from - PCT_FLOOR) > TOUCHING:
			frappe.throw(
				_("The slab table starts at {0}%, not 0%. Attendance below that would "
				  "match no row, and the engine would pay the day in full.")
				.format(rows[0].percent_from), title=_("Gap in the slab table"))

		for earlier, later in zip(rows, rows[1:]):
			if later.percent_from < earlier.percent_to - TOUCHING:
				frappe.throw(
					_("Rows {0} and {1} overlap: {2}% to {3}% and {4}% to {5}%. "
					  "An attendance figure in the overlap matches both rows, so which "
					  "deduction applies would depend on row order.")
					.format(earlier.idx, later.idx, earlier.percent_from,
					        earlier.percent_to, later.percent_from, later.percent_to),
					title=_("Overlapping slabs"))
			if later.percent_from > earlier.percent_to + TOUCHING:
				frappe.throw(
					_("Nothing covers {0}% to {1}%, between rows {2} and {3}. "
					  "Attendance in that gap would match no row, and the day would be "
					  "paid in full by accident. Extend one of the two bands to meet "
					  "the other.")
					.format(earlier.percent_to, later.percent_from,
					        earlier.idx, later.idx),
					title=_("Gap in the slab table"))

		if abs(rows[-1].percent_to - PCT_CEIL) > TOUCHING:
			frappe.throw(
				_("The slab table stops at {0}%, not 100%. A full day's attendance "
				  "would match no row.")
				.format(rows[-1].percent_to), title=_("Gap in the slab table"))

	def _check_rates(self):
		seen = {}
		for row in self.mark_rates:
			grade = (row.grade or "").strip()
			row.grade = grade
			row.amount_per_mark = flt(row.amount_per_mark)
			if not grade:
				frappe.throw(_("Row {0} of the mark rates has no grade.").format(row.idx))
			if row.amount_per_mark < 0:
				frappe.throw(
					_("Row {0}: a mark cannot be worth a negative amount. The same "
					  "figure is deducted for a red and added for a green.")
					.format(row.idx))
			if grade in seen:
				frappe.throw(
					_("Grade {0} is listed twice, in rows {1} and {2}. A red would be "
					  "worth two different amounts.")
					.format(frappe.bold(grade), seen[grade], row.idx))
			seen[grade] = row.idx

		if self.enabled and not self.mark_rates:
			frappe.throw(_("A rule set cannot be switched on with no mark rates. Reds "
			               "and greens would all be worth nothing."))

	def _check_late_window(self):
		"""The late window is optional, and partly filled is worse than empty."""
		has_window = bool(self.late_window_from and self.late_window_to)
		if not has_window:
			if self.late_window_from or self.late_window_to:
				frappe.throw(_("The late arrival window needs both a start and an end, "
				               "or neither."))
			return
		if str(self.late_window_to) <= str(self.late_window_from):
			frappe.throw(_("The late arrival window ends before it starts."))
		# No employee field is fine, and means the window applies to everybody.
		# This used to be refused, on the grounds that the rule was for flagged
		# staff only - but it is not: Surbhi settled on 15 October 2026 that it
		# applies to everyone, and the employee's own shift timing is what
		# decides whether it bites. A shift starting at or after the window is
		# skipped, so a person arriving 11:00 for an 11:00 shift is on time.
		#
		# Naming a field still narrows it, for a tenant that wants a subset.
		if not self.late_window_extra_quarters:
			frappe.throw(_("The late arrival window is set but adds no quarters, so it "
			               "would do nothing. Clear the window or set the quarters."))

	def _check_leave(self):
		"""One threshold, and a credit figure per class.

		Settled 9 October 2026, replacing the per-period accrual given the same
		day. Below the threshold an employee earns nothing; at it they earn the
		whole class. Because the rule is a cliff rather than a slope, the
		threshold is the single number that decides four days of pay for 230
		people, so it is worth refusing nonsense here.
		"""
		self.accrual_month_days = cint(self.accrual_month_days) or 30
		self.leave_threshold_days = cint(self.leave_threshold_days)
		if self.leave_threshold_days < 0:
			frappe.throw(_("The leave threshold cannot be negative."))
		if self.leave_threshold_days > 31:
			frappe.throw(
				_("A threshold of {0} days present can never be reached in a "
				  "month, so no employee would ever earn leave.")
				.format(self.leave_threshold_days))

		seen = {}
		for row in self.leave_classes:
			cls = (row.leave_class or "").strip()
			row.leave_class = cls
			row.monthly_credits = flt(row.monthly_credits)
			if not cls:
				frappe.throw(_("Row {0} of the leave classes has no class.")
				             .format(row.idx))
			if cls in seen:
				frappe.throw(
					_("Leave class {0} is listed twice, in rows {1} and {2}. It "
					  "would be worth two different numbers of days.")
					.format(frappe.bold(cls), seen[cls], row.idx))
			seen[cls] = row.idx
			row.period_days = flt(row.period_days)
			row.credit_per_period = flt(row.credit_per_period)
			if row.monthly_credits < 0:
				frappe.throw(_("Row {0}: a class cannot credit negative days.")
				             .format(row.idx))
			if row.period_days <= 0 or row.credit_per_period <= 0:
				frappe.throw(
					_("Row {0}, class {1}: a cadence of {2} every {3} days would "
					  "never credit anything.")
					.format(row.idx, frappe.bold(cls), row.credit_per_period,
					        row.period_days))

			# The cadence and the cap are two statements of the same thing, so
			# they can disagree. 7.5 mistyped as 7 would credit a fifth day
			# every month to 230 people, and the cap would hide it rather than
			# report it. Checking at full attendance costs nothing here.
			at_full = leave_credits_for_month(
				self.accrual_month_days, row.period_days, row.credit_per_period,
				monthly_cap=0, threshold_days=0,
				month_days=self.accrual_month_days)
			if abs(at_full - row.monthly_credits) > 0.001:
				frappe.throw(
					_("Row {0}, class {1}: {2} every {3} days attended comes to {4} "
					  "over a {5}-day month, not the {6} expected. Either the "
					  "cadence or the cap is wrong, and a payslip is a bad place "
					  "to find out which.")
					.format(row.idx, frappe.bold(cls), row.credit_per_period,
					        row.period_days, at_full, self.accrual_month_days,
					        row.monthly_credits),
					title=_("The cadence does not add up"))

		if self.enabled and self.leave_classes and not self.leave_class_field:
			frappe.throw(
				_("Leave is credited by class, so it needs the Employee field "
				  "that holds the class. Without it no employee can be matched "
				  "to a figure."))

	def _check_categories(self):
		"""Per-category exceptions, and the field that selects them.

		A category listed here with marks switched off is how contract staff
		are handled: they lose quarters for time missed like anybody else, but
		carry no reds and earn no greens, and their grace is longer.
		"""
		seen = {}
		for row in self.categories:
			cat = (row.category or "").strip()
			row.category = cat
			row.grace_minutes = cint(row.grace_minutes)
			if not cat:
				frappe.throw(_("Row {0} of the categories has no value.")
				             .format(row.idx))
			if cat in seen:
				frappe.throw(
					_("Category {0} is listed twice, in rows {1} and {2}.")
					.format(frappe.bold(cat), seen[cat], row.idx))
			seen[cat] = row.idx
			if row.grace_minutes < 0:
				frappe.throw(_("Row {0}: grace cannot be negative.").format(row.idx))

		if self.enabled and self.categories and not self.category_field:
			frappe.throw(
				_("Category overrides are configured, so they need the Employee "
				  "field that holds the category. Without it every employee "
				  "would silently take the defaults and the overrides would do "
				  "nothing at all."))

	def _check_special_day_list(self):
		"""A special day is a working day with a doubled penalty, not a day off.

		Attached to anyone as their holiday list it becomes non-working, no
		attendance is expected, and the doubling it exists for never fires.
		"""
		if not self.special_day_holiday_list:
			return
		used_by = frappe.get_all(
			"Employee",
			filters={"holiday_list": self.special_day_holiday_list, "status": "Active"},
			fields=["name", "employee_name"], limit=5)
		if used_by:
			names = ", ".join("{0} ({1})".format(e.employee_name, e.name) for e in used_by)
			frappe.throw(
				_("{0} is set as the holiday list for {1}. Special days are working "
				  "days that carry a doubled deduction, so marking them as holidays "
				  "would stop the deduction firing at all. Use a separate list.")
				.format(frappe.bold(self.special_day_holiday_list), names),
				title=_("Special days are not holidays"))

		shifts = frappe.get_all(
			"Shift Type", filters={"holiday_list": self.special_day_holiday_list},
			pluck="name", limit=5)
		if shifts:
			frappe.throw(
				_("{0} is set as the holiday list on shift {1}. Special days are "
				  "working days, not holidays. Use a separate list.")
				.format(frappe.bold(self.special_day_holiday_list), ", ".join(shifts)),
				title=_("Special days are not holidays"))
