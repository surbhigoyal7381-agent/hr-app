// Slice 010 group D (VIS-12): the desk list shows the live Objectives. A review
// keeps its own copy of each Objective it rates, and that copy is the record of
// the review.
frappe.listview_settings["Individual Goal"] = {
	onload(listview) {
		listview.page.add_inner_message(__("Live records, not the review record"));
	},
};
