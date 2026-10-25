// Copyright (c) 2026, Alvoraa and contributors
//
// Slice 066 (Y4): who is waiting for a grooming review this month. The flag is
// worked out from the marks, not stored, so Report Builder cannot filter on it.

frappe.query_reports["Grooming Review Pending"] = {
	filters: [
		{
			fieldname: "month",
			label: __("Month"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_start(),
		},
	],
};
