frappe.ui.form.on('PMS Calibration Session', {
    refresh(frm) {
        if (frm.doc.status !== 'Locked' && !frm.is_new()) {
            frm.add_custom_button('Open Calibration Portal', () => {
                window.open('/pms-calibration', '_blank');
            });

            frm.add_custom_button('Lock & Apply Ratings', () => {
                frappe.confirm(
                    'Lock this session and apply all calibrated ratings? This cannot be undone.',
                    () => {
                        frappe.call({
                            method: 'hrms.pms.calibration.lock_session',
                            args: { session_name: frm.doc.name },
                            callback() {
                                frappe.show_alert({ message: 'Session locked and ratings applied', indicator: 'green' });
                                frm.reload_doc();
                            }
                        });
                    }
                );
            }, 'Actions');
        }
    }
});
