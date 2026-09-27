# Copyright (c) 2026, Alvoraa and contributors
# For license information, please see license.txt

from calendar import monthrange

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on
from hrms.hr.doctype.leave_ledger_entry.leave_ledger_entry import create_leave_ledger_entry, delete_ledger_entry


class AttendanceDeduction(Document):
	def validate(self):
		if getdate(self.week_start) > getdate(self.week_end):
			frappe.throw(_("Week start is after week end."))
		self.compute_days()
		self.explanation = self.build_explanation()

	def compute_days(self):
		"""Counts and days follow from the violations and the rule; nothing is typed in."""
		rule = frappe.get_cached_doc("Attendance Deduction Rule", self.rule)
		rows = sorted(self.violations, key=lambda v: (str(v.attendance_date), str(v.actual_time or "")))
		free = int(rule.free_violations_per_week or 0)
		for i, row in enumerate(rows):
			row.counted = 0 if i < free else 1
		self.total_violations = len(rows)
		self.counted_violations = sum(1 for r in rows if r.counted)
		self.computed_days = flt(self.counted_violations * flt(rule.deduction_per_violation_days), 2)
		if flt(rule.round_up_from_days) and self.computed_days >= flt(rule.round_up_from_days):
			self.deduction_days = flt(rule.round_up_to_days)
		else:
			self.deduction_days = self.computed_days

	def build_explanation(self):
		rule = frappe.get_cached_doc("Attendance Deduction Rule", self.rule)
		free = int(rule.free_violations_per_week or 0)
		parts = [
			_("{0} violation(s) in the week of {1}.").format(self.total_violations, frappe.format(self.week_start, "Date")),
		]
		if free:
			parts.append(_("The first {0} is free.").format(free) if free == 1 else _("The first {0} are free.").format(free))
		parts.append(
			_("{0} counted × {1} day = {2} day(s).").format(
				self.counted_violations, flt(rule.deduction_per_violation_days), self.computed_days
			)
		)
		if self.deduction_days != self.computed_days:
			parts.append(
				_("{0} day(s) or more becomes a full {1} day.").format(flt(rule.round_up_from_days), flt(rule.round_up_to_days))
			)
		if self.docstatus == 1 or self.leave_deductions or self.lwp_days:
			taken = [f"{flt(r.days)} {_('from')} {r.leave_type}" for r in self.leave_deductions if flt(r.days)]
			if flt(self.lwp_days):
				taken.append(_("{0} as loss of pay").format(flt(self.lwp_days)))
			if taken:
				parts.append(_("Taken: ") + ", ".join(taken) + ".")
		return " ".join(parts)

	# ── Submit: consume leave, then pay ──────────────────────────────────
	def on_submit(self):
		self.apply_deduction()
		self.db_set(
			{
				"lwp_days": self.lwp_days,
				"lwp_amount": self.lwp_amount,
				"additional_salary": self.additional_salary,
				"explanation": self.build_explanation(),
			}
		)
		self.notify()

	def apply_deduction(self):
		rule = frappe.get_cached_doc("Attendance Deduction Rule", self.rule)
		remaining = flt(self.deduction_days)
		self.set("leave_deductions", [])
		if rule.deduct_from_leave_first and remaining > 0:
			for lt in sorted(rule.leave_types, key=lambda r: r.priority or 0):
				if remaining <= 0:
					break
				balance = flt(get_leave_balance_on(self.employee, lt.leave_type, getdate(self.week_end)))
				take = min(balance, remaining)
				if take <= 0:
					continue
				entry = self.consume_leave(lt.leave_type, take)
				self.append("leave_deductions", {"leave_type": lt.leave_type, "days": take, "leave_ledger_entry": entry})
				remaining = flt(remaining - take, 2)
		for row in self.leave_deductions:
			row.db_insert() if row.is_new() else row.db_update()
		self.lwp_days = remaining
		self.lwp_amount = 0
		self.additional_salary = None
		if remaining > 0:
			self.additional_salary, self.lwp_amount = self.create_loss_of_pay(rule, remaining)

	def consume_leave(self, leave_type, days):
		ref = frappe._dict(
			doctype=self.doctype, name=self.name, employee=self.employee, employee_name=self.employee_name, leave_type=leave_type
		)
		create_leave_ledger_entry(
			ref,
			{
				"leaves": -days,
				"from_date": self.week_end,
				"to_date": self.week_end,
				"company": self.company,
				"holiday_list": frappe.db.get_value("Employee", self.employee, "holiday_list"),
			},
			submit=True,
		)
		return frappe.db.get_value(
			"Leave Ledger Entry",
			{"transaction_type": self.doctype, "transaction_name": self.name, "leave_type": leave_type},
			"name",
			order_by="creation desc",
		)

	def daily_wage(self, rule):
		week_end = getdate(self.week_end)
		days_in_month = monthrange(week_end.year, week_end.month)[1]
		if rule.daily_wage_basis == "Gross Pay of Last Salary Slip":
			slip = frappe.db.get_value(
				"Salary Slip",
				{"employee": self.employee, "docstatus": 1},
				["gross_pay", "total_working_days"],
				order_by="end_date desc",
				as_dict=True,
			)
			if slip and flt(slip.total_working_days):
				return flt(slip.gross_pay) / flt(slip.total_working_days)
		base = frappe.db.get_value(
			"Salary Structure Assignment",
			{"employee": self.employee, "docstatus": 1, "from_date": ["<=", self.week_end]},
			"base",
			order_by="from_date desc",
		)
		if not base:
			frappe.throw(
				_("{0} has no Salary Structure Assignment on {1}, so the loss of pay cannot be valued.").format(
					self.employee_name, frappe.format(self.week_end, "Date")
				)
			)
		return flt(base) / days_in_month

	def create_loss_of_pay(self, rule, days):
		amount = flt(self.daily_wage(rule) * days, 2)
		if amount <= 0:
			return None, 0
		doc = frappe.get_doc(
			{
				"doctype": "Additional Salary",
				"employee": self.employee,
				"company": self.company,
				"salary_component": rule.lwp_salary_component,
				"amount": amount,
				"payroll_date": self.week_end,
				"currency": frappe.db.get_value("Company", self.company, "default_currency"),
				"ref_doctype": self.doctype,
				"ref_docname": self.name,
				"overwrite_salary_structure_amount": 0,
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert()
		doc.submit()
		return doc.name, amount

	# ── Cancel: put everything back ──────────────────────────────────────
	def on_cancel(self):
		self.ignore_linked_doctypes = ("Leave Ledger Entry", "Additional Salary")
		delete_ledger_entry(frappe._dict(transaction_type=self.doctype, transaction_name=self.name))
		if self.additional_salary:
			extra = frappe.get_doc("Additional Salary", self.additional_salary)
			if extra.docstatus == 1:
				extra.flags.ignore_permissions = True
				extra.cancel()
		self.db_set({"lwp_days": 0, "lwp_amount": 0, "additional_salary": None})

	# ── Notifications ────────────────────────────────────────────────────
	#
	# ALV-113 / 043 AC-17. Until this change one `sendmail` put the employee's
	# and the manager's user_id in ONE recipients list and sent both the
	# identical stored `explanation`. That text carries no rupee figure - it
	# never did - but it names the LEAVE TYPE the days came from:
	#
	#     "Taken: 0.5 from Sick Leave, 0.5 as loss of pay"
	#
	# So a manager whose report had half a day taken from Sick Leave read that
	# in his inbox, about a leave type the product hides on every screen. A
	# colleague's leave type is the one thing slice 002's one-way rule and the
	# design's section 9 both forbid, and it was going out by email.
	#
	# The fix is four rules, not "remove the number":
	#
	#   1. separate bodies    - the employee's is byte-identical to before
	#   2. days only          - no amount, no minutes, no per-day list
	#   3. no leave type      - the real leak
	#   4. separate sends     - one recipient each, so a later change to one
	#                           body cannot reach the other person
	#
	# Rule 4 is the one that makes the other three hold a year from now. Two
	# people on one `recipients` list share a body by construction, and the
	# next person to add a helpful line to "the email" adds it to both.

	def manager_body(self):
		"""What a manager may read: days, and nothing that names a leave type.

		Whole sentences with placeholders, never fragments joined up, because
		the figures move in word order between English, Hindi and Punjabi.
		"""
		total = flt(self.deduction_days)
		return _(
			"{0} lost {1} day(s) of paid time for late coming in the week of {2}, "
			"under your organisation's late-coming rule. The details are between "
			"{0} and HR."
		).format(
			self.employee_name,
			total,
			frappe.format(self.week_start, "Date"),
		)

	def notify(self):
		rule = frappe.get_cached_doc("Attendance Deduction Rule", self.rule)
		if not (rule.notify_employee or rule.notify_manager):
			return
		emp = frappe.db.get_value("Employee", self.employee, ["user_id", "reports_to"], as_dict=True)
		subject = _("Attendance deduction for {0}, week of {1}").format(
			self.employee_name, frappe.format(self.week_start, "Date")
		)

		# One send per recipient, each with its own body. The employee's body
		# is `self.explanation` exactly as it always was.
		sends = []
		if rule.notify_employee and emp.user_id:
			sends.append((emp.user_id, self.explanation))
		if rule.notify_manager and emp.reports_to:
			mgr = frappe.db.get_value("Employee", emp.reports_to, "user_id")
			# Nobody is their own manager's audience twice. If reports_to points
			# back at the employee's own login, the manager send is dropped
			# rather than sent a second, different body about themselves.
			if mgr and mgr != emp.user_id:
				sends.append((mgr, self.manager_body()))

		for recipient, message in sends:
			try:
				frappe.sendmail(
					recipients=[recipient],
					subject=subject,
					message=message,
					reference_doctype=self.doctype,
					reference_name=self.name,
				)
			except Exception:
				# One failed send must not stop the other. The employee's
				# notification is the one that matters most, and it goes first.
				frappe.log_error(frappe.get_traceback(), "Attendance Deduction notification failed")


def on_doctype_update():
	# the portal and the weekly job both look up one employee's week
	frappe.db.add_index("Attendance Deduction", ["employee", "week_start"])
