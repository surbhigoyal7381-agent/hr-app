import frappe
from frappe import _
from frappe.utils import now_datetime
import json


@frappe.whitelist()
def get_goal_cascade(cascade_id):
    from grace_goals.controllers.cascade import get_cascade_tree
    if not frappe.has_permission("Goal Cascade", "read", cascade_id):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    return get_cascade_tree(cascade_id)


@frappe.whitelist()
def get_employee_goals(employee_id=None):
    if not frappe.has_permission("Individual Goal", "read"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    user_employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
    if not employee_id:
        employee_id = user_employee
    if not employee_id:
        frappe.throw(_("No employee record found for your account."), frappe.DoesNotExistError)
    if user_employee != employee_id and not frappe.has_permission("Individual Goal", "write"):
        frappe.throw(_("Not permitted to view other employees' goals"), frappe.PermissionError)
    goals = frappe.get_all(
        "Individual Goal",
        filters={"employee": employee_id, "status": ["!=", "Cancelled"], "docstatus": 1},
        fields=["name", "goal_name", "target_value", "unit", "actual_progress",
                "progress_pct", "status", "trajectory", "start_date", "end_date", "goal_cascade"]
    )
    for goal in goals:
        goal["evidence"] = frappe.get_all(
            "Goal Evidence",
            filters={"parent": goal["name"], "validation_status": "Approved"},
            fields=["evidence_type", "upload_date", "extracted_order_count",
                    "extracted_amount", "extracted_date", "extracted_customer"]
        )
        goal["pending_evidence_count"] = frappe.db.count(
            "Goal Evidence", {"parent": goal["name"], "validation_status": "Pending"}
        )
    return goals


@frappe.whitelist()
def submit_goal_evidence(goal_id, evidence_type, extracted_order_count=None,
                         extracted_amount=None, extracted_date=None,
                         extracted_customer=None, evidence_file=None, raw_extracted_data=None):
    goal = frappe.get_doc("Individual Goal", goal_id)
    user_employee = frappe.get_value("Employee", {"user_id": frappe.session.user}, "name")
    if goal.employee != user_employee and not frappe.has_permission("Individual Goal", "write", goal_id):
        frappe.throw(_("Not permitted to submit evidence for this goal"), frappe.PermissionError)
    evidence = {
        "doctype": "Goal Evidence",
        "parenttype": "Individual Goal",
        "parentfield": "evidence_items",
        "parent": goal_id,
        "evidence_type": evidence_type,
        "uploaded_by": frappe.session.user,
        "upload_date": now_datetime(),
        "validation_status": "Approved",
        "extracted_order_count": extracted_order_count,
        "extracted_amount": extracted_amount,
        "extracted_date": extracted_date,
        "extracted_customer": extracted_customer,
        "evidence_file": evidence_file,
        "raw_extracted_data": raw_extracted_data,
    }
    goal.append("evidence_items", evidence)
    goal.flags.ignore_validate_update_after_submit = True
    goal.save()
    frappe.db.commit()

    # Recalculate progress immediately so the submission is reflected at once
    from grace_goals.controllers.goal import recalculate_progress
    recalculate_progress(goal_id)

    goal.reload()
    return {
        "status": "Approved",
        "evidence_idx": len(goal.evidence_items) - 1,
        "progress": goal.actual_progress,
        "progress_pct": goal.progress_pct,
    }


@frappe.whitelist()
def get_cascade_alignment(cascade_id):
    reports = frappe.get_all(
        "Cascade Alignment Report",
        filters={"goal_cascade": cascade_id},
        fields=["*"],
        order_by="report_date desc",
        limit=1
    )
    if reports:
        return reports[0]
    from grace_goals.controllers.cascade import run_alignment_check
    return run_alignment_check(cascade_id).as_dict()


@frappe.whitelist()
def get_progress_audit_log(goal_id, start_date=None, end_date=None):
    if not frappe.has_permission("Individual Goal", "read", goal_id):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    filters = {"goal_id": goal_id}
    if start_date:
        filters["change_date"] = [">=", start_date]
    if end_date:
        filters["change_date"] = ["<=", end_date]
    return frappe.get_all(
        "Goal Progress Audit Log",
        filters=filters,
        fields=["event_type", "old_value", "new_value", "changed_by",
                "change_date", "reason"],
        order_by="change_date desc"
    )


@frappe.whitelist()
def recalculate_progress(goal_id):
    if not frappe.has_permission("Individual Goal", "write", goal_id):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    from grace_goals.controllers.goal import recalculate_progress as _recalc
    _recalc(goal_id)
    goal = frappe.get_doc("Individual Goal", goal_id)
    return {"progress": goal.actual_progress, "progress_pct": goal.progress_pct, "trajectory": goal.trajectory}
