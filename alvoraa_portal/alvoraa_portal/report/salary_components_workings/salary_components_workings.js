// Copyright (c) 2026, Alvoraa and contributors
//
// A month at a time, because that is the unit the rules work in: the leave
// cliff, the free reds and the daily rate are all monthly, and a report
// spanning two months would add together figures that were never meant to meet.

frappe.query_reports["Salary Components and Workings"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "from_date",
			label: __("From"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_start(),
		},
		{
			fieldname: "to_date",
			label: __("To"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_end(),
		},
		{
			fieldname: "branch",
			label: __("Branch"),
			fieldtype: "Link",
			options: "Branch",
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
		},
		{
			fieldname: "employee",
			label: __("One employee"),
			fieldtype: "Link",
			options: "Employee",
		},
	],

	// Red where money comes off, green where it goes on. Never colour alone:
	// every one of these columns carries its own number beside it.
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) return value;
		if (column.fieldname === "red_deduction" && data.red_deduction > 0) {
			value = "<span style='color:var(--red,#b00)'>" + value + "</span>";
		}
		if (column.fieldname === "green_earning" && data.green_earning > 0) {
			value = "<span style='color:var(--green,#0a0)'>" + value + "</span>";
		}
		if (column.fieldname === "days_held" && data.days_held > 0) {
			// Held days are neither paid nor deducted until somebody confirms
			// when the person left, so they are the figure to chase first.
			value = "<b>" + value + "</b>";
		}
		return value;
	},
};
