# Copyright (c) 2026, Alvoraa and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	conditions = {"docstatus": 1, "company": filters.company,
	              "week_start": ["between", [filters.from_date, filters.to_date]]}
	if filters.get("branch"):
		conditions["branch"] = filters.branch
	if filters.get("employee"):
		conditions["employee"] = filters.employee
	rows = frappe.get_all(
		"Attendance Deduction",
		filters=conditions,
		fields=["name", "employee", "employee_name", "branch", "week_start", "total_violations", "counted_violations",
		        "deduction_days", "lwp_days", "lwp_amount"],
		order_by="branch asc, week_start asc, employee asc",
	)
	for r in rows:
		r["leave_days"] = round(float(r.deduction_days or 0) - float(r.lwp_days or 0), 2)
	columns = [
		{"label": _("Deduction"), "fieldname": "name", "fieldtype": "Link", "options": "Attendance Deduction", "width": 150},
		{"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 110},
		{"label": _("Employee Name"), "fieldname": "employee_name", "width": 160},
		{"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 170},
		{"label": _("Week"), "fieldname": "week_start", "fieldtype": "Date", "width": 100},
		{"label": _("Violations"), "fieldname": "total_violations", "fieldtype": "Int", "width": 90},
		{"label": _("Counted"), "fieldname": "counted_violations", "fieldtype": "Int", "width": 80},
		{"label": _("Days"), "fieldname": "deduction_days", "fieldtype": "Float", "width": 80},
		{"label": _("From Leave"), "fieldname": "leave_days", "fieldtype": "Float", "width": 90},
		{"label": _("Loss of Pay Days"), "fieldname": "lwp_days", "fieldtype": "Float", "width": 110},
		{"label": _("Loss of Pay Amount"), "fieldname": "lwp_amount", "fieldtype": "Currency", "width": 130},
	]
	return columns, rows
