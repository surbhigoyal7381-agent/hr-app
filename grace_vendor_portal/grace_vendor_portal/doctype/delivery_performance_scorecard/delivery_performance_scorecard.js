frappe.ui.form.on("Delivery Performance Scorecard", {
    refresh(frm) {
        _show_performance_indicator(frm);
        _show_score_breakdown(frm);

        if (!frm.is_new()) {
            frm.add_custom_button(__("Regenerate from Live Data"), function () {
                frappe.confirm(
                    "This will overwrite the current scorecard metrics with live aggregated data. Continue?",
                    function () {
                        frappe.call({
                            method: "grace_vendor_portal.controllers.scorecard.generate_scorecard_for_partner",
                            args: {
                                partner: frm.doc.delivery_partner,
                                month: frm.doc.month,
                                year: frm.doc.year,
                            },
                            callback(r) {
                                if (r.message) {
                                    frm.reload_doc();
                                    frappe.show_alert({ message: "Scorecard regenerated!", indicator: "green" });
                                }
                            },
                        });
                    }
                );
            }, __("Actions"));

            frm.add_custom_button(__("Hub Performance Report"), function () {
                frappe.prompt(
                    [{ fieldtype: "Link", fieldname: "hub", label: "Delivery Hub", options: "Delivery Hub", reqd: 1 }],
                    function (values) {
                        frappe.call({
                            method: "grace_vendor_portal.controllers.scorecard.get_hub_performance_report",
                            args: { hub_name: values.hub, month: frm.doc.month, year: frm.doc.year },
                            callback(r) {
                                if (!r.message) return;
                                const d = r.message;
                                const top = (d.top_performers || []).map((s, i) =>
                                    `<tr>
                                        <td>${i + 1}</td>
                                        <td>${s.delivery_partner}</td>
                                        <td>${s.total_deliveries}</td>
                                        <td>${(s.on_time_percentage || 0).toFixed(1)}%</td>
                                        <td>${(s.avg_customer_rating || 0).toFixed(2)}/5</td>
                                        <td><b>${(s.overall_delivery_score || 0).toFixed(1)}</b></td>
                                        <td>${s.performance_level}</td>
                                    </tr>`
                                ).join("");
                                frappe.msgprint({
                                    title: `Hub Report — ${d.hub} | ${d.month}/${d.year}`,
                                    message: `
                                        <p><b>Partners:</b> ${d.partner_count} &nbsp;
                                        <b>Total Deliveries:</b> ${d.summary.total_deliveries} &nbsp;
                                        <b>Avg On-Time:</b> ${d.summary.avg_on_time_pct}% &nbsp;
                                        <b>Avg Rating:</b> ${d.summary.avg_customer_rating}/5</p>
                                        <p><b>Total Commission:</b> ₹${(d.summary.total_commission || 0).toLocaleString()} &nbsp;
                                        <b>Bonuses:</b> ₹${(d.summary.total_bonuses || 0).toLocaleString()}</p>
                                        <table class="table table-bordered">
                                            <thead><tr><th>#</th><th>Partner</th><th>Deliveries</th>
                                            <th>On-Time</th><th>Rating</th><th>Score</th><th>Level</th></tr></thead>
                                            <tbody>${top}</tbody>
                                        </table>
                                    `,
                                    wide: true,
                                });
                            },
                        });
                    },
                    "View Hub Performance Report",
                    "View"
                );
            }, __("Actions"));
        }
    },

    on_time_deliveries(frm) { _recalculate_percentages(frm); },
    total_deliveries(frm) { _recalculate_percentages(frm); },
    avg_customer_rating(frm) { _show_score_breakdown(frm); },
    safety_incidents(frm) { _show_score_breakdown(frm); },
    attendance_rate(frm) { _show_score_breakdown(frm); },

    commission_earned(frm) { _recalculate_net(frm); },
    bonuses_earned(frm) { _recalculate_net(frm); },
    deductions(frm) { _recalculate_net(frm); },
});

function _recalculate_percentages(frm) {
    const total = frm.doc.total_deliveries || 0;
    const ontime = frm.doc.on_time_deliveries || 0;
    if (total > 0) {
        frm.set_value("on_time_percentage", Math.round((ontime / total) * 1000) / 10);
        frm.set_value("late_deliveries", total - ontime);
    }
}

function _recalculate_net(frm) {
    const net = (frm.doc.commission_earned || 0) + (frm.doc.bonuses_earned || 0) - (frm.doc.deductions || 0);
    frm.set_value("net_amount", net);
}

function _show_performance_indicator(frm) {
    const level = frm.doc.performance_level;
    const color_map = {
        "Excellent": "green", "Good": "blue",
        "Satisfactory": "yellow", "Poor": "orange", "Critical": "red",
    };
    if (level) {
        frm.dashboard.add_indicator(
            `Performance: ${level} (Score: ${frm.doc.overall_delivery_score || 0})`,
            color_map[level] || "grey"
        );
    }
    if (frm.doc.promotion_eligible) {
        frm.dashboard.add_indicator("Promotion Eligible", "green");
    }
    if (frm.doc.warning_issued) {
        frm.dashboard.add_indicator(`Warning: ${frm.doc.warning_type}`, "red");
    }
}

function _show_score_breakdown(frm) {
    if (!frm.doc.overall_delivery_score) return;
    // Display score breakdown in a message box below the section header
    const score = frm.doc.overall_delivery_score;
    const band = score >= 90 ? "Excellent (90-100)"
        : score >= 75 ? "Good (75-89)"
        : score >= 60 ? "Satisfactory (60-74)"
        : score >= 40 ? "Poor (40-59)"
        : "Critical (Below 40)";
    frm.set_intro(`Score: <b>${score}/100</b> — ${band}.
        On-Time: ${frm.doc.on_time_score || 0} |
        Quality: ${frm.doc.quality_score || 0} |
        Safety: ${frm.doc.safety_score || 0} |
        Professionalism: ${frm.doc.professionalism_score || 0}`,
        score >= 75 ? "green" : score >= 60 ? "yellow" : "red");
}
