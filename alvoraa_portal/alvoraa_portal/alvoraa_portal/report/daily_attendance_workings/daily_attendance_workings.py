# Copyright (c) 2026, Alvoraa and contributors
# For license information, please see license.txt

"""One person's month, a day per row, as the pay rules judged it (ALV-358).

Asked for on 18 Nov 2026 to match the per-employee sheet DTC's own software
prints: in, out, minutes, (-/+), status, quarters, red, green, leave, fine,
remarks and shift, with the month's totals underneath.

NOTHING IS WORKED OUT HERE. Every day comes from `payroll_rules_apply.judge`
and every total from `payroll_slip.month_summary` - the same two calls the
salary slip and the Salary Components and Workings report make. So this report
cannot disagree with either; it only shows the days behind their totals.

Like that report it reads the company's rule set even when the set is switched
off (`_rules_for_reading`), and it writes nothing.

Two settled points (Surbhi, 18 Nov 2026):
  * a day with a punch missing shows HELD, as the rules hold it - not the four
    quarters DTC's own software charges;
  * Fine is the grooming red deduction. It shows on the month's total row
    only: grooming marks are read for the fine and nowhere else (slice 066,
    PRIV-5, fenced by test_ac73), so this report never reads the marks or
    their dates. The total comes from month_summary, like the slip's.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, get_first_day, get_last_day, getdate

from alvoraa_portal.alvoraa_portal.report.salary_components_and_workings.salary_components_and_workings import (
	_may_read_days_of,
	_rules_for_reading,
)
from alvoraa_portal.payroll_rules import minutes_on_break
from alvoraa_portal.payroll_rules_apply import LEAVE_FIELDS, _punches, judge, prepare
from alvoraa_portal.payroll_slip import month_summary

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def execute(filters=None):
	filters = frappe._dict(filters or {})
	employee = filters.get("employee")
	if not employee:
		frappe.throw(_("Choose an employee."))

	# Read through get_list, so the user's own permissions decide whether they
	# may see this person at all - the same scoping the monthly report uses.
	emp = frappe.get_list("Employee", filters={"name": employee},
	                      fields=["name", "employee_name", "company", "default_shift",
	                              "date_of_joining", "relieving_date"], limit_page_length=1)
	if not emp or not _may_read_days_of(employee):
		frappe.throw(_("You cannot see this employee's attendance."), frappe.PermissionError)
	emp = emp[0]

	year = cint(filters.get("year")) or getdate().year
	month = MONTHS.index(filters.get("month")) + 1 if filters.get("month") in MONTHS else getdate().month
	from_date = get_first_day("%d-%02d-01" % (year, month))
	to_date = get_last_day(from_date)

	rule_set, live = _rules_for_reading(emp.company)
	if not rule_set:
		return _columns(), [], _(
			"<b>{0}</b> has no payroll rule set, so there is nothing to judge.").format(
				frappe.bold(emp.company))

	ctx = prepare(rule_set, from_date, to_date, employee=employee)
	rows = {str(r.attendance_date): r for r in frappe.get_all(
		"Attendance",
		filters={"docstatus": 1, "employee": employee,
		         "attendance_date": ("between", [from_date, to_date])},
		fields=["name", "employee", "attendance_date", "status", "shift", "company",
		        "alvoraa_held_confirmed", "alvoraa_confirmed_out_time"] + list(LEAVE_FIELDS),
		limit_page_length=0)}
	summary = month_summary(employee, emp.company, from_date, to_date,
	                        rule_set=rule_set, ctx=ctx)
	holidays = _holidays(emp, from_date, to_date)

	data = []
	for i in range(date_diff(to_date, from_date) + 1):
		day = add_days(from_date, i)
		data.append(_day(str(day), emp, rows.get(str(day)), ctx, holidays))
	data.append(_totals(data, summary))
	return _columns(), data, _message(summary, live, ctx, data)


def _day(d, emp, att, ctx, holidays):
	shift_name = (att.shift if att else None) or emp.default_shift
	shift = ctx["shifts"].get(shift_name)
	length = (shift[1] - shift[0]) if shift and shift[1] > shift[0] else None
	# The weekday, so a weekend reads at a glance, and "*" on a special day:
	# a date on the rule set's special-day list, where a deduction is
	# multiplied for staff whose deductions double (Surbhi, 19 Nov 2026).
	special = getdate(d) in ctx["special_days"]
	row = {"date": d, "day": getdate(d).strftime("%a") + (" *" if special else ""),
	       "is_special": 1 if special else 0, "shift": shift_name, "shift_minutes": length}

	first, last, count, gaps = _punches(emp.name, d)
	if count:
		row["in_time"] = _clock(first)
		row["out_time"] = _clock(last) if count > 1 else None
	# Break: the time out between the first and the last punch - the gaps
	# between punch 2 and 3, 4 and 5 (the same break_gaps the engine and the
	# portal use). With an odd count one punch is missing, so nobody can say
	# which gap was a break: it is not measured, exactly as the engine does.
	if count >= 2 and count % 2 == 0:
		row["break_minutes"] = int(round(minutes_on_break(gaps, first, last)))

	if emp.date_of_joining and d < str(emp.date_of_joining):
		row.update(status="", remarks=_("Not yet joined"))
		return row
	if emp.relieving_date and d > str(emp.relieving_date):
		row.update(status="", remarks=_("Left"))
		return row
	if not att:
		if d in holidays:
			row.update(status="Holiday", remarks=holidays[d])
		else:
			row.update(status="", remarks=_("No attendance record for this day"))
		return row

	v = judge(att, ctx)
	row["leave"] = att.get("leave_type") if (v.on_leave or v.half_leave) else None
	if v.on_leave:
		status = "Leave"
	elif v.held:
		status = "Held"
	elif v.absent:
		status = "A"
	elif v.half_leave:
		status = "P (half leave)"
	else:
		status = "P"
	row["status"] = status
	# On a half-day leave the engine judges the OTHER half only, against half
	# the shift (_judge_other_half), so its percent is a share of half the shift.
	expected = (length / 2.0 if v.half_leave else length) if length else None
	if expected and not (v.held or v.on_leave) and not v.absent:
		minutes = int(round(flt(v.attendance_percent) * expected / 100.0))
		row["minutes"] = minutes
		row["difference"] = minutes - int(round(expected))
	elif v.absent and expected:
		row["minutes"] = 0
		row["difference"] = -int(round(expected))
	row["quarters"] = v.total_quarters or None
	# The month never counts a red or green on an absent day (summarise_month),
	# so the day does not show one either - or the column would not add up.
	row["red"] = (v.reds or None) if not v.absent else None
	row["green"] = (v.greens or None) if not v.absent else None
	reasons = list(v.reasons)
	if count >= 3 and count % 2 == 1:
		reasons.append(_("Break not measured: an odd number of punches."))
	row["remarks"] = " ".join(reasons)
	return row


def _totals(days, s):
	"""The month, from month_summary - the slip's own figures, never re-added here."""
	return {
		"date": None,
		"is_total": 1,
		"status": _("P {0} · A {1} · Held {2} · Leave {3}").format(
			flt(s.days_worked, 2), flt(s.days_absent, 2), flt(s.days_held, 2),
			flt(s.days_on_leave, 2)),
		"minutes": sum(r.get("minutes") or 0 for r in days),
		"difference": sum(r.get("difference") or 0 for r in days),
		"break_minutes": sum(r.get("break_minutes") or 0 for r in days),
		"quarters": s.total_quarters,
		"red": s.reds,
		"green": s.greens,
		"leave": flt(s.days_on_leave, 2),
		"fine": flt(s.grooming_deduction, 2),
		"remarks": _("Month total. Quarters = {0} days. Reds {1}, of which {2} free and {3} "
		             "charged. Paid days {4}.").format(
			flt(s.quarter_days, 2), s.reds, min(s.reds, s.free_reds), s.deductible_reds,
			flt(s.paid_days, 2)),
	}


def _holidays(emp, from_date, to_date):
	"""Date -> description, from the list Frappe itself would use on that day:
	the shift's list when the shift names one, else the person's own."""
	from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee

	name = (frappe.db.get_value("Shift Type", emp.default_shift, "holiday_list")
	        if emp.default_shift else None) or get_holiday_list_for_employee(
		emp.name, False, as_on=to_date)
	if not name:
		return {}
	return {str(h.holiday_date): h.description or _("Holiday") for h in frappe.get_all(
		"Holiday", filters={"parent": name, "holiday_date": ("between", [from_date, to_date])},
		fields=["holiday_date", "description"])}


def _clock(minutes):
	if minutes is None:
		return None
	m = int(minutes)
	return "%02d:%02d" % (m // 60, m % 60)


def _message(s, live, ctx=None, days=()):
	bits = []
	if any(r.get("is_special") for r in days):
		bits.append(_("<b>*</b> Special day: a deduction on this day counts {0} times for staff "
		              "whose deductions double. The Remarks say when it was.").format(
			ctx["multiplier"]))
	if not live:
		bits.append(_("<b>These rules are not switched on.</b> The figures below are what "
		              "they WOULD produce; nothing has been charged."))
	bits.append(_("Every day is judged exactly as the salary working judges it. A day with "
	              "a punch missing is <b>Held</b>: neither paid nor deducted until HR "
	              "confirms the time."))
	bits.append(_("Fine (grooming reds) is shown for the month only, on the total row."))
	if s.grooming_capped:
		bits.append(_("The grooming fines were capped by the legal limit."))
	return "<br>".join(bits)


def _columns():
	def c(key, label, width=90, kind="Data", opts=None):
		col = {"fieldname": key, "label": _(label), "fieldtype": kind, "width": width}
		if opts:
			col["options"] = opts
		return col

	return [
		c("date", "Date", 100, "Date"),
		c("day", "Day", 60),
		c("in_time", "In", 70),
		c("out_time", "Out", 70),
		c("minutes", "Minutes", 85, "Int"),
		c("difference", "(-/+) Min", 85, "Int"),
		c("break_minutes", "Break (min)", 90, "Int"),
		c("status", "Status", 90),
		c("quarters", "Quarters", 80, "Int"),
		c("red", "Red", 60, "Int"),
		c("green", "Green", 65, "Int"),
		c("leave", "Leave", 110),
		c("fine", "Fine", 90, "Currency"),
		c("remarks", "Remarks", 420),
		c("shift", "Shift", 200, "Link", "Shift Type"),
		c("shift_minutes", "Shift (min)", 90, "Int"),
	]
