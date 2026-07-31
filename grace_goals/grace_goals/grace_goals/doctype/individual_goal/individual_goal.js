frappe.ui.form.on('Individual Goal', {
    onload: function(frm) {
        if (frm.doc.actual_progress > 0) {
            frm.set_df_property('target_value', 'read_only', 1);
            frm.set_df_property('unit', 'read_only', 1);
        }
    },

    refresh: function(frm) {
        _render_progress_bar(frm);
        _render_trajectory_badge(frm);

        if (frm.doc.docstatus === 1 && frm.doc.status === 'Active') {
            frm.add_custom_button(__('Submit Evidence'), function() {
                _show_evidence_dialog(frm);
            }, __('Actions'));

            frm.add_custom_button(__('Recalculate Progress'), function() {
                frappe.call({
                    method: 'grace_goals.api.goal_api.recalculate_progress',
                    args: { goal_id: frm.doc.name },
                    callback: function(r) {
                        if (r.message) {
                            frappe.show_alert({message: __('Progress updated: {0}%', [r.message.progress_pct.toFixed(1)]), indicator: 'green'});
                            frm.reload_doc();
                        }
                    }
                });
            }, __('Actions'));
        }

        if (frm.doc.docstatus === 1) {
            _render_evidence_gallery(frm);
        }
    },
});

function _render_progress_bar(frm) {
    var pct = frm.doc.progress_pct || 0;
    var color = pct >= 75 ? '#28a745' : (pct >= 40 ? '#ffc107' : '#dc3545');
    var html = `
        <div style="margin: 10px 0;">
            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                <span><b>Progress</b></span>
                <span>${frm.doc.actual_progress || 0} / ${frm.doc.target_value || 0} ${frm.doc.unit || ''} &nbsp; <b>${pct.toFixed(1)}%</b></span>
            </div>
            <div style="background:#e9ecef; border-radius:4px; height:18px; overflow:hidden;">
                <div style="background:${color}; width:${Math.min(pct,100)}%; height:100%; border-radius:4px; transition:width 0.4s;"></div>
            </div>
        </div>`;
    frm.set_intro(html, false);
}

function _render_trajectory_badge(frm) {
    var map = {'On Track': 'green', 'At Risk': 'yellow', 'Off Track': 'red', 'Not Started': 'grey'};
    var color = map[frm.doc.trajectory] || 'grey';
    if (frm.doc.trajectory) {
        frm.page.set_indicator(frm.doc.trajectory, color);
    }
}

function _render_evidence_gallery(frm) {
    var ev = (frm.doc.evidence_items || []).filter(e => e.validation_status === 'Approved');
    if (!ev.length) return;
    var rows = ev.map(function(e) {
        return `<tr>
            <td>${e.evidence_type}</td>
            <td>${frappe.datetime.str_to_user(e.upload_date) || ''}</td>
            <td>${e.extracted_order_count || '-'}</td>
            <td>${e.extracted_amount ? frappe.format(e.extracted_amount, {fieldtype:'Currency'}) : '-'}</td>
            <td>${e.extracted_customer || '-'}</td>
            <td><span class="indicator-pill green">Approved</span></td>
        </tr>`;
    }).join('');
    var html = `<table class="table table-bordered table-sm" style="margin-top:10px;">
        <thead><tr><th>Type</th><th>Date</th><th>Orders</th><th>Amount</th><th>Customer</th><th>Status</th></tr></thead>
        <tbody>${rows}</tbody>
    </table>`;
    frm.fields_dict['goal_name'].$wrapper.after(
        $('<div class="evidence-gallery" style="margin:10px 0;"><b>Approved Evidence</b>' + html + '</div>')
    );
}

function _show_evidence_dialog(frm) {
    var d = new frappe.ui.Dialog({
        title: __('Submit Evidence'),
        fields: [
            {fieldname: 'evidence_type', fieldtype: 'Select', label: __('Evidence Type'),
             options: 'Invoice\nSales Order\nManual Entry', reqd: 1},
            {fieldname: 'evidence_file', fieldtype: 'Attach', label: __('Upload File (optional)')},
            {fieldname: 'extracted_order_count', fieldtype: 'Int', label: __('Number of Orders')},
            {fieldname: 'extracted_amount', fieldtype: 'Currency', label: __('Amount (₹)')},
            {fieldname: 'extracted_date', fieldtype: 'Date', label: __('Invoice / Order Date')},
            {fieldname: 'extracted_customer', fieldtype: 'Data', label: __('Customer Name')},
        ],
        primary_action_label: __('Submit'),
        primary_action: function(values) {
            frappe.call({
                method: 'grace_goals.api.goal_api.submit_goal_evidence',
                args: {
                    goal_id: frm.doc.name,
                    evidence_type: values.evidence_type,
                    extracted_order_count: values.extracted_order_count,
                    extracted_amount: values.extracted_amount,
                    extracted_date: values.extracted_date,
                    extracted_customer: values.extracted_customer,
                    evidence_file: values.evidence_file,
                },
                freeze: true,
                freeze_message: __('Validating evidence...'),
                callback: function(r) {
                    if (r.message) {
                        var msg = r.message.status === 'Approved'
                            ? __('Evidence approved! New progress: {0}%', [r.message.progress_pct.toFixed(1)])
                            : r.message.status === 'Pending'
                                ? __('Evidence submitted and pending HR review.')
                                : __('Evidence rejected.');
                        frappe.show_alert({message: msg, indicator: r.message.status === 'Approved' ? 'green' : 'yellow'});
                        d.hide();
                        frm.reload_doc();
                    }
                }
            });
        }
    });
    d.show();
}
