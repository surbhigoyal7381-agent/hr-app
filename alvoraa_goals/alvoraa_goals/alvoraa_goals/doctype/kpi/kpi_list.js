// Slice 010 group D (R8, VIS-12): the desk list shows the live KPIs. A review
// keeps its own copy of each KPI it rates, and that copy is the record of the
// review. Say so, so nobody reads this list as the review.
frappe.listview_settings["KPI"] = {
	onload(listview) {
		listview.page.add_inner_message(__("Live records, not the review record"));
	},
};
