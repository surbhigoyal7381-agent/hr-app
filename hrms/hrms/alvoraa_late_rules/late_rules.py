# Copyright (c) 2026, Alvoraa and contributors
# For license information, please see license.txt

"""The quarter-day late-coming rule.

Every week, for every employee an enabled Attendance Deduction Rule covers, count the
late arrivals and early exits on submitted Attendance, and record an Attendance
Deduction when the counted violations add up to something. The deduction document
itself decides where the days come from (leave balance first, then pay).
"""

from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import add_days, getdate, nowdate
from frappe.utils.synchronization import filelock

from hrms.alvoraa_hr_core.features import late_rules_on

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def week_start_for(date, week_start_day="Monday"):
	date = getdate(date)
	offset = (date.weekday() - WEEKDAYS.index(week_start_day)) % 7
	return add_days(date, -offset)


def _shift_times(shift_name, cache):
	if shift_name not in cache:
		cache[shift_name] = frappe.db.get_value("Shift Type", shift_name, ["start_time", "end_time"], as_dict=True)
	return cache[shift_name]


def _to_time(value):
	"""Datetime, time or timedelta -> datetime.time."""
	if value is None:
		return None
	if isinstance(value, datetime):
		return value.time()
	if isinstance(value, timedelta):
		return (datetime.min + value).time()
	return value


def _whole_minutes(later, earlier):
	"""Minutes between two MOMENTS, seconds dropped. Never wraps at midnight."""
	later = later.replace(second=0, microsecond=0)
	earlier = earlier.replace(second=0, microsecond=0)
	return int((later - earlier).total_seconds() // 60)


def _shift_window(attendance_date, times):
	"""The shift's start and end as moments in time, not as times of day.

	Comparing times of day wrapped at midnight, and the wrap cost real money.
	A day shift ending 18:30 with a clock-out at 00:30 read as 1,080 minutes
	EARLY - a quarter-day deduction for somebody who had in fact worked four
	hours extra. The mirror image also hid violations: a 22:00 night shift with
	a clock-in at 00:10 came out as minus 1,310 and counted as on time, when
	the person was over two hours late.

	Anchoring both ends to the attendance date removes the wrap. This is the
	same shape Frappe HR's own `shift_type` uses when it decides `late_entry`.
	"""
	date = getdate(attendance_date)
	start = datetime.combine(date, _to_time(times.start_time))
	end = datetime.combine(date, _to_time(times.end_time))
	if end <= start:                     # the shift crosses midnight
		end += timedelta(days=1)
	return start, end


def _as_datetime(value, fallback_date):
	"""A punch as a moment. Frappe stores these as datetimes; older or
	hand-made rows can hold a bare time, and those are read as being on the
	attendance date."""
	if isinstance(value, datetime):
		return value
	return datetime.combine(getdate(fallback_date), _to_time(value))


def violations_for(rule, employee, week_start, week_end, shift_cache=None):
	"""Late arrivals and early exits on submitted Present attendance in the week."""
	shift_cache = shift_cache if shift_cache is not None else {}
	rows = frappe.get_all(
		"Attendance",
		filters={
			"employee": employee,
			"attendance_date": ["between", [week_start, week_end]],
			"docstatus": 1,
			"status": "Present",
		},
		fields=["name", "attendance_date", "in_time", "out_time", "shift"],
		order_by="attendance_date asc",
	)
	out = []
	for att in rows:
		shift = att.shift or rule.shift_type
		if not shift:
			continue
		times = _shift_times(shift, shift_cache)
		if not times or times.start_time is None or times.end_time is None:
			continue
		begins, ends = _shift_window(att.attendance_date, times)
		if att.in_time:
			late = _whole_minutes(_as_datetime(att.in_time, att.attendance_date), begins)
			if late > int(rule.late_threshold_minutes):
				out.append(
					{
						"attendance_date": att.attendance_date,
						"attendance": att.name,
						"violation_type": "Late Arrival",
						"expected_time": times.start_time,
						"actual_time": _to_time(att.in_time),
						"minutes": late,
					}
				)
		if rule.count_early_exit and att.out_time:
			left = _as_datetime(att.out_time, att.attendance_date)
			# Leaving before the shift even began is not an early exit, it is
			# bad data. Counting it would deduct pay on the strength of it.
			early = _whole_minutes(ends, left) if left > begins else 0
			if early > int(rule.early_exit_threshold_minutes or 0):
				out.append(
					{
						"attendance_date": att.attendance_date,
						"attendance": att.name,
						"violation_type": "Early Exit",
						"expected_time": times.end_time,
						"actual_time": _to_time(att.out_time),
						"minutes": early,
					}
				)
	out.sort(key=lambda v: (str(v["attendance_date"]), str(v["actual_time"])))
	return out


def covers(rule, employee, week_start=None, week_end=None, emp=None):
	"""Would this rule actually take a deduction off this person for this week?

	The same conditions the weekly job applies, asked about one person. The
	portal used to skip all of them, so somebody on an exempt grade was shown
	projected days that would never be taken off them, and so was somebody
	whose week fell before the rule's start date or before they joined.

	Called with no week, it answers the part that does not depend on a week.
	`emp` lets a caller that has already read the Employee row pass it in, so a
	whole team does not cost a query each.
	"""
	if emp is None:
		emp = frappe.db.get_value(
			"Employee", employee, ["grade", "date_of_joining", "status"], as_dict=True)
	if not emp or emp.get("status") != "Active":
		return False
	exempt = {r.employee_grade for r in rule.exempt_grades}
	if exempt and emp.get("grade") in exempt:
		return False
	if week_start and rule.process_from and getdate(week_start) < getdate(rule.process_from):
		return False
	joined = emp.get("date_of_joining")
	if week_end and joined and getdate(joined) > getdate(week_end):
		return False
	return True


def covered_employees(rule):
	filters = {"company": rule.company, "status": "Active"}
	exempt = [r.employee_grade for r in rule.exempt_grades]
	if exempt:
		filters["grade"] = ["not in", exempt]
	employees = frappe.get_all("Employee", filters=filters, fields=["name", "date_of_joining"])
	if rule.shift_type:
		on_shift = set(
			frappe.get_all(
				"Shift Assignment",
				filters={"shift_type": rule.shift_type, "docstatus": 1, "status": "Active"},
				pluck="employee",
			)
		)
		employees = [e for e in employees if e.name in on_shift]
	return employees


def process_week(rule, week_start, commit_every=50, commit=True):
	"""Create (and submit) one Attendance Deduction per employee whose counted
	violations amount to a deduction. Idempotent: a submitted deduction for the
	employee-week is left alone; a draft is refreshed."""
	if isinstance(rule, str):
		rule = frappe.get_doc("Attendance Deduction Rule", rule)
	week_start = week_start_for(week_start, rule.week_start_day)
	week_end = add_days(week_start, 6)
	if rule.process_from and getdate(week_start) < getdate(rule.process_from):
		return {"week": str(week_start), "created": 0, "existing": 0, "skipped": "before process_from"}

	# one runner per rule and week: the scheduler and an HR catch-up must not
	# both create deductions for the same employees
	with filelock(f"late_rule_{frappe.scrub(rule.name)}_{week_start}", timeout=600):
		return _process_week(rule, week_start, week_end, commit_every, commit)


def _process_week(rule, week_start, week_end, commit_every, commit):
	created = existing = 0
	shift_cache = {}
	free = int(rule.free_violations_per_week or 0)
	for i, emp in enumerate(covered_employees(rule), 1):
		if emp.date_of_joining and getdate(emp.date_of_joining) > getdate(week_end):
			continue
		found = frappe.db.get_value(
			"Attendance Deduction",
			{"employee": emp.name, "week_start": week_start, "rule": rule.name, "docstatus": ["!=", 2]},
			["name", "docstatus"],
			as_dict=True,
		)
		if found and found.docstatus == 1:
			existing += 1
			continue
		violations = violations_for(rule, emp.name, week_start, week_end, shift_cache)
		if len(violations) <= free:
			if found:  # a draft from an earlier run that no longer applies
				frappe.delete_doc("Attendance Deduction", found.name, ignore_permissions=True, force=True)
			continue
		doc = frappe.get_doc("Attendance Deduction", found.name) if found else frappe.new_doc("Attendance Deduction")
		doc.update({"employee": emp.name, "rule": rule.name, "week_start": week_start, "week_end": week_end})
		doc.set("violations", [])
		for v in violations:
			doc.append("violations", v)
		doc.flags.ignore_permissions = True
		doc.save()
		if doc.deduction_days > 0:
			doc.submit()
			created += 1
		if commit and i % commit_every == 0:
			frappe.db.commit()
	frappe.db.set_value("Attendance Deduction Rule", rule.name, "last_processed_week", week_start, update_modified=False)
	if commit:  # tests run inside one transaction and roll it back
		frappe.db.commit()
	return {"week": str(week_start), "created": created, "existing": existing}


def process_previous_week():
	"""Scheduler: every enabled rule, the week that ended yesterday or earlier.

	Does nothing at all unless HR has switched late coming and early exit rules on
	in Organisation Settings. Deductions already made stay as they are.
	"""
	if not late_rules_on():
		return {"skipped": "late rules are switched off"}
	for name in frappe.get_all("Attendance Deduction Rule", filters={"enabled": 1}, pluck="name"):
		rule = frappe.get_doc("Attendance Deduction Rule", name)
		this_week = week_start_for(nowdate(), rule.week_start_day)
		try:
			process_week(rule, add_days(this_week, -7))
		except Exception:
			frappe.log_error(frappe.get_traceback(), f"Attendance deduction run failed for {name}")


@frappe.whitelist()
def run_for_range(rule, from_date, to_date):
	"""HR: process every week that starts inside the range (used to catch up)."""
	if not ({"HR Manager", "System Manager", "Administrator"} & set(frappe.get_roles())):
		frappe.throw(_("Only HR Managers can run the attendance deduction rule."), frappe.PermissionError)
	if not late_rules_on():
		frappe.throw(
			_(
				"Late coming and early exit rules are switched off for this organisation. Switch them on in Organisation Settings, under Attendance rules, then run the rule again."
			)
		)
	rule_doc = frappe.get_doc("Attendance Deduction Rule", rule)
	if not rule_doc.enabled:
		frappe.throw(_("Rule {0} is disabled.").format(rule))
	start = week_start_for(from_date, rule_doc.week_start_day)
	end = getdate(to_date)
	weeks = created = existing = 0
	while add_days(start, 6) <= end:
		result = process_week(rule_doc, start)
		weeks += 1
		created += result.get("created", 0)
		existing += result.get("existing", 0)
		start = add_days(start, 7)
	return {"weeks": weeks, "created": created, "existing": existing}


def current_week_projection(rule, employee, as_on=None):
	"""What this week looks like so far, for the portal: not persisted."""
	as_on = getdate(as_on or nowdate())
	start = week_start_for(as_on, rule.week_start_day)
	# Say nothing rather than something untrue. If the weekly job would not act
	# on this person this week, a projected figure is a threat that will never
	# be carried out, and they cannot tell the difference.
	if not covers(rule, employee, start, add_days(start, 6)):
		return {"week_start": str(start), "violations": [], "counted": 0,
		        "projected_days": 0, "covered": False}
	violations = violations_for(rule, employee, start, add_days(start, 6))
	free = int(rule.free_violations_per_week or 0)
	counted = max(0, len(violations) - free)
	days = counted * float(rule.deduction_per_violation_days or 0)
	if rule.round_up_from_days and days >= float(rule.round_up_from_days):
		days = float(rule.round_up_to_days or days)
	return {"week_start": str(start), "violations": violations, "counted": counted,
	        "projected_days": days, "covered": True}
