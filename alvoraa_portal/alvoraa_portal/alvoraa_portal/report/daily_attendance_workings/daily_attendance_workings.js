// Copyright (c) 2026, Alvoraa and contributors
//
// One person, one month, a day per row (ALV-358). The last row is the month's
// total, taken from the salary working itself.

frappe.query_reports["Daily Attendance Workings"] = {
	filters: [
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
			reqd: 1,
		},
		{
			fieldname: "month",
			label: __("Month"),
			fieldtype: "Select",
			reqd: 1,
			options: ["January", "February", "March", "April", "May", "June", "July",
			          "August", "September", "October", "November", "December"],
			default: ["January", "February", "March", "April", "May", "June", "July",
			          "August", "September", "October", "November", "December"][
				frappe.datetime.str_to_obj(frappe.datetime.get_today()).getMonth()],
		},
		{
			fieldname: "year",
			label: __("Year"),
			fieldtype: "Int",
			reqd: 1,
			default: frappe.datetime.str_to_obj(frappe.datetime.get_today()).getFullYear(),
		},
	],

	// Words carry the meaning; colour only repeats it.
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) return value;
		if (data.is_total) return "<b>" + value + "</b>";
		if (column.fieldname === "status" && (data.status === "A" || data.status === "Held")) {
			value = "<b>" + value + "</b>";
		}
		if (column.fieldname === "red" && data.red > 0) {
			value = "<span style='color:var(--red,#b00)'>" + value + "</span>";
		}
		if (column.fieldname === "green" && data.green > 0) {
			value = "<span style='color:var(--green,#0a0)'>" + value + "</span>";
		}
		return value;
	},
};
