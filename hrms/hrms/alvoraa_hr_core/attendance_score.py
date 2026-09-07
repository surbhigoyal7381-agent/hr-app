"""Attendance as a part of the appraisal score.

An Appraisal Cycle that ticks "Include Attendance Score" gets its final score
formula built from three weights (targets, manager feedback, attendance), and
every Appraisal in it gets an attendance score worked out from the employee's
attendance records inside the appraisal window:

    reliability  = 1 - (absent days + loss-of-pay days) / scheduled days
    punctuality  = 1 - late days / present days
    base         = 5 x (reliability share x reliability + punctuality share x punctuality)
    score        = base - penalty x days deducted by the late-coming rule, kept between 0 and 5

Scheduled days are the calendar days in the window less the employee's holidays,
trimmed to their joining and relieving dates. Approved paid leave does not count
against the employee unless the cycle says so. Exempt grades get full marks.

The score is a snapshot: it is written when the appraisal is saved or submitted,
so an attendance correction after submit does not change a submitted appraisal.
"""

import frappe
from frappe import _
from frappe.utils import cint, date_diff, flt, getdate

from hrms.alvoraa_hr_core.features import feature_enabled
from hrms.hr.utils import get_holidays_for_employee
from hrms.utils.holiday_list import get_holiday_list_for_employee

PRESENT_STATUSES = ("Present", "Work From Home")
MAX_SCORE = 5.0


# ── Appraisal Cycle ─────────────────────────────────────────────────────────
def apply_cycle_settings(doc, method=None):
	"""Appraisal Cycle validate: check the weights and write the formula."""
	if not cint(doc.get("include_attendance_score")):
		return
	if not feature_enabled("attendance_scoring"):
		frappe.throw(_("Attendance in the appraisal score is not switched on for this site."))
	total = flt(doc.get("goal_weight")) + flt(doc.get("feedback_weight")) + flt(doc.get("attendance_weight"))
	if abs(total - 100) > 0.01:
		frappe.throw(
			_("Targets, manager feedback and attendance weights must add up to 100. They add up to {0}.").format(
				flt(total, 2)
			)
		)
	if flt(doc.get("attendance_reliability_weight")) + flt(doc.get("attendance_punctuality_weight")) <= 0:
		frappe.throw(_("Reliability and punctuality shares must add up to more than zero."))
	if flt(doc.get("attendance_deduction_penalty")) < 0:
		frappe.throw(_("The penalty per deducted day cannot be negative."))
	doc.calculate_final_score_based_on_formula = 1
	doc.final_score_formula = build_formula(doc)


def build_formula(cycle):
	"""The final score formula for a cycle, from its weights.

	With attendance included: the three-part formula. Without it: targets and
	manager feedback when both weights are set and add up to 100, otherwise the
	targets score alone (what the portal wrote before this existed).
	"""
	gw = flt(cycle.get("goal_weight"))
	fw = flt(cycle.get("feedback_weight"))
	aw = flt(cycle.get("attendance_weight"))
	if cint(cycle.get("include_attendance_score")):
		return f"goal_score * {gw / 100:g} + average_feedback_score * {fw / 100:g} + attendance_score * {aw / 100:g}"
	if fw > 0 and abs(gw + fw - 100) <= 0.01:
		return f"goal_score * {gw / 100:g} + average_feedback_score * {fw / 100:g}"
	return "goal_score"


# ── Numbers ─────────────────────────────────────────────────────────────────
def attendance_numbers(employee, start_date, end_date, count_paid_leave_as_absent=False):
	"""The attendance figures for one employee inside a window."""
	return numbers_for_many([employee], start_date, end_date, count_paid_leave_as_absent)[employee]


def numbers_for_many(employees, start_date, end_date, count_paid_leave_as_absent=False):
	"""The same figures for many employees with one query per doctype, not one
	per employee: appraisal generation for a few hundred people stays cheap."""
	start, end = getdate(start_date), getdate(end_date)
	employees = list(dict.fromkeys(employees))
	result = {}
	if not employees:
		return result

	emp_rows = {
		r.name: r
		for r in frappe.get_all(
			"Employee", filters={"name": ["in", employees]}, fields=["name", "date_of_joining", "relieving_date"]
		)
	}
	attendance = {}
	for r in frappe.get_all(
		"Attendance",
		filters={
			"employee": ["in", employees],
			"docstatus": 1,
			"attendance_date": ["between", [start, end]],
		},
		fields=["employee", "attendance_date", "status", "late_entry", "leave_type"],
	):
		attendance.setdefault(r.employee, []).append(r)
	deductions = {}
	if frappe.db.exists("DocType", "Attendance Deduction"):
		for r in frappe.get_all(
			"Attendance Deduction",
			filters={"employee": ["in", employees], "docstatus": 1, "week_end": ["between", [start, end]]},
			fields=["employee", "deduction_days"],
		):
			deductions[r.employee] = deductions.get(r.employee, 0) + flt(r.deduction_days)
	lwp_types = set(frappe.get_all("Leave Type", filters={"is_lwp": 1}, pluck="name"))
	holidays_by_list = {}

	for employee in employees:
		emp = emp_rows.get(employee) or frappe._dict()
		e_start, e_end = start, end
		if emp.date_of_joining and getdate(emp.date_of_joining) > e_start:
			e_start = getdate(emp.date_of_joining)
		if emp.relieving_date and getdate(emp.relieving_date) < e_end:
			e_end = getdate(emp.relieving_date)
		n = frappe._dict(
			scheduled_days=0,
			present_days=0.0,
			late_days=0,
			absent_days=0.0,
			lwp_days=0.0,
			deduction_days=flt(deductions.get(employee)),
			has_data=False,
			reliability_pct=None,
			punctuality_pct=None,
		)
		result[employee] = n
		if e_start > e_end:
			continue

		holiday_list = get_holiday_list_for_employee(employee, raise_exception=False)
		if holiday_list not in holidays_by_list:
			holidays_by_list[holiday_list] = (
				{getdate(h.holiday_date) for h in get_holidays_for_employee(employee, start, end, raise_exception=False)}
				if holiday_list
				else set()
			)
		holidays = {d for d in holidays_by_list[holiday_list] if e_start <= d <= e_end}
		n.scheduled_days = date_diff(e_end, e_start) + 1 - len(holidays)

		for r in attendance.get(employee, []):
			d = getdate(r.attendance_date)
			if d < e_start or d > e_end:
				continue
			n.has_data = True
			if r.status in PRESENT_STATUSES:
				n.present_days += 1
				n.late_days += cint(r.late_entry)
			elif r.status == "Half Day":
				n.present_days += 0.5
				n.absent_days += 0.5
				n.late_days += cint(r.late_entry)
			elif r.status == "Absent":
				n.absent_days += 1
			elif r.status == "On Leave":
				if r.leave_type in lwp_types:
					n.lwp_days += 1
				elif count_paid_leave_as_absent:
					n.absent_days += 1

		if n.scheduled_days > 0:
			n.reliability_pct = flt(max(0.0, 1 - (n.absent_days + n.lwp_days) / n.scheduled_days) * 100, 2)
		if n.present_days > 0:
			n.punctuality_pct = flt(max(0.0, 1 - n.late_days / n.present_days) * 100, 2)
	return result


# ── Score ───────────────────────────────────────────────────────────────────
def score_for(cycle, numbers):
	"""(score, summary). Score is None when there is nothing to score."""
	if not numbers.has_data or not numbers.scheduled_days or numbers.reliability_pct is None:
		return None, _("No attendance records in this period.")
	rel_w = flt(cycle.get("attendance_reliability_weight"))
	pun_w = flt(cycle.get("attendance_punctuality_weight"))
	share = rel_w + pun_w
	if share <= 0:
		rel_w, pun_w, share = 60, 40, 100
	punctuality = numbers.punctuality_pct if numbers.punctuality_pct is not None else 100.0
	base = MAX_SCORE * (rel_w / share * numbers.reliability_pct / 100 + pun_w / share * punctuality / 100)
	penalty = flt(cycle.get("attendance_deduction_penalty")) * flt(numbers.deduction_days)
	score = flt(max(0.0, min(MAX_SCORE, base - penalty)), 2)

	parts = [
		_("Scheduled {0} days, present {1}, absent {2}, loss of pay {3}: reliability {4}%.").format(
			numbers.scheduled_days,
			_num(numbers.present_days),
			_num(numbers.absent_days),
			_num(numbers.lwp_days),
			_num(numbers.reliability_pct),
		),
		_("Late on {0} of {1} present days: punctuality {2}%.").format(
			numbers.late_days, _num(numbers.present_days), _num(punctuality)
		),
	]
	if penalty:
		parts.append(
			_("Base {0}, minus {1} for {2} day(s) deducted by the late-coming rule = {3} out of 5.").format(
				_num(flt(base, 2)), _num(flt(penalty, 2)), _num(numbers.deduction_days), _num(score)
			)
		)
	else:
		parts.append(_("Score {0} out of 5.").format(_num(score)))
	return score, " ".join(parts)


def _num(v):
	v = flt(v)
	return str(int(v)) if v == int(v) else f"{v:g}"


def exempt_reason(cycle, employee):
	grade = frappe.db.get_value("Employee", employee, "grade")
	exempt = {row.employee_grade for row in (cycle.get("attendance_exempt_grades") or [])}
	if grade and grade in exempt:
		return _("Exempt from attendance scoring (grade {0}): full marks.").format(grade)
	return None


# ── Appraisal hook ──────────────────────────────────────────────────────────
def compute(doc, method=None):
	"""Appraisal before_save and before_submit: snapshot the attendance score
	and redo the final score with it."""
	if not doc.appraisal_cycle:
		return
	cycle = frappe.get_cached_doc("Appraisal Cycle", doc.appraisal_cycle)
	if not cint(cycle.get("include_attendance_score")) or not feature_enabled("attendance_scoring"):
		return

	reason = exempt_reason(cycle, doc.employee)
	if reason:
		numbers = frappe._dict(reliability_pct=None, punctuality_pct=None, deduction_days=0)
		score, summary = MAX_SCORE, reason
	else:
		numbers = _cached_numbers(cycle, doc.employee, doc.start_date, doc.end_date)
		score, summary = score_for(cycle, numbers)
		if score is None:
			if (cycle.get("attendance_when_no_data") or "") == "Give full marks":
				score = MAX_SCORE
				summary += " " + _("Full marks given.")
			else:
				score = flt((flt(doc.total_score) + flt(doc.avg_feedback_score)) / 2, 2)
				summary += " " + _("The average of the other parts is used instead.")

	doc.attendance_score = score
	doc.attendance_reliability_pct = numbers.reliability_pct
	doc.attendance_punctuality_pct = numbers.punctuality_pct
	doc.attendance_deduction_days = flt(numbers.deduction_days)
	doc.attendance_summary = summary
	# validate already computed the final score without this number
	doc.calculate_final_score()


def _cached_numbers(cycle, employee, start_date, end_date):
	key = (employee, str(start_date), str(end_date))
	cache = getattr(frappe.local, "attendance_score_cache", None) or {}
	if key in cache:
		return cache[key]
	return attendance_numbers(employee, start_date, end_date, cint(cycle.get("count_paid_leave_as_absent")))


def precompute(cycle, employees):
	"""Work out the numbers for a whole cycle in three queries and keep them for
	the rest of this request, so generating hundreds of appraisals does not
	query attendance hundreds of times."""
	if isinstance(cycle, str):
		cycle = frappe.get_cached_doc("Appraisal Cycle", cycle)
	if not cint(cycle.get("include_attendance_score")):
		return
	numbers = numbers_for_many(
		employees, cycle.start_date, cycle.end_date, cint(cycle.get("count_paid_leave_as_absent"))
	)
	cache = getattr(frappe.local, "attendance_score_cache", None) or {}
	for employee, n in numbers.items():
		cache[(employee, str(cycle.start_date), str(cycle.end_date))] = n
	frappe.local.attendance_score_cache = cache


def cycle_scoring(cycle):
	"""The scoring settings of a cycle as plain values, for the portal."""
	if isinstance(cycle, str):
		cycle = frappe.get_cached_doc("Appraisal Cycle", cycle)
	return {
		"include_attendance": cint(cycle.get("include_attendance_score")),
		"goal_weight": flt(cycle.get("goal_weight")),
		"feedback_weight": flt(cycle.get("feedback_weight")),
		"attendance_weight": flt(cycle.get("attendance_weight")),
		"reliability_weight": flt(cycle.get("attendance_reliability_weight")),
		"punctuality_weight": flt(cycle.get("attendance_punctuality_weight")),
		"deduction_penalty": flt(cycle.get("attendance_deduction_penalty")),
		"count_paid_leave_as_absent": cint(cycle.get("count_paid_leave_as_absent")),
		"when_no_data": cycle.get("attendance_when_no_data") or "",
		"exempt_grades": [row.employee_grade for row in (cycle.get("attendance_exempt_grades") or [])],
		"formula": cycle.get("final_score_formula") or "",
	}
