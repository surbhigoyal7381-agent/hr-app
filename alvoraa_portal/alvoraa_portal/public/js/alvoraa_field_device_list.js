// The phone list, "Field app phones" (slice 013 step 5, US-18).
//
// One list for rollout days and lost phones: who, which phone, how it joined,
// when, and whether it still works - with the block reason or the date under
// the status. Opens on "joined in the last 7 days". There is no "last seen",
// "online now" or map column, on purpose (PRIV-9, AC-114): this list is about
// phones, not about watching people. Who may see which rows is decided on the
// server (the company scoping hooks, C-11c); this file only shapes the columns.

frappe.listview_settings["Alvoraa Field Device"] = {
	add_fields: ["status", "block_reason", "status_changed_on", "join_method", "registered_on"],
	hide_name_column: true,
	filters: [["registered_on", ">=", frappe.datetime.add_days(frappe.datetime.get_today(), -7)]],

	formatters: {
		status(value, df, doc) {
			const esc = frappe.utils.escape_html;
			const colour = {
				Active: "green", Pending: "orange", Blocked: "red", Replaced: "gray",
				Removed: "gray", "Consent not given": "orange", "Signed out": "gray",
			}[value] || "gray";
			const word = {
				Active: __("Active"), Pending: __("Waiting for HR"), Blocked: __("Blocked"),
				Replaced: __("Replaced"), Removed: __("Removed"),
				"Consent not given": __("Not agreed yet"),
				"Signed out": __("Signed out"),
			}[value] || __(value || "");
			let under = "";
			if (value === "Blocked" && doc.block_reason) under = __(doc.block_reason);
			else if (["Blocked", "Replaced", "Removed", "Signed out"].includes(value) && doc.status_changed_on) {
				under = frappe.datetime.str_to_user(doc.status_changed_on);
			}
			// Colour and a word, never colour alone.
			return `<span class="indicator-pill ${esc(colour)}">${esc(word)}</span>` +
				(under ? `<div class="text-muted small">${esc(under)}</div>` : "");
		},
		join_method(value) {
			return value ? __(value) : __("Web check-in page");
		},
	},

	onload(listview) {
		// The note under the list. `$paging_area` sits below the rows and is
		// not redrawn on refresh, so the note is added once.
		if (listview.$paging_area && !listview.$paging_area.find(".alvfd-note").length) {
			listview.$paging_area.append(
				`<p class="text-muted small alvfd-note" style="margin:.5em 0 0">${frappe.utils.escape_html(
					__('There is no "last seen" or "online now" column, on purpose. This list is about phones, not about watching people.')
				)}</p>`
			);
		}
	},
};
