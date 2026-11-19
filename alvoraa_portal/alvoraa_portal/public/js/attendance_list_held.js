/* Slice 085 (ALV-392, AC-8): the Attendance list gains a Held chip in amber,
   with an icon and the word. Wraps the stock indicator rather than replacing it,
   so every other status keeps its colour. The Held filter value itself comes from
   the status options (the Property Setter). */
(function () {
	var settings = (frappe.listview_settings["Attendance"] = frappe.listview_settings["Attendance"] || {});
	var stock = settings.get_indicator;
	settings.get_indicator = function (doc) {
		if (doc.status === "Held") {
			return ["\u26A0 " + __("Held"), "orange", "status,=,Held"];
		}
		return stock ? stock.call(this, doc) : undefined;
	};
})();
