frappe.ui.form.on('Delivery Assignment', {
    refresh: function(frm) {
        if (frm.doc.status === 'Assigned' || frm.doc.status === 'In Transit') {
            frm.add_custom_button(__('Verify OTP'), function() {
                frappe.prompt([
                    {label: __('Enter OTP'), fieldname: 'otp', fieldtype: 'Data', reqd: 1}
                ], function(values) {
                    frappe.call({
                        method: 'alvoraa_portal.controllers.delivery_assignment.verify_delivery_otp',
                        args: {
                            assignment_name: frm.doc.name,
                            entered_otp: values.otp
                        },
                        callback: function(r) {
                            if (!r.exc) {
                                frm.reload_doc();
                                frappe.show_alert({message: __('OTP verified — delivery marked complete'), indicator: 'green'});
                            }
                        }
                    });
                }, __('Verify Delivery OTP'), __('Verify'));
            }, __('Actions'));

            frm.add_custom_button(__('Update GPS Location'), function() {
                frappe.prompt([
                    {label: __('Latitude'), fieldname: 'lat', fieldtype: 'Float', reqd: 1},
                    {label: __('Longitude'), fieldname: 'lng', fieldtype: 'Float', reqd: 1},
                    {label: __('ETA (minutes)'), fieldname: 'eta_minutes', fieldtype: 'Int'}
                ], function(values) {
                    frappe.call({
                        method: 'alvoraa_portal.controllers.delivery_assignment.update_gps_location',
                        args: {
                            assignment_name: frm.doc.name,
                            lat: values.lat,
                            lng: values.lng,
                            eta_minutes: values.eta_minutes
                        },
                        callback: function(r) {
                            if (!r.exc) {
                                frm.reload_doc();
                                frappe.show_alert({message: __('GPS location updated'), indicator: 'green'});
                            }
                        }
                    });
                }, __('Update GPS'), __('Update'));
            }, __('Actions'));
        }
    }
});
