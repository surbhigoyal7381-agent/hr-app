import frappe

from alvoraa_portal.subscription import requires_feature
import calendar as _calendar
from frappe.utils import today, get_first_day, get_last_day, getdate, add_days, now
from alvoraa_goals.permissions import get_effective_manager

# ── Cache invalidation helpers (called by doc_events hooks in hooks.py) ──────

def invalidate_portal_context_cache(doc, method=None):
    """Clear portal context cache when an Employee or Has Role record changes."""
    try:
        if doc.doctype == "Employee":
            if doc.user_id:
                frappe.cache().delete_value(f"portal_ctx_{doc.user_id}")
            # Clear the current manager's cache (their is_manager flag may have changed)
            if doc.reports_to:
                mgr_user = frappe.db.get_value("Employee", doc.reports_to, "user_id")
                if mgr_user:
                    frappe.cache().delete_value(f"portal_ctx_{mgr_user}")
            # If reports_to changed, also clear the previous manager's cache
            prev = getattr(doc, "_doc_before_save", None)
            if prev:
                old_mgr = getattr(prev, "reports_to", None)
                if old_mgr and old_mgr != doc.reports_to:
                    old_mgr_user = frappe.db.get_value("Employee", old_mgr, "user_id")
                    if old_mgr_user:
                        frappe.cache().delete_value(f"portal_ctx_{old_mgr_user}")
        elif doc.doctype == "Has Role" and getattr(doc, "parenttype", None) == "User":
            frappe.cache().delete_value(f"portal_ctx_{doc.parent}")
    except Exception:
        pass


def invalidate_features_cache(doc, method=None):
    """Clear global features cache when Shift Type or Leave Type configuration changes."""
    try:
        frappe.cache().delete_value("portal_features_global")
    except Exception:
        pass


LEAVE_COLORS = {
    "Casual Leave":       "#3b82f6",
    "Sick Leave":         "#ef4444",
    "Privilege Leave":    "#8b5cf6",
    "Compensatory Off":   "#f59e0b",
    "Leave Without Pay":  "#6b7280",
}

def _leave_year_start(date_=None, company=None):
    """Start of the year that leave is counted against.

    Leave entitlement follows the company's FINANCIAL year, not the calendar
    year. Every caller here used frappe.utils.get_year_start(), which returns
    1 January - so on a company running April-March, "leave taken this year"
    silently counted from the wrong date and was out by three months.

    ERPNext already owns this: Fiscal Year, resolved per company and date.

    Falls back to the calendar year when no Fiscal Year is defined. That is not
    theoretical - dev.alvoraa.co and demo.alvoraa.co have none, and without the
    fallback get_fiscal_year() raises and every leave screen breaks.
    """
    date_ = date_ or today()
    try:
        from erpnext.accounts.utils import get_fiscal_year

        company = company or frappe.defaults.get_user_default("Company")
        fy = get_fiscal_year(date_, company=company, as_dict=True)
        if fy and fy.get("year_start_date"):
            return fy["year_start_date"]
    except Exception:
        # No Fiscal Year for this date/company, or erpnext unavailable.
        pass
    return frappe.utils.get_year_start(date_)


def _get_employee(user=None):
    user = user or frappe.session.user
    return frappe.db.get_value(
        "Employee", {"user_id": user, "status": "Active"},
        ["name", "employee_name", "designation", "department", "branch",
         "company", "reports_to", "gender", "date_of_joining",
         "date_of_birth", "image", "cell_number"],
        as_dict=True,
    )


@frappe.whitelist(allow_guest=True)
def get_portal_context():
    user = frappe.session.user
    if user == "Guest":
        return {"type": "guest"}

    cache_key = f"portal_ctx_{user}"
    try:
        cached = frappe.cache().get_value(cache_key)
        if cached:
            return cached
    except Exception:
        pass

    emp = _get_employee(user)
    roles = frappe.get_roles(user)

    is_system_manager = bool({"System Manager", "Administrator"} & set(roles))
    is_hr = is_system_manager or bool({"HR Manager", "HR User"} & set(roles))
    is_manager = False
    manager_name = None

    if emp:
        is_manager = frappe.db.count("Employee", {"reports_to": emp.name, "status": "Active"}) > 0
        if not is_manager and is_hr:
            is_manager = frappe.db.count(
                "Employee", {"reports_to": ("is", "not set"), "status": "Active",
                             "name": ["!=", emp.name]}
            ) > 0
        eff_mgr = get_effective_manager(emp.name)
        if eff_mgr and eff_mgr != emp.name:
            manager_name = frappe.db.get_value("Employee", eff_mgr, "employee_name")

    result = {
        "type": "hr" if is_hr else ("manager" if is_manager else "employee"),
        "user": user,
        "employee": emp,
        "is_hr": is_hr,
        "is_manager": is_manager,
        "is_system_manager": is_system_manager,
        # Is THIS site the control plane, or a tenant provisioned from one?
        #
        # The portal's "Tenant Admin" link used to appear for any System Manager,
        # which on a tenant means its own administrator. They were shown a link
        # to /alvoraa-admin, a page that then refused them - a door advertised to
        # people who may not open it, pointing at tooling that is not theirs.
        #
        # Read from site config, so it costs nothing and cannot drift from the
        # check /alvoraa-admin itself performs.
        "is_control_plane": bool(frappe.conf.get("alvoraa_control_plane")),
        "manager_name": manager_name,
        "roles": roles,
    }
    try:
        # 1-hour safety-net TTL only; doc_events hooks clear this immediately on change
        frappe.cache().set_value(cache_key, result, expires_in_sec=3600)
    except Exception:
        pass
    return result


@frappe.whitelist()
def get_employee_dashboard():
    user = frappe.session.user
    emp = _get_employee(user)
    if not emp:
        return {"no_employee": True}

    td       = today()
    yr_start = _leave_year_start(td, emp.company)
    mo_start = get_first_day(td)

    # ── Leave balances ────────────────────────────────────────────────────
    allocations = frappe.get_all(
        "Leave Allocation",
        filters={
            "employee": emp.name, "docstatus": 1,
            "from_date": ["<=", td], "to_date": [">=", td],
        },
        fields=["leave_type", "total_leaves_allocated"],
        ignore_permissions=True,
    )

    taken_map = {}
    if allocations:
        apps = frappe.get_all(
            "Leave Application",
            filters={"employee": emp.name, "docstatus": 1, "status": "Approved",
                     "from_date": [">=", yr_start]},
            fields=["leave_type", "total_leave_days"],
            ignore_permissions=True,
        )
        for a in apps:
            taken_map[a.leave_type] = taken_map.get(a.leave_type, 0) + a.total_leave_days

    leave_balances = []
    for al in allocations:
        lt    = al.leave_type
        total = float(al.total_leaves_allocated)
        taken = float(taken_map.get(lt, 0))
        leave_balances.append({
            "leave_type": lt,
            "total":      total,
            "taken":      taken,
            "balance":    max(total - taken, 0),
            "color":      LEAVE_COLORS.get(lt, "#64748b"),
            "pct_used":   round(taken / total * 100) if total else 0,
        })

    # ── Attendance this month ─────────────────────────────────────────────
    att_rows = frappe.get_all(
        "Attendance",
        filters={"employee": emp.name, "attendance_date": [">=", mo_start], "docstatus": 1},
        fields=["status"],
        ignore_permissions=True,
    )
    att = {}
    for r in att_rows:
        att[r.status] = att.get(r.status, 0) + 1

    # ── Recent leave applications ─────────────────────────────────────────
    recent_leaves = frappe.get_all(
        "Leave Application",
        filters={"employee": emp.name},
        fields=["name", "leave_type", "from_date", "to_date", "status", "total_leave_days", "description"],
        order_by="creation desc",
        limit=6,
        ignore_permissions=True,
    )

    # ── Pending approvals (as leave approver) ────────────────────────────
    pending = frappe.get_all(
        "Leave Application",
        filters={"leave_approver": user, "status": "Open", "docstatus": 0},
        fields=["name", "employee", "employee_name", "leave_type",
                "from_date", "to_date", "total_leave_days", "description"],
        order_by="creation asc",
        ignore_permissions=True,
    )

    # ── Upcoming holidays (full year, no Sundays, deduped across lists) ──
    _mo_start  = get_first_day(td)
    _year_end  = "{0}-12-31".format(getdate(td).year)
    _raw_hols  = frappe.get_all(
        "Holiday",
        filters={
            "holiday_date": ["between", [_mo_start, _year_end]],
            "weekly_off":   0,
        },
        fields=["holiday_date", "description"],
        order_by="holiday_date asc",
        limit=200,
        ignore_permissions=True,
    )
    _seen = set()
    holidays = []
    for _h in _raw_hols:
        if _h.holiday_date not in _seen:
            _seen.add(_h.holiday_date)
            holidays.append(_h)

    return {
        "employee":        emp,
        "leave_balances":  leave_balances,
        "attendance":      att,
        "recent_leaves":   recent_leaves,
        "pending_approvals": pending,
        "holidays":        holidays,
        "month_days":      len(att_rows),
    }


@frappe.whitelist()
def get_manager_dashboard():
    user = frappe.session.user
    emp  = _get_employee(user)
    if not emp:
        return {"no_employee": True}

    # Direct reports
    team = frappe.get_all(
        "Employee",
        filters={"reports_to": emp.name, "status": "Active"},
        fields=["name", "employee_name", "designation", "department", "user_id", "image"],
        ignore_permissions=True,
    )
    # HR managers also own employees who have no reporting manager set
    roles = frappe.get_roles()
    if {"HR Manager", "HR User"} & set(roles):
        orphans = frappe.get_all(
            "Employee",
            filters={"reports_to": ("is", "not set"), "status": "Active", "name": ["!=", emp.name]},
            fields=["name", "employee_name", "designation", "department", "user_id", "image"],
            ignore_permissions=True,
        )
        existing = {t.name for t in team}
        team.extend(o for o in orphans if o.name not in existing)

    # Indirect reports (L2 only) — single query instead of one per manager
    l2 = []
    if team:
        team_names = [t.name for t in team]
        mgr_name_map = {t.name: t.employee_name for t in team}
        all_l2 = frappe.get_all(
            "Employee",
            filters={"reports_to": ["in", team_names], "status": "Active"},
            fields=["name", "employee_name", "designation", "department", "reports_to"],
            ignore_permissions=True,
        )
        for s in all_l2:
            s["reports_to_name"] = mgr_name_map.get(s.reports_to, s.reports_to)
        l2 = all_l2

    # Team names for queries
    team_ids = [t.name for t in team] + [s.name for s in l2]

    # Today's attendance for direct reports
    td = today()
    today_att = {}
    if team_ids:
        rows = frappe.get_all(
            "Attendance",
            filters={"employee": ["in", team_ids], "attendance_date": td, "docstatus": 1},
            fields=["employee", "employee_name", "status"],
            ignore_permissions=True,
        )
        for r in rows:
            today_att[r.employee] = r.status

    # Who is on leave today
    on_leave_today = []
    if team_ids:
        # .format() only inserts "%s" placeholders — no user data in the format string; safe.
        on_leave_today = frappe.db.sql("""
            SELECT employee, employee_name, leave_type
            FROM `tabLeave Application`
            WHERE employee IN ({placeholders})
              AND docstatus = 1 AND status = 'Approved'
              AND from_date <= %s AND to_date >= %s
        """.format(placeholders=",".join(["%s"] * len(team_ids))),
            tuple(team_ids) + (td, td), as_dict=True,
        )

    # Pending leave approvals (from all in org for this approver)
    pending = frappe.get_all(
        "Leave Application",
        filters={"leave_approver": user, "status": "Open", "docstatus": 0},
        fields=["name", "employee", "employee_name", "department", "leave_type",
                "from_date", "to_date", "total_leave_days", "description"],
        order_by="creation asc",
        ignore_permissions=True,
    )

    # Approved leaves for the month (team)
    mo_start = get_first_day(td)
    month_leaves = []
    if team_ids:
        month_leaves = frappe.get_all(
            "Leave Application",
            filters={"employee": ["in", team_ids], "docstatus": 1,
                     "status": "Approved", "from_date": [">=", mo_start]},
            fields=["employee_name", "leave_type", "from_date", "to_date", "total_leave_days"],
            order_by="from_date asc",
            ignore_permissions=True,
        )

    return {
        "manager":         emp,
        "team":            team,
        "l2_reports":      l2,
        "today_att":       today_att,
        "on_leave_today":  on_leave_today,
        "pending_approvals": pending,
        "month_leaves":    month_leaves,
        "team_size":       len(team),
        "l2_size":         len(l2),
    }


@frappe.whitelist()
@requires_feature("analytics")
def get_hr_analytics():
    # Role AND plan. The role says this person may see analytics; the feature
    # says this tenant bought them. Hiding the nav item stopped neither a URL
    # nor a fetch() from reaching here.
    roles = frappe.get_roles()
    if not ({"HR Manager", "HR User", "Administrator"} & set(roles)):
        frappe.throw("Access denied", frappe.PermissionError)

    td       = today()
    mo_start = get_first_day(td)
    mo_end   = get_last_day(td)
    yr_start = _leave_year_start(td)

    # ── Headcount ─────────────────────────────────────────────────────────
    total_active = frappe.db.count("Employee", {"status": "Active"})
    total_all    = frappe.db.count("Employee")

    # New joiners this month
    new_joiners = frappe.db.count("Employee",
        {"date_of_joining": ["between", [mo_start, mo_end]]})

    # ── Department distribution ───────────────────────────────────────────
    dept_dist = frappe.db.sql("""
        SELECT department, COUNT(*) AS count
        FROM `tabEmployee` WHERE status = 'Active' AND department IS NOT NULL
        GROUP BY department ORDER BY count DESC
    """, as_dict=True)

    # ── Gender ratio ─────────────────────────────────────────────────────
    gender_dist = frappe.db.sql("""
        SELECT COALESCE(NULLIF(gender,''),'Not Specified') AS gender, COUNT(*) AS count
        FROM `tabEmployee` WHERE status = 'Active'
        GROUP BY gender
    """, as_dict=True)

    # ── Location / Branch ────────────────────────────────────────────────
    loc_dist = frappe.db.sql("""
        SELECT COALESCE(NULLIF(branch,''),'HQ') AS location, COUNT(*) AS count
        FROM `tabEmployee` WHERE status = 'Active'
        GROUP BY location ORDER BY count DESC
    """, as_dict=True)

    # ── Monthly joiners (last 6 months) ──────────────────────────────────
    six_months_ago = add_days(td, -180)
    joiners_trend = frappe.db.sql("""
        SELECT DATE_FORMAT(date_of_joining,'%%b %%Y') AS month,
               DATE_FORMAT(date_of_joining,'%%Y-%%m') AS sort_key,
               COUNT(*) AS count
        FROM `tabEmployee`
        WHERE date_of_joining >= %s
        GROUP BY month, sort_key ORDER BY sort_key
    """, six_months_ago, as_dict=True)

    # ── Attendance KPIs this month ────────────────────────────────────────
    att_summary = frappe.db.sql("""
        SELECT status, COUNT(*) AS count
        FROM `tabAttendance`
        WHERE attendance_date >= %s AND docstatus = 1
        GROUP BY status
    """, mo_start, as_dict=True)
    att_map = {r.status: r.count for r in att_summary}
    present  = att_map.get("Present", 0) + att_map.get("Half Day", 0) * 0.5
    absent   = att_map.get("Absent", 0)
    att_rate = round(present / max(present + absent, 1) * 100, 1)

    # ── Leave utilization (current year) ─────────────────────────────────
    total_alloc = frappe.db.sql(
        "SELECT COALESCE(SUM(total_leaves_allocated),0) FROM `tabLeave Allocation` WHERE docstatus=1"
    )[0][0] or 0
    total_taken = frappe.db.sql(
        "SELECT COALESCE(SUM(total_leave_days),0) FROM `tabLeave Application` WHERE docstatus=1 AND status='Approved' AND from_date>=%s",
        yr_start,
    )[0][0] or 0
    leave_util = round(float(total_taken) / max(float(total_alloc), 1) * 100, 1)

    # ── Pending approvals ─────────────────────────────────────────────────
    pending_count = frappe.db.count("Leave Application", {"status": "Open", "docstatus": 0})

    # ── Confirmations due this month ─────────────────────────────────────
    confirmations = frappe.get_all(
        "Employee",
        filters={
            "scheduled_confirmation_date": ["between", [mo_start, mo_end]],
            "status": "Active",
        },
        fields=["name", "employee_name", "designation", "department", "date_of_joining", "scheduled_confirmation_date"],
        ignore_permissions=True,
    )

    # ── Department-wise leave utilization ────────────────────────────────
    dept_leave = frappe.db.sql("""
        SELECT e.department, COALESCE(SUM(la.total_leave_days),0) AS taken
        FROM `tabEmployee` e
        LEFT JOIN `tabLeave Application` la
            ON la.employee = e.name AND la.docstatus=1 AND la.status='Approved' AND la.from_date>=%s
        WHERE e.status='Active' AND e.department IS NOT NULL
        GROUP BY e.department ORDER BY taken DESC
    """, yr_start, as_dict=True)

    # ── Designation distribution ─────────────────────────────────────────
    desig_dist = frappe.db.sql("""
        SELECT COALESCE(NULLIF(designation,''),'Not Set') AS designation, COUNT(*) AS count
        FROM `tabEmployee` WHERE status='Active'
        GROUP BY designation ORDER BY count DESC LIMIT 10
    """, as_dict=True)

    # ── Recent employee list (for lifecycle tab) ──────────────────────────
    recent_employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name", "designation", "department", "date_of_joining", "gender"],
        order_by="date_of_joining desc",
        limit=10,
        ignore_permissions=True,
    )

    return {
        "headcount": {
            "active":      total_active,
            "total":       total_all,
            "new_joiners": new_joiners,
        },
        "dept_distribution":    dept_dist,
        "gender_distribution":  gender_dist,
        "location_distribution": loc_dist,
        "joiners_trend":        joiners_trend,
        "desig_distribution":   desig_dist,
        "kpis": {
            "attendance_rate":      att_rate,
            "leave_utilization":    leave_util,
            "pending_approvals":    pending_count,
            "total_leave_taken":    float(total_taken),
            "total_leave_allocated": float(total_alloc),
        },
        "org_health": {
            "attendance_rate":    att_rate,
            "pending_approvals":  pending_count,
            "confirmations_due": len(confirmations),
            "present_this_month": int(present),
            "absent_this_month":  int(absent),
        },
        "confirmations_due": confirmations,
        "dept_leave":         dept_leave,
        "recent_employees":   recent_employees,
    }


def _can_action_leave(name):
    """Can the CURRENT user actually approve or reject this application?

    Asked of the document, not of the user's roles, because that is what Frappe
    will check when we submit. Roles alone say too little: Frappe HR creates a
    User Permission tying each user to their own Employee record, applied to all
    doctypes, so an HR Manager who is also an employee can be blocked from every
    document but their own - which is exactly what happened, while the portal
    cheerfully drew Approve and Reject buttons.

    A button that cannot work is worse than no button: it turns a configuration
    problem into what looks like a broken product.
    """
    try:
        doc = frappe.get_doc("Leave Application", name)
        return bool(frappe.has_permission("Leave Application", "submit", doc=doc))
    except Exception:
        return False


def _mark_actionable(rows):
    """Annotate each pending row with whether this user can action it."""
    for r in rows:
        r["can_action"] = _can_action_leave(r.get("name"))
    return rows


@frappe.whitelist()
def action_leave(leave_id, action):
    """Approve or reject a leave application."""
    user = frappe.session.user
    doc  = frappe.get_doc("Leave Application", leave_id)

    if doc.leave_approver != user:
        roles = frappe.get_roles(user)
        if not ({"HR Manager", "HR User", "Administrator"} & set(roles)):
            frappe.throw("Not authorised to action this leave application.")

    # Having the role is not the same as being allowed to submit THIS document,
    # and finding that out from a bare PermissionError helps nobody. Say what is
    # wrong and who can fix it.
    if not frappe.has_permission("Leave Application", "submit", doc=doc):
        approver = doc.leave_approver or "nobody"
        frappe.throw(
            _("You cannot approve this request. Frappe HR restricts you to your "
              "own employee records, and this one belongs to {0}. The assigned "
              "approver is {1}. HR can fix this by naming an approver on the "
              "employee, or by turning off 'Apply User Permissions' for the HR "
              "Manager role on Leave Application.").format(
                  doc.employee_name or doc.employee, approver),
            frappe.PermissionError,
        )

    if action == "approve":
        doc.status = "Approved"
        doc.db_set("status", "Approved", update_modified=False)
        doc.submit()
    elif action == "reject":
        doc.status = "Rejected"
        doc.db_set("status", "Rejected", update_modified=False)
        doc.submit()
    else:
        frappe.throw(f"Unknown action: {action}")

    frappe.db.commit()
    return {"status": doc.status, "name": doc.name}


@frappe.whitelist()
def get_portal_activity(days=7):
    """Return recent portal activity for the logged-in user, sorted latest-first."""
    user = frappe.session.user
    emp  = _get_employee(user)
    if not emp:
        return {"activities": []}

    td    = today()
    since = add_days(td, -int(days))
    since_dt = since + " 00:00:00"

    activity = []

    # Employee checkins
    checkins = frappe.get_all(
        "Employee Checkin",
        filters={"employee": emp.name, "time": [">=", since_dt]},
        fields=["log_type", "time"],
        order_by="time desc",
        ignore_permissions=True,
    )
    for c in checkins:
        t = str(c.time)
        activity.append({
            "type":   "checkin",
            "icon":   c.log_type,
            "label":  "Checked " + ("in" if c.log_type == "IN" else "out"),
            "time":   t,
            "date":   t[:10],
            "detail": "",
        })

    # Leave applications submitted
    leaves = frappe.get_all(
        "Leave Application",
        filters={"employee": emp.name, "creation": [">=", since_dt]},
        fields=["leave_type", "status", "creation", "from_date", "to_date", "total_leave_days"],
        order_by="creation desc",
        ignore_permissions=True,
    )
    for l in leaves:
        t     = str(l.creation)
        days_ = float(l.total_leave_days or 0)
        cnt   = int(days_) if days_ == int(days_) else days_
        dr    = str(l.from_date)
        if l.to_date and str(l.to_date) != str(l.from_date):
            dr += " to " + str(l.to_date)
        activity.append({
            "type":   "leave",
            "icon":   "LEAVE",
            "label":  "Applied for " + (l.leave_type or "Leave"),
            "time":   t,
            "date":   t[:10],
            "detail": dr + " · " + str(cnt) + " day" + ("s" if cnt != 1 else ""),
            "status": l.status or "",
        })

    # Leaves actioned by this user as approver
    actioned = frappe.get_all(
        "Leave Application",
        filters={"leave_approver": user, "modified": [">=", since_dt], "docstatus": 1},
        fields=["employee_name", "leave_type", "status", "modified"],
        order_by="modified desc",
        ignore_permissions=True,
    )
    for l in actioned:
        t = str(l.modified)
        activity.append({
            "type":   "approval",
            "icon":   "APPROVED" if l.status == "Approved" else "REJECTED",
            "label":  (l.status or "") + " leave for " + (l.employee_name or ""),
            "time":   t,
            "date":   t[:10],
            "detail": l.leave_type or "",
        })

    activity.sort(key=lambda x: x["time"], reverse=True)
    return {"activities": activity}


@frappe.whitelist()
def get_employee_scorecard(employee_id):
    """Comprehensive scorecard for one employee — for manager view."""
    mgr_emp = _get_employee()
    if not mgr_emp:
        frappe.throw("No employee record found for current user")

    roles = frappe.get_roles()
    is_hr = bool({"HR Manager", "HR User", "Administrator"} & set(roles))
    effective_mgr = get_effective_manager(employee_id)
    if effective_mgr != mgr_emp.name and not is_hr:
        frappe.throw("Access denied", frappe.PermissionError)

    emp = frappe.db.get_value(
        "Employee", employee_id,
        ["name", "employee_name", "designation", "department", "branch",
         "date_of_joining", "cell_number", "personal_email", "company_email",
         "status", "gender", "image"],
        as_dict=True,
    )
    if not emp:
        frappe.throw("Employee not found")

    td = today()

    # 6-month attendance trend — single query, grouped in Python
    six_ago = add_days(td, -180)
    all_att_rows = frappe.get_all(
        "Attendance",
        filters={"employee": employee_id, "attendance_date": ["between", [six_ago, td]], "docstatus": 1},
        fields=["status", "attendance_date", "working_hours"],
        ignore_permissions=True,
    )
    _month_buckets = {}
    for r in all_att_rows:
        key = str(r.attendance_date)[:7]  # "YYYY-MM"
        if key not in _month_buckets:
            _month_buckets[key] = {"statuses": [], "hrs": []}
        _month_buckets[key]["statuses"].append(r.status)
        if r.working_hours:
            _month_buckets[key]["hrs"].append(float(r.working_hours))

    monthly_att = []
    for i in range(5, -1, -1):
        m_ref = add_days(td, -(i * 30))
        mo_s = get_first_day(m_ref)
        dt = getdate(mo_s)
        key = dt.strftime("%Y-%m")
        bucket = _month_buckets.get(key, {"statuses": [], "hrs": []})
        counts = {}
        for s in bucket["statuses"]:
            counts[s] = counts.get(s, 0) + 1
        hrs = bucket["hrs"]
        monthly_att.append({
            "month_label": dt.strftime("%b"),
            "present": counts.get("Present", 0) + round(counts.get("Half Day", 0) * 0.5),
            "absent": counts.get("Absent", 0),
            "on_leave": counts.get("On Leave", 0),
            "wfh": counts.get("Work From Home", 0),
            "avg_hours": round(sum(hrs) / len(hrs), 1) if hrs else 0,
        })

    # Current month summary
    mo_start = get_first_day(td)
    month_att = frappe.get_all(
        "Attendance",
        filters={"employee": employee_id, "attendance_date": [">=", mo_start], "docstatus": 1},
        fields=["status", "working_hours"],
        ignore_permissions=True,
    )
    att_summary = {}
    hrs = []
    for a in month_att:
        att_summary[a.status] = att_summary.get(a.status, 0) + 1
        if a.working_hours:
            hrs.append(float(a.working_hours))
    avg_hours = round(sum(hrs) / len(hrs), 1) if hrs else 0

    # Leave balances
    alloc_rows = frappe.db.sql("""
        SELECT leave_type, SUM(total_leaves_allocated) as allocated
        FROM `tabLeave Allocation`
        WHERE employee = %s AND docstatus = 1
          AND from_date <= %s AND to_date >= %s
        GROUP BY leave_type ORDER BY leave_type
    """, (employee_id, td, td), as_dict=True)
    yr_start = _leave_year_start(td)
    taken_rows = frappe.get_all(
        "Leave Application",
        filters={"employee": employee_id, "docstatus": 1, "status": "Approved",
                 "from_date": [">=", yr_start]},
        fields=["leave_type", "total_leave_days"],
        ignore_permissions=True,
    )
    taken_map = {}
    for r in taken_rows:
        taken_map[r.leave_type] = taken_map.get(r.leave_type, 0) + float(r.total_leave_days or 0)
    leave_balances = []
    for a in alloc_rows:
        alloc = float(a.allocated or 0)
        taken = taken_map.get(a.leave_type, 0)
        leave_balances.append({
            "leave_type": a.leave_type,
            "allocated": alloc,
            "taken": round(taken, 1),
            "balance": max(alloc - taken, 0),
        })

    # Pending leave requests
    pending_leaves = frappe.get_all(
        "Leave Application",
        filters={"employee": employee_id, "status": "Open", "docstatus": 0},
        fields=["name", "leave_type", "from_date", "to_date", "total_leave_days", "description"],
        order_by="creation desc", limit=10,
        ignore_permissions=True,
    )
    _mark_actionable(pending_leaves)

    # Goals
    goals = []
    goals_available = False
    if frappe.db.exists("DocType", "Individual Goal"):
        goals_available = True
        goals = frappe.get_all(
            "Individual Goal",
            filters={"employee": employee_id, "docstatus": ["!=", 2]},
            fields=["name", "goal_name", "progress_pct", "status", "trajectory"],
            order_by="creation desc", limit=15,
            ignore_permissions=True,
        )

    # Appraisal history
    appraisal_history = []
    if frappe.db.exists("DocType", "Alvoraa Appraisal Extension"):
        rows = frappe.db.sql("""
            SELECT ae.name, ae.appraisal_cycle, ae.review_status, ae.overall_rating,
                   COALESCE(ac.cycle_name, ae.appraisal_cycle) AS cycle_label,
                   ac.start_date,
                   (SELECT a2.total_score FROM `tabAppraisal` a2 WHERE a2.name = ae.name LIMIT 1) AS score
            FROM `tabAlvoraa Appraisal Extension` ae
            LEFT JOIN `tabAppraisal Cycle` ac ON ac.name = ae.appraisal_cycle
            WHERE ae.employee = %s AND ae.docstatus != 2
            ORDER BY COALESCE(ac.start_date, ae.creation) ASC
            LIMIT 8
        """, employee_id, as_dict=True)
        for r in rows:
            appraisal_history.append({
                "cycle_label": (r.cycle_label or "—"),
                "review_status": r.review_status or "",
                "overall_rating": r.overall_rating or "",
                "score": float(r.score or 0),
            })

    # Today's check-in status
    checkins = frappe.get_all(
        "Employee Checkin",
        filters={"employee": employee_id, "time": [">=", td + " 00:00:00"]},
        fields=["log_type", "time"],
        order_by="time asc",
        ignore_permissions=True,
    )
    last_checkin = checkins[-1] if checkins else None
    checked_in = bool(last_checkin and last_checkin.log_type == "IN")
    today_att = frappe.db.get_value(
        "Attendance",
        {"employee": employee_id, "attendance_date": td, "docstatus": 1},
        ["status", "in_time", "out_time", "working_hours"],
        as_dict=True,
    )

    return {
        "employee": emp,
        "checked_in": checked_in,
        "today_attendance": today_att,
        "month_att_summary": att_summary,
        "avg_hours": avg_hours,
        "monthly_att": monthly_att,
        "leave_balances": leave_balances,
        "pending_leaves": pending_leaves,
        "goals": goals,
        "goals_available": goals_available,
        "appraisal_history": appraisal_history,
    }


@frappe.whitelist()
def get_team_scorecard():
    """Compact scorecard for all direct reports — for comparison charts."""
    mgr_emp = _get_employee()
    if not mgr_emp:
        return {"members": []}

    td = today()
    mo_start = get_first_day(td)

    team = frappe.get_all(
        "Employee",
        filters={"reports_to": mgr_emp.name, "status": "Active"},
        fields=["name", "employee_name", "designation"],
        ignore_permissions=True,
    )
    if not team:
        return {"members": []}

    emp_ids = [m.name for m in team]

    # Monthly attendance for all team members
    att_rows = frappe.get_all(
        "Attendance",
        filters={"employee": ["in", emp_ids], "attendance_date": [">=", mo_start], "docstatus": 1},
        fields=["employee", "status", "working_hours"],
        ignore_permissions=True,
    )
    att_by_emp = {}
    for r in att_rows:
        e = r.employee
        if e not in att_by_emp:
            att_by_emp[e] = {"Present": 0, "Absent": 0, "On Leave": 0, "Work From Home": 0, "hrs": []}
        att_by_emp[e][r.status] = att_by_emp[e].get(r.status, 0) + 1
        if r.working_hours:
            att_by_emp[e]["hrs"].append(float(r.working_hours))

    # Goals per team member
    goals_by_emp = {}
    if frappe.db.exists("DocType", "Individual Goal"):
        goal_rows = frappe.get_all(
            "Individual Goal",
            filters={"employee": ["in", emp_ids], "docstatus": ["!=", 2]},
            fields=["employee", "progress_pct", "status"],
            ignore_permissions=True,
        )
        for g in goal_rows:
            e = g.employee
            if e not in goals_by_emp:
                goals_by_emp[e] = {"total": 0, "pct_sum": 0, "completed": 0}
            goals_by_emp[e]["total"] += 1
            goals_by_emp[e]["pct_sum"] += float(g.progress_pct or 0)
            if g.status == "Completed":
                goals_by_emp[e]["completed"] += 1
        for e, gd in goals_by_emp.items():
            gd["avg"] = round(gd["pct_sum"] / gd["total"]) if gd["total"] else 0

    # Latest appraisal score per team member
    score_by_emp = {}
    if frappe.db.exists("DocType", "Alvoraa Appraisal Extension"):
        # .format() only inserts "%s" placeholders — no user data in the format string; safe.
        placeholders = ",".join(["%s"] * len(emp_ids))
        rows = frappe.db.sql("""
            SELECT ae.employee, ae.overall_rating,
                   (SELECT a2.total_score FROM `tabAppraisal` a2 WHERE a2.name = ae.name LIMIT 1) AS score
            FROM `tabAlvoraa Appraisal Extension` ae
            WHERE ae.employee IN ({})
              AND ae.docstatus != 2
            ORDER BY ae.creation DESC
        """.format(placeholders), emp_ids, as_dict=True)
        for r in rows:
            if r.employee not in score_by_emp:
                score_by_emp[r.employee] = {
                    "score": float(r.score or 0),
                    "rating": r.overall_rating or "",
                }

    members = []
    for m in team:
        att = att_by_emp.get(m.name, {})
        hrs_list = att.get("hrs", [])
        gd = goals_by_emp.get(m.name, {})
        sc = score_by_emp.get(m.name, {})
        members.append({
            "name": m.name,
            "employee_name": m.employee_name,
            "designation": m.designation or "",
            "present": att.get("Present", 0) + round(att.get("Half Day", 0) * 0.5),
            "absent": att.get("Absent", 0),
            "on_leave": att.get("On Leave", 0),
            "wfh": att.get("Work From Home", 0),
            "avg_hours": round(sum(hrs_list) / len(hrs_list), 1) if hrs_list else 0,
            "goals_total": gd.get("total", 0),
            "goals_completed": gd.get("completed", 0),
            "goals_avg": gd.get("avg", 0),
            "appraisal_score": sc.get("score", 0),
            "appraisal_rating": sc.get("rating", ""),
        })

    return {"members": members}


@frappe.whitelist()
def get_employee_detail_for_manager(employee_id):
    """Detailed view of one employee for their manager."""
    mgr_emp = _get_employee()
    if not mgr_emp:
        frappe.throw("No employee record found for current user")

    # Allow direct manager OR HR roles
    roles = frappe.get_roles()
    is_hr = bool({"HR Manager", "HR User", "Administrator"} & set(roles))
    emp_reports_to = frappe.db.get_value("Employee", employee_id, "reports_to")
    if emp_reports_to != mgr_emp.name and not is_hr:
        frappe.throw("Access denied", frappe.PermissionError)

    emp = frappe.db.get_value(
        "Employee", employee_id,
        ["name", "employee_name", "designation", "department", "branch",
         "date_of_joining", "cell_number", "personal_email", "company_email",
         "status", "gender", "image"],
        as_dict=True,
    )
    if not emp:
        frappe.throw("Employee not found")

    td = today()

    # Today's checkins
    checkins = frappe.get_all(
        "Employee Checkin",
        filters={"employee": employee_id, "time": [">=", td + " 00:00:00"]},
        fields=["log_type", "time"],
        order_by="time asc",
        ignore_permissions=True,
    )
    last_checkin = checkins[-1] if checkins else None
    checked_in   = bool(last_checkin and last_checkin.log_type == "IN")

    # Today's attendance record
    today_att = frappe.db.get_value(
        "Attendance",
        {"employee": employee_id, "attendance_date": td, "docstatus": 1},
        ["status", "in_time", "out_time", "working_hours"],
        as_dict=True,
    )

    # Current-month attendance summary
    mo_start  = get_first_day(td)
    month_att = frappe.get_all(
        "Attendance",
        filters={"employee": employee_id, "attendance_date": [">=", mo_start], "docstatus": 1},
        fields=["status"],
        ignore_permissions=True,
    )
    att_summary = {}
    for a in month_att:
        att_summary[a.status] = att_summary.get(a.status, 0) + 1

    # Leave balances — allocations minus approved applications (leaves_taken column removed in newer HRMS)
    alloc_rows = frappe.db.sql("""
        SELECT leave_type, SUM(total_leaves_allocated) as allocated
        FROM `tabLeave Allocation`
        WHERE employee = %s AND docstatus = 1
          AND from_date <= %s AND to_date >= %s
        GROUP BY leave_type ORDER BY leave_type
    """, (employee_id, td, td), as_dict=True)
    yr_start = _leave_year_start(td)
    taken_rows = frappe.get_all(
        "Leave Application",
        filters={"employee": employee_id, "docstatus": 1, "status": "Approved",
                 "from_date": [">=", yr_start]},
        fields=["leave_type", "total_leave_days"],
        ignore_permissions=True,
    )
    taken_map = {}
    for r in taken_rows:
        taken_map[r.leave_type] = taken_map.get(r.leave_type, 0) + float(r.total_leave_days or 0)
    leave_balances = [
        {"leave_type": a.leave_type,
         "allocated": float(a.allocated or 0),
         "balance": max(float(a.allocated or 0) - taken_map.get(a.leave_type, 0), 0)}
        for a in alloc_rows
    ]

    # Pending leave requests from this employee
    pending_leaves = frappe.get_all(
        "Leave Application",
        filters={"employee": employee_id, "status": "Open", "docstatus": 0},
        fields=["name", "leave_type", "from_date", "to_date",
                "total_leave_days", "description", "leave_approver"],
        order_by="creation desc", limit=10,
        ignore_permissions=True,
    )
    _mark_actionable(pending_leaves)

    # Recent approved/rejected leaves
    recent_leaves = frappe.get_all(
        "Leave Application",
        filters={"employee": employee_id, "docstatus": 1},
        fields=["name", "leave_type", "from_date", "to_date",
                "total_leave_days", "status"],
        order_by="from_date desc", limit=8,
        ignore_permissions=True,
    )

    return {
        "employee":        emp,
        "checked_in":      checked_in,
        "last_checkin":    last_checkin,
        "today_checkins":  checkins,
        "today_attendance": today_att,
        "month_att_summary": att_summary,
        "leave_balances":  leave_balances,
        "pending_leaves":  pending_leaves,
        "recent_leaves":   recent_leaves,
    }


# ── Default approver helpers ──────────────────────────────────────────────────

@frappe.whitelist()
def get_hr_approver():
    """Return the first enabled HR Manager or HR User (fallback approver)."""
    for role in ("HR Manager", "HR User"):
        rows = frappe.get_all(
            "Has Role",
            filters={"role": role, "parenttype": "User"},
            fields=["parent"],
            ignore_permissions=True,
        )
        if not rows:
            continue
        user_ids = [r.parent for r in rows]
        enabled = frappe.get_all(
            "User",
            filters={"name": ["in", user_ids], "enabled": 1},
            fields=["name"],
            limit=1,
            ignore_permissions=True,
        )
        if enabled:
            return enabled[0].name
    return None


@frappe.whitelist()
def get_switch_target():
    """Where this user may switch to, and what to call the link.

    The portal's api() helper prefixes every call with this module, so the
    endpoint lives here while the logic - and the role sets it depends on - stay
    in module_access.
    """
    from alvoraa_portal.module_access import get_switch_target as _target

    return _target()


@frappe.whitelist()
def get_available_features():
    """Return which HR self-service features are available on this instance.

    Static HR config (shift_request, leave_encashment, goals) is cached globally
    under portal_features_global — one entry for the whole site, invalidated
    immediately by doc_events hooks on Shift Type / Leave Type.

    Permission-based flags (attendance_request, advance_request) are computed
    live per call — they are two cheap has_permission checks and must not be
    cached globally (they vary per user).
    """
    # ── Static flags: global cache, invalidated by hooks on Shift Type / Leave Type ──
    static_cache_key = "portal_features_global"
    static = None
    try:
        static = frappe.cache().get_value(static_cache_key)
    except Exception:
        pass

    if not static:
        static = {}
        try:
            static["shift_request"] = frappe.db.count("Shift Type") > 0
        except Exception:
            static["shift_request"] = False

        try:
            static["leave_encashment"] = bool(
                frappe.db.get_value("Leave Type", {"allow_encashment": 1}, "name")
            )
        except Exception:
            static["leave_encashment"] = False

        try:
            static["goals"] = bool(frappe.db.exists("DocType", "Individual Goal"))
        except Exception:
            static["goals"] = False

        try:
            # Safety-net TTL only; hooks clear this immediately when config changes
            frappe.cache().set_value(static_cache_key, static, expires_in_sec=3600)
        except Exception:
            pass

    # ── Permission flags: live per user, never cached ──────────────────────────
    features = dict(static)

    try:
        features["attendance_request"] = bool(
            frappe.has_permission("Attendance Request", "create", raise_exception=False)
        )
    except Exception:
        features["attendance_request"] = False

    try:
        features["advance_request"] = bool(
            frappe.has_permission("Employee Advance", "create", raise_exception=False)
        )
    except Exception:
        features["advance_request"] = False

    # ── Plan entitlement: what this tenant actually bought ─────────────────────
    #
    # Wave 6. subscription.has_feature() has existed since wave 1 and NOTHING
    # called it, so the portal offered Goals, Analytics and the Vendor panel to
    # every tenant regardless of plan. Hiding modules in the desk while the
    # portal - the interface most staff actually use - ignored the plan entirely.
    #
    # Read straight from the registry, so a new sellable feature is gated the day
    # it is added rather than needing a matching change here.
    try:
        from alvoraa_portal.subscription import FEATURES, has_feature

        for key in FEATURES:
            features[f"plan_{key}"] = bool(has_feature(key))
    except Exception:
        # Never black out the portal because entitlement could not be read. The
        # desk gates are the boundary; this only decides what to draw.
        frappe.log_error(title="hr_api: could not read plan entitlement",
                         message=frappe.get_traceback())

    # `goals` already meant "is the app installed", which wave 5 makes plan-aware
    # anyway. AND them so a site that still has the app from an earlier plan does
    # not keep showing the panel after a downgrade.
    if "plan_goals" in features:
        features["goals"] = bool(features.get("goals")) and features["plan_goals"]

    return features


# ── Employee self-service endpoints ───────────────────────────────────────────

@frappe.whitelist()
def get_checkin_status():
    emp = _get_employee()
    if not emp:
        return {"no_employee": True}
    td = today()
    checkins = frappe.get_all(
        "Employee Checkin",
        filters={"employee": emp.name, "time": [">=", td + " 00:00:00"]},
        fields=["name", "log_type", "time"],
        order_by="time asc",
        ignore_permissions=True,
    )
    last = checkins[-1] if checkins else None
    checked_in = bool(last and last.log_type == "IN")
    # Also get today's attendance record if exists
    att = frappe.db.get_value(
        "Attendance",
        {"employee": emp.name, "attendance_date": td, "docstatus": 1},
        ["status", "in_time", "out_time", "working_hours"],
        as_dict=True,
    )
    return {
        "employee": emp,
        "checked_in": checked_in,
        "last_action": last,
        "todays_checkins": checkins,
        "attendance": att,
    }


@frappe.whitelist()
def do_checkin(log_type):
    if log_type not in ("IN", "OUT"):
        frappe.throw("Invalid log_type")
    emp = _get_employee()
    if not emp:
        frappe.throw("No employee record found for this user")
    doc = frappe.get_doc({
        "doctype": "Employee Checkin",
        "employee": emp.name,
        "employee_name": emp.employee_name,
        "log_type": log_type,
        "time": now(),
        "device_id": "web-portal",
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "ok", "log_type": log_type, "time": str(doc.time), "name": doc.name}


@frappe.whitelist()
def get_attendance_calendar(year, month):
    emp = _get_employee()
    if not emp:
        return {"no_employee": True}
    year, month = int(year), int(month)
    from_date = f"{year}-{month:02d}-01"
    last_day = _calendar.monthrange(year, month)[1]
    to_date = f"{year}-{month:02d}-{last_day}"

    rows = frappe.get_all(
        "Attendance",
        filters={
            "employee": emp.name,
            "attendance_date": ["between", [from_date, to_date]],
            "docstatus": 1,
        },
        fields=["attendance_date", "status", "in_time", "out_time", "working_hours"],
        ignore_permissions=True,
    )

    # Leave applications overlapping this month
    leaves = frappe.get_all(
        "Leave Application",
        filters={
            "employee": emp.name,
            "docstatus": 1,
            "status": "Approved",
            "from_date": ["<=", to_date],
            "to_date": [">=", from_date],
        },
        fields=["leave_type", "from_date", "to_date"],
        ignore_permissions=True,
    )

    # Holidays
    holiday_list = frappe.db.get_value("Employee", emp.name, "holiday_list")
    holidays = []
    if holiday_list:
        holidays = frappe.get_all(
            "Holiday",
            filters={
                "parent": holiday_list,
                "holiday_date": ["between", [from_date, to_date]],
            },
            fields=["holiday_date", "description"],
            ignore_permissions=True,
        )

    return {
        "records": rows,
        "leaves": leaves,
        "holidays": holidays,
        "year": year,
        "month": month,
        "last_day": last_day,
    }


@frappe.whitelist()
def get_payslips():
    emp = _get_employee()
    if not emp:
        return {"no_employee": True}
    slips = frappe.get_all(
        "Salary Slip",
        filters={"employee": emp.name, "docstatus": 1},
        fields=["name", "posting_date", "start_date", "end_date",
                "gross_pay", "total_deduction", "net_pay", "currency"],
        order_by="posting_date desc",
        limit=12,
        ignore_permissions=True,
    )
    return {"payslips": slips, "employee": emp}


@frappe.whitelist()
def get_expense_claims():
    emp = _get_employee()
    if not emp:
        return {"no_employee": True}
    claims = frappe.get_all(
        "Expense Claim",
        filters={"employee": emp.name},
        fields=["name", "posting_date", "total_claimed_amount",
                "total_sanctioned_amount", "status", "approval_status", "remark"],
        order_by="posting_date desc",
        limit=15,
        ignore_permissions=True,
    )
    return {"claims": claims, "employee": emp}


@frappe.whitelist()
def get_all_active_employees():
    roles = frappe.get_roles()
    if not ({"HR Manager", "HR User", "System Manager"} & set(roles)):
        frappe.throw("Not permitted.", frappe.PermissionError)
    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name", "department", "designation"],
        order_by="employee_name asc",
        ignore_permissions=True,
    )
    return {"employees": employees}


@frappe.whitelist()
def get_leave_summary(employee_id=None):
    roles = frappe.get_roles()
    is_hr = bool({"HR Manager", "HR User", "System Manager"} & set(roles))
    if employee_id and is_hr:
        emp = frappe.get_doc("Employee", employee_id)
    else:
        emp = _get_employee()
    if not emp:
        return {"no_employee": True}
    td = today()
    yr_start = _leave_year_start(td, emp.company)

    allocations = frappe.get_all(
        "Leave Allocation",
        filters={
            "employee": emp.name, "docstatus": 1,
            "from_date": ["<=", td], "to_date": [">=", td],
        },
        fields=["leave_type", "total_leaves_allocated", "from_date", "to_date"],
        ignore_permissions=True,
    )

    taken_map = {}
    pending_map = {}
    if allocations:
        apps = frappe.get_all(
            "Leave Application",
            filters={"employee": emp.name, "from_date": [">=", yr_start]},
            fields=["leave_type", "total_leave_days", "status", "docstatus"],
            ignore_permissions=True,
        )
        for a in apps:
            if a.docstatus == 1 and a.status == "Approved":
                taken_map[a.leave_type] = taken_map.get(a.leave_type, 0) + a.total_leave_days
            elif a.status == "Open":
                pending_map[a.leave_type] = pending_map.get(a.leave_type, 0) + a.total_leave_days

    balances = []
    for al in allocations:
        lt = al.leave_type
        total = float(al.total_leaves_allocated)
        taken = float(taken_map.get(lt, 0))
        pending = float(pending_map.get(lt, 0))
        balances.append({
            "leave_type": lt,
            "total": total,
            "taken": taken,
            "pending": pending,
            "balance": max(total - taken, 0),
            "color": LEAVE_COLORS.get(lt, "#64748b"),
            "pct_used": round(taken / total * 100) if total else 0,
        })

    applications = frappe.get_all(
        "Leave Application",
        filters={"employee": emp.name},
        fields=["name", "leave_type", "from_date", "to_date", "status",
                "total_leave_days", "description", "docstatus"],
        order_by="creation desc",
        limit=10,
        ignore_permissions=True,
    )

    # Tell the caller WHY the list is empty. "No leave types allocated for this
    # period" reads as a date problem, and sent a tester hunting through fiscal
    # year settings when the real answer was that the employee had never been
    # given a leave policy at all. Those are different problems with different
    # fixes, so the UI needs to be able to tell them apart.
    ever_allocated = bool(frappe.db.exists("Leave Allocation",
                                           {"employee": emp.name, "docstatus": 1}))

    return {"balances": balances, "applications": applications, "employee": emp,
            "ever_allocated": ever_allocated}


@frappe.whitelist()
def get_expense_types():
    return frappe.get_all(
        "Expense Claim Type",
        fields=["name"],
        order_by="name asc",
        ignore_permissions=True,
    )


@frappe.whitelist()
def apply_expense_claim(expense_type, expense_date, amount, description=None):
    emp = _get_employee()
    if not emp:
        frappe.throw("No employee record is linked to your account.")

    amount = float(amount)
    if amount <= 0:
        frappe.throw("Amount must be greater than zero.")

    # The child table is `expenses`. It was `expense_claim_details` in older
    # ERPNext; under v16 that key is ignored, so the claim was built with no rows
    # and every submission died on
    #   MandatoryError: exchange_rate, expenses
    # `currency` and `exchange_rate` are required too. Same-currency claims are
    # rate 1; a claim in another currency is not something this portal offers.
    currency = frappe.db.get_value("Company", emp.company, "default_currency")

    doc = frappe.get_doc({
        "doctype": "Expense Claim",
        "employee": emp.name,
        "company": emp.company,
        "posting_date": today(),
        "currency": currency,
        "exchange_rate": 1,
        "expenses": [{
            "doctype": "Expense Claim Detail",
            "expense_date": expense_date,
            "expense_type": expense_type,
            "description": description or "",
            "amount": amount,
            "sanctioned_amount": amount,
        }],
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name}


@frappe.whitelist()
def apply_leave(leave_type, from_date, to_date, half_day=0, half_day_date=None, reason=None, on_behalf_of=None):
    roles = frappe.get_roles()
    is_hr = bool({"HR Manager", "HR User", "System Manager"} & set(roles))

    if on_behalf_of and is_hr:
        emp = frappe.get_doc("Employee", on_behalf_of)
    else:
        emp = _get_employee()
    if not emp:
        frappe.throw("No employee record is linked to your account.")

    doc = frappe.get_doc({
        "doctype": "Leave Application",
        "employee": emp.name,
        "leave_type": leave_type,
        "from_date": from_date,
        "to_date": to_date,
        "half_day": int(half_day),
        "half_day_date": half_day_date if int(half_day) else None,
        "description": reason or "",
        "status": "Open",
        "company": emp.company,
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name}


@frappe.whitelist()
def preview_leave_request(leave_type, from_date, to_date, half_day=0, half_day_date=None,
                          on_behalf_of=None):
    """How many days a leave request costs, and whether the balance covers it.

    Read-only. Exists so the portal can tell the user BEFORE they submit, instead of
    letting them find out from a raw server error afterwards.

    It deliberately reuses Frappe HR's own functions and mirrors the rule in
    LeaveApplication.validate_balance_leaves(). Counting days in JavaScript would be
    wrong - weekends, the employee's holiday list, half days and the Leave Type's
    include_holiday flag all change the answer. If this ever disagrees with the server,
    the server wins: this is a preview, not the gate.
    """
    from hrms.hr.doctype.leave_application.leave_application import (
        get_leave_balance_on,
        get_number_of_leave_days,
        is_lwp,
    )

    roles = frappe.get_roles()
    is_hr = bool({"HR Manager", "HR User", "System Manager"} & set(roles))

    # same rule as apply_leave: only HR may act for someone else
    if on_behalf_of and is_hr:
        emp = frappe.get_doc("Employee", on_behalf_of)
    else:
        emp = _get_employee()
    if not emp:
        frappe.throw("No employee record is linked to your account.")

    days = get_number_of_leave_days(
        emp.name, leave_type, from_date, to_date,
        int(half_day or 0), half_day_date if int(half_day or 0) else None,
    )

    # Leave Without Pay is not drawn from an allocation, so it has no balance to check
    if is_lwp(leave_type):
        return {"days": days, "balance": None, "unlimited": True,
                "allow_negative": True, "employee_name": emp.employee_name}

    precision = frappe.utils.cint(
        frappe.db.get_single_value("System Settings", "float_precision")) or 2
    balance = get_leave_balance_on(
        emp.name, leave_type, from_date, to_date,
        consider_all_leaves_in_the_allocation_period=True,
        for_consumption=True,
    )
    available = frappe.utils.flt(balance.get("leave_balance_for_consumption"), precision)

    return {
        "days": days,
        "balance": available,
        "unlimited": False,
        # when the Leave Type allows a negative balance Frappe only warns, so neither do we
        "allow_negative": bool(frappe.db.get_value("Leave Type", leave_type, "allow_negative")),
        "employee_name": emp.employee_name,
    }


# ── Self-service form submissions ──────────────────────────────────────────────

@frappe.whitelist()
def get_shift_types():
    return frappe.get_all(
        "Shift Type",
        fields=["name", "start_time", "end_time"],
        ignore_permissions=True,
    )


@frappe.whitelist()
def get_encashable_leave_types():
    emp = _get_employee()
    if not emp:
        return []
    td = today()
    allocations = frappe.get_all(
        "Leave Allocation",
        filters={"employee": emp.name, "docstatus": 1, "from_date": ["<=", td], "to_date": [">=", td]},
        fields=["leave_type", "total_leaves_allocated"],
        ignore_permissions=True,
    )
    leave_type_names = [a.leave_type for a in allocations]
    encashable = {
        r.name for r in frappe.get_all(
            "Leave Type",
            filters={"name": ["in", leave_type_names], "allow_encashment": 1},
            fields=["name"],
            ignore_permissions=True,
        )
    }
    return [
        {"leave_type": a.leave_type, "allocated": float(a.total_leaves_allocated)}
        for a in allocations
        if a.leave_type in encashable
    ]


@frappe.whitelist()
def submit_shift_request(shift_type, from_date, to_date, company=""):
    emp = _get_employee()
    if not emp:
        frappe.throw("No employee record found for this user.")
    approver = frappe.db.get_value("Employee", emp.name, "shift_request_approver")
    if not approver:
        approver = get_hr_approver()
    if not approver:
        frappe.throw("No shift request approver configured. Please contact HR.")
    doc = frappe.get_doc({
        "doctype": "Shift Request",
        "employee": emp.name,
        "employee_name": emp.employee_name,
        "company": company or emp.company,
        "shift_type": shift_type,
        "from_date": from_date,
        "to_date": to_date,
        "approver": approver,
        "status": "Draft",
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name}


@frappe.whitelist()
def submit_attendance_request(from_date, to_date, reason, explanation=""):
    emp = _get_employee()
    if not emp:
        frappe.throw("No employee record found for this user.")
    doc = frappe.get_doc({
        "doctype": "Attendance Request",
        "employee": emp.name,
        "employee_name": emp.employee_name,
        "company": emp.company,
        "from_date": from_date,
        "to_date": to_date,
        "reason": reason,
        "explanation": explanation,
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name}


@frappe.whitelist()
def submit_advance_request(purpose, amount):
    emp = _get_employee()
    if not emp:
        frappe.throw("No employee record found for this user.")
    doc = frappe.get_doc({
        "doctype": "Employee Advance",
        "employee": emp.name,
        "employee_name": emp.employee_name,
        "company": emp.company,
        "purpose": purpose,
        "advance_amount": float(amount),
        "posting_date": today(),
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name}


@frappe.whitelist()
def submit_leave_encashment(leave_type, encashment_date=None):
    emp = _get_employee()
    if not emp:
        frappe.throw("No employee record found for this user.")
    doc = frappe.get_doc({
        "doctype": "Leave Encashment",
        "employee": emp.name,
        "employee_name": emp.employee_name,
        "department": emp.department,
        "leave_type": leave_type,
        "encashment_date": encashment_date or today(),
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name}


@frappe.whitelist()
def get_requests_history():
    """Return history for all four self-service request types."""
    emp = _get_employee()
    if not emp:
        return {}

    shift_requests = frappe.get_all(
        "Shift Request",
        filters={"employee": emp.name},
        fields=["name", "shift_type", "from_date", "to_date", "status"],
        order_by="creation desc",
        limit=5,
        ignore_permissions=True,
    )

    try:
        encashments = frappe.get_all(
            "Leave Encashment",
            filters={"employee": emp.name},
            fields=["name", "leave_type", "encashment_date", "encashment_amount", "status"],
            order_by="creation desc",
            limit=5,
            ignore_permissions=True,
        )
    except Exception:
        encashments = []

    try:
        att_requests = frappe.get_all(
            "Attendance Request",
            filters={"employee": emp.name},
            fields=["name", "from_date", "to_date", "reason", "docstatus"],
            order_by="creation desc",
            limit=5,
            ignore_permissions=True,
        )
    except Exception:
        att_requests = []

    try:
        advances = frappe.get_all(
            "Employee Advance",
            filters={"employee": emp.name},
            fields=["name", "posting_date", "purpose", "advance_amount", "status"],
            order_by="posting_date desc",
            limit=5,
            ignore_permissions=True,
        )
    except Exception:
        advances = []

    return {
        "shift_requests": shift_requests,
        "encashments": encashments,
        "att_requests": att_requests,
        "advances": advances,
    }


# ── Goals & Performance ───────────────────────────────────────────────────────

@frappe.whitelist()
@requires_feature("goals")
def get_goals_portal_data():
    """Return all goals for the employee (draft + submitted). Returns {available: False} if alvoraa_goals not installed."""
    if not frappe.db.exists("DocType", "Individual Goal"):
        return {"available": False}

    emp = _get_employee()
    if not emp:
        return {"available": True, "no_employee": True}

    # Include drafts (docstatus=0) and submitted (docstatus=1); exclude Frappe-cancelled (docstatus=2)
    try:
        goals = frappe.get_all(
            "Individual Goal",
            filters={"employee": emp.name, "docstatus": ["!=", 2], "status": ["!=", "Cancelled"]},
            fields=["name", "employee", "employee_name", "goal_name", "goal_cascade",
                    "target_value", "unit", "start_date", "end_date", "status",
                    "actual_progress", "progress_pct", "trajectory", "docstatus"],
            order_by="trajectory asc, end_date asc",
            ignore_permissions=True,
        )
    except Exception:
        goals = []

    # Attach evidence per goal — single batch query instead of one per goal
    if goals:
        try:
            all_evidence = frappe.get_all(
                "Goal Evidence",
                filters={"parent": ["in", [g["name"] for g in goals]]},
                fields=["parent", "evidence_type", "validation_status", "extracted_date",
                        "extracted_order_count", "extracted_amount", "extracted_customer",
                        "evidence_file", "validation_notes"],
                order_by="creation desc",
                ignore_permissions=True,
            )
            evidence_map = {}
            for ev in all_evidence:
                evidence_map.setdefault(ev["parent"], []).append(ev)
            for g in goals:
                evs = evidence_map.get(g["name"], [])
                g["evidence"] = evs
                g["pending_evidence_count"] = sum(1 for e in evs if e.get("validation_status") == "Pending")
        except Exception:
            for g in goals:
                g["evidence"] = []
                g["pending_evidence_count"] = 0

    cascades = {}
    for g in goals:
        cid = g.get("goal_cascade")
        if cid and cid not in cascades:
            try:
                c = frappe.db.get_value(
                    "Goal Cascade", cid,
                    ["name", "cascade_name", "period_start", "period_end", "unit", "company_target", "status"],
                    as_dict=True, ignore_permissions=True,
                )
                if c:
                    cascades[cid] = c
            except Exception:
                pass

    total     = len(goals)
    on_track  = sum(1 for g in goals if g.get("trajectory") == "On Track")
    at_risk   = sum(1 for g in goals if g.get("trajectory") == "At Risk")
    off_track = sum(1 for g in goals if g.get("trajectory") == "Off Track")
    completed = sum(1 for g in goals if g.get("status") == "Completed")

    return {
        "available": True,
        "employee": emp.name,
        "goals": goals,
        "cascades": list(cascades.values()),
        "summary": {
            "total": total,
            "on_track": on_track,
            "at_risk": at_risk,
            "off_track": off_track,
            "completed": completed,
        },
    }


@frappe.whitelist()
@requires_feature("goals")
def submit_goal_evidence_portal(goal_id, evidence_type="Manual Entry",
                                 value=None, extracted_date=None,
                                 evidence_file=None, raw_extracted_data=None,
                                 extracted_amount=None):
    """Submit evidence for an employee goal — portal-facing proxy with ownership check."""
    if not frappe.db.exists("DocType", "Individual Goal"):
        frappe.throw("Goals feature is not available on this instance")

    emp = _get_employee()
    if not emp:
        frappe.throw("No employee record found for current user")

    goal_employee = frappe.db.get_value("Individual Goal", goal_id, "employee")
    if goal_employee != emp.name:
        frappe.throw("Access denied", frappe.PermissionError)

    from alvoraa_goals.api.goal_api import submit_goal_evidence
    return submit_goal_evidence(
        goal_id=goal_id,
        evidence_type=evidence_type,
        value=value or extracted_amount,
        extracted_date=extracted_date,
        evidence_file=evidence_file or None,
        raw_extracted_data=raw_extracted_data or None,
    )


@frappe.whitelist()
def get_pending_approvals():
    from alvoraa_goals.api.goal_api import get_pending_approvals as _gpa
    return _gpa()


@frappe.whitelist()
@requires_feature("goals")
def approve_goal_evidence(goal_name, evidence_idx):
    from alvoraa_goals.controllers.evidence import approve_evidence
    return approve_evidence(goal_name, evidence_idx)


@frappe.whitelist()
@requires_feature("goals")
def reject_goal_evidence(goal_name, evidence_idx, reason=""):
    from alvoraa_goals.controllers.evidence import reject_evidence
    return reject_evidence(goal_name, evidence_idx, reason)


@frappe.whitelist()
def approve_kpi_progress(kpi_name, log_idx, comment=None):
    from alvoraa_goals.api.goal_api import approve_kpi_progress as _akp
    return _akp(kpi_name, log_idx, comment)


@frappe.whitelist()
def reject_kpi_progress(kpi_name, log_idx, comment=None):
    from alvoraa_goals.api.goal_api import reject_kpi_progress as _rkp
    return _rkp(kpi_name, log_idx, comment)


@frappe.whitelist()
def get_org_setting(key):
    _require_hr()
    return frappe.db.get_default(key)


@frappe.whitelist()
def set_org_setting(key, value):
    _require_hr()
    frappe.db.set_default(key, value)
    frappe.db.commit()
    return {"ok": True}


def _require_hr():
    if not (frappe.has_role("HR Manager") or frappe.has_role("System Manager")):
        frappe.throw("Not permitted", frappe.PermissionError)


@frappe.whitelist()
@requires_feature("goals")
def get_goal_detail(goal_id):
    """Full goal detail for drawer — accessible to employee (own) or manager (direct report) or HR."""
    if not frappe.db.exists("DocType", "Individual Goal"):
        frappe.throw("Goals feature not available")
    emp = _get_employee()
    if not emp:
        frappe.throw("No employee record")
    goal_employee = frappe.db.get_value("Individual Goal", goal_id, "employee")
    roles = frappe.get_roles()
    is_hr = bool({"HR Manager", "HR User", "Administrator"} & set(roles))
    is_owner = goal_employee == emp.name
    if not is_owner and not is_hr:
        dr = frappe.db.get_value("Employee",
            {"name": goal_employee, "reports_to": emp.name, "status": "Active"},
            "name")
        if not dr:
            frappe.throw("Access denied", frappe.PermissionError)
    # Query directly — include drafts (docstatus=0) as well as submitted
    goals = frappe.get_all(
        "Individual Goal",
        filters={"employee": goal_employee, "docstatus": ["!=", 2], "name": goal_id},
        fields=["name", "employee", "employee_name", "goal_name", "goal_cascade",
                "target_value", "unit", "start_date", "end_date", "status",
                "actual_progress", "progress_pct", "trajectory", "docstatus",
                "goal_type", "company_value", "is_extra_initiative"],
        ignore_permissions=True,
    )
    goal = goals[0] if goals else None
    if not goal:
        frappe.throw("Goal not found")
    try:
        evs = frappe.get_all(
            "Goal Evidence",
            filters={"parent": goal_id},
            fields=["evidence_type", "validation_status", "extracted_date",
                    "extracted_order_count", "extracted_amount", "extracted_customer",
                    "evidence_file", "validation_notes"],
            order_by="creation desc",
            ignore_permissions=True,
        )
        goal["evidence"] = evs
        goal["pending_evidence_count"] = sum(1 for e in evs if e.get("validation_status") == "Pending")
    except Exception:
        goal["evidence"] = []
        goal["pending_evidence_count"] = 0
    cascade = {}
    if goal.get("goal_cascade"):
        cascade = frappe.db.get_value(
            "Goal Cascade", goal["goal_cascade"],
            ["name", "cascade_name", "period_start", "period_end", "unit"],
            as_dict=True,
        ) or {}
    return {"goal": goal, "cascade": cascade, "is_owner": is_owner, "can_edit": is_owner or is_hr}


@frappe.whitelist()
@requires_feature("goals")
def get_team_goals():
    """Goals grouped by direct report — manager-facing."""
    if not frappe.db.exists("DocType", "Individual Goal"):
        return {"available": False}
    emp = _get_employee()
    if not emp:
        return {"available": True, "no_employee": True}
    reports = frappe.get_all(
        "Employee",
        filters={"reports_to": emp.name, "status": "Active"},
        fields=["name", "employee_name", "designation"],
        ignore_permissions=True,
    )
    if not reports:
        return {"available": True, "by_employee": {}}
    report_ids = [r.name for r in reports]
    try:
        goals = frappe.get_all(
            "Individual Goal",
            filters={"employee": ["in", report_ids], "docstatus": ["!=", 2], "status": ["!=", "Cancelled"]},
            fields=["name", "employee", "employee_name", "goal_name", "goal_cascade",
                    "target_value", "unit", "start_date", "end_date", "status",
                    "actual_progress", "progress_pct", "trajectory", "docstatus"],
            order_by="employee asc, trajectory asc",
            ignore_permissions=True,
        )
    except Exception:
        goals = []
    by_employee = {}
    for g in goals:
        eid = g.employee
        if eid not in by_employee:
            rec = next((r for r in reports if r.name == eid), {"employee_name": g.employee_name, "designation": ""})
            by_employee[eid] = {"employee": rec, "goals": []}
        by_employee[eid]["goals"].append(g)
    return {"available": True, "by_employee": by_employee}


@frappe.whitelist()
@requires_feature("goals")
def update_goal_status(goal_id, new_status):
    """Update goal status. Employee (own) or manager (direct reports) or HR."""
    if new_status not in ("Active", "Completed", "Cancelled"):
        frappe.throw("Invalid status")
    emp = _get_employee()
    if not emp:
        frappe.throw("No employee record")
    goal_employee = frappe.db.get_value("Individual Goal", goal_id, "employee")
    roles = frappe.get_roles()
    is_hr = bool({"HR Manager", "HR User", "Administrator"} & set(roles))
    if goal_employee != emp.name and not is_hr:
        dr = frappe.db.get_value("Employee",
            {"name": goal_employee, "reports_to": emp.name, "status": "Active"},
            "name")
        if not dr:
            frappe.throw("Access denied", frappe.PermissionError)
    frappe.db.set_value("Individual Goal", goal_id, "status", new_status)
    frappe.db.commit()
    return {"goal_id": goal_id, "status": new_status}


@frappe.whitelist()
@requires_feature("goals")
def add_goal_comment(goal_id, content):
    """Add a comment to a goal visible to employee, manager, and HR."""
    if not content or not content.strip():
        frappe.throw("Comment cannot be empty")
    emp = _get_employee()
    if not emp:
        frappe.throw("No employee record")
    goal_employee = frappe.db.get_value("Individual Goal", goal_id, "employee")
    roles = frappe.get_roles()
    is_hr = bool({"HR Manager", "HR User", "Administrator"} & set(roles))
    if goal_employee != emp.name and not is_hr:
        dr = frappe.db.get_value("Employee",
            {"name": goal_employee, "reports_to": emp.name, "status": "Active"},
            "name")
        if not dr:
            frappe.throw("Access denied", frappe.PermissionError)
    comment = frappe.get_doc({
        "doctype": "Comment",
        "comment_type": "Comment",
        "reference_doctype": "Individual Goal",
        "reference_name": goal_id,
        "content": content.strip(),
    })
    comment.insert(ignore_permissions=True)
    full_name = frappe.db.get_value("User", comment.owner, "full_name") or comment.owner
    return {"name": comment.name, "content": comment.content, "owner": comment.owner,
            "commenter_name": full_name, "creation": str(comment.creation)}


@frappe.whitelist()
@requires_feature("goals")
def get_goal_comments(goal_id):
    """Get comments for a goal."""
    emp = _get_employee()
    if not emp:
        frappe.throw("No employee record")
    goal_employee = frappe.db.get_value("Individual Goal", goal_id, "employee")
    roles = frappe.get_roles()
    is_hr = bool({"HR Manager", "HR User", "Administrator"} & set(roles))
    if goal_employee != emp.name and not is_hr:
        dr = frappe.db.get_value("Employee",
            {"name": goal_employee, "reports_to": emp.name, "status": "Active"},
            "name")
        if not dr:
            frappe.throw("Access denied", frappe.PermissionError)
    comments = frappe.get_all(
        "Comment",
        filters={"reference_doctype": "Individual Goal", "reference_name": goal_id, "comment_type": "Comment"},
        fields=["name", "content", "owner", "creation"],
        order_by="creation asc",
        limit=30,
        ignore_permissions=True,
    )
    if comments:
        unique_owners = list({c.owner for c in comments})
        user_rows = frappe.get_all(
            "User",
            filters={"name": ["in", unique_owners]},
            fields=["name", "full_name"],
            ignore_permissions=True,
        )
        name_map = {u.name: (u.full_name or u.name) for u in user_rows}
        for c in comments:
            c["commenter_name"] = name_map.get(c.owner, c.owner)
    return {"comments": comments}


@frappe.whitelist()
def get_manager_notes(employee_id=None, from_date=None, to_date=None):
    """Get manager's private notes. Scoped to own session user as owner."""
    import json as _json
    emp = _get_employee()
    if not emp:
        return {"notes": [], "employees": {}}
    is_hr = bool({"HR Manager", "HR User", "Administrator"} & set(frappe.get_roles()))
    if employee_id:
        dr = frappe.db.get_value("Employee",
            {"name": employee_id, "reports_to": emp.name, "status": "Active"}, "name")
        if not dr and not is_hr:
            frappe.throw("Access denied", frappe.PermissionError)
        ref_filter = {"reference_name": employee_id}
        emp_map = {employee_id: frappe.db.get_value("Employee", employee_id, "employee_name") or employee_id}
    else:
        reports = frappe.get_all("Employee",
            filters={"reports_to": emp.name, "status": "Active"},
            fields=["name", "employee_name"], ignore_permissions=True)
        if not reports:
            return {"notes": [], "employees": {}}
        ref_filter = {"reference_name": ["in", [r.name for r in reports]]}
        emp_map = {r.name: r.employee_name for r in reports}
    raw = frappe.get_all("Comment",
        filters=dict(reference_doctype="Employee", comment_type="Info",
                     owner=frappe.session.user, **ref_filter),
        fields=["name", "content", "creation", "modified", "reference_name"],
        order_by="creation desc", limit=200, ignore_permissions=True)
    result = []
    for n in raw:
        try:
            data = _json.loads(n.content)
        except Exception:
            continue  # skip non-JSON Info comments (not manager notes)
        if not data.get("_mgr"):
            continue  # skip Info comments not created by this portal
        nd = data.get("date", str(n.creation)[:10])
        if from_date and nd < from_date:
            continue
        if to_date and nd > to_date:
            continue
        result.append({
            "id": n.name,
            "employee_id": n.reference_name,
            "employee_name": emp_map.get(n.reference_name, n.reference_name),
            "date": nd,
            "text": data.get("text", ""),
            "created": str(n.creation)[:19],
            "modified": str(n.modified)[:19],
        })
    return {"notes": result, "employees": emp_map}


@frappe.whitelist()
def save_manager_note(employee_id, note_text, note_date, note_id=None):
    """Create or update a manager's private note."""
    import json as _json
    if not note_text or not note_text.strip():
        frappe.throw("Note text cannot be empty")
    emp = _get_employee()
    if not emp:
        frappe.throw("No employee record")
    is_hr = bool({"HR Manager", "HR User", "Administrator"} & set(frappe.get_roles()))
    dr = frappe.db.get_value("Employee",
        {"name": employee_id, "reports_to": emp.name, "status": "Active"}, "name")
    if not dr and not is_hr:
        frappe.throw("Access denied", frappe.PermissionError)
    content = _json.dumps({"_mgr": 1, "date": note_date, "text": note_text.strip()})
    if note_id:
        owner = frappe.db.get_value("Comment", note_id, "owner")
        if owner != frappe.session.user:
            frappe.throw("You can only edit your own notes", frappe.PermissionError)
        frappe.db.set_value("Comment", note_id, "content", content)
        frappe.db.commit()
        return {"id": note_id, "status": "updated"}
    doc = frappe.get_doc({
        "doctype": "Comment", "comment_type": "Info",
        "reference_doctype": "Employee", "reference_name": employee_id,
        "content": content,
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"id": doc.name, "status": "created"}


@frappe.whitelist()
def delete_manager_note(note_id):
    """Delete a manager's private note."""
    owner = frappe.db.get_value("Comment", note_id, "owner")
    if owner != frappe.session.user:
        frappe.throw("You can only delete your own notes", frappe.PermissionError)
    frappe.delete_doc("Comment", note_id, ignore_permissions=True)
    frappe.db.commit()
    return {"status": "deleted"}


@frappe.whitelist()
@requires_feature("goals")
def get_employee_goals_for_manager(employee_id):
    """Get all goals for a specific direct report or any employee accessible to HR."""
    if not frappe.db.exists("DocType", "Individual Goal"):
        return {"available": False, "goals": []}
    emp = _get_employee()
    if not emp:
        return {"available": True, "goals": []}
    is_hr = bool({"HR Manager", "HR User", "Administrator"} & set(frappe.get_roles()))
    dr = frappe.db.get_value("Employee",
        {"name": employee_id, "reports_to": emp.name, "status": "Active"}, "name")
    if not dr and not is_hr:
        return {"available": True, "goals": [], "access_denied": True}
    try:
        goals = frappe.get_all(
            "Individual Goal",
            filters={"employee": employee_id, "docstatus": ["!=", 2], "status": ["!=", "Cancelled"]},
            fields=["name", "goal_name", "trajectory", "progress_pct", "status", "docstatus",
                    "actual_progress", "target_value", "unit", "end_date"],
            order_by="trajectory asc, end_date asc",
            ignore_permissions=True,
        )
    except Exception:
        goals = []
    return {"available": True, "goals": goals}
