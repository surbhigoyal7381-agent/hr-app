"""ATT-07: re-run the rules over a period, on request, with the numbers shown first.

Attendance does not stand still. Punches arrive late, a device gets fixed, a
manager confirms a held day, the special-day calendar lands mid-month - which
is exactly what happened in October 2026. A payslip prepared on Monday is wrong
by Friday.

Without this the only honest options are to run payroll last and never touch
it, or to correct slips by hand.

THE FOUR THINGS IT HAS TO GET RIGHT, and how each is done here:

  SAFE TO CLICK TWICE. The engine writes a verdict per Attendance record, and a
  verdict REPLACES what was there. Nothing accumulates, so running it again
  produces the same answer rather than twice the deduction. That is why the
  daily verdict lives on the Attendance row and not in a ledger of adjustments.

  NEVER TOUCH A PAID SLIP. A submitted salary slip is a paid slip. Those
  employees are skipped and named. Correcting a payment is a decision for next
  month - an Arrear or a deduction - not a recalculation.

  SHOW THE CHANGE FIRST. `preview` computes the whole thing and writes nothing.
  It returns the days that move, the quarters and reds either side, and the
  money difference. That IS the confirmation. A dialogue reading "Reprocess?"
  with no numbers is a button, not a decision.

  LEAVE A TRAIL. `apply` records who ran it, when, over what, and the totals
  before and after. This changes pay, so it needs a record that outlives an
  Error Log.
"""

import json

import frappe
from frappe import _
from frappe.utils import flt, now

from alvoraa_portal.payroll_rules_apply import (
	VERDICT_FIELDS,
	judge,
	prepare,
	rule_set_for,
	write_verdict,
)

# Preview walks every day in the range. Beyond this many it refuses rather than
# tying up a web worker - 312 employees over a month is about 9,000 rows, so the
# ceiling sits above a normal payroll run and below a year by accident.
MAX_DAYS = 20000


def _attendance_rows(company, from_date, to_date, employees=None):
	filters = {
		"docstatus": 1,
		"company": company,
		"attendance_date": ("between", [from_date, to_date]),
	}
	if employees:
		filters["employee"] = ("in", employees)
	return frappe.get_all(
		"Attendance", filters=filters,
		fields=["name", "employee", "employee_name", "attendance_date", "status",
		        "shift", "company", "alvoraa_held_confirmed",
		        "alvoraa_confirmed_out_time"]
		       + list(VERDICT_FIELDS),
		order_by="employee asc, attendance_date asc", limit_page_length=0)


def _paid_employees(company, from_date, to_date):
	"""Employees whose slip for an overlapping period is already submitted."""
	rows = frappe.get_all(
		"Salary Slip",
		filters={"docstatus": 1, "company": company,
		         "start_date": ("<=", to_date), "end_date": (">=", from_date)},
		fields=["employee", "employee_name", "name", "start_date", "end_date"])
	return {r.employee: r for r in rows}


def _daily_rates(employees, month_days):
	"""Basic over the month length, per employee, for the money column."""
	rates = {}
	if not employees:
		return rates
	for a in frappe.get_all(
			"Salary Structure Assignment",
			filters={"docstatus": 1, "employee": ("in", list(employees))},
			fields=["employee", "base"], order_by="from_date asc"):
		rates[a.employee] = flt(a.base) / month_days if month_days else 0.0
	return rates


@frappe.whitelist()
def preview(company, from_date, to_date, employees=None):
	"""What a reprocess would change. Writes nothing.

	Returns the per-employee movement and the totals, so the requester can see
	the money before agreeing to it.
	"""
	frappe.has_permission("Attendance", "write", throw=True)
	if isinstance(employees, str):
		employees = json.loads(employees)

	rule_set = rule_set_for(company)
	if not rule_set:
		return {"ok": False, "reason": _(
			"{0} has no payroll rule set switched on, so there are no rules to "
			"re-run.").format(company)}

	rows = _attendance_rows(company, from_date, to_date, employees)
	if len(rows) > MAX_DAYS:
		frappe.throw(_("{0} days is more than this can preview in one go. Narrow "
		               "the dates or the employees.").format(len(rows)))

	paid = _paid_employees(company, from_date, to_date)
	ctx = prepare(rule_set, from_date, to_date)
	month_days = frappe.utils.date_diff(to_date, from_date) + 1
	rates = _daily_rates({r.employee for r in rows}, month_days)

	moved, skipped, totals = [], {}, {
		"days": 0, "changed": 0,
		"quarters_before": 0, "quarters_after": 0,
		"reds_before": 0, "reds_after": 0,
		"held_before": 0, "held_after": 0,
		"money": 0.0,
	}

	for row in rows:
		if row.employee in paid:
			slip = paid[row.employee]
			skipped.setdefault(row.employee, {
				"employee": row.employee, "employee_name": row.employee_name,
				"slip": slip.name, "days": 0})
			skipped[row.employee]["days"] += 1
			continue

		totals["days"] += 1
		before_q = int(row.get("alvoraa_slab_quarters") or 0) + \
			int(row.get("alvoraa_extra_quarters") or 0)
		before_r = int(row.get("alvoraa_reds") or 0)
		before_h = 1 if row.get("alvoraa_held") else 0

		v = judge(row, ctx)
		totals["quarters_before"] += before_q
		totals["quarters_after"] += v.total_quarters
		totals["reds_before"] += before_r
		totals["reds_after"] += v.reds
		totals["held_before"] += before_h
		totals["held_after"] += 1 if v.held else 0

		if (before_q != v.total_quarters or before_r != v.reds
				or before_h != (1 if v.held else 0)):
			totals["changed"] += 1
			# A quarter is a quarter of a day's pay, so the money a day moves by
			# is the change in quarters over four, times the daily rate.
			delta = (before_q - v.total_quarters) / 4.0 * rates.get(row.employee, 0.0)
			totals["money"] += delta
			moved.append({
				"attendance": row.name,
				"employee": row.employee,
				"employee_name": row.employee_name,
				"date": str(row.attendance_date),
				"quarters_before": before_q, "quarters_after": v.total_quarters,
				"reds_before": before_r, "reds_after": v.reds,
				"held_before": before_h, "held_after": 1 if v.held else 0,
				"money": round(delta, 2),
				"why": " ".join(v.reasons),
			})

	totals["money"] = round(totals["money"], 2)
	return {
		"ok": True,
		"company": company, "from_date": from_date, "to_date": to_date,
		"totals": totals,
		"employees_affected": len({m["employee"] for m in moved}),
		"moved": moved[:500],
		"moved_truncated": max(0, len(moved) - 500),
		"skipped_paid": list(skipped.values()),
	}


@frappe.whitelist()
def apply(company, from_date, to_date, employees=None, confirmed=0):
	"""Re-run the rules and store the result. Refuses without a confirmation.

	`confirmed` is not ceremony. Everything this writes changes pay, and the
	requester is meant to have seen `preview` first.
	"""
	frappe.has_permission("Attendance", "write", throw=True)
	if not int(confirmed or 0):
		frappe.throw(_("Reprocessing changes pay, so it needs a confirmation. "
		               "Run the preview first and agree to what it shows."))
	if isinstance(employees, str):
		employees = json.loads(employees)

	before = preview(company, from_date, to_date, employees)
	if not before.get("ok"):
		return before

	rule_set = rule_set_for(company)
	ctx = prepare(rule_set, from_date, to_date)
	paid = _paid_employees(company, from_date, to_date)
	written = 0

	for row in _attendance_rows(company, from_date, to_date, employees):
		if row.employee in paid:
			continue
		# A verdict replaces what was there, so this is safe to run twice.
		write_verdict(row.name, judge(row, ctx))
		written += 1

	frappe.db.commit()

	log = frappe.get_doc({
		"doctype": "Alvoraa Payroll Reprocess Log",
		"company": company,
		"from_date": from_date,
		"to_date": to_date,
		"run_by": frappe.session.user,
		"run_on": now(),
		"days_reprocessed": written,
		"days_changed": before["totals"]["changed"],
		"employees_affected": before["employees_affected"],
		"quarters_before": before["totals"]["quarters_before"],
		"quarters_after": before["totals"]["quarters_after"],
		"reds_before": before["totals"]["reds_before"],
		"reds_after": before["totals"]["reds_after"],
		"money_difference": before["totals"]["money"],
		"skipped_paid_slips": len(before["skipped_paid"]),
		"detail": json.dumps(before, indent=1, default=str)[:140000],
	})
	log.flags.ignore_permissions = True
	log.insert()
	frappe.db.commit()

	return {"ok": True, "written": written, "log": log.name, "preview": before}
