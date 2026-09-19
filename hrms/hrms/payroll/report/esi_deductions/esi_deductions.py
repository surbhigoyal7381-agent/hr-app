# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder.functions import Extract

EMPLOYEE_TYPE = "ESI"
EMPLOYER_TYPE = "Employer ESI"


def execute(filters=None):
	if not frappe.db.exists("Salary Component", {"component_type": ["in", [EMPLOYEE_TYPE, EMPLOYER_TYPE]]}):
		frappe.msgprint(
			_("Salary components of type ESI or Employer ESI are not set up."),
			title=_("Missing Salary Components"),
			indicator="red",
		)
		return [], []

	data = get_data(filters)
	columns = get_columns() if data else []
	return columns, data


def get_columns():
	return [
		{"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 160},
		{"label": _("Employee Name"), "fieldname": "employee_name", "width": 160},
		{"label": _("ESI Number"), "fieldname": "esi_number", "fieldtype": "Data", "width": 140},
		{"label": _("Gross Pay"), "fieldname": "gross_pay", "fieldtype": "Currency", "width": 130},
		{"label": _("Employee ESI"), "fieldname": "employee_esi", "fieldtype": "Currency", "width": 130},
		{"label": _("Employer ESI"), "fieldname": "employer_esi", "fieldtype": "Currency", "width": 130},
		{"label": _("Total"), "fieldname": "total", "fieldtype": "Currency", "width": 130},
	]


def get_conditions(filters):
	SalarySlip = DocType("Salary Slip")
	clauses = []
	if filters.get("department"):
		clauses.append(SalarySlip.department == filters["department"])
	if filters.get("branch"):
		clauses.append(SalarySlip.branch == filters["branch"])
	if filters.get("company"):
		clauses.append(SalarySlip.company == filters["company"])
	if filters.get("month"):
		clauses.append(Extract("month", SalarySlip.start_date) == int(filters["month"]))
	if filters.get("year"):
		clauses.append(Extract("year", SalarySlip.start_date) == int(filters["year"]))
	if filters.get("mode_of_payment"):
		clauses.append(SalarySlip.mode_of_payment == filters["mode_of_payment"])
	return clauses


def get_data(filters):
	SalarySlip = DocType("Salary Slip")
	SalaryDetail = DocType("Salary Detail")
	SalaryComponent = DocType("Salary Component")
	Employee = DocType("Employee")

	component_type = frappe._dict(
		frappe.qb.from_(SalaryComponent)
		.select(SalaryComponent.name, SalaryComponent.component_type)
		.where(SalaryComponent.component_type.isin([EMPLOYEE_TYPE, EMPLOYER_TYPE]))
		.run()
	)
	if not component_type:
		return []

	where = SalarySlip.docstatus == 1
	for clause in get_conditions(filters):
		where = where & clause

	rows = (
		frappe.qb.from_(SalarySlip)
		.join(SalaryDetail)
		.on(SalarySlip.name == SalaryDetail.parent)
		.select(
			SalarySlip.name,
			SalarySlip.employee,
			SalarySlip.employee_name,
			SalarySlip.gross_pay,
			SalaryDetail.salary_component,
			SalaryDetail.amount,
		)
		.where(where & SalaryDetail.salary_component.isin(list(component_type)) & (SalaryDetail.amount > 0))
		.run(as_dict=True)
	)
	if not rows:
		return []

	esi_numbers = {}
	if frappe.get_meta("Employee").has_field("esi_number"):
		esi_numbers = frappe._dict(frappe.qb.from_(Employee).select(Employee.name, Employee.esi_number).run())

	by_slip = {}
	for r in rows:
		slip = by_slip.setdefault(
			r.name,
			{
				"employee": r.employee,
				"employee_name": r.employee_name,
				"esi_number": esi_numbers.get(r.employee),
				"gross_pay": r.gross_pay,
				"employee_esi": 0,
				"employer_esi": 0,
			},
		)
		key = "employee_esi" if component_type[r.salary_component] == EMPLOYEE_TYPE else "employer_esi"
		slip[key] += r.amount

	data = []
	for slip in by_slip.values():
		slip["total"] = slip["employee_esi"] + slip["employer_esi"]
		data.append(slip)
	data.sort(key=lambda d: d["employee"])
	return data
