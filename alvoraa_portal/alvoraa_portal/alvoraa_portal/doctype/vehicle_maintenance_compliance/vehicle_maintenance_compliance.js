frappe.ui.form.on("Vehicle Maintenance Compliance", {
    refresh(frm) {
        _show_alert_indicator(frm);

        if (!frm.is_new()) {
            frm.add_custom_button(__("Mark Renewed"), function () {
                frappe.prompt(
                    [
                        { fieldtype: "Date", fieldname: "renewal_date", label: "Renewal Date", reqd: 1, default: frappe.datetime.get_today() },
                        { fieldtype: "Date", fieldname: "new_expiry", label: "New Expiry Date", reqd: 1 },
                        { fieldtype: "Currency", fieldname: "renewal_cost", label: "Renewal Cost" },
                    ],
                    function (values) {
                        frm.set_value("renewal_date", values.renewal_date);
                        frm.set_value("compliance_expiry_date", values.new_expiry);
                        if (values.renewal_cost) frm.set_value("renewal_cost", values.renewal_cost);
                        frm.set_value("renewal_required", 0);
                        frm.set_value("alert_notification_sent", 0);

                        // Add to compliance history
                        frm.add_child("compliance_history", {
                            check_date: values.renewal_date,
                            status: "Pass",
                            details: `Renewed. New expiry: ${values.new_expiry}`,
                            action_completed: 1,
                        });
                        frm.refresh_field("compliance_history");
                        frm.save().then(() => {
                            frappe.show_alert({ message: "Compliance renewed successfully!", indicator: "green" });
                        });
                    },
                    "Mark Compliance as Renewed",
                    "Save"
                );
            }, __("Actions"));
        }
    },

    compliance_expiry_date(frm) {
        if (frm.doc.compliance_expiry_date) {
            const days = frappe.datetime.get_diff(frm.doc.compliance_expiry_date, frappe.datetime.get_today());
            frm.set_value("days_until_expiry", days);
            frm.set_value("is_expired", days < 0 ? 1 : 0);

            let status = "Clear";
            if (days < 0) status = "Overdue";
            else if (days <= 7) status = "Critical";
            else if (days <= 30) status = "Warning";
            frm.set_value("alert_status", status);
            _show_alert_indicator(frm);
        }
    },
});

function _show_alert_indicator(frm) {
    const status = frm.doc.alert_status;
    const color_map = { "Clear": "green", "Warning": "yellow", "Critical": "orange", "Overdue": "red" };
    if (status) {
        frm.dashboard.add_indicator(`Compliance: ${status}`, color_map[status] || "grey");
    }
    if (frm.doc.is_expired) {
        frm.dashboard.add_indicator("EXPIRED — Vehicle should not operate!", "red");
    }
}
