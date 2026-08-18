frappe.ui.form.on("Delivery Partner", {
    refresh(frm) {
        _toggle_financial_fields(frm);
        _highlight_compliance_status(frm);

        if (!frm.is_new()) {
            frm.add_custom_button(__("Performance Summary"), function () {
                frappe.call({
                    method: "alvoraa_portal.controllers.delivery_partner.get_partner_performance_summary",
                    args: { partner_name: frm.doc.name },
                    callback(r) {
                        if (!r.message) return;
                        const d = r.message;
                        const sc = d.latest_scorecard;
                        frappe.msgprint({
                            title: `Performance Summary — ${d.partner_name}`,
                            message: `
                                <p><b>Total Deliveries:</b> ${d.total_deliveries || 0} &nbsp;
                                <b>On-Time %:</b> ${(d.on_time_percentage || 0).toFixed(1)}% &nbsp;
                                <b>Customer Rating:</b> ${(d.customer_rating || 0).toFixed(2)}/5</p>
                                ${sc ? `<p><b>Latest Scorecard (${sc.month}/${sc.year}):</b>
                                Score: <b>${sc.overall_delivery_score}</b> |
                                Level: <b>${sc.performance_level}</b> |
                                Net Payable: ₹${(sc.net_amount || 0).toLocaleString()}</p>` : "<p>No scorecard yet.</p>"}
                                ${d.compliance_alert ? `<p style="color:red">⚠ Compliance Alert:
                                ${d.compliance_alert.compliance_type} — ${d.compliance_alert.alert_status}</p>` : ""}
                            `,
                            wide: true,
                        });
                    },
                });
            }, __("Actions"));

            frm.add_custom_button(__("Today's Orders"), function () {
                frappe.call({
                    method: "alvoraa_portal.controllers.delivery_partner.get_today_orders_for_partner",
                    args: { partner_name: frm.doc.name },
                    callback(r) {
                        if (!r.message) return;
                        const orders = r.message;
                        if (!orders.length) {
                            frappe.msgprint("No pending orders today.");
                            return;
                        }
                        const rows = orders.map(o =>
                            `<tr>
                                <td><a href="/app/delivery-order/${o.name}">${o.name}</a></td>
                                <td>${o.customer_name}</td>
                                <td>${o.delivery_time_slot}</td>
                                <td>${o.current_status}</td>
                                <td>₹${(o.grand_total || 0).toLocaleString()}</td>
                            </tr>`
                        ).join("");
                        frappe.msgprint({
                            title: `Today's Orders — ${frm.doc.partner_name}`,
                            message: `<table class="table table-bordered">
                                <thead><tr><th>Order</th><th>Customer</th><th>Slot</th><th>Status</th><th>Value</th></tr></thead>
                                <tbody>${rows}</tbody>
                            </table>`,
                            wide: true,
                        });
                    },
                });
            }, __("Actions"));

            frm.add_custom_button(__("Generate Scorecard"), function () {
                const dialog = new frappe.ui.Dialog({
                    title: "Generate Monthly Scorecard",
                    fields: [
                        { fieldtype: "Int", fieldname: "month", label: "Month (1-12)", reqd: 1, default: new Date().getMonth() || 12 },
                        { fieldtype: "Int", fieldname: "year", label: "Year", reqd: 1, default: new Date().getFullYear() },
                    ],
                    primary_action_label: "Generate",
                    primary_action(values) {
                        dialog.hide();
                        frappe.call({
                            method: "alvoraa_portal.controllers.scorecard.generate_scorecard_for_partner",
                            args: { partner: frm.doc.name, month: values.month, year: values.year },
                            callback(r) {
                                if (r.message) {
                                    frappe.show_alert({ message: `Scorecard created: ${r.message}`, indicator: "green" });
                                    frappe.set_route("Form", "Delivery Performance Scorecard", r.message);
                                }
                            },
                        });
                    },
                });
                dialog.show();
            }, __("Actions"));
        }
    },

    partner_contract_type(frm) {
        _toggle_financial_fields(frm);
    },

    status(frm) {
        if (frm.doc.status === "Terminated") {
            frm.set_value("is_active", 0);
        } else if (frm.doc.status === "Active") {
            frm.set_value("is_active", 1);
        }
    },

    is_active(frm) {
        if (!frm.doc.is_active) {
            frm.toggle_reqd("deactivation_reason", true);
        } else {
            frm.toggle_reqd("deactivation_reason", false);
        }
    },
});

function _toggle_financial_fields(frm) {
    const type = frm.doc.partner_contract_type;
    frm.toggle_display("daily_rate", type === "Fixed");
    frm.toggle_display("per_order_rate", type === "Per-Order");
}

function _highlight_compliance_status(frm) {
    const today = frappe.datetime.get_today();

    function _check_field(dateVal, label) {
        if (!dateVal) return;
        const days = frappe.datetime.get_diff(dateVal, today);
        if (days < 0) {
            frm.dashboard.add_indicator(`${label}: EXPIRED`, "red");
        } else if (days <= 7) {
            frm.dashboard.add_indicator(`${label}: expires in ${days} days`, "orange");
        } else if (days <= 30) {
            frm.dashboard.add_indicator(`${label}: expires in ${days} days`, "yellow");
        }
    }

    _check_field(frm.doc.license_expiry, "DL");
    _check_field(frm.doc.vehicle_fitness_cert_expiry, "Fitness Cert");
    _check_field(frm.doc.insurance_expiry, "Insurance");
}
