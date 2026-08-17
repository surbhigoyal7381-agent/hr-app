import frappe
from frappe import _
from frappe.utils import now_datetime
from grace_goals.validators.invoice_validator import validate_invoice
from grace_goals.validators.sales_order_validator import validate_sales_order
from grace_goals.validators.duplicate_detector import check_duplicate
from grace_goals.controllers.goal import recalculate_progress, _append_audit_log


def validate_evidence(doc, method=None):
    """Registered as before_insert on Goal Evidence — dead on portal path (Frappe v16
    inserts child rows via db_insert, bypassing hooks). Called directly by approve_evidence."""
    goal = frappe.get_doc("Individual Goal", doc.parent)
    if not doc.upload_date:
        doc.upload_date = now_datetime()
    if not doc.uploaded_by:
        doc.uploaded_by = frappe.session.user

    if doc.evidence_type == "Invoice":
        result = validate_invoice(doc, goal)
        doc.validation_notes = result["notes"]
        if result["errors"]:
            doc.validation_status = "Pending"
            doc.validation_notes += "\n→ Pending: rule(s) failed — sent for manager review"
        else:
            doc.validation_status = "Approved"
            doc.approved_by = "System"
            doc.approved_on = now_datetime()
            doc.validation_notes += "\n→ Auto-approved by System"

    elif doc.evidence_type == "Sales Order":
        result = validate_sales_order(doc, goal)
        doc.validation_notes = result["notes"]
        if result["errors"]:
            doc.validation_status = "Pending"
            doc.validation_notes += "\n→ Pending: rule(s) failed — sent for manager review"
        else:
            doc.validation_status = "Approved"
            doc.approved_by = "System"
            doc.approved_on = now_datetime()
            doc.validation_notes += "\n→ Auto-approved by System"

    else:
        doc.validation_status = "Pending"
        doc.validation_notes = "[Manual Entry] No automated validation — pending manager review"

    dup_result = check_duplicate(doc, goal.name)
    if dup_result:
        doc.validation_status = "Pending"
        doc.validation_notes += f"\n⚠ Duplicate detected (similarity: {dup_result['score']}%) — overriding to Pending for manager review"
        frappe.msgprint(f"Possible duplicate evidence detected (similarity: {dup_result['score']}%). Sent for manager review.", alert=True)


def after_insert_evidence(doc, method=None):
    """Registered as after_insert on Goal Evidence — dead on portal path (Frappe v16
    inserts child rows via db_insert, bypassing hooks). Called directly by approve_evidence."""
    _append_audit_log(doc.parent, "Evidence Added", None, doc.evidence_type, frappe.session.user, f"Evidence type: {doc.evidence_type}, status: {doc.validation_status}")
    if doc.validation_status == "Approved":
        recalculate_progress(doc.parent)


@frappe.whitelist()
def approve_evidence(goal_name, evidence_idx):
    goal = frappe.get_doc("Individual Goal", goal_name)
    me_employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
    goal_employee = frappe.db.get_value("Employee", goal.employee, "reports_to")
    is_manager = me_employee and me_employee == goal_employee
    is_hr = frappe.has_role("HR Manager") or frappe.has_role("System Manager")
    if not is_manager and not is_hr:
        frappe.throw(_("Only the employee's manager or HR can approve evidence"), frappe.PermissionError)
    evidence = goal.evidence_items[int(evidence_idx)]
    evidence.validation_status = "Approved"
    evidence.approved_by = frappe.session.user
    evidence.approved_on = now_datetime()
    evidence.validation_notes = (evidence.validation_notes or "") + f"\n→ Approved by {frappe.session.user}"
    goal.flags.ignore_validate = True
    goal.save()
    frappe.db.commit()
    recalculate_progress(goal_name)
    _append_audit_log(goal_name, "Evidence Approved", "Pending", "Approved", frappe.session.user)
    return {"status": "approved"}


@frappe.whitelist()
def reject_evidence(goal_name, evidence_idx, reason):
    goal = frappe.get_doc("Individual Goal", goal_name)
    me_employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
    goal_employee = frappe.db.get_value("Employee", goal.employee, "reports_to")
    is_manager = me_employee and me_employee == goal_employee
    is_hr = frappe.has_role("HR Manager") or frappe.has_role("System Manager")
    if not is_manager and not is_hr:
        frappe.throw(_("Only the employee's manager or HR can reject evidence"), frappe.PermissionError)
    evidence = goal.evidence_items[int(evidence_idx)]
    evidence.validation_status = "Rejected"
    evidence.rejection_reason = reason
    evidence.validation_notes = (evidence.validation_notes or "") + f"\n→ Rejected by {frappe.session.user}: {reason}"
    goal.flags.ignore_validate = True
    goal.save()
    frappe.db.commit()
    _append_audit_log(goal_name, "Evidence Rejected", "Pending", "Rejected", frappe.session.user, reason)
    return {"status": "rejected"}
