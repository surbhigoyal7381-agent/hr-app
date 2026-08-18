frappe.ui.form.on('Vendor User', {
    refresh: function(frm) {
        if (frm.doc.account_locked) {
            frm.add_custom_button(__('Unlock Account'), function() {
                frappe.db.set_value('Vendor User', frm.doc.name, {
                    account_locked: 0,
                    failed_attempts: 0
                }).then(() => frm.reload_doc());
            }, __('Actions'));
        }
    }
});
