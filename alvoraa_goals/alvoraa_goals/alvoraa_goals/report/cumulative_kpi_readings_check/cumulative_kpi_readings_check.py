# Copyright (c) 2026, Alvoraa and contributors
# For license information, please see license.txt

"""Cumulative KPIs whose readings look like running totals. Read-only, for HR.

Slice 010 group D fix round (release risk in the code review, 05 section 8).
Since group D, a Cumulative KPI's reading is "the amount since the last update",
and a review adds up the approved readings dated in its period (decision 1, R4).
Readings typed before that were often the total so far. Added up, they count
the same work more than once. This lists every Cumulative KPI whose approved
readings never go down (each one at least the one before), so HR can check and
correct them in the desk before relying on the reviews that count them.

It changes nothing. It lists only KPIs of the people the caller looks after as
HR - their companies, narrowed to their store when they hold a Branch User
Permission (slice 030) - and shows no rating. Three queries, plus one per 500 KPIs.
"""

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	from hrms.alvoraa_hr_core.access import permitted_employees

	filters = frappe._dict(filters or {})
	if not {"HR Manager", "HR User", "System Manager"} & set(frappe.get_roles()):
		frappe.throw(_("Only HR can run this report."), frappe.PermissionError)

	return _columns(), _rows(permitted_employees(), filters.get("appraisal_cycle"), filters.get("company"))


def _columns():
	return [
		{"label": _("KPI"), "fieldname": "kpi", "fieldtype": "Link", "options": "KPI", "width": 130},
		{"label": _("KPI Name"), "fieldname": "kpi_name", "width": 200},
		{"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
		{"label": _("Employee Name"), "fieldname": "employee_name", "width": 160},
		{"label": _("Appraisal Cycle"), "fieldname": "appraisal_cycle", "fieldtype": "Link",
		 "options": "Appraisal Cycle", "width": 150},
		{"label": _("Approved Readings"), "fieldname": "readings", "fieldtype": "Int", "width": 90},
		{"label": _("First Reading"), "fieldname": "first_value", "fieldtype": "Float", "width": 100},
		{"label": _("Last Reading"), "fieldname": "last_value", "fieldtype": "Float", "width": 100},
		{"label": _("Readings Added Up"), "fieldname": "sum_of_readings", "fieldtype": "Float", "width": 120},
		{"label": _("Live Number"), "fieldname": "actual_value", "fieldtype": "Float", "width": 100},
		{"label": _("What to check"), "fieldname": "note", "width": 320},
	]


def _rows(employees, cycle=None, company=None):
	"""`employees` is the set the caller may see; the company filter only narrows it."""
	if not employees:
		return []
	emp_filters = {"name": ["in", sorted(employees)]}
	if company:
		emp_filters["company"] = company
	kpi_filters = {
		"progress_mode": "Cumulative",
		"status": ["!=", "Cancelled"],
		"employee": ["in", frappe.get_all("Employee", filters=emp_filters, pluck="name") or [""]],
	}
	if cycle:
		kpi_filters["appraisal_cycle"] = cycle
	kpis = frappe.get_all(
		"KPI",
		filters=kpi_filters,
		fields=["name", "kpi_name", "employee", "employee_name", "appraisal_cycle", "actual_value"],
		order_by="employee_name asc, kpi_name asc",
	)

	readings = {}
	names = [k.name for k in kpis]
	for start in range(0, len(names), 500):
		for r in frappe.get_all(
			"KPI Progress Log",
			filters={"parenttype": "KPI", "parent": ["in", names[start:start + 500]], "approval_status": "Approved"},
			fields=["parent", "value", "log_date", "creation"],
			order_by="log_date asc, creation asc",
		):
			readings.setdefault(r.parent, []).append(flt(r.value))

	out = []
	for k in kpis:
		values = readings.get(k.name) or []
		if len(values) < 2 or not values[-1] or any(b < a for a, b in zip(values, values[1:])):
			continue
		out.append({
			"kpi": k.name,
			"kpi_name": k.kpi_name,
			"employee": k.employee,
			"employee_name": k.employee_name,
			"appraisal_cycle": k.appraisal_cycle,
			"readings": len(values),
			"first_value": values[0],
			"last_value": values[-1],
			"sum_of_readings": flt(sum(values), 6),
			"actual_value": flt(k.actual_value),
			"note": _("Every reading is at least the one before. If they were totals so far, a review adds "
			          "them up and counts the same work more than once."),
		})
	return out
