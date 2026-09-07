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


def _minutes_between(later, earlier):
	l = _to_time(later)
	e = _to_time(earlier)
	return int(((l.hour * 60 + l.minute) - (e.hour * 60 + e.minute)))


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
		if not times:
			continue
		if att.in_time:
			late = _minutes_between(att.in_time, times.start_time)
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
			early = _minutes_between(times.end_time, att.out_time)
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
	"""Scheduler: every enabled rule, the week that ended yesterday or earlier."""
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
	violations = violations_for(rule, employee, start, add_days(start, 6))
	free = int(rule.free_violations_per_week or 0)
	counted = max(0, len(violations) - free)
	days = counted * float(rule.deduction_per_violation_days or 0)
	if rule.round_up_from_days and days >= float(rule.round_up_from_days):
		days = float(rule.round_up_to_days or days)
	return {"week_start": str(start), "violations": violations, "counted": counted, "projected_days": days}
