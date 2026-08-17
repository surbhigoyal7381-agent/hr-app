import frappe
from frappe import _
from frappe.utils import now_datetime, today
import json


def _auto_approve_enabled():
    return frappe.db.get_default("auto_approve_evidence") == "1"


def _notify_manager(employee, subject, message):
    manager_employee = frappe.db.get_value("Employee", employee, "reports_to")
    if not manager_employee:
        return
    manager_email = (
        frappe.db.get_value("Employee", manager_employee, "company_email")
        or frappe.db.get_value("Employee", manager_employee, "prefered_email")
    )
    if manager_email:
        frappe.sendmail(recipients=[manager_email], subject=subject, message=message)


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
        fields=["name", "goal_name", "target_value", "unit", "progress_mode",
                "actual_progress", "progress_pct", "status", "trajectory",
                "start_date", "end_date", "goal_cascade"],
    )
    for goal in goals:
        goal["evidence"] = frappe.get_all(
            "Goal Evidence",
            filters={"parent": goal["name"], "validation_status": "Approved"},
            fields=["evidence_type", "upload_date", "value", "extracted_date"],
        )
        goal["pending_evidence_count"] = frappe.db.count(
            "Goal Evidence", {"parent": goal["name"], "validation_status": "Pending"}
        )
    return goals


@frappe.whitelist()
def submit_goal_evidence(goal_id, evidence_type, value=None, extracted_date=None,
                         evidence_file=None, raw_extracted_data=None, appraisal_id=None,
                         extracted_amount=None):
    # extracted_amount kept as alias for backward compat; value takes precedence
    progress_value = value or extracted_amount

    goal = frappe.get_doc("Individual Goal", goal_id)
    user_employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
    if goal.employee != user_employee and not frappe.has_permission("Individual Goal", "write", goal_id):
        frappe.throw(_("Not permitted to submit evidence for this goal"), frappe.PermissionError)

    auto_approve = _auto_approve_enabled()
    status = "Approved" if auto_approve else "Pending"

    evidence = {
        "doctype": "Goal Evidence",
        "parenttype": "Individual Goal",
        "parentfield": "evidence_items",
        "parent": goal_id,
        "evidence_type": evidence_type,
        "uploaded_by": frappe.session.user,
        "upload_date": now_datetime(),
        "validation_status": status,
        "value": progress_value,
        "extracted_date": extracted_date,
        "evidence_file": evidence_file,
        "raw_extracted_data": raw_extracted_data,
    }
    if auto_approve:
        evidence["approved_by"] = frappe.session.user
        evidence["approved_on"] = now_datetime()

    goal.append("evidence_items", evidence)
    goal.flags.ignore_validate_update_after_submit = True
    goal.save()
    frappe.db.commit()

    if auto_approve:
        from grace_goals.controllers.goal import recalculate_progress
        recalculate_progress(goal_id)
    else:
        _notify_manager(
            goal.employee,
            f"Evidence Pending Approval: {goal.goal_name}",
            f"{frappe.session.user} submitted evidence for goal <b>{goal.goal_name}</b> "
            f"(value: {progress_value or '—'}, type: {evidence_type}). "
            f"Please review and approve.",
        )

    goal.reload()
    return {
        "status": status,
        "evidence_idx": len(goal.evidence_items) - 1,
        "progress": goal.actual_progress,
        "progress_pct": goal.progress_pct,
    }


@frappe.whitelist()
def submit_kpi_progress(kpi_name, value, log_date=None, note=None, evidence_file=None):
    kpi = frappe.get_doc("KPI", kpi_name)
    user_employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
    if kpi.employee != user_employee and not frappe.has_permission("KPI", "write", kpi_name):
        frappe.throw(_("Not permitted to submit progress for this KPI"), frappe.PermissionError)

    auto_approve = _auto_approve_enabled()
    status = "Approved" if auto_approve else "Pending"

    log_entry = {
        "doctype": "KPI Progress Log",
        "parenttype": "KPI",
        "parentfield": "progress_log",
        "parent": kpi_name,
        "log_date": log_date or today(),
        "value": frappe.utils.flt(value),
        "logged_by": frappe.session.user,
        "note": note,
        "evidence_file": evidence_file,
        "approval_status": status,
    }
    if auto_approve:
        log_entry["approved_by"] = frappe.session.user
        log_entry["approved_on"] = now_datetime()

    kpi.append("progress_log", log_entry)
    kpi.flags.ignore_validate = True
    kpi.save()
    frappe.db.commit()

    if auto_approve:
        from grace_goals.controllers.goal import recalculate_kpi_progress
        recalculate_kpi_progress(kpi_name)
    else:
        _notify_manager(
            kpi.employee,
            f"KPI Progress Pending Approval: {kpi.kpi_name}",
            f"{frappe.session.user} logged progress for KPI <b>{kpi.kpi_name}</b> "
            f"(value: {value}). Please review and approve.",
        )

    kpi.reload()
    return {
        "status": status,
        "log_idx": len(kpi.progress_log) - 1,
        "actual_value": kpi.actual_value,
        "attainment_pct": kpi.attainment_pct,
    }


@frappe.whitelist()
def approve_kpi_progress(kpi_name, log_idx, comment=None):
    kpi = frappe.get_doc("KPI", kpi_name)
    me_employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
    kpi_manager = frappe.db.get_value("Employee", kpi.employee, "reports_to")
    is_manager = me_employee and me_employee == kpi_manager
    is_hr = frappe.has_role("HR Manager") or frappe.has_role("System Manager")
    if not is_manager and not is_hr:
        frappe.throw(_("Only the employee's manager or HR can approve KPI progress"), frappe.PermissionError)
    log = kpi.progress_log[int(log_idx)]
    log.approval_status = "Approved"
    log.approved_by = frappe.session.user
    log.approved_on = now_datetime()
    if comment:
        log.approval_comment = comment
    kpi.flags.ignore_validate = True
    kpi.save()
    frappe.db.commit()
    from grace_goals.controllers.goal import recalculate_kpi_progress
    recalculate_kpi_progress(kpi_name)
    return {"status": "approved"}


@frappe.whitelist()
def reject_kpi_progress(kpi_name, log_idx, comment=None):
    kpi = frappe.get_doc("KPI", kpi_name)
    me_employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
    kpi_manager = frappe.db.get_value("Employee", kpi.employee, "reports_to")
    is_manager = me_employee and me_employee == kpi_manager
    is_hr = frappe.has_role("HR Manager") or frappe.has_role("System Manager")
    if not is_manager and not is_hr:
        frappe.throw(_("Only the employee's manager or HR can reject KPI progress"), frappe.PermissionError)
    log = kpi.progress_log[int(log_idx)]
    log.approval_status = "Rejected"
    log.approved_by = frappe.session.user
    log.approved_on = now_datetime()
    if comment:
        log.approval_comment = comment
    kpi.flags.ignore_validate = True
    kpi.save()
    frappe.db.commit()
    return {"status": "rejected"}


@frappe.whitelist()
def get_pending_approvals(employee_id=None):
    """Returns pending goal evidence and KPI progress logs for the manager's direct reports."""
    me_employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
    if not me_employee:
        return {"goals": [], "kpis": []}

    # ignore_permissions: caller already verified via me_employee lookup; reading org structure data only.
    direct_reports = frappe.get_all(
        "Employee",
        filters={"reports_to": me_employee, "status": "Active"},
        pluck="name",
        ignore_permissions=True,
    )
    if not direct_reports:
        return {"goals": [], "kpis": []}

    pending_goals = []
    for emp in direct_reports:
        # ignore_permissions: scope limited to caller's direct reports (verified above).
        goals = frappe.get_all(
            "Individual Goal",
            filters={"employee": emp, "docstatus": ["!=", 2]},
            fields=["name", "goal_name", "unit", "employee", "employee_name"],
            ignore_permissions=True,
        )
        for g in goals:
            # ignore_permissions: child table of a doc already in scope.
            evidence = frappe.get_all(
                "Goal Evidence",
                filters={"parent": g["name"], "validation_status": "Pending"},
                fields=["name", "idx", "evidence_type", "value", "extracted_date", "upload_date", "uploaded_by"],
                ignore_permissions=True,
            )
            for e in evidence:
                pending_goals.append({**g, "evidence": e})

    pending_kpis = []
    for emp in direct_reports:
        # ignore_permissions: scope limited to caller's direct reports (verified above).
        kpis = frappe.get_all(
            "KPI",
            filters={"employee": emp, "docstatus": ["!=", 2]},
            fields=["name", "kpi_name", "unit", "employee", "employee_name"],
            ignore_permissions=True,
        )
        for k in kpis:
            # ignore_permissions: child table of a doc already in scope.
            logs = frappe.get_all(
                "KPI Progress Log",
                filters={"parent": k["name"], "approval_status": "Pending"},
                fields=["name", "idx", "log_date", "value", "note", "logged_by"],
                ignore_permissions=True,
            )
            for l in logs:
                pending_kpis.append({**k, "log": l})

    return {"goals": pending_goals, "kpis": pending_kpis}


@frappe.whitelist()
def get_cascade_alignment(cascade_id):
    reports = frappe.get_all(
        "Cascade Alignment Report",
        filters={"goal_cascade": cascade_id},
        fields=["*"],
        order_by="report_date desc",
        limit=1,
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
        fields=["event_type", "old_value", "new_value", "changed_by", "change_date", "reason"],
        order_by="change_date desc",
    )


@frappe.whitelist()
def recalculate_progress(goal_id):
    if not frappe.has_permission("Individual Goal", "write", goal_id):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    from grace_goals.controllers.goal import recalculate_progress as _recalc
    _recalc(goal_id)
    goal = frappe.get_doc("Individual Goal", goal_id)
    return {"progress": goal.actual_progress, "progress_pct": goal.progress_pct, "trajectory": goal.trajectory}
