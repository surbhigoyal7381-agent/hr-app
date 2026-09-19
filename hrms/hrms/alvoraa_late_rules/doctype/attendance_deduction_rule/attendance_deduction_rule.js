// Copyright (c) 2026, Alvoraa and contributors
// For license information, please see license.txt

frappe.ui.form.on("Attendance Deduction Rule", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Run for Range"), () => {
			const d = new frappe.ui.Dialog({
				title: __("Process weeks"),
				fields: [
					{ fieldname: "from_date", fieldtype: "Date", label: __("From Date"), reqd: 1 },
					{ fieldname: "to_date", fieldtype: "Date", label: __("To Date"), reqd: 1, default: frappe.datetime.get_today() },
				],
				primary_action_label: __("Run"),
				primary_action(values) {
					frm.call({ method: "run_for_range", doc: frm.doc, args: values, freeze: true }).then((r) => {
						const s = r.message || {};
						frappe.msgprint(
							__("{0} week(s) processed: {1} deduction(s) created, {2} already existed.", [
								s.weeks, s.created, s.existing,
							])
						);
						frm.reload_doc();
					});
					d.hide();
				},
			});
			d.show();
		});
	},
});
