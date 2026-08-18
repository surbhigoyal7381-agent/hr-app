frappe.ui.form.on('Vendor Order', {
    refresh: function(frm) {
        var inactiveStatuses = ['Delivered', 'Cancelled'];
        if (!inactiveStatuses.includes(frm.doc.order_status)) {
            frm.add_custom_button(__('Change Status'), function() {
                let validNext = {
                    'Draft':              ['Under Review', 'Cancelled'],
                    'Under Review':       ['Approved', 'Cancelled'],
                    'Approved':           ['Packing', 'Cancelled'],
                    'Packing':            ['Ready for Dispatch', 'Cancelled'],
                    'Ready for Dispatch': ['Dispatched'],
                    'Dispatched':         ['In Transit'],
                    'In Transit':         ['Delivered'],
                }[frm.doc.order_status] || [];

                if (!validNext.length) {
                    frappe.msgprint(__('No valid status transitions available.'));
                    return;
                }

                frappe.prompt([
                    {
                        label: __('New Status'),
                        fieldname: 'new_status',
                        fieldtype: 'Select',
                        options: validNext.join('\n'),
                        reqd: 1
                    },
                    {
                        label: __('Reason'),
                        fieldname: 'reason',
                        fieldtype: 'Data'
                    }
                ], function(values) {
                    frappe.call({
                        method: 'alvoraa_portal.controllers.vendor_order.change_order_status',
                        args: {
                            order_name: frm.doc.name,
                            new_status: values.new_status,
                            reason: values.reason
                        },
                        callback: function(r) {
                            if (!r.exc) {
                                frm.reload_doc();
                                frappe.show_alert({message: __('Status updated'), indicator: 'green'});
                            }
                        }
                    });
                }, __('Change Order Status'), __('Update'));
            }, __('Actions'));
        }

        if (frm.doc.order_status === 'Approved') {
            frm.add_custom_button(__('Assign Delivery'), function() {
                frappe.prompt([
                    {label: __('Driver'), fieldname: 'driver_id', fieldtype: 'Link', options: 'Employee', reqd: 1},
                    {label: __('Vehicle Reg'), fieldname: 'vehicle_reg', fieldtype: 'Data', reqd: 1},
                    {label: __('Estimated Arrival'), fieldname: 'eta_time', fieldtype: 'Datetime'}
                ], function(values) {
                    frappe.call({
                        method: 'alvoraa_portal.controllers.vendor_order.assign_delivery',
                        args: {
                            order_name: frm.doc.name,
                            driver_id: values.driver_id,
                            vehicle_reg: values.vehicle_reg,
                            eta_time: values.eta_time
                        },
                        callback: function(r) {
                            if (!r.exc) {
                                frm.reload_doc();
                                frappe.show_alert({message: __('Delivery assigned'), indicator: 'green'});
                            }
                        }
                    });
                }, __('Assign Delivery'), __('Assign'));
            }, __('Actions'));
        }
    },

    items_add: function(frm) {
        frm.trigger('calculate_totals');
    },

    items_remove: function(frm) {
        frm.trigger('calculate_totals');
    },

    calculate_totals: function(frm) {
        let total = 0;
        (frm.doc.items || []).forEach(function(item) {
            let line_total = (item.quantity || 0) * (item.unit_price || 0);
            frappe.model.set_value(item.doctype, item.name, 'line_total', line_total);
            total += line_total;
        });
        frm.set_value('total_amount', total);
    }
});

frappe.ui.form.on('Vendor Order Item', {
    sku: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.sku) return;
        frappe.db.get_value('Item', row.sku, ['item_name', 'standard_rate'], function(r) {
            if (!r) return;
            if (r.item_name) frappe.model.set_value(cdt, cdn, 'item_name', r.item_name);
            if (r.standard_rate) {
                frappe.model.set_value(cdt, cdn, 'unit_price', r.standard_rate);
            }
        });
    },
    quantity: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        let line_total = (row.quantity || 0) * (row.unit_price || 0);
        frappe.model.set_value(cdt, cdn, 'line_total', line_total);
        frm.trigger('calculate_totals');
    },
    unit_price: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        let line_total = (row.quantity || 0) * (row.unit_price || 0);
        frappe.model.set_value(cdt, cdn, 'line_total', line_total);
        frm.trigger('calculate_totals');
    }
});
