import frappe


def validate_goal(doc, method=None):
    if doc.is_review_draft:
        return
    _check_approval_flow(doc)


def before_submit_goal(doc, method=None):
    if doc.approval_status not in ("Approved",) and not frappe.db.exists(
        "Has Role", {"parent": frappe.session.user, "role": ["in", ["HR Manager", "System Manager"]]}
    ):
        frappe.throw("Goal must be approved before it can be submitted.")


def _check_approval_flow(doc):
    if doc.status == "Pending Approval" and not doc.approval_status:
        doc.approval_status = "Pending"
