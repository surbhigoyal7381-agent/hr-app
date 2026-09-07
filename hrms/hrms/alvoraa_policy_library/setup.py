"""One custom field: who heads a department. Department belongs to ERPNext, so
it is a custom field, not an edit to the stock JSON. Top leadership in the
policy rules is the set of department heads."""

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.setup import delete_custom_fields


def get_custom_fields():
	return {
		"Department": [
			{
				"fieldname": "department_head",
				"label": "Department Head",
				"fieldtype": "Link",
				"options": "Employee",
				"insert_after": "company",
				"description": "Can create and edit the department's policies and reads every policy.",
			},
		],
	}


def make_custom_fields(update=True):
	create_custom_fields(get_custom_fields(), update=update)


def remove_custom_fields():
	delete_custom_fields(get_custom_fields())
