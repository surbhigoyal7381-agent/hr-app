frappe.ui.form.on('PMS Review Record', {
    refresh(frm) {
        // Potential rating: hide from employee view unless explicitly unlocked
        const isEmployee = frappe.session.user_roles.includes('Employee') &&
            !frappe.session.user_roles.some(r => ['HR Manager','HR User','System Manager'].includes(r));
        if (isEmployee && !frm.doc.overall_rating_visible_to_employee) {
            frm.set_df_property('potential_rating', 'hidden', 1);
            frm.set_df_property('potential_rating_scale', 'hidden', 1);
        }

        // HR-only: unlock rating visibility button
        if (frappe.user.has_role('HR Manager') || frappe.user.has_role('System Manager')) {
            if (!frm.doc.overall_rating_visible_to_employee) {
                frm.add_custom_button('Unlock Rating Visibility', () => {
                    frappe.call({
                        method: 'hrms.pms.api.unlock_rating_visibility',
                        args: { review_record_name: frm.doc.name },
                        callback() {
                            frappe.show_alert({ message: 'Rating now visible to employee', indicator: 'green' });
                            frm.reload_doc();
                        }
                    });
                }, 'HR Actions');
            }
        }
    }
});
