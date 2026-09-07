# Copyright (c) 2026, Alvoraa and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate


class AttendanceDeductionRule(Document):
	def validate(self):
		if self.late_threshold_minutes <= 0:
			frappe.throw(_("Late Arrival Threshold must be more than zero minutes."))
		if self.count_early_exit and (self.early_exit_threshold_minutes or 0) <= 0:
			frappe.throw(_("Early Exit Threshold must be more than zero minutes."))
		if flt(self.deduction_per_violation_days) <= 0:
			frappe.throw(_("Deduction per Counted Violation must be more than zero."))
		if flt(self.round_up_from_days) and flt(self.round_up_to_days) < flt(self.round_up_from_days):
			frappe.throw(_("Round Up To cannot be smaller than Round Up From."))
		if self.deduct_from_leave_first and not self.leave_types:
			frappe.throw(_("Add at least one leave type, or untick Deduct from Leave Balance First."))
		if self.lwp_salary_component:
			ctype = frappe.db.get_value("Salary Component", self.lwp_salary_component, "type")
			if ctype != "Deduction":
				frappe.throw(_("{0} must be a Deduction component.").format(self.lwp_salary_component))
		self.validate_one_enabled_rule()

	def validate_one_enabled_rule(self):
		if not self.enabled:
			return
		clash = frappe.db.get_value(
			"Attendance Deduction Rule",
			{"company": self.company, "shift_type": self.shift_type or "", "enabled": 1, "name": ["!=", self.name]},
			"name",
		)
		if clash:
			frappe.throw(
				_("{0} is already the enabled rule for this company and shift. Disable one of them.").format(clash)
			)

	@frappe.whitelist()
	def run_for_range(self, from_date, to_date):
		"""HR button: process every week that starts within the range."""
		from hrms.alvoraa_late_rules.late_rules import run_for_range

		return run_for_range(self.name, from_date, to_date)
