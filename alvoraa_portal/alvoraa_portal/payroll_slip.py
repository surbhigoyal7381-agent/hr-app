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

  The slip's own save writes them (slice 067, ALV-208), in the same transaction
  as the slip, just before the calculation is re-run. So a late attendance fix,
  a reprocess or a re-run Payroll Entry changes paid days and marks together,
  the moment the draft slip is saved again. One record per person, line and
  month: an unchanged figure writes nothing, a changed one cancels the old
  record and makes a new one amended from it, so the trail of every change
  stays. A paid (submitted) slip is never touched.

WHY THE HOOK RE-RUNS THE CALCULATION.

Frappe's `validate` does three things in order: work out the working days,
attach the structure, then calculate net pay. A `validate` doc_event runs after
all of it, so by the time we see the slip the pay has already been worked out
from Frappe's own payment_days. Setting ours and calling `calculate_net_pay()`
again is what makes it take. Frappe also works out the year-to-date figures in
its validate, from ITS net pay, so those are worked out again afterwards too.
"""

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, flt, getdate

import alvoraa_portal.grooming as grooming
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
GROOMING_COMPONENT = "Grooming Red Value"

# The pay lines the engine owns, and the month-summary figure each one carries.
ENGINE_LINES = (
	(RED_COMPONENT, "red_deduction"),
	(GREEN_COMPONENT, "green_earning"),
	# Slice 066: the month's grooming reds, one line whatever the number of marks.
	(GROOMING_COMPONENT, "grooming_deduction"),
)

# How the engine knows its own Additional Salary records: a standard field
# pointing at the rule set. Frappe HR only acts on ref_doctype for Gratuity and
# Leave Encashment, so this is safe, and a record HR typed by hand (no
# reference) is never touched.
ENGINE_REF = "Alvoraa Payroll Rule Set"


def credit_rows_for(rule_set, designation, cat, cls, month_days):
	"""Slice 063 (SEC-18): this month's rows of the days-present table for one
	person, as [(from, to, credits)], or None for everybody the table does not reach.

	All four must hold: the category earns no leave credit (Contract at DTC; a
	Permanent person keeps the office rule), the rule set has rows for the
	designation, the class gives credit, and the period is a 28 to 31 day month.
	No company or designation name is in code - the rows name their own.
	"""
	if not (designation and cat and not cat.earns_leave_credits and cls
	        and flt(cls.monthly_credits) > 0 and 28 <= month_days <= 31):
		return None
	length = "28-29" if month_days <= 29 else "30-31"
	rows = sorted((r.days_from, r.days_to, flt(r.credits)) for r in rule_set.leave_credit_rows
	              if r.designation == designation and r.month_length == length)
	return rows or None


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
		["designation"] + [f for f in (rule_set.leave_class_field, rule_set.category_field,
		                               rule_set.grade_field) if f], as_dict=True) or {}

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

	# Slice 066 (SEC-2, SEC-9): grooming reds are charged by DISTINCT day, so two
	# marks on one date are one day, and never on a day the attendance says was a
	# full-day leave or absence (a leave approved after the mark). Half Day is
	# charged. Only the slip's own employee is read.
	# With grooming switched off (grooming.is_on) there is no grooming line.
	not_charged = {str(r.attendance_date) for r in rows if r.status in ("On Leave", "Absent")}
	grooming_days = min(len({str(d) for d in frappe.get_all(
		"Grooming Mark",
		filters={"employee": employee, "docstatus": 1,
		         "mark_date": ("between", [from_date, to_date])},
		pluck="mark_date")} - not_charged), grooming.MONTH_MAX) if grooming.is_on() else 0

	designation = emp.get("designation") or ""
	table = credit_rows_for(rule_set, designation, cat, cls, month_days)
	summary = summarise_month(
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
		credit_rows=table,
		credit_designation=designation,
		earns_marks=(cat.earns_marks if cat else True),
		free_reds=int(rule_set.free_reds_per_month or 0),
		mark_rate=(rate.amount_per_mark if rate else 0),
		grooming_days=grooming_days,
	)
	# [ASSUMPTION: DTC's payroll periods are calendar months] A period of another
	# length for a person the table would reach gives no leave, and says so.
	if designation and not 28 <= month_days <= 31 and any(
			r.designation == designation for r in rule_set.leave_credit_rows):
		summary.notes.append("The days-present table covers months of 28 to 31 days; this "
		                     "period is {0} days, so it gave no leave.".format(month_days))
	return summary


def _set_additional_salary(slip, component, amount, payroll_date, rule_set):
	"""One engine-made Additional Salary per person, line and month. Replaced, never added.

	Replaced matters more than it looks. A reprocess re-runs the same period,
	and a second record would stack on the first: two saves, twice the red
	deduction. So:

	  the same amount already there   -> nothing is written (safe to save twice)
	  a different amount             -> the old record is cancelled and a new
	                                    one is made, amended from it, so the
	                                    change leaves a trail
	  nothing owed any more          -> the old record is cancelled

	Only records the engine made are looked at (ENGINE_REF). A line HR typed by
	hand is not the engine's to change.
	"""
	amount = flt(amount, 2)
	existing = frappe.get_all(
		"Additional Salary",
		filters={"employee": slip.employee, "salary_component": component,
		         "payroll_date": ("between", [slip.start_date, slip.end_date]),
		         "docstatus": 1, "ref_doctype": ENGINE_REF},
		fields=["name", "amount", "payroll_date"],
		order_by="creation desc")

	keep, old = None, None
	for row in existing:
		if (keep is None and amount and flt(row.amount, 2) == amount
				and getdate(row.payroll_date) == getdate(payroll_date)):
			keep = row.name
			continue
		doc = frappe.get_doc("Additional Salary", row.name)
		doc.flags.ignore_permissions = True
		doc.cancel()
		old = old or row.name

	if keep or not amount:
		return keep

	doc = frappe.get_doc({
		"doctype": "Additional Salary",
		"employee": slip.employee,
		"company": slip.company,
		"currency": slip.currency,
		"salary_component": component,
		"type": frappe.db.get_value("Salary Component", component, "type"),
		"amount": amount,
		"payroll_date": payroll_date,
		"overwrite_salary_structure_amount": 1,
		"ref_doctype": ENGINE_REF,
		"ref_docname": rule_set.name,
		"amended_from": old,
	})
	doc.flags.ignore_permissions = True
	doc.insert()
	doc.submit()
	return doc.name


def push_marks_to_additional_salary(slip, summary, rule_set):
	"""Put this month's engine lines (red, green) where the slip will find them.

	Dated on the slip's last day, or on the relieving date when that comes
	first: Frappe refuses a payroll date after somebody has left.
	"""
	payroll_date = getdate(slip.end_date)
	relieving = frappe.db.get_value("Employee", slip.employee, "relieving_date")
	if relieving and getdate(relieving) < payroll_date:
		payroll_date = getdate(relieving)
	return {component: _set_additional_salary(slip, component, getattr(summary, figure),
	                                          payroll_date, rule_set)
	        for component, figure in ENGINE_LINES}


def _apply_engine_lines(doc, summary, rule_set):
	"""Write the lines, or write none of them.

	A savepoint, because a failure half way (the old red cancelled, the new one
	refused) would leave the slip with no red line at all and say nothing. The
	slip is still saved with its paid days, as before, but with a comment HR
	can see, and the Error Log names the slip only.
	"""
	frappe.db.savepoint("alvoraa_engine_lines")
	try:
		live = push_marks_to_additional_salary(doc, summary, rule_set)
	except Exception:
		frappe.db.rollback(save_point="alvoraa_engine_lines")
		frappe.log_error(
			title="Red and green lines not applied to {0}".format(doc.name or "a slip"),
			message=frappe.get_traceback())
		_note(doc, _(
			"The red and green lines and the grooming line could not be updated on this slip, so they "
			"may be missing or out of date. Paid days are correct. See the Error "
			"Log, fix the cause, then save this slip again."))
		return

	# Frappe keeps a slip row that points at an Additional Salary even after
	# that record is cancelled, so the old figure would stay beside the new one.
	# Drop every engine-line row that is not the live record's.
	for table in ("earnings", "deductions"):
		doc.set(table, [r for r in doc.get(table)
		                if r.salary_component not in live or not r.additional_salary
		                or r.additional_salary == live[r.salary_component]])


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
		# Before the calculation, so it picks the lines up in this same save.
		_apply_engine_lines(doc, summary, rule_set)
		doc.calculate_net_pay()
		# Frappe worked these out in its own validate, from ITS net pay. The
		# portal shows year_to_date straight off the slip.
		doc.compute_year_to_date()
		doc.compute_month_to_date()
		doc.compute_component_wise_year_to_date()

		if summary.days_held:
			_note(doc, _held_note(summary))
	except Exception:
		frappe.log_error(
			title="Payroll rules could not price {0}".format(doc.name or "a slip"),
			message=frappe.get_traceback())


def check_grooming_before_submit(doc, method=None):
	"""doc_events before_submit (slice 066, SEC-9 and D2). Fails closed.

	The validate hook prices a slip only while it is a draft. A mark made or
	removed after the last save would otherwise be submitted at the old figure.
	So the month is priced again - the same `month_summary`, one definition of
	the price - and the submit is refused if the slip's grooming line differs.
	Payroll Entry submits slips one by one and carries on past a refused one.
	"""
	rule_set = rule_set_for(doc.company)
	if not rule_set:
		return
	if not grooming.is_on():
		# Off: no grooming line is priced, so an open "Ask HR" holds nothing. But
		# a draft saved while grooming was on still carries the engine's line,
		# and nobody can contest that fine now (switch review S-1). Saving the
		# slip again drops it.
		lines = [r.additional_salary for r in doc.get("deductions") or []
		         if r.salary_component == GROOMING_COMPONENT and r.additional_salary]
		if lines and frappe.db.exists("Additional Salary", {"name": ("in", lines),
		                                                   "ref_doctype": ENGINE_REF}):
			frappe.throw(_("Grooming reds are switched off. Save this slip again to drop the "
			               "grooming line."))
		return
	# A fine deducted with the person's question unread is the show-cause risk
	# (brief, Decisions (3)). A manager's raise adds no money and holds nothing.
	asked = frappe.get_all("Grooming Mark", filters={
		"employee": doc.employee, "docstatus": 1, "asked_on": ("is", "set"),
		"kept_on": ("is", "not set"), "mark_date": ("between", [doc.start_date, doc.end_date])},
		fields=["mark_date"], order_by="mark_date asc", limit_page_length=1)
	if asked:
		first = (doc.employee_name or "").split(" ")[0] or doc.employee
		frappe.throw(_("{0} asked HR to look at the grooming red on {1}. Keep or remove it "
		               "first.").format(first, getdate(asked[0].mark_date).strftime("%-d %b")))
	summary = month_summary(doc.employee, doc.company, doc.start_date, doc.end_date, rule_set)
	if summary is None:
		return
	# Compare the ENGINE'S RECORD with the marks, not the slip row (architect
	# review M-1). Frappe HR scales an Additional Salary row by payment days when
	# the component "depends on payment days", and rounds it when the component
	# rounds - so the row can rightly differ from the marks' price, and comparing
	# the row would refuse the slip for ever. What must agree is the engine-made
	# Additional Salary (the price of the marks) and the slip must carry that
	# record's row.
	engine = frappe.get_all("Additional Salary", filters={
		"employee": doc.employee, "salary_component": GROOMING_COMPONENT, "docstatus": 1,
		"ref_doctype": ENGINE_REF, "payroll_date": ("between", [doc.start_date, doc.end_date])},
		fields=["name", "amount"])
	priced = sum(flt(a.amount) for a in engine)
	carried = {r.additional_salary for r in doc.get("deductions") or []
	           if r.salary_component == GROOMING_COMPONENT}
	if (flt(priced, 2) != flt(summary.grooming_deduction, 2)
			or any(a.name not in carried for a in engine)):
		frappe.throw(_("Grooming marks changed since this slip was saved. Save it again."))


def _note(doc, text):
	"""Keep a note for HR until the slip is saved (see post_slip_notes)."""
	doc.flags.alvoraa_notes = (doc.flags.alvoraa_notes or []) + [text]


def post_slip_notes(doc, method=None):
	"""doc_events on_update. Post the notes the validate hook kept.

	During validate a NEW slip is not in the database, and a comment pointing
	at it is refused ("Could not find Reference Name"). So notes wait here.
	"""
	for text in doc.flags.alvoraa_notes or []:
		doc.add_comment("Comment", text)
	doc.flags.alvoraa_notes = None


def _held_note(summary):
	return (
		"{0} day(s) are held for a missing check-out and are NOT in these paid "
		"days. Each is neither paid nor deducted until a manager confirms the "
		"employee left on time, and is then released as an Arrear."
	).format(summary.days_held)
