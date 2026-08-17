import frappe
from frappe import _
from frappe.utils import now_datetime, date_diff, today

_ABSOLUTE_UNITS = {"percent", "score"}


def _default_progress_mode(unit):
    return "Absolute" if (unit or "").strip().lower() in _ABSOLUTE_UNITS else "Cumulative"


def validate_individual_goal(doc, method=None):
    if doc.target_value <= 0:
        frappe.throw(_("Target value must be greater than 0"))
    if doc.start_date and doc.end_date and doc.start_date > doc.end_date:
        frappe.throw(_("Start date must be before end date"))

    if doc.goal_cascade:
        cascade = frappe.get_doc("Goal Cascade", doc.goal_cascade)
        if cascade.status not in ("Active", "Draft"):
            frappe.throw(_("Cannot assign goal to a {0} cascade").format(cascade.status))

    if doc.parent_goal and doc.parent_goal == doc.name:
        frappe.throw(_("A goal cannot roll up into itself"))

    if doc.actual_progress > 0 and doc.has_value_changed("target_value"):
        frappe.throw(_("Cannot change target after evidence has been submitted"))

    if not doc.progress_mode:
        doc.progress_mode = _default_progress_mode(doc.unit)

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
    approved = frappe.get_all(
        "Goal Evidence",
        filters={"parent": goal_name, "validation_status": "Approved"},
        fields=["value", "upload_date"],
        order_by="upload_date asc",
        ignore_permissions=True,
    )
    mode = goal.progress_mode or _default_progress_mode(goal.unit)
    if mode == "Absolute":
        total = approved[-1].value if approved else 0
    else:
        total = sum(e.value or 0 for e in approved)

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


def recalculate_kpi_progress(kpi_name):
    kpi = frappe.get_doc("KPI", kpi_name)
    approved = frappe.get_all(
        "KPI Progress Log",
        filters={"parent": kpi_name, "approval_status": "Approved"},
        fields=["value", "log_date"],
        order_by="log_date asc",
        ignore_permissions=True,
    )
    mode = kpi.progress_mode or _default_progress_mode(kpi.unit)
    if mode == "Absolute":
        actual = approved[-1].value if approved else 0
    else:
        actual = sum(r.value or 0 for r in approved)

    if kpi.direction == "Lower is Better":
        attainment = min(kpi.target_value / actual * 100, 100) if actual else 100.0
    else:
        attainment = min(actual / kpi.target_value * 100, 100) if kpi.target_value else 0

    kpi.actual_value = actual
    kpi.attainment_pct = attainment
    if attainment >= 100:
        kpi.status = "Achieved"
    kpi.flags.ignore_validate = True
    kpi.save()
    frappe.db.commit()


def _aggregate_cascade(cascade_name):
    if not cascade_name:
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
