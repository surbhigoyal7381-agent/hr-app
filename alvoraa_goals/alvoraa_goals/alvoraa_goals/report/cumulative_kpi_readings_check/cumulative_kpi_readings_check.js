// Copyright (c) 2026, Alvoraa and contributors
// For license information, please see license.txt

frappe.query_reports["Cumulative KPI Readings Check"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
		},
		{
			fieldname: "appraisal_cycle",
			label: __("Appraisal Cycle"),
			fieldtype: "Link",
			options: "Appraisal Cycle",
		},
	],
};
