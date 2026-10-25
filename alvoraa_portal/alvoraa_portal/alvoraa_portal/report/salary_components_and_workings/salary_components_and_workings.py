"""Every salary component for a month, with the workings behind each one.

WHAT THIS IS FOR. The client checks the pay rules against a spreadsheet. The
spreadsheet is a model of what the engine ought to do; this is what the engine
actually did. Put side by side, a disagreement is a bug in one of them, and
until both exist there is nothing to compare.

IT RECALCULATES NOTHING. Every figure comes from `payroll_slip.month_summary`,
the same call the salary slip itself makes. A report with its own arithmetic
would eventually disagree with the payslip, and the one place that must never
happen is the document somebody is checking the payslip against.

IT READS; IT WRITES NOTHING. Running it on a closed month is safe.

WHY IT IS EMPTY ON EVERY OTHER TENANT. The engine is driven by one
`Alvoraa Payroll Rule Set` per company, and `month_summary` returns None where
there is none. That is not an error - it is every company but the one this was
built for - so the report says so in words rather than showing a blank grid.
"""

import frappe
from frappe import _
from frappe.utils import flt, get_first_day, get_last_day, nowdate

from alvoraa_portal.payroll_rules_apply import prepare, rule_set_for
from alvoraa_portal.payroll_slip import month_summary


def execute(filters=None):
	filters = frappe._dict(filters or {})
	company = filters.get("company")
	if not company:
		frappe.throw(_("Choose a company."))

	from_date = filters.get("from_date") or get_first_day(nowdate())
	to_date = filters.get("to_date") or get_last_day(from_date)

	rule_set, live = _rules_for_reading(company)
	if not rule_set:
		return _columns(), [], _no_rules(company)

	# Built ONCE and handed to every employee. `month_summary` would otherwise
	# rebuild the slab table, the holiday list, the green windows and the shift
	# hours for each of 363 people - the same work, 363 times, in a report
	# somebody is waiting on.
	ctx = prepare(rule_set, from_date, to_date)

	rows, skipped = [], []
	for emp in _employees(company, filters):
		summary = month_summary(emp.name, company, from_date, to_date,
		                        rule_set=rule_set, ctx=ctx)
		if summary is None:
			continue
		if not summary.days_with_record and not flt(emp.base):
			# Nothing to show and nothing to pay. Named at the end rather than
			# given a row of noughts that reads like a finding.
			skipped.append(emp.employee_name or emp.name)
			continue
		rows.append(_row(emp, summary))

	return _columns(), rows, _message(rule_set, from_date, to_date, skipped, live), None


def _rules_for_reading(company):
	"""The rule set to show, and whether it is actually live.

	READING IS NOT THE SAME ACT AS SWITCHING ON, and the report used to make it
	so. `rule_set_for` finds only a set with `enabled = 1` - the same flag the
	hooks wake up on - so the only way to see these figures was to start the
	engine judging attendance and changing payslips for real.

	That is backwards. This report exists so somebody can check the rules
	BEFORE committing to them, against a spreadsheet, with nothing at stake.
	Making them commit first to look is how a wrong figure reaches a payslip
	before anybody has seen it.

	So a rule set that is SAVED BUT SWITCHED OFF is read here, and the message
	says plainly that it is not live. Nothing else in the product does this:
	every other path still goes through `rule_set_for` and still does nothing
	without an enabled set. The engine stays asleep.
	"""
	live = rule_set_for(company)
	if live:
		return live, True
	name = frappe.db.get_value("Alvoraa Payroll Rule Set", {"company": company},
	                           "name")
	if not name:
		return None, False
	return frappe.get_cached_doc("Alvoraa Payroll Rule Set", name), False


def _employees(company, filters):
	"""Active employees, with the three fields the rules are keyed on.

	Read through `frappe.get_list`, so a store's HR person gets their store and
	nothing else - the same scoping every other reader on this app obeys.
	"""
	where = {"status": "Active", "company": company}
	if filters.get("branch"):
		where["branch"] = filters.get("branch")
	if filters.get("department"):
		where["department"] = filters.get("department")
	if filters.get("employee"):
		where["name"] = filters.get("employee")

	fields = ["name", "employee_name", "branch", "department", "designation",
	          "employment_type"]
	rows = frappe.get_list("Employee", filters=where, fields=fields,
	                       order_by="branch asc, employee_name asc",
	                       limit_page_length=0)

	# The monthly figure every money column hangs off. One query, not one each.
	bases = {}
	if rows:
		for a in frappe.get_all(
				"Salary Structure Assignment",
				filters={"employee": ("in", [r.name for r in rows]),
				         "docstatus": 1},
				fields=["employee", "base", "from_date"],
				order_by="from_date asc", limit_page_length=0):
			bases[a.employee] = a.base          # last one wins: the newest
	for r in rows:
		r.base = bases.get(r.name, 0)
	return rows


def _row(emp, s):
	return {
		"employee": emp.name,
		"employee_name": emp.employee_name,
		"branch": emp.branch,
		"department": emp.department,
		"employment_type": emp.employment_type,

		"days_with_record": s.days_with_record,
		"days_worked": s.days_worked,
		"days_on_leave": s.days_on_leave,
		"days_absent": s.days_absent,
		"days_held": s.days_held,

		"quarters": s.total_quarters,
		"quarter_days": flt(s.quarter_days, 2),

		"leave_earned": flt(s.leave_credits_earned, 2),
		"leave_used": flt(s.leave_used_for_approved, 2),
		"leave_encashed": flt(s.leave_encashed, 2),

		"paid_days": flt(s.paid_days, 2),
		"daily_rate": flt(s.daily_rate, 2),
		"basic": flt(s.earning_basic, 2),

		"greens": s.greens,
		"green_earning": flt(s.green_earning, 2),
		"reds": s.reds,
		"free_reds": s.free_reds,
		"deductible_reds": s.deductible_reds,
		"red_deduction": flt(s.red_deduction, 2),
		"grooming_days": s.grooming_days,
		"grooming_deduction": flt(s.grooming_deduction, 2),

		"incentive": flt(s.incentive, 2),
		"gross": flt(s.gross, 2),
		"other_deductions": flt(s.other_deductions, 2),
		"net": flt(s.net, 2),

		# Why this person's figures are what they are, in the engine's own
		# words. The column that turns a disagreement into a conversation.
		"why": " ".join(s.notes) if s.notes else "",
	}


def _no_rules(company):
	return _(
		"<b>{0} has no payroll rule set switched on</b>, so there is nothing "
		"to work out. This report shows what the pay-rule engine did, and the "
		"engine does nothing for a company without a rule set - which is every "
		"company except the one these rules were written for."
	).format(frappe.bold(company))


def _message(rule_set, from_date, to_date, skipped, live=True):
	bits = []
	if not live:
		# FIRST, and said plainly. A reader who assumes these figures are
		# already being applied will not chase a wrong one, because they will
		# think it is somebody else's job now.
		bits.append(_(
			"<b>These rules are not switched on.</b> The figures below are what "
			"they WOULD produce. No attendance has been judged and no salary "
			"slip carries any of it. Tick <b>Enabled</b> on the rule set when "
			"the numbers are right."))
	bits += [
		_("Every figure here comes from the same calculation the salary slip "
		  "uses, so the two cannot disagree. Nothing is written by running it."),
		_("Period: {0} to {1}. Rule set: {2}{3}.").format(
			from_date, to_date, frappe.bold(rule_set.name),
			"" if live else _(" (not live)")),
	]
	if skipped:
		bits.append(_(
			"{0} active employee(s) have neither an attendance record in this "
			"period nor a salary structure, so they have no row: {1}"
		).format(len(skipped), ", ".join(sorted(skipped)[:12])
		         + ("..." if len(skipped) > 12 else "")))
	return "<br>".join(bits)


def _columns():
	def c(key, label, width=110, kind="Float", opts=None):
		col = {"fieldname": key, "label": _(label), "fieldtype": kind,
		       "width": width}
		if opts:
			col["options"] = opts
		return col

	return [
		c("employee", "Employee", 110, "Link", "Employee"),
		c("employee_name", "Name", 170, "Data"),
		c("branch", "Branch", 130, "Data"),
		c("department", "Department", 130, "Data"),
		c("employment_type", "Type", 90, "Data"),

		c("days_with_record", "Days recorded", 110, "Int"),
		# Float since slice 063: a half-day leave is half worked, half on leave.
		c("days_worked", "Worked", 80, "Float"),
		c("days_on_leave", "On leave", 85, "Float"),
		c("days_absent", "Absent", 80, "Float"),
		c("days_held", "Held", 70, "Float"),

		c("quarters", "Quarters off", 100, "Int"),
		c("quarter_days", "= days", 80),

		c("leave_earned", "Leave earned", 105),
		c("leave_used", "Leave used", 95),
		c("leave_encashed", "Leave encashed", 115),

		c("paid_days", "Paid days", 90),
		c("daily_rate", "Daily rate", 100, "Currency"),
		c("basic", "Basic earned", 110, "Currency"),

		c("greens", "Greens", 75, "Int"),
		c("green_earning", "Green pay", 100, "Currency"),
		c("reds", "Reds", 65, "Int"),
		c("free_reds", "Free reds", 85, "Int"),
		c("deductible_reds", "Reds charged", 110, "Int"),
		c("red_deduction", "Red deduction", 115, "Currency"),
		# Slice 066: the month's grooming reds and what they cost, after the cap.
		c("grooming_days", "Grooming reds", 110, "Int"),
		c("grooming_deduction", "Grooming deduction", 140, "Currency"),

		c("incentive", "Incentive", 95, "Currency"),
		c("gross", "Gross", 110, "Currency"),
		c("other_deductions", "Other deductions", 130, "Currency"),
		c("net", "Net", 115, "Currency"),

		c("why", "Why", 420, "Small Text"),
	]
