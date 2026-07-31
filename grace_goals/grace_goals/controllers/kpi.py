"""KPI controller — attainment, status, and the weightage invariant.

Attainment is deliberately direction-aware. "Higher is Better" KPIs (revenue,
new accounts) attain actual/target; "Lower is Better" KPIs (collection days,
defect rate) attain target/actual, so beating a target by going *down* scores
above 100 rather than below it.
"""

import frappe
from frappe.utils import flt

# HRMS scores appraisal goals out of 5, so 100% attainment maps to 5.
MAX_RATING = 5.0

# A KPI whose weightage would push an employee's cycle total past this is
# rejected. HRMS itself throws if the appraisal's weightages do not sum to
# exactly 100, so catching it here gives a comprehensible error at the point
# of data entry rather than at appraisal generation.
TOTAL_WEIGHTAGE = 100.0


def validate_kpi(doc, method=None):
    _set_period_from_cycle(doc)
    _validate_target(doc)
    _validate_linked_objective(doc)
    _calculate_attainment(doc)
    _clamp_ratings(doc)
    _set_status(doc)
    _validate_weightage_budget(doc)


def _validate_linked_objective(doc):
    """A KPI may hang off an objective owned by the KPI's employee or anyone
    above them.

    One objective therefore collects KPIs from many people down the owner's
    branch of the tree — that is the whole point of the cascade. What it must
    not do is collect KPIs from a sibling branch, so the KPI's employee has to
    be the goal owner or sit somewhere beneath them.
    """
    if not doc.individual_goal:
        return

    goal = frappe.db.get_value(
        "Individual Goal", doc.individual_goal,
        ["employee", "employee_name", "goal_name", "goal_cascade"], as_dict=True,
    )
    if not goal:
        frappe.throw(f"Objective '{doc.individual_goal}' no longer exists.")

    if goal.employee != doc.employee:
        from grace_goals.permissions import descendants
        if doc.employee not in descendants(goal.employee):
            frappe.throw(
                f"'{goal.goal_name}' belongs to {goal.employee_name or goal.employee}, "
                f"who is not in {doc.employee_name or doc.employee}'s reporting line. "
                "A KPI can only be linked to an objective owned by that employee "
                "or by someone above them."
            )

    # The linked objective is the single source of truth for the cascade. It
    # used to only fill a blank, which let the two disagree — a KPI could claim
    # cascade Y while hanging off an objective under cascade X.
    doc.goal_cascade = goal.goal_cascade or None


def _set_period_from_cycle(doc):
    """Default the measurement window to the appraisal cycle it belongs to."""
    if not doc.appraisal_cycle or (doc.period_start and doc.period_end):
        return
    cycle = frappe.db.get_value(
        "Appraisal Cycle", doc.appraisal_cycle, ["start_date", "end_date"], as_dict=True
    )
    if not cycle:
        return
    doc.period_start = doc.period_start or cycle.start_date
    doc.period_end = doc.period_end or cycle.end_date


def _validate_target(doc):
    if flt(doc.target_value) == 0:
        frappe.throw(
            f"KPI '{doc.kpi_name}' needs a non-zero target — attainment is measured against it."
        )
    if doc.period_start and doc.period_end and doc.period_start > doc.period_end:
        frappe.throw(f"KPI '{doc.kpi_name}': period start is after period end.")


def _calculate_attainment(doc):
    target = flt(doc.target_value)
    actual = flt(doc.actual_value)

    if doc.direction == "Lower is Better":
        # No actual logged yet is not the same as a perfect score.
        doc.attainment_pct = 0 if actual == 0 else flt(target / actual * 100, 2)
    else:
        doc.attainment_pct = flt(actual / target * 100, 2)


def _clamp_ratings(doc):
    for field in ("self_rating", "manager_rating"):
        value = flt(doc.get(field))
        if value < 0 or value > MAX_RATING:
            frappe.throw(
                f"KPI '{doc.kpi_name}': {doc.meta.get_label(field)} must be between 0 and {int(MAX_RATING)}."
            )


def _set_status(doc):
    # Draft and Cancelled are explicit human decisions; never overwrite them.
    if doc.status in ("Draft", "Cancelled"):
        return
    if not doc.period_end or frappe.utils.getdate(doc.period_end) >= frappe.utils.getdate():
        doc.status = "Active"
    else:
        doc.status = "Achieved" if flt(doc.attainment_pct) >= 100 else "Missed"


def _validate_weightage_budget(doc):
    """Keep one employee's KPI weightages for one cycle within 100%."""
    if not doc.appraisal_cycle or not doc.employee or not flt(doc.weightage):
        return

    others = frappe.get_all(
        "KPI",
        filters={
            "employee": doc.employee,
            "appraisal_cycle": doc.appraisal_cycle,
            "status": ["!=", "Cancelled"],
            "name": ["!=", doc.name or ""],
        },
        pluck="weightage",
    )
    total = sum(flt(w) for w in others) + flt(doc.weightage)
    if flt(total, 2) > TOTAL_WEIGHTAGE:
        frappe.throw(
            f"{doc.employee_name or doc.employee} would be at {flt(total, 2)}% weightage for this cycle. "
            f"KPI weightages for one employee in one cycle cannot exceed {int(TOTAL_WEIGHTAGE)}%."
        )


def rating_from_attainment(attainment_pct):
    """Map attainment onto the 0-5 scale HRMS uses for appraisal goals."""
    return min(MAX_RATING, flt(attainment_pct) / 100 * MAX_RATING)
