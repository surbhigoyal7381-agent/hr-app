frappe.ui.form.on('Vendor', {
    refresh: function(frm) {
        frm.add_custom_button(__('View Orders'), function() {
            frappe.set_route('List', 'Vendor Order', {vendor: frm.doc.name});
        });
    }
});
