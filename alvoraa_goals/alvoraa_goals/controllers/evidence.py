import frappe
from frappe import _
from frappe.utils import now_datetime
from alvoraa_goals.validators.invoice_validator import validate_invoice
from alvoraa_goals.validators.sales_order_validator import validate_sales_order
from alvoraa_goals.validators.duplicate_detector import check_duplicate
from alvoraa_goals.controllers.goal import recalculate_progress, _append_audit_log


def validate_evidence(doc, method=None):
    # ── DEBUG ─────────────────────────────────────────────────────────────
    frappe.log_error(
        f"[DEBUG] validate_evidence CALLED\n"
        f"  parent goal : {doc.parent}\n"
        f"  evidence_type: {doc.evidence_type}\n"
        f"  order_count  : {doc.extracted_order_count}\n"
        f"  amount       : {doc.extracted_amount}\n"
        f"  date         : {doc.extracted_date}\n"
        f"  customer     : {doc.extracted_customer}\n"
        f"  volume       : {doc.extracted_volume} {doc.extracted_volume_unit}\n"
        f"  evidence_file: {doc.evidence_file}",
        "[DEBUG] validate_evidence entry"
    )
    frappe.msgprint(
        f"[DEBUG] Validation hook fired — type: <b>{doc.evidence_type}</b> | "
        f"count: {doc.extracted_order_count} | amount: {doc.extracted_amount} | "
        f"volume: {doc.extracted_volume} {doc.extracted_volume_unit}",
        alert=True, indicator="blue"
    )
    # ── END DEBUG ──────────────────────────────────────────────────────────

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
            doc.validation_notes += "\n→ Pending: rule(s) failed — sent for HR review"
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
            doc.validation_notes += "\n→ Pending: rule(s) failed — sent for HR review"
        else:
            doc.validation_status = "Approved"
            doc.approved_by = "System"
            doc.approved_on = now_datetime()
            doc.validation_notes += "\n→ Auto-approved by System"

    else:
        doc.validation_status = "Pending"
        doc.validation_notes = "[Manual Entry] No automated validation — pending HR review"

    # ── DEBUG ─────────────────────────────────────────────────────────────
    frappe.log_error(
        f"[DEBUG] validate_evidence RESULT\n"
        f"  validation_status: {doc.validation_status}\n"
        f"  approved_by      : {doc.approved_by}\n"
        f"  validation_notes :\n{doc.validation_notes}",
        "[DEBUG] validate_evidence result"
    )
    frappe.msgprint(
        f"[DEBUG] Validation result — status: <b>{doc.validation_status}</b> | "
        f"approved_by: {doc.approved_by or 'none'}",
        alert=True, indicator="green" if doc.validation_status == "Approved" else "orange"
    )
    # ── END DEBUG ──────────────────────────────────────────────────────────

    dup_result = check_duplicate(doc, goal.name)
    if dup_result:
        doc.validation_status = "Pending"
        doc.validation_notes += f"\n⚠ Duplicate detected (similarity: {dup_result['score']}%) — overriding to Pending for HR review"
        frappe.msgprint(f"Possible duplicate evidence detected (similarity: {dup_result['score']}%). Sent for HR review.", alert=True)


def after_insert_evidence(doc, method=None):
    # ── DEBUG ─────────────────────────────────────────────────────────────
    frappe.log_error(
        f"[DEBUG] after_insert_evidence CALLED — status={doc.validation_status}",
        "[DEBUG] after_insert_evidence"
    )
    # ── END DEBUG ──────────────────────────────────────────────────────────
    _append_audit_log(doc.parent, "Evidence Added", None, doc.evidence_type, frappe.session.user, f"Evidence type: {doc.evidence_type}, status: {doc.validation_status}")
    if doc.validation_status == "Approved":
        recalculate_progress(doc.parent)


@frappe.whitelist()
def approve_evidence(goal_name, evidence_idx):
    goal = frappe.get_doc("Individual Goal", goal_name)
    if not frappe.has_permission("Individual Goal", "write", goal_name):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    evidence = goal.evidence_items[int(evidence_idx)]
    evidence.validation_status = "Approved"
    evidence.approved_by = frappe.session.user
    evidence.approved_on = now_datetime()
    evidence.validation_notes = (evidence.validation_notes or "") + f"\n→ Manually approved by {frappe.session.user}"
    goal.flags.ignore_validate = True
    goal.save()
    frappe.db.commit()
    recalculate_progress(goal_name)
    _append_audit_log(goal_name, "Evidence Approved", "Pending", "Approved", frappe.session.user)
    return {"status": "approved"}


@frappe.whitelist()
def reject_evidence(goal_name, evidence_idx, reason):
    goal = frappe.get_doc("Individual Goal", goal_name)
    if not frappe.has_permission("Individual Goal", "write", goal_name):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    evidence = goal.evidence_items[int(evidence_idx)]
    evidence.validation_status = "Rejected"
    evidence.rejection_reason = reason
    evidence.validation_notes = (evidence.validation_notes or "") + f"\n→ Rejected by {frappe.session.user}: {reason}"
    goal.flags.ignore_validate = True
    goal.save()
    frappe.db.commit()
    _append_audit_log(goal_name, "Evidence Rejected", "Pending", "Rejected", frappe.session.user, reason)
    return {"status": "rejected"}
