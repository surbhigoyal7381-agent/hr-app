"""
Goals & Performance Management – Employee Portal API
Method path: alvoraa_portal.goals_api.*

Bridges alvoraa_goals (Individual Goal, Goal Cascade) and Frappe HRMS
(Appraisal, Appraisal Cycle, KRA) into a single API layer for the portal.
"""

import frappe
from frappe.utils import today, flt, add_days


# ── Guards ────────────────────────────────────────────────────────────────

HR_ROLES = {"HR Manager", "HR User", "System Manager"}

def _is_hr(user=None):
    return bool(HR_ROLES.intersection(frappe.get_roles(user or frappe.session.user)))

def _employee_id(user=None):
    """Returns employee name or None — never throws."""
    if frappe.session.user == "Guest":
        return None
    return frappe.db.get_value("Employee", {"user_id": user or frappe.session.user}, "name")

def _require_employee():
    if frappe.session.user == "Guest":
        frappe.throw("Please log in.", frappe.PermissionError)
    emp = _employee_id()
    if not emp:
        frappe.throw("No Employee record found for your account.")
    return emp


def _is_manager(employee_id):
    return frappe.db.count("Employee", {"reports_to": employee_id, "status": "Active"}) > 0


def _goals_installed():
    try:
        frappe.get_meta("Individual Goal")
        return True
    except Exception:
        return False


def _get_active_cycle():
    cycles = frappe.get_all(
        "Appraisal Cycle",
        filters={"status": "In Progress"},
        fields=["name", "cycle_name", "start_date", "end_date",
                "kra_evaluation_method", "status"],
        order_by="start_date desc",
        limit=1,
    )
    if not cycles:
        cycles = frappe.get_all(
            "Appraisal Cycle",
            filters={"status": ["!=", "Completed"]},
            fields=["name", "cycle_name", "start_date", "end_date",
                    "kra_evaluation_method", "status"],
            order_by="start_date desc",
            limit=1,
        )
    if not cycles:
        return None
    c = cycles[0]
    c["start_date"] = str(c["start_date"]) if c["start_date"] else ""
    c["end_date"]   = str(c["end_date"])   if c["end_date"]   else ""
    return c


def _dashboard_stats(emp_id):
    if not _goals_installed():
        return {"total": 0, "active": 0, "completed": 0, "at_risk": 0,
                "avg_progress": 0, "upcoming_deadlines": 0}

    goals = frappe.get_all(
        "Individual Goal",
        filters={"employee": emp_id, "docstatus": ["!=", 2]},
        fields=["status", "progress_pct", "trajectory", "end_date"],
    )
    total     = len(goals)
    active    = sum(1 for g in goals if g["status"] == "Active")
    completed = sum(1 for g in goals if g["status"] == "Completed")
    at_risk   = sum(1 for g in goals if g.get("trajectory") in ("At Risk", "Off Track"))
    avg_pct   = round(sum(flt(g["progress_pct"]) for g in goals) / total, 1) if total else 0
    deadline30 = str(add_days(today(), 30))
    upcoming  = sum(
        1 for g in goals
        if g.get("end_date") and str(g["end_date"]) <= deadline30 and g["status"] == "Active"
    )
    return {
        "total": total, "active": active, "completed": completed,
        "at_risk": at_risk, "avg_progress": avg_pct,
        "upcoming_deadlines": upcoming,
    }


# ══════════════════════════════════════════════════════════════════════════
# Public endpoints
# ══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_portal_context():
    """Boot call: employee info + goal dashboard + active appraisal cycle."""
    if frappe.session.user == "Guest":
        frappe.throw("Please log in.", frappe.PermissionError)

    emp_id = _employee_id()
    is_hr  = _is_hr()

    # HR users without an Employee record are allowed — they see the full HR Setup tab.
    if not emp_id and not is_hr:
        frappe.throw("No Employee record found for your account.")

    emp = {}
    if emp_id:
        emp = frappe.db.get_value(
            "Employee", emp_id,
            ["employee_name", "designation", "department", "image"],
            as_dict=True,
        ) or {}

    return {
        "employee_id":    emp_id or "",
        "employee_name":  emp.get("employee_name", ""),
        "designation":    emp.get("designation", ""),
        "department":     emp.get("department", ""),
        "avatar":         emp.get("image", ""),
        "is_hr":          is_hr,
        "is_manager":     _is_manager(emp_id) if emp_id else False,
        "goals_installed": _goals_installed(),
        "dashboard":      _dashboard_stats(emp_id) if emp_id else {},
        "cycle":          _get_active_cycle(),
    }


@frappe.whitelist()
def get_my_goals(include_team=0):
    """Individual Goals for the current employee.

    With include_team, also returns goals raised for anyone in their subtree, so
    a manager sees what they set for their people alongside their own.
    """
    emp_id = _require_employee()
    if not _goals_installed():
        return []

    if int(include_team or 0):
        subjects = _manageable_employees()
    else:
        subjects = [emp_id]

    goals = frappe.get_all(
        "Individual Goal",
        filters={"employee": ["in", subjects or [""]], "docstatus": ["!=", 2]},
        fields=[
            "name", "goal_name", "goal_cascade", "parent_goal", "target_value", "unit",
            "actual_progress", "progress_pct", "trajectory", "status",
            "start_date", "end_date", "docstatus", "owner", "employee", "employee_name",
        ],
        order_by="trajectory asc, end_date asc",
    )
    hr = _is_hr()
    for g in goals:
        # Editing follows the creator, not the subject — see alvoraa_goals.permissions.
        g["can_edit"] = int(hr or g["owner"] == frappe.session.user)
        g["is_own"] = int(g["employee"] == emp_id)
        # Nothing above it: an organisational objective rather than a link in
        # someone else's chain.
        g["is_organisational"] = int(not g["parent_goal"] and not g["goal_cascade"])
        g["linked_kpi_count"] = frappe.db.count(
            "KPI", {"individual_goal": g["name"], "status": ["!=", "Cancelled"]}
        )
        g["evidence_count"]   = frappe.db.count("Goal Evidence", {"parent": g["name"]})
        g["pending_evidence"] = frappe.db.count(
            "Goal Evidence", {"parent": g["name"], "validation_status": "Pending"}
        )
        g["start_date"] = str(g["start_date"]) if g["start_date"] else ""
        g["end_date"]   = str(g["end_date"])   if g["end_date"]   else ""
        # Resolve cascade label
        g["cascade_name"] = frappe.db.get_value(
            "Goal Cascade", g["goal_cascade"], "cascade_name"
        ) or g["goal_cascade"] or ""
    return goals


@frappe.whitelist()
def get_active_cascades():
    """Active Goal Cascades available for employees to align to."""
    if not _goals_installed():
        return []
    cascades = frappe.get_all(
        "Goal Cascade",
        filters={"status": "Active"},
        fields=["name", "cascade_name", "unit", "period_start", "period_end",
                "company_target", "description"],
        order_by="period_end asc",
    )
    for c in cascades:
        c["period_start"] = str(c["period_start"]) if c["period_start"] else ""
        c["period_end"]   = str(c["period_end"])   if c["period_end"]   else ""
    return cascades


# ── Cascade alignment: the goals an employee may parent their own goal to ──

# Guards a reports_to cycle (A reports to B reports to A), which would otherwise
# spin forever, and keeps a pathological org chart from producing a huge list.
MAX_CHAIN_DEPTH = 10

# Org-tree walks live in alvoraa_goals so the permission hooks and the portal
# agree on what "subordinate" means.
from alvoraa_goals.permissions import (  # noqa: E402
    descendants as _descendants,
    manager_chain as _manager_chain,
    manageable_employees as _manageable_employees,
)


def _alignable_goal_ids(employee_id):
    """Set of Individual Goal ids this employee is allowed to align under."""
    return {g["name"] for g in _chain_goals(employee_id)}


def _require_manages(employee_id):
    """Caller must be this employee, or somewhere above them in the tree."""
    if _is_hr():
        return
    me = _require_employee()
    if employee_id != me and employee_id not in _descendants(me):
        frappe.throw(
            "You can only do this for yourself or someone who reports to you.",
            frappe.PermissionError,
        )


def _is_hr(user=None):
    from alvoraa_goals.permissions import FULL_ACCESS_ROLES
    return bool(FULL_ACCESS_ROLES.intersection(frappe.get_roles(user or frappe.session.user)))


@frappe.whitelist()
def get_manageable_employees():
    """Employees the caller may raise goals and KPIs for: self plus subtree."""
    if _is_hr():
        rows = frappe.get_all(
            "Employee", filters={"status": "Active"},
            fields=["name", "employee_name", "designation"], order_by="employee_name",
        )
    else:
        allowed = _manageable_employees()
        rows = frappe.get_all(
            "Employee", filters={"name": ["in", allowed or [""]]},
            fields=["name", "employee_name", "designation"], order_by="employee_name",
            ignore_permissions=True,
        )
    me = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
    for r in rows:
        r["is_self"] = int(r["name"] == me)
    return rows


def _chain_goals(employee_id):
    """Active goals owned by everyone up the employee's reporting line.

    Deliberately read with ignore_permissions and a narrow field list. Row-level
    scoping (alvoraa_goals.permissions) restricts an employee to their own rows,
    which is right for browsing but would hide exactly the goals they must align
    to. Alignment needs the goal's *definition* — what it is and what it targets
    — so progress, evidence and ratings are not returned here.
    """
    chain = _manager_chain(employee_id)
    if not chain:
        return []

    goals = frappe.get_all(
        "Individual Goal",
        filters={
            "employee": ["in", chain],
            "status": ["in", ["Active", "Completed"]],
            "docstatus": ["!=", 2],
        },
        fields=["name", "goal_name", "employee", "employee_name", "goal_cascade",
                "target_value", "unit", "start_date", "end_date"],
        ignore_permissions=True,
    )

    depth_of = {emp: i + 1 for i, emp in enumerate(chain)}
    for g in goals:
        g["depth"] = depth_of.get(g["employee"], 99)
        g["start_date"] = str(g["start_date"]) if g["start_date"] else ""
        g["end_date"] = str(g["end_date"]) if g["end_date"] else ""
    goals.sort(key=lambda g: (-g["depth"], g["goal_name"] or ""))
    return goals


@frappe.whitelist()
def get_alignment_options():
    """What an employee can align a new goal to, ordered top of the org down.

    Two kinds of option:
      - the company's active Goal Cascades (the top of every tree), and
      - the active goals of each manager up this employee's reporting line,
        so an individual goal rolls up through its actual chain of command.
    """
    emp_id = _require_employee()
    if not _goals_installed():
        return {"options": [], "chain": []}

    options = []
    for c in get_active_cascades():
        options.append({
            "type":         "cascade",
            "value":        c["name"],
            "cascade":      c["name"],
            "parent_goal":  "",
            "label":        c["cascade_name"],
            "level":        "Company objective",
            "unit":         c["unit"] or "",
            "target":       flt(c["company_target"]),
            "period_start": c["period_start"],
            "period_end":   c["period_end"],
        })

    for g in _chain_goals(emp_id):
        relation = "Your manager" if g["depth"] == 1 else f"{g['depth']} levels up"
        options.append({
            "type":         "goal",
            "value":        g["name"],
            "cascade":      g["goal_cascade"] or "",
            "parent_goal":  g["name"],
            "label":        g["goal_name"],
            "level":        f"{relation} · {g['employee_name'] or g['employee']}",
            "unit":         g["unit"] or "",
            "target":       flt(g["target_value"]),
            "period_start": g["start_date"],
            "period_end":   g["end_date"],
        })

    # Not every goal is derived from one above it. The company owner's objective
    # is where a cascade starts, so "aligned to nothing" has to be a real,
    # selectable answer rather than something you work around.
    options.append({
        "type":         "none",
        "value":        "__none__",
        "cascade":      "",
        "parent_goal":  "",
        "label":        "Organisational objective — this one is the source",
        "level":        "Not cascaded",
        "unit":         "",
        "target":       0,
        "period_start": "",
        "period_end":   "",
    })

    chain = [
        frappe.db.get_value("Employee", e, "employee_name") or e
        for e in _manager_chain(emp_id)
    ]
    return {"options": options, "chain": chain}


@frappe.whitelist()
def create_goal(goal_name, target_value, start_date, end_date, cascade_id=None,
                parent_goal=None, employee=None, unit=None,
                goal_type="Business", company_value=None, is_extra_initiative=0,
                appraisal_cycle=None):
    """Create an Individual Goal for yourself or for one of your subordinates.

    Alignment is optional. Not every goal is derived from one above it — the
    company owner's objective is the source of the cascade, not a link in it, so
    a goal with neither a parent nor a cascade is a valid organisational goal.

    When `parent_goal` is given it must belong to someone on the *subject*
    employee's reporting line; the chain is re-derived server-side rather than
    trusted from the client, so a crafted request cannot attach a goal under an
    arbitrary colleague's.
    """
    me = _require_employee()
    if not _goals_installed():
        frappe.throw("Goals module is not installed on this site.")

    emp_id = employee or me
    if emp_id != me:
        _require_manages(emp_id)

    if parent_goal:
        if parent_goal not in _alignable_goal_ids(emp_id):
            frappe.throw(
                "You can only align a goal to one held by someone in your reporting line.",
                frappe.PermissionError,
            )
        # Inherit the cascade from the parent so the whole chain traces back to
        # the same company objective even if the client sent something else.
        parent_cascade = frappe.db.get_value("Individual Goal", parent_goal, "goal_cascade")
        if parent_cascade:
            cascade_id = parent_cascade

    if cascade_id:
        cascade = frappe.get_doc("Goal Cascade", cascade_id)
        if cascade.status != "Active":
            frappe.throw(f"Goal Cascade '{cascade.cascade_name}' is not active.")
        unit = unit or cascade.unit

    goal = frappe.new_doc("Individual Goal")
    goal.employee    = emp_id
    goal.goal_name   = goal_name
    goal.goal_cascade = cascade_id or None
    goal.parent_goal = parent_goal or None
    goal.unit        = unit or ""
    goal.target_value = flt(target_value)
    goal.start_date  = start_date
    goal.end_date    = end_date
    goal.status      = "Active"
    goal.goal_type   = goal_type or "Business"
    goal.company_value = company_value or None
    goal.is_extra_initiative = int(is_extra_initiative or 0)
    if appraisal_cycle and frappe.db.exists("Appraisal Cycle", appraisal_cycle):
        goal.appraisal_cycle = appraisal_cycle
    goal.insert()
    frappe.db.commit()

    return {
        "name":            goal.name,
        "goal_name":       goal.goal_name,
        "employee":        goal.employee,
        "status":          goal.status,
        "parent_goal":     goal.parent_goal or "",
        "goal_cascade":    goal.goal_cascade or "",
        "is_organisational": int(not goal.parent_goal and not goal.goal_cascade),
        "message":         "Goal created successfully.",
    }


def _require_can_edit(doc, what):
    """Editing and deleting are the creator's right, plus HR's.

    Being someone's manager lets you raise a goal for them; it does not let you
    rewrite one they wrote for themselves.
    """
    if _is_hr():
        return
    me = _require_employee()
    if doc.employee != me and doc.employee not in _descendants(me):
        frappe.throw(
            f"That {what} belongs to someone outside your team.", frappe.PermissionError
        )
    if doc.owner != frappe.session.user:
        frappe.throw(
            f"Only whoever created this {what} — or HR — can change it.",
            frappe.PermissionError,
        )


@frappe.whitelist()
def update_goal(goal_id, goal_name=None, target_value=None, start_date=None,
                end_date=None, status=None, parent_goal=None,
                goal_type=None, company_value=None, is_extra_initiative=None):
    """Revise a goal you created, for yourself or a subordinate."""
    goal = frappe.get_doc("Individual Goal", goal_id)
    _require_can_edit(goal, "goal")

    if goal.docstatus == 1:
        frappe.throw("This goal is submitted and can no longer be edited.")

    if goal_name is not None:
        goal.goal_name = goal_name
    if target_value is not None:
        goal.target_value = flt(target_value)
    if start_date:
        goal.start_date = start_date
    if end_date:
        goal.end_date = end_date
    if status:
        goal.status = status
    if parent_goal is not None:
        if parent_goal and parent_goal not in _alignable_goal_ids(goal.employee):
            frappe.throw(
                "You can only align a goal to one held by someone in that employee's "
                "reporting line.",
                frappe.PermissionError,
            )
        if parent_goal == goal.name:
            frappe.throw("A goal cannot roll up into itself.")
        # Clearing the parent is legitimate: it turns the goal back into a
        # standalone organisational objective.
        goal.parent_goal = parent_goal or None
        if parent_goal:
            parent_cascade = frappe.db.get_value("Individual Goal", parent_goal, "goal_cascade")
            if parent_cascade:
                goal.goal_cascade = parent_cascade

    if goal_type is not None:
        goal.goal_type = goal_type
    if company_value is not None:
        goal.company_value = company_value or None
    if is_extra_initiative is not None:
        goal.is_extra_initiative = int(is_extra_initiative or 0)

    goal.save()
    frappe.db.commit()
    return {"name": goal.name, "message": "Goal updated."}


@frappe.whitelist()
def delete_goal(goal_id):
    """Delete a goal you created. Refuses while anything still rolls into it."""
    goal = frappe.get_doc("Individual Goal", goal_id)
    _require_can_edit(goal, "goal")

    children = frappe.get_all(
        "Individual Goal", filters={"parent_goal": goal_id}, pluck="goal_name",
        ignore_permissions=True,
    )
    if children:
        frappe.throw(
            "Other goals still roll up into this one: " + ", ".join(children[:5]) +
            (" …" if len(children) > 5 else "") +
            ". Re-align or remove them first."
        )

    linked_kpis = frappe.get_all(
        "KPI", filters={"individual_goal": goal_id}, pluck="kpi_name",
        ignore_permissions=True,
    )
    if linked_kpis:
        frappe.throw(
            "KPIs are still linked to this objective: " + ", ".join(linked_kpis[:5]) +
            (" …" if len(linked_kpis) > 5 else "") + ". Unlink them first."
        )

    name = goal.goal_name
    frappe.delete_doc("Individual Goal", goal_id)
    frappe.db.commit()
    return {"message": f"Goal '{name}' deleted."}


@frappe.whitelist()
def get_linkable_objectives(employee=None):
    """Objectives a KPI for `employee` may hang off.

    That is the employee's own goals plus every goal held above them, which is
    what lets one objective gather KPIs from several people down its branch.
    """
    me = _require_employee()
    emp_id = employee or me
    if emp_id != me:
        _require_manages(emp_id)

    own = frappe.get_all(
        "Individual Goal",
        filters={"employee": emp_id, "status": ["in", ["Active", "Completed"]],
                 "docstatus": ["!=", 2]},
        fields=["name", "goal_name", "employee", "employee_name", "target_value",
                "unit", "goal_cascade"],
        ignore_permissions=True,
    )
    for g in own:
        g["level"] = "Own objective"

    upward = _chain_goals(emp_id)
    for g in upward:
        relation = "Manager" if g["depth"] == 1 else f"{g['depth']} levels up"
        g["level"] = f"{relation} · {g['employee_name'] or g['employee']}"

    return own + upward


@frappe.whitelist()
def get_goal_detail(goal_id):
    """Full goal record with evidence list. Employee can only see own goals."""
    emp_id = _require_employee()
    goal = frappe.get_doc("Individual Goal", goal_id)

    # Viewable if it is yours, one of your subordinates', or one you may align
    # to (i.e. held above you) — the last case is why a plain "is it mine"
    # check is not enough now that goals cascade.
    if not _is_hr():
        viewable = set(_manageable_employees()) | set(_manager_chain(emp_id))
        if goal.employee not in viewable:
            frappe.throw(
                "That goal belongs to someone outside your reporting line.",
                frappe.PermissionError,
            )

    cascade_name = (
        frappe.db.get_value("Goal Cascade", goal.goal_cascade, "cascade_name")
        or goal.goal_cascade or ""
    )

    # Everything that rolls into this objective. One goal deliberately gathers
    # KPIs from several people down the owner's branch, so these are grouped by
    # employee rather than listed flat.
    linked = frappe.get_all(
        "KPI",
        filters={"individual_goal": goal.name, "status": ["!=", "Cancelled"]},
        fields=["name", "kpi_name", "employee", "employee_name", "unit",
                "target_value", "actual_value", "attainment_pct", "weightage",
                "appraisal_cycle", "status"],
        order_by="employee_name asc, kpi_name asc",
        ignore_permissions=True,
    )
    contributors = {}
    for k in linked:
        contributors.setdefault(k["employee"], {
            "employee": k["employee"],
            "employee_name": k["employee_name"] or k["employee"],
            "kpis": [],
        })["kpis"].append(k)
    for c in contributors.values():
        c["avg_attainment"] = round(
            sum(flt(k["attainment_pct"]) for k in c["kpis"]) / len(c["kpis"]), 1
        )

    child_goals = frappe.get_all(
        "Individual Goal",
        filters={"parent_goal": goal.name, "docstatus": ["!=", 2]},
        fields=["name", "goal_name", "employee_name", "progress_pct", "status"],
        ignore_permissions=True,
    )

    created_by_name = (
        frappe.db.get_value("User", goal.owner, "full_name") or goal.owner or ""
    ) if goal.owner else ""

    return {
        "name":            goal.name,
        "goal_name":       goal.goal_name,
        "description":     getattr(goal, "description", "") or "",
        "employee":        goal.employee,
        "employee_name":   goal.employee_name or goal.employee,
        "owner":           goal.owner or "",
        "created_by_name": created_by_name,
        "goal_cascade":    goal.goal_cascade,
        "cascade_name":    cascade_name,
        "parent_goal":     goal.parent_goal or "",
        "target_value":    flt(goal.target_value),
        "unit":            goal.unit or "",
        "actual_progress": flt(goal.actual_progress),
        "progress_pct":    flt(goal.progress_pct),
        "trajectory":      goal.trajectory or "Not Started",
        "status":          goal.status,
        "start_date":      str(goal.start_date) if goal.start_date else "",
        "end_date":        str(goal.end_date)   if goal.end_date   else "",
        "docstatus":       goal.docstatus,
        "goal_type":       getattr(goal, "goal_type", "") or "",
        "company_value":   getattr(goal, "company_value", "") or "",
        "can_edit":        int(_is_hr() or goal.owner == frappe.session.user),
        "is_mine":         int(goal.employee == emp_id),
        "is_organisational": int(not goal.parent_goal and not goal.goal_cascade),
        "linked_kpis":     linked,
        "contributors":    sorted(contributors.values(), key=lambda c: c["employee_name"]),
        "child_goals":     child_goals,
        "evidence": [
            {
                "name":                  e.name,
                "evidence_type":         e.evidence_type or "",
                "upload_date":           str(e.upload_date)       if e.upload_date   else "",
                "validation_status":     e.validation_status      or "Pending",
                "extracted_amount":      flt(e.extracted_amount),
                "extracted_order_count": int(e.extracted_order_count or 0),
                "extracted_date":        str(e.extracted_date)    if e.extracted_date else "",
                "rejection_reason":      e.rejection_reason       or "",
            }
            for e in (goal.evidence_items or [])
        ],
    }


@frappe.whitelist()
def set_goal_progress(goal_id, actual_progress):
    """Allow HR/managers to manually override actual_progress on a goal."""
    emp_id = _require_employee()
    goal = frappe.get_doc("Individual Goal", goal_id)
    if not (_is_hr() or goal.owner == frappe.session.user):
        frappe.throw("Not permitted to update this goal", frappe.PermissionError)
    val = flt(actual_progress)
    goal.actual_progress = val
    goal.progress_pct = min((val / flt(goal.target_value)) * 100, 100) if goal.target_value else 0
    goal.flags.ignore_validate = True
    goal.flags.ignore_validate_update_after_submit = True
    goal.save()
    frappe.db.commit()
    from alvoraa_goals.controllers.goal import _update_trajectory, _aggregate_cascade
    _update_trajectory(goal)
    goal.flags.ignore_validate = True
    goal.flags.ignore_validate_update_after_submit = True
    goal.save()
    frappe.db.commit()
    _aggregate_cascade(goal.goal_cascade)
    return {"actual_progress": goal.actual_progress, "progress_pct": goal.progress_pct}


@frappe.whitelist()
def get_appraisal_data():
    """Active appraisal cycle + the employee's appraisal record."""
    emp_id = _require_employee()
    cycle  = _get_active_cycle()
    if not cycle:
        return {"cycle": None, "appraisal": None}

    ap_list = frappe.get_all(
        "Appraisal",
        filters={"employee": emp_id, "appraisal_cycle": cycle["name"], "docstatus": ["!=", 2]},
        fields=["name"],
        limit=1,
    )
    if not ap_list:
        return {"cycle": cycle, "appraisal": None}

    ap = frappe.get_doc("Appraisal", ap_list[0]["name"])

    kras = [
        {
            "kra":             k.kra or "",
            "per_weightage":   flt(k.per_weightage),
            "goal_completion": flt(k.goal_completion),
            "goal_score":      flt(k.goal_score),
        }
        for k in (ap.appraisal_kra or [])
    ]

    self_ratings = [
        {
            "criteria":      str(getattr(r, "criteria", getattr(r, "kra", ""))),
            "per_weightage": flt(getattr(r, "per_weightage", 0)),
            "rating":        flt(getattr(r, "rating", 0)),
        }
        for r in (ap.self_ratings or [])
    ]

    # Appraisals scored from KPIs use HRMS's manual path, which fills `goals`
    # rather than `appraisal_kra`. Return both so the portal can render whichever
    # this appraisal actually uses instead of showing an empty table.
    manual_goals = [
        {
            "kra":           g.kra or "",
            "per_weightage": flt(g.per_weightage),
            "score":         flt(g.score),
            "score_earned":  flt(g.score_earned),
        }
        for g in (ap.goals or [])
    ]

    return {
        "cycle": cycle,
        "appraisal": {
            "name":        ap.name,
            "docstatus":   ap.docstatus,
            "total_score": flt(ap.total_score),
            "final_score": flt(ap.final_score),
            "self_score":  flt(ap.self_score),
            "reflections": ap.reflections or "",
            "kras":        kras,
            "goals":       manual_goals,
            "rate_goals_manually": int(ap.rate_goals_manually or 0),
            "self_ratings": self_ratings,
        },
    }


@frappe.whitelist()
def save_self_assessment(appraisal_id, reflections):
    """Save employee self-reflection text to their appraisal."""
    emp_id = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal_id)
    if ap.employee != emp_id:
        frappe.throw("Not permitted.", frappe.PermissionError)
    if ap.docstatus == 1:
        frappe.throw("Appraisal is already submitted.")
    ap.reflections = reflections
    ap.save()
    frappe.db.commit()
    return {"status": "ok", "message": "Self-assessment saved."}


@frappe.whitelist()
def get_team_goals():
    """Goals summary for all direct reports (managers only)."""
    emp_id = _require_employee()
    if not _is_manager(emp_id):
        frappe.throw("You have no direct reports.", frappe.PermissionError)

    reportees = frappe.get_all(
        "Employee",
        filters={"reports_to": emp_id, "status": "Active"},
        fields=["name", "employee_name", "designation", "image"],
    )
    result = []
    for emp in reportees:
        if _goals_installed():
            g_list = frappe.get_all(
                "Individual Goal",
                filters={"employee": emp["name"], "status": "Active", "docstatus": ["!=", 2]},
                fields=["name", "goal_name", "progress_pct", "trajectory"],
            )
        else:
            g_list = []

        on_track = sum(1 for g in g_list if g.get("trajectory") == "On Track")
        at_risk  = sum(1 for g in g_list if g.get("trajectory") in ("At Risk", "Off Track"))
        avg_pct  = round(sum(flt(g.get("progress_pct") or 0) for g in g_list) / len(g_list), 1) if g_list else 0

        result.append({
            "employee_id":   emp["name"],
            "employee_name": emp["employee_name"],
            "designation":   emp.get("designation") or "",
            "avatar":        emp.get("image") or "",
            "total_goals":   len(g_list),
            "on_track":      on_track,
            "at_risk":       at_risk,
            "avg_progress":  avg_pct,
        })

    result.sort(key=lambda x: x["at_risk"], reverse=True)
    return result


# ── Check-ins ─────────────────────────────────────────────────────────────

@frappe.whitelist()
def create_checkin(goal_id, note, completion_pct="", trajectory=""):
    """Log a check-in (% complete + outlook) on an Individual Goal."""
    emp_id = _require_employee()
    goal = frappe.get_doc("Individual Goal", goal_id)

    if goal.employee != emp_id:
        frappe.throw("You can only check in on your own goals.", frappe.PermissionError)
    if goal.docstatus == 2:
        frappe.throw("Goal is cancelled.")
    if not note:
        frappe.throw("A check-in note is required.")

    entry = frappe.new_doc("Goal Check-In")
    entry.goal = goal_id
    entry.employee = emp_id
    entry.note = note
    entry.checkin_date = today()

    if completion_pct != "":
        entry.completion_pct = min(max(flt(completion_pct), 0), 100)
    if trajectory in ("On Track", "At Risk"):
        entry.trajectory = trajectory

    entry.insert(ignore_permissions=True)

    # Propagate pct and trajectory back to the goal immediately so the tree stays live.
    changed = False
    if completion_pct != "":
        goal.progress_pct = min(max(flt(completion_pct), 0), 100)
        changed = True
    if trajectory in ("On Track", "At Risk"):
        goal.trajectory = trajectory
        changed = True
    if changed:
        goal.flags.ignore_validate = True
        goal.flags.ignore_validate_update_after_submit = True
        goal.save(ignore_permissions=True)

    frappe.db.commit()
    return {"name": entry.name, "message": "Check-in logged."}


@frappe.whitelist()
def get_checkins(goal_id):
    """List all check-ins for a goal, newest first."""
    emp_id = _require_employee()
    goal = frappe.get_doc("Individual Goal", goal_id)

    is_manager = frappe.db.exists(
        "Employee", {"reports_to": emp_id, "name": goal.employee}
    ) is not None

    hr_roles = {"HR Manager", "HR User", "System Manager"}
    is_hr = bool(hr_roles.intersection(frappe.get_roles(frappe.session.user)))

    if goal.employee != emp_id and not is_manager and not is_hr:
        frappe.throw("Not permitted.", frappe.PermissionError)

    rows = frappe.get_all(
        "Goal Check-In",
        filters={"goal": goal_id},
        fields=["name", "checkin_date", "note", "completion_pct", "trajectory"],
        order_by="checkin_date desc, creation desc",
    )
    return [
        {
            "name": r["name"],
            "checkin_date": str(r["checkin_date"]) if r["checkin_date"] else "",
            "note": r["note"] or "",
            "completion_pct": flt(r["completion_pct"]) if r.get("completion_pct") is not None else None,
            "trajectory": r.get("trajectory") or "",
        }
        for r in rows
    ]


# ── Upward feedback ───────────────────────────────────────────────────────

@frappe.whitelist()
def submit_upward_feedback(about_employee, cycle, rating, comments=""):
    """Employee submits upward feedback about their manager."""
    emp_id = _require_employee()

    # Caller must report to the target employee (using effective manager so
    # employees without a reports_to still have HR as their effective manager)
    from alvoraa_goals.permissions import get_effective_manager
    my_manager = get_effective_manager(emp_id)
    if my_manager != about_employee:
        frappe.throw(
            "Upward feedback can only be submitted about your direct manager.",
            frappe.PermissionError,
        )

    rating = flt(rating)
    if rating < 0 or rating > 5:
        frappe.throw("Rating must be between 0 and 5.")

    if not frappe.db.exists("Appraisal Cycle", cycle):
        frappe.throw(f"Cycle '{cycle}' not found.")

    fb = frappe.new_doc("Upward Feedback")
    fb.from_employee = emp_id
    fb.about_employee = about_employee
    fb.appraisal_cycle = cycle
    fb.rating = rating
    fb.comments = comments
    fb.submitted_on = today()
    fb.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": fb.name, "message": "Feedback submitted. Thank you."}


@frappe.whitelist()
def get_upward_feedback(cycle, employee=None):
    """Return aggregated upward feedback received about a manager.

    Managers see their own; HR sees everyone's. Individual rater identities
    are always anonymised.
    """
    emp_id = _require_employee()
    hr_roles = {"HR Manager", "HR User", "System Manager"}
    is_hr = bool(hr_roles.intersection(frappe.get_roles(frappe.session.user)))

    target = employee or emp_id
    if target != emp_id and not is_hr:
        frappe.throw("Not permitted.", frappe.PermissionError)

    rows = frappe.get_all(
        "Upward Feedback",
        filters={"about_employee": target, "appraisal_cycle": cycle},
        fields=["rating", "comments", "submitted_on"],
        order_by="submitted_on desc",
        ignore_permissions=True,
    )
    if not rows:
        return {"count": 0, "avg_rating": None, "comments": []}

    avg = flt(sum(flt(r["rating"]) for r in rows) / len(rows), 2)
    return {
        "count": len(rows),
        "avg_rating": avg,
        "comments": [r["comments"] for r in rows if r.get("comments")],
    }


# ── Progress update log (Individual Goal) ────────────────────────────────

@frappe.whitelist()
def submit_goal_update(goal_id, new_value, note="", evidence_url=None):
    """Log a progress update on an Individual Goal — creates an approval-pending entry."""
    emp_id = _require_employee()
    goal   = frappe.get_doc("Individual Goal", goal_id)

    if goal.employee != emp_id and not _is_hr():
        frappe.throw("You can only update your own goals.", frappe.PermissionError)
    if goal.docstatus == 2:
        frappe.throw("Goal is cancelled.")

    ev_missing = 1 if not evidence_url else 0
    val = flt(new_value)

    row = goal.append("progress_updates", {
        "log_date":         today(),
        "value":            val,
        "note":             note,
        "logged_by":        frappe.session.user,
        "evidence_file":    evidence_url or None,
        "evidence_missing": ev_missing,
        "approval_status":  "Pending",
    })

    # Optimistically roll up progress so the dashboard stays live.
    goal.actual_progress = val
    if flt(goal.target_value):
        goal.progress_pct = min(flt(val / flt(goal.target_value) * 100, 2), 100)
    goal.flags.ignore_validate                  = True
    goal.flags.ignore_validate_update_after_submit = True
    goal.save(ignore_permissions=True)
    frappe.db.commit()

    _notify_manager_of_goal_update(goal.name, goal.goal_name, goal.employee, row.name)

    return {
        "name":            goal.name,
        "row_name":        row.name,
        "actual_progress": goal.actual_progress,
        "progress_pct":    goal.progress_pct,
        "evidence_missing": ev_missing,
        "message":         "Progress update submitted — awaiting manager approval.",
    }


def _notify_manager_of_goal_update(goal_id, goal_name, employee_id, row_name):
    try:
        reports_to   = frappe.db.get_value("Employee", employee_id, "reports_to")
        if not reports_to:
            return
        manager_user = frappe.db.get_value("Employee", reports_to, "user_id")
        if not manager_user:
            return
        emp_name = frappe.db.get_value("Employee", employee_id, "employee_name") or employee_id
        notif = frappe.new_doc("Notification Log")
        notif.for_user      = manager_user
        notif.type          = "Alert"
        notif.document_type = "Individual Goal"
        notif.document_name = goal_id
        notif.subject       = f"{emp_name} posted an update on goal \"{goal_name}\""
        notif.email_content = (
            f"<p>{emp_name} submitted a progress update requiring your approval.</p>"
        )
        notif.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        pass


@frappe.whitelist()
def approve_goal_update(goal_id, row_name, action, comment=""):
    """Manager approves or rejects a specific Goal Progress Update row."""
    _require_employee()
    if action not in ("Approved", "Rejected"):
        frappe.throw("action must be 'Approved' or 'Rejected'.")

    goal = frappe.get_doc("Individual Goal", goal_id)
    goal_mgr = frappe.db.get_value("Employee", goal.employee, "reports_to")
    my_emp   = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
    if not (_is_hr() or my_emp == goal_mgr):
        frappe.throw("Only this employee's manager or HR can approve updates.",
                     frappe.PermissionError)

    for row in (goal.progress_updates or []):
        if row.name == row_name:
            row.approval_status  = action
            row.approval_comment = comment
            row.approved_by      = frappe.session.user
            row.approved_on      = frappe.utils.now()
            break
    else:
        frappe.throw(f"Progress update row '{row_name}' not found on goal {goal_id}.")

    goal.flags.ignore_validate                  = True
    goal.flags.ignore_validate_update_after_submit = True
    goal.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": f"Update {action.lower()}."}


@frappe.whitelist()
def get_goal_update_log(goal_id):
    """Return the progress_updates for a goal, newest first."""
    emp_id = _require_employee()
    goal   = frappe.get_doc("Individual Goal", goal_id)

    goal_mgr = frappe.db.get_value("Employee", goal.employee, "reports_to")
    if not (_is_hr() or goal.employee == emp_id or emp_id == goal_mgr):
        frappe.throw("Not permitted.", frappe.PermissionError)

    rows = sorted(
        goal.progress_updates or [],
        key=lambda r: (str(r.log_date or ""), str(r.creation or "")),
        reverse=True,
    )
    result = []
    for r in rows:
        by_name  = frappe.db.get_value("User", r.logged_by,  "full_name") or r.logged_by or ""
        apr_name = frappe.db.get_value("User", r.approved_by, "full_name") or r.approved_by or "" if r.approved_by else ""
        result.append({
            "name":             r.name,
            "log_date":         str(r.log_date)   if r.log_date   else "",
            "value":            flt(r.value),
            "note":             r.note             or "",
            "logged_by":        r.logged_by        or "",
            "logged_by_name":   by_name,
            "evidence_file":    r.evidence_file    or "",
            "evidence_missing": int(r.evidence_missing or 0),
            "approval_status":  r.approval_status  or "Pending",
            "approval_comment": r.approval_comment or "",
            "approved_by":      r.approved_by      or "",
            "approved_by_name": apr_name,
            "approved_on":      str(r.approved_on) if r.approved_on else "",
        })
    return result


@frappe.whitelist()
def get_pending_approvals():
    """Return all pending-approval updates across the manager's direct reports."""
    emp_id = _require_employee()
    is_mgr = _is_manager(emp_id)
    is_hr  = _is_hr()

    if not is_mgr and not is_hr:
        return {"kpi_updates": [], "goal_updates": [], "total": 0}

    if is_hr:
        all_employees = frappe.get_all(
            "Employee", filters={"status": "Active"}, pluck="name"
        )
    else:
        all_employees = frappe.get_all(
            "Employee",
            filters={"reports_to": emp_id, "status": "Active"},
            pluck="name",
        )

    kpi_updates  = []
    goal_updates = []

    for emp in all_employees:
        emp_name = frappe.db.get_value("Employee", emp, "employee_name") or emp

        # KPI progress-log rows pending approval
        for kpi in frappe.get_all(
            "KPI",
            filters={"employee": emp, "status": ["!=", "Cancelled"]},
            fields=["name", "kpi_name"],
        ):
            doc = frappe.get_doc("KPI", kpi["name"])
            for row in (doc.progress_log or []):
                if (row.approval_status or "Pending") == "Pending":
                    by_name = frappe.db.get_value("User", row.logged_by, "full_name") or row.logged_by or ""
                    kpi_updates.append({
                        "kpi":              kpi["name"],
                        "kpi_name":         kpi["kpi_name"],
                        "row_name":         row.name,
                        "employee":         emp,
                        "employee_name":    emp_name,
                        "log_date":         str(row.log_date)  if row.log_date else "",
                        "value":            flt(row.value),
                        "note":             row.note           or "",
                        "logged_by_name":   by_name,
                        "evidence_file":    row.evidence_file  or "",
                        "evidence_missing": int(row.evidence_missing or 0),
                    })

        # Goal progress-update rows pending approval
        for goal in frappe.get_all(
            "Individual Goal",
            filters={"employee": emp, "status": ["!=", "Cancelled"], "docstatus": ["!=", 2]},
            fields=["name", "goal_name"],
        ):
            gdoc = frappe.get_doc("Individual Goal", goal["name"])
            for row in (gdoc.progress_updates or []):
                if (row.approval_status or "Pending") == "Pending":
                    by_name = frappe.db.get_value("User", row.logged_by, "full_name") or row.logged_by or ""
                    goal_updates.append({
                        "goal":             goal["name"],
                        "goal_name":        goal["goal_name"],
                        "row_name":         row.name,
                        "employee":         emp,
                        "employee_name":    emp_name,
                        "log_date":         str(row.log_date)  if row.log_date else "",
                        "value":            flt(row.value),
                        "note":             row.note           or "",
                        "logged_by_name":   by_name,
                        "evidence_file":    row.evidence_file  or "",
                        "evidence_missing": int(row.evidence_missing or 0),
                    })

    return {
        "kpi_updates":  kpi_updates,
        "goal_updates": goal_updates,
        "total":        len(kpi_updates) + len(goal_updates),
    }
