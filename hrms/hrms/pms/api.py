import frappe
from frappe import _


def _employee_or_throw():
    emp = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
    if not emp:
        frappe.throw(_("No Employee record found for current user."), frappe.PermissionError)
    return emp


# ── Dashboard context ────────────────────────────────────────────────────────

@frappe.whitelist()
def get_employee_dashboard(cycle=None):
    emp = _employee_or_throw()
    if not cycle:
        cycle = frappe.db.get_value("PMS Cycle", {"status": "Active"}, "name", order_by="creation desc")
    if not cycle:
        return {"cycle": None, "review_record": None, "goals": [], "dev_goals": [], "checkins": []}

    review_record = frappe.db.get_value(
        "PMS Review Record", {"employee": emp, "cycle": cycle}, "*", as_dict=True
    )

    goals = frappe.get_all(
        "PMS Business Goal",
        filters={"employee": emp, "cycle": cycle, "is_review_draft": 0, "status": ["!=", "Cancelled"]},
        fields=["name", "goal_title", "status", "weight", "goal_type"],
        order_by="goal_title asc",
    )

    dev_goals = frappe.get_all(
        "PMS Development Goal",
        filters={"employee": emp, "cycle": cycle},
        fields=["name", "title", "status", "development_type"],
    )

    checkins = frappe.get_all(
        "PMS Check In",
        filters={"employee": emp, "cycle": cycle},
        fields=["name", "check_in_date", "status", "manager"],
        order_by="check_in_date desc",
        limit=5,
    )

    return {
        "cycle": cycle,
        "review_record": review_record,
        "goals": goals,
        "dev_goals": dev_goals,
        "checkins": checkins,
    }


@frappe.whitelist()
def get_manager_dashboard(cycle=None):
    emp = _employee_or_throw()
    if not cycle:
        cycle = frappe.db.get_value("PMS Cycle", {"status": "Active"}, "name", order_by="creation desc")

    direct_reports = frappe.get_all("Employee", filters={"reports_to": emp}, fields=["name", "employee_name"])

    review_records = []
    for dr in direct_reports:
        rr = frappe.db.get_value(
            "PMS Review Record",
            {"employee": dr.name, "cycle": cycle},
            ["name", "status", "self_review_submitted_on", "dialogue_date"],
            as_dict=True,
        )
        if rr:
            rr["employee_name"] = dr.employee_name
            review_records.append(rr)

    return {"cycle": cycle, "team": review_records}


@frappe.whitelist()
def get_steering_dashboard():
    if not frappe.db.exists("Has Role", {"parent": frappe.session.user, "role": ["in", ["HR Manager", "System Manager"]]}):
        frappe.throw(_("Access restricted to HR."), frappe.PermissionError)

    cycles = frappe.get_all("PMS Cycle", filters={"status": "Active"}, fields=["name", "cycle_name"])
    data = []
    for c in cycles:
        total = frappe.db.count("PMS Review Record", {"cycle": c.name})
        closed = frappe.db.count("PMS Review Record", {"cycle": c.name, "status": "Closed"})
        calibrated = frappe.db.count("PMS Review Record", {"cycle": c.name, "status": "Calibrated"})
        data.append({**c, "total": total, "closed": closed, "calibrated": calibrated})
    return {"cycles": data}


# ── Goal management ───────────────────────────────────────────────────────────

@frappe.whitelist()
def approve_goal(goal_name):
    emp = _employee_or_throw()
    goal = frappe.get_doc("PMS Business Goal", goal_name)
    reports = frappe.get_all("Employee", filters={"reports_to": emp}, pluck="name")
    if goal.employee not in reports:
        frappe.throw(_("Not permitted to approve this goal."), frappe.PermissionError)
    frappe.db.set_value("PMS Business Goal", goal_name, {
        "approval_status": "Approved",
        "approved_by": emp,
        "approved_on": frappe.utils.now(),
        "status": "Active",
    })
    return {"status": "approved"}


@frappe.whitelist()
def reject_goal(goal_name, reason):
    emp = _employee_or_throw()
    goal = frappe.get_doc("PMS Business Goal", goal_name)
    reports = frappe.get_all("Employee", filters={"reports_to": emp}, pluck="name")
    if goal.employee not in reports:
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    frappe.db.set_value("PMS Business Goal", goal_name, {
        "approval_status": "Rejected",
        "rejection_reason": reason,
        "status": "Draft",
    })
    return {"status": "rejected"}


@frappe.whitelist()
def get_cascade_tree(goal_name):
    """Return the cascade hierarchy for a goal using recursive CTE."""
    rows = frappe.db.sql(
        """
        WITH RECURSIVE cascade_tree AS (
          SELECT name, goal_title, employee, parent_objective, 0 AS depth
          FROM `tabPMS Business Goal`
          WHERE name = %(goal)s
          UNION ALL
          SELECT g.name, g.goal_title, g.employee, g.parent_objective, ct.depth + 1
          FROM `tabPMS Business Goal` g
          JOIN cascade_tree ct ON g.parent_objective = ct.name
          WHERE ct.depth < 10
        )
        SELECT * FROM cascade_tree ORDER BY depth
        """,
        {"goal": goal_name},
        as_dict=True,
    )
    return rows


# ── Review flow actions ───────────────────────────────────────────────────────

@frappe.whitelist()
def submit_self_review(review_record_name):
    emp = _employee_or_throw()
    rr = frappe.get_doc("PMS Review Record", review_record_name)
    if rr.employee != emp:
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    from hrms.pms.draft_isolation import activate_review_goals
    activate_review_goals(review_record_name)
    frappe.db.set_value("PMS Review Record", review_record_name, {
        "self_review_submitted_on": frappe.utils.now(),
        "status": "Self Review Submitted",
    })
    return {"status": "submitted"}


@frappe.whitelist()
def acknowledge_final_form(review_record_name):
    emp = _employee_or_throw()
    rr = frappe.get_doc("PMS Review Record", review_record_name)
    if rr.employee != emp:
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    if rr.status != "Final Form With Employee":
        frappe.throw(_("Review is not in 'Final Form With Employee' state."))
    frappe.db.set_value("PMS Review Record", review_record_name, {
        "employee_submitted_on": frappe.utils.now(),
        "status": "Submitted by Employee",
    })
    return {"status": "acknowledged"}


@frappe.whitelist()
def unlock_rating_visibility(review_record_name):
    if not frappe.db.exists("Has Role", {"parent": frappe.session.user, "role": ["in", ["HR Manager", "System Manager"]]}):
        frappe.throw(_("HR access required."), frappe.PermissionError)
    frappe.db.set_value("PMS Review Record", review_record_name, "overall_rating_visible_to_employee", 1)
    return {"status": "unlocked"}


# ── Reporting ─────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_rating_distribution(cycle):
    if not frappe.db.exists("Has Role", {"parent": frappe.session.user, "role": ["in", ["HR Manager", "System Manager"]]}):
        frappe.throw(_("HR access required."), frappe.PermissionError)
    rows = frappe.db.sql(
        """
        SELECT overall_rating, COUNT(*) as count
        FROM `tabPMS Review Record`
        WHERE cycle = %s AND status IN ('Calibrated','Closed')
        GROUP BY overall_rating
        ORDER BY overall_rating
        """,
        (cycle,),
        as_dict=True,
    )
    return rows


@frappe.whitelist()
def get_cycle_completion(cycle):
    if not frappe.db.exists("Has Role", {"parent": frappe.session.user, "role": ["in", ["HR Manager", "System Manager"]]}):
        frappe.throw(_("HR access required."), frappe.PermissionError)
    total = frappe.db.count("PMS Review Record", {"cycle": cycle})
    by_status = frappe.db.sql(
        "SELECT status, COUNT(*) as count FROM `tabPMS Review Record` WHERE cycle=%s GROUP BY status",
        (cycle,),
        as_dict=True,
    )
    return {"total": total, "by_status": by_status}
