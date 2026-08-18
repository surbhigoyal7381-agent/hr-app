frappe.ui.form.on("Delivery Hub", {
    refresh(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__("View Live Summary"), function () {
                frappe.call({
                    method: "grace_vendor_portal.controllers.delivery_order.get_hub_live_summary",
                    args: { hub_name: frm.doc.name },
                    callback(r) {
                        if (r.message) {
                            const d = r.message;
                            const rows = Object.entries(d.by_status || {})
                                .map(([status, count]) => `<tr><td>${status}</td><td>${count}</td></tr>`)
                                .join("");
                            frappe.msgprint({
                                title: `Live Summary — ${d.hub}`,
                                message: `
                                    <p><b>Active Partners:</b> ${d.active_partners} &nbsp;
                                    <b>Total Orders Today:</b> ${d.total_orders_today}</p>
                                    <table class="table table-bordered">
                                        <thead><tr><th>Status</th><th>Count</th></tr></thead>
                                        <tbody>${rows}</tbody>
                                    </table>
                                `,
                                wide: true,
                            });
                        }
                    },
                });
            }, __("Actions"));

            frm.add_custom_button(__("Compliance Dashboard"), function () {
                frappe.call({
                    method: "grace_vendor_portal.controllers.vehicle_compliance.get_compliance_dashboard",
                    args: { hub_name: frm.doc.name },
                    callback(r) {
                        if (r.message) {
                            const { summary, alerts } = r.message;
                            const rows = alerts.map(a =>
                                `<tr>
                                    <td>${a.vehicle_registration}</td>
                                    <td>${a.partner}</td>
                                    <td>${a.compliance_type}</td>
                                    <td>${a.compliance_expiry_date}</td>
                                    <td><span class="badge badge-${a.alert_status === 'Overdue' ? 'danger' : 'warning'}">${a.alert_status}</span></td>
                                </tr>`
                            ).join("");
                            frappe.msgprint({
                                title: `Compliance Dashboard — ${frm.doc.hub_name}`,
                                message: `
                                    <p>Clear: ${summary.Clear} &nbsp; Warning: ${summary.Warning} &nbsp;
                                    Critical: ${summary.Critical} &nbsp; Overdue: ${summary.Overdue}</p>
                                    ${rows ? `<table class="table table-bordered">
                                        <thead><tr><th>Vehicle</th><th>Partner</th><th>Type</th><th>Expiry</th><th>Status</th></tr></thead>
                                        <tbody>${rows}</tbody>
                                    </table>` : "<p>All compliance records are clear.</p>"}
                                `,
                                wide: true,
                            });
                        }
                    },
                });
            }, __("Actions"));
        }
    },

    average_deliveries_per_day(frm) {
        _calculate_utilization(frm);
    },
    max_deliveries_per_day(frm) {
        _calculate_utilization(frm);
    },
});

function _calculate_utilization(frm) {
    const max = frm.doc.max_deliveries_per_day || 0;
    const avg = frm.doc.average_deliveries_per_day || 0;
    if (max > 0) {
        frm.set_value("utilization_percentage", Math.min(100, (avg / max) * 100));
    }
}
