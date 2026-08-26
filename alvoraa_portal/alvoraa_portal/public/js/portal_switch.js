/**
 * Make "Switch to Employee Portal" actually work.
 *
 * Frappe v16 builds the sidebar dropdown, then handles a click with:
 *
 *     current_item.onClick(item);
 *
 * For the HELP dropdown it first translates the item type properly:
 *
 *     if (element.item_type === "Route")  dropdown_children.url = element.route;
 *     if (element.item_type === "Action") dropdown_children.onClick = ...;
 *
 * but add_navbar_items(), which builds the SETTINGS dropdown, does neither - it
 * copies the label across and pushes the row. So the item has no url and no
 * onClick, the click throws, and nothing happens. Any item added through Navbar
 * Settings is inert in this version; ours was not special.
 *
 * onClick cannot come from the server: Navbar Item is data, and a handler is a
 * function. So we bind it here. The item still comes from Navbar Settings - it
 * renders with the right label, icon and position - and this only supplies the
 * behaviour Frappe left out.
 *
 * Matched on `data-app-route`, which the renderer writes from the item's route,
 * so this binds OUR row and nothing else in that menu.
 */

frappe.provide("alvoraa");

alvoraa.bind_portal_switch = function () {
	const ROUTE = "/hrms-employee";
	const SELECTOR = `.dropdown-menu-item[data-app-route="${ROUTE}"]`;

	document.querySelectorAll(SELECTOR).forEach((el) => {
		if (el.dataset.alvoraaBound) return;   // the menu is rebuilt on navigation
		el.dataset.alvoraaBound = "1";

		// Capture phase, and stop propagation: Frappe's own handler on the same
		// element would still run and throw on the missing onClick, which shows
		// the user an error after we have already sent them on their way.
		el.addEventListener(
			"click",
			function (e) {
				e.preventDefault();
				e.stopImmediatePropagation();
				window.location.href = ROUTE;
			},
			true
		);

		// Give it a real href too, so it behaves like a link: middle-click and
		// "open in new tab" work, and the status bar shows where it goes.
		const a = el.querySelector("a");
		if (a && !a.getAttribute("href")) a.setAttribute("href", ROUTE);
	});
};

$(document).on("startup", function () {
	alvoraa.bind_portal_switch();
});

// The sidebar is rebuilt as the user moves around, which drops our binding. A
// short poll is unglamorous but survives that, and every other way in would mean
// patching a Frappe class we do not own.
$(document).ready(function () {
	alvoraa.bind_portal_switch();
	setInterval(alvoraa.bind_portal_switch, 2000);
});
