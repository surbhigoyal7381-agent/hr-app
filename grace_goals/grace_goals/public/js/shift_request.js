frappe.ui.form.on("Shift Request", {
    refresh: function(frm) {
        restrict_approver(frm);
    },
    employee: function(frm) {
        restrict_approver(frm);
    }
});

function restrict_approver(frm) {
    if (!frm.doc.employee) return;

    frappe.db.get_value(
        "Employee",
        frm.doc.employee,
        "shift_request_approver",
        function(d) {
            if (d && d.shift_request_approver) {
                setApprover(frm, d.shift_request_approver);
            } else {
                // No designated approver on the employee — fall back to HR Manager.
                frappe.call({
                    method: "grace_vendor_portal.hr_api.get_hr_approver",
                    callback: function(r) {
                        if (r.message) {
                            setApprover(frm, r.message);
                        }
                    },
                });
            }
        }
    );
}

function setApprover(frm, approver) {
    frm.set_query("approver", function() {
        return { filters: { name: approver } };
    });
    if (!frm.doc.approver) {
        frm.set_value("approver", approver);
    }
}
