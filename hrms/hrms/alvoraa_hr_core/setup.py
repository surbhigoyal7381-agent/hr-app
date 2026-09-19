"""Custom fields that put attendance into the appraisal score.

They sit on the stock Appraisal Cycle and Appraisal doctypes so that Frappe HR's
own final-score formula can read them: the formula is evaluated with every field
of the Appraisal and its cycle in scope.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.setup import delete_custom_fields

NO_DATA_OPTIONS = "Give full marks\nUse the average of the other parts"


def get_custom_fields():
	return {
		"Appraisal Cycle": [
			{
				"fieldname": "attendance_score_section",
				"label": "Attendance in the Score",
				"fieldtype": "Section Break",
				"insert_after": "calculate_final_score_based_on_formula",
				"collapsible": 0,
			},
			{
				"fieldname": "include_attendance_score",
				"label": "Include Attendance Score",
				"fieldtype": "Check",
				"insert_after": "attendance_score_section",
				"description": "When ticked, the final score formula is built from the three weights below "
				"and every appraisal gets an attendance score computed from its attendance records.",
			},
			{
				"fieldname": "goal_weight",
				"label": "Targets Weight (%)",
				"fieldtype": "Percent",
				"insert_after": "include_attendance_score",
				"default": "50",
				"depends_on": "include_attendance_score",
			},
			{
				"fieldname": "feedback_weight",
				"label": "Manager Feedback Weight (%)",
				"fieldtype": "Percent",
				"insert_after": "goal_weight",
				"default": "30",
				"depends_on": "include_attendance_score",
			},
			{
				"fieldname": "attendance_weight",
				"label": "Attendance Weight (%)",
				"fieldtype": "Percent",
				"insert_after": "feedback_weight",
				"default": "20",
				"depends_on": "include_attendance_score",
			},
			{
				"fieldname": "attendance_score_column",
				"fieldtype": "Column Break",
				"insert_after": "attendance_weight",
			},
			{
				"fieldname": "attendance_reliability_weight",
				"label": "Reliability Share (%)",
				"fieldtype": "Percent",
				"insert_after": "attendance_score_column",
				"default": "60",
				"depends_on": "include_attendance_score",
				"description": "Share of the attendance score that comes from days present versus days scheduled.",
			},
			{
				"fieldname": "attendance_punctuality_weight",
				"label": "Punctuality Share (%)",
				"fieldtype": "Percent",
				"insert_after": "attendance_reliability_weight",
				"default": "40",
				"depends_on": "include_attendance_score",
				"description": "Share that comes from days on time versus days present.",
			},
			{
				"fieldname": "attendance_deduction_penalty",
				"label": "Penalty per Deducted Day",
				"fieldtype": "Float",
				"insert_after": "attendance_punctuality_weight",
				"default": "0.25",
				"depends_on": "include_attendance_score",
				"description": "Score points taken off for each day the late-coming rule deducted.",
			},
			{
				"fieldname": "count_paid_leave_as_absent",
				"label": "Count Paid Leave as Absent",
				"fieldtype": "Check",
				"insert_after": "attendance_deduction_penalty",
				"depends_on": "include_attendance_score",
			},
			{
				"fieldname": "attendance_when_no_data",
				"label": "When There Is No Attendance Data",
				"fieldtype": "Select",
				"options": NO_DATA_OPTIONS,
				"default": "Use the average of the other parts",
				"insert_after": "count_paid_leave_as_absent",
				"depends_on": "include_attendance_score",
			},
			{
				"fieldname": "attendance_exempt_grades",
				"label": "Exempt Grades",
				"fieldtype": "Table MultiSelect",
				"options": "Appraisal Cycle Exempt Grade",
				"insert_after": "attendance_when_no_data",
				"depends_on": "include_attendance_score",
				"description": "Employees in these grades get full marks for attendance.",
			},
		],
		"Appraisal": [
			{
				"fieldname": "attendance_section",
				"label": "Attendance",
				"fieldtype": "Section Break",
				"insert_after": "final_score",
				"collapsible": 1,
				"depends_on": "eval:doc.attendance_summary",
			},
			{
				"fieldname": "attendance_score",
				"label": "Attendance Score",
				"fieldtype": "Float",
				"insert_after": "attendance_section",
				"read_only": 1,
				"precision": "2",
			},
			{
				"fieldname": "attendance_reliability_pct",
				"label": "Reliability (%)",
				"fieldtype": "Percent",
				"insert_after": "attendance_score",
				"read_only": 1,
			},
			{
				"fieldname": "attendance_punctuality_pct",
				"label": "Punctuality (%)",
				"fieldtype": "Percent",
				"insert_after": "attendance_reliability_pct",
				"read_only": 1,
			},
			{
				"fieldname": "attendance_column",
				"fieldtype": "Column Break",
				"insert_after": "attendance_punctuality_pct",
			},
			{
				"fieldname": "attendance_deduction_days",
				"label": "Days Deducted by the Late Rule",
				"fieldtype": "Float",
				"insert_after": "attendance_column",
				"read_only": 1,
			},
			{
				"fieldname": "attendance_summary",
				"label": "Attendance Summary",
				"fieldtype": "Small Text",
				"insert_after": "attendance_deduction_days",
				"read_only": 1,
			},
		],
	}


def make_custom_fields(update=True):
	create_custom_fields(get_custom_fields(), update=update)


def remove_custom_fields():
	delete_custom_fields(get_custom_fields())
