"""Performance management — KPIs, goals and appraisals, end to end in the portal.

Method path: grace_vendor_portal.performance_api.*

Covers the whole review loop without anyone touching the Frappe desk:

    HR       create cycle -> assign KPIs -> generate appraisals -> complete cycle
    Employee log KPI progress -> self-rate -> write reflections
    Manager  rate reports' KPIs -> sync scores -> submit appraisal

Tenant isolation: every call runs against the site resolved from the request
Host, and each site is a separate database, so no query here can observe another
tenant's rows. Within a tenant, callers are narrowed to what their role allows —
see grace_goals.permissions for the row-level rules applied to KPI queries.
"""

import frappe
from frappe.utils import flt, today, getdate
from grace_goals.permissions import get_effective_manager

from grace_goals.controllers.kpi import MAX_RATING, TOTAL_WEIGHTAGE, rating_from_attainment

HR_ROLES = frozenset({"HR Manager", "HR User", "System Manager"})


# ══════════════════════════════════════════════════════════════════════════
# Guards
# ══════════════════════════════════════════════════════════════════════════

def _employee_id(user=None):
    user = user or frappe.session.user
    if user == "Guest":
        frappe.throw("Please log in.", frappe.PermissionError)
    return frappe.db.get_value("Employee", {"user_id": user}, "name")


def _require_employee():
    emp = _employee_id()
    if not emp:
        frappe.throw("No Employee record is linked to your account.")
    return emp


def _is_hr(user=None):
    return bool(HR_ROLES.intersection(frappe.get_roles(user or frappe.session.user)))


def _require_hr():
    if not _is_hr():
        frappe.throw("This action requires an HR role.", frappe.PermissionError)


def _reports_of(employee_id):
    """Direct reports — used for the appraisal review relationship."""
    return frappe.get_all(
        "Employee",
        filters={"reports_to": employee_id, "status": "Active"},
        pluck="name",
    )


def _subordinates(employee_id):
    """Everyone below this employee at any depth."""
    from grace_goals.permissions import descendants
    return descendants(employee_id)


def _require_manages(employee_id):
    """Caller must be this employee or somewhere above them, or HR."""
    if _is_hr():
        return
    me = _require_employee()
    if employee_id != me and employee_id not in _subordinates(me):
        frappe.throw(
            "You can only do this for yourself or someone who reports to you.",
            frappe.PermissionError,
        )


def _require_can_edit_kpi(doc):
    """Revising or deleting a KPI is the creator's right, plus HR's."""
    if _is_hr():
        return
    me = _require_employee()
    if doc.employee != me and doc.employee not in _subordinates(me):
        frappe.throw("That KPI belongs to someone outside your team.", frappe.PermissionError)
    if doc.owner != frappe.session.user:
        frappe.throw(
            "Only whoever created this KPI — or HR — can change it.",
            frappe.PermissionError,
        )


def _require_can_review(kpi_employee):
    """Caller must be the employee's manager, or HR."""
    if _is_hr():
        return
    me = _require_employee()
    if kpi_employee not in _reports_of(me):
        frappe.throw(
            "You can only review KPIs for your own direct reports.", frappe.PermissionError
        )


def _require_owns(kpi_employee):
    """Caller must be the employee the record belongs to."""
    if kpi_employee != _require_employee():
        frappe.throw("You can only update your own KPIs.", frappe.PermissionError)


def _default_company():
    company = frappe.defaults.get_user_default("Company")
    if company:
        return company
    companies = frappe.get_all("Company", pluck="name", limit=1)
    if not companies:
        frappe.throw("No Company exists on this site. Create one before running a review cycle.")
    return companies[0]


def _serialise_dates(row, *fields):
    for f in fields:
        row[f] = str(row[f]) if row.get(f) else ""
    return row


def _plain(message):
    """Strip the HTML Frappe embeds in exception messages, for portal display."""
    import re
    return re.sub(r"<[^>]+>", "", message or "").strip()


def _existing_appraisal(employee, cycle, start_date, end_date):
    """Find an appraisal that blocks creating one for this employee and cycle.

    HRMS's own validate_duplicate rejects not only a second appraisal in the
    same cycle but any whose period overlaps, so checking the cycle alone would
    let generation fail later with an opaque error.
    """
    rows = frappe.get_all(
        "Appraisal",
        filters={"employee": employee, "docstatus": ["!=", 2]},
        fields=["name", "appraisal_cycle", "start_date", "end_date"],
    )
    for r in rows:
        if r["appraisal_cycle"] == cycle:
            return r
        if r["start_date"] and r["end_date"] and start_date and end_date:
            if getdate(r["start_date"]) <= getdate(end_date) and \
               getdate(r["end_date"]) >= getdate(start_date):
                return r
    return None


# ══════════════════════════════════════════════════════════════════════════
# Shared context
# ══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_performance_context():
    """Boot call for the performance UI: who am I, what can I do, which cycles exist."""
    emp_id = _employee_id()
    reports = _reports_of(emp_id) if emp_id else []

    emp = {}
    if emp_id:
        emp = frappe.db.get_value(
            "Employee", emp_id,
            ["employee_name", "designation", "department"],
            as_dict=True,
        ) or {}

    cycles = [
        _serialise_dates(c, "start_date", "end_date")
        for c in frappe.get_all(
            "Appraisal Cycle",
            fields=["name", "cycle_name", "status", "start_date", "end_date"],
            order_by="start_date desc",
        )
    ]
    active = next((c for c in cycles if c["status"] == "In Progress"), None)
    if not active:
        active = next((c for c in cycles if c["status"] != "Completed"), None)

    return {
        "employee_id":   emp_id or "",
        "employee_name": emp.get("employee_name", ""),
        "designation":   emp.get("designation", ""),
        "department":    emp.get("department", ""),
        "is_hr":         _is_hr(),
        "is_manager":    bool(reports),
        "report_count":  len(reports),
        "cycles":        cycles,
        "active_cycle":  active,
        "max_rating":    MAX_RATING,
        "tenant_name":   frappe.conf.get("tenant_name", "") or "",
    }


# ══════════════════════════════════════════════════════════════════════════
# Employee self-service
# ══════════════════════════════════════════════════════════════════════════

KPI_FIELDS = [
    "name", "kpi_name", "employee", "employee_name", "appraisal_cycle", "category",
    "status", "unit", "direction", "baseline_value", "target_value", "actual_value",
    "attainment_pct", "weightage", "period_start", "period_end", "goal_cascade",
    "individual_goal", "self_rating", "self_comment", "manager_rating",
    "manager_comment", "potential_rating", "potential_comment",
    "company_value", "is_extra_initiative", "description", "owner",
]


def _decorate_kpis(rows):
    """Add the objective label and whether this caller may revise each row."""
    hr = _is_hr()
    user = frappe.session.user
    goal_names = {}
    for r in rows:
        r["can_edit"] = int(hr or r.get("owner") == user)
        gid = r.get("individual_goal")
        if gid and gid not in goal_names:
            goal_names[gid] = frappe.db.get_value("Individual Goal", gid, "goal_name") or gid
        r["objective"] = goal_names.get(gid, "")
    return rows


def _kpi_rows(filters):
    """Read KPIs *through* the permission layer.

    frappe.get_all is get_list with ignore_permissions=True — it skips both the
    doctype permission check and the row-level conditions in
    grace_goals.permissions. Using get_list means the explicit filters below and
    the scoping hook both have to agree before a row comes back, so a mistake in
    one is still caught by the other.
    """
    rows = frappe.get_list("KPI", filters=filters, fields=KPI_FIELDS, order_by="kpi_name asc")
    for r in rows:
        _serialise_dates(r, "period_start", "period_end")
    return _decorate_kpis(rows)


@frappe.whitelist()
def get_my_kpis(cycle=None, include_team=0):
    """The signed-in employee's KPIs, newest cycle first unless one is named.

    With include_team, also returns KPIs raised for anyone in their subtree.
    Weightage totals still describe the caller's own KPIs — that is the number
    that has to reach 100% for their appraisal to score.
    """
    emp_id = _require_employee()
    subjects = [emp_id]
    if int(include_team or 0):
        subjects = [emp_id, *_subordinates(emp_id)]

    filters = {"employee": ["in", subjects]}
    if cycle:
        filters["appraisal_cycle"] = cycle

    rows = _kpi_rows(filters)
    own = [r for r in rows if r["employee"] == emp_id and r["status"] != "Cancelled"]
    total_weightage = sum(flt(r["weightage"]) for r in own)
    return {
        "kpis": rows,
        "employee_id": emp_id,
        "total_weightage": flt(total_weightage, 2),
        "weightage_complete": flt(total_weightage, 2) == TOTAL_WEIGHTAGE,
    }


@frappe.whitelist()
def log_kpi_progress(kpi, value, note="", evidence_url=None):
    """Append a dated reading, set approval pending, and notify the manager."""
    doc = frappe.get_doc("KPI", kpi)
    _require_owns(doc.employee)

    if doc.status in ("Cancelled",):
        frappe.throw("This KPI is cancelled and no longer accepts progress updates.")

    ev_missing = 1 if not evidence_url else 0
    row = doc.append("progress_log", {
        "log_date":        today(),
        "value":           flt(value),
        "note":            note,
        "logged_by":       frappe.session.user,
        "evidence_file":   evidence_url or None,
        "evidence_missing": ev_missing,
        "approval_status": "Pending",
    })
    doc.actual_value = flt(value)
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    _notify_manager_of_kpi_update(doc, row.name)

    return {
        "name":            doc.name,
        "row_name":        row.name,
        "actual_value":    flt(doc.actual_value),
        "attainment_pct":  flt(doc.attainment_pct),
        "status":          doc.status,
        "evidence_missing": ev_missing,
        "message":         "Progress logged — awaiting manager approval.",
    }


def _notify_manager_of_kpi_update(kpi_doc, row_name):
    """Create a Notification Log entry for the KPI owner's manager."""
    try:
        reports_to = frappe.db.get_value("Employee", kpi_doc.employee, "reports_to")
        if not reports_to:
            return
        manager_user = frappe.db.get_value("Employee", reports_to, "user_id")
        if not manager_user:
            return
        emp_name = kpi_doc.employee_name or kpi_doc.employee
        notif = frappe.new_doc("Notification Log")
        notif.for_user    = manager_user
        notif.type        = "Alert"
        notif.document_type = "KPI"
        notif.document_name = kpi_doc.name
        notif.subject     = f"{emp_name} posted a KPI update on \"{kpi_doc.kpi_name}\""
        notif.email_content = (
            f"<p>{emp_name} submitted a progress update requiring your approval.</p>"
        )
        notif.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        pass  # never block the main save


@frappe.whitelist()
def approve_kpi_update(kpi, row_name, action, comment=""):
    """Manager approves or rejects a specific KPI progress-log row."""
    _require_employee()
    if action not in ("Approved", "Rejected"):
        frappe.throw("action must be 'Approved' or 'Rejected'.")

    doc = frappe.get_doc("KPI", kpi)
    # Gate: only the employee's direct manager or HR may approve.
    kpi_emp_mgr = frappe.db.get_value("Employee", doc.employee, "reports_to")
    my_emp      = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
    if not (_is_hr() or my_emp == kpi_emp_mgr):
        frappe.throw("Only this employee's manager or HR can approve updates.",
                     frappe.PermissionError)

    for row in (doc.progress_log or []):
        if row.name == row_name:
            row.approval_status  = action
            row.approval_comment = comment
            row.approved_by      = frappe.session.user
            row.approved_on      = frappe.utils.now()
            break
    else:
        frappe.throw(f"Progress log row '{row_name}' not found on KPI {kpi}.")

    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": f"Update {action.lower()}."}


@frappe.whitelist()
def get_kpi_update_log(kpi):
    """Return the full progress_log for a KPI, newest first."""
    doc = frappe.get_doc("KPI", kpi)
    my_emp = _require_employee()

    kpi_mgr = frappe.db.get_value("Employee", doc.employee, "reports_to")
    if not (_is_hr() or doc.employee == my_emp or my_emp == kpi_mgr):
        frappe.throw("Not permitted.", frappe.PermissionError)

    rows = sorted(
        doc.progress_log or [],
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
def save_kpi_self_review(kpi, rating, comment=""):
    """Employee's own 0-5 rating for one of their KPIs."""
    doc = frappe.get_doc("KPI", kpi)
    _require_owns(doc.employee)

    rating = flt(rating)
    if rating < 0 or rating > MAX_RATING:
        frappe.throw(f"Rating must be between 0 and {int(MAX_RATING)}.")

    doc.self_rating = rating
    doc.self_comment = comment
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name, "self_rating": rating, "message": "Self review saved."}


@frappe.whitelist()
def get_my_appraisal(cycle=None):
    """The signed-in employee's appraisal for a cycle, with KPI-derived goal rows."""
    emp_id = _require_employee()
    ctx = get_performance_context()
    cycle = cycle or (ctx["active_cycle"] or {}).get("name")
    if not cycle:
        return {"cycle": None, "appraisal": None}

    return _appraisal_payload(emp_id, cycle)


def _appraisal_payload(emp_id, cycle):
    names = frappe.get_all(
        "Appraisal",
        filters={"employee": emp_id, "appraisal_cycle": cycle, "docstatus": ["!=", 2]},
        pluck="name",
        limit=1,
    )
    cycle_doc = frappe.db.get_value(
        "Appraisal Cycle", cycle,
        ["name", "cycle_name", "status", "start_date", "end_date"],
        as_dict=True,
    )
    if cycle_doc:
        _serialise_dates(cycle_doc, "start_date", "end_date")

    if not names:
        return {"cycle": cycle_doc, "appraisal": None}

    ap = frappe.get_doc("Appraisal", names[0])
    return {
        "cycle": cycle_doc,
        "appraisal": {
            "name":         ap.name,
            "employee":     ap.employee,
            "employee_name": ap.employee_name,
            "docstatus":    ap.docstatus,
            "total_score":  flt(ap.total_score),
            "self_score":   flt(ap.self_score),
            "avg_feedback_score": flt(ap.avg_feedback_score),
            "final_score":  flt(ap.final_score),
            "reflections":  ap.reflections or "",
            "remarks":      ap.remarks or "",
            "goals": [
                {
                    "idx": g.idx,
                    "kra": g.kra,
                    "per_weightage": flt(g.per_weightage),
                    "score": flt(g.score),
                    "score_earned": flt(g.score_earned),
                }
                for g in (ap.goals or [])
            ],
        },
    }


@frappe.whitelist()
def list_appraisals(cycle=None, status=None):
    """Every appraisal the caller may see.

    HR sees the whole tenant; a manager sees their own plus everyone below
    them; anyone else sees only their own. Rows carry the flags the UI needs so
    it does not have to re-derive who may open or act on what.
    """
    me = _require_employee()
    hr = _is_hr()

    if hr:
        subjects = None            # unrestricted
    else:
        subjects = [me, *_subordinates(me)]

    filters = {"docstatus": ["!=", 2]}
    if cycle:
        filters["appraisal_cycle"] = cycle
    if not hr:
        filters["employee"] = ["in", subjects or [""]]

    rows = frappe.get_all(
        "Appraisal",
        filters=filters,
        fields=["name", "employee", "employee_name", "designation", "department",
                "appraisal_cycle", "docstatus", "total_score", "self_score",
                "avg_feedback_score", "final_score", "start_date", "end_date"],
        order_by="appraisal_cycle desc, employee_name asc",
    )

    my_reports = set(_reports_of(me))
    cycle_status = {
        c["name"]: c["status"]
        for c in frappe.get_all("Appraisal Cycle", fields=["name", "status"])
    }

    out = []
    for r in rows:
        _serialise_dates(r, "start_date", "end_date")
        submitted = r["docstatus"] == 1
        r["status"] = "Submitted" if submitted else "Draft"
        r["cycle_status"] = cycle_status.get(r["appraisal_cycle"], "")
        r["is_own"] = int(r["employee"] == me)
        # Reviewing is the direct manager's job (and HR's), which is a narrower
        # relationship than the subtree used for visibility.
        r["can_review"] = int(not submitted and (hr or r["employee"] in my_reports))
        r["can_self_assess"] = int(not submitted and r["employee"] == me)
        out.append(r)

    if status:
        out = [r for r in out if r["status"] == status]

    return {
        "appraisals": out,
        "is_hr": int(hr),
        "employee_id": me,
        "counts": {
            "total": len(out),
            "submitted": sum(1 for r in out if r["status"] == "Submitted"),
            "draft": sum(1 for r in out if r["status"] == "Draft"),
        },
    }


@frappe.whitelist()
def get_appraisals(cycle=None, status=None):
    """Alias for list_appraisals — backward-compatible name used by the portal."""
    return list_appraisals(cycle=cycle, status=status)


@frappe.whitelist()
def get_appraisal(appraisal):
    """One appraisal by id, for the detail screen."""
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)

    if not _is_hr() and ap.employee != me and ap.employee not in _subordinates(me):
        frappe.throw(
            "That appraisal belongs to someone outside your team.", frappe.PermissionError
        )

    payload = _appraisal_payload(ap.employee, ap.appraisal_cycle)
    detail = payload.get("appraisal") or {}
    detail["designation"] = ap.designation or ""
    detail["department"] = ap.department or ""
    detail["is_own"] = int(ap.employee == me)
    detail["can_review"] = int(ap.docstatus == 0 and
                               (_is_hr() or ap.employee in _reports_of(me)))
    detail["can_self_assess"] = int(ap.docstatus == 0 and ap.employee == me)
    detail["self_ratings"] = [
        {"criteria": str(getattr(r, "criteria", "")),
         "per_weightage": flt(getattr(r, "per_weightage", 0)),
         "rating": flt(getattr(r, "rating", 0))}
        for r in (ap.self_ratings or [])
    ]
    payload["appraisal"] = detail
    return payload


@frappe.whitelist()
def hr_start_appraisal_process(cycle_name, start_date, end_date, description="",
                               generate=1):
    """Create a review cycle and, optionally, its appraisals in one step.

    This is the 'new appraisal process' action: without it an HR user has to
    create a cycle, leave, assign KPIs, and come back to generate. Generation is
    skipped silently when nobody has KPIs yet — the cycle still gets created, and
    the response says so.
    """
    _require_hr()
    cycle = hr_create_cycle(cycle_name, start_date, end_date, description)

    result = {"cycle": cycle["name"], "created": [], "existing": [], "skipped": [],
              "message": f"Cycle '{cycle['name']}' created."}
    if not int(generate or 0):
        return result

    # Generation now pulls in anything live during the cycle, so an empty
    # pre-tagged set is no longer a reason to stop.
    try:
        gen = hr_generate_appraisals(cycle["name"])
    except frappe.ValidationError as e:
        result["message"] += " " + _plain(str(e))
        return result
    result.update(gen)
    result["cycle"] = cycle["name"]
    result["message"] = f"Cycle '{cycle['name']}' created. " + gen["message"]
    return result


@frappe.whitelist()
def save_reflections(appraisal, reflections):
    """Employee's free-text self assessment."""
    emp_id = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)
    if ap.employee != emp_id:
        frappe.throw("Not permitted.", frappe.PermissionError)
    if ap.docstatus == 1:
        frappe.throw("This appraisal is already submitted and can no longer be edited.")

    ap.reflections = reflections
    ap.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": "Self assessment saved."}


# ══════════════════════════════════════════════════════════════════════════
# Manager review
# ══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_team_reviews(cycle=None):
    """Performance review status for the caller's direct reports (or all employees for HR)."""
    me = _require_employee()
    hr = _is_hr()

    if hr:
        reports = frappe.get_all("Employee", filters={"status": "Active"}, pluck="name")
    else:
        reports = _reports_of(me)

    if not reports:
        return {"team": [], "cycle": cycle or ""}

    # Get employee names
    emp_names = {
        e["name"]: e["employee_name"]
        for e in frappe.get_all("Employee", filters={"name": ["in", reports]}, fields=["name", "employee_name"])
    }

    # Get appraisals for the cycle (or all if no cycle)
    appraisal_filters = {"employee": ["in", reports], "docstatus": ["!=", 2]}
    if cycle:
        appraisal_filters["appraisal_cycle"] = cycle

    appraisals = frappe.get_all(
        "Appraisal",
        filters=appraisal_filters,
        fields=["name", "employee", "appraisal_cycle", "start_date", "end_date"],
    )

    if not appraisals:
        team = [
            {"employee": e, "employee_name": emp_names.get(e, e),
             "appraisal": None, "review_status": "Not Started",
             "overall_rating": None, "potential_rating": None}
            for e in reports
        ]
        return {"team": team, "cycle": cycle or ""}

    # Load extension data
    appraisal_names = [a["name"] for a in appraisals]
    ext_map = {}
    for ext in frappe.get_all(
        "Grace Appraisal Extension",
        filters={"appraisal": ["in", appraisal_names]},
        fields=["appraisal", "review_status", "overall_rating", "potential_rating"],
    ):
        ext_map[ext["appraisal"]] = ext

    appraisal_by_emp = {a["employee"]: a for a in appraisals}

    team = []
    for emp_id in reports:
        ap = appraisal_by_emp.get(emp_id)
        if ap:
            ext = ext_map.get(ap["name"]) or {}
            team.append({
                "employee":       emp_id,
                "employee_name":  emp_names.get(emp_id, emp_id),
                "appraisal":      ap["name"],
                "review_status":  ext.get("review_status") or "Not Started",
                "overall_rating": ext.get("overall_rating"),
                "potential_rating": ext.get("potential_rating"),
                "start_date":     ap.get("start_date") or "",
                "end_date":       ap.get("end_date") or "",
            })
        else:
            team.append({
                "employee":       emp_id,
                "employee_name":  emp_names.get(emp_id, emp_id),
                "appraisal":      None,
                "review_status":  "Not Started",
                "overall_rating": None,
                "potential_rating": None,
                "start_date":     "",
                "end_date":       "",
            })

    return {"team": team, "cycle": cycle or ""}


@frappe.whitelist()
def get_team_kpis(cycle=None):
    """KPIs for the caller's direct reports, grouped per employee."""
    me = _require_employee()
    reports = _reports_of(me)
    if not reports:
        return {"team": [], "cycle": cycle or ""}

    filters = {"employee": ["in", reports]}
    if cycle:
        filters["appraisal_cycle"] = cycle
    rows = _kpi_rows(filters)

    by_emp = {}
    for r in rows:
        by_emp.setdefault(r["employee"], {
            "employee": r["employee"],
            "employee_name": r["employee_name"],
            "kpis": [],
        })["kpis"].append(r)

    # Fetch appraisal names for the cycle so the UI can link review actions
    appraisal_by_emp = {}
    if cycle:
        for a in frappe.get_all(
            "Appraisal",
            filters={"appraisal_cycle": cycle, "employee": ["in", reports], "docstatus": ["!=", 2]},
            fields=["name", "employee"],
        ):
            appraisal_by_emp[a["employee"]] = a["name"]

    team = []
    for emp_id in reports:
        entry = by_emp.get(emp_id)
        if not entry:
            name = frappe.db.get_value("Employee", emp_id, "employee_name")
            entry = {"employee": emp_id, "employee_name": name, "kpis": []}
        kpis = entry["kpis"]
        entry["total_weightage"] = flt(sum(flt(k["weightage"]) for k in kpis), 2)
        entry["rated_count"] = sum(1 for k in kpis if flt(k["manager_rating"]) > 0)
        entry["avg_attainment"] = flt(
            sum(flt(k["attainment_pct"]) for k in kpis) / len(kpis), 1
        ) if kpis else 0
        entry["appraisal"] = appraisal_by_emp.get(emp_id, "")
        team.append(entry)

    return {"team": team, "cycle": cycle or ""}


@frappe.whitelist()
def save_kpi_manager_review(kpi, rating, comment="", potential_rating="", potential_comment=""):
    """Manager's 0-5 rating for a report's KPI. This is what scores the appraisal."""
    doc = frappe.get_doc("KPI", kpi)
    _require_can_review(doc.employee)

    rating = flt(rating)
    if rating < 0 or rating > MAX_RATING:
        frappe.throw(f"Rating must be between 0 and {int(MAX_RATING)}.")

    doc.manager_rating = rating
    doc.manager_comment = comment

    if potential_rating != "":
        pot = flt(potential_rating)
        if pot < 0 or pot > MAX_RATING:
            frappe.throw(f"Potential rating must be between 0 and {int(MAX_RATING)}.")
        doc.potential_rating = pot
        doc.potential_comment = potential_comment

    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name, "manager_rating": rating, "message": "Review saved."}


@frappe.whitelist()
def suggest_ratings(employee, cycle):
    """Pre-fill manager ratings from measured attainment, for review not for record."""
    _require_can_review(employee)
    rows = _kpi_rows({"employee": employee, "appraisal_cycle": cycle})
    return [
        {
            "kpi": r["name"],
            "kpi_name": r["kpi_name"],
            "attainment_pct": flt(r["attainment_pct"]),
            "suggested_rating": flt(rating_from_attainment(r["attainment_pct"]), 2),
        }
        for r in rows
    ]


@frappe.whitelist()
def get_team_appraisal(employee, cycle):
    """One report's appraisal, for the manager's review screen."""
    _require_can_review(employee)
    return _appraisal_payload(employee, cycle)


@frappe.whitelist()
def sync_appraisal_from_kpis(appraisal):
    """Rewrite an appraisal's goal rows from the employee's current KPIs.

    Manager ratings live on the KPI; the Appraisal is the HRMS-side projection
    of them. Re-running this is safe and idempotent — it is how a manager pulls
    revised ratings through before submitting.
    """
    ap = frappe.get_doc("Appraisal", appraisal)
    _require_can_review(ap.employee)
    if ap.docstatus == 1:
        frappe.throw("This appraisal is already submitted.")

    _apply_kpis_to_appraisal(ap)
    ap.save(ignore_permissions=True)

    # Compute and persist avg potential rating on the extension
    _sync_potential_to_extension(appraisal, ap.employee, ap.appraisal_cycle)

    frappe.db.commit()
    return {
        "name": ap.name,
        "total_score": flt(ap.total_score),
        "final_score": flt(ap.final_score),
        "message": "Scores pulled from KPIs.",
    }


def _sync_potential_to_extension(appraisal, employee, cycle):
    """Compute avg potential rating from KPIs and store it on the extension."""
    rows = frappe.get_all(
        "KPI",
        filters={"employee": employee, "appraisal_cycle": cycle, "status": ["!=", "Cancelled"]},
        fields=["potential_rating"],
    )
    rated = [flt(r["potential_rating"]) for r in rows if r.get("potential_rating")]
    if not rated:
        return
    avg = flt(sum(rated) / len(rated), 2)

    ext = _get_or_create_extension(appraisal)
    ext.avg_potential_rating = avg
    ext.save(ignore_permissions=True)


def _cycle_window(cycle):
    row = frappe.db.get_value(
        "Appraisal Cycle", cycle, ["start_date", "end_date"], as_dict=True
    )
    return (row.start_date, row.end_date) if row else (None, None)


def _is_overdue(end_date, reference=None):
    """A deadline that has already passed. Used to flag, never to exclude."""
    if not end_date:
        return False
    return getdate(end_date) < getdate(reference or today())


@frappe.whitelist()
def attach_ongoing_to_cycle(cycle, employee=None):
    """Pull every goal and KPI that is live during the cycle into that cycle.

    "Ongoing" means the item's period overlaps the cycle window and it has not
    been cancelled. Overdue items are attached too: a missed deadline is exactly
    what a review should discuss, so it is flagged rather than dropped.

    An item can only belong to one cycle, so claiming has rules. Work tagged to
    a cycle that is still running is left alone — a deliberate opt-in must not
    be silently overwritten. Work whose cycle is already Completed *is* re-
    claimed, otherwise long-running goals would be stuck in a closed cycle and
    invisible to every review that follows.
    """
    start, end = _cycle_window(cycle)
    if not start or not end:
        frappe.throw(f"Cycle '{cycle}' has no period set.")

    closed = set(frappe.get_all(
        "Appraisal Cycle", filters={"status": "Completed"}, pluck="name"
    ))

    def claimable(current):
        return (not current) or current == cycle or current in closed

    attached = {"goals": [], "kpis": []}

    goal_filters = {"docstatus": ["!=", 2], "status": ["!=", "Cancelled"]}
    kpi_filters = {"status": ["!=", "Cancelled"]}
    if employee:
        goal_filters["employee"] = employee
        kpi_filters["employee"] = employee

    for g in frappe.get_all("Individual Goal", filters=goal_filters,
                            fields=["name", "goal_name", "start_date", "end_date",
                                    "appraisal_cycle"], ignore_permissions=True):
        if not claimable(g.appraisal_cycle):
            continue
        if g.appraisal_cycle == cycle:
            continue
        if _overlaps(str(g.start_date or ""), str(g.end_date or ""), str(start), str(end)):
            frappe.db.set_value("Individual Goal", g.name, "appraisal_cycle", cycle,
                                update_modified=False)
            attached["goals"].append(g.goal_name)

    for k in frappe.get_all("KPI", filters=kpi_filters,
                            fields=["name", "kpi_name", "period_start", "period_end",
                                    "appraisal_cycle"], ignore_permissions=True):
        if not claimable(k.appraisal_cycle):
            continue
        if k.appraisal_cycle == cycle:
            continue
        if _overlaps(str(k.period_start or ""), str(k.period_end or ""), str(start), str(end)):
            frappe.db.set_value("KPI", k.name, "appraisal_cycle", cycle,
                                update_modified=False)
            attached["kpis"].append(k.kpi_name)

    frappe.db.commit()
    return attached


@frappe.whitelist()
def set_cycle_membership(kind, name, cycle, include=1):
    """Opt a goal or KPI in or out of a review cycle.

    Anyone may nominate their own work; a manager or HR may nominate for
    someone in their line. This is the "I want this considered" control, so it
    deliberately does not require authorship the way editing does.
    """
    if kind not in ("goal", "kpi"):
        frappe.throw("kind must be 'goal' or 'kpi'.")
    doctype = "Individual Goal" if kind == "goal" else "KPI"

    owner_emp = frappe.db.get_value(doctype, name, "employee")
    if not owner_emp:
        frappe.throw(f"{doctype} '{name}' not found.")
    _require_manages(owner_emp)

    if int(include or 0):
        if not frappe.db.exists("Appraisal Cycle", cycle):
            frappe.throw(f"Cycle '{cycle}' does not exist.")
        frappe.db.set_value(doctype, name, "appraisal_cycle", cycle, update_modified=False)
        msg = "added to the cycle"
    else:
        frappe.db.set_value(doctype, name, "appraisal_cycle", None, update_modified=False)
        msg = "removed from the cycle"

    frappe.db.commit()
    label = frappe.db.get_value(doctype, name, "goal_name" if kind == "goal" else "kpi_name")
    return {"name": name, "kind": kind, "cycle": cycle if int(include or 0) else "",
            "message": f"'{label}' {msg}."}


@frappe.whitelist()
def get_cycle_items(cycle, employee=None):
    """Everything currently considered in a cycle for one employee.

    Returns goals and KPIs side by side with an `is_overdue` flag, which is what
    the appraisal screen highlights.
    """
    me = _require_employee()
    emp = employee or me
    if emp != me:
        _require_manages(emp)

    goals = frappe.get_all(
        "Individual Goal",
        filters={"employee": emp, "appraisal_cycle": cycle, "docstatus": ["!=", 2]},
        fields=["name", "goal_name", "target_value", "actual_progress", "progress_pct",
                "unit", "status", "trajectory", "start_date", "end_date", "weightage"],
        ignore_permissions=True,
    )
    for g in goals:
        _serialise_dates(g, "start_date", "end_date")
        g["kind"] = "goal"
        g["label"] = g["goal_name"]
        g["is_overdue"] = int(_is_overdue(g["end_date"]))

    kpis = frappe.get_all(
        "KPI",
        filters={"employee": emp, "appraisal_cycle": cycle, "status": ["!=", "Cancelled"]},
        fields=["name", "kpi_name", "target_value", "actual_value", "attainment_pct",
                "unit", "status", "period_start", "period_end", "weightage",
                "manager_rating"],
        ignore_permissions=True,
    )
    for k in kpis:
        _serialise_dates(k, "period_start", "period_end")
        k["kind"] = "kpi"
        k["label"] = k["kpi_name"]
        k["is_overdue"] = int(_is_overdue(k["period_end"]))

    total = sum(flt(i["weightage"]) for i in goals + kpis)
    return {
        "cycle": cycle,
        "employee": emp,
        "goals": goals,
        "kpis": kpis,
        "total_weightage": flt(total, 2),
        "weightage_complete": flt(total, 2) == TOTAL_WEIGHTAGE,
        "overdue_count": sum(1 for i in goals + kpis if i["is_overdue"]),
    }


def _scored_items(employee, cycle):
    """Goals and KPIs carrying a weightage — the rows an appraisal scores.

    Zero-weightage items ride along on the cycle for context but are not part
    of the score, so they are excluded here and listed separately on screen.
    """
    rows = []
    for k in frappe.get_all(
        "KPI",
        filters={"employee": employee, "appraisal_cycle": cycle, "status": ["!=", "Cancelled"]},
        fields=["kpi_name", "weightage", "manager_rating", "attainment_pct", "period_end"],
        order_by="kpi_name asc", ignore_permissions=True,
    ):
        if flt(k["weightage"]):
            rows.append({"label": k["kpi_name"], "weightage": flt(k["weightage"]),
                         "score": flt(k["manager_rating"]), "end_date": k["period_end"]})

    for g in frappe.get_all(
        "Individual Goal",
        filters={"employee": employee, "appraisal_cycle": cycle, "docstatus": ["!=", 2],
                 "status": ["!=", "Cancelled"]},
        fields=["goal_name", "weightage", "progress_pct", "end_date"],
        order_by="goal_name asc", ignore_permissions=True,
    ):
        if flt(g["weightage"]):
            # A goal has progress rather than a manager rating; map it onto the
            # same 0-5 scale so both kinds can share the appraisal's goal table.
            rows.append({"label": g["goal_name"], "weightage": flt(g["weightage"]),
                         "score": flt(rating_from_attainment(g["progress_pct"])),
                         "end_date": g["end_date"]})
    return rows


def _apply_kpis_to_appraisal(ap):
    """Project the employee's cycle KPIs *and goals* onto the Appraisal table.

    Both kinds can carry a weightage, so both can be scored; anything left at 0
    stays attached to the cycle for context and is simply not projected here.

    HRMS computes score_earned = score * per_weightage / 100 and rejects the doc
    unless the weightages total exactly 100, so an employee whose weightages are
    incomplete cannot be scored — the caller is told the number and why.
    """
    rows = _scored_items(ap.employee, ap.appraisal_cycle)
    who = ap.employee_name or ap.employee

    if not rows:
        attached = frappe.db.count("KPI", {"employee": ap.employee,
                                           "appraisal_cycle": ap.appraisal_cycle}) + \
                   frappe.db.count("Individual Goal", {"employee": ap.employee,
                                                       "appraisal_cycle": ap.appraisal_cycle})
        frappe.throw(
            f"{who} has nothing weighted in this cycle. "
            + (f"{attached} item(s) are attached but all sit at 0% weightage — "
               "give them a share of the score before generating."
               if attached else
               "Assign KPIs or goals to the cycle before generating the appraisal.")
        )

    total_weightage = flt(sum(r["weightage"] for r in rows), 2)
    if total_weightage != TOTAL_WEIGHTAGE:
        frappe.throw(
            f"{who}'s weightages total {total_weightage}%, not {int(TOTAL_WEIGHTAGE)}%. "
            "Adjust them before scoring."
        )

    ap.rate_goals_manually = 1
    ap.set("goals", [])
    for r in rows:
        # A passed deadline is worth seeing on the appraisal itself, not only in
        # the portal, so it is marked in the row label HRMS will render.
        label = r["label"] + (" ⚠ overdue" if _is_overdue(r["end_date"]) else "")
        ap.append("goals", {
            "kra": label,
            "per_weightage": r["weightage"],
            "score": r["score"],
        })


@frappe.whitelist()
def submit_appraisal(appraisal):
    """Manager submits a report's appraisal once every KPI is rated."""
    ap = frappe.get_doc("Appraisal", appraisal)
    _require_can_review(ap.employee)
    if ap.docstatus == 1:
        frappe.throw("This appraisal is already submitted.")

    _apply_kpis_to_appraisal(ap)

    unrated = [g.kra for g in ap.goals if flt(g.score) <= 0]
    if unrated:
        frappe.throw("Rate every KPI before submitting. Still unrated: " + ", ".join(unrated))

    ap.save(ignore_permissions=True)
    ap.submit()
    frappe.db.commit()
    return {
        "name": ap.name,
        "total_score": flt(ap.total_score),
        "final_score": flt(ap.final_score),
        "message": "Appraisal submitted.",
    }


# ══════════════════════════════════════════════════════════════════════════
# HR administration
# ══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def hr_get_setup():
    """Everything the HR admin screen needs in one round trip."""
    _require_hr()

    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name", "designation", "department", "reports_to", "user_id"],
        order_by="employee_name asc",
    )
    cycles = [
        _serialise_dates(c, "start_date", "end_date")
        for c in frappe.get_all(
            "Appraisal Cycle",
            fields=["name", "cycle_name", "status", "start_date", "end_date"],
            order_by="start_date desc",
        )
    ]
    cascades = [
        _serialise_dates(c, "period_start", "period_end")
        for c in frappe.get_all(
            "Goal Cascade",
            fields=["name", "cascade_name", "status", "company_target", "unit",
                    "period_start", "period_end"],
            order_by="period_end desc",
        )
    ]
    return {
        "employees": employees,
        "cycles": cycles,
        "cascades": cascades,
        "company": _default_company(),
        "max_rating": MAX_RATING,
    }


@frappe.whitelist()
def hr_create_cycle(cycle_name, start_date, end_date, description=""):
    """Create a review cycle set up for KPI-based manual scoring."""
    _require_hr()
    if getdate(start_date) > getdate(end_date):
        frappe.throw("Cycle start date is after its end date.")

    # Appraisal Cycle is named by its title, so a repeat name is a primary-key
    # clash. Say that plainly instead of surfacing a DuplicateEntryError.
    if frappe.db.exists("Appraisal Cycle", cycle_name):
        frappe.throw(f"A cycle called '{cycle_name}' already exists. Pick a different name.")

    cycle = frappe.new_doc("Appraisal Cycle")
    cycle.cycle_name = cycle_name
    cycle.company = _default_company()
    cycle.start_date = start_date
    cycle.end_date = end_date
    cycle.description = description
    # KPIs are rated by managers, so appraisals must use the manual goal table
    # rather than HRMS's automated KRA-from-goal-progress path.
    cycle.kra_evaluation_method = "Manual Rating"
    # Without a formula HRMS averages goal, feedback and self scores. This model
    # scores on manager-rated KPIs, and there are no Employee Feedback Criteria
    # behind the other two terms, so averaging in two structural zeros would cut
    # every final score to a third of what was actually awarded.
    cycle.calculate_final_score_based_on_formula = 1
    cycle.final_score_formula = "goal_score"
    cycle.status = "Not Started"
    cycle.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": cycle.name, "cycle_name": cycle.cycle_name, "message": "Cycle created."}


@frappe.whitelist()
def get_wizard_filter_options():
    """Return departments, designations and managers for the employee-selection step."""
    _require_hr()
    departments = frappe.get_all("Department", filters={"is_group": 0}, pluck="name", order_by="name")
    designations = frappe.db.sql_list(
        "SELECT DISTINCT designation FROM `tabEmployee` WHERE status='Active' "
        "AND designation IS NOT NULL AND designation!='' ORDER BY designation"
    )
    managers = frappe.db.sql(
        "SELECT DISTINCT e.name, e.employee_name FROM `tabEmployee` e "
        "WHERE EXISTS (SELECT 1 FROM `tabEmployee` r WHERE r.reports_to=e.name AND r.status='Active') "
        "AND e.status='Active' ORDER BY e.employee_name",
        as_dict=True,
    )
    return {"departments": departments, "designations": designations, "managers": managers}


@frappe.whitelist()
def get_filterable_employees(department=None, manager=None, designation=None,
                              joining_from=None, joining_to=None):
    """Return active employees matching filters for the wizard employee-selection step."""
    _require_hr()
    filters = {"status": "Active"}
    if department:   filters["department"] = department
    if manager:      filters["reports_to"] = manager
    if designation:  filters["designation"] = designation
    employees = frappe.get_all(
        "Employee",
        filters=filters,
        fields=["name", "employee_name", "designation", "department", "reports_to", "date_of_joining"],
        order_by="employee_name asc",
    )
    if joining_from:
        employees = [e for e in employees if e.get("date_of_joining") and str(e["date_of_joining"]) >= joining_from]
    if joining_to:
        employees = [e for e in employees if e.get("date_of_joining") and str(e["date_of_joining"]) <= joining_to]
    mgr_cache = {}
    for emp in employees:
        mgr = emp.get("reports_to") or ""
        if mgr and mgr not in mgr_cache:
            mgr_cache[mgr] = frappe.db.get_value("Employee", mgr, "employee_name") or mgr
        emp["reports_to_name"] = mgr_cache.get(mgr, "")
        if emp.get("date_of_joining"):
            emp["date_of_joining"] = str(emp["date_of_joining"])
    return employees


@frappe.whitelist()
def save_cycle_wizard(cycle_name, start_date, end_date,
                      description="", employee_fields=None, page_config=None,
                      page_settings=None, selected_employees=None, existing_cycle=None):
    """Create a new Appraisal Cycle via the setup wizard and persist its configuration."""
    import json
    _require_hr()
    from frappe.utils import getdate
    if getdate(start_date) > getdate(end_date):
        frappe.throw("Start date must be before end date.")

    # Create cycle (reuses hr_create_cycle logic)
    if existing_cycle and frappe.db.exists("Appraisal Cycle", existing_cycle):
        cycle = frappe.get_doc("Appraisal Cycle", existing_cycle)
        cycle.cycle_name = cycle_name
        cycle.start_date = start_date
        cycle.end_date = end_date
        cycle.description = description
        cycle.save(ignore_permissions=True)
    else:
        if frappe.db.exists("Appraisal Cycle", cycle_name):
            frappe.throw(f"A cycle called '{cycle_name}' already exists. Pick a different name.")
        cycle = frappe.new_doc("Appraisal Cycle")
        cycle.cycle_name = cycle_name
        cycle.company = _default_company()
        cycle.start_date = start_date
        cycle.end_date = end_date
        cycle.description = description
        cycle.kra_evaluation_method = "Manual Rating"
        cycle.calculate_final_score_based_on_formula = 1
        cycle.final_score_formula = "goal_score"
        cycle.status = "Not Started"
        cycle.insert(ignore_permissions=True)

    # Save or update the Grace Cycle Config
    emp_fields_json   = json.dumps(employee_fields) if isinstance(employee_fields, (dict, list)) else (employee_fields or "{}")
    page_config_json  = json.dumps(page_config)     if isinstance(page_config,     (dict, list)) else (page_config     or "{}")
    page_settings_json = json.dumps(page_settings)  if isinstance(page_settings,   (dict, list)) else (page_settings   or "{}")

    if frappe.db.exists("Grace Cycle Config", cycle.name):
        cfg = frappe.get_doc("Grace Cycle Config", cycle.name)
    else:
        cfg = frappe.new_doc("Grace Cycle Config")
        cfg.appraisal_cycle = cycle.name

    cfg.description      = description
    cfg.employee_fields  = emp_fields_json
    cfg.page_config      = page_config_json
    cfg.page_settings    = page_settings_json

    emp_list = []
    if selected_employees:
        if isinstance(selected_employees, str):
            emp_list = json.loads(selected_employees)
        elif isinstance(selected_employees, list):
            emp_list = selected_employees

    cfg.selected_employees = json.dumps(emp_list)

    if cfg.is_new():
        cfg.insert(ignore_permissions=True)
    else:
        cfg.save(ignore_permissions=True)

    # Create Appraisal + Grace Appraisal Extension for each selected employee
    created = 0
    skipped = 0

    for emp_id in emp_list:
        existing = frappe.db.get_value(
            "Appraisal", {"appraisal_cycle": cycle.name, "employee": emp_id}, "name"
        )
        if existing:
            skipped += 1
            continue
        try:
            appr = frappe.new_doc("Appraisal")
            appr.appraisal_cycle = cycle.name
            appr.employee = emp_id
            appr.company = cycle.company
            appr.start_date = cycle.start_date
            appr.end_date = cycle.end_date
            appr.status = "Draft"
            appr.insert(ignore_permissions=True)
            ext = frappe.new_doc("Grace Appraisal Extension")
            ext.appraisal = appr.name
            ext.employee = emp_id
            ext.appraisal_cycle = cycle.name
            ext.review_status = "Not Started"
            ext.insert(ignore_permissions=True)
            created += 1
        except Exception as e:
            frappe.log_error(f"Failed to create appraisal for {emp_id}: {e}", "save_cycle_wizard")
            skipped += 1

    frappe.db.commit()
    msg = f"Appraisal cycle created. {created} appraisals generated."
    if skipped:
        msg += f" {skipped} skipped (already existed or error)."
    return {"name": cycle.name, "cycle_name": cycle.cycle_name, "message": msg, "created": created, "skipped": skipped}


@frappe.whitelist()
def get_cycle_config(cycle):
    """Return the wizard configuration for a cycle."""
    import json
    _require_hr()
    if not frappe.db.exists("Grace Cycle Config", cycle):
        return {"employee_fields": {}, "page_config": {}, "page_settings": {}, "description": ""}
    cfg = frappe.get_doc("Grace Cycle Config", cycle)
    def _parse(val):
        try:
            return json.loads(val or "{}")
        except Exception:
            return {}
    return {
        "description":    cfg.description or "",
        "employee_fields": _parse(cfg.employee_fields),
        "page_config":    _parse(cfg.page_config),
        "page_settings":  _parse(cfg.page_settings),
    }


@frappe.whitelist()
def search_employees(query=""):
    """Search active employees by name or ID — open to any logged-in user."""
    if frappe.session.user == "Guest":
        frappe.throw("Please log in.", frappe.PermissionError)
    query = (query or "").strip()
    filters = {"status": "Active"}
    if query:
        filters["employee_name"] = ["like", "%" + query + "%"]
    rows = frappe.get_all(
        "Employee",
        filters=filters,
        fields=["name", "employee_name", "designation", "department"],
        order_by="employee_name asc",
        limit=80,
    )
    # Also search by employee ID if query looks like one
    if query:
        by_id = frappe.get_all(
            "Employee",
            filters={"name": ["like", "%" + query + "%"], "status": "Active"},
            fields=["name", "employee_name", "designation", "department"],
            limit=20,
        )
        seen = {r["name"] for r in rows}
        for r in by_id:
            if r["name"] not in seen:
                rows.append(r)
    return rows


@frappe.whitelist()
def get_rating_scales():
    """Return all organisation rating scales with their points."""
    if frappe.session.user == "Guest":
        frappe.throw("Please log in.", frappe.PermissionError)
    scales = frappe.get_all(
        "Grace Rating Scale",
        fields=["name", "scale_name", "description", "is_default"],
        order_by="scale_name",
    )
    for s in scales:
        s["items"] = frappe.get_all(
            "Grace Rating Scale Item",
            filters={"parent": s["name"]},
            fields=["label", "value", "color"],
            order_by="value desc",
        )
    return scales


@frappe.whitelist()
def save_rating_scale(scale_name, items, existing_name=None):
    """Create or update a rating scale. items should be a JSON list of {label, value, color}."""
    import json
    _require_hr()
    if isinstance(items, str):
        items = json.loads(items)
    if not items:
        frappe.throw("A rating scale must have at least one point.")
    for it in items:
        if not it.get("label"):
            frappe.throw("Every scale point must have a label.")
        if it.get("value") is None:
            frappe.throw("Every scale point must have a numeric value.")

    if existing_name and frappe.db.exists("Grace Rating Scale", existing_name):
        doc = frappe.get_doc("Grace Rating Scale", existing_name)
        doc.scale_name = scale_name
    else:
        if frappe.db.exists("Grace Rating Scale", scale_name):
            frappe.throw(f"A scale called '{scale_name}' already exists.")
        doc = frappe.new_doc("Grace Rating Scale")
        doc.scale_name = scale_name

    doc.set("items", [])
    for it in items:
        doc.append("items", {
            "label": it.get("label", ""),
            "value": float(it.get("value", 0)),
            "color": it.get("color", ""),
        })

    if doc.is_new():
        doc.insert(ignore_permissions=True)
    else:
        doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name, "message": "Rating scale saved."}


@frappe.whitelist()
def delete_rating_scale(name):
    _require_hr()
    if not frappe.db.exists("Grace Rating Scale", name):
        frappe.throw("Rating scale not found.")
    frappe.delete_doc("Grace Rating Scale", name, ignore_permissions=True)
    frappe.db.commit()
    return {"message": "Deleted."}


@frappe.whitelist()
def hr_list_appraisals(cycle, show_archived=0):
    """Return all appraisals in a cycle with employee info and review_status from Grace Appraisal Extension."""
    _require_hr()
    appraisals = frappe.get_all(
        "Appraisal",
        filters={"appraisal_cycle": cycle},
        fields=["name", "employee", "employee_name", "department", "designation"],
        order_by="employee_name asc",
    )
    if not appraisals:
        return []
    # Bulk-fetch extensions to avoid N+1 queries
    ext_map = {}
    for ext in frappe.get_all(
        "Grace Appraisal Extension",
        filters={"appraisal_cycle": cycle},
        fields=["appraisal", "review_status", "overall_rating", "archived"],
    ):
        ext_map[ext["appraisal"]] = ext
    result = []
    for ap in appraisals:
        ext = ext_map.get(ap["name"]) or {}
        ap["review_status"]  = ext.get("review_status") or "Not Started"
        ap["overall_rating"] = ext.get("overall_rating")
        ap["archived"]       = int(ext.get("archived") or 0)
        if ap["archived"] and not int(show_archived):
            continue
        # Fetch the email of whoever is responsible at the current stage
        ap["responsible_email"] = _get_responsible_email(ap["employee"], ap["review_status"])
        result.append(ap)
    return result


def _get_responsible_email(employee_id, review_status):
    """Return the work email of whoever should act at the given review stage."""
    if review_status in ("Not Started", "Employee Review", "Employee Final Review"):
        email = frappe.db.get_value("Employee", employee_id, "company_email") or \
                frappe.db.get_value("Employee", employee_id, "prefered_email") or \
                frappe.db.get_value("Employee", employee_id, "personal_email") or ""
        return email
    if review_status == "Manager Review":
        reports_to = get_effective_manager(employee_id)
        if reports_to:
            email = frappe.db.get_value("Employee", reports_to, "company_email") or \
                    frappe.db.get_value("Employee", reports_to, "prefered_email") or \
                    frappe.db.get_value("Employee", reports_to, "personal_email") or ""
            return email
    return ""


@frappe.whitelist()
def send_review_reminder(appraisal):
    """Send an email reminder to whoever is responsible at the current review stage."""
    _require_hr()
    ap = frappe.get_doc("Appraisal", appraisal)
    ext = _get_or_create_extension(appraisal)
    status = ext.review_status or "Not Started"

    recipient = _get_responsible_email(ap.employee, status)
    if not recipient:
        frappe.throw("No email address found for the responsible person.")

    stage_label = {
        "Not Started":          "start their self-review",
        "Employee Review":      "complete their self-review",
        "Manager Review":       "complete the manager review",
        "Employee Final Review": "acknowledge the manager's feedback",
        "HR Review":            "complete the HR review",
    }.get(status, "continue the review process")

    employee_name = ap.employee_name or ap.employee
    cycle_name = frappe.db.get_value("Appraisal Cycle", ap.appraisal_cycle, "cycle_name") or ap.appraisal_cycle

    subject = f"Reminder: Performance Review — {employee_name}"
    message = f"""<p>Hi,</p>
<p>This is a reminder that action is required for the performance review of <strong>{employee_name}</strong>
in the <strong>{cycle_name}</strong> cycle.</p>
<p>Current status: <strong>{status}</strong></p>
<p>Please log in to the HR portal to <strong>{stage_label}</strong>.</p>
<p>Thank you.</p>"""

    frappe.sendmail(
        recipients=[recipient],
        subject=subject,
        message=message,
        now=True,
    )
    frappe.db.commit()
    return {"message": f"Reminder sent to {recipient}."}


@frappe.whitelist()
def archive_review(appraisal):
    """HR-only: mark a completed review as archived (hidden from default list)."""
    _require_hr()
    ext = _get_or_create_extension(appraisal)
    if ext.review_status != "Completed":
        frappe.throw("Only completed reviews can be archived.")
    ext.archived = 1
    ext.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": "Review archived."}


@frappe.whitelist()
def unarchive_review(appraisal):
    """HR-only: restore an archived review to the active list."""
    _require_hr()
    ext = _get_or_create_extension(appraisal)
    ext.archived = 0
    ext.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": "Review restored."}


@frappe.whitelist()
def hr_set_cycle_status(cycle, status):
    _require_hr()
    if status not in ("Not Started", "In Progress", "Completed"):
        frappe.throw("Unknown cycle status.")
    frappe.db.set_value("Appraisal Cycle", cycle, "status", status)
    frappe.db.commit()
    return {"name": cycle, "status": status, "message": f"Cycle marked {status}."}


@frappe.whitelist()
def hr_create_cascade(cascade_name, company_target, unit, period_start, period_end, description=""):
    """Create a company-level cascade that KPIs and goals can align to."""
    _require_hr()
    cascade = frappe.new_doc("Goal Cascade")
    cascade.cascade_name = cascade_name
    cascade.company = _default_company()
    cascade.company_target = flt(company_target)
    cascade.unit = unit
    cascade.period_start = period_start
    cascade.period_end = period_end
    cascade.description = description
    cascade.status = "Active"
    cascade.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": cascade.name, "message": "Cascade created."}


def _write_kpi(employee, kpi_name, target_value, appraisal_cycle, weightage=0,
               unit="Number", direction="Higher is Better", category="Financial",
               baseline_value=0, period_start=None, period_end=None,
               goal_cascade=None, individual_goal=None, description="", kpi=None):
    """Shared create/update path. Callers do their own authorisation first."""
    doc = frappe.get_doc("KPI", kpi) if kpi else frappe.new_doc("KPI")
    doc.employee = employee
    doc.kpi_name = kpi_name
    doc.appraisal_cycle = appraisal_cycle
    doc.target_value = flt(target_value)
    doc.weightage = flt(weightage)
    doc.unit = unit
    doc.direction = direction
    doc.category = category
    doc.baseline_value = flt(baseline_value)
    # The controller checks the objective's owner is this employee or above
    # them, so a KPI can never be attached to a sibling branch's goal.
    doc.individual_goal = individual_goal or None
    # Cascade is derived from the linked objective (see grace_goals.controllers
    # .kpi), so it is no longer collected from the UI. It stays an accepted
    # argument for the unlinked case and for API callers.
    if not doc.individual_goal:
        doc.goal_cascade = goal_cascade or None
    doc.description = description
    if period_start:
        doc.period_start = period_start
    if period_end:
        doc.period_end = period_end
    if doc.status == "Draft":
        doc.status = "Active"

    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {
        "name": doc.name,
        "kpi_name": doc.kpi_name,
        "employee": doc.employee,
        "individual_goal": doc.individual_goal or "",
        "attainment_pct": flt(doc.attainment_pct),
        "message": "KPI saved.",
    }


@frappe.whitelist()
def relink_kpi(kpi, individual_goal=None):
    """Move a KPI under a different objective — the drag-and-drop endpoint.

    Re-runs the same authorisation and linkage rules as a normal edit: you must
    be the KPI's author (or HR), and the target objective must belong to the
    KPI's employee or someone above them. Passing an empty objective detaches it.
    """
    doc = frappe.get_doc("KPI", kpi)
    _require_can_edit_kpi(doc)

    previous = doc.individual_goal or ""
    doc.individual_goal = individual_goal or None
    doc.save(ignore_permissions=True)   # controller validates the new linkage
    frappe.db.commit()

    target = ""
    if doc.individual_goal:
        target = frappe.db.get_value("Individual Goal", doc.individual_goal, "goal_name") or ""
    return {
        "name": doc.name,
        "individual_goal": doc.individual_goal or "",
        "objective": target,
        "previous": previous,
        "goal_cascade": doc.goal_cascade or "",
        "message": f"'{doc.kpi_name}' moved to {target}" if target
                   else f"'{doc.kpi_name}' detached from its objective",
    }


# ══════════════════════════════════════════════════════════════════════════
# Combined objective + KPI tree
# ══════════════════════════════════════════════════════════════════════════

def _overlaps(start, end, from_date, to_date):
    """True when [start, end] intersects the filter window (open-ended sides ok)."""
    if from_date and end and getdate(end) < getdate(from_date):
        return False
    if to_date and start and getdate(start) > getdate(to_date):
        return False
    return True


GOAL_TREE_FIELDS = [
    "name", "goal_name", "employee", "employee_name", "parent_goal",
    "goal_cascade", "target_value", "actual_progress", "progress_pct",
    "unit", "status", "trajectory", "start_date", "end_date", "owner",
    "appraisal_cycle", "goal_type", "company_value", "is_extra_initiative",
]

# Where a KPI has no trajectory field, attainment stands in for one. The bands
# match the colour coding already used on the bars, so the filter agrees with
# what the row looks like.
KPI_ON_TRACK = 70
KPI_AT_RISK = 40


def _scope_employees(scope, me, hr):
    """Employee ids a given scope covers.

    `team` (self + reporting subtree) is kept for the older include_team flag.
    """
    from grace_goals.permissions import manageable_employees, descendants

    if scope == "mine":
        return [me]
    if scope == "department":
        dept = frappe.db.get_value("Employee", me, "department")
        if not dept:
            return [me]
        return frappe.get_all(
            "Employee", filters={"department": dept, "status": "Active"},
            pluck="name", ignore_permissions=True,
        ) or [me]
    if scope == "organisation":
        # Seeing every objective and KPI in the tenant is a supervisory view, so
        # it takes someone below you or an HR role. Enforced here and not only
        # hidden in the UI, because the endpoint is callable directly.
        if not hr and not descendants(me):
            frappe.throw(
                "The organisation-wide view is available to managers and HR.",
                frappe.PermissionError,
            )
        return frappe.get_all(
            "Employee", filters={"status": "Active"}, pluck="name", ignore_permissions=True,
        )
    # team
    return manageable_employees() if not hr else frappe.get_all(
        "Employee", filters={"status": "Active"}, pluck="name", ignore_permissions=True,
    )


def _kpi_trajectory(k):
    pct = flt(k.get("attainment_pct"))
    if pct >= KPI_ON_TRACK:
        return "On Track"
    if pct >= KPI_AT_RISK:
        return "At Risk"
    return "Off Track"


def _add_ancestors(goals):
    """Pull in every parent above the matched goals, exactly once each.

    Without this a goal whose parent falls outside the chosen scope renders as
    a root and the cascade looks severed. Collecting the closure in a dict keyed
    by name is also what stops a shared parent being emitted twice when several
    goals descend from it.
    """
    from grace_goals.permissions import MAX_TREE_DEPTH

    by_name = {g["name"]: g for g in goals}
    wanted = set()
    for g in goals:
        parent, depth = g["parent_goal"], 0
        while parent and parent not in by_name and parent not in wanted and depth < MAX_TREE_DEPTH:
            wanted.add(parent)
            parent = frappe.db.get_value("Individual Goal", parent, "parent_goal")
            depth += 1

    if not wanted:
        return goals, set()

    extra = frappe.get_all(
        "Individual Goal", filters={"name": ["in", list(wanted)]},
        fields=GOAL_TREE_FIELDS, ignore_permissions=True,
    )
    return goals + extra, {e["name"] for e in extra}


@frappe.whitelist()
def get_performance_tree(cycle=None, show="all", date_from=None, date_to=None,
                         category=None, scope=None, trajectory=None,
                         progress_min=None, progress_max=None, include_team=None):
    """Objectives arranged by their cascade, with their KPIs nested under them.

    `scope` chooses the population: mine | department | organisation (or the
    legacy `team`, still driven by include_team). Whatever the scope, every
    ancestor of a matched goal is pulled in so the cascade renders whole — each
    appearing exactly once, however many descendants point at it.

    trajectory/progress filter which rows *match*; ancestors are then added for
    structure and flagged `context: 1` so the UI can show them as scaffolding
    rather than results.
    """
    hr = _is_hr()
    me = _employee_id()
    if not me and not hr:
        frappe.throw("No Employee record is linked to your account.")
    me = me or ""

    if not scope:
        scope = "team" if (include_team is None or int(include_team or 0)) else "mine"
    if scope not in ("mine", "department", "organisation", "team"):
        frappe.throw(f"Unknown scope '{scope}'.")

    # HR without an employee record: treat "mine"/"department" as org-wide.
    if not me and hr and scope in ("mine", "department"):
        scope = "team"

    subjects = _scope_employees(scope, me, hr)

    goals = frappe.get_all(
        "Individual Goal",
        filters={"employee": ["in", subjects or [""]], "docstatus": ["!=", 2]},
        fields=GOAL_TREE_FIELDS,
        ignore_permissions=True,
    )

    kpi_filters = {"employee": ["in", subjects or [""]]}
    if cycle:
        kpi_filters["appraisal_cycle"] = cycle
    if category:
        kpi_filters["category"] = category
    kpis = frappe.get_all(
        "KPI", filters=kpi_filters, fields=KPI_FIELDS, ignore_permissions=True,
    )

    # Date window applies to both kinds, against their own period fields.
    if date_from or date_to:
        goals = [g for g in goals
                 if _overlaps(str(g["start_date"] or ""), str(g["end_date"] or ""), date_from, date_to)]
        kpis = [k for k in kpis
                if _overlaps(str(k["period_start"] or ""), str(k["period_end"] or ""), date_from, date_to)]

    # Trajectory / progress narrow what counts as a match.
    wanted_traj = [t.strip() for t in (trajectory or "").split(",") if t.strip()]
    if wanted_traj:
        goals = [g for g in goals if (g["trajectory"] or "Not Started") in wanted_traj]
        kpis = [k for k in kpis if _kpi_trajectory(k) in wanted_traj]

    if progress_min not in (None, ""):
        lo = flt(progress_min)
        goals = [g for g in goals if flt(g["progress_pct"]) >= lo]
        kpis = [k for k in kpis if flt(k["attainment_pct"]) >= lo]
    if progress_max not in (None, ""):
        hi = flt(progress_max)
        goals = [g for g in goals if flt(g["progress_pct"]) <= hi]
        kpis = [k for k in kpis if flt(k["attainment_pct"]) <= hi]

    matched_goals = len(goals)
    goals, context_ids = _add_ancestors(goals)

    user = frappe.session.user
    for g in goals:
        g["type"] = "goal"
        _serialise_dates(g, "start_date", "end_date")
        g["can_edit"] = int(hr or g["owner"] == user)
        g["is_own"] = int(g["employee"] == me)
        g["is_organisational"] = int(not g["parent_goal"] and not g["goal_cascade"])
        g["context"] = int(g["name"] in context_ids)
        g["is_overdue"] = int(_is_overdue(g["end_date"]))
        g["in_cycle"] = g.get("appraisal_cycle") or ""
        g["children"] = []
        g["kpis"] = []
    for k in kpis:
        k["type"] = "kpi"
        k["trajectory"] = _kpi_trajectory(k)
        _serialise_dates(k, "period_start", "period_end")
        k["is_overdue"] = int(_is_overdue(k["period_end"]))
        k["in_cycle"] = k.get("appraisal_cycle") or ""
    _decorate_kpis(kpis)

    by_id = {g["name"]: g for g in goals}

    unattached = []
    if show != "objectives":
        for k in kpis:
            parent = by_id.get(k["individual_goal"])
            if parent:
                parent["kpis"].append(k)
            else:
                unattached.append(k)

    roots = []
    for g in goals:
        parent = by_id.get(g["parent_goal"])
        if parent:
            parent["children"].append(g)
        else:
            # Parent outside the visible slice, or none at all: render as a root.
            roots.append(g)

    def sort_branch(node):
        node["children"].sort(key=lambda c: (c["employee_name"] or "", c["goal_name"] or ""))
        node["kpis"].sort(key=lambda k: (k["employee_name"] or "", k["kpi_name"] or ""))
        for c in node["children"]:
            sort_branch(c)
    roots.sort(key=lambda g: (g["employee_name"] or "", g["goal_name"] or ""))
    for r in roots:
        sort_branch(r)

    if show == "kpis":
        # Flat KPI view: no objective scaffolding at all.
        roots, unattached = [], kpis

    categories = sorted({k["category"] for k in kpis if k.get("category")})
    return {
        "roots": roots,
        "unattached_kpis": unattached,
        "categories": categories,
        "employee_id": me,
        "is_hr": int(hr),
        "scope": scope,
        "scope_size": len(subjects),
        "counts": {
            "objectives": matched_goals,
            "kpis": len(kpis),
            # Ancestors shown purely to keep the cascade intact.
            "context": len(context_ids),
            "total_rows": len(goals),
        },
        "flat_goals": [
            {k: g[k] for k in ("name", "goal_name", "employee", "employee_name",
                               "parent_goal", "goal_cascade", "target_value", "unit",
                               "progress_pct", "status", "trajectory", "start_date",
                               "end_date", "can_edit", "is_own", "is_organisational",
                               "context")}
            for g in goals
        ],
    }


@frappe.whitelist()
def save_kpi(kpi_name, target_value, appraisal_cycle, employee=None, weightage=0,
             unit="Number", direction="Higher is Better", category="Financial",
             baseline_value=0, period_start=None, period_end=None,
             goal_cascade=None, individual_goal=None, description="", kpi=None):
    """Raise or revise a KPI for yourself or for one of your subordinates.

    Creating is open to anyone for themselves or their team; revising an
    existing KPI is restricted to whoever created it (or HR), so a manager
    cannot quietly rewrite a target an employee set for themselves.
    """
    me = _require_employee()
    if kpi:
        existing = frappe.get_doc("KPI", kpi)
        _require_can_edit_kpi(existing)
        employee = employee or existing.employee
        if employee != existing.employee:
            _require_manages(employee)
    else:
        employee = employee or me
        _require_manages(employee)

    return _write_kpi(
        employee=employee, kpi_name=kpi_name, target_value=target_value,
        appraisal_cycle=appraisal_cycle, weightage=weightage, unit=unit,
        direction=direction, category=category, baseline_value=baseline_value,
        period_start=period_start, period_end=period_end, goal_cascade=goal_cascade,
        individual_goal=individual_goal, description=description, kpi=kpi,
    )


@frappe.whitelist()
def delete_kpi(kpi):
    """Delete a KPI you created. HR can delete any."""
    doc = frappe.get_doc("KPI", kpi)
    _require_can_edit_kpi(doc)
    name = doc.kpi_name
    frappe.delete_doc("KPI", kpi, ignore_permissions=True)
    frappe.db.commit()
    return {"message": f"KPI '{name}' deleted."}


@frappe.whitelist()
def hr_save_kpi(employee, kpi_name, target_value, appraisal_cycle, weightage=0,
                unit="Number", direction="Higher is Better", category="Financial",
                baseline_value=0, period_start=None, period_end=None,
                goal_cascade=None, individual_goal=None, description="", kpi=None):
    """Create or update a KPI for any employee. `kpi` set = update."""
    _require_hr()
    return _write_kpi(
        employee=employee, kpi_name=kpi_name, target_value=target_value,
        appraisal_cycle=appraisal_cycle, weightage=weightage, unit=unit,
        direction=direction, category=category, baseline_value=baseline_value,
        period_start=period_start, period_end=period_end, goal_cascade=goal_cascade,
        individual_goal=individual_goal, description=description, kpi=kpi,
    )


@frappe.whitelist()
def hr_cancel_kpi(kpi):
    """Cancel a KPI so it stops counting toward weightage and appraisals."""
    _require_hr()
    frappe.db.set_value("KPI", kpi, "status", "Cancelled")
    frappe.db.commit()
    return {"name": kpi, "message": "KPI cancelled."}


@frappe.whitelist()
def hr_list_kpis(cycle=None, employee=None):
    """All KPIs in the tenant, optionally narrowed. HR sees everyone."""
    _require_hr()
    filters = {}
    if cycle:
        filters["appraisal_cycle"] = cycle
    if employee:
        filters["employee"] = employee
    return _kpi_rows(filters)


@frappe.whitelist()
def hr_generate_appraisals(cycle, attach_ongoing=1):
    """Create one Appraisal per employee with work in this cycle.

    Anything live during the cycle window is pulled in first, so a review starts
    from the work people are actually doing rather than only what someone
    remembered to tag. Employees whose weightages do not total 100% are skipped
    rather than failing the whole run — the response names them so HR can fix
    and re-run. Re-running is safe: existing appraisals are left alone.
    """
    _require_hr()
    cycle_doc = frappe.get_doc("Appraisal Cycle", cycle)

    attached = {"goals": [], "kpis": []}
    if int(attach_ongoing or 0):
        attached = attach_ongoing_to_cycle(cycle)

    employees = set()
    for dt in ("KPI", "Individual Goal"):
        filters = {"appraisal_cycle": cycle, "status": ["!=", "Cancelled"]}
        if dt == "Individual Goal":
            filters["docstatus"] = ["!=", 2]
        employees.update(
            r["employee"] for r in frappe.get_all(dt, filters=filters, fields=["employee"],
                                                  ignore_permissions=True)
        )
    employees = list(employees)
    if not employees:
        frappe.throw(
            "Nothing is attached to this cycle and nothing was live during its dates. "
            "Assign KPIs or goals first."
        )

    created, skipped, existing = [], [], []
    company = _default_company()

    for idx, emp_id in enumerate(sorted(employees)):
        emp_name = frappe.db.get_value("Employee", emp_id, "employee_name") or emp_id

        clash = _existing_appraisal(emp_id, cycle, cycle_doc.start_date, cycle_doc.end_date)
        if clash:
            if clash["appraisal_cycle"] == cycle:
                existing.append(emp_name)
            else:
                # HRMS rejects appraisals whose periods overlap, even across
                # different cycles, so say which one is in the way.
                skipped.append({
                    "employee": emp_name,
                    "reason": f"already has appraisal {clash['name']} for overlapping cycle "
                              f"'{clash['appraisal_cycle']}'",
                })
            continue

        # A savepoint per employee: one bad record must not roll back the
        # appraisals already created in this run.
        savepoint = f"gen_appraisal_{idx}"
        try:
            frappe.db.savepoint(savepoint)
            ap = frappe.new_doc("Appraisal")
            ap.employee = emp_id
            ap.appraisal_cycle = cycle
            ap.company = company
            ap.start_date = cycle_doc.start_date
            ap.end_date = cycle_doc.end_date
            ap.rate_goals_manually = 1
            _apply_kpis_to_appraisal(ap)
            ap.insert(ignore_permissions=True)
            created.append(emp_name)
        except Exception as e:
            # Deliberately broad: HRMS raises DuplicateEntryError (a NameError
            # subclass, not a ValidationError) as well as ValidationError here,
            # and neither should abort the other employees' appraisals.
            frappe.db.rollback(save_point=savepoint)
            skipped.append({"employee": emp_name, "reason": _plain(str(e))})

    if cycle_doc.status == "Not Started" and created:
        frappe.db.set_value("Appraisal Cycle", cycle, "status", "In Progress")

    frappe.db.commit()
    pulled = len(attached["goals"]) + len(attached["kpis"])
    msg = (f"{len(created)} appraisal(s) created, {len(existing)} already existed, "
           f"{len(skipped)} skipped.")
    if pulled:
        msg = (f"Pulled in {len(attached['goals'])} ongoing goal(s) and "
               f"{len(attached['kpis'])} KPI(s). ") + msg
    return {
        "created": created,
        "existing": existing,
        "skipped": skipped,
        "attached": attached,
        "message": msg,
    }


@frappe.whitelist()
def hr_cycle_summary(cycle):
    """Progress board for one cycle: who is assigned, rated, and submitted."""
    _require_hr()

    kpis = frappe.get_all(
        "KPI",
        filters={"appraisal_cycle": cycle, "status": ["!=", "Cancelled"]},
        fields=["employee", "employee_name", "weightage", "manager_rating", "attainment_pct"],
    )
    appraisals = {
        a["employee"]: a
        for a in frappe.get_all(
            "Appraisal",
            filters={"appraisal_cycle": cycle, "docstatus": ["!=", 2]},
            fields=["name", "employee", "docstatus", "total_score", "final_score"],
        )
    }

    by_emp = {}
    for k in kpis:
        e = by_emp.setdefault(k["employee"], {
            "employee": k["employee"],
            "employee_name": k["employee_name"],
            "kpi_count": 0, "total_weightage": 0, "rated": 0, "attainment": 0,
        })
        e["kpi_count"] += 1
        e["total_weightage"] += flt(k["weightage"])
        e["attainment"] += flt(k["attainment_pct"])
        if flt(k["manager_rating"]) > 0:
            e["rated"] += 1

    rows = []
    for e in by_emp.values():
        ap = appraisals.get(e["employee"])
        e["total_weightage"] = flt(e["total_weightage"], 2)
        e["weightage_ok"] = e["total_weightage"] == TOTAL_WEIGHTAGE
        e["avg_attainment"] = flt(e["attainment"] / e["kpi_count"], 1) if e["kpi_count"] else 0
        e.pop("attainment")
        e["appraisal"] = ap["name"] if ap else ""
        e["submitted"] = bool(ap and ap["docstatus"] == 1)
        e["final_score"] = flt(ap["final_score"]) if ap else 0
        rows.append(e)

    rows.sort(key=lambda r: r["employee_name"] or "")
    return {
        "cycle": cycle,
        "rows": rows,
        "assigned": len(rows),
        "with_appraisal": sum(1 for r in rows if r["appraisal"]),
        "submitted": sum(1 for r in rows if r["submitted"]),
    }


# ══════════════════════════════════════════════════════════════════════════
# Grace Appraisal Extension — review workflow, narrative, action items
# ══════════════════════════════════════════════════════════════════════════

_REVIEW_STATUS_FLOW = {
    "Not Started": "Employee Review",
    "Employee Review": "Manager Review",
    "Manager Review": "Employee Final Review",
    "Employee Final Review": "HR Review",
    "HR Review": "Completed",
}


def _get_or_create_extension(appraisal):
    """Return the GraceAppraisalExtension for this appraisal, creating it if absent."""
    if frappe.db.exists("Grace Appraisal Extension", appraisal):
        return frappe.get_doc("Grace Appraisal Extension", appraisal)
    ext = frappe.new_doc("Grace Appraisal Extension")
    ext.appraisal = appraisal
    ext.review_status = "Not Started"
    ext.insert(ignore_permissions=True)
    frappe.db.commit()
    return ext


@frappe.whitelist()
def get_appraisal_extension(appraisal):
    """Return the full Grace Appraisal Extension for the given appraisal."""
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)
    if not _is_hr() and ap.employee != me and ap.employee not in _subordinates(me):
        frappe.throw("Not permitted.", frappe.PermissionError)

    ext = _get_or_create_extension(appraisal)
    action_items = [
        {
            "name": row.name,
            "description": row.description,
            "assigned_to": row.assigned_to or "",
            "assigned_to_name": row.assigned_to_name or "",
            "due_date": str(row.due_date) if row.due_date else "",
            "status": row.status or "Open",
        }
        for row in (ext.action_items or [])
    ]
    is_employee_self = (ap.employee == me)
    return {
        "appraisal": appraisal,
        "review_status": ext.review_status or "Not Started",
        "avg_potential_rating": flt(ext.avg_potential_rating),
        "potential_category": ext.potential_category or "",
        "achievements_text": ext.achievements_text or "",
        "challenges_text": ext.challenges_text or "",
        "development_needs_text": ext.development_needs_text or "",
        "support_needed": ext.support_needed or "",
        # Overall rating: shown to employee only after they submit (Completed status)
        "overall_rating": flt(ext.overall_rating) if (
            not is_employee_self or ext.review_status == "Completed"
        ) else None,
        "next_period_goals_text": ext.next_period_goals_text or "",
        "return_reason": ext.return_reason or "",
        "action_items": action_items,
    }


@frappe.whitelist()
def save_self_review_narrative(appraisal, achievements_text="", challenges_text="",
                               development_needs_text=""):
    """Employee fills in their structured self-review narrative."""
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)
    if ap.employee != me:
        frappe.throw("Not permitted.", frappe.PermissionError)
    if ap.docstatus == 1:
        frappe.throw("This appraisal is already submitted.")

    ext = _get_or_create_extension(appraisal)
    if ext.review_status not in ("Not Started", "Employee Review"):
        frappe.throw("Self-review narrative can only be edited during Employee Review stage.")

    ext.achievements_text = achievements_text
    ext.challenges_text = challenges_text
    ext.development_needs_text = development_needs_text
    ext.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": "Self-review narrative saved."}


@frappe.whitelist()
def save_forward_planning(appraisal, next_period_goals_text=""):
    """Employee or manager fills in goals for the next period."""
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)
    if not _is_hr() and ap.employee != me and ap.employee not in _reports_of(me):
        frappe.throw("Not permitted.", frappe.PermissionError)
    if ap.docstatus == 1:
        frappe.throw("This appraisal is already submitted.")

    ext = _get_or_create_extension(appraisal)
    ext.next_period_goals_text = next_period_goals_text
    ext.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": "Forward planning saved."}


@frappe.whitelist()
def advance_review_status(appraisal):
    """Move the review to the next stage.

    Not Started → Employee Review (employee triggers)
    Employee Review → Manager Review (employee submits self-review)
    Manager Review → Employee Final Review (manager submits — use submit_manager_review instead)
    Employee Final Review → HR Review (employee acknowledges — use acknowledge_final_review instead)
    HR Review → Completed (HR triggers)
    """
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)

    ext = _get_or_create_extension(appraisal)
    current = ext.review_status or "Not Started"
    nxt = _REVIEW_STATUS_FLOW.get(current)
    if not nxt:
        frappe.throw("Review is already Completed.")

    # Authorisation: who can advance from each stage
    if current in ("Not Started", "Employee Review"):
        if ap.employee != me:
            frappe.throw("Only the employee can advance from this stage.", frappe.PermissionError)
    elif current == "Manager Review":
        if not _is_hr() and ap.employee not in _reports_of(me):
            frappe.throw("Only the direct manager or HR can advance from Manager Review.",
                         frappe.PermissionError)
        open_items = [r for r in (ext.action_items or []) if r.status != "Completed"]
        if not ext.action_items:
            frappe.throw("At least one action item must be added before advancing the review. "
                         "Use the 'Add Action Item' button in the team review card.")
    elif current == "Employee Final Review":
        if ap.employee != me:
            frappe.throw("Only the subject employee can acknowledge the final review.",
                         frappe.PermissionError)
    elif current == "HR Review":
        _require_hr()

    ext.review_status = nxt
    ext.return_reason = ""
    ext.save(ignore_permissions=True)
    frappe.db.commit()

    emp_user = _employee_user(ap.employee)
    mgr_user = _manager_user(ap.employee)
    emp_name = frappe.db.get_value("Employee", ap.employee, "employee_name") or ap.employee

    if nxt == "Manager Review" and mgr_user:
        _send_notification(
            mgr_user,
            f"Action required: {emp_name}'s self-review is ready",
            f"<p>{emp_name} has submitted their self-review. Please open the performance portal to begin your manager assessment.</p>",
        )
    elif nxt == "HR Review" and _is_hr():
        pass
    elif nxt == "Completed" and emp_user:
        _send_notification(
            emp_user,
            "Your appraisal review is complete",
            f"<p>Your performance review has been completed. Log in to view your final assessment.</p>",
        )

    return {"review_status": nxt, "message": f"Review moved to '{nxt}'."}


@frappe.whitelist()
def return_for_revision(appraisal, reason=""):
    """Manager or HR sends a review back to Employee Review with a reason."""
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)

    ext = _get_or_create_extension(appraisal)
    current = ext.review_status or "Not Started"
    if current not in ("Manager Review", "HR Review"):
        frappe.throw("Can only return reviews that are in Manager Review or HR Review stage.")

    if current == "Manager Review":
        if not _is_hr() and ap.employee not in _reports_of(me):
            frappe.throw("Only the direct manager or HR can return a review.",
                         frappe.PermissionError)
    else:
        _require_hr()

    ext.review_status = "Employee Review"
    ext.return_reason = reason
    ext.save(ignore_permissions=True)
    frappe.db.commit()

    emp_user = _employee_user(ap.employee)
    emp_name = frappe.db.get_value("Employee", ap.employee, "employee_name") or ap.employee
    if emp_user:
        _send_notification(
            emp_user,
            "Your review has been returned for revision",
            f"<p>Your performance review has been returned to you for revision."
            f"{(' Reason: ' + reason) if reason else ''} Please log in to update your self-review.</p>",
        )

    return {"review_status": "Employee Review", "message": "Review returned to employee."}


@frappe.whitelist()
def return_to_manager(appraisal, reason=""):
    """Employee sends their Final Review back to the manager requesting amendments."""
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)

    if ap.employee != me:
        frappe.throw("Only the employee can return their own review to the manager.",
                     frappe.PermissionError)

    ext = _get_or_create_extension(appraisal)
    if (ext.review_status or "") != "Employee Final Review":
        frappe.throw("This action is only available in the Employee Final Review stage.")

    ext.review_status = "Manager Review"
    ext.return_reason = reason
    ext.save(ignore_permissions=True)
    frappe.db.commit()

    # Notify the manager
    mgr_emp = frappe.db.get_value("Employee", ap.employee, "reports_to")
    emp_name = frappe.db.get_value("Employee", ap.employee, "employee_name") or ap.employee
    if mgr_emp:
        mgr_user = _employee_user(mgr_emp)
        if mgr_user:
            _send_notification(
                mgr_user,
                f"{emp_name} has requested amendments to their review",
                f"<p>{emp_name} has read your feedback and is requesting revisions."
                f"{(' Note: ' + reason) if reason else ''} Please log in to update your review.</p>",
            )

    return {"review_status": "Manager Review", "message": "Review sent back to manager for amendments."}


@frappe.whitelist()
def add_action_item(appraisal, description, assigned_to="", due_date=""):
    """Add an action item to an appraisal's extension. Manager or HR only."""
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)
    if not _is_hr() and ap.employee not in _reports_of(me):
        frappe.throw("Not permitted.", frappe.PermissionError)

    if not description:
        frappe.throw("Action item description is required.")

    ext = _get_or_create_extension(appraisal)
    row = ext.append("action_items", {
        "description": description,
        "assigned_to": assigned_to or None,
        "due_date": due_date or None,
        "status": "Open",
    })
    ext.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": "Action item added.", "row_name": row.name}


@frappe.whitelist()
def update_action_item_status(appraisal, row_name, status):
    """Update the status of a single action item."""
    if status not in ("Open", "In Progress", "Completed"):
        frappe.throw("Status must be Open, In Progress, or Completed.")

    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)
    ext = _get_or_create_extension(appraisal)

    row = next((r for r in ext.action_items if r.name == row_name), None)
    if not row:
        frappe.throw("Action item not found.")

    is_assignee = row.assigned_to and frappe.db.get_value(
        "Employee", {"user_id": frappe.session.user}, "name"
    ) == row.assigned_to

    if not (_is_hr() or ap.employee in _reports_of(me) or is_assignee):
        frappe.throw("Not permitted.", frappe.PermissionError)

    row.status = status
    ext.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": f"Action item marked {status}."}


# ══════════════════════════════════════════════════════════════════════════
# Additional reviewers (dotted-line managers / secondary raters)
# ══════════════════════════════════════════════════════════════════════════

def _require_can_review_or_additional(kpi_doc):
    """Caller must be the direct manager, an additional reviewer, or HR."""
    if _is_hr():
        return
    me = _require_employee()
    if kpi_doc.employee in _reports_of(me):
        return
    reviewer_ids = [r.reviewer for r in (kpi_doc.additional_reviewers or [])]
    if me in reviewer_ids:
        return
    frappe.throw("You are not authorised to review this KPI.", frappe.PermissionError)


@frappe.whitelist()
def add_additional_reviewer(kpi, reviewer, reviewer_role=""):
    """Add a secondary reviewer (dotted-line manager) to a KPI. Manager or HR only."""
    doc = frappe.get_doc("KPI", kpi)
    _require_can_review(doc.employee)

    if frappe.db.get_value("Employee", reviewer, "name") is None:
        frappe.throw(f"Employee '{reviewer}' not found.")

    existing = [r.reviewer for r in (doc.additional_reviewers or [])]
    if reviewer in existing:
        frappe.throw("This reviewer is already on the KPI.")

    doc.append("additional_reviewers", {
        "reviewer": reviewer,
        "reviewer_role": reviewer_role,
        "reviewed_on": None,
    })
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": "Additional reviewer added."}


@frappe.whitelist()
def save_additional_reviewer_rating(kpi, row_name, rating, comment=""):
    """An additional reviewer saves their rating on a KPI row."""
    from frappe.utils import now_datetime
    doc = frappe.get_doc("KPI", kpi)
    _require_can_review_or_additional(doc)

    rating = flt(rating)
    if rating < 0 or rating > MAX_RATING:
        frappe.throw(f"Rating must be between 0 and {int(MAX_RATING)}.")

    row = next((r for r in doc.additional_reviewers if r.name == row_name), None)
    if not row:
        frappe.throw("Reviewer row not found.")

    row.rating = rating
    row.comment = comment
    row.reviewed_on = now_datetime()
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": "Rating saved."}


# ══════════════════════════════════════════════════════════════════════════
# Company values
# ══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_company_values():
    """List active company values. Available to any logged-in user."""
    if frappe.session.user == "Guest":
        frappe.throw("Please log in.", frappe.PermissionError)
    return frappe.get_all(
        "Company Value",
        filters={"is_active": 1},
        fields=["name", "value_name", "icon_emoji", "description"],
        order_by="value_name asc",
    )


@frappe.whitelist()
def save_company_value(value_name, icon_emoji="", description="", name=None, is_active=1):
    """Create or update a Company Value. HR only."""
    _require_hr()
    if not value_name:
        frappe.throw("Value name is required.")

    if name and frappe.db.exists("Company Value", name):
        doc = frappe.get_doc("Company Value", name)
    else:
        doc = frappe.new_doc("Company Value")

    doc.value_name = value_name
    doc.icon_emoji = icon_emoji
    doc.description = description
    doc.is_active = int(is_active or 0)

    if doc.is_new():
        doc.insert(ignore_permissions=True)
    else:
        doc.save(ignore_permissions=True)

    frappe.db.commit()
    return {"name": doc.name, "message": "Company value saved."}


@frappe.whitelist()
def delete_company_value(name):
    """Delete a Company Value. HR only."""
    _require_hr()
    if not frappe.db.exists("Company Value", name):
        frappe.throw("Company Value not found.")
    frappe.delete_doc("Company Value", name, ignore_permissions=True)
    frappe.db.commit()
    return {"message": "Company value deleted."}


# ══════════════════════════════════════════════════════════════════════════
# Exports
# ══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def export_cycle_kpis_csv(cycle):
    """Return all KPIs for a cycle as a CSV string. HR only."""
    _require_hr()

    kpis = frappe.get_all(
        "KPI",
        filters={"appraisal_cycle": cycle, "status": ["!=", "Cancelled"]},
        fields=[
            "name", "kpi_name", "employee", "employee_name",
            "category", "unit", "direction", "target_value", "actual_value",
            "attainment_pct", "weightage",
            "self_rating", "self_comment",
            "manager_rating", "manager_comment",
            "potential_rating", "potential_comment",
            "company_value", "is_extra_initiative",
            "status",
        ],
        order_by="employee_name asc, kpi_name asc",
        ignore_permissions=True,
    )

    import csv, io
    buf = io.StringIO()
    headers = [
        "KPI ID", "KPI Name", "Employee ID", "Employee Name",
        "Category", "Unit", "Direction", "Target", "Actual",
        "Attainment %", "Weightage %",
        "Self Rating", "Self Comment",
        "Manager Rating", "Manager Comment",
        "Potential Rating", "Potential Comment",
        "Company Value", "Stretch/Extra Initiative",
        "Status",
    ]
    writer = csv.writer(buf)
    writer.writerow(headers)
    for k in kpis:
        writer.writerow([
            k.get("name", ""), k.get("kpi_name", ""),
            k.get("employee", ""), k.get("employee_name", ""),
            k.get("category", ""), k.get("unit", ""), k.get("direction", ""),
            flt(k.get("target_value")), flt(k.get("actual_value")),
            flt(k.get("attainment_pct")), flt(k.get("weightage")),
            flt(k.get("self_rating")), k.get("self_comment", ""),
            flt(k.get("manager_rating")), k.get("manager_comment", ""),
            flt(k.get("potential_rating")), k.get("potential_comment", ""),
            k.get("company_value", ""), int(k.get("is_extra_initiative") or 0),
            k.get("status", ""),
        ])

    return {"csv": buf.getvalue(), "cycle": cycle}


# ══════════════════════════════════════════════════════════════════════════
# Leadership Principles (FR-10)
# ══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_leadership_principles():
    """Return all active leadership principles. Available to any logged-in user."""
    if frappe.session.user == "Guest":
        frappe.throw("Please log in.", frappe.PermissionError)
    return frappe.get_all(
        "Leadership Principle",
        filters={"is_active": 1},
        fields=["name", "principle_name", "description", "expected_behaviours"],
        order_by="principle_name asc",
    )


@frappe.whitelist()
def save_leadership_principle(principle_name, description="", expected_behaviours="",
                               is_active=1, name=None):
    """Create or update a Leadership Principle. HR only."""
    _require_hr()
    if not principle_name:
        frappe.throw("Principle name is required.")

    if name and frappe.db.exists("Leadership Principle", name):
        doc = frappe.get_doc("Leadership Principle", name)
    else:
        doc = frappe.new_doc("Leadership Principle")

    doc.principle_name = principle_name
    doc.description = description
    doc.expected_behaviours = expected_behaviours
    doc.is_active = int(is_active or 0)

    if doc.is_new():
        doc.insert(ignore_permissions=True)
    else:
        doc.save(ignore_permissions=True)

    frappe.db.commit()
    return {"name": doc.name, "message": "Leadership principle saved."}


@frappe.whitelist()
def delete_leadership_principle(name):
    """Delete a Leadership Principle. HR only."""
    _require_hr()
    if not frappe.db.exists("Leadership Principle", name):
        frappe.throw("Leadership Principle not found.")
    frappe.delete_doc("Leadership Principle", name, ignore_permissions=True)
    frappe.db.commit()
    return {"message": "Leadership principle deleted."}


# ══════════════════════════════════════════════════════════════════════════
# Upward Feedback — principles-based retrieval (FR-10)
# ══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_upward_feedback_received(cycle):
    """Return aggregated upward feedback about the current user as a manager.
    Only returned when minimum-respondent threshold (3) is met; else count only.
    """
    me = _require_employee()
    rows = frappe.get_all(
        "Upward Feedback",
        filters={"about_employee": me, "appraisal_cycle": cycle},
        fields=["from_employee", "rating", "comments", "submitted_on"],
        ignore_permissions=True,
    )
    count = len(rows)
    MIN_THRESHOLD = 3
    if count < MIN_THRESHOLD:
        return {"count": count, "threshold": MIN_THRESHOLD, "below_threshold": True}

    avg_rating = sum(flt(r["rating"]) for r in rows) / count if count else 0
    return {
        "count": count,
        "threshold": MIN_THRESHOLD,
        "below_threshold": False,
        "avg_rating": flt(avg_rating, 2),
        "comments": [r["comments"] for r in rows if r.get("comments")],
    }


# ══════════════════════════════════════════════════════════════════════════
# Self-review — support_needed + overall_rating (FR-6, FR-9)
# ══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def save_support_needed(appraisal, support_needed=""):
    """Employee records what support they need from their manager."""
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)
    if ap.employee != me:
        frappe.throw("Not permitted.", frappe.PermissionError)
    ext = _get_or_create_extension(appraisal)
    if ext.review_status not in ("Not Started", "Employee Review"):
        frappe.throw("Support field can only be edited during Employee Review stage.")
    ext.support_needed = support_needed
    ext.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": "Saved."}


@frappe.whitelist()
def save_overall_rating(appraisal, overall_rating):
    """Manager records the overall rating. Hidden from employee until their final submission."""
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)
    if not _is_hr() and ap.employee not in _reports_of(me):
        frappe.throw("Not permitted.", frappe.PermissionError)
    rating = flt(overall_rating)
    if rating < 0 or rating > MAX_RATING:
        frappe.throw(f"Rating must be between 0 and {int(MAX_RATING)}.")
    ext = _get_or_create_extension(appraisal)
    ext.overall_rating = rating
    ext.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": "Overall rating saved."}


# ══════════════════════════════════════════════════════════════════════════
# Calibration overview (FR-11)
# ══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_calibration_overview(cycle):
    """Return all employees in a cycle with KPI summary and potential data. HR only."""
    _require_hr()

    kpis = frappe.get_all(
        "KPI",
        filters={"appraisal_cycle": cycle, "status": ["!=", "Cancelled"]},
        fields=["employee", "employee_name", "manager_rating", "potential_rating",
                "attainment_pct", "weightage"],
        ignore_permissions=True,
    )

    appraisals = {
        a["employee"]: a
        for a in frappe.get_all(
            "Appraisal",
            filters={"appraisal_cycle": cycle, "docstatus": ["!=", 2]},
            fields=["name", "employee", "total_score", "final_score"],
            ignore_permissions=True,
        )
    }

    extensions = {}
    for ap in appraisals.values():
        if frappe.db.exists("Grace Appraisal Extension", ap["name"]):
            ext = frappe.get_doc("Grace Appraisal Extension", ap["name"])
            extensions[ap["employee"]] = {
                "review_status": ext.review_status or "Not Started",
                "avg_potential_rating": flt(ext.avg_potential_rating),
                "potential_category": ext.potential_category or "",
                "overall_rating": flt(ext.overall_rating),
                "action_items_count": len(ext.action_items or []),
            }

    by_emp = {}
    for k in kpis:
        emp = k["employee"]
        e = by_emp.setdefault(emp, {
            "employee": emp,
            "employee_name": k["employee_name"] or emp,
            "kpi_count": 0, "rated_count": 0,
            "total_attainment": 0.0, "total_potential": 0.0, "potential_count": 0,
        })
        e["kpi_count"] += 1
        e["total_attainment"] += flt(k["attainment_pct"])
        if flt(k["manager_rating"]) > 0:
            e["rated_count"] += 1
        if flt(k["potential_rating"]) > 0:
            e["total_potential"] += flt(k["potential_rating"])
            e["potential_count"] += 1

    rows = []
    for emp, e in by_emp.items():
        e["avg_attainment"] = flt(e["total_attainment"] / e["kpi_count"], 1) if e["kpi_count"] else 0
        e["avg_potential"] = flt(e["total_potential"] / e["potential_count"], 2) if e["potential_count"] else 0
        e.pop("total_attainment"); e.pop("total_potential"); e.pop("potential_count")
        ap = appraisals.get(emp)
        e["appraisal"] = ap["name"] if ap else ""
        ext = extensions.get(emp, {})
        e.update(ext)
        rows.append(e)

    rows.sort(key=lambda r: r["employee_name"] or "")
    return {"cycle": cycle, "rows": rows}


@frappe.whitelist()
def save_calibration_note(appraisal, calibration_notes, calibrated_rating=None):
    """HR saves calibration notes and optional adjusted rating on an appraisal extension."""
    _require_hr()
    if not appraisal:
        frappe.throw("Appraisal is required.")
    ext = _get_or_create_extension(appraisal)
    if not hasattr(ext, "calibration_notes"):
        frappe.db.set_value("Grace Appraisal Extension", ext.name,
                            "calibration_notes", calibration_notes)
        if calibrated_rating is not None:
            frappe.db.set_value("Grace Appraisal Extension", ext.name,
                                "overall_rating", flt(calibrated_rating))
    else:
        ext.calibration_notes = calibration_notes
        if calibrated_rating is not None:
            ext.overall_rating = flt(calibrated_rating)
        ext.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": "Calibration note saved."}


@frappe.whitelist()
def get_calibration_matrix(cycle):
    """Return completed appraisals for the 2D calibration matrix. HR only."""
    import json as _json
    _require_hr()

    # ── Rating scale config from cycle ──────────────────────────────────
    overall_scale_name = ""
    potential_scale_name = ""
    show_potential = False
    if frappe.db.exists("Grace Cycle Config", cycle):
        cfg_ps = frappe.db.get_value("Grace Cycle Config", cycle, "page_settings") or "{}"
        try:
            ps = _json.loads(cfg_ps)
            mgf = ps.get("manager-feedback", {})
            overall_scale_name = mgf.get("overall_rating_scale", "") or ""
            potential_scale_name = mgf.get("potential_rating_scale", "") or ""
            show_potential = bool(mgf.get("show_potential"))
        except Exception:
            pass

    def _fetch_scale(name, ascending=True):
        if not name or not frappe.db.exists("Grace Rating Scale", name):
            return None
        info = frappe.db.get_value(
            "Grace Rating Scale", name, ["scale_name", "description"], as_dict=True
        ) or {}
        items = frappe.get_all(
            "Grace Rating Scale Item",
            filters={"parent": name},
            fields=["label", "value", "color"],
            order_by="value asc" if ascending else "value desc",
        )
        return {"scale_name": info.get("scale_name", name), "items": items}

    overall_scale = _fetch_scale(overall_scale_name)
    potential_scale = _fetch_scale(potential_scale_name) if show_potential else None

    # ── Cycle metadata (duration) ────────────────────────────────────────
    ci = frappe.db.get_value(
        "Appraisal Cycle", cycle,
        ["cycle_name", "start_date", "end_date"], as_dict=True,
    ) or {}
    cycle_info = {
        "cycle_name": str(ci.get("cycle_name") or cycle),
        "start_date": str(ci.get("start_date") or ""),
        "end_date":   str(ci.get("end_date") or ""),
    }

    # ── All appraisals in cycle ──────────────────────────────────────────
    appraisals = frappe.get_all(
        "Appraisal",
        filters={"appraisal_cycle": cycle, "docstatus": ["!=", 2]},
        fields=["name", "employee"],
        ignore_permissions=True,
    )

    rows = []
    stage_counts = {}
    filter_depts, filter_desig, filter_genders, filter_emp_types = set(), set(), set(), set()
    filter_managers = {}  # emp_id -> employee_name

    for ap in appraisals:
        ap_name = ap["name"]
        emp_id  = ap["employee"]

        # Fetch extension (one call covers both exists-check and field values)
        ext = {}
        if frappe.db.exists("Grace Appraisal Extension", ap_name):
            ext = frappe.db.get_value(
                "Grace Appraisal Extension", ap_name,
                ["review_status", "overall_rating", "potential_rating"],
                as_dict=True,
            ) or {}

        status = (ext.get("review_status") or "").strip() or "Not Started"
        stage_counts[status] = stage_counts.get(status, 0) + 1

        # Only plot completed reviews on the matrix
        if status != "Completed":
            continue

        emp = frappe.db.get_value(
            "Employee", emp_id,
            ["employee_name", "department", "designation", "gender",
             "employment_type", "reports_to"],
            as_dict=True,
        ) or {}

        reports_to      = emp.get("reports_to") or ""
        reports_to_name = ""
        if reports_to:
            reports_to_name = frappe.db.get_value("Employee", reports_to, "employee_name") or reports_to
            filter_managers[reports_to] = reports_to_name

        dept     = emp.get("department")     or ""
        desig    = emp.get("designation")    or ""
        gender   = emp.get("gender")         or ""
        emp_type = emp.get("employment_type") or ""

        if dept:     filter_depts.add(dept)
        if desig:    filter_desig.add(desig)
        if gender:   filter_genders.add(gender)
        if emp_type: filter_emp_types.add(emp_type)

        rows.append({
            "employee":        emp_id,
            "employee_name":   emp.get("employee_name", emp_id),
            "appraisal":       ap_name,
            "overall_rating":  flt(ext.get("overall_rating")),
            "potential_rating": flt(ext.get("potential_rating")),
            "department":      dept,
            "designation":     desig,
            "gender":          gender,
            "employment_type": emp_type,
            "reports_to":      reports_to,
            "reports_to_name": reports_to_name,
        })

    rows.sort(key=lambda r: r["employee_name"])

    return {
        "cycle":            cycle,
        "cycle_info":       cycle_info,
        "all_participants": len(appraisals),
        "stage_counts":     stage_counts,
        "rows":             rows,
        "overall_scale":    overall_scale,
        "potential_scale":  potential_scale,
        "show_potential":   show_potential,
        "filter_options": {
            "departments":      sorted(filter_depts),
            "designations":     sorted(filter_desig),
            "genders":          sorted(filter_genders),
            "employment_types": sorted(filter_emp_types),
            "managers": [
                {"id": k, "name": v}
                for k, v in sorted(filter_managers.items(), key=lambda x: x[1])
            ],
        },
    }


# ══════════════════════════════════════════════════════════════════════════
# Email notifications (FR-13) — helpers
# ══════════════════════════════════════════════════════════════════════════

def _send_notification(to_user, subject, message):
    """Send an in-app + email notification. Silently skips if user not found."""
    try:
        frappe.sendmail(
            recipients=[to_user],
            subject=subject,
            message=message,
        )
        frappe.publish_realtime(
            "eval_js",
            {"script": "console.log('notification sent');"},
            user=to_user,
        )
    except Exception:
        pass


def _employee_user(employee_id):
    return frappe.db.get_value("Employee", employee_id, "user_id") or ""


def _manager_user(employee_id):
    mgr = get_effective_manager(employee_id)
    if mgr:
        return frappe.db.get_value("Employee", mgr, "user_id") or ""
    return ""


# ══════════════════════════════════════════════════════════════════════════
# My Reviews list (employee view)
# ══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_my_appraisals():
    """Return appraisals for the logged-in employee plus reviews where they are an invited reviewer."""
    import json as _json
    me = _employee_id()   # returns None instead of throwing — graceful for users without employee record
    if not me:
        return {"own": [], "invited": []}

    # ── Own appraisals ────────────────────────────────────────────────────
    appraisals = frappe.get_all(
        "Appraisal",
        filters={"employee": me},
        fields=["name", "appraisal_cycle", "start_date", "end_date", "final_score"],
        order_by="end_date desc",
        ignore_permissions=True,
    )

    ext_map = {}
    if appraisals:
        ap_names = [a["name"] for a in appraisals]
        for ext in frappe.get_all(
            "Grace Appraisal Extension",
            filters={"appraisal": ["in", ap_names]},
            fields=["appraisal", "review_status", "overall_rating", "return_reason"],
            ignore_permissions=True,
        ):
            ext_map[ext["appraisal"]] = ext

    cycle_names = list({a["appraisal_cycle"] for a in appraisals if a["appraisal_cycle"]})
    cycle_map = {}
    if cycle_names:
        for cy in frappe.get_all(
            "Appraisal Cycle",
            filters={"name": ["in", cycle_names]},
            fields=["name", "cycle_name", "status"],
        ):
            cycle_map[cy["name"]] = cy

    own = []
    for ap in appraisals:
        ext = ext_map.get(ap["name"]) or {}
        cy = cycle_map.get(ap["appraisal_cycle"]) or {}
        own.append({
            "name":            ap["name"],
            "appraisal_cycle": ap["appraisal_cycle"],
            "cycle_name":      cy.get("cycle_name") or ap["appraisal_cycle"],
            "cycle_status":    cy.get("status") or "",
            "start_date":      str(ap["start_date"] or ""),
            "end_date":        str(ap["end_date"] or ""),
            "review_status":   ext.get("review_status") or "Not Started",
            "overall_rating":  ext.get("overall_rating"),
            "return_reason":   ext.get("return_reason") or "",
        })

    # ── Reviews where I am an invited reviewer ────────────────────────────
    # Use a LIKE search on the JSON blob to cheaply narrow rows, then filter precisely in Python
    candidate_exts = frappe.get_all(
        "Grace Appraisal Extension",
        filters={"invited_reviewers": ["like", "%" + me + "%"]},
        fields=["appraisal", "invited_reviewers", "review_status", "employee"],
        ignore_permissions=True,
    )

    invited_cycle_names = set()
    invited_rows = []
    for ext in candidate_exts:
        try:
            reviewers = _json.loads(ext["invited_reviewers"] or "[]")
        except Exception:
            continue
        my_entry = next((r for r in reviewers if r.get("employee") == me), None)
        if not my_entry:
            continue
        invited_cycle_names.add(
            frappe.db.get_value("Appraisal", ext["appraisal"], "appraisal_cycle") or ""
        )
        ap_doc = frappe.db.get_value(
            "Appraisal", ext["appraisal"], ["appraisal_cycle", "start_date", "end_date"], as_dict=True
        ) or {}
        invited_rows.append({
            "appraisal":       ext["appraisal"],
            "employee":        ext["employee"],
            "employee_name":   frappe.db.get_value("Employee", ext["employee"], "employee_name") or ext["employee"],
            "appraisal_cycle": ap_doc.get("appraisal_cycle") or "",
            "start_date":      str(ap_doc.get("start_date") or ""),
            "end_date":        str(ap_doc.get("end_date") or ""),
            "review_status":   ext["review_status"] or "Manager Review",
            "my_reviewer_status": my_entry.get("status", "Invited"),
        })

    # Fill cycle names for invited rows
    if invited_cycle_names:
        inv_cycle_map = {}
        for cy in frappe.get_all(
            "Appraisal Cycle",
            filters={"name": ["in", list(invited_cycle_names)]},
            fields=["name", "cycle_name"],
        ):
            inv_cycle_map[cy["name"]] = cy["cycle_name"]
        for r in invited_rows:
            r["cycle_name"] = inv_cycle_map.get(r["appraisal_cycle"]) or r["appraisal_cycle"]

    return {"own": own, "invited": invited_rows}


# ══════════════════════════════════════════════════════════════════════════
# Employee Review Wizard
# ══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_my_review(appraisal):
    """Return everything the review wizard needs: page config, goals, KPIs, and saved page data."""
    import json
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)
    if ap.employee != me and not _is_hr():
        frappe.throw("Not permitted.", frappe.PermissionError)

    cycle_name = ap.appraisal_cycle
    page_config, page_settings = [], {}
    if frappe.db.exists("Grace Cycle Config", cycle_name):
        cfg = frappe.get_doc("Grace Cycle Config", cycle_name)
        try: page_config = json.loads(cfg.page_config or "[]")
        except: pass
        try: page_settings = json.loads(cfg.page_settings or "{}")
        except: pass

    ext = _get_or_create_extension(appraisal)
    try: page_data = json.loads(ext.page_data or "{}")
    except: page_data = {}
    try: pages_completed = json.loads(ext.pages_completed or "[]")
    except: pages_completed = []

    # Goals hierarchy: Individual Goal → KPIs
    goals = frappe.get_all(
        "Individual Goal",
        filters={"employee": ap.employee, "appraisal_cycle": cycle_name, "docstatus": ["!=", 2]},
        fields=["name", "goal_name", "parent_goal", "is_extra_initiative",
                "target_value", "actual_progress", "progress_pct",
                "unit", "status", "start_date", "end_date", "weightage", "employee", "owner"],
        ignore_permissions=True, order_by="creation asc",
    )
    # Batch-resolve creator names (owner is a User email)
    owner_emails = list({g["owner"] for g in goals if g.get("owner")})
    user_full_names = {}
    if owner_emails:
        for u in frappe.get_all("User", filters={"name": ["in", owner_emails]},
                                fields=["name", "full_name"], ignore_permissions=True):
            user_full_names[u["name"]] = u["full_name"]
    # Resolve employee display name for the review subject
    assignee_name = frappe.db.get_value("Employee", ap.employee, "employee_name") or ap.employee_name or ""
    for g in goals:
        g["creator_name"] = user_full_names.get(g.get("owner", ""), "")
        g["assignee_name"] = assignee_name
        _serialise_dates(g, "start_date", "end_date")
        g["kpis"] = _goal_kpis(g["name"], ap.employee)

    # Incomplete goals from previous cycles — shown on Future Objectives page
    past_incomplete = frappe.get_all(
        "Individual Goal",
        filters={
            "employee": ap.employee,
            "appraisal_cycle": ["not in", [cycle_name, ""]],
            "docstatus": ["!=", 2],
            "status": ["not in", ["Completed", "Cancelled"]],
        },
        fields=["name", "goal_name", "parent_goal", "is_extra_initiative",
                "target_value", "actual_progress", "progress_pct",
                "unit", "status", "start_date", "end_date", "appraisal_cycle", "owner"],
        ignore_permissions=True, order_by="creation desc",
        limit=50,
    )
    for g in past_incomplete:
        g["creator_name"] = user_full_names.get(g.get("owner", ""), "")
        _serialise_dates(g, "start_date", "end_date")
        cycle_label = frappe.db.get_value("Appraisal Cycle", g.get("appraisal_cycle"), "cycle_name") or g.get("appraisal_cycle", "")
        g["cycle_label"] = cycle_label

    # Standalone KPIs (not linked to any goal)
    standalone = frappe.get_all(
        "KPI",
        filters={"employee": ap.employee, "appraisal_cycle": cycle_name,
                 "individual_goal": ("is", "not set"), "docstatus": ["!=", 2]},
        fields=["name", "kpi_name", "target_value", "actual_value", "attainment_pct",
                "unit", "weightage", "period_start", "period_end", "self_rating", "self_comment", "owner"],
        ignore_permissions=True, order_by="kpi_name asc",
    )
    kpi_owners = list({k["owner"] for k in standalone if k.get("owner") and k["owner"] not in user_full_names})
    if kpi_owners:
        for u in frappe.get_all("User", filters={"name": ["in", kpi_owners]},
                                fields=["name", "full_name"], ignore_permissions=True):
            user_full_names[u["name"]] = u["full_name"]
    for k in standalone:
        k["creator_name"] = user_full_names.get(k.get("owner", ""), "")
        _serialise_dates(k, "period_start", "period_end")

    cycle_info = frappe.db.get_value(
        "Appraisal Cycle", cycle_name,
        ["cycle_name", "start_date", "end_date"], as_dict=True,
    ) or {}

    return {
        "appraisal":       appraisal,
        "employee":        ap.employee,
        "employee_name":   ap.employee_name or "",
        "cycle": {
            "name":       cycle_name,
            "cycle_name": cycle_info.get("cycle_name", cycle_name),
            "start_date": str(cycle_info.get("start_date") or ""),
            "end_date":   str(cycle_info.get("end_date") or ""),
        },
        "review_status":   ext.review_status or "Not Started",
        "return_reason":   ext.return_reason or "",
        "page_config":     page_config,
        "page_settings":   page_settings,
        "page_data":       page_data,
        "pages_completed": pages_completed,
        "overall_comment": ext.overall_comment or "",
        "goals":                goals,
        "standalone_kpis":      standalone,
        "past_incomplete_goals": past_incomplete,
    }


def _goal_kpis(goal_name, employee):
    """KPIs attached to one Individual Goal."""
    rows = frappe.get_all(
        "KPI",
        filters={"individual_goal": goal_name, "employee": employee, "docstatus": ["!=", 2]},
        fields=["name", "kpi_name", "target_value", "actual_value", "attainment_pct",
                "unit", "weightage", "period_start", "period_end", "self_rating", "self_comment",
                "baseline_value", "direction", "category", "owner"],
        ignore_permissions=True, order_by="kpi_name asc",
    )
    for r in rows:
        _serialise_dates(r, "period_start", "period_end")
    return rows


@frappe.whitelist()
def get_available_for_review(appraisal):
    """Return date-eligible objectives and standalone KPIs for the past-objectives selector dialog."""
    import json
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)
    if ap.employee != me and not _is_hr() and not _is_manager_of(ap.employee):
        frappe.throw("Not permitted.", frappe.PermissionError)

    cycle_name = ap.appraisal_cycle
    page_settings = {}
    if frappe.db.exists("Grace Cycle Config", cycle_name):
        cfg = frappe.get_doc("Grace Cycle Config", cycle_name)
        try:
            page_settings = json.loads(cfg.page_settings or "{}")
        except Exception:
            pass

    po = page_settings.get("past-objectives", {})
    period_from = po.get("period_from") or frappe.db.get_value("Appraisal Cycle", cycle_name, "start_date")
    period_to   = po.get("period_to")   or frappe.db.get_value("Appraisal Cycle", cycle_name, "end_date")

    goals = frappe.get_all(
        "Individual Goal",
        filters={
            "employee": ap.employee,
            "docstatus": ["!=", 2],
            "start_date": ["<=", period_to],
            "end_date":   [">=", period_from],
        },
        fields=["name", "goal_name", "start_date", "end_date", "status",
                "target_value", "unit", "appraisal_cycle"],
        ignore_permissions=True,
        order_by="start_date asc",
    )
    for g in goals:
        g["selected"] = g.get("appraisal_cycle") == cycle_name
        _serialise_dates(g, "start_date", "end_date")

    # Only standalone KPIs (goal-linked KPIs are included automatically with their parent goal)
    kpis = frappe.get_all(
        "KPI",
        filters={
            "employee": ap.employee,
            "individual_goal": ("is", "not set"),
            "docstatus": ["!=", 2],
            "period_start": ["<=", period_to],
            "period_end":   [">=", period_from],
        },
        fields=["name", "kpi_name", "period_start", "period_end", "status",
                "target_value", "unit", "category", "appraisal_cycle"],
        ignore_permissions=True,
        order_by="kpi_name asc",
    )
    for k in kpis:
        k["selected"] = k.get("appraisal_cycle") == cycle_name
        _serialise_dates(k, "period_start", "period_end")

    return {
        "goals":       goals,
        "kpis":        kpis,
        "period_from": str(period_from or ""),
        "period_to":   str(period_to   or ""),
    }


@frappe.whitelist()
def set_review_selection(appraisal, selected_goals_json=None, selected_kpis_json=None):
    """Assign or clear appraisal_cycle on objectives/KPIs to control what appears on the past-objectives page."""
    import json
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)
    if ap.employee != me and not _is_hr() and not _is_manager_of(ap.employee):
        frappe.throw("Not permitted.", frappe.PermissionError)

    cycle_name = ap.appraisal_cycle
    page_settings = {}
    if frappe.db.exists("Grace Cycle Config", cycle_name):
        cfg = frappe.get_doc("Grace Cycle Config", cycle_name)
        try:
            page_settings = json.loads(cfg.page_settings or "{}")
        except Exception:
            pass

    po = page_settings.get("past-objectives", {})
    period_from = po.get("period_from") or frappe.db.get_value("Appraisal Cycle", cycle_name, "start_date")
    period_to   = po.get("period_to")   or frappe.db.get_value("Appraisal Cycle", cycle_name, "end_date")

    if selected_goals_json is not None:
        selected_goals = set(json.loads(selected_goals_json) if isinstance(selected_goals_json, str) else selected_goals_json)
        eligible = frappe.get_all(
            "Individual Goal",
            filters={
                "employee": ap.employee,
                "docstatus": ["!=", 2],
                "start_date": ["<=", period_to],
                "end_date":   [">=", period_from],
            },
            fields=["name", "appraisal_cycle"],
            ignore_permissions=True,
        )
        for g in eligible:
            in_cycle = g.get("appraisal_cycle") == cycle_name
            want_in  = g["name"] in selected_goals
            if want_in and not in_cycle:
                frappe.db.set_value("Individual Goal", g["name"], "appraisal_cycle", cycle_name)
            elif not want_in and in_cycle:
                frappe.db.set_value("Individual Goal", g["name"], "appraisal_cycle", "")

    if selected_kpis_json is not None:
        selected_kpis = set(json.loads(selected_kpis_json) if isinstance(selected_kpis_json, str) else selected_kpis_json)
        eligible = frappe.get_all(
            "KPI",
            filters={
                "employee": ap.employee,
                "individual_goal": ("is", "not set"),
                "docstatus": ["!=", 2],
                "period_start": ["<=", period_to],
                "period_end":   [">=", period_from],
            },
            fields=["name", "appraisal_cycle"],
            ignore_permissions=True,
        )
        for k in eligible:
            in_cycle = k.get("appraisal_cycle") == cycle_name
            want_in  = k["name"] in selected_kpis
            if want_in and not in_cycle:
                frappe.db.set_value("KPI", k["name"], "appraisal_cycle", cycle_name)
            elif not want_in and in_cycle:
                frappe.db.set_value("KPI", k["name"], "appraisal_cycle", "")

    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist()
def save_review_page(appraisal, page_key, page_data_json):
    """Persist the employee's self-assessment for a single review page."""
    import json
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)
    if ap.employee != me:
        frappe.throw("Not permitted.", frappe.PermissionError)

    ext = _get_or_create_extension(appraisal)
    if ext.review_status not in ("Not Started", "Employee Review"):
        frappe.throw("Your review is no longer editable.")

    try: all_pd = json.loads(ext.page_data or "{}")
    except: all_pd = {}
    try: new_pd = json.loads(page_data_json) if isinstance(page_data_json, str) else page_data_json
    except: new_pd = {}
    all_pd[page_key] = new_pd

    try: done = json.loads(ext.pages_completed or "[]")
    except: done = []
    if page_key not in done:
        done.append(page_key)

    ext.page_data       = json.dumps(all_pd)
    ext.pages_completed = json.dumps(done)
    if ext.review_status == "Not Started":
        ext.review_status = "Employee Review"
    ext.save(ignore_permissions=True)
    frappe.db.commit()
    return {"pages_completed": done}


@frappe.whitelist()
def submit_employee_review(appraisal, overall_comment=""):
    """Employee finalises self-review and applies page data to actual records."""
    import json
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)
    if ap.employee != me:
        frappe.throw("Only the employee can submit their own review.", frappe.PermissionError)

    ext = _get_or_create_extension(appraisal)
    if ext.review_status not in ("Not Started", "Employee Review"):
        frappe.throw("Review has already been submitted.")

    try:
        all_pd = json.loads(ext.page_data or "{}")
    except Exception:
        all_pd = {}

    # ── Past Objectives: apply KPI self-ratings/comments and objective progress ──
    past = all_pd.get("past-objectives") or all_pd.get("past_objectives") or {}
    kpi_data = past.get("kpis") or {}
    obj_data = past.get("objectives") or {}
    for kpi_name, vals in kpi_data.items():
        try:
            if not frappe.db.exists("KPI", kpi_name):
                continue
            update = {}
            if vals.get("self_rating") not in (None, ""):
                update["self_rating"] = frappe.utils.flt(vals["self_rating"])
            if vals.get("self_comment") is not None:
                update["self_comment"] = vals["self_comment"]
            if update:
                frappe.db.set_value("KPI", kpi_name, update)
        except Exception:
            pass

    for obj_name, vals in obj_data.items():
        try:
            if not frappe.db.exists("Individual Goal", obj_name):
                continue
            if vals.get("actual_progress") not in (None, ""):
                frappe.db.set_value("Individual Goal", obj_name, "actual_progress",
                                    frappe.utils.flt(vals["actual_progress"]))
        except Exception:
            pass

    # ── Past Development: copy textarea fields to extension named fields ──
    past_dev = all_pd.get("past-dev") or {}
    if past_dev.get("achievements"):
        ext.achievements_text = past_dev["achievements"]
    if past_dev.get("challenges"):
        ext.challenges_text = past_dev["challenges"]
    if past_dev.get("development_needs"):
        ext.development_needs_text = past_dev["development_needs"]
    if past_dev.get("support_needed"):
        ext.support_needed = past_dev["support_needed"]

    # ── Future Development Plan ──
    future_dev = all_pd.get("future-dev") or {}
    goals_text = "\n\n".join(filter(None, [
        future_dev.get("development_goals", ""),
        ("Training needs: " + future_dev["training_needs"]) if future_dev.get("training_needs") else "",
    ]))
    if goals_text:
        ext.next_period_goals_text = goals_text

    # ── Future Objectives: create draft goals as Individual Goal records ──
    future_obj = all_pd.get("future-objectives") or all_pd.get("future_goals") or {}
    new_goals = future_obj.get("new_goals") or []
    for g in new_goals:
        try:
            ig = frappe.new_doc("Individual Goal")
            ig.goal_name      = g.get("name", "New Goal")
            ig.description    = g.get("description", "")
            ig.target_value   = frappe.utils.flt(g.get("target_value") or 0)
            ig.unit            = g.get("unit", "")
            ig.employee        = me
            ig.appraisal_cycle = ap.appraisal_cycle
            ig.status          = "Not Started"
            ig.insert(ignore_permissions=True)
        except Exception:
            pass

    ext.overall_comment = overall_comment
    ext.review_status   = "Manager Review"
    ext.save(ignore_permissions=True)
    frappe.db.commit()
    return {"review_status": "Manager Review"}


# ══════════════════════════════════════════════════════════════════════════
# Multi-stage review workflow — manager review, invited reviewers,
# employee final review, acknowledgement
# ══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_manager_review(appraisal):
    """Manager or HR views the full review — employee self-assessment + manager fields."""
    import json
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)
    # Must be the employee's manager or an HR user
    is_hr = _is_hr()
    is_manager = _is_manager_of(ap.employee) if not is_hr else False
    if not is_hr and not is_manager:
        frappe.throw("Only the employee's manager or HR can open this review.", frappe.PermissionError)

    ext = _get_or_create_extension(appraisal)
    cycle_name = ap.appraisal_cycle

    try: page_data = json.loads(ext.page_data or "{}")
    except: page_data = {}
    try: pages_completed = json.loads(ext.pages_completed or "[]")
    except: pages_completed = []
    try: invited = json.loads(ext.invited_reviewers or "[]")
    except: invited = []

    page_config, page_settings = {}, {}
    if frappe.db.exists("Grace Cycle Config", cycle_name):
        cfg = frappe.get_doc("Grace Cycle Config", cycle_name)
        try: page_config = json.loads(cfg.page_config or "{}")
        except: pass
        try: page_settings = json.loads(cfg.page_settings or "{}")
        except: pass

    # Resolve rating scales referenced in the manager-feedback page settings
    mgf_ps = page_settings.get("manager-feedback", {})
    _scale_names = [s for s in [
        mgf_ps.get("overall_rating_scale"),
        mgf_ps.get("potential_rating_scale"),
    ] if s]
    rating_scales = {}
    for sname in _scale_names:
        if frappe.db.exists("Grace Rating Scale", sname):
            sinfo = frappe.db.get_value("Grace Rating Scale", sname, ["scale_name", "description"], as_dict=True) or {}
            sitems = frappe.get_all("Grace Rating Scale Item",
                filters={"parent": sname},
                fields=["label", "value", "color"],
                order_by="value desc")
            rating_scales[sname] = {"scale_name": sinfo.get("scale_name", sname), "items": sitems}

    goals = frappe.get_all(
        "Individual Goal",
        filters={"employee": ap.employee, "appraisal_cycle": cycle_name, "docstatus": ["!=", 2]},
        fields=["name", "goal_name", "target_value", "actual_progress", "progress_pct",
                "unit", "status", "start_date", "end_date", "weightage", "employee", "owner"],
        ignore_permissions=True, order_by="creation asc",
    )
    for g in goals:
        _serialise_dates(g, "start_date", "end_date")
        g["kpis"] = _goal_kpis(g["name"], ap.employee)

    cycle_info = frappe.db.get_value("Appraisal Cycle", cycle_name,
        ["cycle_name", "start_date", "end_date"], as_dict=True) or {}

    return {
        "appraisal":        appraisal,
        "employee":         ap.employee,
        "employee_name":    ap.employee_name or "",
        "cycle": {
            "name":       cycle_name,
            "cycle_name": cycle_info.get("cycle_name", cycle_name),
            "start_date": str(cycle_info.get("start_date") or ""),
            "end_date":   str(cycle_info.get("end_date") or ""),
        },
        "review_status":   ext.review_status or "Not Started",
        "return_reason":   ext.return_reason or "",
        "page_config":     page_config,
        "page_settings":   page_settings,
        "page_data":       page_data,
        "pages_completed": pages_completed,
        "overall_comment": ext.overall_comment or "",
        "goals":           goals,
        "standalone_kpis": [],
        # Manager fields (visible because caller is manager/HR)
        "manager_feedback":      ext.manager_feedback or "",
        "manager_internal_notes": ext.manager_internal_notes or "",
        "overall_rating":        ext.overall_rating or 0,
        "potential_rating":      ext.potential_rating or 0,
        "reviewer_comments_visible": ext.reviewer_comments_visible or 0,
        "invited_reviewers":     invited,
        "viewer_role":           "hr" if is_hr else "manager",
        "rating_scales":         rating_scales,
    }


def _is_manager_of(employee_id):
    """Return True if the logged-in user is in the direct management chain of employee_id."""
    user = frappe.session.user
    me_emp = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not me_emp:
        return False
    mgr = frappe.db.get_value("Employee", employee_id, "reports_to")
    while mgr:
        if mgr == me_emp:
            return True
        mgr = frappe.db.get_value("Employee", mgr, "reports_to")
    return False


@frappe.whitelist()
def save_manager_review(appraisal, manager_feedback="", manager_internal_notes="",
                        overall_rating=0, potential_rating=0):
    """Manager saves draft of their review (does not change status)."""
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)
    if not _is_hr() and not _is_manager_of(ap.employee):
        frappe.throw("Not permitted.", frappe.PermissionError)
    ext = _get_or_create_extension(appraisal)
    if ext.review_status not in ("Manager Review",):
        frappe.throw("Review is not in Manager Review stage.")
    ext.manager_feedback       = manager_feedback
    ext.manager_internal_notes = manager_internal_notes
    ext.overall_rating         = flt(overall_rating)
    ext.potential_rating       = flt(potential_rating)
    ext.save(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist()
def invite_reviewer(appraisal, reviewer_employee, allowed_pages=None):
    """Manager invites an additional reviewer."""
    import json
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)
    if not _is_hr() and not _is_manager_of(ap.employee):
        frappe.throw("Not permitted.", frappe.PermissionError)
    if reviewer_employee == ap.employee:
        frappe.throw("Cannot invite the subject employee as a reviewer.")
    ext = _get_or_create_extension(appraisal)
    if ext.review_status != "Manager Review":
        frappe.throw("Reviewers can only be invited during Manager Review stage.")
    try: invited = json.loads(ext.invited_reviewers or "[]")
    except: invited = []
    if any(r["employee"] == reviewer_employee for r in invited):
        frappe.throw("This reviewer is already invited.")
    emp_doc = frappe.db.get_value("Employee", reviewer_employee, ["employee_name", "user_id"], as_dict=True)
    if not emp_doc:
        frappe.throw(f"Employee {reviewer_employee} not found.")
    if isinstance(allowed_pages, str):
        try: pages = json.loads(allowed_pages)
        except: pages = []
    elif isinstance(allowed_pages, list):
        pages = allowed_pages
    else:
        pages = []
    invited.append({
        "employee":      reviewer_employee,
        "employee_name": emp_doc.get("employee_name", ""),
        "user":          emp_doc.get("user_id", ""),
        "status":        "Invited",
        "comments":      "",
        "submitted_on":  "",
        "allowed_pages": pages,
        "page_comments": {},
    })
    ext.invited_reviewers = json.dumps(invited)
    ext.save(ignore_permissions=True)
    frappe.db.commit()
    if emp_doc.get("user_id"):
        try:
            frappe.sendmail(
                recipients=[emp_doc["user_id"]],
                subject=f"You have been invited to review {ap.employee_name}'s performance",
                message=f"<p>You have been invited by your colleague to provide feedback on {ap.employee_name}'s performance review for {ap.appraisal_cycle}. Please log in to the portal to submit your feedback.</p>",
            )
        except Exception:
            pass
    return {"ok": True, "invited": invited}


@frappe.whitelist()
def invite_reviewers_batch(appraisal, reviewers):
    """Invite multiple reviewers at once. reviewers is a JSON array of {employee, allowed_pages}."""
    import json
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)
    if not _is_hr() and not _is_manager_of(ap.employee):
        frappe.throw("Not permitted.", frappe.PermissionError)
    ext = _get_or_create_extension(appraisal)
    if ext.review_status != "Manager Review":
        frappe.throw("Reviewers can only be invited during Manager Review stage.")
    if isinstance(reviewers, str):
        try: reviewers = json.loads(reviewers)
        except: frappe.throw("Invalid reviewers format.")
    try: invited = json.loads(ext.invited_reviewers or "[]")
    except: invited = []
    existing = {r["employee"] for r in invited}
    added = 0
    for item in (reviewers or []):
        rev_emp = item.get("employee", "")
        if not rev_emp or rev_emp == ap.employee or rev_emp in existing:
            continue
        emp_doc = frappe.db.get_value("Employee", rev_emp, ["employee_name", "user_id"], as_dict=True)
        if not emp_doc:
            continue
        pages = item.get("allowed_pages", [])
        if isinstance(pages, str):
            try: pages = json.loads(pages)
            except: pages = []
        invited.append({
            "employee":      rev_emp,
            "employee_name": emp_doc.get("employee_name", ""),
            "user":          emp_doc.get("user_id", ""),
            "status":        "Invited",
            "comments":      "",
            "submitted_on":  "",
            "allowed_pages": pages,
            "page_comments": {},
        })
        existing.add(rev_emp)
        added += 1
        if emp_doc.get("user_id"):
            try:
                frappe.sendmail(
                    recipients=[emp_doc["user_id"]],
                    subject=f"You have been invited to review {ap.employee_name}'s performance",
                    message=f"<p>You have been invited to provide feedback on {ap.employee_name}'s performance review for {ap.appraisal_cycle}. Please log in to the portal to submit your feedback.</p>",
                )
            except Exception:
                pass
    ext.invited_reviewers = json.dumps(invited)
    ext.save(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True, "invited": invited, "added": added}


@frappe.whitelist()
def get_reviewer_view(appraisal):
    """Return an invited reviewer's view: their allowed pages, employee's page_data, and existing comments."""
    import json
    me_user = frappe.session.user
    me_emp = frappe.db.get_value("Employee", {"user_id": me_user}, "name")
    if not me_emp:
        frappe.throw("Only employees can access reviewer views.", frappe.PermissionError)
    ext = _get_or_create_extension(appraisal)
    try: invited = json.loads(ext.invited_reviewers or "[]")
    except: invited = []
    entry = next((r for r in invited if r.get("employee") == me_emp), None)
    if not entry:
        frappe.throw("You are not an invited reviewer for this appraisal.", frappe.PermissionError)
    try: page_data = json.loads(ext.page_data or "{}")
    except: page_data = {}
    ap = frappe.get_doc("Appraisal", appraisal)
    goals = frappe.get_all(
        "Individual Goal",
        filters={"employee": ap.employee, "appraisal_cycle": ap.appraisal_cycle, "docstatus": ["!=", 2]},
        fields=["name", "goal_name", "parent_goal", "is_extra_initiative",
                "status", "actual_progress", "progress_pct", "unit"],
        ignore_permissions=True,
    )
    allowed_pages = entry.get("allowed_pages", [])
    page_comments = entry.get("page_comments", {})
    if isinstance(page_comments, str):
        try: page_comments = json.loads(page_comments)
        except: page_comments = {}
    # Resolve page labels from cycle config
    page_label_map = {}
    if ap.appraisal_cycle:
        cc_val = frappe.db.get_value("Grace Cycle Config", {"appraisal_cycle": ap.appraisal_cycle}, "page_config")
        if cc_val:
            try:
                for p in json.loads(cc_val):
                    if isinstance(p, dict):
                        page_label_map[p.get("key", "")] = p.get("label", p.get("key", ""))
            except: pass
    _defaults = {"past-objectives": "Past Objectives", "future-objectives": "Future Objectives",
                 "past-dev": "Development Areas", "future-dev": "Future Development",
                 "strengths": "Strengths", "general": "General"}
    allowed_page_objs = [{"key": pk, "label": page_label_map.get(pk) or _defaults.get(pk) or pk}
                         for pk in allowed_pages]
    return {
        "allowed_pages":    allowed_page_objs,
        "page_data":        page_data,
        "goals":            goals,
        "my_comments":      entry.get("comments", ""),
        "my_page_comments": page_comments,
        "my_status":        entry.get("status", "Invited"),
        "employee_name":    ap.employee_name,
        "cycle":            ap.appraisal_cycle,
    }


@frappe.whitelist()
def submit_reviewer_comments(appraisal, comments, page_comments=None):
    """An invited reviewer submits their comments."""
    import json
    from frappe.utils import now_datetime
    me_user = frappe.session.user
    me_emp = frappe.db.get_value("Employee", {"user_id": me_user}, "name")
    if not me_emp:
        frappe.throw("Only employees can submit reviewer comments.", frappe.PermissionError)
    ext = _get_or_create_extension(appraisal)
    if ext.review_status != "Manager Review":
        frappe.throw("Review is not in Manager Review stage.")
    try: invited = json.loads(ext.invited_reviewers or "[]")
    except: invited = []
    pc = {}
    if page_comments:
        if isinstance(page_comments, str):
            try: pc = json.loads(page_comments)
            except: pc = {}
        elif isinstance(page_comments, dict):
            pc = page_comments
    updated = False
    for r in invited:
        if r["employee"] == me_emp:
            r["comments"]      = comments
            r["page_comments"] = pc
            r["status"]        = "Submitted"
            r["submitted_on"]  = str(now_datetime())[:10]
            updated = True
            break
    if not updated:
        frappe.throw("You are not an invited reviewer for this appraisal.", frappe.PermissionError)
    ext.invited_reviewers = json.dumps(invited)
    ext.save(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist()
def submit_manager_review(appraisal, manager_feedback="", manager_internal_notes="",
                          overall_rating=0, potential_rating=0, reviewer_comments_visible=0):
    """Manager finalises their review → Employee Final Review stage."""
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)
    if not _is_hr() and not _is_manager_of(ap.employee):
        frappe.throw("Not permitted.", frappe.PermissionError)
    ext = _get_or_create_extension(appraisal)
    if ext.review_status != "Manager Review":
        frappe.throw("Review is not in Manager Review stage.")
    if not manager_feedback:
        frappe.throw("Manager feedback is required before submitting.")
    # Only require overall_rating when the cycle was configured with a rating scale
    _overall_required = False
    if frappe.db.exists("Grace Cycle Config", ap.appraisal_cycle):
        try:
            import json as _json
            _cfg = frappe.get_doc("Grace Cycle Config", ap.appraisal_cycle)
            _ps = _json.loads(_cfg.page_settings or "{}")
            _overall_required = bool((_ps.get("manager-feedback") or {}).get("overall_rating_scale"))
        except Exception:
            pass
    if _overall_required and not flt(overall_rating):
        frappe.throw("Overall rating is required before submitting.")
    ext.manager_feedback            = manager_feedback
    ext.manager_internal_notes      = manager_internal_notes
    ext.overall_rating              = flt(overall_rating)
    ext.potential_rating            = flt(potential_rating)
    ext.reviewer_comments_visible   = int(reviewer_comments_visible or 0)
    ext.review_status               = "Employee Final Review"
    ext.save(ignore_permissions=True)
    frappe.db.commit()
    # Notify employee
    emp_user = frappe.db.get_value("Employee", ap.employee, "user_id")
    if emp_user:
        try:
            frappe.sendmail(
                recipients=[emp_user],
                subject=f"Your performance review is ready: {ap.appraisal_cycle}",
                message=f"<p>Your manager has completed their review of your performance for {ap.appraisal_cycle}. Please log in to view the feedback and acknowledge.</p>",
            )
        except Exception:
            pass
    return {"review_status": "Employee Final Review"}


@frappe.whitelist()
def acknowledge_final_review(appraisal):
    """Employee acknowledges the final review → HR Review."""
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)
    if ap.employee != me:
        frappe.throw("Only the subject employee can acknowledge.", frappe.PermissionError)
    ext = _get_or_create_extension(appraisal)
    if ext.review_status != "Employee Final Review":
        frappe.throw("Review is not in Employee Final Review stage.")
    ext.review_status = "HR Review"
    ext.save(ignore_permissions=True)
    frappe.db.commit()
    return {"review_status": "HR Review"}


@frappe.whitelist()
def get_employee_final_review(appraisal):
    """Return manager feedback and ratings for the employee's final review view."""
    import json
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)
    if ap.employee != me:
        frappe.throw("Not permitted.", frappe.PermissionError)
    ext = _get_or_create_extension(appraisal)
    if ext.review_status not in ("Employee Final Review",):
        frappe.throw("Final review is not yet available.")
    try: invited = json.loads(ext.invited_reviewers or "[]")
    except: invited = []
    visible_reviewers = []
    if ext.reviewer_comments_visible:
        visible_reviewers = [
            {"employee_name": r["employee_name"], "comments": r["comments"], "submitted_on": r["submitted_on"]}
            for r in invited if r.get("status") == "Submitted"
        ]

    # Load page settings for this cycle so the UI knows which scales were configured
    page_settings = {}
    cycle_name = ap.appraisal_cycle
    if cycle_name and frappe.db.exists("Grace Cycle Config", cycle_name):
        cfg = frappe.get_doc("Grace Cycle Config", cycle_name)
        try: page_settings = json.loads(cfg.page_settings or "{}")
        except: pass

    mgf_ps = page_settings.get("manager-feedback", {})
    _scale_names = [s for s in [
        mgf_ps.get("overall_rating_scale"),
        mgf_ps.get("potential_rating_scale"),
    ] if s]
    rating_scales = {}
    for sname in _scale_names:
        if frappe.db.exists("Grace Rating Scale", sname):
            sinfo = frappe.db.get_value("Grace Rating Scale", sname, ["scale_name", "description"], as_dict=True) or {}
            sitems = frappe.get_all("Grace Rating Scale Item",
                filters={"parent": sname},
                fields=["label", "value", "color"],
                order_by="value desc")
            rating_scales[sname] = {"scale_name": sinfo.get("scale_name", sname), "items": sitems}

    return {
        "appraisal":       appraisal,
        "review_status":   ext.review_status,
        "manager_feedback": ext.manager_feedback or "",
        "overall_rating":  ext.overall_rating or 0,
        "potential_rating": ext.potential_rating or 0,
        "potential_category": ext.potential_category or "",
        "reviewer_comments_visible": ext.reviewer_comments_visible or 0,
        "invited_reviewer_comments": visible_reviewers,
        "page_settings":   page_settings,
        "rating_scales":   rating_scales,
    }


# ── Review Template management ───────────────────────────────────────────────
# Templates are stored as a JSON blob in frappe's global defaults table so that
# no new doctype is required.  Only HR roles can read or write templates.

_TEMPLATES_KEY = "grace_cycle_templates"


@frappe.whitelist()
def save_cycle_template(template_name, page_config, page_settings, employee_fields):
    """Persist the current wizard configuration as a named reusable template."""
    import json as _json
    _require_hr()
    template_name = (template_name or "").strip()
    if not template_name:
        frappe.throw("Template name is required.")
    existing = frappe.db.get_global(_TEMPLATES_KEY) or "{}"
    templates = _json.loads(existing)
    templates[template_name] = {
        "name": template_name,
        "page_config": _json.loads(page_config)  if isinstance(page_config,  str) else page_config,
        "page_settings": _json.loads(page_settings) if isinstance(page_settings, str) else page_settings,
        "employee_fields": _json.loads(employee_fields) if isinstance(employee_fields, str) else employee_fields,
        "saved_by": frappe.session.user,
        "saved_at": frappe.utils.now(),
    }
    frappe.db.set_global(_TEMPLATES_KEY, _json.dumps(templates))
    return {"message": "Template saved", "name": template_name}


@frappe.whitelist()
def list_cycle_templates():
    """Return all saved review templates (HR only)."""
    import json as _json
    _require_hr()
    raw = frappe.db.get_global(_TEMPLATES_KEY) or "{}"
    return list(_json.loads(raw).values())


@frappe.whitelist()
def delete_cycle_template(template_name):
    """Delete a saved review template (HR only)."""
    import json as _json
    _require_hr()
    existing = frappe.db.get_global(_TEMPLATES_KEY) or "{}"
    templates = _json.loads(existing)
    templates.pop(template_name, None)
    frappe.db.set_global(_TEMPLATES_KEY, _json.dumps(templates))
    return {"message": "Deleted"}
