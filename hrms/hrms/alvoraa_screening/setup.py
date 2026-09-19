"""Screening questions on the application form.

Generic answer fields on Job Applicant, the screen-out rules on Job Opening.
The wording of each question lives on the Web Form (a field label there), so a
client can ask it their own way without a custom field per client.
"""

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.setup import delete_custom_fields

YES_NO = "\nYes\nNo"


def get_custom_fields():
	return {
		"Job Applicant": [
			{
				"fieldname": "screening_section",
				"label": "Screening",
				"fieldtype": "Section Break",
				"insert_after": "notes",
				"collapsible": 0,
			},
			{
				"fieldname": "screening_retail_experience",
				"label": "Has Relevant Retail Experience",
				"fieldtype": "Select",
				"options": YES_NO,
				"insert_after": "screening_section",
			},
			{
				"fieldname": "screening_years_in_category",
				"label": "Years Selling in This Category",
				"fieldtype": "Int",
				"insert_after": "screening_retail_experience",
			},
			{
				"fieldname": "screening_product_knowledge",
				"label": "Can Explain the Product to a Customer",
				"fieldtype": "Select",
				"options": YES_NO,
				"insert_after": "screening_years_in_category",
			},
			{
				"fieldname": "screening_roster_ok",
				"label": "Comfortable With the Store Roster",
				"fieldtype": "Select",
				"options": YES_NO,
				"insert_after": "screening_product_knowledge",
			},
			{
				"fieldname": "screening_festival_ok",
				"label": "Available on Festival Days",
				"fieldtype": "Select",
				"options": YES_NO,
				"insert_after": "screening_roster_ok",
			},
			{
				"fieldname": "screening_column",
				"fieldtype": "Column Break",
				"insert_after": "screening_festival_ok",
			},
			{
				"fieldname": "screening_current_employer",
				"label": "Current Employer",
				"fieldtype": "Data",
				"insert_after": "screening_column",
			},
			{
				"fieldname": "screening_category_experience",
				"label": "Categories Sold",
				"fieldtype": "Small Text",
				"insert_after": "screening_current_employer",
			},
			{
				"fieldname": "screening_expected_monthly_ctc",
				"label": "Expected Monthly CTC",
				"fieldtype": "Currency",
				"insert_after": "screening_category_experience",
			},
			{
				"fieldname": "screening_availability",
				"label": "When Can You Join",
				"fieldtype": "Small Text",
				"insert_after": "screening_expected_monthly_ctc",
			},
			{
				"fieldname": "screening_result_section",
				"label": "Screening Result",
				"fieldtype": "Section Break",
				"insert_after": "screening_availability",
			},
			{
				"fieldname": "screening_result",
				"label": "Screening Result",
				"fieldtype": "Select",
				"options": "\nPassed\nScreened Out",
				"insert_after": "screening_result_section",
				"read_only": 1,
				"in_list_view": 1,
				"in_standard_filter": 1,
			},
			{
				"fieldname": "screening_notes",
				"label": "Screening Notes",
				"fieldtype": "Small Text",
				"insert_after": "screening_result",
				"read_only": 1,
			},
		],
		"Job Opening": [
			{
				"fieldname": "screening_rules_section",
				"label": "Screening Rules",
				"fieldtype": "Section Break",
				"insert_after": "description",
				"collapsible": 1,
				"description": "Applicants who fail a rule are marked Screened Out as they come in. "
				"Leave everything blank to screen by hand.",
			},
			{
				"fieldname": "screening_require_retail_experience",
				"label": "Must Have Relevant Retail Experience",
				"fieldtype": "Check",
				"insert_after": "screening_rules_section",
			},
			{
				"fieldname": "screening_min_years",
				"label": "Minimum Years in the Category",
				"fieldtype": "Int",
				"insert_after": "screening_require_retail_experience",
			},
			{
				"fieldname": "screening_require_product_knowledge",
				"label": "Must Be Able to Explain the Product",
				"fieldtype": "Check",
				"insert_after": "screening_min_years",
			},
			{
				"fieldname": "screening_rules_column",
				"fieldtype": "Column Break",
				"insert_after": "screening_require_product_knowledge",
			},
			{
				"fieldname": "screening_require_roster_ok",
				"label": "Must Accept the Store Roster",
				"fieldtype": "Check",
				"insert_after": "screening_rules_column",
			},
			{
				"fieldname": "screening_require_festival_ok",
				"label": "Must Be Available on Festival Days",
				"fieldtype": "Check",
				"insert_after": "screening_require_roster_ok",
			},
			{
				"fieldname": "screening_max_monthly_ctc",
				"label": "Maximum Expected Monthly CTC",
				"fieldtype": "Currency",
				"insert_after": "screening_require_festival_ok",
			},
		],
	}


def make_custom_fields(update=True):
	create_custom_fields(get_custom_fields(), update=update)


def remove_custom_fields():
	delete_custom_fields(get_custom_fields())
