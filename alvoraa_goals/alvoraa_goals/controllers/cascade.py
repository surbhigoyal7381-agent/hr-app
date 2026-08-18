import frappe
from frappe import _
from frappe.utils import now_datetime


def validate_goal_cascade(doc, method=None):
    if doc.period_start and doc.period_end and doc.period_start > doc.period_end:
        frappe.throw(_("Period start must be before period end"))
    if doc.company_target <= 0:
        frappe.throw(_("Company target must be greater than 0"))


def get_cascade_tree(cascade_name):
    cascade = frappe.get_doc("Goal Cascade", cascade_name)
    goals = frappe.get_all(
        "Individual Goal",
        filters={"goal_cascade": cascade_name, "docstatus": ["!=", 2]},
        fields=["name", "employee", "employee_name", "goal_name", "target_value",
                "actual_progress", "progress_pct", "status", "trajectory",
                "parent_goal", "unit", "start_date", "end_date"],
        ignore_permissions=True,
    )
    roots = [g for g in goals if not g.parent_goal]
    children_map = {}
    for g in goals:
        if g.parent_goal:
            children_map.setdefault(g.parent_goal, []).append(g)

    def build_tree(node):
        node["children"] = [build_tree(c) for c in children_map.get(node["name"], [])]
        return node

    return {
        "cascade": cascade.as_dict(),
        "goals": [build_tree(r) for r in roots],
        "flat_goals": goals,
    }


def run_alignment_check(cascade_name):
    cascade = frappe.get_doc("Goal Cascade", cascade_name)
    # Goals are live from creation in the portal — nothing submits them — so
    # anything not cancelled counts toward alignment.
    goals = frappe.get_all(
        "Individual Goal",
        filters={"goal_cascade": cascade_name, "docstatus": ["!=", 2]},
        fields=["target_value"],
        ignore_permissions=True,
    )
    sum_targets = sum(g.target_value for g in goals if g.target_value)
    variance_pct = abs(cascade.company_target - sum_targets) / cascade.company_target * 100 if cascade.company_target else 0
    status = "Aligned" if variance_pct < 5 else ("Misaligned" if goals else "Not Enough Data")
    report = frappe.new_doc("Cascade Alignment Report")
    report.goal_cascade = cascade_name
    report.report_date = now_datetime()
    report.company_target = cascade.company_target
    report.sum_division_targets = sum_targets
    report.variance_pct = variance_pct
    report.status = status
    report.details = f"Company target: {cascade.company_target}, Sum of individual goal targets: {sum_targets:.2f}, Variance: {variance_pct:.1f}%"
    report.generated_by = frappe.session.user or "System"
    report.flags.ignore_permissions = True
    report.insert()
    frappe.db.commit()
    return report
