frappe.ui.form.on("Delivery Order", {
    refresh(frm) {
        _update_status_badge(frm);

        if (!frm.is_new()) {
            // Status update button (internal/ops users)
            if (!["Delivered", "Cancelled", "Returned"].includes(frm.doc.current_status)) {
                frm.add_custom_button(__("Update Status"), function () {
                    _show_status_update_dialog(frm);
                }, __("Actions"));
            }

            // Assign partner button
            if (!frm.doc.assigned_to_partner && frm.doc.current_status === "Pending") {
                frm.add_custom_button(__("Assign Delivery Partner"), function () {
                    _show_assign_partner_dialog(frm);
                }, __("Actions"));
            }

            // Mark as delivered (quick action)
            if (frm.doc.current_status === "At Location") {
                frm.add_custom_button(__("Mark Delivered"), function () {
                    frappe.confirm(
                        `Mark order <b>${frm.doc.name}</b> as Delivered?`,
                        function () {
                            frappe.call({
                                method: "alvoraa_portal.controllers.delivery_order.update_delivery_status",
                                args: { order_name: frm.doc.name, new_status: "Delivered" },
                                callback(r) {
                                    if (r.message && r.message.success) {
                                        frm.reload_doc();
                                        frappe.show_alert({ message: "Marked as Delivered!", indicator: "green" });
                                    }
                                },
                            });
                        }
                    );
                }, __("Actions"));
            }
        }
    },

    // Recalculate grand total when delivery charges, tax, or discount change
    delivery_charges(frm) { _calculate_grand_total(frm); },
    tax(frm) { _calculate_grand_total(frm); },
    discount(frm) { _calculate_grand_total(frm); },
});

frappe.ui.form.on("Delivery Order Item", {
    quantity(frm, cdt, cdn) { _calculate_row_total(frm, cdt, cdn); },
    unit_price(frm, cdt, cdn) { _calculate_row_total(frm, cdt, cdn); },
    order_items_remove(frm) { _calculate_subtotal(frm); },
});

function _calculate_row_total(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    frappe.model.set_value(cdt, cdn, "total", (row.quantity || 0) * (row.unit_price || 0));
    _calculate_subtotal(frm);
}

function _calculate_subtotal(frm) {
    let subtotal = 0;
    (frm.doc.order_items || []).forEach(item => { subtotal += item.total || 0; });
    frm.set_value("subtotal", subtotal);
    _calculate_grand_total(frm);
}

function _calculate_grand_total(frm) {
    const grand = (frm.doc.subtotal || 0)
        + (frm.doc.delivery_charges || 0)
        + (frm.doc.tax || 0)
        - (frm.doc.discount || 0);
    frm.set_value("grand_total", grand);
}

function _update_status_badge(frm) {
    const status = frm.doc.current_status;
    const color_map = {
        "Pending": "yellow", "Assigned": "blue", "Picked Up": "blue",
        "In Transit": "blue", "Nearby": "purple", "At Location": "orange",
        "Delivered": "green", "Failed": "red", "Returned": "red", "Cancelled": "grey",
    };
    const color = color_map[status] || "grey";
    frm.dashboard.add_indicator(status, color);
}

function _show_status_update_dialog(frm) {
    const valid_next = {
        "Pending": ["Assigned", "Cancelled"],
        "Assigned": ["Picked Up", "Cancelled"],
        "Picked Up": ["In Transit", "Failed"],
        "In Transit": ["Nearby", "Delivered", "Failed"],
        "Nearby": ["At Location", "Delivered", "Failed"],
        "At Location": ["Delivered", "Failed"],
        "Failed": ["Returned", "Assigned"],
    };
    const options = (valid_next[frm.doc.current_status] || []).join("\n");
    if (!options) {
        frappe.msgprint("No valid status transitions available.");
        return;
    }
    const dialog = new frappe.ui.Dialog({
        title: "Update Delivery Status",
        fields: [
            { fieldtype: "Select", fieldname: "new_status", label: "New Status", options, reqd: 1 },
            { fieldtype: "Small Text", fieldname: "notes", label: "Notes (optional)" },
        ],
        primary_action_label: "Update",
        primary_action(values) {
            dialog.hide();
            frappe.call({
                method: "alvoraa_portal.controllers.delivery_order.update_delivery_status",
                args: { order_name: frm.doc.name, new_status: values.new_status, notes: values.notes },
                callback(r) {
                    if (r.message && r.message.success) {
                        frm.reload_doc();
                        frappe.show_alert({ message: `Status updated to ${values.new_status}`, indicator: "green" });
                    }
                },
            });
        },
    });
    dialog.show();
}

function _show_assign_partner_dialog(frm) {
    const dialog = new frappe.ui.Dialog({
        title: "Assign Delivery Partner",
        fields: [
            {
                fieldtype: "Link", fieldname: "partner", label: "Delivery Partner",
                options: "Delivery Partner", reqd: 1,
                get_query() {
                    return { filters: { is_active: 1, status: "Active" } };
                },
            },
        ],
        primary_action_label: "Assign",
        primary_action(values) {
            dialog.hide();
            frappe.call({
                method: "alvoraa_portal.controllers.delivery_order.assign_partner_to_order",
                args: { order_name: frm.doc.name, partner_name: values.partner },
                callback(r) {
                    if (r.message && r.message.success) {
                        frm.reload_doc();
                        frappe.show_alert({ message: `Assigned to ${values.partner}`, indicator: "green" });
                    }
                },
            });
        },
    });
    dialog.show();
}
