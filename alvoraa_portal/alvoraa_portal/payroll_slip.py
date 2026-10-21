"""Feeding the monthly roll-up into Frappe's own Salary Slip.

`payroll_month.summarise_month` works out paid days, red and green money. This
is what puts those figures where a payslip can see them.

TWO ROUTES IN, chosen for different reasons.

  PAID DAYS go straight onto the slip, because Frappe already has the field.
  Basic is `base` with depends_on_payment_days set, so Frappe computes it as
  base x payment_days / total_working_days. That is the same arithmetic as
  ours - paid days x (Basic / days in month) - so overriding payment_days is
  enough to make Basic correct, and nothing else needs touching.

  Leave credits are folded INTO paid days rather than shown as a separate
  earning. That matches DTC's own salary sheet, where PAID DAYS = P + WO - LOP
  and EARNING BASIC is prorated from the total. It also avoids adding rows to
  the salary structure, which is a change to every employee rather than to one
  month.

  RED AND GREEN MONEY go in as `Additional Salary` records, not by writing
  amounts onto the slip. Frappe recomputes slip rows from the STRUCTURE on
  every validate, so an amount written onto a row is erased the next time
  somebody opens it. An Additional Salary survives, is a record HR can see and
  question, carries a link back to what produced it, and is how Frappe itself
  expects a per-employee per-month figure to arrive.

WHY THE HOOK RE-RUNS THE CALCULATION.

Frappe's `validate` does three things in order: work out the working days,
attach the structure, then calculate net pay. A `validate` doc_event runs after
all of it, so by the time we see the slip the pay has already been worked out
from Frappe's own payment_days. Setting ours and calling `calculate_net_pay()`
again is what makes it take.

NOT YET PROVEN ON A SITE. The pure parts of this are tested; the hook itself
needs a bench run before anybody trusts a payslip it produced.
"""

import frappe
from frappe.utils import add_days, date_diff, flt, getdate

from alvoraa_portal.payroll_month import summarise_month
from alvoraa_portal.payroll_rules_apply import (
	LEAVE_FIELDS,
	PAID_LEAVES,
	judge,
	prepare,
	rule_set_for,
)

RED_COMPONENT = "Red Value"
GREEN_COMPONENT = "Green Value"


def month_summary(employee, company, from_date, to_date, rule_set=None, ctx=None):
	"""Judge every day in the period for one employee, then add them up.

	Returns None where the company has no rule set switched on, which is every
	tenant but DTC and is not an error.
	"""
	rule_set = rule_set or rule_set_for(company)
	if not rule_set:
		return None
	ctx = ctx or prepare(rule_set, from_date, to_date)

	rows = frappe.get_all(
		"Attendance",
		filters={"docstatus": 1, "employee": employee,
		         "attendance_date": ("between", [from_date, to_date])},
		fields=["name", "employee", "attendance_date", "status", "shift", "company"]
		+ list(LEAVE_FIELDS),
		order_by="attendance_date asc", limit_page_length=0)
	verdicts = [judge(r, ctx) for r in rows]

	# Approved Paid Leaves days, from the same rows (slice 063). They are what
	# the credits are "used" for (U1 - a Leave Without Pay day is simply
	# unpaid) and they count toward the 15-day gate (E6). A half-day leave is
	# 0.5. Read here, once, so the slip, the desk report and the Leave page card
	# all get the same figure from the one call they share.
	paid_leave_days = sum(
		1.0 if r.status == "On Leave" else 0.5
		for r in rows
		if r.get("leave_type") == PAID_LEAVES
		and (r.status == "On Leave"
		     or (r.status == "Half Day" and r.get("leave_application"))))

	emp = frappe.db.get_value(
		"Employee", employee,
		[f for f in (rule_set.leave_class_field, rule_set.category_field,
		             rule_set.grade_field) if f] or ["name"], as_dict=True) or {}

	leave_class = str(emp.get(rule_set.leave_class_field) or "").strip() \
		if rule_set.leave_class_field else ""
	category = str(emp.get(rule_set.category_field) or "").strip().lower() \
		if rule_set.category_field else ""
	grade = str(emp.get(rule_set.grade_field) or "").strip() \
		if rule_set.grade_field else ""

	cls = next((c for c in rule_set.leave_classes
	            if (c.leave_class or "").strip() == leave_class), None)
	cat = next((c for c in rule_set.categories
	            if (c.category or "").strip().lower() == category), None)
	rate = next((r for r in rule_set.mark_rates
	             if (r.grade or "").strip() == grade), None)

	basic = flt(frappe.db.get_value(
		"Salary Structure Assignment",
		{"employee": employee, "docstatus": 1, "from_date": ("<=", to_date)},
		"base", order_by="from_date desc"))

	# GBL-02: the divisor is the real length of the period, not a fixed 30.
	month_days = date_diff(to_date, from_date) + 1

	return summarise_month(
		verdicts,
		basic=basic,
		month_days=month_days,
		approved_leave_days=paid_leave_days,
		earns_leave_credits=(cat.earns_leave_credits if cat else True),
		period_days=(cls.period_days if cls else 0),
		credit_per_period=(cls.credit_per_period if cls else 0),
		monthly_cap=(cls.monthly_credits if cls else 0),
		threshold_days=int(rule_set.leave_threshold_days or 0),
		accrual_month_days=int(rule_set.accrual_month_days or 30),
		earns_marks=(cat.earns_marks if cat else True),
		free_reds=int(rule_set.free_reds_per_month or 0),
		mark_rate=(rate.amount_per_mark if rate else 0),
	)


def _set_additional_salary(employee, company, component, amount, payroll_date,
                           note=None):
	"""One Additional Salary per employee, component and month - replaced, not added.

	Replaced matters more than it looks. A reprocess re-runs the same period,
	and a second record would stack on the first: two clicks, twice the red
	deduction. Finding the existing draft and overwriting it is what makes the
	whole chain safe to run again.
	"""
	existing = frappe.db.get_value("Additional Salary", {
		"employee": employee, "salary_component": component,
		"payroll_date": payroll_date, "docstatus": ("<", 2),
	}, "name")

	if not flt(amount):
		# Nothing owed this month. Remove a stale record rather than leave a
		# zero one lying about looking like a decision.
		if existing and frappe.db.get_value("Additional Salary", existing,
		                                    "docstatus") == 0:
			frappe.delete_doc("Additional Salary", existing, ignore_permissions=True)
		return None

	if existing:
		doc = frappe.get_doc("Additional Salary", existing)
		if doc.docstatus == 1:
			# Submitted. Changing it is a decision, not a recalculation.
			return doc.name
		doc.amount = flt(amount)
		doc.flags.ignore_permissions = True
		doc.save()
		return doc.name

	doc = frappe.get_doc({
		"doctype": "Additional Salary",
		"employee": employee,
		"company": company,
		"salary_component": component,
		"amount": flt(amount),
		"payroll_date": payroll_date,
		"overwrite_salary_structure_amount": 1,
		"type": frappe.db.get_value("Salary Component", component, "type"),
	})
	doc.flags.ignore_permissions = True
	doc.insert()
	doc.submit()
	return doc.name


def push_marks_to_additional_salary(employee, company, from_date, to_date,
                                    summary=None):
	"""Put this month's red and green money where the slip will find it."""
	summary = summary or month_summary(employee, company, from_date, to_date)
	if not summary:
		return {}
	payroll_date = getdate(to_date)
	return {
		"red": _set_additional_salary(employee, company, RED_COMPONENT,
		                              summary.red_deduction, payroll_date),
		"green": _set_additional_salary(employee, company, GREEN_COMPONENT,
		                                summary.green_earning, payroll_date),
	}


def on_salary_slip_validate(doc, method=None):
	"""doc_events hook. Replace Frappe's paid days with the rules engine's.

	Runs after Frappe has already worked the slip out, so the figures are set
	and then the calculation is re-run over them.

	Wrapped, because a rules problem must never stop a payslip being saved. A
	slip that cannot be produced is a person who cannot be paid; a slip with
	Frappe's own figures is at least a slip somebody can look at. The failure
	goes to the Error Log and the reprocess picks it up once the rule set is
	fixed.
	"""
	try:
		if doc.docstatus != 0:
			return
		rule_set = rule_set_for(doc.company)
		if not rule_set:
			return

		summary = month_summary(doc.employee, doc.company,
		                        doc.start_date, doc.end_date, rule_set)
		if not summary:
			return

		doc.total_working_days = date_diff(doc.end_date, doc.start_date) + 1
		doc.payment_days = flt(summary.paid_days, 2)
		doc.absent_days = summary.days_absent
		doc.calculate_net_pay()

		if summary.days_held:
			doc.add_comment("Comment", _held_note(summary))
	except Exception:
		frappe.log_error(
			title="Payroll rules could not price {0}".format(doc.name or "a slip"),
			message=frappe.get_traceback())


def _held_note(summary):
	return (
		"{0} day(s) are held for a missing check-out and are NOT in these paid "
		"days. Each is neither paid nor deducted until a manager confirms the "
		"employee left on time, and is then released as an Arrear."
	).format(summary.days_held)
