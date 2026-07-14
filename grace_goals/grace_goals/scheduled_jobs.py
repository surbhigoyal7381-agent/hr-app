import frappe


def recalculate_all_progress():
    from grace_goals.controllers.goal import recalculate_progress
    active_goals = frappe.get_all(
        "Individual Goal",
        filters={"status": "Active", "docstatus": 1},
        fields=["name"]
    )
    for goal in active_goals:
        try:
            recalculate_progress(goal.name)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"Progress recalc failed for {goal.name}")


def check_cascade_alignment():
    from grace_goals.controllers.cascade import run_alignment_check
    active_cascades = frappe.get_all(
        "Goal Cascade",
        filters={"status": "Active"},
        fields=["name"]
    )
    for cascade in active_cascades:
        try:
            run_alignment_check(cascade.name)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"Alignment check failed for {cascade.name}")


def send_progress_reminders():
    at_risk_goals = frappe.get_all(
        "Individual Goal",
        filters={"trajectory": ["in", ["At Risk", "Off Track"]], "status": "Active", "docstatus": 1},
        fields=["name", "goal_name", "employee", "employee_name", "progress_pct", "trajectory"]
    )
    for goal in at_risk_goals:
        try:
            email = frappe.get_value("Employee", goal.employee, "company_email") or \
                    frappe.get_value("Employee", goal.employee, "prefered_email")
            if not email:
                continue
            frappe.sendmail(
                recipients=[email],
                subject=f"Goal Alert: {goal.goal_name} is {goal.trajectory}",
                message=f"Hi {goal.employee_name},<br><br>Your goal <b>{goal.goal_name}</b> is currently <b>{goal.trajectory}</b> at {goal.progress_pct:.1f}% progress.<br><br>Please submit evidence or contact your manager.",
            )
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"Reminder failed for {goal.name}")
