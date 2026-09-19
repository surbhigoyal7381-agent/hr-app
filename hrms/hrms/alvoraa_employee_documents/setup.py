"""Custom fields for the employee document checklist.

Employee belongs to ERPNext and Employee Onboarding to Frappe HR; both stay
untouched. The checklist is a child table on Employee added as a custom field,
so upgrades of either app leave it alone.
"""

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.setup import delete_custom_fields


def get_custom_fields():
	return {
		"Employee": [
			{
				"fieldname": "documents_tab",
				"label": "Documents",
				"fieldtype": "Tab Break",
				"insert_after": "feedback",
			},
			{
				"fieldname": "documents_summary",
				"label": "Documents Summary",
				"fieldtype": "Data",
				"insert_after": "documents_tab",
				"read_only": 1,
			},
			{
				"fieldname": "employee_documents",
				"label": "Employee Documents",
				"fieldtype": "Table",
				"options": "Employee Document",
				"insert_after": "documents_summary",
				"description": "Filled from the document types that apply to the grade when the employee is created. "
				"Attach a file to mark a row Received; only the verifier roles on the document type can mark it Verified.",
			},
		],
		"Employee Onboarding": [
			{
				"fieldname": "documents_section",
				"label": "Documents",
				"fieldtype": "Section Break",
				"insert_after": "activities",
				"collapsible": 1,
			},
			{
				"fieldname": "documents_summary",
				"label": "Document Checklist",
				"fieldtype": "Small Text",
				"insert_after": "documents_section",
				"read_only": 1,
				"description": "Counts from the employee's document checklist; open the Employee record to see the rows.",
			},
		],
	}


def make_custom_fields(update=True):
	create_custom_fields(get_custom_fields(), update=update)


def remove_custom_fields():
	delete_custom_fields(get_custom_fields())
