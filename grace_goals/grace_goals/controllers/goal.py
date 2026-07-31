import frappe
from frappe import _
from frappe.utils import now_datetime, date_diff, today


def validate_individual_goal(doc, method=None):
    if doc.target_value <= 0:
        frappe.throw(_("Target value must be greater than 0"))
    if doc.start_date and doc.end_date and doc.start_date > doc.end_date:
        frappe.throw(_("Start date must be before end date"))

    # Alignment is optional. An organisational objective — the company owner's,
    # typically — is where a cascade begins rather than a link within one, so it
    # has neither a parent nor a cascade to validate against.
    if doc.goal_cascade:
        cascade = frappe.get_doc("Goal Cascade", doc.goal_cascade)
        if cascade.status not in ("Active", "Draft"):
            frappe.throw(_("Cannot assign goal to a {0} cascade").format(cascade.status))

    if doc.parent_goal and doc.parent_goal == doc.name:
        frappe.throw(_("A goal cannot roll up into itself"))

    if doc.actual_progress > 0 and doc.has_value_changed("target_value"):
        frappe.throw(_("Cannot change target after evidence has been submitted"))
    _update_trajectory(doc)


def _update_trajectory(doc):
    if not doc.start_date or not doc.end_date or not doc.target_value:
        return
    days_total = date_diff(doc.end_date, doc.start_date)
    days_elapsed = date_diff(today(), doc.start_date)
    if days_elapsed <= 0:
        doc.trajectory = "Not Started"
        return
    expected_pct = min((days_elapsed / days_total) * 100, 100) if days_total > 0 else 0
    actual_pct = (doc.actual_progress / doc.target_value) * 100 if doc.target_value else 0
    if actual_pct >= expected_pct:
        doc.trajectory = "On Track"
    elif actual_pct >= expected_pct * 0.75:
        doc.trajectory = "At Risk"
    else:
        doc.trajectory = "Off Track"


def after_insert_goal(doc, method=None):
    _append_audit_log(doc.name, "Created", None, doc.target_value, frappe.session.user, "Goal created")


def before_submit_goal(doc, method=None):
    frappe.sendmail(
        recipients=[frappe.get_value("Employee", doc.employee, "company_email") or frappe.get_value("Employee", doc.employee, "prefered_email")],
        subject=f"Goal Submitted: {doc.goal_name}",
        message=f"Your goal '{doc.goal_name}' has been submitted. Target: {doc.target_value} {doc.unit or ''}",
    )


def on_submit_goal(doc, method=None):
    _append_audit_log(doc.name, "Status Changed", "Draft", "Submitted", frappe.session.user, "Goal submitted")


def recalculate_progress(goal_name):
    goal = frappe.get_doc("Individual Goal", goal_name)
    approved_evidence = frappe.get_all(
        "Goal Evidence",
        filters={"parent": goal_name, "validation_status": "Approved"},
        fields=["extracted_order_count", "extracted_amount", "evidence_type"]
    )
    unit = (goal.unit or "").lower()
    if "revenue" in unit or "amount" in unit:
        total = sum(e.extracted_amount or 0 for e in approved_evidence)
    else:
        total = sum(e.extracted_order_count or 0 for e in approved_evidence)
    old = goal.actual_progress
    goal.actual_progress = total
    goal.progress_pct = min((total / goal.target_value) * 100, 100) if goal.target_value else 0
    _update_trajectory(goal)
    if goal.progress_pct >= 100:
        goal.status = "Completed"
    goal.flags.ignore_validate = True
    goal.flags.ignore_validate_update_after_submit = True
    goal.save()
    frappe.db.commit()
    _append_audit_log(goal_name, "Progress Updated", old, total, frappe.session.user, "Recalculated from approved evidence")
    _aggregate_cascade(goal.goal_cascade)


def _aggregate_cascade(cascade_name):
    """Roll up contributing goals' progress onto the Goal Cascade.

    Two things used to stop this working. It filtered on `docstatus: 1`, but
    nothing in the portal submits goals, so it always matched zero rows; goals
    are live from creation here, and only a cancelled one (docstatus 2) should
    be excluded. And it wrote to `__last_agg_pct`, which is not a field on the
    doctype — the value went nowhere.
    """
    if not cascade_name:
        # Organisational goals have no cascade; there is nothing to roll up to.
        return

    goals = frappe.get_all(
        "Individual Goal",
        filters={"goal_cascade": cascade_name, "docstatus": ["!=", 2]},
        fields=["actual_progress", "target_value"],
        ignore_permissions=True,
    )
    total_target = sum(g.target_value for g in goals if g.target_value)
    total_actual = sum(g.actual_progress for g in goals if g.actual_progress)
    agg_pct = (total_actual / total_target * 100) if total_target else 0

    frappe.db.set_value(
        "Goal Cascade", cascade_name,
        {"aggregate_progress_pct": agg_pct, "aggregate_updated_on": now_datetime()},
        update_modified=False,
    )


def _append_audit_log(goal_id, event_type, old_value, new_value, changed_by, reason=None):
    try:
        log = frappe.new_doc("Goal Progress Audit Log")
        log.goal_id = goal_id
        log.event_type = event_type
        log.old_value = str(old_value) if old_value is not None else ""
        log.new_value = str(new_value) if new_value is not None else ""
        log.changed_by = changed_by or frappe.session.user
        log.change_date = now_datetime()
        log.reason = reason
        log.flags.ignore_permissions = True
        log.insert()
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Audit Log Write Failed")
