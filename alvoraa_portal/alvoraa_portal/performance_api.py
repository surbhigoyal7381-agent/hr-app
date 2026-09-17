"""Performance management — KPIs, goals and appraisals, end to end in the portal.

Method path: alvoraa_portal.performance_api.*

Covers the whole review loop without anyone touching the Frappe desk:

    HR       create cycle -> assign KPIs -> generate appraisals -> complete cycle
    Employee log KPI progress -> self-rate -> write reflections
    Manager  rate reports' KPIs -> sync scores -> submit appraisal

Tenant isolation: every call runs against the site resolved from the request
Host, and each site is a separate database, so no query here can observe another
tenant's rows. Within a tenant, callers are narrowed to what their role allows —
see alvoraa_goals.permissions for the row-level rules applied to KPI queries.
"""

import frappe
from frappe.utils import cint, flt, today, getdate
from alvoraa_goals.permissions import get_effective_manager

from alvoraa_goals.controllers.kpi import MAX_RATING, TOTAL_WEIGHTAGE, rating_from_attainment
import alvoraa_goals.review_items as review_items
from hrms.alvoraa_hr_core.access import permitted_companies, refuse, refuse_own_rating

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


def _assert_hr_can_view(appraisal_name):
    """Stop HR reading an appraisal that is still being written.

    Only when they are acting AS HR, which is the part this got wrong. It asked
    "do you hold an HR role?" rather than "is this somebody else's appraisal?",
    so anybody holding HR Manager was blocked from their OWN review - and from
    their team's. On PP Jewellers that is the Owner and Managing Director, who
    holds HR Manager and could not open his own appraisal.

    Two exemptions, and both are about WHOSE appraisal it is:

      - your own is never HR snooping;
      - one belonging to somebody below you is not either. In that moment you
        are their manager, and the manager review stage is exactly when you are
        supposed to be in there.

    The HR Manager who stands in for an employee with no manager is NOT exempt
    here: that would open every manager-less employee's review to them at every
    stage. The manager-review actions allow that stand-in themselves
    (_is_line_manager).

    Acting as HR for anyone else (slice 010, group D):

      - System Manager follows the same stage rule; it used to be exempt
        (decision 15);
      - only for the companies you look after (decision 16);
      - a review with no record yet has not reached HR either.
    """
    if not _is_hr():
        return

    me = _employee_id()
    owner = frappe.db.get_value("Appraisal", appraisal_name, "employee")
    if me and owner and (owner == me or owner in _subordinates(me)):
        return

    company = frappe.db.get_value("Employee", owner, "company") if owner else None
    if not company or company not in permitted_companies():
        refuse(
            "This appraisal belongs to a company you do not look after.",
            "SEC-13", "review", "Appraisal", appraisal_name,
        )

    status = frappe.db.get_value(
        "Alvoraa Appraisal Extension", {"appraisal": appraisal_name}, "review_status"
    )
    if (status or "Not Started") not in ("HR Review", "Completed"):
        refuse(
            "This appraisal is still with the employee and their manager. "
            "It reaches HR once their review is finished.",
            "SEC-27", "review", "Appraisal", appraisal_name,
        )


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
    from alvoraa_goals.permissions import descendants
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


def _require_scoring_access(appraisal, employee, endpoint):
    """Who may score a review through the older scoring calls (security review M1).

    suggest_ratings, sync_appraisal_from_kpis and submit_appraisal used to let
    any HR role act on any company's review at any stage. Now, in order:
    never the subject (SEC-10); the direct manager or HR; HR acting for someone
    outside their line follows the stage and company rule (decisions 15, 16);
    and nobody scores a review whose self-review has not been sent (PRIV-2).
    """
    refuse_own_rating(employee, "Appraisal", appraisal, endpoint)
    _require_can_review(employee)
    if not _is_line_manager(employee, _employee_id()):
        _assert_hr_can_view(appraisal)
    if _review_status(appraisal) in _SELF_REVIEW_DRAFT:
        refuse(
            "The self-review has not been sent yet. Scores can be worked out once it is sent.",
            "PRIV-2", endpoint, "Appraisal", appraisal,
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

# No rating or comment fields: ratings are given and shown only inside a review,
# on its copy (slice 010 group D: R14, PRIV-9). This list feeds the tree, "My
# KPIs" and the team's KPIs, which every employee and manager can open.
KPI_FIELDS = [
    "name", "kpi_name", "employee", "employee_name", "appraisal_cycle", "category",
    "status", "unit", "direction", "baseline_value", "target_value", "actual_value",
    "attainment_pct", "weightage", "period_start", "period_end", "goal_cascade",
    "individual_goal",
    "company_value", "is_extra_initiative", "description", "owner",
]


def _decorate_kpis(rows):
    """Add the objective label, whether this caller may revise each row, and the
    plain "in review" badge (R5): one query for every row."""
    hr = _is_hr()
    user = frappe.session.user
    goal_names = {}
    badges = review_items.review_badges("KPI", [r.get("name") for r in rows])
    for r in rows:
        r["review_badge"] = badges.get(r.get("name"))
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
    alvoraa_goals.permissions. Using get_list means the explicit filters below and
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


# How far back a reading may be dated when the KPI has no period of its own.
READING_DATE_MAX_DAYS_BACK = 366


def _reading_date(doc, log_date):
    """The date a KPI reading is for (slice 010 group D, decision 2).

    Blank means today. Otherwise it must be a real date, not after today (the
    server's date), and not before the KPI's period start - or, for a KPI with
    no period, not more than a year back. A date after the period end is
    allowed: people log late, and the review counts only dates inside its own
    period anyway (R3).
    """
    if not log_date:
        return getdate(today())
    try:
        day = getdate(log_date)
    except Exception:
        frappe.throw(frappe._("Choose the date this reading is for."))
    if day > getdate(today()):
        frappe.throw(frappe._("A reading cannot be dated in the future. Choose today or an earlier day."))
    earliest = getdate(doc.period_start) if doc.period_start else getdate(frappe.utils.add_days(today(), -READING_DATE_MAX_DAYS_BACK))
    if day < earliest:
        frappe.throw(frappe._("A reading cannot be dated before {0}. Choose {0} or a later day.").format(
            frappe.utils.formatdate(earliest)))
    return day


@frappe.whitelist()
def log_kpi_progress(kpi, value, note="", evidence_url=None, log_date=None):
    """Append a dated reading, set approval pending, and notify the manager.

    The portal asks for the amount since the last update on a Cumulative KPI
    and for the current reading on an Absolute one (decision 1), and lets the
    person say which day the reading is for (decision 2).
    """
    doc = frappe.get_doc("KPI", kpi)
    _require_owns(doc.employee)

    if doc.status in ("Cancelled",):
        frappe.throw("This KPI is cancelled and no longer accepts progress updates.")

    day = _reading_date(doc, log_date)

    # Private, uploaded by the caller, and attached to this KPI - or refused (SEC-4).
    from alvoraa_goals.controllers.evidence import claim_evidence_file
    evidence_url = claim_evidence_file(evidence_url, "KPI", doc.name, "performance_api.log_kpi_progress")
    ev_missing = 1 if not evidence_url else 0
    row = doc.append("progress_log", {
        "log_date":        day,
        "value":           flt(value),
        "note":            note,
        "logged_by":       frappe.session.user,
        "evidence_file":   evidence_url or None,
        "evidence_missing": ev_missing,
        "approval_status": "Pending",
    })
    # The live number moves only when a reading is approved (code review M2):
    # a reading someone rejects never reaches it. The review never reads this
    # number either: it counts approved readings by date (R3, R4).
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
    # Nobody approves their own update, whatever roles they hold (SEC-9).
    from hrms.alvoraa_hr_core.access import refuse_own_decision
    refuse_own_decision(doc.employee, "KPI", doc.name, "performance_api.approve_kpi_update")
    # Gate: only the employee's direct manager or HR may approve.
    kpi_emp_mgr = frappe.db.get_value("Employee", doc.employee, "reports_to")
    my_emp      = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
    if not (_is_hr() or my_emp == kpi_emp_mgr):
        frappe.throw("Only this employee's manager or HR can approve updates.",
                     frappe.PermissionError)
    if my_emp != kpi_emp_mgr and frappe.db.get_value("Employee", doc.employee, "company") not in permitted_companies():
        # HR approves only for the companies they look after (security review m8):
        # an approved reading flows into that employee's open review.
        refuse("This employee belongs to a company you do not look after.",
               "SEC-26", "approve_kpi_update", "KPI", doc.name)

    for row in (doc.progress_log or []):
        if row.name == row_name:
            before = row.approval_status or "Pending"
            row.approval_status  = action
            row.approval_comment = comment
            row.approved_by      = frappe.session.user
            row.approved_on      = frappe.utils.now()
            _move_live_number(doc, row, before, action)
            break
    else:
        frappe.throw(f"Progress log row '{row_name}' not found on KPI {kpi}.")

    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": f"Update {action.lower()}."}


def _reading_order(row):
    return (str(row.log_date or ""), str(row.approved_on or ""), str(row.creation or ""))


def _move_live_number(doc, row, before, after):
    """The live KPI number counts approved readings only (code review M2).

    Cumulative: an approved amount adds to it; taking an approval back takes
    the amount off again. Absolute: the latest approved reading by date is the
    number; with no approved reading left it stays as it is, so a number from
    before readings needed approval is not wiped. Deciding the same way twice
    changes nothing. Attainment and the end-of-period status follow on save
    (controllers.kpi.validate_kpi).
    """
    if before == after:
        return
    if (doc.progress_mode or "Cumulative") == "Cumulative":
        if after == "Approved":
            doc.actual_value = flt(doc.actual_value) + flt(row.value)
        elif before == "Approved":
            doc.actual_value = flt(doc.actual_value) - flt(row.value)
        return
    approved = [r for r in (doc.progress_log or []) if (r.approval_status or "") == "Approved"]
    if approved:
        doc.actual_value = flt(max(approved, key=_reading_order).value)


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
            # When it was typed, beside the day it is for (security review m2).
            "logged_on":        str(r.creation)   if r.creation   else "",
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


def _refuse_rating_outside_review(endpoint, doctype, name):
    """Ratings are given only inside a review, on its copy (R13, R14, SEC-1).

    The live KPI no longer takes a rating from anyone, so a rating can never
    reach it around the review's stage and stamp rules.
    """
    refuse(
        "Ratings are given inside the review. Open the review to rate this item.",
        "R13", endpoint, doctype, name,
    )


@frappe.whitelist()
def save_kpi_self_review(kpi, rating=None, comment=""):
    """Retired in slice 010 group D: rate the item inside your review instead."""
    _refuse_rating_outside_review("save_kpi_self_review", "KPI", kpi)


@frappe.whitelist()
def get_my_appraisal(cycle=None):
    """The signed-in employee's appraisal for a cycle, with KPI-derived goal rows."""
    emp_id = _require_employee()
    ctx = get_performance_context()
    cycle = cycle or (ctx["active_cycle"] or {}).get("name")
    if not cycle:
        return {"cycle": None, "appraisal": None}

    return _appraisal_payload(emp_id, cycle, subject=True)


def _appraisal_payload(emp_id, cycle, subject=False):
    """The HRMS appraisal summary, as a screen outside the review shows it.

    No item score, ever: each goal row's score is a KPI or Objective rating, and
    those are shown only inside the review (R14, decision 14). The appraisal's
    totals follow the overall rating's release rule (decision 3): the person the
    appraisal is about sees them from Employee Final Review on. Callers decide
    who else may open it before calling.
    """
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
        cycle_doc["scoring"] = _cycle_scoring(cycle)

    if not names:
        return {"cycle": cycle_doc, "appraisal": None}

    ap = frappe.get_doc("Appraisal", names[0])
    released = not subject or _review_status(ap.name) in _RATING_RELEASED

    def total(value):
        return flt(value) if released else None

    return {
        "cycle": cycle_doc,
        "appraisal": {
            "name":         ap.name,
            "employee":     ap.employee,
            "employee_name": ap.employee_name,
            "docstatus":    ap.docstatus,
            "total_score":  total(ap.total_score),
            "self_score":   total(ap.self_score),
            "avg_feedback_score": total(ap.avg_feedback_score),
            "final_score":  total(ap.final_score),
            "attendance_score": flt(ap.get("attendance_score")),
            "attendance_reliability_pct": ap.get("attendance_reliability_pct"),
            "attendance_punctuality_pct": ap.get("attendance_punctuality_pct"),
            "attendance_deduction_days": flt(ap.get("attendance_deduction_days")),
            "attendance_summary": ap.get("attendance_summary") or "",
            "reflections":  ap.reflections or "",
            "remarks":      ap.remarks or "",
            "goals": [
                {
                    "idx": g.idx,
                    "kra": g.kra,
                    "per_weightage": flt(g.per_weightage),
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
    or_filters = None
    if cycle:
        filters["appraisal_cycle"] = cycle
    if not hr:
        filters["employee"] = ["in", subjects or [""]]
    else:
        # HR sees the companies they look after, plus their own line (decision 16).
        or_filters = [
            ["company", "in", permitted_companies() or [""]],
            ["employee", "in", [me, *_subordinates(me)]],
        ]

    rows = frappe.get_all(
        "Appraisal",
        filters=filters,
        or_filters=or_filters,
        fields=["name", "employee", "employee_name", "designation", "department",
                "appraisal_cycle", "docstatus", "total_score", "self_score",
                "avg_feedback_score", "final_score", "start_date", "end_date"],
        order_by="appraisal_cycle desc, employee_name asc",
    )

    my_reports = set(_reports_of(me))
    my_line = set(_subordinates(me))
    cycle_status = {
        c["name"]: c["status"]
        for c in frappe.get_all("Appraisal Cycle", fields=["name", "status"])
    }
    # Scores follow the overall rating's release rule (decision 3, PRIV-9): your
    # own from Employee Final Review; your line's always; anyone else's, for HR,
    # from HR Review. One query for every row's stage.
    stages = dict(frappe.get_all(
        "Alvoraa Appraisal Extension",
        filters={"name": ["in", [r["name"] for r in rows] or [""]]},
        fields=["name", "review_status"], as_list=True,
    ))

    out = []
    for r in rows:
        stage = stages.get(r["name"]) or "Not Started"
        if r["employee"] == me:
            scores_visible = stage in _RATING_RELEASED
        else:
            scores_visible = r["employee"] in my_line or stage in ("HR Review", "Completed")
        if not scores_visible:
            for field in ("total_score", "self_score", "avg_feedback_score", "final_score"):
                r[field] = None
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
    _assert_hr_can_view(appraisal)

    payload = _appraisal_payload(ap.employee, ap.appraisal_cycle, subject=ap.employee == me)
    detail = payload.get("appraisal") or {}
    detail["designation"] = ap.designation or ""
    detail["department"] = ap.department or ""
    detail["is_own"] = int(ap.employee == me)
    detail["can_review"] = int(ap.docstatus == 0 and
                               (_is_hr() or ap.employee in _reports_of(me)))
    detail["can_self_assess"] = int(ap.docstatus == 0 and ap.employee == me)
    # A self-rating reaches anyone else only once the self-review is sent (PRIV-2).
    self_ratings_visible = ap.employee == me or _review_status(appraisal) not in _SELF_REVIEW_DRAFT
    detail["self_ratings"] = [
        {"criteria": str(getattr(r, "criteria", "")),
         "per_weightage": flt(getattr(r, "per_weightage", 0)),
         "rating": flt(getattr(r, "rating", 0))}
        for r in (ap.self_ratings or [])
    ] if self_ratings_visible else []
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
    """Review status for the caller's direct reports, or for HR every active
    employee of the companies they look after (decision 16).

    Ratings in each row follow who is looking: the manager line sees them; HR
    sees them for someone outside their line only from HR Review on; and nobody
    sees their own potential rating, or their own overall rating before it is
    released (PRIV-1).
    """
    me = _require_employee()
    hr = _is_hr()

    reports = _reports_of(me)
    if hr:
        companies = permitted_companies()
        scoped = frappe.get_all(
            "Employee", filters={"status": "Active", "company": ["in", companies or [""]]}, pluck="name"
        )
        reports = list(dict.fromkeys(reports + scoped))
    line = set(_subordinates(me)) if hr else set(reports)

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
        "Alvoraa Appraisal Extension",
        filters={"appraisal": ["in", appraisal_names]},
        fields=["appraisal", "review_status", "overall_rating", "potential_rating",
                "overall_rating_flag"],
    ):
        ext_map[ext["appraisal"]] = ext

    appraisal_by_emp = {a["employee"]: a for a in appraisals}

    def ratings(emp_id, ext):
        status = ext.get("review_status") or "Not Started"
        if emp_id == me:
            return (ext.get("overall_rating") if status in _RATING_RELEASED else None), None
        if emp_id in line or status in ("HR Review", "Completed"):
            return ext.get("overall_rating"), ext.get("potential_rating")
        return None, None

    team = []
    for emp_id in reports:
        ap = appraisal_by_emp.get(emp_id)
        if ap:
            ext = ext_map.get(ap["name"]) or {}
            overall, potential = ratings(emp_id, ext)
            team.append({
                "employee":       emp_id,
                "employee_name":  emp_names.get(emp_id, emp_id),
                "appraisal":      ap["name"],
                "review_status":  ext.get("review_status") or "Not Started",
                "overall_rating": overall,
                "potential_rating": potential,
                # The overall rating was given on numbers that changed since, and
                # is waiting to be kept or changed (R7). Only to whoever may see
                # the rating itself; never on the subject's own row.
                "rating_needs_answer": (
                    cint(ext.get("overall_rating_flag")) if (overall is not None and emp_id != me) else 0
                ),
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
        # No "rated" count: ratings live in the review, not on the live KPI (R14).
        entry["avg_attainment"] = flt(
            sum(flt(k["attainment_pct"]) for k in kpis) / len(kpis), 1
        ) if kpis else 0
        entry["appraisal"] = appraisal_by_emp.get(emp_id, "")
        team.append(entry)

    return {"team": team, "cycle": cycle or ""}


@frappe.whitelist()
def save_kpi_manager_review(kpi, rating=None, comment="", potential_rating="", potential_comment=""):
    """Retired in slice 010 group D: rate the item inside the manager review instead."""
    _refuse_rating_outside_review("save_kpi_manager_review", "KPI", kpi)


@frappe.whitelist()
def suggest_ratings(employee, cycle):
    """Pre-fill manager ratings from measured attainment, for review not for record."""
    refuse_own_rating(employee, "Employee", employee, "suggest_ratings")
    _require_can_review(employee)
    appraisal = frappe.db.get_value(
        "Appraisal", {"employee": employee, "appraisal_cycle": cycle, "docstatus": ["!=", 2]}, "name"
    )
    if not appraisal:
        frappe.throw("There is no review for this employee in this cycle.")
    _require_scoring_access(appraisal, employee, "suggest_ratings")
    _ext, copies = _review_copies_for_scoring(appraisal)
    # From the review's own copies, by row name (VIS-7, VIS-3).
    return [
        {
            "item": r.name,
            "kpi_name": r.title,
            "attainment_pct": flt(r.attainment_pct),
            "suggested_rating": flt(rating_from_attainment(r.attainment_pct), 2),
        }
        for r in copies if r.item_type == "KPI"
    ]


@frappe.whitelist()
def get_team_appraisal(employee, cycle):
    """One report's appraisal, for the manager's review screen.

    HR acting for someone outside their own line follows the review's stage and
    company rule (SEC-26, decision 16); it used to open any company's appraisal.
    """
    _require_can_review(employee)
    me = _employee_id()
    if employee not in _reports_of(me):
        appraisal = frappe.db.get_value(
            "Appraisal", {"employee": employee, "appraisal_cycle": cycle, "docstatus": ["!=", 2]}, "name"
        )
        if appraisal:
            _assert_hr_can_view(appraisal)
        elif employee != me and frappe.db.get_value("Employee", employee, "company") not in permitted_companies():
            refuse("This employee belongs to a company you do not look after.",
                   "SEC-26", "get_team_appraisal", "Employee", employee)
    return _appraisal_payload(employee, cycle, subject=employee == me)


@frappe.whitelist()
def sync_appraisal_from_kpis(appraisal):
    """Rewrite an appraisal's goal rows from the employee's current KPIs.

    Manager ratings live on the KPI; the Appraisal is the HRMS-side projection
    of them. Re-running this is safe and idempotent — it is how a manager pulls
    revised ratings through before submitting.
    """
    ap = frappe.get_doc("Appraisal", appraisal)
    _require_scoring_access(appraisal, ap.employee, "sync_appraisal_from_kpis")
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
    """Average the potential ratings on the review's copies onto its record (VIS-7)."""
    ext, copies = _review_copies_for_scoring(appraisal)
    rated = [flt(r.potential_rating) for r in copies if flt(r.potential_rating)]
    if not rated:
        return
    ext.avg_potential_rating = flt(sum(rated) / len(rated), 2)
    review_items.save_review_record(ext)


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

    HR only, and only for the companies they look after (SEC-20). An item an
    open review still holds keeps its cycle and is listed under
    held_by_open_review: the new cycle's review copies it instead (R16).
    """
    _require_hr()
    start, end = _cycle_window(cycle)
    if not start or not end:
        frappe.throw(f"Cycle '{cycle}' has no period set.")

    people = frappe.get_all(
        "Employee", filters={"company": ["in", permitted_companies() or [""]]}, pluck="name"
    )
    if employee:
        if employee not in people:
            refuse("This employee belongs to a company you do not look after.",
                   "SEC-20", "attach_ongoing_to_cycle", "Employee", employee)
        people = [employee]

    closed = set(frappe.get_all(
        "Appraisal Cycle", filters={"status": "Completed"}, pluck="name"
    ))

    def claimable(current):
        return (not current) or current == cycle or current in closed

    attached = {"goals": [], "kpis": [], "held_by_open_review": {"goals": [], "kpis": []}}

    goal_filters = {"docstatus": ["!=", 2], "status": ["!=", "Cancelled"], "employee": ["in", people or [""]]}
    kpi_filters = {"status": ["!=", "Cancelled"], "employee": ["in", people or [""]]}

    goals = [g for g in frappe.get_all("Individual Goal", filters=goal_filters,
                                       fields=["name", "goal_name", "start_date", "end_date",
                                               "appraisal_cycle"], ignore_permissions=True)
             if claimable(g.appraisal_cycle) and g.appraisal_cycle != cycle
             and _overlaps(str(g.start_date or ""), str(g.end_date or ""), str(start), str(end))]
    kpis = [k for k in frappe.get_all("KPI", filters=kpi_filters,
                                      fields=["name", "kpi_name", "period_start", "period_end",
                                              "appraisal_cycle"], ignore_permissions=True)
            if claimable(k.appraisal_cycle) and k.appraisal_cycle != cycle
            and _overlaps(str(k.period_start or ""), str(k.period_end or ""), str(start), str(end))]

    # One lookup per kind: which of these does an open review still hold (R2)?
    held_goals = review_items.holds("Individual Goal", [g.name for g in goals])
    held_kpis = review_items.holds("KPI", [k.name for k in kpis])
    for g in goals:
        if g.name in held_goals:
            attached["held_by_open_review"]["goals"].append(g.goal_name)
            continue
        frappe.db.set_value("Individual Goal", g.name, "appraisal_cycle", cycle, update_modified=False)
        attached["goals"].append(g.goal_name)
    for k in kpis:
        if k.name in held_kpis:
            attached["held_by_open_review"]["kpis"].append(k.kpi_name)
            continue
        frappe.db.set_value("KPI", k.name, "appraisal_cycle", cycle, update_modified=False)
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
    # The cycle is part of the definition an open review locks (R2). This write
    # skips the document's own lock, so it asks here.
    if review_items.holds(doctype, [name]):
        refuse("This item is in an open review, so its cycle cannot be changed now.",
               "R2", "set_cycle_membership", doctype, name)

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

    Slice 010 group D: once the employee's review for this cycle has its own
    copies, and the caller may open that review at its stage, the list is built
    from those copies by row name and never names a live record (VIS-3). Before
    that, or for someone who may not open the review yet (a manager while the
    self-review is still a draft, PRIV-2), it is the live Objectives and KPIs.
    No rating in either (R14): `source` says which one it is.
    """
    me = _require_employee()
    emp = employee or me
    if emp != me:
        _require_manages(emp)
        if emp not in _subordinates(me) and frappe.db.get_value("Employee", emp, "company") not in permitted_companies():
            # HR acts only for the companies they look after (decision 16).
            refuse("This employee belongs to a company you do not look after.",
                   "SEC-26", "get_cycle_items", "Employee", emp)

    copies = _cycle_items_from_review(emp, me, cycle)
    if copies is not None:
        return copies

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
                "unit", "status", "period_start", "period_end", "weightage"],
        ignore_permissions=True,
    )
    for k in kpis:
        _serialise_dates(k, "period_start", "period_end")
        k["kind"] = "kpi"
        k["label"] = k["kpi_name"]
        k["is_overdue"] = int(_is_overdue(k["period_end"]))

    return _cycle_items_result(cycle, emp, goals, kpis, "live")


def _cycle_items_result(cycle, emp, goals, kpis, source):
    total = sum(flt(i["weightage"]) for i in goals + kpis)
    return {
        "cycle": cycle,
        "employee": emp,
        "source": source,
        "goals": goals,
        "kpis": kpis,
        "total_weightage": flt(total, 2),
        "weightage_complete": flt(total, 2) == TOTAL_WEIGHTAGE,
        "overdue_count": sum(1 for i in goals + kpis if i["is_overdue"]),
    }


def _cycle_items_from_review(emp, me, cycle):
    """get_cycle_items from the review's copies, or None when the live list applies."""
    appraisal = frappe.db.get_value(
        "Appraisal", {"employee": emp, "appraisal_cycle": cycle, "docstatus": ["!=", 2]}, "name"
    )
    ext = _extension(appraisal) if appraisal else None
    if not ext or not ext.get("items_taken_on"):
        return None
    if emp != me and (ext.review_status or "Not Started") in _SELF_REVIEW_DRAFT:
        return None
    if emp != me:
        _assert_hr_can_view(appraisal)

    goals, kpis = [], []
    for row in ext.review_items:
        if row.removed:
            continue
        item = {
            "name": row.name, "label": row.title or "", "unit": row.unit or "",
            "target_value": flt(row.target_value), "weightage": flt(row.weightage),
            "status": "Cancelled" if row.source_cancelled else "Active",
            "is_overdue": int(_is_overdue(row.period_end)),
        }
        if row.item_type == "Objective":
            item.update({"kind": "goal", "goal_name": item["label"], "actual_progress": flt(row.actual_value),
                         "progress_pct": flt(row.attainment_pct),
                         "start_date": str(row.period_start or ""), "end_date": str(row.period_end or "")})
            goals.append(item)
        else:
            item.update({"kind": "kpi", "kpi_name": item["label"], "actual_value": flt(row.actual_value),
                         "attainment_pct": flt(row.attainment_pct),
                         "period_start": str(row.period_start or ""), "period_end": str(row.period_end or "")})
            kpis.append(item)
    return _cycle_items_result(cycle, emp, goals, kpis, "review")


def _review_copies_for_scoring(appraisal):
    """The review's live copies, or a refusal. Scores never fall back to the live
    Objectives and KPIs (VIS-7)."""
    ext = _extension(appraisal)
    if not ext or not ext.get("items_taken_on"):
        frappe.throw("This review has no items of its own yet. Open the review first: "
                     "scores are taken from the review, not from the live Objectives and KPIs.")
    return ext, [r for r in ext.review_items if not r.removed]


def _scored_items(ap):
    """Items carrying a weightage — the rows an appraisal scores.

    From the review's own copies (VIS-7): a KPI scores its manager rating, an
    Objective its attainment on the same 0-5 scale. Only an appraisal that is
    being created, before its review record can exist, is projected from the
    live records tagged to the cycle (hr_generate_appraisals).

    Zero-weightage items ride along for context but are not part of the score.
    """
    if not ap.is_new():
        _ext, copies = _review_copies_for_scoring(ap.name)
        return [
            {"label": r.title, "weightage": flt(r.weightage),
             "score": flt(r.manager_rating) if r.item_type == "KPI" else flt(rating_from_attainment(r.attainment_pct)),
             "end_date": r.period_end}
            for r in sorted(copies, key=lambda r: (r.item_type != "KPI", r.title or ""))
            if flt(r.weightage)
        ]
    return _scored_live_items(ap.employee, ap.appraisal_cycle)


def _scored_live_items(employee, cycle):
    """The first projection of a new appraisal, before it has a review record."""
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
    rows = _scored_items(ap)
    who = ap.employee_name or ap.employee

    if not rows:
        if ap.is_new():
            attached = frappe.db.count("KPI", {"employee": ap.employee,
                                               "appraisal_cycle": ap.appraisal_cycle}) + \
                       frappe.db.count("Individual Goal", {"employee": ap.employee,
                                                           "appraisal_cycle": ap.appraisal_cycle})
        else:
            attached = len(_review_copies_for_scoring(ap.name)[1])
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
    _require_scoring_access(appraisal, ap.employee, "submit_appraisal")
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


def _build_formula(cycle):
    """The cycle's own weights decide the formula. Until attendance is switched
    on for a cycle this is "goal_score", which is what the portal always wrote."""
    from hrms.alvoraa_hr_core.attendance_score import build_formula
    return build_formula(cycle)


def _apply_scoring(cycle, scoring):
    """Copy the wizard's "How the score is built" step onto the Appraisal Cycle.
    Ignored unless the tenant has the attendance-scoring feature."""
    import json
    if not scoring:
        return
    from alvoraa_portal.subscription import has_feature
    if not has_feature("attendance_scoring"):
        return
    if isinstance(scoring, str):
        scoring = json.loads(scoring or "{}")
    cycle.include_attendance_score = cint(scoring.get("include_attendance"))
    for src, dst in (
        ("goal_weight", "goal_weight"),
        ("feedback_weight", "feedback_weight"),
        ("attendance_weight", "attendance_weight"),
        ("reliability_weight", "attendance_reliability_weight"),
        ("punctuality_weight", "attendance_punctuality_weight"),
        ("deduction_penalty", "attendance_deduction_penalty"),
    ):
        if scoring.get(src) not in (None, ""):
            cycle.set(dst, flt(scoring.get(src)))
    cycle.count_paid_leave_as_absent = cint(scoring.get("count_paid_leave_as_absent"))
    if scoring.get("when_no_data"):
        cycle.attendance_when_no_data = scoring.get("when_no_data")
    cycle.set("attendance_exempt_grades",
              [{"employee_grade": g} for g in (scoring.get("exempt_grades") or []) if g])


def _precompute_attendance(cycle, employees):
    """One pass over attendance for every employee about to get an appraisal,
    so the save hook does not query per employee."""
    from hrms.alvoraa_hr_core.attendance_score import precompute
    precompute(cycle, list(employees))


def _cycle_scoring(cycle):
    from hrms.alvoraa_hr_core.attendance_score import cycle_scoring
    return cycle_scoring(cycle)


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
    cycle.final_score_formula = _build_formula(cycle)
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
    grades = frappe.get_all("Employee Grade", pluck="name", order_by="name")
    return {"departments": departments, "designations": designations, "managers": managers,
            "grades": grades}


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
                      page_settings=None, selected_employees=None, existing_cycle=None,
                      scoring=None):
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
        _apply_scoring(cycle, scoring)
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
        _apply_scoring(cycle, scoring)
        cycle.final_score_formula = _build_formula(cycle)
        cycle.status = "Not Started"
        cycle.insert(ignore_permissions=True)

    # Save or update the Alvoraa Cycle Config
    emp_fields_json   = json.dumps(employee_fields) if isinstance(employee_fields, (dict, list)) else (employee_fields or "{}")
    page_config_json  = json.dumps(page_config)     if isinstance(page_config,     (dict, list)) else (page_config     or "{}")
    page_settings_json = json.dumps(page_settings)  if isinstance(page_settings,   (dict, list)) else (page_settings   or "{}")

    if frappe.db.exists("Alvoraa Cycle Config", cycle.name):
        cfg = frappe.get_doc("Alvoraa Cycle Config", cycle.name)
    else:
        cfg = frappe.new_doc("Alvoraa Cycle Config")
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

    # Create Appraisal + Alvoraa Appraisal Extension for each selected employee
    created = 0
    skipped = 0
    _precompute_attendance(cycle, emp_list)

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
            ext = frappe.new_doc("Alvoraa Appraisal Extension")
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
    scoring = _cycle_scoring(cycle) if frappe.db.exists("Appraisal Cycle", cycle) else {}
    if not frappe.db.exists("Alvoraa Cycle Config", cycle):
        return {"employee_fields": {}, "page_config": {}, "page_settings": {}, "description": "",
                "scoring": scoring}
    cfg = frappe.get_doc("Alvoraa Cycle Config", cycle)
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
        "scoring":        scoring,
    }


@frappe.whitelist()
def search_employees(query="", appraisal=None):
    """Find people to invite as reviewers, by name or employee ID.

    It used to return up to 100 active employees of every company to anyone
    logged in (slice 010 group D, commit 9).

    With `appraisal` (the reviewer picker): only someone who may invite
    reviewers for that review - its manager line, or HR under the review's stage
    and company rule, never the person reviewed (SEC-7, SEC-10). Results are
    active employees of the reviewed person's company, not limited to the
    manager's line (decision 2), never the reviewed person.

    Without it (the page does not send it yet): a manager searches their own
    company, HR the companies they look after, anyone else finds nobody.
    At most 50 people.
    """
    if frappe.session.user == "Guest":
        frappe.throw("Please log in.", frappe.PermissionError)
    query = (query if isinstance(query, str) else "").strip()
    me = _employee_id()
    subject = None
    if appraisal:
        if not isinstance(appraisal, str):
            frappe.throw("Choose the review you are finding reviewers for.")
        subject = frappe.db.get_value("Appraisal", appraisal, "employee")
        if not subject:
            frappe.throw("Appraisal not found.")
        refuse_own_rating(subject, "Appraisal", appraisal, "search_employees")
        if not _is_line_manager(subject, me):
            if not _is_hr():
                refuse("You can only find reviewers for a review you manage.",
                       "SEC-7", "search_employees", "Appraisal", appraisal)
            _assert_hr_can_view(appraisal)
        companies = [frappe.db.get_value("Employee", subject, "company")]
    elif _is_hr():
        companies = permitted_companies()
    elif me and _reports_of(me):
        companies = [frappe.db.get_value("Employee", me, "company")]
    else:
        return []

    companies = [c for c in companies if c]
    if not companies:
        return []
    filters = {"status": "Active", "company": ["in", companies]}
    if subject:
        filters["name"] = ["!=", subject]
    or_filters = None
    if query:
        or_filters = [["employee_name", "like", f"%{query}%"], ["name", "like", f"%{query}%"]]
    return frappe.get_all(
        "Employee",
        filters=filters,
        or_filters=or_filters,
        fields=["name", "employee_name", "designation", "department"],
        order_by="employee_name asc",
        limit=50,
    )


def _check_invitees(ap, employees, endpoint):
    """Invited reviewers are active employees of the reviewed person's company,
    and never the reviewed person (SEC-7). One refusal stops the whole call, so
    nothing is invited and nobody is emailed."""
    wanted = sorted({e for e in employees if e})
    company = frappe.db.get_value("Employee", ap.employee, "company")
    allowed = set(frappe.get_all(
        "Employee",
        filters={"name": ["in", wanted or [""]], "status": "Active", "company": company},
        pluck="name",
    ))
    for employee in wanted:
        if employee == ap.employee or employee not in allowed:
            refuse("Reviewers must be active employees of the same company as the person reviewed, "
                   "and not that person.", "SEC-7", endpoint, "Appraisal", ap.name)


@frappe.whitelist()
def get_rating_scales():
    """Return all organisation rating scales with their points."""
    if frappe.session.user == "Guest":
        frappe.throw("Please log in.", frappe.PermissionError)
    scales = frappe.get_all(
        "Alvoraa Rating Scale",
        fields=["name", "scale_name", "description", "is_default"],
        order_by="scale_name",
    )
    for s in scales:
        s["items"] = frappe.get_all(
            "Alvoraa Rating Scale Item",
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

    if existing_name and frappe.db.exists("Alvoraa Rating Scale", existing_name):
        doc = frappe.get_doc("Alvoraa Rating Scale", existing_name)
        doc.scale_name = scale_name
    else:
        if frappe.db.exists("Alvoraa Rating Scale", scale_name):
            frappe.throw(f"A scale called '{scale_name}' already exists.")
        doc = frappe.new_doc("Alvoraa Rating Scale")
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
    if not frappe.db.exists("Alvoraa Rating Scale", name):
        frappe.throw("Rating scale not found.")
    frappe.delete_doc("Alvoraa Rating Scale", name, ignore_permissions=True)
    frappe.db.commit()
    return {"message": "Deleted."}


@frappe.whitelist()
def hr_list_appraisals(cycle, show_archived=0):
    """Return all appraisals in a cycle with employee info and review_status from Alvoraa Appraisal Extension.

    Only reviews the caller may list (SEC-26): the companies they look after and
    their own line. The overall rating follows the review's stage (decision 3).
    """
    reviews = _hr_cycle_reviews(cycle, include_cancelled=True)
    if not reviews:
        return []
    emails = _responsible_emails(reviews)
    result = []
    for a in reviews:
        archived = int(a.extension.get("archived") or 0)
        if archived and not int(show_archived):
            continue
        result.append({
            "name": a.name,
            "employee": a.employee,
            "employee_name": a.employee_name,
            "department": a.department,
            "designation": a.designation,
            "review_status": a.status,
            "overall_rating": a.extension.get("overall_rating")
                              if review_items.overall_rating_visible(a.viewer, a.status) else None,
            "archived": archived,
            "responsible_email": emails.get(a.name, ""),
        })
    return result


def _responsible_emails(reviews):
    """Whoever should act at each review's stage, by email: the employee, or the
    manager in Manager Review. Two queries, plus one for the stand-in HR manager
    when someone has no manager (it used to be three queries per row)."""
    def email(person):
        return (person.company_email or person.prefered_email or person.personal_email or "") if person else ""

    fields = ["name", "company_email", "prefered_email", "personal_email", "reports_to"]
    people = {e.name: e for e in frappe.get_all(
        "Employee", filters={"name": ["in", sorted({a.employee for a in reviews}) or [""]]}, fields=fields)}
    manager_of = {}
    for a in reviews:
        if a.status == "Manager Review":
            person = people.get(a.employee)
            manager_of[a.name] = (person.reports_to if person and person.reports_to
                                  else get_effective_manager(a.employee))
    managers = {e.name: e for e in frappe.get_all(
        "Employee", filters={"name": ["in", sorted({m for m in manager_of.values() if m}) or [""]]}, fields=fields)}

    out = {}
    for a in reviews:
        if a.status in ("Not Started", "Employee Review", "Employee Final Review"):
            out[a.name] = email(people.get(a.employee))
        elif a.status == "Manager Review":
            out[a.name] = email(managers.get(manager_of.get(a.name)))
        else:
            out[a.name] = ""
    return out


def _require_hr_for(appraisal, endpoint):
    """HR acting on one review: only for the companies they look after, or their
    own line (SEC-26, decision 16). Returns the review's employee."""
    _require_hr()
    owner = frappe.db.get_value("Appraisal", appraisal, "employee")
    if not owner:
        frappe.throw("Appraisal not found.")
    me = _employee_id()
    if me and (owner == me or owner in _subordinates(me)):
        return owner
    if frappe.db.get_value("Employee", owner, "company") not in permitted_companies():
        refuse("This appraisal belongs to a company you do not look after.",
               "SEC-26", endpoint, "Appraisal", appraisal)
    return owner


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
    """Send an email reminder to whoever is responsible at the current review stage.

    For the companies the caller looks after (SEC-26). Reads the stage without
    creating a review record (SEC-6).
    """
    _require_hr_for(appraisal, "send_review_reminder")
    ap = frappe.get_doc("Appraisal", appraisal)
    status = _review_status(appraisal)

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
    """HR-only: mark a completed review as archived (hidden from default list).

    For the companies the caller looks after (SEC-26); never creates a record.
    """
    _require_hr_for(appraisal, "archive_review")
    ext = _extension(appraisal)
    if not ext or ext.review_status != "Completed":
        frappe.throw("Only completed reviews can be archived.")
    ext.archived = 1
    ext.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": "Review archived."}


@frappe.whitelist()
def unarchive_review(appraisal):
    """HR-only: restore an archived review to the active list.

    For the companies the caller looks after (SEC-26); never creates a record.
    """
    _require_hr_for(appraisal, "unarchive_review")
    ext = _extension(appraisal)
    if not ext:
        frappe.throw("This review has not started yet.")
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
    # Cascade is derived from the linked objective (see alvoraa_goals.controllers
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
    from alvoraa_goals.permissions import manageable_employees, descendants

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
    from alvoraa_goals.permissions import MAX_TREE_DEPTH

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
        g["children"] = []
        g["kpis"] = []
    # The tree's "in review" tag means an open review holds the record, not just
    # that it is tagged to a cycle (R5). One query per kind; the badge says only
    # that, and from which day updates no longer change the review (PRIV-10).
    goal_badges = review_items.review_badges("Individual Goal", [g["name"] for g in goals])
    for g in goals:
        g["review_badge"] = goal_badges.get(g["name"])
        g["in_cycle"] = (g.get("appraisal_cycle") or "") if g["review_badge"] else ""
    for k in kpis:
        k["type"] = "kpi"
        k["trajectory"] = _kpi_trajectory(k)
        _serialise_dates(k, "period_start", "period_end")
        k["is_overdue"] = int(_is_overdue(k["period_end"]))
    _decorate_kpis(kpis)
    for k in kpis:
        k["in_cycle"] = (k.get("appraisal_cycle") or "") if k["review_badge"] else ""

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


# ── HR cycle screens read the review record (slice 010 group D: R8, SEC-26) ──
#
# Calibration, the cycle summary, the HR KPI list, the appraisals table and the
# CSV export show each review's own copies, never the live Objectives and KPIs,
# and only for the reviews the caller may list. A row's ratings follow the same
# rule as the review screens (review_items.rating_fields_for).

_COPY_FIELDS = [
    "name", "parent", "idx", "item_type", "source_doctype", "source_name", "title", "unit", "direction",
    "category", "baseline_value", "target_value", "weightage", "period_start", "period_end",
    "actual_value", "attainment_pct", "facts_count", "source_cancelled", "removed",
    "self_rating", "self_comment", "manager_rating", "manager_comment", "potential_rating", "potential_comment",
]


def _hr_cycle_reviews(cycle, employee=None, include_cancelled=False):
    """The reviews in one cycle this HR person may list, and what each row may show.

    Scope (SEC-26, decision 16): subjects of the companies the caller looks
    after, plus the caller's own line and their own review. Each row gets
    `status`, `extension` and `viewer`, which review_items.rating_fields_for reads:
      subject  the caller's own review
      manager  someone in the caller's line
      hr       anyone else, once the review has reached HR Review
      none     anyone else before that: status and counts, no rating (fail closed)
    A fixed number of queries whatever the size of the cycle.
    """
    _require_hr()
    me = _employee_id()
    line = set(_subordinates(me)) if me else set()
    filters = {"appraisal_cycle": cycle}
    if not include_cancelled:
        filters["docstatus"] = ["!=", 2]
    if employee:
        filters["employee"] = employee
    appraisals = frappe.get_all(
        "Appraisal",
        filters=filters,
        or_filters=[
            ["company", "in", permitted_companies() or [""]],
            ["employee", "in", sorted(line | {me}) if me else [""]],
        ],
        fields=["name", "employee", "employee_name", "department", "designation", "company", "docstatus",
                "total_score", "final_score", "attendance_score", "attendance_summary"],
        order_by="employee_name asc",
    )
    extensions = {
        e.name: e for e in frappe.get_all(
            "Alvoraa Appraisal Extension",
            filters={"name": ["in", [a.name for a in appraisals] or [""]]},
            fields=["name", "review_status", "overall_rating", "potential_rating", "avg_potential_rating",
                    "potential_category", "archived", "frozen", "frozen_on", "review_window_start",
                    "review_window_end", "items_taken_on"],
        )
    }
    for a in appraisals:
        a.extension = extensions.get(a.name) or frappe._dict()
        a.status = a.extension.get("review_status") or "Not Started"
        if me and a.employee == me:
            a.viewer = review_items.VIEWER_SUBJECT
        elif a.employee in line:
            a.viewer = review_items.VIEWER_MANAGER
        elif a.status in ("HR Review", "Completed"):
            a.viewer = review_items.VIEWER_HR
        else:
            a.viewer = review_items.VIEWER_NONE
    return appraisals


def _copies_of(reviews):
    """Every copy of these reviews, by review name, in their order. One query."""
    names = [a.name for a in reviews if a.extension.get("items_taken_on")]
    out = {}
    if not names:
        return out
    for row in frappe.get_all(
        "Alvoraa Review Item",
        filters={"parenttype": "Alvoraa Appraisal Extension", "parent": ["in", names]},
        fields=_COPY_FIELDS,
        order_by="parent asc, idx asc",
    ):
        out.setdefault(row.parent, []).append(row)
    return out


def _visible_ratings(row, review):
    """The rating and comment fields of one copy this row's viewer may see; absent otherwise."""
    return {
        field: flt(row.get(field)) if field.endswith("_rating") else (row.get(field) or "")
        for field in review_items.rating_fields_for(review.viewer, review.status)
    }


def _copy_numbers(row):
    return {
        "unit": row.unit or "", "direction": row.direction or "", "category": row.category or "",
        "baseline_value": flt(row.baseline_value), "target_value": flt(row.target_value),
        "actual_value": flt(row.actual_value), "attainment_pct": flt(row.attainment_pct),
        "weightage": flt(row.weightage),
        "period_start": str(row.period_start or ""), "period_end": str(row.period_end or ""),
    }


@frappe.whitelist()
def hr_list_kpis(cycle=None, employee=None):
    """One cycle's KPIs as its reviews hold them, for HR (R8).

    From each review's own copies, by row name; only reviews the caller may
    list, with ratings only where the stage allows (SEC-26). A cycle is needed:
    without one this used to return every KPI in the tenant.
    """
    _require_hr()
    if not cycle:
        frappe.throw("Choose a cycle. This list shows the KPIs each review in that cycle holds.")
    reviews = _hr_cycle_reviews(cycle, employee)
    copies = _copies_of(reviews)
    out = []
    for a in reviews:
        for row in copies.get(a.name, []):
            if row.removed or row.item_type != "KPI":
                continue
            item = {
                "name": row.name, "kpi_name": row.title or "", "employee": a.employee,
                "employee_name": a.employee_name, "appraisal": a.name, "appraisal_cycle": cycle,
                "review_status": a.status, "status": "Cancelled" if row.source_cancelled else "Active",
            }
            item.update(_copy_numbers(row))
            item.update(_visible_ratings(row, a))
            out.append(item)
    return out


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
    _precompute_attendance(cycle_doc, employees)

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
    """Progress board for one cycle: who is assigned, rated, and submitted.

    From each review's own copies (R8), for the reviews the caller may list
    (SEC-26). A row before HR Review, for someone outside the caller's line,
    carries counts and weightage but no rating, rated count or final score.
    """
    reviews = _hr_cycle_reviews(cycle)
    copies = _copies_of(reviews)

    rows = []
    appraisals = {}
    for a in reviews:
        live = [c for c in copies.get(a.name, []) if not c.removed]
        kpis = [c for c in live if c.item_type == "KPI"]
        total_weightage = flt(sum(flt(c.weightage) for c in live), 2)
        row = {
            "employee": a.employee,
            "employee_name": a.employee_name,
            "appraisal": a.name,
            "review_status": a.status,
            "item_count": len(live),
            "kpi_count": len(kpis),
            "total_weightage": total_weightage,
            "weightage_ok": total_weightage == TOTAL_WEIGHTAGE,
            "avg_attainment": flt(sum(flt(c.attainment_pct) for c in kpis) / len(kpis), 1) if kpis else 0,
            "submitted": a.docstatus == 1,
            "attendance_score": flt(a.attendance_score) if a.attendance_summary else None,
        }
        if "manager_rating" in review_items.rating_fields_for(a.viewer, a.status):
            row["rated"] = sum(1 for c in kpis if flt(c.manager_rating) > 0)
        final_visible = review_items.overall_rating_visible(a.viewer, a.status)
        if final_visible:
            row["final_score"] = flt(a.final_score)
        rows.append(row)
        appraisals[a.employee] = {"attendance_score": a.attendance_score, "attendance_summary": a.attendance_summary,
                                  "final_score": a.final_score if final_visible else None}

    rows.sort(key=lambda r: r["employee_name"] or "")
    scoring = _cycle_scoring(cycle)
    return {
        "cycle": cycle,
        "rows": rows,
        "scoring": scoring,
        "attendance_by_branch": _attendance_by_branch(appraisals) if scoring.get("include_attendance") else [],
        "assigned": len(rows),
        "with_appraisal": sum(1 for r in rows if r["appraisal"]),
        "submitted": sum(1 for r in rows if r["submitted"]),
    }


def _attendance_by_branch(appraisals):
    """Average attendance and final score per branch, for the HR cycle board.

    A final score the caller may not see yet (final_score None) counts for the
    attendance average only (slice 010 group D, SEC-26).
    """
    scored = {emp: ap for emp, ap in appraisals.items() if ap.get("attendance_summary")}
    if not scored:
        return []
    branch_of = dict(frappe.get_all("Employee", filters={"name": ["in", list(scored)]},
                                    fields=["name", "branch"], as_list=True))
    groups = {}
    for emp, ap in scored.items():
        g = groups.setdefault(branch_of.get(emp) or "No branch",
                              {"count": 0, "attendance": 0.0, "final": 0.0, "final_count": 0})
        g["count"] += 1
        g["attendance"] += flt(ap["attendance_score"])
        if ap.get("final_score") is not None:
            g["final"] += flt(ap["final_score"])
            g["final_count"] += 1
    return sorted(
        [{"branch": b, "count": g["count"],
          "avg_attendance": flt(g["attendance"] / g["count"], 2),
          "avg_final": flt(g["final"] / g["final_count"], 2) if g["final_count"] else None}
         for b, g in groups.items()],
        key=lambda r: r["branch"],
    )


# ══════════════════════════════════════════════════════════════════════════
# Alvoraa Appraisal Extension — review workflow, narrative, action items
# ══════════════════════════════════════════════════════════════════════════

_REVIEW_STATUS_FLOW = {
    "Not Started": "Employee Review",
    "Employee Review": "Manager Review",
    "Manager Review": "Employee Final Review",
    "Employee Final Review": "HR Review",
    "HR Review": "Completed",
}


def _get_or_create_extension(appraisal):
    """Return the review record for this appraisal, creating it if absent.

    Call this only once the caller is allowed to start the record: the subject,
    or HR setting up a cycle. Everyone else uses _extension(), which never
    creates one (SEC-6).
    """
    if frappe.db.exists("Alvoraa Appraisal Extension", appraisal):
        return frappe.get_doc("Alvoraa Appraisal Extension", appraisal)
    ap = frappe.db.get_value("Appraisal", appraisal, ["employee", "appraisal_cycle"], as_dict=True) or {}
    ext = frappe.new_doc("Alvoraa Appraisal Extension")
    ext.appraisal = appraisal
    # The desk and HR scorecards find reviews by employee and cycle.
    ext.employee = ap.get("employee")
    ext.appraisal_cycle = ap.get("appraisal_cycle")
    ext.review_status = "Not Started"
    ext.insert(ignore_permissions=True)
    frappe.db.commit()
    return ext


# Stages in which only the subject may see the review (PRIV-2), and from which
# the subject may see the overall rating (decision 3).
_SELF_REVIEW_DRAFT = ("Not Started", "Employee Review")
_RATING_RELEASED = ("Employee Final Review", "HR Review", "Completed")


def _extension(appraisal):
    """The review record, or None. Never creates one (SEC-6)."""
    if frappe.db.exists("Alvoraa Appraisal Extension", appraisal):
        return frappe.get_doc("Alvoraa Appraisal Extension", appraisal)
    return None


def _review_status(appraisal):
    """The review's stage without loading or creating the record."""
    return frappe.db.get_value(
        "Alvoraa Appraisal Extension", appraisal, "review_status"
    ) or "Not Started"


def _is_line_manager(employee, me, direct_only=False):
    """Is `me` this employee's manager for a manager review?

    The reporting line (direct reports only where an endpoint always was), or,
    for an employee with no manager at all, the HR Manager the portal treats as
    their manager (get_effective_manager). That stand-in is limited to the
    manager-review actions; it does not open the review anywhere else.
    """
    if not me or not employee:
        return False
    if direct_only:
        if employee in _reports_of(me):
            return True
    elif _is_manager_of(employee):
        return True
    return (
        not frappe.db.get_value("Employee", employee, "reports_to")
        and get_effective_manager(employee) == me
    )


def _manager_review_record(appraisal, endpoint, direct_only=False,
                           stage_message="Review is not in Manager Review stage."):
    """Everything a manager-review write checks, in order, before it reads or writes (SEC-6).

    1. never the subject, whatever roles they hold (SEC-10);
    2. the manager line (direct reports only where the endpoint always was), or HR;
    3. HR acting for someone else: the stage and company rule;
    4. the review must exist and be in Manager Review.

    Then the review's copies are brought up to date, so a rating stamped next is
    stamped on current numbers.
    """
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)
    refuse_own_rating(ap.employee, "Appraisal", appraisal, endpoint)
    if not _is_line_manager(ap.employee, me, direct_only):
        if not _is_hr():
            frappe.throw("Not permitted.", frappe.PermissionError)
        _assert_hr_can_view(appraisal)
    ext = _extension(appraisal)
    if not ext or ext.review_status != "Manager Review":
        frappe.throw(stage_message)
    review_items.open_review(ext)
    return ap, ext


def _sent_rating(value):
    """A rating the page really sent, or None when it sent nothing.

    The page's "Save draft" sends 0 for a rating the manager did not touch on
    this visit, so 0 and blank mean "leave it as it is".
    """
    if value in (None, ""):
        return None
    rating = flt(value)
    if rating <= 0:
        return None
    if rating > MAX_RATING:
        frappe.throw(f"Rating must be between 0 and {int(MAX_RATING)}.")
    return rating


def _set_manager_ratings(ext, overall_rating, potential_rating):
    """Change only the ratings that were sent; stamp the overall rating (R7)."""
    overall = _sent_rating(overall_rating)
    if overall is not None and flt(ext.overall_rating) != overall:
        ext.overall_rating = overall
        review_items.stamp_overall_rating(ext)
    potential = _sent_rating(potential_rating)
    if potential is not None:
        ext.potential_rating = potential


@frappe.whitelist()
def get_appraisal_extension(appraisal):
    """The review record for this appraisal, cut to what this viewer may see.

    - The subject never receives the potential rating or its category (PRIV-1),
      and sees the overall rating from Employee Final Review on (decision 3).
    - Anyone else sees the self-review narrative only once it has been sent
      (PRIV-2).
    - Only the subject's own visit may start the record (SEC-6).
    """
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)
    if not _is_hr() and ap.employee != me and ap.employee not in _subordinates(me):
        frappe.throw("Not permitted.", frappe.PermissionError)
    _assert_hr_can_view(appraisal)

    is_employee_self = (ap.employee == me)
    ext = _get_or_create_extension(appraisal) if is_employee_self else _extension(appraisal)
    status = (ext.review_status if ext else None) or "Not Started"
    draft_hidden = not is_employee_self and status in _SELF_REVIEW_DRAFT

    def text(field):
        return "" if (not ext or draft_hidden) else (ext.get(field) or "")

    action_items = [
        {
            "name": row.name,
            "description": row.description,
            "assigned_to": row.assigned_to or "",
            "assigned_to_name": row.assigned_to_name or "",
            "due_date": str(row.due_date) if row.due_date else "",
            "status": row.status or "Open",
        }
        for row in ((ext.action_items or []) if ext else [])
    ]
    out = {
        "appraisal": appraisal,
        "review_status": status,
        "achievements_text": text("achievements_text"),
        "challenges_text": text("challenges_text"),
        "development_needs_text": text("development_needs_text"),
        "support_needed": text("support_needed"),
        "overall_rating": flt(ext.overall_rating) if ext and (
            not is_employee_self or status in _RATING_RELEASED
        ) else None,
        "next_period_goals_text": text("next_period_goals_text"),
        "return_reason": (ext.return_reason or "") if ext else "",
        "action_items": action_items,
    }
    if not is_employee_self:
        out["avg_potential_rating"] = flt(ext.avg_potential_rating) if ext else 0
        out["potential_category"] = (ext.potential_category or "") if ext else ""
    return out


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

    # Stage from the record without creating it; nothing is created before the
    # caller is known to be allowed (SEC-6).
    current = _review_status(appraisal)
    nxt = _REVIEW_STATUS_FLOW.get(current)
    if not nxt:
        frappe.throw("Review is already Completed.")

    # Authorisation: who can advance from each stage
    if current in ("Not Started", "Employee Review"):
        if ap.employee != me:
            frappe.throw("Only the employee can advance from this stage.", frappe.PermissionError)
    elif current == "Manager Review":
        refuse_own_rating(ap.employee, "Appraisal", appraisal, "advance_review_status")
        if not _is_line_manager(ap.employee, me, direct_only=True):
            if not _is_hr():
                frappe.throw("Only the direct manager or HR can advance from Manager Review.",
                             frappe.PermissionError)
            _assert_hr_can_view(appraisal)
    elif current == "Employee Final Review":
        if ap.employee != me:
            frappe.throw("Only the subject employee can acknowledge the final review.",
                         frappe.PermissionError)
    elif current == "HR Review":
        _require_hr()
        # Nobody completes their own review, whatever roles they hold (SEC-10).
        refuse_own_rating(ap.employee, "Appraisal", appraisal, "advance_review_status")
        _assert_hr_can_view(appraisal)

    ext = _get_or_create_extension(appraisal)
    if current == "Manager Review":
        if not ext.action_items:
            frappe.throw("At least one action item must be added before advancing the review. "
                         "Use the 'Add Action Item' button in the team review card.")

    write_back_notes = 0
    if nxt == "Completed":
        # Numbers are brought up to date first, so a rating question raised by
        # the last facts is seen now rather than after the review closes (R7).
        review_items.open_review(ext)
        _refuse_open_rating_questions(ext, appraisal)

    ext.review_status = nxt
    ext.return_reason = ""
    review_items.apply_stage(ext)
    if nxt == "Completed":
        _refuse_open_rating_questions(ext, appraisal)
        ext.completed_on = frappe.utils.now_datetime()
        write_back_notes = review_items.write_back(ext)
    review_items.save_review_record(ext)
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

    out = {"review_status": nxt, "message": f"Review moved to '{nxt}'."}
    if nxt == "Completed":
        # How many items carry a note about handing their changes back (R15).
        out["write_back_notes"] = write_back_notes
    return out


def _refuse_open_rating_questions(ext, appraisal):
    """HR cannot complete a review while a manager or overall rating waits for an
    answer (R7, SEC-23). Self-rating questions are information only (decision 13)."""
    waiting = review_items.open_blocking_flags(ext)
    if waiting:
        refuse(
            f"{waiting} rating(s) were given on numbers that changed since. The person who gave "
            "them must keep or change them before this review can be completed.",
            "SEC-23", "advance_review_status", "Appraisal", appraisal,
        )


@frappe.whitelist()
def return_for_revision(appraisal, reason=""):
    """Manager or HR sends a review back to Employee Review with a reason.

    Once it is back with the employee, the self-review is hidden from everyone
    else again until it is re-sent (PRIV-2 follows the stage).
    """
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)
    refuse_own_rating(ap.employee, "Appraisal", appraisal, "return_for_revision")
    if not (_is_line_manager(ap.employee, me, direct_only=True)
            and _review_status(appraisal) == "Manager Review"):
        if not _is_hr():
            frappe.throw("Only the direct manager or HR can return a review.",
                         frappe.PermissionError)
        _assert_hr_can_view(appraisal)

    ext = _extension(appraisal)
    current = (ext.review_status if ext else None) or "Not Started"
    if current not in ("Manager Review", "HR Review"):
        frappe.throw("Can only return reviews that are in Manager Review or HR Review stage.")
    if current == "HR Review":
        _require_hr()

    ext.review_status = "Employee Review"
    ext.return_reason = reason
    # Back before the freeze point: the numbers take facts again (decision 18).
    review_items.apply_stage(ext)
    review_items.save_review_record(ext)
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

    ext = _extension(appraisal)
    if not ext or (ext.review_status or "") != "Employee Final Review":
        frappe.throw("This action is only available in the Employee Final Review stage.")

    ext.review_status = "Manager Review"
    ext.return_reason = reason
    review_items.apply_stage(ext)
    review_items.save_review_record(ext)
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
    _assert_hr_can_view(appraisal)

    if not description:
        frappe.throw("Action item description is required.")

    ext = _extension(appraisal)
    if not ext:
        frappe.throw("This review has not started yet.")
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
    ext = _extension(appraisal)

    row = next((r for r in (ext.action_items if ext else []) if r.name == row_name), None)
    is_assignee = bool(row and row.assigned_to and row.assigned_to == me)
    is_manager = ap.employee in _reports_of(me)

    if not (_is_hr() or is_manager or is_assignee):
        frappe.throw("Not permitted.", frappe.PermissionError)
    if not (is_manager or is_assignee):
        _assert_hr_can_view(appraisal)
    if not row:
        frappe.throw("Action item not found.")

    row.status = status
    ext.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": f"Action item marked {status}."}


# ══════════════════════════════════════════════════════════════════════════
# Additional reviewers (dotted-line managers / secondary raters)
# ══════════════════════════════════════════════════════════════════════════

def _refuse_additional_reviewer(endpoint, kpi):
    # Per-KPI additional reviewers rated the live KPI, outside any review, and let
    # one reviewer overwrite another (R13, SEC-29). Invited reviewers comment
    # inside the review instead.
    refuse(
        "Ratings are given inside the review. Invite a reviewer from the review instead.",
        "R13", endpoint, "KPI", kpi,
    )


@frappe.whitelist()
def add_additional_reviewer(kpi, reviewer=None, reviewer_role=""):
    """Retired in slice 010 group D."""
    _refuse_additional_reviewer("add_additional_reviewer", kpi)


@frappe.whitelist()
def save_additional_reviewer_rating(kpi, row_name=None, rating=None, comment=""):
    """Retired in slice 010 group D."""
    _refuse_additional_reviewer("save_additional_reviewer_rating", kpi)


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
    """Return a cycle's reviewed Objectives and KPIs as a CSV string. HR only.

    Slice 010 group D: from each review's own copies (R8), for the reviews the
    caller may list, with ratings and comments only where the review's stage
    allows (SEC-26). The first columns keep their order; "KPI ID" is now the
    review's row id, never the live record's (VIS-3). Added at the end: item
    type, review, stage, removed, and facts approved after the numbers froze
    (R10, HR in HR Review and Completed only). One security log line per export,
    with counts only.
    """
    import csv, io, json

    reviews = _hr_cycle_reviews(cycle)
    copies = _copies_of(reviews)
    by_name = {a.name: a for a in reviews}
    late = review_items.late_fact_counts(
        [dict(a.extension, name=a.name) for a in reviews if a.viewer == review_items.VIEWER_HR],
        {name: rows for name, rows in copies.items() if by_name[name].viewer == review_items.VIEWER_HR},
    )
    # Tags kept on the live KPI. Looked up here and never written out by name.
    tags = {
        k.name: k for k in frappe.get_all(
            "KPI",
            filters={"name": ["in", sorted({c.source_name for rows in copies.values() for c in rows
                                            if c.source_doctype == "KPI" and c.source_name}) or [""]]},
            fields=["name", "company_value", "is_extra_initiative"],
        )
    }

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
        "Item Type", "Review", "Review Stage", "Removed", "Facts Approved After Close",
    ]
    writer = csv.writer(buf)
    writer.writerow(headers)
    written = 0
    for a in reviews:
        deciders = a.viewer in (review_items.VIEWER_MANAGER, review_items.VIEWER_HR)
        for row in copies.get(a.name, []):
            if row.removed and not deciders:
                continue
            shown = _visible_ratings(row, a)
            tag = tags.get(row.source_name) if row.source_doctype == "KPI" else None
            status = "Removed" if row.removed else ("Cancelled" if row.source_cancelled else "Active")
            writer.writerow([_csv_cell(v) for v in (
                row.name, row.title or "",
                a.employee, a.employee_name or "",
                row.category or "", row.unit or "", row.direction or "",
                flt(row.target_value), flt(row.actual_value),
                flt(row.attainment_pct), flt(row.weightage),
                shown.get("self_rating", ""), shown.get("self_comment", ""),
                shown.get("manager_rating", ""), shown.get("manager_comment", ""),
                shown.get("potential_rating", ""), shown.get("potential_comment", ""),
                (tag.company_value or "") if tag else "", int(tag.is_extra_initiative or 0) if tag else 0,
                status,
                row.item_type or "", a.name, a.status, int(row.removed or 0), late.get(row.name, 0),
            )])
            written += 1

    try:
        frappe.logger("security").info(json.dumps({
            "event": "export", "at": str(frappe.utils.now_datetime()), "user": frappe.session.user,
            "endpoint": "export_cycle_kpis_csv", "doctype": "Appraisal Cycle", "name": cycle,
            "reviews": len(reviews), "rows": written,
        }))
    except Exception:
        pass
    return {"csv": buf.getvalue(), "cycle": cycle}


def _csv_cell(value):
    """A cell a spreadsheet will not run as a formula: text typed by people
    (titles, comments) is written as text."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


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
    """Manager records the overall rating, during Manager Review, never on their own review.

    Hidden from the employee until Employee Final Review.
    """
    rating = flt(overall_rating)
    if rating < 0 or rating > MAX_RATING:
        frappe.throw(f"Rating must be between 0 and {int(MAX_RATING)}.")
    ap, ext = _manager_review_record(appraisal, "save_overall_rating", direct_only=True)
    ext.overall_rating = rating
    review_items.stamp_overall_rating(ext)
    ext.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": "Overall rating saved."}


# ══════════════════════════════════════════════════════════════════════════
# Calibration overview (FR-11)
# ══════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_calibration_overview(cycle):
    """Return all employees in a cycle with KPI summary and potential data. HR only.

    From each review's own copies (R8), for the reviews the caller may list.
    Keys a row's viewer may not see are left out, not blanked (SEC-26): before
    HR Review, for someone outside the caller's line, only status and counts;
    the caller's own row never has potential (PRIV-1). Four queries in all; it
    used to load every review record one by one.
    """
    from collections import Counter

    reviews = _hr_cycle_reviews(cycle)
    copies = _copies_of(reviews)
    actions = Counter(frappe.get_all(
        "Appraisal Action Item",
        filters={"parenttype": "Alvoraa Appraisal Extension", "parent": ["in", [a.name for a in reviews] or [""]]},
        pluck="parent",
    ))

    rows = []
    for a in reviews:
        kpis = [c for c in copies.get(a.name, []) if not c.removed and c.item_type == "KPI"]
        allowed = review_items.rating_fields_for(a.viewer, a.status)
        row = {
            "employee": a.employee,
            "employee_name": a.employee_name or a.employee,
            "appraisal": a.name,
            "review_status": a.status,
            "kpi_count": len(kpis),
            "avg_attainment": flt(sum(flt(c.attainment_pct) for c in kpis) / len(kpis), 1) if kpis else 0,
            "action_items_count": actions.get(a.name, 0),
        }
        if "manager_rating" in allowed:
            row["rated_count"] = sum(1 for c in kpis if flt(c.manager_rating) > 0)
        if "potential_rating" in allowed:
            rated = [flt(c.potential_rating) for c in kpis if flt(c.potential_rating) > 0]
            row["avg_potential"] = flt(sum(rated) / len(rated), 2) if rated else 0
            row["avg_potential_rating"] = flt(a.extension.get("avg_potential_rating"))
            row["potential_category"] = a.extension.get("potential_category") or ""
        if review_items.overall_rating_visible(a.viewer, a.status):
            row["overall_rating"] = flt(a.extension.get("overall_rating"))
        rows.append(row)

    rows.sort(key=lambda r: r["employee_name"] or "")
    return {"cycle": cycle, "rows": rows}


@frappe.whitelist()
def save_calibration_note(appraisal, calibration_notes, calibrated_rating=None):
    """HR saves calibration notes and an optional adjusted rating, during HR Review.

    Never on their own review (SEC-10), only for companies they look after
    (decision 16), and never on a completed review (VIS-10).
    """
    _require_hr()
    if not appraisal:
        frappe.throw("Appraisal is required.")
    owner = frappe.db.get_value("Appraisal", appraisal, "employee")
    if not owner:
        frappe.throw("Appraisal not found.")
    refuse_own_rating(owner, "Appraisal", appraisal, "save_calibration_note")
    _assert_hr_can_view(appraisal)
    ext = _extension(appraisal)
    if not ext or ext.review_status != "HR Review":
        frappe.throw("Calibration can be changed only while the review is in HR Review.")
    if calibrated_rating not in (None, ""):
        rating = flt(calibrated_rating)
        if rating < 0 or rating > MAX_RATING:
            frappe.throw(f"Rating must be between 0 and {int(MAX_RATING)}.")
    review_items.open_review(ext)
    if not hasattr(ext, "calibration_notes"):
        frappe.db.set_value("Alvoraa Appraisal Extension", ext.name,
                            "calibration_notes", calibration_notes)
    else:
        ext.calibration_notes = calibration_notes
    if calibrated_rating not in (None, ""):
        ext.overall_rating = flt(calibrated_rating)
        review_items.stamp_overall_rating(ext)
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
    if frappe.db.exists("Alvoraa Cycle Config", cycle):
        cfg_ps = frappe.db.get_value("Alvoraa Cycle Config", cycle, "page_settings") or "{}"
        try:
            ps = _json.loads(cfg_ps)
            mgf = ps.get("manager-feedback", {})
            overall_scale_name = mgf.get("overall_rating_scale", "") or ""
            potential_scale_name = mgf.get("potential_rating_scale", "") or ""
            show_potential = bool(mgf.get("show_potential"))
        except Exception:
            pass

    def _fetch_scale(name, ascending=True):
        if not name or not frappe.db.exists("Alvoraa Rating Scale", name):
            return None
        info = frappe.db.get_value(
            "Alvoraa Rating Scale", name, ["scale_name", "description"], as_dict=True
        ) or {}
        items = frappe.get_all(
            "Alvoraa Rating Scale Item",
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

    # ── The reviews this HR person may list (slice 010 group D, SEC-26) ──
    appraisals = _hr_cycle_reviews(cycle)

    rows = []
    stage_counts = {}
    filter_depts, filter_desig, filter_genders, filter_emp_types = set(), set(), set(), set()
    filter_managers = {}  # emp_id -> employee_name

    plotted = [a for a in appraisals if a.status in ("HR Review", "Completed")]
    people = {e.name: e for e in frappe.get_all(
        "Employee", filters={"name": ["in", [a.employee for a in plotted] or [""]]},
        fields=["name", "employee_name", "department", "designation", "gender", "employment_type", "reports_to"],
    )}
    manager_names = dict(frappe.get_all(
        "Employee", filters={"name": ["in", sorted({p.reports_to for p in people.values() if p.reports_to}) or [""]]},
        fields=["name", "employee_name"], as_list=True,
    ))

    for ap in appraisals:
        ap_name = ap.name
        emp_id  = ap.employee
        ext = ap.extension

        status = ap.status
        stage_counts[status] = stage_counts.get(status, 0) + 1

        # Plot reviews that are at HR Review or Completed stage
        if status not in ("HR Review", "Completed"):
            continue

        emp = people.get(emp_id) or {}

        reports_to      = emp.get("reports_to") or ""
        reports_to_name = ""
        if reports_to:
            reports_to_name = manager_names.get(reports_to) or reports_to
            filter_managers[reports_to] = reports_to_name

        dept     = emp.get("department")     or ""
        desig    = emp.get("designation")    or ""
        gender   = emp.get("gender")         or ""
        emp_type = emp.get("employment_type") or ""

        if dept:     filter_depts.add(dept)
        if desig:    filter_desig.add(desig)
        if gender:   filter_genders.add(gender)
        if emp_type: filter_emp_types.add(emp_type)

        row = {
            "employee":        emp_id,
            "employee_name":   emp.get("employee_name", emp_id),
            "appraisal":       ap_name,
            "overall_rating":  flt(ext.get("overall_rating")),
            "department":      dept,
            "designation":     desig,
            "gender":          gender,
            "employment_type": emp_type,
            "reports_to":      reports_to,
            "reports_to_name": reports_to_name,
        }
        # Never your own potential rating (PRIV-1).
        if ap.viewer != review_items.VIEWER_SUBJECT:
            row["potential_rating"] = flt(ext.get("potential_rating"))
        rows.append(row)

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
    """Send the review email. A failure never blocks the review step.

    The server never pushes script to a browser (slice 010, SEC-12): this used
    to publish a realtime event carrying a script after every email. A failure is logged with
    the traceback only - no recipient, subject or names.
    """
    try:
        frappe.sendmail(
            recipients=[to_user],
            subject=subject,
            message=message,
        )
    except Exception:
        # The plain traceback, passed in: log_error's own default captures the
        # local variables, which here are the recipient, subject and message.
        frappe.log_error(title="Review notification failed", message=frappe.get_traceback())


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
            "Alvoraa Appraisal Extension",
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
            # The overall rating is released to the employee at Employee Final
            # Review, never before (decision 3, PRIV-1).
            "overall_rating":  ext.get("overall_rating")
                               if ext.get("review_status") in _RATING_RELEASED else None,
            "return_reason":   ext.get("return_reason") or "",
        })

    # ── Reviews where I am an invited reviewer ────────────────────────────
    # Use a LIKE search on the JSON blob to cheaply narrow rows, then filter precisely in Python
    candidate_exts = frappe.get_all(
        "Alvoraa Appraisal Extension",
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
    _assert_hr_can_view(appraisal)
    if ap.employee != me and _review_status(appraisal) in _SELF_REVIEW_DRAFT:
        # Nobody but the subject sees a self-review before it is sent - not even
        # an HR person who is also in the subject's line (PRIV-2).
        refuse(
            "The self-review has not been sent yet. You can open it once it is sent.",
            "PRIV-2", "get_my_review", "Appraisal", appraisal,
        )

    cycle_name = ap.appraisal_cycle
    page_config, page_settings = [], {}
    if frappe.db.exists("Alvoraa Cycle Config", cycle_name):
        cfg = frappe.get_doc("Alvoraa Cycle Config", cycle_name)
        try: page_config = json.loads(cfg.page_config or "[]")
        except: pass
        try: page_settings = json.loads(cfg.page_settings or "{}")
        except: pass

    ext = _get_or_create_extension(appraisal) if ap.employee == me else _extension(appraisal)
    # The first open takes the review's own copies of its items (decision 4).
    if review_items.open_review(ext):
        frappe.db.commit()
    try: page_data = json.loads(ext.page_data or "{}")
    except: page_data = {}
    try: pages_completed = json.loads(ext.pages_completed or "[]")
    except: pages_completed = []

    # The review shows its own copies, never the live records (commit 4, VIS-3).
    viewer = review_items.VIEWER_SUBJECT if ap.employee == me else review_items.VIEWER_HR
    items = review_items.review_payload(ext, viewer, ap.employee, ap.employee_name)

    # Incomplete goals from other cycles, for the Future Objectives page. These
    # are next-period plans, not this review's items (VIS-15), so they stay live
    # records - except any this review already holds a copy of, which would tie
    # a copy to its live record (VIS-3).
    copied = review_items.copied_sources(ext)
    past_incomplete = frappe.get_all(
        "Individual Goal",
        filters={
            "employee": ap.employee,
            "appraisal_cycle": ["not in", [cycle_name, ""]],
            "docstatus": ["!=", 2],
            "status": ["not in", ["Completed", "Cancelled"]],
            "name": ["not in", sorted(copied) or [""]],
        },
        fields=["name", "goal_name", "is_extra_initiative",
                "target_value", "actual_progress", "progress_pct",
                "unit", "status", "start_date", "end_date", "appraisal_cycle"],
        ignore_permissions=True, order_by="creation desc",
        limit=50,
    )
    # One query for every label (it used to be one per goal).
    cycle_labels = dict(frappe.get_all(
        "Appraisal Cycle",
        filters={"name": ["in", sorted({g["appraisal_cycle"] for g in past_incomplete}) or [""]]},
        fields=["name", "cycle_name"], as_list=True,
    ))
    for g in past_incomplete:
        _serialise_dates(g, "start_date", "end_date")
        g["cycle_label"] = cycle_labels.get(g.get("appraisal_cycle")) or g.get("appraisal_cycle", "")

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
        "goals":                items["goals"],
        "standalone_kpis":      items["standalone_kpis"],
        "removed_items":        items["removed_items"],
        "numbers_frozen":       items["numbers_frozen"],
        "past_incomplete_goals": past_incomplete,
    }


def _selection_record(appraisal, endpoint):
    """The subject's own review, in Employee Review, with its copies taken (VIS-5).

    Only the subject chooses what their review covers, and only before sending
    it. Nobody adds items later (decision 7); a manager or HR removes an item
    with remove_review_item and a reason.
    """
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)
    if ap.employee != me:
        refuse("Only the employee chooses what their review covers.", "VIS-5", endpoint, "Appraisal", appraisal)
    if _review_status(appraisal) not in _SELF_REVIEW_DRAFT:
        refuse("Your review has been sent, so its items can no longer be changed.",
               "VIS-5", endpoint, "Appraisal", appraisal)
    ext = _get_or_create_extension(appraisal)
    if review_items.open_review(ext):
        frappe.db.commit()
    return ap, ext


@frappe.whitelist()
def get_available_for_review(appraisal):
    """The subject's live Objectives and standalone KPIs that meet the review period,
    for the add/remove dialog. `selected` means the review holds a copy of it."""
    ap, ext = _selection_record(appraisal, "get_available_for_review")
    # The period stamped on the review when it opened, so a later change to the
    # cycle's page settings cannot move it (SEC-21).
    period_from = ext.review_window_start
    period_to = ext.review_window_end
    if not (period_from and period_to):
        return {"goals": [], "kpis": [], "period_from": "", "period_to": ""}
    held = {r.source_name for r in ext.review_items if not r.removed}

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
        g["selected"] = g["name"] in held
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
        k["selected"] = k["name"] in held
        _serialise_dates(k, "period_start", "period_end")

    return {
        "goals":       goals,
        "kpis":        kpis,
        "period_from": str(period_from or ""),
        "period_to":   str(period_to   or ""),
    }


@frappe.whitelist()
def set_review_selection(appraisal, selected_goals_json=None, selected_kpis_json=None, acknowledge_removal=0):
    """The subject chooses what their review covers, before sending it (VIS-5).

    Ticking adds a copy; unticking takes the copy out under the review's
    removal setting (R12). Nothing here changes a live record's cycle any more.
    Removing needs acknowledge_removal=1: whatever was changed for that item
    inside the review is lost.
    """
    import json
    ap, ext = _selection_record(appraisal, "set_review_selection")

    def names(raw):
        if raw is None:
            return None
        try:
            value = json.loads(raw) if isinstance(raw, str) else raw
        except ValueError:
            value = None
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            frappe.throw("The selection could not be read. Reload the page and try again.")
        return set(value)

    goals, kpis = names(selected_goals_json), names(selected_kpis_json)
    live = [r for r in ext.review_items if not r.removed]
    live_goals = {r.source_name: r for r in live if r.source_doctype == "Individual Goal"}
    live_names = {r.name for r in live}
    # The dialog lists standalone KPIs only; a KPI under a live Objective comes with it.
    live_kpis = {r.source_name: r for r in live
                 if r.source_doctype == "KPI" and r.parent_item not in live_names}

    add_goals = sorted(goals - set(live_goals)) if goals is not None else []
    add_kpis = sorted(kpis - set(live_kpis)) if kpis is not None else []
    remove = ([live_goals[n] for n in sorted(set(live_goals) - goals)] if goals is not None else []) + \
             ([live_kpis[n] for n in sorted(set(live_kpis) - kpis)] if kpis is not None else [])
    if remove and not cint(acknowledge_removal):
        frappe.throw("Removing an item loses what was changed for it inside this review. "
                     "Confirm the removal to go on.")

    added = review_items.add_items(ext, ap.employee, add_goals, add_kpis)
    outcomes = []
    for row in remove:
        outcomes.append(review_items.remove_item(ext, row, "", ext.review_status or "Not Started"))
        review_items.audit(ext, f"Review item {row.name} removed by {frappe.session.user} "
                                f"({outcomes[-1]}) in {ext.review_status or 'Not Started'}.")
    if added or remove:
        review_items.save_review_record(ext)
        frappe.db.commit()
    return {"ok": True, "added": added, "removed": len(remove)}


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
    if page_key in ("past-objectives", "past_objectives"):
        # Ratings are keyed by this review's copies only; anything else refuses
        # the save before it is stored (SEC-1).
        review_items.open_review(ext)
        review_items.apply_self_review(ext, new_pd, "save_review_page", write=False)
    all_pd[page_key] = new_pd

    try: done = json.loads(ext.pages_completed or "[]")
    except: done = []
    if page_key not in done:
        done.append(page_key)

    ext.page_data       = json.dumps(all_pd)
    ext.pages_completed = json.dumps(done)
    if ext.review_status == "Not Started":
        ext.review_status = "Employee Review"
    review_items.save_review_record(ext)
    frappe.db.commit()
    return {"pages_completed": done}


@frappe.whitelist()
def submit_employee_review(appraisal, overall_comment=""):
    """Employee sends their self-review to the manager.

    Self-ratings and comments go onto this review's copies only; no Objective
    or KPI is written, and progress typed in the review is not applied anywhere
    (SEC-1, decision 4). One item that is not in this review, or one future
    objective that cannot be created, stops the whole submission (VIS-15).
    """
    import json
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)
    if ap.employee != me:
        frappe.throw("Only the employee can submit their own review.", frappe.PermissionError)

    ext = _get_or_create_extension(appraisal)
    if ext.review_status not in ("Not Started", "Employee Review"):
        frappe.throw("Review has already been submitted.")
    review_items.open_review(ext)

    try:
        all_pd = json.loads(ext.page_data or "{}")
    except Exception:
        all_pd = {}
    if not isinstance(all_pd, dict):
        all_pd = {}

    # ── Past Objectives: self-ratings and comments onto the copies ──
    past = all_pd.get("past-objectives") or all_pd.get("past_objectives") or {}
    review_items.apply_self_review(ext, past)

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

    # ── Future Objectives: new live Objectives for the next period ──
    # Live records, not copies, and tagged to no cycle (VIS-15, decision 19).
    future_obj = all_pd.get("future-objectives") or all_pd.get("future_goals") or {}
    new_goals = future_obj.get("new_goals") or []
    if not isinstance(new_goals, list):
        frappe.throw("The future objectives could not be read. Reload the page and try again.")
    for g in new_goals:
        if not isinstance(g, dict):
            frappe.throw("The future objectives could not be read. Reload the page and try again.")
        ig = frappe.new_doc("Individual Goal")
        ig.goal_name      = (g.get("name") or "").strip() or "New Goal"
        ig.description    = g.get("description", "")
        ig.target_value   = flt(g.get("target_value") or 0)
        ig.unit           = g.get("unit", "")
        ig.start_date     = g.get("start_date")
        ig.end_date       = g.get("end_date")
        ig.employee       = me
        ig.status         = "Active"
        ig.is_future_plan = 1
        ig.insert(ignore_permissions=True)

    ext.overall_comment = overall_comment
    ext.review_status   = "Manager Review"
    review_items.apply_stage(ext)
    review_items.save_review_record(ext)
    frappe.db.commit()
    return {"review_status": "Manager Review"}


# ══════════════════════════════════════════════════════════════════════════
# Changes to a review's items, made on its copies (slice 010 group D, commit 5)
# ══════════════════════════════════════════════════════════════════════════

# Who changes which items when. The subject before sending the self-review; the
# manager during Manager Review; HR during HR Review (removal only).
_ITEM_STAGES = {
    "subject": _SELF_REVIEW_DRAFT,
    "manager": ("Manager Review",),
    "hr": ("HR Review",),
}


def _review_actor(appraisal, endpoint, roles):
    """Who is changing this review's items, checked before anything is read or written.

    Returns (ap, ext, role). The subject, the manager line, or HR
    under the stage and company rule; anyone else is refused. The record is
    never created here (SEC-6). The stage must be the one this role acts in:
    nobody changes an item after their own step (SEC-1, SEC-24, VIS-10).
    """
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)
    if ap.employee == me:
        role = "subject"
    elif _is_line_manager(ap.employee, me):
        role = "manager"
    elif _is_hr():
        _assert_hr_can_view(appraisal)
        role = "hr"
    else:
        frappe.throw("Not permitted.", frappe.PermissionError)
    if role not in roles:
        refuse("You cannot make this change in this review.", "SEC-6", endpoint, "Appraisal", appraisal)
    ext = _extension(appraisal)
    status = (ext.review_status if ext else None) or "Not Started"
    if not ext or status not in _ITEM_STAGES[role]:
        refuse(
            "This review is not at a stage where you can change its items.",
            "SEC-24" if role != "subject" else "SEC-1", endpoint, "Appraisal", appraisal,
        )
    review_items.open_review(ext)
    return ap, ext, role


def _review_row(ext, row, endpoint):
    """This review's live copy, or a refusal. Live record names are never accepted (VIS-3)."""
    found = review_items.live_row(ext, row)
    if not found:
        refuse("That item is not in this review.", "VIS-3", endpoint, "Alvoraa Appraisal Extension", ext.name)
    return found


@frappe.whitelist()
def save_review_item_rating(appraisal, row, rating=None, comment=None,
                            potential_rating=None, potential_comment=None):
    """Rate one item of a review, on its copy (VIS-6, R13).

    The subject gives the self-rating before sending the self-review; the
    manager gives the manager rating and potential during Manager Review. The
    numbers it was given on are stamped (R7). No live record is written.
    """
    ap, ext, role = _review_actor(appraisal, "save_review_item_rating", ("subject", "manager"))
    item = _review_row(ext, row, "save_review_item_rating")
    if role == "subject":
        if potential_rating not in (None, "") or potential_comment not in (None, ""):
            refuse("You cannot rate your own potential.", "SEC-10", "save_review_item_rating", "Appraisal", appraisal)
        review_items.set_item_rating(item, "self", rating, comment)
    else:
        review_items.set_item_rating(item, "manager", rating, comment, potential_rating, potential_comment)
    review_items.save_review_record(ext)
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist()
def remove_review_item(appraisal, row, reason="", acknowledge=0):
    """Take one item out of a review (R12, SEC-24).

    The subject may do it before sending the self-review; the manager during
    Manager Review and HR during HR Review, always with a reason. The caller
    must confirm that whatever was changed for the item inside the review is
    lost. A rated copy is always kept, marked Removed (decision 9).
    """
    ap, ext, role = _review_actor(appraisal, "remove_review_item", ("subject", "manager", "hr"))
    item = _review_row(ext, row, "remove_review_item")
    reason = (reason or "").strip()
    if role != "subject" and not reason:
        frappe.throw("Say why this item is being removed. The employee will see the reason.")
    if not cint(acknowledge):
        frappe.throw("Removing an item loses what was changed for it inside this review. "
                     "Confirm the removal to go on.")
    rated = review_items.is_rated(item)
    outcome = review_items.remove_item(ext, item, reason, ext.review_status)
    review_items.audit(
        ext,
        f"Review item {item.name} removed by {frappe.session.user} in {ext.review_status}; "
        f"rated: {'yes' if rated else 'no'}; {outcome}. Reason: {reason or '(none given)'}",
    )
    review_items.save_review_record(ext)
    frappe.db.commit()
    return {"ok": True, "outcome": outcome}


@frappe.whitelist()
def delete_review_item(appraisal, row, acknowledge=0):
    """Delete an item that was created and added inside this review (R11).

    Only an item whose live record was created after the review opened, that
    nobody has rated and that has no progress or evidence of its own. Anything
    else can only be removed. Same people and stages as removal.
    """
    ap, ext, role = _review_actor(appraisal, "delete_review_item", ("subject", "manager", "hr"))
    item = _review_row(ext, row, "delete_review_item")
    if not cint(acknowledge):
        frappe.throw("Deleting removes the Objective or KPI itself. Confirm to go on.")
    doctype, source = item.source_doctype, item.source_name
    created = frappe.db.get_value(doctype, source, "creation") if doctype in ("KPI", "Individual Goal") else None
    fact_tables = {"KPI": ("KPI Progress Log",), "Individual Goal": ("Goal Evidence", "Goal Progress Update")}
    has_facts = created and any(
        frappe.db.exists(t, {"parenttype": doctype, "parent": source}) for t in fact_tables[doctype]
    )
    if (not cint(item.added_in_review) or not created or not ext.items_taken_on
            or frappe.utils.get_datetime(created) <= frappe.utils.get_datetime(ext.items_taken_on)):
        refuse("Only an item created during this review can be deleted. Remove it from the review instead.",
               "R11", "delete_review_item", "Alvoraa Appraisal Extension", ext.name)
    if has_facts or review_items.is_rated(item):
        refuse("This item has progress, evidence or a rating, so it can only be removed from the review.",
               "R11", "delete_review_item", "Alvoraa Appraisal Extension", ext.name)

    review_items.remove_item(ext, item, "", ext.review_status)
    review_items.audit(ext, f"Review item {item.name} deleted with its live record by {frappe.session.user} "
                            f"in {ext.review_status}.")
    review_items.save_review_record(ext)
    # No longer held by this review, so the live record may go (R11). One
    # transaction: if the delete is refused, the copy comes back too.
    frappe.delete_doc(doctype, source, ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist()
def save_review_item_definition(appraisal, row, title=None, target_value=None, weightage=None,
                                period_start=None, period_end=None):
    """Change an item's name, target, weight or period inside the review (R2, decision 6).

    The employee during Employee Review; the manager during Manager Review. The
    manager's submit counts as agreeing, and completion writes agreed changes
    back to the live record once (R15).
    """
    ap, ext, role = _review_actor(appraisal, "save_review_item_definition", ("subject", "manager"))
    item = _review_row(ext, row, "save_review_item_definition")
    changed = review_items.change_definition(ext, item, {
        "title": title, "target_value": target_value, "weightage": weightage,
        "period_start": period_start, "period_end": period_end,
    })
    if changed:
        review_items.audit(ext, f"Review item {item.name}: {', '.join(changed)} changed by "
                                f"{frappe.session.user} in {ext.review_status}.")
        review_items.save_review_record(ext)
        frappe.db.commit()
    return {"ok": True, "changed": changed}


def _rater_still_acts(rater_user, subject):
    """Is the person who gave a rating still in a position to answer for it?

    Active, with a working login, and still the subject's manager - or, for a
    rating given by HR, still HR for the subject's company.
    """
    if not rater_user:
        return False
    emp = frappe.db.get_value("Employee", {"user_id": rater_user}, ["name", "status"], as_dict=True)
    if not emp or emp.status != "Active" or not cint(frappe.db.get_value("User", rater_user, "enabled")):
        return False
    manager, depth = frappe.db.get_value("Employee", subject, "reports_to"), 0
    while manager and depth < 50:
        if manager == emp.name:
            return True
        manager, depth = frappe.db.get_value("Employee", manager, "reports_to"), depth + 1
    if not frappe.db.get_value("Employee", subject, "reports_to") and get_effective_manager(subject) == emp.name:
        return True
    if HR_ROLES.intersection(frappe.get_roles(rater_user)):
        company = frappe.db.get_value("Employee", subject, "company")
        return company in permitted_companies(rater_user)
    return False


@frappe.whitelist()
def answer_rating_flag(appraisal, target, keep=1, rating=None, reason=""):
    """Keep or change a rating whose numbers changed after it was given (R7, decision 12).

    target is "overall" or the row name of a copy with a manager rating. The
    person who gave the rating answers. If they have left or no longer manage
    the employee, HR answers, with a reason. The answerer is recorded. The
    employee is emailed if a released overall rating changes. Self-rating
    flags are information only (decision 13).
    """
    me = _require_employee()
    ap = frappe.get_doc("Appraisal", appraisal)
    refuse_own_rating(ap.employee, "Appraisal", appraisal, "answer_rating_flag")
    ext = _extension(appraisal)
    status = (ext.review_status if ext else None) or "Not Started"
    if not ext or status in _SELF_REVIEW_DRAFT or status == "Completed":
        refuse("This review has no rating question you can answer now.",
               "SEC-23", "answer_rating_flag", "Appraisal", appraisal)
    review_items.open_review(ext)

    if target == "overall":
        rater = ext.overall_rated_by
    else:
        rater = (_review_row(ext, target, "answer_rating_flag").manager_rated_by)

    user = frappe.session.user
    line_manager = _is_line_manager(ap.employee, me)
    # The rater answers. A rating stamped before raters were recorded is
    # answered by the manager line.
    as_rater = (rater == user and _rater_still_acts(user, ap.employee)) or (not rater and line_manager)
    if as_rater and not line_manager:
        _assert_hr_can_view(appraisal)   # a rating HR gave follows HR's stage rule
    if not as_rater:
        if (rater and _rater_still_acts(rater, ap.employee)) or not _is_hr():
            refuse("Only the person who gave this rating can answer for it.",
                   "SEC-23", "answer_rating_flag", "Appraisal", appraisal)
        # The rater has left or no longer manages this employee: HR answers,
        # during HR Review, for a company they look after, with a reason.
        _assert_hr_can_view(appraisal)
        if status != "HR Review":
            refuse("HR answers for a former rater during HR Review.",
                   "SEC-23", "answer_rating_flag", "Appraisal", appraisal)
        if not (reason or "").strip():
            frappe.throw("Say why HR is answering for this rating.")

    keep = cint(keep)
    new_rating = None
    if not keep:
        new_rating = _sent_rating(rating)
        if new_rating is None:
            frappe.throw(f"Choose a rating between 1 and {int(MAX_RATING)}.")
    changed = review_items.answer_flag(ext, target, keep, new_rating)
    review_items.audit(
        ext,
        f"Rating question on {target} answered by {user} ({'kept' if keep else 'changed'})"
        + ("" if as_rater else f" for {rater or 'a former rater'}. Reason: {(reason or '').strip()}"),
    )
    review_items.save_review_record(ext)
    frappe.db.commit()

    if changed and target == "overall" and status in _RATING_RELEASED:
        emp_user = _employee_user(ap.employee)
        if emp_user:
            _send_notification(
                emp_user,
                "Your review rating was updated",
                "<p>The overall rating in your performance review was updated. "
                "Log in to the portal to see it.</p>",
            )
    return {"ok": True, "rating_changed": int(changed)}


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
    # In order, before anything is read or created (SEC-6): never the subject
    # (SEC-10); the manager line or HR; HR's stage and company rule; and only
    # once the self-review has been sent (PRIV-2).
    refuse_own_rating(ap.employee, "Appraisal", appraisal, "get_manager_review")
    is_hr = _is_hr()
    viewer = review_items.VIEWER_MANAGER
    if not _is_line_manager(ap.employee, me):
        if not is_hr:
            frappe.throw("Only the employee's manager or HR can open this review.", frappe.PermissionError)
        _assert_hr_can_view(appraisal)
        viewer = review_items.VIEWER_HR
    if _review_status(appraisal) in _SELF_REVIEW_DRAFT:
        refuse(
            "The self-review has not been sent yet. You can open it once it is sent.",
            "PRIV-2", "get_manager_review", "Appraisal", appraisal,
        )

    ext = _extension(appraisal)
    if review_items.open_review(ext):
        frappe.db.commit()
    cycle_name = ap.appraisal_cycle

    try: page_data = json.loads(ext.page_data or "{}")
    except: page_data = {}
    try: pages_completed = json.loads(ext.pages_completed or "[]")
    except: pages_completed = []
    try: invited = json.loads(ext.invited_reviewers or "[]")
    except: invited = []

    page_config, page_settings = {}, {}
    if frappe.db.exists("Alvoraa Cycle Config", cycle_name):
        cfg = frappe.get_doc("Alvoraa Cycle Config", cycle_name)
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
        if frappe.db.exists("Alvoraa Rating Scale", sname):
            sinfo = frappe.db.get_value("Alvoraa Rating Scale", sname, ["scale_name", "description"], as_dict=True) or {}
            sitems = frappe.get_all("Alvoraa Rating Scale Item",
                filters={"parent": sname},
                fields=["label", "value", "color"],
                order_by="value desc")
            rating_scales[sname] = {"scale_name": sinfo.get("scale_name", sname), "items": sitems}

    # The review's own copies (commit 4, VIS-3). HR acting as HR also sees facts
    # that arrived after the numbers froze (R10); a manager who holds an HR role
    # is here as the manager.
    items = review_items.review_payload(ext, viewer, ap.employee, ap.employee_name)

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
        "goals":           items["goals"],
        "standalone_kpis": items["standalone_kpis"],
        "removed_items":   items["removed_items"],
        "numbers_frozen":  items["numbers_frozen"],
        "overall_rating_flag": items["overall_rating_flag"],
        "open_blocking_flags": items["open_blocking_flags"],
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
                        overall_rating=None, potential_rating=None):
    """Manager saves a draft of their review (does not change status).

    A rating changes only when one is sent. "Save draft" in the page sends 0 for
    ratings the manager did not touch on that visit, and that used to wipe the
    ratings already saved.
    """
    ap, ext = _manager_review_record(appraisal, "save_manager_review")
    ext.manager_feedback       = manager_feedback
    ext.manager_internal_notes = manager_internal_notes
    _set_manager_ratings(ext, overall_rating, potential_rating)
    ext.save(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist()
def invite_reviewer(appraisal, reviewer_employee, allowed_pages=None):
    """Manager invites an additional reviewer."""
    import json
    ap, ext = _manager_review_record(
        appraisal, "invite_reviewer",
        stage_message="Reviewers can only be invited during Manager Review stage.",
    )
    if reviewer_employee == ap.employee:
        frappe.throw("Cannot invite the subject employee as a reviewer.")
    if not isinstance(reviewer_employee, str):
        frappe.throw("Choose one employee to invite.")
    _check_invitees(ap, [reviewer_employee], "invite_reviewer")
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
    ap, ext = _manager_review_record(
        appraisal, "invite_reviewers_batch",
        stage_message="Reviewers can only be invited during Manager Review stage.",
    )
    if isinstance(reviewers, str):
        try: reviewers = json.loads(reviewers)
        except: frappe.throw("Invalid reviewers format.")
    if not isinstance(reviewers, list) or not all(isinstance(r, dict) for r in reviewers):
        frappe.throw("Invalid reviewers format.")
    _check_invitees(
        ap,
        [r.get("employee") for r in reviewers
         if isinstance(r.get("employee"), str) and r.get("employee") != ap.employee],
        "invite_reviewers_batch",
    )
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
    # An invitation lives on the record, so no record means no invitation (SEC-6).
    ext = _extension(appraisal)
    if not ext:
        frappe.throw("You are not an invited reviewer for this appraisal.", frappe.PermissionError)
    try: invited = json.loads(ext.invited_reviewers or "[]")
    except: invited = []
    entry = next((r for r in invited if r.get("employee") == me_emp), None)
    if not entry:
        frappe.throw("You are not an invited reviewer for this appraisal.", frappe.PermissionError)
    # An invitation is for the manager review only: not before the self-review
    # is sent, and not after the manager has finished (SEC-7, decision 17).
    if (ext.review_status or "") != "Manager Review":
        refuse(
            "This review is not open for reviewer feedback now.",
            "SEC-7", "get_reviewer_view", "Appraisal", appraisal,
        )
    allowed_pages = entry.get("allowed_pages", [])
    if not isinstance(allowed_pages, list):
        allowed_pages = []
    allowed_pages = [p for p in allowed_pages if isinstance(p, str)]
    try: page_data = json.loads(ext.page_data or "{}")
    except: page_data = {}
    # Only the pages this reviewer was invited to read; none means nothing.
    page_data = {k: v for k, v in (page_data if isinstance(page_data, dict) else {}).items()
                 if k in allowed_pages}
    ap = frappe.get_doc("Appraisal", appraisal)
    goals, standalone = [], []
    if "past-objectives" in allowed_pages:
        if review_items.open_review(ext):
            frappe.db.commit()
        items = review_items.review_payload(ext, review_items.VIEWER_REVIEWER, ap.employee, ap.employee_name)
        goals, standalone = items["goals"], items["standalone_kpis"]
    page_comments = entry.get("page_comments", {})
    if isinstance(page_comments, str):
        try: page_comments = json.loads(page_comments)
        except: page_comments = {}
    # Resolve page labels from cycle config
    page_label_map = {}
    if ap.appraisal_cycle:
        cc_val = frappe.db.get_value("Alvoraa Cycle Config", {"appraisal_cycle": ap.appraisal_cycle}, "page_config")
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
        "standalone_kpis":  standalone,
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
    ext = _extension(appraisal)
    try: invited = json.loads((ext.invited_reviewers if ext else None) or "[]")
    except: invited = []
    if not any(r.get("employee") == me_emp for r in invited):
        frappe.throw("You are not an invited reviewer for this appraisal.", frappe.PermissionError)
    if ext.review_status != "Manager Review":
        frappe.throw("Review is not in Manager Review stage.")
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
                          overall_rating=None, potential_rating=None, reviewer_comments_visible=0):
    """Manager finalises their review → Employee Final Review stage."""
    ap, ext = _manager_review_record(appraisal, "submit_manager_review")
    if not manager_feedback:
        frappe.throw("Manager feedback is required before submitting.")
    # Only require overall_rating when the cycle was configured with a rating scale
    _overall_required = False
    if frappe.db.exists("Alvoraa Cycle Config", ap.appraisal_cycle):
        try:
            import json as _json
            _cfg = frappe.get_doc("Alvoraa Cycle Config", ap.appraisal_cycle)
            _ps = _json.loads(_cfg.page_settings or "{}")
            _overall_required = bool((_ps.get("manager-feedback") or {}).get("overall_rating_scale"))
        except Exception:
            pass
    _set_manager_ratings(ext, overall_rating, potential_rating)
    if _overall_required and not flt(ext.overall_rating):
        frappe.throw("Overall rating is required before submitting.")
    ext.manager_feedback            = manager_feedback
    ext.manager_internal_notes      = manager_internal_notes
    ext.reviewer_comments_visible   = int(reviewer_comments_visible or 0)
    ext.review_status               = "Employee Final Review"
    review_items.apply_stage(ext)
    review_items.save_review_record(ext)
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
    ext = _extension(appraisal)
    if not ext or ext.review_status != "Employee Final Review":
        frappe.throw("Review is not in Employee Final Review stage.")
    ext.review_status = "HR Review"
    review_items.apply_stage(ext)
    review_items.save_review_record(ext)
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
    ext = _extension(appraisal)
    if not ext or ext.review_status not in ("Employee Final Review",):
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
    if cycle_name and frappe.db.exists("Alvoraa Cycle Config", cycle_name):
        cfg = frappe.get_doc("Alvoraa Cycle Config", cycle_name)
        try: page_settings = json.loads(cfg.page_settings or "{}")
        except: pass

    mgf_ps = page_settings.get("manager-feedback", {})
    _scale_names = [s for s in [
        mgf_ps.get("overall_rating_scale"),
        mgf_ps.get("potential_rating_scale"),
    ] if s]
    rating_scales = {}
    for sname in _scale_names:
        if frappe.db.exists("Alvoraa Rating Scale", sname):
            sinfo = frappe.db.get_value("Alvoraa Rating Scale", sname, ["scale_name", "description"], as_dict=True) or {}
            sitems = frappe.get_all("Alvoraa Rating Scale Item",
                filters={"parent": sname},
                fields=["label", "value", "color"],
                order_by="value desc")
            rating_scales[sname] = {"scale_name": sinfo.get("scale_name", sname), "items": sitems}

    return {
        "appraisal":       appraisal,
        "review_status":   ext.review_status,
        "manager_feedback": ext.manager_feedback or "",
        "overall_rating":  ext.overall_rating or 0,
        # No potential rating or category: the employee never receives them (PRIV-1).
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


@frappe.whitelist()
def save_calibration_signoff(cycle, summary):
    """Store a calibration sign-off summary against the cycle config (HR only)."""
    import json as _json
    _require_hr()
    if not cycle or not summary:
        frappe.throw("cycle and summary are required")
    if not frappe.db.exists("Alvoraa Cycle Config", cycle):
        frappe.throw("Cycle config not found for: " + cycle)
    raw = frappe.db.get_value("Alvoraa Cycle Config", cycle, "page_settings") or "{}"
    try:
        settings = _json.loads(raw)
    except Exception:
        settings = {}
    settings["calibration_signoff"] = {
        "summary": summary,
        "signed_by": frappe.session.user,
        "signed_at": frappe.utils.now(),
    }
    frappe.db.set_value("Alvoraa Cycle Config", cycle, "page_settings", _json.dumps(settings))
    frappe.db.commit()
    return settings["calibration_signoff"]


@frappe.whitelist()
def get_calibration_signoff(cycle):
    """Retrieve the calibration sign-off for a cycle, or None if not signed off.

    HR only (slice 010 group D, SEC-30): the summary is HR's calibration text,
    and any logged-in employee could read it.
    """
    import json as _json
    _require_hr()
    if not cycle:
        return None
    if not frappe.db.exists("Alvoraa Cycle Config", cycle):
        return None
    raw = frappe.db.get_value("Alvoraa Cycle Config", cycle, "page_settings") or "{}"
    try:
        settings = _json.loads(raw)
    except Exception:
        return None
    return settings.get("calibration_signoff")


# ── Review settings on the portal's Org Settings screen (slice 010 group D, decision 23) ──
#
# The three settings live on HR Settings (SEC-28): typed, validated by
# review_items.validate_hr_settings, and every change keeps a Version row. These
# two calls only show and save those same fields. Not hr_api.set_org_setting,
# which writes Global Defaults with no history and allows one listed key.


def _review_settings_payload():
    settings = review_items.review_settings()
    return {
        "freeze_point": settings["freeze_point"],
        "lock_release_days": settings["lock_release_days"],
        "removal_mode": settings["removal_mode"],
        "freeze_points": list(review_items.FREEZE_POINTS),
        "removal_modes": list(review_items.REMOVAL_MODES),
        "can_edit": "HR Manager" in frappe.get_roles(),
    }


@frappe.whitelist()
def get_review_settings():
    """The three review settings, for HR. Anyone else is refused."""
    if not _is_hr():
        refuse(frappe._("Only HR can see the review settings."), "SEC-28", "performance_api.get_review_settings")
    return _review_settings_payload()


@frappe.whitelist(methods=["POST"])
def save_review_settings(freeze_point, lock_release_days, removal_mode):
    """Save the three review settings. HR Manager only, as in the desk (SEC-28).

    Values are checked here and again by HR Settings' own validation; the save
    goes through the document with the caller's own permission, so HR Settings'
    change history records who changed what.
    """
    if "HR Manager" not in frappe.get_roles():
        refuse(frappe._("Only an HR Manager can change the review settings."), "SEC-28",
               "performance_api.save_review_settings")
    if freeze_point not in review_items.FREEZE_POINTS:
        frappe.throw(frappe._("Choose when review numbers freeze from the list."))
    if removal_mode not in review_items.REMOVAL_MODES:
        frappe.throw(frappe._("Choose what happens to a removed review item from the list."))
    days = frappe.utils.cstr(lock_release_days).strip()
    if not days.isdigit() or int(days) > 3650:
        frappe.throw(frappe._("Enter the number of days as a whole number from 0 to 3650. Use 0 for never."))

    doc = frappe.get_doc("HR Settings")
    doc.set(review_items.SETTING_FIELDS["freeze_point"], freeze_point)
    doc.set(review_items.SETTING_FIELDS["lock_release_days"], int(days))
    doc.set(review_items.SETTING_FIELDS["removal_mode"], removal_mode)
    doc.save()
    frappe.db.commit()
    import json

    frappe.logger("security").info(json.dumps({
        "event": "review_settings_saved", "at": str(frappe.utils.now_datetime()), "user": frappe.session.user,
        "endpoint": "performance_api.save_review_settings", "doctype": "HR Settings"}))
    return _review_settings_payload()
