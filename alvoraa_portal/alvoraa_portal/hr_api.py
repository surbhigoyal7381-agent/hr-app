import re

import frappe
from frappe import _

from alvoraa_portal.attendance_analytics import LATE_GRACE_KEY
from alvoraa_portal.goals_api import current_cycle_name, goal_average, in_cycle
from alvoraa_portal.subscription import requires_feature
import calendar as _calendar
from frappe.utils import cint, flt, today, get_first_day, get_last_day, getdate, add_days, now
from alvoraa_goals.permissions import get_effective_manager
from hrms.alvoraa_hr_core.access import permitted_employee_filters
# A module import, not `from ... import`: the two switch KEYS are constants, and
# scripts/check_app_integrity.py only recognises functions and classes across apps.
import hrms.alvoraa_hr_core.features as org_features
from alvoraa_portal.frame_api import ME_FIELDS

# The Team screen's ceiling. Company-wide HR on a thousand-person tenant would
# otherwise draw a thousand cards and push a thousand ids into the attendance
# and leave queries below. The same 50 the Inbox uses (SEC-13, AC-72).
TEAM_LIST_CAP = 50


def me_block(row):
    """The caller's own six keys, cut from an Employee row already read.

    **The six names are `frame_api.ME_FIELDS` and they are not re-typed here**
    (045 AC-6). Wave 1 decided which fields describe the caller and named what
    must never join them - date_of_birth, gender, cell_number, date_of_joining,
    reports_to, branch. A second list in a second module is how the two come to
    disagree, and the disagreement is always in the direction of more.

    `_get_employee()` reads twelve fields because other callers need them. This
    takes the six, and the Employee id arrives as `name` and leaves as
    `employee`, so a payload never carries two things called name - the same
    rename `frame_api._me` does.

    Returns None when there is no Active record, which is persona rule 6.
    """
    if not row:
        return None
    src = dict(row)
    src["employee"] = src.get("name")
    return {k: src.get(k) for k in ME_FIELDS}


def direct_reports_query(emp_id):
    """This person's own Active direct reports, **as a subquery**.

    Never a list of ids read into Python and shipped back as an `IN (...)`.
    That shape is one statement, so the query count stays flat and nothing
    looks wrong, while the statement's cost grows with the company - slice 044
    measured a x5 slope on it and `nfr-budget.md` now bans it.

    Fails closed on a caller with no Employee id: `name IN ()` matches nobody
    in every Frappe query builder, and it is never an empty condition (SEC-4).
    """
    if not emp_id:
        return frappe.qb.get_query("Employee", fields=["name"],
                                   filters=[["name", "in", []]])
    return frappe.qb.get_query("Employee", fields=["name"],
                               filters={"reports_to": emp_id, "status": "Active"})


# The approval row's own fields, and the two that describe WHY somebody is off.
# Split into two names so that "what can this query return" is answerable by
# reading the query (045 AC-76e).
LEAVE_ROW_FIELDS = ("name", "employee", "employee_name", "department",
                    "from_date", "to_date", "total_leave_days")
LEAVE_WHY_FIELDS = ("leave_type", "description")


def _pending_leave_for_approver(user, emp_id):
    """Open leave requests this person approves, in **two reads**.

    The difference between the two reads is the whole of 045 AC-76.

    `leave_type` is the category - "Sick Leave". `description` is what the
    employee typed - "father in hospital" - and it is the more personal of the
    two, so a rule written about the category alone would leak the worse half
    and look like it had been followed.

    Both travel on ONE kind of row: the approval row for the caller's own
    direct report, where the caller is deciding that request and needs to know
    what they are deciding. Everywhere else, for everybody, **neither field is
    read at all**.

    **The case an engineer will meet, and the rule does not soften for it**
    (045 Q4a): an HR person who is the named `leave_approver` for somebody who
    is NOT their direct report decides that request **without seeing either
    field**. The decided rule is `reports_to`-based; the approval duty is
    `leave_approver`-based; the two do not always coincide. They see the dates,
    the days and the person - "why" stays withheld, in both its forms.

    **Two reads rather than one read and a blank-out afterwards**, because the
    fields must be absent from the `fields` list. A field removed after the
    query is a field that was read, and the next person to touch this function
    re-adds it to the payload without noticing they widened anything.
    """
    LA = frappe.qb.DocType("Leave Application")
    mine = ((LA.leave_approver == user) & (LA.status == "Open") & (LA.docstatus == 0))
    scope = direct_reports_query(emp_id)

    def _read(fields, own):
        cond = LA.employee.isin(scope) if own else LA.employee.notin(scope)
        q = frappe.qb.from_(LA).where(mine & cond).orderby(LA.creation)
        for f in fields:
            q = q.select(getattr(LA, f))
        rows = q.run(as_dict=True)
        for row in rows:
            row["is_own_report"] = own
        return rows

    return (_read(LEAVE_ROW_FIELDS + LEAVE_WHY_FIELDS, True)
            + _read(LEAVE_ROW_FIELDS, False))


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
        elif doc.doctype == "User":
            # Roles are edited through the USER form, and Frappe writes those child
            # rows with raw SQL - no Has Role document is ever loaded, so a hook on
            # that child doctype never fires. The user save is the only reliable
            # place to notice a role change.
            frappe.cache().delete_value(f"portal_ctx_{doc.name}")
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


def _ledger_leave_balances(employee, date_=None):
    """Leave per type from Frappe HR's leave ledger (slice 035, decision Q-e).

    The portal used to work leave out for itself: allocated minus approved Leave
    Applications. That missed every other kind of ledger entry - days the
    late-coming rule took, encashments, expiries - so on PP Jewellers 97 people
    were shown 76 days of Casual Leave they did not have, while the apply form's
    preview, the leave check and the late rule all read the ledger and said less.

    This is the figure Frappe HR's own screens show (get_leave_details), worked
    out the same way: get_leave_balance_on with
    consider_all_leaves_in_the_allocation_period, so leave already approved for
    later in the period counts as used.

    It calls Frappe HR's lower functions rather than get_leave_details or
    get_leave_balance_on, because those begin with validate_leave_access. That
    refuses a manager who is the reporting manager but not the named leave
    approver, and a store HR person whose desk read is branch-scoped - people the
    portal already lets see this figure. So EVERY CALLER MUST CHECK WHO MAY SEE
    THIS EMPLOYEE FIRST. test_leave_ledger_035 compares this with
    get_leave_balance_on, so an upstream change to that shape fails a test.

    Returns [{leave_type, total, taken, pending, balance}], sorted by leave type.
    """
    from hrms.hr.doctype.leave_application.leave_application import (
        get_allocation_expiry_for_cf_leaves,
        get_leave_allocation_records,
        get_leaves_for_period,
        get_leaves_pending_approval_for_period,
        get_manually_expired_leaves,
        get_remaining_leaves,
    )

    date_ = getdate(date_ or today())
    precision = cint(frappe.db.get_single_value("System Settings", "float_precision")) or 2
    rows = []
    for leave_type, alloc in sorted(get_leave_allocation_records(employee, date_).items()):
        start, end = alloc.from_date, alloc.to_date
        cf_expiry = get_allocation_expiry_for_cf_leaves(employee, leave_type, end, start)
        used = get_leaves_for_period(employee, leave_type, start, end)  # negative
        expired = get_manually_expired_leaves(employee, leave_type, start, end)
        balance = get_remaining_leaves(alloc, used, date_, cf_expiry, expired).leave_balance
        total = flt(alloc.total_leaves_allocated)
        taken = flt(-used)
        # Days that were allocated, not taken, and are gone anyway: carry
        # forward that lapsed, or an allocation expired by hand. Frappe HR's own
        # screen works it out the same way (get_leave_details). Without it
        # total - taken does not equal the balance, so a screen would say
        # "3 of 8 used" and "3 left" and leave the employee to wonder about the
        # other 2. Nothing on PP Jewellers expires today; a tenant that carries
        # leave forward will.
        lapsed = total - (balance + taken)
        rows.append({
            "leave_type": leave_type,
            "total": flt(total, precision),
            "taken": flt(taken, precision),
            "expired": flt(lapsed, precision) if lapsed > 0 else 0.0,
            "pending": flt(get_leaves_pending_approval_for_period(employee, leave_type, start, end),
                           precision),
            "balance": flt(balance, precision),
        })
    return rows


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
            return _with_review_count(cached)
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
    return _with_review_count(result)


def _with_review_count(context):
    """Slice 012: how many figures need review, for HR's menu badge (AC-31).

    Added around the cache, not inside it, so a confirmation shows on the next
    page load instead of up to an hour later. One permission-checked read, and
    only for HR: everybody else gets the context untouched.
    """
    if not context.get("is_hr"):
        return context
    from alvoraa_portal.data_review import open_count_for_hr

    return {**context, "review_open_count": open_count_for_hr()}


@frappe.whitelist()
def get_employee_dashboard():
    user = frappe.session.user
    emp = _get_employee(user)
    if not emp:
        return {"no_employee": True}

    td       = today()
    mo_start = get_first_day(td)

    # ── Leave balances: Frappe HR's ledger (slice 035) ───────────────────
    # The caller's own record, so no one else's figure can be reached here.
    leave_balances = []
    for b in _ledger_leave_balances(emp.name, td):
        total, taken = b["total"], b["taken"]
        leave_balances.append({
            "leave_type": b["leave_type"],
            "total":      total,
            "taken":      taken,
            "expired":    b["expired"],
            # The ledger's own figure, negative and all. A leave type set to
            # allow a negative balance can genuinely be below zero; clamping it
            # to 0 told the employee they had none left when they were two in
            # debt, and the leave gate would have said otherwise.
            "balance":    b["balance"],
            "color":      LEAVE_COLORS.get(b["leave_type"], "#64748b"),
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

    holidays, holiday_note = _own_upcoming_holidays(emp.name, td)

    return {
        "employee":        emp,
        "leave_balances":  leave_balances,
        "attendance":      att,
        "recent_leaves":   recent_leaves,
        "pending_approvals": pending,
        "holidays":        holidays,
        "holiday_note":    holiday_note,
        "month_days":      len(att_rows),
    }


def _own_upcoming_holidays(employee, date_):
    """The employee's own named holidays, this month to the end of their list.

    Slice 035. Home used to read EVERY holiday list on the site, so store staff
    at PP Jewellers were told Diwali, Dussehra, Guru Nanak Jayanti and Christmas
    were holidays - Head Office's, not theirs. It also stopped at 31 December,
    hiding January to March of an April-March list.

    The list is found exactly as payroll and leave find it: ERPNext's
    get_holiday_list_for_employee, which Frappe HR takes over through its
    employee_holiday_list hook and answers from Holiday List Assignment only
    (never Employee.holiday_list or the company default). So this card can
    never show a calendar that payroll ignores. When payroll has no list for
    this person, the card says so plainly - on a new tenant that is a setup gap
    HR must close, and a quiet empty card would hide it.

    Returns (holidays, note). note is None when a list was found.
    """
    # `holiday_list_for` is ERPNext's `get_holiday_list_for_employee` with a
    # memo that lives for one call and only when a call opened one (044 R1).
    # Home asks this question twice - the attendance-gap rule and this card -
    # for the same person on the same day. Every other caller behaves exactly
    # as before: with no memo open the lookup simply runs.
    from alvoraa_portal.call_cache import holiday_list_for

    holiday_list = holiday_list_for(employee, date_)
    if not holiday_list:
        return [], _("No holiday list is assigned to you yet. Ask HR to set one up.")

    list_end = frappe.db.get_value("Holiday List", holiday_list, "to_date")
    holidays = frappe.get_all(
        "Holiday",
        filters={
            "parent": holiday_list,
            "weekly_off": 0,
            "holiday_date": ["between", [get_first_day(date_), list_end]],
        },
        fields=["holiday_date", "description"],
        order_by="holiday_date asc",
        # No cap. This is one list's own named holidays now, not every list on
        # the site, so it is already small - and a cap here would silently drop
        # a real holiday off the end of the card. get_all is unlimited by default.
    )
    return holidays, None


@frappe.whitelist()
def get_manager_dashboard():
    user = frappe.session.user
    emp  = _get_employee(user)
    if not emp:
        return {"no_employee": True}

    fields = ["name", "employee_name", "designation", "department", "user_id", "image"]

    # Their own direct reports. Theirs whatever else they are.
    team = frappe.get_all(
        "Employee",
        filters={"reports_to": emp.name, "status": "Active"},
        fields=fields,
        ignore_permissions=True,
    )
    team_total = len(team)
    team_capped = False
    is_hr_scope = False

    # SEC-13 / AC-72 / W1D-20. For an HR caller the Team screen is their HR
    # SCOPE, not "everybody in the tenant who has no manager".
    #
    # What was here before added every Active employee in the tenant whose
    # reports_to was empty, with ignore_permissions and NO company or branch
    # filter, to anyone holding HR Manager or HR User. A store's HR person in
    # Ludhiana therefore saw head office and every other store's unassigned
    # people. That block is deleted, not filtered - the replacement is a scope,
    # which is a different question with a different answer.
    #
    # Three things this keeps, each of which would be a regression if dropped:
    #   * status = "Active" stays. permitted_employee_filters returns every
    #     status on purpose, so without this the screen would start listing
    #     leavers - WIDER than before, not narrower.
    #   * the caller's own record stays out, as it always was.
    #   * their direct reports stay in even when they fall outside their HR
    #     scope - an HR person for one company who manages somebody in another
    #     must not lose them off their own team screen.
    # And the list is capped, because company-wide HR on a thousand-person
    # tenant would otherwise draw a thousand cards and push a thousand ids into
    # the attendance query below. The true total goes with it, so the screen can
    # say what it is not showing (AC-72).
    roles = frappe.get_roles()
    if {"HR Manager", "HR User"} & set(roles):
        is_hr_scope = True
        scope = [[f, c[0], c[1]]
                 for f, c in permitted_employee_filters(user).items()]
        scope += [["status", "=", "Active"], ["name", "!=", emp.name]]

        scoped = frappe.get_all(
            "Employee", filters=scope, fields=fields,
            order_by="employee_name asc", limit=TEAM_LIST_CAP,
            ignore_permissions=True,
        )
        scoped_total = frappe.db.count("Employee", filters=scope)

        # The direct reports that the scope does not already cover. Asked of the
        # database rather than worked out here, so the scope rule has exactly one
        # definition (SEC-4).
        outside = []
        if team:
            covered = set(frappe.get_all(
                "Employee",
                filters=scope + [["name", "in", [t.name for t in team]]],
                pluck="name", ignore_permissions=True,
            ))
            outside = [t for t in team if t.name not in covered]

        team_total = scoped_total + len(outside)
        seen = {s.name for s in scoped}
        team = scoped + [t for t in outside if t.name not in seen]
        if len(team) > TEAM_LIST_CAP:
            team = team[:TEAM_LIST_CAP]
        team_capped = team_total > len(team)

    # Indirect reports (L2 only) - single query instead of one per manager.
    #
    # NOT for an HR caller (review finding F5, decided 2026-09-24).
    #
    # For a manager, "L2" means their own indirect reports and the word means
    # something. For an HR caller `team` is the first 50 people of their HR
    # scope in alphabetical order, so "the reports of those 50" is an arbitrary
    # set of people nobody asked for. It did three unhelpful things:
    #
    #   * it was the one UNCAPPED query on this screen. The notes claimed the
    #     cap "passes 50 ids to the queries below"; it did not - it passed 50
    #     plus all of their reports, and that list went into the attendance
    #     query, the raw-SQL IN (...) and the month-leaves query.
    #   * it put people who are NOT on the screen into the "Present" tile, the
    #     "on leave today" list and the month table. A number that does not
    #     match the list beside it is the exact fault AC-20 and AC-51 exist to
    #     stop.
    #   * nothing reads what it returns. `l2_reports` and `l2_size` have no
    #     consumer anywhere in this repository - not the portal, not the frame,
    #     not the mobile app.
    #
    # A manager's Team screen is untouched, which is where L2 earns its place.
    # For HR the screen now answers about exactly the people it is showing.
    l2 = []
    if team and not is_hr_scope:
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

    # Who is on leave today - PRESENCE ONLY.
    #
    # 045 AC-76 / PRIV-2 / D-1, and `01b` §14 rule 9: no screen shows a
    # colleague the reason for an absence. `leave_type` used to be selected
    # here. For a manager about their own report that was arguable - they
    # approve the request. W1D-20 then widened `team_ids` from a manager's
    # direct reports to an HR person's whole scope, up to 50 people, and the
    # leave type went with it. Nobody asked for that; it arrived with a scope
    # change. This takes it back.
    #
    # The field is gone from the SELECT, not from the renderer. A field
    # filtered in JavaScript is still in the response and still in the
    # browser's cache.
    # 045 AC-14, the second live instance of the banned shape. This was raw SQL
    # with one bound parameter per person - `employee IN (%s,%s,...)` built from
    # `team_ids`. For a company-wide HR caller that was up to fifty, and before
    # Wave 1 capped the list it was the whole tenant.
    #
    # **What this fix does and does not do, said plainly.** The raw SQL is
    # gone and `leave_type` is gone. The id list is NOT gone: it is now a
    # `filters={"employee": ["in", team_ids]}`, which is the same `IN (...)`
    # shape written in the query builder instead of by hand.
    #
    # That is a declared trade-off, not an oversight. AC-14 asks for a
    # subquery, and the reason a subquery cannot simply be dropped in here is
    # that this read must match the list the screen DRAWS, which is capped at
    # TEAM_LIST_CAP - a subquery over the caller's scope would count people who
    # are not on the page, and a number that does not equal the list beside it
    # is the fault AC-12 exists to stop. MariaDB's support for `LIMIT` inside
    # an `IN (SELECT ...)` is not something to build a privacy-relevant read
    # on.
    #
    # The list is bounded at fifty by construction, so the x5 slope slice 044
    # measured cannot appear here. **AC-14's subquery lands with the Team
    # rewrite**, where `direct` and `covered` are each their own scope with
    # their own count and the question "which list must this equal" has an
    # answer. This function is replaced there.
    on_leave_today = []
    if team_ids:
        on_leave_today = frappe.get_all(
            "Leave Application",
            filters={"employee": ["in", team_ids], "docstatus": 1,
                     "status": "Approved",
                     "from_date": ["<=", td], "to_date": [">=", td]},
            fields=["employee", "employee_name"],
            ignore_permissions=True,
        )

    # Pending leave approvals, in TWO reads, and the difference between them is
    # the whole of AC-76.
    #
    # `leave_type` is the category - "Sick Leave". `description` is what the
    # employee typed - "father in hospital" - and it is the more personal of
    # the two, so a rule written about the category alone would leak the worse
    # half and look like it had been followed.
    #
    # Both travel on ONE row only: the approval row for the caller's OWN direct
    # report, where the caller is deciding that request and needs to know what
    # they are deciding. Everywhere else, for everybody, neither field is read.
    #
    # The case an engineer will meet, and the rule does not soften for it
    # (045 Q4a): an HR person who is the named `leave_approver` for somebody who
    # is NOT their direct report decides that request WITHOUT seeing either
    # field. The decided rule is reports_to-based; the approval duty is
    # leave_approver-based; the two do not always coincide. They see the dates,
    # the days and the person - "why" stays withheld, in both its forms.
    #
    # Two reads rather than one read and a blank-out in Python: the fields must
    # be absent from the `fields` list, not removed after the fact, so that
    # "what can this query return" is answerable by reading the query.
    pending = _pending_leave_for_approver(user, emp.name)

    # Approved leaves that TOUCH this month.
    #
    # 045 AC-21. This asked `from_date >= mo_start`, which is not the question
    # the card asks. Two ways it was wrong, and it has been wrong since it was
    # written (Appendix D B18/TM-05):
    #
    #   * leave that BEGAN last month and is still running was missing. Somebody
    #     off from 28 August to 3 September did not appear on the September
    #     card at all, which is the person a manager most needs to see.
    #   * leave that starts NEXT month was included. A request for 2-4 October
    #     appeared on the September card.
    #
    # The right test is overlap: it starts on or before the last day of the
    # month AND ends on or after the first. Still one query.
    #
    # `leave_type` is also gone from the `fields` list - AC-76. This is a card,
    # not an approval row, so it carries presence and dates and nothing about
    # why.
    mo_start = get_first_day(td)
    mo_end = get_last_day(td)
    month_leaves = []
    if team_ids:
        month_leaves = frappe.get_all(
            "Leave Application",
            filters={"employee": ["in", team_ids], "docstatus": 1,
                     "status": "Approved",
                     "from_date": ["<=", mo_end], "to_date": [">=", mo_start]},
            fields=["employee_name", "from_date", "to_date", "total_leave_days"],
            order_by="from_date asc",
            ignore_permissions=True,
        )

    return {
        # 045 AC-6 / US-12. This was `"manager": emp` - the WHOLE Employee row
        # that `_get_employee()` reads, which carries date_of_birth, gender,
        # cell_number, branch, date_of_joining and reports_to. Every browser
        # that drew a Team screen was handed all of them, and nothing on the
        # screen ever used one. The key is renamed as well as narrowed: this
        # block describes the CALLER, and calling it "manager" is what made a
        # whole record look like a reasonable thing to put there.
        "me":              me_block(emp),
        "team":            team,
        "today_att":       today_att,
        "on_leave_today":  on_leave_today,
        "pending_approvals": pending,
        "month_leaves":    month_leaves,
        "team_size":       len(team),
        # What the list really holds, and what it would hold uncapped. The
        # screen must say so when they differ: a count that does not match the
        # list beside it is worse than no count.
        "team_total":      team_total,
        "team_capped":     team_capped,
        # Whether this list is an HR scope or a manager's own reports, so the
        # screen can name what it is showing instead of calling every row a
        # "direct report" when most of them are not.
        "is_hr_scope":     is_hr_scope,
        "team_cap":        TEAM_LIST_CAP,
        # 045 AC-16 / US-16. `l2_reports` and `l2_size` are GONE. Wave 1
        # recorded at hr_api.py:441-460 that nothing reads them, and a grep
        # across alvoraa_portal, alvoraa_goals, hrms and mobile/ on this branch
        # agrees: the only reader anywhere was Wave 1's own test asserting they
        # were empty. A payload key nobody reads cannot grow a reader later if
        # it is not there.
        #
        # `l2` itself is still worked out for a manager, because it still feeds
        # `team_ids` and so the presence and leave reads. That is the remaining
        # question - a person in team_ids who is not drawn on the screen makes a
        # count disagree with its list - and it belongs to the Team rewrite and
        # its per-section counts (AC-12, AC-74), not to this deletion.
    }


# POST only, and never stored by a browser or proxy: the answer carries the names,
# roles and joining dates of people due confirmation and of the newest joiners (F4).
# The portal asks through frappe.call, which posts.
@frappe.whitelist(methods=["POST"])
@requires_feature("analytics")
def get_hr_analytics():
    # Role AND plan. The role says this person may see analytics; the feature
    # says this tenant bought them. Hiding the nav item stopped neither a URL
    # nor a fetch() from reaching here.
    roles = frappe.get_roles()
    if not ({"HR Manager", "HR User", "Administrator"} & set(roles)):
        frappe.throw("Access denied", frappe.PermissionError)

    # Slice 012 G1 (SEC-16): every figure and name below is limited to the
    # caller's companies, and to their branches when they are location HR. It
    # used to cover the whole tenant - a store's HR person saw every store's and
    # every company's names, gender and joining dates. Attendance and leave come
    # from the one calculation the leader view uses (org_figures.py).
    import time as _time
    from alvoraa_portal import data_review, org_figures as of

    started = _time.monotonic()
    try:
        frappe.local.response_headers.set("Cache-Control", "no-store")
    except Exception:
        pass
    scope = of.hr_scope()
    if scope.not_linked:
        # Fail closed: no company, no figures and no names (BA-Q5). The page
        # explains how to get linked.
        return {"not_linked": True}

    td       = getdate(today())
    mo_start = get_first_day(td)
    mo_end   = get_last_day(td)

    # ── Headcount ─────────────────────────────────────────────────────────
    people = of.people_figures(scope, td, mo_start, mo_end)
    emp_where, emp_params = of.employee_condition(scope)
    scope_filters = {"company": ["in", list(scope.companies)]}
    if scope.branches is not None:
        scope_filters["branch"] = ["in", list(scope.branches)]

    # ── Department distribution ───────────────────────────────────────────
    dept_dist = frappe.db.sql(f"""
        SELECT e.department, COUNT(*) AS count
        FROM `tabEmployee` e WHERE e.status = 'Active' AND e.department IS NOT NULL AND {emp_where}
        GROUP BY e.department ORDER BY count DESC
    """, emp_params, as_dict=True)

    # ── Gender ratio ─────────────────────────────────────────────────────
    gender_dist = frappe.db.sql(f"""
        SELECT COALESCE(NULLIF(e.gender,''),'Not Specified') AS gender, COUNT(*) AS count
        FROM `tabEmployee` e WHERE e.status = 'Active' AND {emp_where}
        GROUP BY gender
    """, emp_params, as_dict=True)

    # ── Location / Branch ────────────────────────────────────────────────
    loc_dist = frappe.db.sql(f"""
        SELECT COALESCE(NULLIF(e.branch,''),'HQ') AS location, COUNT(*) AS count
        FROM `tabEmployee` e WHERE e.status = 'Active' AND {emp_where}
        GROUP BY location ORDER BY count DESC
    """, emp_params, as_dict=True)

    # ── Monthly joiners (last 6 months) ──────────────────────────────────
    joiners_trend = frappe.db.sql(f"""
        SELECT DATE_FORMAT(e.date_of_joining,'%%b %%Y') AS month,
               DATE_FORMAT(e.date_of_joining,'%%Y-%%m') AS sort_key,
               COUNT(*) AS count
        FROM `tabEmployee` e
        WHERE e.date_of_joining >= %(six_months_ago)s AND {emp_where}
        GROUP BY month, sort_key ORDER BY sort_key
    """, {**emp_params, "six_months_ago": add_days(td, -180)}, as_dict=True)

    # ── Attendance: the month of the last day with data (decision D-13) ──
    period = of.period(scope)
    # No late arrivals, short days or people count: this screen shows none of them,
    # and asking for them costs two joins and a distinct count over the month.
    att = of.attendance_figures(scope, *period, detail=False) if period else dict(of.NO_ATTENDANCE)
    att_rate = att["rate"]
    present = att["present"] + att["wfh"] + att["half"] * 0.5
    absent = att["absent"]

    # ── Leave used this leave year, per company ──────────────────────────
    leave = of.leave_figures(scope, td)

    # ── Pending approvals ─────────────────────────────────────────────────
    pending_filters = {"status": "Open", "docstatus": 0, "company": ["in", list(scope.companies)]}
    if scope.branches is not None:
        pending_filters["alvoraa_branch"] = ["in", list(scope.branches)]
    pending_count = frappe.db.count("Leave Application", pending_filters)

    # ── Confirmations due this month ─────────────────────────────────────
    # get_list: the caller's own User Permissions apply as well as the scope.
    confirmations = frappe.get_list(
        "Employee",
        filters={
            "scheduled_confirmation_date": ["between", [mo_start, mo_end]],
            "status": "Active",
            **scope_filters,
        },
        fields=["name", "employee_name", "designation", "department", "date_of_joining", "scheduled_confirmation_date"],
        limit_page_length=500,
    )

    # ── Department-wise leave, each company's own leave year ─────────────
    year_or, year_params = [], {}
    for i, (company, figs) in enumerate(sorted(leave["by_company"].items())):
        year_params.update({f"lc{i}": company, f"lys{i}": figs["year_start"], f"lye{i}": figs["year_end"]})
        year_or.append(f"(la.company = %(lc{i})s AND la.from_date BETWEEN %(lys{i})s AND %(lye{i})s)")
    dept_leave = frappe.db.sql(f"""
        SELECT e.department, COALESCE(SUM(la.total_leave_days),0) AS taken
        FROM `tabEmployee` e
        LEFT JOIN `tabLeave Application` la
            ON la.employee = e.name AND la.docstatus=1 AND la.status='Approved'
           AND ({' OR '.join(year_or) or '1=0'})
        WHERE e.status='Active' AND e.department IS NOT NULL AND {emp_where}
        GROUP BY e.department ORDER BY taken DESC
    """, {**emp_params, **year_params}, as_dict=True)

    # ── Designation distribution ─────────────────────────────────────────
    desig_dist = frappe.db.sql(f"""
        SELECT COALESCE(NULLIF(e.designation,''),'Not Set') AS designation, COUNT(*) AS count
        FROM `tabEmployee` e WHERE e.status='Active' AND {emp_where}
        GROUP BY designation ORDER BY count DESC LIMIT 10
    """, emp_params, as_dict=True)

    # ── Recent employee list (for lifecycle tab) ──────────────────────────
    recent_employees = frappe.get_list(
        "Employee",
        filters={"status": "Active", **scope_filters},
        # No gender: the screen shows name, role, team and joining date, and nothing
        # else reads this list. The gender ratio above is counts, not people (F3).
        fields=["name", "employee_name", "designation", "department", "date_of_joining"],
        order_by="date_of_joining desc",
        limit_page_length=10,
    )

    review = data_review.review_summary(scope)
    of.log_if_slow("get_hr_analytics", scope, started)

    return {
        "not_linked": False,
        "scope": {"kind": scope.kind, "companies": len(scope.companies),
                  "branches": len(scope.branches) if scope.branches is not None else None},
        "data_up_to": str(period[1]) if period else None,
        "period": {"from": str(period[0]), "to": str(period[1])} if period else None,
        "review": review,
        "headcount": {
            "active":      people["active"],
            "total":       people["total"],
            "new_joiners": people["joiners"],
        },
        "dept_distribution":    dept_dist,
        "gender_distribution":  gender_dist,
        "location_distribution": loc_dist,
        "joiners_trend":        joiners_trend,
        "desig_distribution":   desig_dist,
        "kpis": {
            # None, not 0, when there is nothing to divide: "No figures yet".
            "attendance_rate":      att_rate,
            "leave_utilization":    leave["used_pct"],
            "pending_approvals":    pending_count,
            "total_leave_taken":    float(leave["taken"]),
            "total_leave_allocated": float(leave["allocated"]),
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


def _leave_approver_for(doc):
    """Who Frappe HR says may approve this - the employee's approver, or their
    department's. Exactly the rule get_leave_approver() applies when it fills the
    field in the first place, so the portal cannot disagree with the desk."""
    if doc.leave_approver:
        return doc.leave_approver
    try:
        # ALV-173. The UNGUARDED helper, deliberately. `get_leave_approver` is
        # the web entry point and now refuses anyone who is not the employee,
        # their approver, or someone with read access to them. This call runs
        # server-side inside our own already-checked endpoint, and it asks a
        # question ABOUT a third party on purpose: "who is allowed to approve
        # this?". Going through the web guard would make the `except` below
        # swallow a PermissionError and return None, and the caller would then
        # tell HR that no approver is set when one is.
        from hrms.hr.doctype.leave_application.leave_application import (
            get_employee_leave_approver,
        )

        return get_employee_leave_approver(doc.employee)
    except Exception:
        return None


def _can_action_leave(name, doc=None):
    """May the CURRENT user approve or reject this application?

    ONE rule, used by the button and by the action, because a button that offers
    something the action then refuses is worse than no button - it turns a
    configuration problem into what looks like a broken product.

    The rule is Frappe HR's own: approving is the NAMED APPROVER's job. The
    approver is a property of the employee or their department, not something a
    role confers. This portal used to let any HR Manager approve anybody's leave;
    that was ours, it is not how Frappe HR works, and it made the audit trail
    meaningless - "approved by whoever held HR Manager" is not "approved by the
    person responsible".

    Frappe's own permission check still has to pass on top: being named approver
    does not help if the document is out of reach for another reason.
    """
    try:
        doc = doc or frappe.get_doc("Leave Application", name)
    except Exception:
        return False

    # Never your own leave, even when you are named as your own approver.
    from hrms.alvoraa_hr_core.access import is_own_record
    if is_own_record(doc.employee):
        return False

    if frappe.session.user != _leave_approver_for(doc):
        return False

    return bool(frappe.has_permission("Leave Application", "submit", doc=doc))


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

    # Nobody approves or rejects their own leave, even when HR Settings would
    # allow it (SEC-9). Checked first, so the message says why.
    from hrms.alvoraa_hr_core.access import refuse_own_decision
    refuse_own_decision(doc.employee, "Leave Application", doc.name, "hr_api.action_leave")

    # The same rule the button uses. No role bypass: holding HR Manager does not
    # make somebody the approver, and Frappe HR does not treat it as though it
    # does.
    if not _can_action_leave(None, doc=doc):
        approver = _leave_approver_for(doc)
        if not approver:
            frappe.throw(
                _("No leave approver is set for {0}. HR should name one on the "
                  "employee record, or add a Leave Approver to their department, "
                  "before this request can be actioned.").format(
                      doc.employee_name or doc.employee),
                frappe.PermissionError)
        frappe.throw(
            _("Only {0} can action this request - they are the approver for {1}.").format(
                approver, doc.employee_name or doc.employee),
            frappe.PermissionError)

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


# Review stages from which an overall rating is released to the employee, and so
# may show on screens outside the review (slice 010 group D, decision 3).
_REVIEW_RATING_RELEASED = ("Employee Final Review", "HR Review", "Completed")


@frappe.whitelist()
def get_employee_scorecard(employee_id):
    """Comprehensive scorecard for one employee — for manager view."""
    mgr_emp = _get_employee()
    if not mgr_emp:
        frappe.throw("No employee record found for current user")

    roles = frappe.get_roles()
    is_hr = bool({"HR Manager", "HR User", "Administrator"} & set(roles))
    effective_mgr = get_effective_manager(employee_id)
    if effective_mgr != mgr_emp.name:
        if not is_hr:
            frappe.throw("Access denied", frappe.PermissionError)
        # HR opens only employees of the companies they look after (slice 010
        # group D, decision 28). It used to open any company's employee: contact
        # details, attendance, leave and appraisal history.
        _hr_target_employee(employee_id, "hr_api.get_employee_scorecard")

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

    # Leave balances: Frappe HR's ledger (slice 035). Access to this employee
    # was checked at the top of this function.
    leave_balances = [
        {"leave_type": b["leave_type"], "allocated": b["total"],
         "taken": round(b["taken"], 1), "expired": b["expired"],
         "balance": b["balance"]}
        for b in _ledger_leave_balances(employee_id, td)
    ]

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
            fields=["name", "goal_name", "progress_pct", "status", "trajectory", "appraisal_cycle"],
            order_by="creation desc", limit=30,
            ignore_permissions=True,
        )
        # The current cycle's goals first (slice 035), so a finished quarter's
        # 100% does not sit at the top of this quarter's list. Newest first
        # within each group, as before; still 15 at most.
        cycle = current_cycle_name(frappe.db.get_value("Employee", employee_id, "company"))
        # This quarter's goals, and undated ones, before older quarters'.
        goals.sort(key=lambda g: bool(cycle) and bool(g.get("appraisal_cycle"))
                   and g["appraisal_cycle"] != cycle)
        for g in goals:
            g.pop("appraisal_cycle", None)   # ordering only; not sent to the page
        goals = goals[:15]

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
            # A rating and its score show outside the review only once released
            # to the employee (slice 010, decision 3 / PRIV-1). Before that the
            # scorecard says where the review is, not what it says.
            released = r.review_status in _REVIEW_RATING_RELEASED
            appraisal_history.append({
                "cycle_label": (r.cycle_label or "—"),
                "review_status": r.review_status or "",
                "overall_rating": (r.overall_rating or "") if released else "",
                "score": float(r.score or 0) if released else 0,
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
        fields=["name", "employee_name", "designation", "company"],
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

    # Goals per team member: their company's current cycle only (slice 035).
    # This used to average every goal the person ever had, so the comparison
    # chart managers rate beside blended last quarter into this one.
    goals_by_emp = {}
    if frappe.db.exists("DocType", "Individual Goal"):
        cycles = {c: current_cycle_name(c) for c in {m.company for m in team}}
        cycle_of = {m.name: cycles.get(m.company) for m in team}
        goal_rows = frappe.get_all(
            "Individual Goal",
            filters={"employee": ["in", emp_ids], "docstatus": ["!=", 2]},
            fields=["employee", "appraisal_cycle", "progress_pct", "status", "weightage"],
            ignore_permissions=True,
        )
        rows_by_emp = {}
        # in_cycle is goals_api's one rule - this quarter's goals plus goals
        # that belong to no quarter. A second copy of it here is how the team
        # list and this chart came to disagree in the first place.
        for g in in_cycle(goal_rows, cycle_of):
            if g.status == "Cancelled":
                # Dropped here rather than only from the average: counted in
                # "total" but not in "avg", the two numbers on one card
                # described different sets of goals.
                continue
            rows_by_emp.setdefault(g.employee, []).append(g)
        for e, rows in rows_by_emp.items():
            goals_by_emp[e] = {
                "total": len(rows),
                "completed": sum(1 for g in rows if g.status == "Completed"),
                # One decimal, the same as the team goals list (slice 035,
                # takeover review). Rounded to whole numbers here and to one
                # decimal there, two manager screens printed 67 and 66.7 for
                # one person's goals.
                "avg": round(goal_average(rows), 1),
            }

    # Latest released appraisal score per team member.
    #
    # 045 AC-14. Three things were wrong with the statement this replaces, and
    # they were wrong together:
    #
    #   * **the scope was an `IN (...)` with one bound parameter per person.**
    #     That is one statement, so the query count stayed flat and nothing
    #     looked wrong, while the statement's cost grew with the company.
    #     Slice 044 measured a x5 slope on this shape and `nfr-budget.md` now
    #     bans it. The scope goes into the database as a subquery instead, and
    #     the statement is the same size for four reports as for four hundred.
    #   * **`ORDER BY ae.creation DESC` with no `LIMIT`.** Every extension row
    #     every report ever had came back, sorted, so a team that had been
    #     through twelve cycles fetched twelve times the rows needed.
    #   * **the privacy filter ran in Python**, so unreleased ratings were read
    #     out of the database and into this process before being dropped. The
    #     `review_status` test is the whole of slice 010's PRIV-1, and a filter
    #     that runs after the read is a filter that the next refactor forgets.
    #     It is now in the `WHERE`: an unreleased rating is never fetched.
    #
    # The correlated `MAX(creation)` is what makes it one row per person rather
    # than all of them sorted - the same answer the Python loop was working out
    # by taking the first of each employee it met.
    score_by_emp = {}
    if frappe.db.exists("DocType", "Alvoraa Appraisal Extension"):
        # .format() only inserts "%s" placeholders and a fixed-length list of
        # them for the three released statuses — no user data, and no
        # per-person placeholder, in the format string.
        released = ",".join(["%s"] * len(_REVIEW_RATING_RELEASED))
        rows = frappe.db.sql("""
            SELECT ae.employee, ae.overall_rating, a2.total_score AS score
            FROM `tabAlvoraa Appraisal Extension` ae
            LEFT JOIN `tabAppraisal` a2 ON a2.name = ae.name
            WHERE ae.employee IN (
                    SELECT e.name FROM `tabEmployee` e
                    WHERE e.reports_to = %s AND e.status = 'Active')
              AND ae.docstatus != 2
              AND ae.review_status IN ({released})
              AND ae.creation = (
                    SELECT MAX(x.creation) FROM `tabAlvoraa Appraisal Extension` x
                    WHERE x.employee = ae.employee
                      AND x.docstatus != 2
                      AND x.review_status IN ({released}))
        """.format(released=released),
            (mgr_emp.name,) + tuple(_REVIEW_RATING_RELEASED)
            + tuple(_REVIEW_RATING_RELEASED),
            as_dict=True,
        )
        for r in rows:
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
    if emp_reports_to != mgr_emp.name:
        if not is_hr:
            frappe.throw("Access denied", frappe.PermissionError)
        # The same hole as get_employee_scorecard, closed the same way (decision 28).
        _hr_target_employee(employee_id, "hr_api.get_employee_detail_for_manager")

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

    # Leave balances: Frappe HR's ledger (slice 035). Access to this employee
    # was checked at the top of this function.
    leave_balances = [
        # No "expired" here: this screen shows allocated and balance only, so
        # the figure has nothing to reconcile and a manager does not need it.
        # Adding a field to a screen the slice did not ask for is a visibility
        # change, even when the field is harmless.
        {"leave_type": b["leave_type"], "allocated": b["total"],
         "balance": b["balance"]}
        for b in _ledger_leave_balances(employee_id, td)
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

    # frappe.has_permission returns a bool and takes no `raise_exception`. It
    # was called with one, which raised TypeError, which the except swallowed -
    # so both of these were False for every user on every tenant, and the two
    # sidebar items they gate were permanently invisible. The except is kept for
    # a doctype an app has not installed; it no longer hides our own mistakes.
    try:
        features["attendance_request"] = bool(
            frappe.has_permission("Attendance Request", "create")
        )
    except Exception:
        features["attendance_request"] = False

    try:
        features["advance_request"] = bool(
            frappe.has_permission("Employee Advance", "create")
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

    # Organisation switches (26 Sep 2026). Not plan entitlements: HR turns them on
    # in Organisation Settings. Read live, never from the cached block above, so
    # a switch HR just changed shows on the next page load.
    features["org_late_rules"] = org_features.late_rules_on()
    features["org_attendance_scoring"] = org_features.attendance_scoring_on()

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
        # Tells the page whether to ask the browser for a position before it
        # calls do_checkin. Sent with the status so the button knows before it
        # is ever pressed, rather than finding out from a failure.
        "needs_location": checkin_needs_location(),
    }


def checkin_needs_location():
    """Whether this organisation records where a check-in happened.

    Frappe HR refuses a check-in with no coordinates whenever
    `allow_geolocation_tracking` is on, so the page has to ask the browser for
    a position BEFORE it calls. Asked per tenant rather than always: a browser
    location prompt is an intrusion, and there is no reason to show it to
    somebody whose employer does not record this.
    """
    try:
        return bool(frappe.db.get_single_value("HR Settings", "allow_geolocation_tracking"))
    except Exception:
        return False


@frappe.whitelist()
def do_checkin(log_type, latitude=None, longitude=None):
    if log_type not in ("IN", "OUT"):
        frappe.throw("Invalid log_type")
    emp = _get_employee()
    if not emp:
        frappe.throw("No employee record found for this user")

    # Said here, in words about this screen, rather than letting Frappe HR's
    # "Latitude and longitude values are required for checking in." reach
    # somebody who has no idea what a latitude is or why one is wanted.
    if checkin_needs_location() and latitude in (None, "") and longitude in (None, ""):
        frappe.throw(
            "Your organisation records where check-ins happen, so this needs "
            "your location. Allow location access for this site in your browser, "
            "then try again."
        )

    doc = frappe.get_doc({
        "doctype": "Employee Checkin",
        "employee": emp.name,
        "employee_name": emp.employee_name,
        "log_type": log_type,
        "time": now(),
        "device_id": "web-portal",
        # Stored against this one moment. The portal asks the browser at the
        # instant somebody presses the button and never between times - there
        # is no continuous tracking anywhere in this product.
        "latitude": flt(latitude) if latitude not in (None, "") else None,
        "longitude": flt(longitude) if longitude not in (None, "") else None,
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


# ── The one sentence every payslip refusal gives ─────────────────────────────
#
# 043 AC-31. Four different causes, one sentence, byte for byte:
#
#   1. the slip belongs to somebody else
#   2. the slip does not exist
#   3. the slip is still a draft
#   4. the tenant never bought payroll
#
# A refusal that varies is an oracle. "Payroll is not included in your plan."
# tells the caller what the tenant bought; "That payslip is not available."
# told for cause 1 and a different sentence for cause 4 lets somebody walk a
# list of slip names and learn which tenants run payroll and whose slips exist.
#
# It is a module constant rather than four copies of the literal so that
# changing one of them is impossible. There is no translation catalogue in this
# app yet (Hindi and Punjabi are Wave 5), so nothing is lost by the extractor
# not seeing a literal here; when the catalogue arrives this string goes into it
# by hand, once, which is the point of there being one of it.
PAYSLIP_UNAVAILABLE = "That payslip is not available."


# ── The only Employee fields that leave a Wave 3 payload ─────────────────────
#
# 043 AC-6, and Wave 1's biggest finding, live until this commit.
#
# `get_payslips` returned `{"payslips": [...], "employee": emp}` where `emp` is
# `_get_employee()`'s WHOLE row: date_of_birth, gender, cell_number, branch,
# reports_to and date_of_joining along with the rest. That is the payload behind
# the screen people screenshot and attach to a support ticket, and send to a
# bank. Nothing on the screen ever read it - `portal.js:2593` uses
# `data.payslips` and nothing else - so seven fields of the most sensitive data
# in the product travelled on every Pay load for no reason at all.
#
# The same six fields Wave 1 fixed on the frame (`frame_api.ME_FIELDS`), and the
# same discipline: a FIXED KEY LIST, so adding a field is a decision somebody
# makes on purpose rather than something that arrives by passing a row through.
ME_FIELDS = ("employee", "employee_name", "designation", "department", "image", "company")


def _me_block(emp):
    """The six-key `me` block, built key by key from an Employee row.

    Deliberately not `{k: emp[k] for k in ME_FIELDS}` over a row - the point is
    that this function names what it returns, so a reviewer reads the payload
    here rather than working out what `_get_employee` happens to select today.
    """
    if not emp:
        return None
    return {
        "employee": emp.name,
        "employee_name": emp.employee_name,
        "designation": emp.designation,
        "department": emp.department,
        "image": emp.image,
        "company": emp.company,
    }


@frappe.whitelist()
@requires_feature("payroll", message=PAYSLIP_UNAVAILABLE)
def get_payslips():
    """The caller's own submitted payslips.

    The gate is 043 AC-30 / ALV-114. This endpoint carried `@frappe.whitelist()`
    and nothing else while `get_payslip` and `download_payslip` beside it both
    carried `@requires_feature("payroll")`. W1D-01 hides the salary parts of the
    menu on a tenant without payroll, and a hidden menu is not a permission: the
    list behind it answered anyone who called it by hand, so the entitlement
    claim was false for as long as it shipped.

    ORDER, and a correction to the spec. 043 AC-30(c) asks for
    `@requires_feature` to sit textually ABOVE `@frappe.whitelist()`. Written
    that way the endpoint stops working altogether, for everybody, on every
    tenant. `frappe.whitelist()` does `whitelisted.add(fn)` on the object it is
    handed (frappe/__init__.py:465) and `is_whitelisted` tests the object the
    module name resolves to (:483). Put the gate outermost and the module name
    resolves to the gate's wrapper, which was never added, so every call is
    refused with "You are not permitted to access this resource."

    So the order here is `@frappe.whitelist()` then `@requires_feature(...)` -
    byte for byte the order `get_payslip` and `download_payslip` already use.
    The gate still runs before the body, which is what the requirement is
    actually about. The check that enforces it asserts SAMENESS with the two
    endpoints beside it rather than a fixed line order.
    """
    emp = _get_employee()
    if not emp:
        return {"no_employee": True}
    return {"payslips": _own_slips(emp.name), "me": _me_block(emp)}


# The fields the payslip LIST carries. `rounded_total` joined them in 043: the
# Pay screen calls the rounded figure the take-home (§20 D-2), because that is
# what the bank paid, and a list that carried only `net_pay` would disagree
# with the hero above it by a rupee on 555 of PP Jewellers' 800 slips.
SLIP_LIST_FIELDS = ("name", "posting_date", "start_date", "end_date",
                    "gross_pay", "total_deduction", "net_pay", "rounded_total",
                    "currency")

# Twelve months. A year of slips is what a person needs to show a bank, and an
# uncapped read of a long-serving employee's whole history is a list nobody
# scrolls.
SLIP_LIST_LIMIT = 12


def _own_slips(employee):
    """The employee's own submitted payslips, newest first.

    **Why the flag is here and not in `pay_api`.** The Employee role no longer
    holds read on Salary Slip at all - that permission was a back door, because
    wherever the narrowing User Permission was wider or missing, other people's
    pay showed. So every payslip read in this product is an ownership check
    followed by a deliberate `ignore_permissions`, and that pattern is declared
    and tested HERE, in `hr_api`. 043 AC-43 forbids the flag in `time_api.py`
    and `pay_api.py` outright, so the Pay screen calls this rather than
    carrying a second copy of the query - which also means the list and the
    payslip page can never disagree about which slips exist.

    The ownership check is the filter itself: `employee` is resolved from the
    session by the caller, never taken from the browser. A cancelled slip
    (`docstatus 2`) is excluded here, which is what keeps it off the screen and
    out of the download (043 AC-53).
    """
    return frappe.get_all(
        "Salary Slip",
        filters={"employee": employee, "docstatus": 1},
        fields=list(SLIP_LIST_FIELDS),
        # Newest PERIOD first, with the posting date only breaking a tie. Two
        # slips posted on the same day - a re-run, or a correction - would
        # otherwise come back in an order the database chose, and the Pay
        # screen reads slips[0] as "the latest".
        order_by="start_date desc, posting_date desc",
        limit=SLIP_LIST_LIMIT,
        ignore_permissions=True,
    )


# ── One payslip, shown in the portal ─────────────────────────────────────────
#
# Employees used to open a payslip in the desk, at /app/salary-slip/<name>. That
# needed the Employee role to hold READ on Salary Slip - and that permission was
# a back door. The Employee role's read is meant to be narrowed to the person's
# own records by a User Permission, so wherever that permission is wider or
# missing, other people's pay showed: a floor manager, whose permission covers
# his reporting line, could open all 18 of his team's payslips, and head-office
# HR staff with no User Permission could open every one of 400.
#
# So the Employee role no longer reads payroll records at all, and the portal
# shows the payslip itself. Ownership is therefore the WHOLE check, and it lives
# here, on the server, before anything is returned.

def _own_payslip(name):
    """The caller's own submitted salary slip, or a refusal.

    The refusal is identical whether the slip belongs to somebody else, is a
    draft, or does not exist - so a slip name cannot be used to find out whose
    payslips exist.
    """
    emp = _get_employee()
    row = None
    if name and isinstance(name, str):
        row = frappe.db.get_value("Salary Slip", name, ["name", "employee", "docstatus"], as_dict=True)
    if not emp or not row or row.docstatus != 1 or row.employee != emp.name:
        frappe.throw(frappe._(PAYSLIP_UNAVAILABLE), frappe.PermissionError)
    return frappe.get_doc("Salary Slip", row.name)


@frappe.whitelist()
@requires_feature("payroll", message=PAYSLIP_UNAVAILABLE)
def get_payslip(name):
    """One of the caller's own payslips, for the portal to draw."""
    return _payslip_payload(_own_payslip(name))


def _payslip_payload(slip):
    """One payslip's payload, in ONE place.

    043: Wave 3's Pay screen shows the newest slip in full on the first load,
    so two callers now build this - `get_payslip` and `pay_api.get_pay`. Two
    copies would drift, and the one that drifts is the one nobody is looking
    at: the Why? control hangs off `additional_salary`, so a copy that forgot
    it would leave a person with a deduction and no way to ask about it.

    Takes an already-checked Salary Slip document. Ownership is `_own_payslip`'s
    job and it happens before this is reached, every time - this function does
    no checking of its own and must never be given a slip that has not been
    through it.
    """

    def lines(rows):
        """One line per non-zero salary component.

        043 AC-26 adds `additional_salary` - and only where Frappe HR set one.
        It is the first link in the chain the "Why?" sheet follows:

            Salary Detail.additional_salary
              -> Additional Salary.ref_doctype / ref_docname
                -> Attendance Deduction
                  -> its violation rows

        A line with no link does not carry the key at all, so the client can
        ask "is there a Why? control on this line" by asking whether the key is
        there, rather than by guessing from the component's name. A component
        called "Late Coming Deduction" that HR typed in by hand has no link,
        and AC-29 is the sentence for that case.
        """
        out = []
        for r in (rows or []):
            if not flt(r.amount):
                continue
            line = {"component": r.salary_component, "amount": flt(r.amount)}
            if r.get("additional_salary"):
                line["additional_salary"] = r.additional_salary
            out.append(line)
        return out

    return {
        "name": slip.name,
        "employee_name": slip.employee_name,
        "designation": slip.designation,
        "department": slip.department,
        "company": slip.company,
        "start_date": slip.start_date,
        "end_date": slip.end_date,
        "posting_date": slip.posting_date,
        "currency": slip.currency,
        "total_working_days": flt(slip.total_working_days),
        "payment_days": flt(slip.payment_days),
        "leave_without_pay": flt(slip.leave_without_pay),
        "absent_days": flt(slip.get("absent_days")),
        "gross_pay": flt(slip.gross_pay),
        "total_deduction": flt(slip.total_deduction),
        "net_pay": flt(slip.net_pay),
        "rounded_total": flt(slip.rounded_total),
        # 051. The year so far, READ off the slip, never added up. Frappe HR's
        # payroll run works these out against the payroll period and stores
        # them here. Summing the slips the screen happens to list would give a
        # different number for a mid-year joiner and for anyone whose list is
        # capped - and it would be the portal's number rather than payroll's,
        # which is the one Form 16 will agree with.
        "year_to_date": flt(slip.get("year_to_date")),
        "gross_year_to_date": flt(slip.get("gross_year_to_date")),
        "earnings": lines(slip.earnings),
        "deductions": lines(slip.deductions),
    }


@frappe.whitelist()
@requires_feature("payroll", message=PAYSLIP_UNAVAILABLE)
def download_payslip(name):
    """The caller's own payslip as a PDF, in the organisation's print format.

    Frappe's print pipeline checks permission again, inside
    get_rendered_template, and employees no longer hold read on Salary Slip. It
    honours frappe.flags.ignore_print_permissions for exactly this case, so the
    flag is raised only after _own_payslip has proved the slip is the caller's,
    and put back whatever happens.

    NOT frappe.set_user("Administrator"). That was the first version, and it is
    wrong in a web request: set_user overwrites the session id with the user
    name, empties the session's stored data and clears form_dict, and switching
    back restores only the name. An employee pressing Download could have been
    signed out, or left with a broken session. A script test cannot see that,
    because a script has no browser session to break.
    """
    slip = _own_payslip(name)
    print_format = frappe.get_meta("Salary Slip").default_print_format or None

    previous = frappe.flags.ignore_print_permissions
    try:
        frappe.flags.ignore_print_permissions = True
        pdf = frappe.get_print("Salary Slip", slip.name, print_format=print_format, as_pdf=True)
    finally:
        frappe.flags.ignore_print_permissions = previous

    period = str(slip.start_date)[:7]
    frappe.local.response.filename = f"Payslip-{period}-{slip.employee}.pdf"
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "download"


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
    # Only the companies this HR user looks after (slice 010, SEC-13).
    from hrms.alvoraa_hr_core.access import permitted_companies
    companies = permitted_companies()
    if not companies:
        return {"employees": []}
    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active", "company": ["in", companies]},
        fields=["name", "employee_name", "department", "designation"],
        order_by="employee_name asc",
        ignore_permissions=True,
    )
    return {"employees": employees}


def _hr_target_employee(employee_id, endpoint):
    """The employee HR is acting for, or a refusal. Fails closed (SEC-13).

    Only employees of a company in permitted_companies(). The message is the
    same whether the employee is in another company or does not exist, so the
    refusal does not confirm who exists elsewhere. Returns only the fields the
    leave screens need - never the whole Employee record (PRIV-6).
    """
    from hrms.alvoraa_hr_core.access import permitted_companies, refuse

    emp = frappe.db.get_value(
        "Employee", employee_id, ["name", "employee_name", "company", "department"], as_dict=True
    )
    if not emp or emp.company not in permitted_companies():
        refuse(_("You can only act for employees of the companies you look after."),
               "SEC-13", endpoint, "Employee", employee_id)
    return emp


@frappe.whitelist()
def get_leave_summary(employee_id=None):
    roles = frappe.get_roles()
    is_hr = bool({"HR Manager", "HR User", "System Manager"} & set(roles))
    if employee_id and is_hr:
        emp = _hr_target_employee(employee_id, "hr_api.get_leave_summary")
    else:
        emp = _get_employee()
    if not emp:
        return {"no_employee": True}
    td = today()

    # Frappe HR's ledger (slice 035). emp is the caller, or someone HR may act
    # for - _hr_target_employee refused anyone else above.
    balances = []
    for b in _ledger_leave_balances(emp.name, td):
        total, taken = b["total"], b["taken"]
        balances.append({
            "leave_type": b["leave_type"],
            "total": total,
            "taken": taken,
            "pending": b["pending"],
            "expired": b["expired"],
            # The ledger's figure, negative included - see get_employee_dashboard.
            "balance": b["balance"],
            "color": LEAVE_COLORS.get(b["leave_type"], "#64748b"),
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

    # Only what the leave screen needs. This used to return the whole Employee
    # record - salary, PAN and bank details included - to any HR User (PRIV-6).
    employee = {"name": emp.name, "employee_name": emp.employee_name,
                "company": emp.company, "department": emp.department}
    return {"balances": balances, "applications": applications, "employee": employee,
            "ever_allocated": ever_allocated}


@frappe.whitelist()
def get_expense_types():
    return frappe.get_all(
        "Expense Claim Type",
        fields=["name"],
        order_by="name asc",
        ignore_permissions=True,
    )


def _expense_claim_accounts(company, expense_type):
    """The accounts a portal expense claim needs, from the company's own settings.

    ALV-178: an Expense Claim books to the ledger again. Without these the employee
    got a raw "Payable Account is mandatory" at approval, or "Set the default account
    for the Expense Claim Type" when filing. Both are HR set-up, so say that plainly,
    and say it before anything is saved.
    """
    payable_account, cost_center = frappe.db.get_value(
        "Company", company, ["default_expense_claim_payable_account", "cost_center"]
    ) or (None, None)
    if not payable_account:
        frappe.throw(
            _("Your expense claim could not be filed because {0} has no account set for "
              "paying expense claims. Please ask HR to set the Default Expense Claim "
              "Payable Account on the company, then try again.").format(company),
            title=_("Expense claims are not set up yet"),
        )
    if not cost_center:
        frappe.throw(
            _("Your expense claim could not be filed because {0} has no default cost "
              "centre. Please ask HR to set the Default Cost Center on the company, then "
              "try again.").format(company),
            title=_("Expense claims are not set up yet"),
        )
    if not frappe.db.exists("Expense Claim Account",
                            {"parent": expense_type, "company": company}):
        frappe.throw(
            _("Your expense claim could not be filed because the expense type {0} has no "
              "expense account for {1}. Please ask HR to set one on the Expense Claim "
              "Type, then try again.").format(expense_type, company),
            title=_("Expense claims are not set up yet"),
        )
    return {"payable_account": payable_account, "cost_center": cost_center}


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
    accounts = _expense_claim_accounts(emp.company, expense_type)

    doc = frappe.get_doc({
        "doctype": "Expense Claim",
        "employee": emp.name,
        "company": emp.company,
        "posting_date": today(),
        "currency": currency,
        "exchange_rate": 1,
        # ALV-178: the claim posts to the ledger again, so it needs the account the
        # employee is owed from and a cost centre. The desk form fills these from
        # the company defaults in JavaScript; the portal has to do it here.
        "payable_account": accounts["payable_account"],
        "cost_center": accounts["cost_center"],
        "expenses": [{
            "doctype": "Expense Claim Detail",
            "expense_date": expense_date,
            "expense_type": expense_type,
            "description": description or "",
            "amount": amount,
            "sanctioned_amount": amount,
            "cost_center": accounts["cost_center"],
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
        emp = _hr_target_employee(on_behalf_of, "hr_api.apply_leave")
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
        emp = _hr_target_employee(on_behalf_of, "hr_api.preview_leave_request")
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
    """The shift types a caller may ask to be moved to.

    043 AC-52 (`01c` SEC-7). What was live: `@frappe.whitelist()` and nothing
    else, `ignore_permissions=True`, no caller check and no scope - so EVERY
    Shift Type in the tenant went to anybody with a login, including somebody
    who had left and whose account was still open. A tenant's shift names
    ("Karol Bagh Night", "Warehouse C 22:00") are a map of its operation.

    **The scope, and why it is this one.** The spec first asked for "the
    caller's company's shift types". `Shift Type` has **no `company` field** -
    verified in `hrms/hrms/hr/doctype/shift_type/shift_type.json`, which has no
    company fieldname at all - so there is nothing to filter on, and an
    engineer meeting that sentence at 11pm would invent a custom field or
    quietly drop the check. `Shift Assignment` DOES carry a company. So the
    scope is D-6's recommendation:

        the Shift Types in use in the caller's own company, through submitted
        Shift Assignments, plus the caller's own `Employee.default_shift`

    That is a scope that exists in the data and needs no schema change. It also
    reads correctly: a shift you could actually be moved to is one somebody in
    your company is already working.

    **Fail closed.** No Active Employee record, no answer. An empty scope
    returns an EMPTY LIST, never an unfiltered one - no filter dict this
    function builds is ever allowed to be empty, because an empty filter dict
    means "everything" to `frappe.get_all` and that is exactly the defect being
    fixed. The screen must say "no shifts are set up for your company" rather
    than draw an empty dropdown.
    """
    emp = _get_employee()
    if not emp:
        # The same shape the other self-service reads use: a caller with no
        # Active Employee record has nothing to be moved between.
        return []

    # The shift types somebody in this company is actually assigned to.
    in_use = frappe.get_all(
        "Shift Assignment",
        filters={"company": emp.company, "docstatus": 1},
        pluck="shift_type",
        distinct=True,
    )

    # Read on its own rather than added to `_get_employee`'s field list.
    # Widening that row would put `default_shift` into the five older payloads
    # that still hand the whole row to the browser (AC-6's pinned debt), and
    # adding a field to a payload is a visibility change even when the field is
    # dull. One cheap query instead.
    default_shift = frappe.db.get_value("Employee", emp.name, "default_shift")

    names = {s for s in in_use if s}
    if default_shift:
        # Their own shift is always offered, even in a company that has never
        # made a Shift Assignment - otherwise the one person whose shift is set
        # on the Employee record sees a list that does not contain it.
        names.add(default_shift)

    if not names:
        return []

    return frappe.get_all(
        "Shift Type",
        filters={"name": ["in", sorted(names)]},
        fields=["name", "start_time", "end_time"],
        order_by="name asc",
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
    """Ask to encash leave. 043 AC-55.

    **This never worked**, and for two different reasons - the second of which
    I got wrong the first time and `test_encashment_043` corrected.

    `leave_period` and `currency` are both `reqd` on Leave Encashment (checked
    field by field in `leave_encashment.json`) and this endpoint set neither.

      * **`leave_period` crashed it.** Nothing fetches it and nothing defaults
        it, so every claim an employee sent failed on a mandatory field and
        the portal showed a generic error. Nobody on either client tenant has
        a successful Leave Encashment; appendix C F-5 recorded the button as
        never proven end to end, and this is why.
      * **`currency` did something quieter.** It is `read_only` AND `reqd`, so
        Frappe fills it from the site's Global Defaults before the mandatory
        check ever runs - meaning the claim was stamped with the SITE's
        currency, not the one the employee is paid in, and that figure goes
        into a payroll component.

    Both are set on the SERVER, not asked of the browser. A currency the
    caller can choose is a currency the caller can get wrong.
    """
    emp = _get_employee()
    if not emp:
        frappe.throw(_("No employee record found for this user."))

    date_ = encashment_date or today()

    # The period the date falls in, for this employee's own company. Leave
    # Period is per company, so a group with two companies has two, and picking
    # the first one on the site would file the claim against the wrong year.
    period = frappe.db.get_value("Leave Period", {
        "company": emp.company,
        "from_date": ("<=", date_),
        "to_date": (">=", date_),
    }, "name")
    if not period:
        # Says what happened, why, and what to do next. "Mandatory field
        # Leave Period" tells an employee nothing they can act on.
        frappe.throw(_("Leave cannot be encashed for {0} yet, because no leave "
                       "period covers that date. Ask HR to set one up.")
                     .format(frappe.format(date_, "Date")))

    from hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment import (
        get_employee_currency,
    )

    doc = frappe.get_doc({
        "doctype": "Leave Encashment",
        "employee": emp.name,
        "employee_name": emp.employee_name,
        "department": emp.department,
        "leave_type": leave_type,
        "encashment_date": date_,
        "leave_period": period,
        # Throws its own plain sentence when the employee has no salary
        # structure - which is a real setup gap, not something to paper over
        # with a default currency that would then be wrong on the component.
        "currency": get_employee_currency(emp.name),
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


EVIDENCE_HR_ROLES = {"HR Manager", "HR User"}   # the roles can_validate_evidence accepts


@frappe.whitelist()
def get_pending_approvals():
    """Goal evidence waiting for THIS user's decision (slice 010, decision 5).

    It used to import a function that does not exist, so the Team panel's
    progress approvals card always failed. It now lists pending evidence the
    caller may decide, by the same rule approve_evidence enforces:
      - a manager: their direct reports' goals;
      - HR: goals of employees in the companies they look after;
      - never the caller's own goals.
    Three bounded queries whatever the headcount. KPI progress approvals are
    listed by goals_api.get_pending_approvals, so `kpis` stays empty here.
    """
    empty = {"goals": [], "kpis": []}
    if not frappe.db.exists("DocType", "Individual Goal"):
        return empty
    me = _get_employee()
    my_id = me.name if me else None
    if EVIDENCE_HR_ROLES & set(frappe.get_roles()):
        from hrms.alvoraa_hr_core.access import permitted_companies
        companies = permitted_companies()
        emp_filters = {"company": ["in", companies]} if companies else None
    elif my_id:
        emp_filters = {"reports_to": my_id}
    else:
        emp_filters = None
    if emp_filters is None:
        return empty

    pending = frappe.get_all(
        "Goal Evidence",
        filters={"parenttype": "Individual Goal", "validation_status": "Pending"},
        fields=["name", "parent", "evidence_type", "value", "extracted_date", "upload_date"],
        order_by="upload_date asc", limit=500,
    )
    if not pending:
        return empty
    goals = {g.name: g for g in frappe.get_all(
        "Individual Goal",
        filters={"name": ["in", list({p.parent for p in pending})], "docstatus": ["!=", 2]},
        fields=["name", "goal_name", "employee", "employee_name", "unit"],
    )}
    emp_filters.update({"name": ["in", list({g.employee for g in goals.values()})]})
    allowed = set(frappe.get_all("Employee", filters=emp_filters, pluck="name")) - {my_id}

    out = []
    for p in pending:
        g = goals.get(p.parent)
        if not g or g.employee not in allowed:
            continue
        out.append({
            "name": g.name, "goal_name": g.goal_name, "employee": g.employee,
            "employee_name": g.employee_name, "unit": g.unit,
            "evidence": {"row": p.name, "type": p.evidence_type, "value": p.value,
                         "extracted_date": str(p.extracted_date) if p.extracted_date else None},
        })
    return {"goals": out, "kpis": []}


@frappe.whitelist()
@requires_feature("goals")
def approve_goal_evidence(goal_name, evidence_row):
    from alvoraa_goals.controllers.evidence import approve_evidence
    return approve_evidence(goal_name, evidence_row)


@frappe.whitelist()
@requires_feature("goals")
def reject_goal_evidence(goal_name, evidence_row, reason=""):
    from alvoraa_goals.controllers.evidence import reject_evidence
    return reject_evidence(goal_name, evidence_row, reason)


@frappe.whitelist()
@requires_feature("goals")
def get_self_approved_evidence(limit=200):
    """Read-only, for HR: evidence approved with no person's sign-off.

    Before slice 010 every evidence row approved itself. Those rows are left
    as they are (decision 5); this lists the ones that need a second look -
    approved by nobody, by "System", or by the person who uploaded them - so
    HR can review them. It changes nothing.
    """
    if not EVIDENCE_HR_ROLES & set(frappe.get_roles()):
        frappe.throw(_("Only HR can see this list."), frappe.PermissionError)
    from hrms.alvoraa_hr_core.access import permitted_companies
    companies = permitted_companies()
    if not companies:
        return []

    ev = frappe.qb.DocType("Goal Evidence")
    goal = frappe.qb.DocType("Individual Goal")
    emp = frappe.qb.DocType("Employee")
    no_person = (ev.approved_by.isnull() | (ev.approved_by == "") | (ev.approved_by == "System")
                 | (ev.approved_by == ev.uploaded_by))
    rows = (
        frappe.qb.from_(ev)
        .join(goal).on(goal.name == ev.parent)
        .join(emp).on(emp.name == goal.employee)
        .select(ev.name.as_("evidence_row"), goal.name.as_("goal"), goal.goal_name, goal.employee,
                goal.employee_name, ev.evidence_type, ev.value, ev.upload_date, ev.uploaded_by,
                ev.approved_by)
        .where((ev.parenttype == "Individual Goal") & (ev.validation_status == "Approved")
               & no_person & emp.company.isin(companies))
        .orderby(ev.upload_date, order=frappe.qb.desc)
        .limit(min(cint(limit) or 200, 1000))
    ).run(as_dict=True)
    return rows


@frappe.whitelist()
def approve_kpi_progress(kpi_name, log_idx, comment=None):
    from alvoraa_goals.api.goal_api import approve_kpi_progress as _akp
    return _akp(kpi_name, log_idx, comment)


@frappe.whitelist()
def reject_kpi_progress(kpi_name, log_idx, comment=None):
    from alvoraa_goals.api.goal_api import reject_kpi_progress as _rkp
    return _rkp(kpi_name, log_idx, comment)


# Slice 012 G2 (SEC-18): the only keys these two calls may touch, with the only
# values each may take. They read and wrote ANY Frappe default before, so one
# call could add "Employee" to alvoraa_attendance_org_roles and show every
# employee everybody's leave types, with no record of who did it. The portal's
# Org Settings screen uses kra_link_mandatory and nothing else. A key that grants
# visibility must never be added here - it needs System Manager and a change record.
#
# Slice 017: the late-coming grace period joins the list. It is a number rather
# than a yes/no, so a value may also be given as a `range` - whole minutes only,
# and still an allow-list, just an arithmetic one. It grants no visibility: it
# moves a threshold on a screen the person can already see, and it does not
# touch the deduction rule, which keeps its own per-organisation threshold.
#
# 26 Sep 2026 (Surbhi): late coming rules and attendance in the appraisal score
# stop being tenant features in the admin console and become these two switches.
# Every company sets its own rules, so HR decides; both are off until HR turns
# them on. Neither grants visibility - each only lets a rule the company already
# writes for itself start acting. Turning one on also needs the modules it works
# on to be sold (ORG_SWITCH_NEEDS below); turning one off is always allowed.
ALLOWED_ORG_SETTINGS = {
    "kra_link_mandatory": ("0", "1"),
    LATE_GRACE_KEY: range(0, 241),          # up to four hours; nothing sensible is longer
    org_features.LATE_RULES_SWITCH: ("0", "1"),
    org_features.ATTENDANCE_SCORING_SWITCH: ("0", "1"),
}

# What each switch needs the tenant to have bought before it may be turned on.
# Late rules take days from leave and then from pay, and read attendance; the
# appraisal score reads attendance into an appraisal. Checked with the same
# has_feature() every other entitlement uses.
ORG_SWITCH_NEEDS = {
    org_features.LATE_RULES_SWITCH: ("attendance", "leaves", "payroll"),
    org_features.ATTENDANCE_SCORING_SWITCH: ("performance", "attendance"),
}


def _open_cycles_using_attendance():
    """Appraisal cycles, not yet Completed, that count attendance in the score.

    Switching attendance scoring off under them breaks them: their formula still
    multiplies a stored attendance score, and completing the cycle saves it, which
    the switched-off check then refuses. So HR finishes or changes them first.
    Cycle names only - never a person.
    """
    if not frappe.db.has_column("Appraisal Cycle", "include_attendance_score"):
        return []
    return frappe.get_all(
        "Appraisal Cycle",
        filters={"include_attendance_score": 1, "status": ["!=", "Completed"]},
        pluck="name", order_by="name asc", limit=20, ignore_permissions=True,
    )


def _switch_missing(key):
    """Labels of the sold features this switch still needs, or []."""
    from alvoraa_portal.subscription import feature_spec, has_feature

    return [_(feature_spec(f).get("label", f)) for f in ORG_SWITCH_NEEDS.get(key, ())
            if not has_feature(f)]


def _refuse_org_setting(endpoint):
    from hrms.alvoraa_hr_core.access import refuse

    # Neither the key nor the value is logged: the rule id says enough.
    refuse(_("This setting cannot be read or changed here."), "SEC-18", endpoint)


@frappe.whitelist()
def get_org_setting(key):
    _require_hr()
    if not isinstance(key, str) or key not in ALLOWED_ORG_SETTINGS:
        _refuse_org_setting("hr_api.get_org_setting")
    return frappe.db.get_default(key)


@frappe.whitelist()
def set_org_setting(key, value):
    _require_hr()
    _refuse_store_hr("hr_api.set_org_setting")
    if not isinstance(key, str) or key not in ALLOWED_ORG_SETTINGS:
        _refuse_org_setting("hr_api.set_org_setting")
    value = str(value) if value is not None else ""
    allowed = ALLOWED_ORG_SETTINGS[key]
    if isinstance(allowed, range):
        # Whole minutes, no sign, no spaces, and inside the range. Anything else
        # is refused rather than coerced - a silently clamped threshold is worse
        # than an error, because nobody finds out what was actually saved.
        if not re.fullmatch(r"[0-9]{1,3}", value) or int(value) not in allowed:
            _refuse_org_setting("hr_api.set_org_setting")
    elif value not in allowed:
        _refuse_org_setting("hr_api.set_org_setting")
    if value == "0" and key == org_features.ATTENDANCE_SCORING_SWITCH:
        open_cycles = _open_cycles_using_attendance()
        if open_cycles:
            frappe.throw(
                _("Finish or change these appraisal cycles first: {0}. They count attendance in the score, and switching it off would stop them completing.").format(", ".join(open_cycles)),
                frappe.ValidationError,
            )
    if value == "1" and key in ORG_SWITCH_NEEDS:
        missing = _switch_missing(key)
        if missing:
            frappe.throw(
                _("This can be switched on only when your plan includes {0}. Ask your Alvora account contact to add it.").format(", ".join(missing)),
                frappe.ValidationError,
            )
    frappe.db.set_default(key, value)
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist()
def get_attendance_rule_switches():
    """The Organisation Settings card "Attendance rules": both switches, whether
    each is on, and - when the plan does not allow one - what it still needs.

    HR only, like the settings it describes. Returns labels, never another
    tenant's data or any person's record.
    """
    _require_hr()
    # Whether THIS caller may save them: the same rule set_org_setting applies
    # (a store's HR person reads, never saves). Computed without calling the
    # guard, which would log a refusal just for opening the page.
    from alvoraa_portal.frame_api import _may_save_settings

    can_edit = _may_save_settings(set(frappe.get_roles()))
    out = []
    for key in org_features.ORG_SWITCHES:
        missing = _switch_missing(key)
        out.append({"key": key, "on": org_features.org_switch(key),
                    "available": not missing, "needs": missing})
    return {"switches": out, "can_edit": can_edit}


def _require_hr():
    # frappe.has_role() does not exist. It threw AttributeError instead of
    # checking anything, which failed all five endpoints behind this guard -
    # "Company Values" among them - for everybody including HR.
    if not {"HR Manager", "System Manager"} & set(frappe.get_roles()):
        frappe.throw("Not permitted", frappe.PermissionError)


def _refuse_store_hr(endpoint):
    """An organisation-wide setting is changed by HR with company-wide reach,
    never by a store's HR person (slice 030, decision 4).

    A store's HR Manager holds a Branch User Permission. The same read that
    limits what they see (access.permitted_employees, through
    permitted_branches) decides here, so "limited to a store" has one
    definition. Reads are not guarded by this; System Manager is not limited.
    """
    from hrms.alvoraa_hr_core.access import permitted_branches, refuse

    if "System Manager" in frappe.get_roles():
        return
    if permitted_branches() is not None:
        refuse(_("Organisation-wide settings are changed by HR with company-wide permission, "
                 "not by a store's HR."), "030-D4", endpoint)


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
    is_owner = bool(goal_employee) and goal_employee == emp.name
    if not is_owner:
        dr = goal_employee and frappe.db.get_value("Employee",
            {"name": goal_employee, "reports_to": emp.name, "status": "Active"},
            "name")
        if not dr:
            if not is_hr:
                frappe.throw("Access denied", frappe.PermissionError)
            # HR outside its own line opens goals only for the companies it looks
            # after (slice 010 group D, decision 33). It used to open any
            # company's goal. Same refusal for "other company" and "no such goal".
            _hr_target_employee(goal_employee, "hr_api.get_goal_detail")
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
    # Slice 010 group D (R5, PRIV-10): "in a review", and the day after which
    # updates no longer change it. Nothing else about the review.
    import alvoraa_goals.review_items as review_items

    goal["review_badge"] = review_items.review_badges("Individual Goal", [goal_id]).get(goal_id)
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


# ══════════════════════════════════════════════════════════════════════════
# Late-coming rule (build B1) - portal views of Attendance Deduction
# ══════════════════════════════════════════════════════════════════════════

EMP_RULE_FIELDS = ["company", "default_shift", "grade", "date_of_joining", "status"]


def _late_rule_for(employee, emp_row=None, cache=None):
    """The enabled rule that would actually act on this employee, or None.

    `emp_row` and `cache` exist so a manager's whole team can be answered without
    a handful of queries per person: the caller passes the Employee row it already
    read, and the cache holds the rule per company-and-shift. Called with neither,
    it behaves exactly as it always did.
    """
    if cache is None:
        cache = {}
    # Switched off in Organisation Settings: no rule acts on anybody, so every
    # screen built on this (my deductions, the team list, the Time tab) is
    # hidden. Recorded deductions are kept; they are simply not drawn here.
    if "_switched_on" not in cache:
        cache["_switched_on"] = org_features.late_rules_on()
    if not cache["_switched_on"]:
        return None
    if "_have_doctype" not in cache:
        cache["_have_doctype"] = bool(frappe.db.exists("DocType", "Attendance Deduction Rule"))
    if not cache["_have_doctype"]:
        return None
    if emp_row is None:
        emp_row = frappe.db.get_value("Employee", employee, EMP_RULE_FIELDS, as_dict=True)
    if not emp_row:
        return None

    key = (emp_row.get("company"), emp_row.get("default_shift"))
    if key in cache:
        rule = cache[key]
    else:
        rule = None
        for filters in ({"company": key[0], "shift_type": key[1], "enabled": 1},
                        {"company": key[0], "shift_type": ["in", ["", None]], "enabled": 1}):
            name = frappe.db.get_value("Attendance Deduction Rule", filters, "name")
            if name:
                rule = frappe.get_cached_doc("Attendance Deduction Rule", name)
                break
        cache[key] = rule
    if not rule:
        return None

    # A rule that names this person's company is not the same as a rule that
    # would act on this person. An exempt grade meant the portal showed
    # deductions the weekly job was never going to make.
    from hrms.alvoraa_late_rules.late_rules import covers

    return rule if covers(rule, employee, emp=emp_row) else None


def _deduction_rows(filters, limit=20):
    rows = frappe.get_all(
        "Attendance Deduction",
        filters=filters,
        fields=["name", "employee", "employee_name", "week_start", "week_end", "total_violations",
                "counted_violations", "deduction_days", "lwp_days", "lwp_amount", "explanation"],
        order_by="week_start desc", limit=limit, ignore_permissions=True,
    )
    for r in rows:
        r["leave_days"] = round(frappe.utils.flt(r.deduction_days) - frappe.utils.flt(r.lwp_days), 2)
        r["violations"] = frappe.get_all(
            "Attendance Deduction Violation", filters={"parent": r.name},
            fields=["attendance_date", "violation_type", "expected_time", "actual_time", "minutes", "counted"],
            order_by="attendance_date asc", ignore_permissions=True,
        )
        for v in r["violations"]:
            v["attendance_date"] = str(v.attendance_date)
            v["expected_time"] = str(v.expected_time)[:5] if v.expected_time else ""
            v["actual_time"] = str(v.actual_time)[:5] if v.actual_time else ""
        r["week_start"] = str(r.week_start)
        r["week_end"] = str(r.week_end)
    return rows


@frappe.whitelist()
def get_my_attendance_deductions(months=3):
    """The employee's own late-coming deductions plus this week so far."""
    emp = _get_employee()
    if not emp:
        return {"no_employee": True}
    rule = _late_rule_for(emp.name)
    since = frappe.utils.add_months(frappe.utils.nowdate(), -int(months))
    if not rule:
        # Switched off in Organisation Settings: nothing new is deducted, but
        # days already taken stay on the person's screen, read-only. Only the
        # forward-looking parts (this week so far, the rule's terms) go.
        if not org_features.late_rules_on():
            rows = _deduction_rows({"employee": emp.name, "docstatus": 1, "week_start": [">=", since]})
            if rows:
                return {"enabled": True, "switched_on": False, "rule": None,
                        "rows": rows, "this_week": None}
        return {"enabled": False, "rows": [], "this_week": None}
    from hrms.alvoraa_late_rules.late_rules import current_week_projection
    rows = _deduction_rows({"employee": emp.name, "docstatus": 1, "week_start": [">=", since]})
    projection = current_week_projection(rule, emp.name)
    for v in projection["violations"]:
        v["attendance_date"] = str(v["attendance_date"])
        v["expected_time"] = str(v["expected_time"])[:5]
        v["actual_time"] = str(v["actual_time"])[:5]
    return {
        "enabled": True,
        "rule": {"name": rule.name, "late_threshold_minutes": rule.late_threshold_minutes,
                 "early_exit_threshold_minutes": rule.early_exit_threshold_minutes if rule.count_early_exit else 0,
                 "free_violations_per_week": rule.free_violations_per_week,
                 "deduction_per_violation_days": rule.deduction_per_violation_days,
                 "round_up_from_days": rule.round_up_from_days, "round_up_to_days": rule.round_up_to_days},
        "rows": rows,
        "this_week": projection,
    }


@frappe.whitelist()
def get_team_late_list(weeks=4):
    """Manager: this week so far for every direct report, and the last few weeks' deductions."""
    emp = _get_employee()
    if not emp:
        return {"no_employee": True}
    team = frappe.get_all("Employee", filters={"reports_to": emp.name, "status": "Active"},
                          fields=["name", "employee_name", "designation"] + EMP_RULE_FIELDS,
                          order_by="employee_name asc")
    if not team:
        return {"enabled": False, "team": [], "recent": []}
    from hrms.alvoraa_late_rules.late_rules import current_week_projection

    # Each person against THEIR OWN rule. This used to look up the first team
    # member's rule and apply it to everybody, so a team split across shifts was
    # judged by one person's thresholds, and anyone the rule did not cover was
    # still given a figure. The shared cache and the row we already read keep
    # this to the same number of queries as the single-rule version.
    out = []
    week_start = None
    rule_cache = {}
    for m in team:
        rule = _late_rule_for(m.name, emp_row=m, cache=rule_cache)
        if not rule:
            continue
        p = current_week_projection(rule, m.name)
        week_start = week_start or p["week_start"]
        out.append({"employee": m.name, "employee_name": m.employee_name, "designation": m.designation,
                    "violations": len(p["violations"]), "counted": p["counted"], "projected_days": p["projected_days"],
                    "detail": [f"{str(v['attendance_date'])[5:]} {v['violation_type']} {str(v['actual_time'])[:5]}"
                               for v in p["violations"]]})
    if not out:
        return {"enabled": False, "team": [], "recent": []}
    since = frappe.utils.add_days(frappe.utils.nowdate(), -7 * int(weeks))
    # Days only. A manager never receives a report's loss-of-pay amount, the
    # explanation text or the per-day punch times (slice 010, PRIV-3). A fixed
    # field list rather than _deduction_rows, which is the employee's own view.
    recent = frappe.get_all(
        "Attendance Deduction",
        filters={"employee": ["in", [m.name for m in team]], "docstatus": 1, "week_start": [">=", since]},
        fields=["name", "employee", "employee_name", "week_start", "week_end", "deduction_days", "lwp_days"],
        order_by="week_start desc", limit=50,
    )
    for r in recent:
        r["week_start"] = str(r.week_start)
        r["week_end"] = str(r.week_end)
    return {"enabled": True, "week_start": week_start, "team": out, "recent": recent}


# ── Employee documents (build B4) ──────────────────────────────────────────
@frappe.whitelist()
def get_my_documents():
    """The signed-in employee's document checklist, with what they can upload."""
    emp = _get_employee()
    if not emp or not frappe.db.exists("DocType", "Employee Document"):
        return {"rows": [], "summary": ""}
    types = {
        t.name: t
        for t in frappe.get_all(
            "Employee Document Type",
            fields=["name", "category", "collect_from", "mandatory_for_joining", "has_expiry"],
        )
    }
    rows = frappe.get_all(
        "Employee Document",
        filters={"parent": emp.name, "parenttype": "Employee"},
        fields=["name", "document_type", "status", "attachment", "document_number", "expiry_date",
                "received_on", "verified_on", "remarks"],
        order_by="idx",
    )
    out = []
    for r in rows:
        t = types.get(r.document_type) or frappe._dict()
        out.append({
            "name": r.name,
            "document_type": r.document_type,
            "category": t.get("category") or "",
            "status": r.status,
            "attachment": r.attachment or "",
            "document_number": r.document_number or "",
            "expiry_date": str(r.expiry_date) if r.expiry_date else "",
            "received_on": str(r.received_on) if r.received_on else "",
            "verified_on": str(r.verified_on) if r.verified_on else "",
            "remarks": r.remarks or "",
            "mandatory": int(t.get("mandatory_for_joining") or 0),
            "collect_from": t.get("collect_from") or "",
            "can_upload": int((t.get("collect_from") == "Employee") and r.status != "Verified"),
        })
    return {"employee": emp.name, "rows": out,
            "summary": frappe.db.get_value("Employee", emp.name, "documents_summary") or ""}


@frappe.whitelist()
def attach_my_document(row, file_url, document_number=None):
    """Put an uploaded file on one of the caller's own checklist rows."""
    from hrms.alvoraa_employee_documents.employee_documents import attach_document

    emp = _get_employee()
    if not emp:
        frappe.throw("No employee record is linked to your login.", frappe.PermissionError)
    doc = attach_document(row, file_url, emp.name)
    if document_number is not None:
        frappe.db.set_value("Employee Document", doc.name, "document_number", document_number)
    frappe.db.commit()
    return {"name": doc.name, "status": doc.status, "message": "Uploaded. HR will verify it."}


@frappe.whitelist()
def hr_document_compliance(branch=None):
    """HR: employees with a mandatory document not yet verified or any document
    expired, grouped by branch."""
    from hrms.alvoraa_employee_documents.employee_documents import employees_missing_mandatory

    _require_hr()
    rows = employees_missing_mandatory(branch or None)
    by_branch = {}
    for r in rows:
        by_branch.setdefault(r["branch"] or "No branch", []).append(r)
    total_active = frappe.db.count("Employee", {"status": "Active"})
    return {
        "employees": rows,
        "by_branch": [{"branch": b, "count": len(v)} for b, v in sorted(by_branch.items())],
        "affected": len(rows),
        "active": total_active,
    }


# ── Policy library (build B5) ──────────────────────────────────────────────
POLICY_FIELDS = ["name", "title", "owner_department", "category", "status", "current_version", "effective_from",
                 "review_due", "summary", "attachment", "pinned", "acknowledge_on_joining",
                 "acknowledge_on_new_version", "has_unpublished_changes", "modified"]


def _policy_row(p, emp, can_write_flag):
    from hrms.alvoraa_policy_library.doctype.policy_document.policy_document import acknowledgement_status

    needed, done = acknowledgement_status(p, emp)
    ack = "acknowledged" if (needed and done) else ("pending" if needed else "")
    return {
        "name": p.name, "title": p.title, "department": p.owner_department, "category": p.category,
        "status": p.status, "version": cint(p.current_version),
        "effective_from": str(p.effective_from) if p.effective_from else "",
        "review_due": str(p.review_due) if p.review_due else "",
        "summary": p.summary or "", "has_attachment": bool(p.attachment), "pinned": cint(p.pinned),
        "ack": ack, "can_write": int(can_write_flag), "unpublished_changes": cint(p.has_unpublished_changes),
        "modified": str(p.modified)[:10],
    }


@frappe.whitelist()
def get_my_policies(limit=6):
    """Home widget: pinned first, then newest published, only what the caller may read."""
    if not frappe.db.exists("DocType", "Policy Document"):
        return {"rows": [], "pending": 0}
    from hrms.alvoraa_policy_library.access import can_write, profile

    emp = (_get_employee() or {}).get("name")
    rows = frappe.get_list("Policy Document", filters={"status": "Published"}, fields=POLICY_FIELDS,
                           order_by="pinned desc, modified desc", limit=cint(limit) or 6)
    out = [_policy_row(p, emp, can_write(p)) for p in rows]
    pending = sum(1 for r in _all_readable(emp) if r["ack"] == "pending")
    return {"rows": out, "pending": pending, "can_manage": int(bool(profile().heads) or profile().is_hr_manager or profile().is_admin)}


def _all_readable(emp, search="", department="", category="", status="Published"):
    from hrms.alvoraa_policy_library.access import can_write

    filters = {}
    if status:
        filters["status"] = status
    if department:
        filters["owner_department"] = department
    if category:
        filters["category"] = category
    or_filters = None
    if search:
        like = "%" + search.strip() + "%"
        or_filters = {"title": ["like", like], "summary": ["like", like], "content": ["like", like]}
    rows = frappe.get_list("Policy Document", filters=filters, or_filters=or_filters, fields=POLICY_FIELDS,
                           order_by="pinned desc, title asc", limit=0)
    return [_policy_row(p, emp, can_write(p)) for p in rows]


@frappe.whitelist()
def list_policies(search="", department="", category="", status="Published"):
    """The Policies page. Writers may ask for Draft or Archived too."""
    emp = (_get_employee() or {}).get("name")
    rows = _all_readable(emp, search, department, category, status if status != "all" else "")
    departments = sorted({r["department"] for r in rows})
    categories = sorted({r["category"] for r in rows})
    return {"rows": rows, "departments": departments, "categories": categories}


@frappe.whitelist()
def get_policy(name):
    """One policy: readers get the last published snapshot, writers also get the working copy."""
    from hrms.alvoraa_policy_library.access import can_write

    doc = frappe.get_doc("Policy Document", name)
    doc.check_permission("read")
    emp = (_get_employee() or {}).get("name")
    writer = can_write(doc)
    view = doc.published_view()
    row = _policy_row(doc, emp, writer)
    row.update({
        "content": view.content or "", "attachment": view.attachment or "",
        "published_on": str(view.get("published_on") or "")[:16], "published_by": view.get("published_by") or "",
        "versions": [{"version": v.version, "published_on": str(v.published_on)[:16], "published_by": v.published_by,
                      "change_note": v.change_note or ""} for v in reversed(doc.versions or [])],
    })
    if writer:
        row["working"] = {
            "title": doc.title, "summary": doc.summary or "", "content": doc.content or "",
            "attachment": doc.attachment or "", "effective_from": str(doc.effective_from or ""),
            "review_due": str(doc.review_due or ""), "pinned": cint(doc.pinned),
            "acknowledge_on_joining": cint(doc.acknowledge_on_joining),
            "acknowledge_on_new_version": cint(doc.acknowledge_on_new_version),
            "read_access": [{"access_type": r.access_type, "role": r.role, "user": r.user, "designation": r.designation,
                             "branch": r.branch, "department": r.department} for r in doc.read_access],
            "acknowledged_count": frappe.db.count("Policy Acknowledgement",
                                                  {"policy_document": doc.name, "version": cint(doc.current_version)}),
        }
    return row


@frappe.whitelist()
def acknowledge_policy(name, source="Manual"):
    """The signed-in employee confirms they have read the current version."""
    emp = _get_employee()
    if not emp:
        frappe.throw("No employee record is linked to your login.", frappe.PermissionError)
    doc = frappe.get_doc("Policy Document", name)
    doc.check_permission("read")
    if doc.status != "Published":
        frappe.throw("Only a published policy can be acknowledged.")
    if frappe.db.exists("Policy Acknowledgement", {"policy_document": name, "version": cint(doc.current_version),
                                                   "employee": emp.name}):
        return {"message": "Already acknowledged."}
    ack = frappe.get_doc({"doctype": "Policy Acknowledgement", "policy_document": name,
                          "version": cint(doc.current_version), "employee": emp.name, "user": frappe.session.user,
                          "source": source if source in ("Onboarding", "New Version", "Manual") else "Manual"})
    ack.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"message": f"Thank you. Version {doc.current_version} of \"{doc.title}\" is acknowledged."}


WHO_PRESETS = {
    "everyone": [{"access_type": "All Employees"}],
    "managers": [{"access_type": "Reporting Managers"}],
    "hr": [{"access_type": "HR Only"}],
    "department": [{"access_type": "Department Only"}],
    "leadership": [{"access_type": "Top Leadership"}],
}


@frappe.whitelist()
def save_policy(name=None, title=None, owner_department=None, category=None, summary=None, content=None,
                effective_from=None, review_due=None, pinned=0, acknowledge_on_joining=0,
                acknowledge_on_new_version=0, who=None, read_access=None):
    """Create or update the working copy. Publishing is a separate step."""
    import json
    from hrms.alvoraa_policy_library.access import can_write

    if name:
        doc = frappe.get_doc("Policy Document", name)
    else:
        doc = frappe.new_doc("Policy Document")
        doc.status = "Draft"
    for field, value in (("title", title), ("owner_department", owner_department), ("category", category),
                         ("summary", summary), ("content", content), ("effective_from", effective_from or None),
                         ("review_due", review_due or None)):
        if value is not None:
            doc.set(field, value)
    doc.pinned = cint(pinned)
    doc.acknowledge_on_joining = cint(acknowledge_on_joining)
    doc.acknowledge_on_new_version = cint(acknowledge_on_new_version)
    if not can_write(doc):
        frappe.throw("You cannot edit this policy. Department heads edit their own department's policies; HR Managers edit any.",
                     frappe.PermissionError)
    rules = None
    if who in WHO_PRESETS:
        rules = WHO_PRESETS[who]
    elif read_access:
        rules = json.loads(read_access) if isinstance(read_access, str) else read_access
    if rules is not None:
        doc.set("read_access", [])
        for r in rules:
            doc.append("read_access", r)
    doc.flags.ignore_permissions = True     # can_write is the check that matters here
    doc.save()
    frappe.db.commit()
    return {"name": doc.name, "status": doc.status, "message": "Saved." + (" Publish it when it is ready." if doc.status == "Draft" else "")}


@frappe.whitelist()
def publish_policy(name, change_note=""):
    doc = frappe.get_doc("Policy Document", name)
    result = doc.publish(change_note)
    frappe.db.commit()
    return {"message": f"Published as version {result['version']}.", **result}


@frappe.whitelist()
def get_policy_compliance(branch=None):
    """HR: who still has to acknowledge which policy, by branch."""
    _require_hr()
    policies = frappe.get_all("Policy Document",
                              filters={"status": "Published", "acknowledge_on_joining": 1},
                              fields=["name", "title", "current_version"])
    policies += frappe.get_all("Policy Document",
                               filters={"status": "Published", "acknowledge_on_joining": 0, "acknowledge_on_new_version": 1},
                               fields=["name", "title", "current_version"])
    filters = {"status": "Active"}
    if branch:
        filters["branch"] = branch
    employees = frappe.get_all("Employee", filters=filters, fields=["name", "employee_name", "branch"])
    acks = set()
    for a in frappe.get_all("Policy Acknowledgement", filters={"policy_document": ["in", [p.name for p in policies]]},
                            fields=["policy_document", "version", "employee"]):
        acks.add((a.policy_document, cint(a.version), a.employee))
    by_branch, by_policy, rows = {}, {}, []
    for e in employees:
        missing = [p.title for p in policies if (p.name, cint(p.current_version), e.name) not in acks]
        b = by_branch.setdefault(e.branch or "No branch", {"branch": e.branch or "No branch", "employees": 0, "pending": 0})
        b["employees"] += 1
        if missing:
            b["pending"] += 1
            rows.append({"employee": e.name, "employee_name": e.employee_name, "branch": e.branch or "", "missing": missing})
        for p in policies:
            bp = by_policy.setdefault(p.name, {"policy": p.title, "version": cint(p.current_version), "acknowledged": 0, "pending": 0})
            if (p.name, cint(p.current_version), e.name) in acks:
                bp["acknowledged"] += 1
            else:
                bp["pending"] += 1
    review = frappe.get_all("Policy Document", filters={"status": "Published", "review_due": ["<=", frappe.utils.add_days(today(), 60)]},
                            fields=["name", "title", "review_due", "owner_department"], order_by="review_due")
    return {"by_branch": sorted(by_branch.values(), key=lambda r: r["branch"]),
            "by_policy": sorted(by_policy.values(), key=lambda r: -r["pending"]),
            "employees": sorted(rows, key=lambda r: (r["branch"], r["employee_name"]))[:200],
            "pending_total": len(rows), "active": len(employees),
            "review_due": [{"name": r.name, "title": r.title, "review_due": str(r.review_due), "department": r.owner_department} for r in review]}


# ── This week, at a glance ───────────────────────────────────────────────────
#
# The old week-presence endpoint USED TO LIVE HERE, and slice 042 (Wave 2,
# SEC-9 / AC-59) deleted it in the same commit that stopped calling it. Its
# name is not written anywhere in this app on purpose - the static check that
# keeps it gone is absolute, so there is nothing for a search to trip over.
#
# It was whitelisted, and it returned NAMED rows - employee_name, designation
# and photo - with a per-day in/away/due/off state for each. When the caller had
# no direct reports it fell back to their whole DEPARTMENT, capped at 40. So any
# signed-in person could ask it, by hand, for forty colleagues' week of
# absences.
#
# Wave 2 replaces the card it fed with `home_api._team_today`: three numbers,
# no names, a minimum group size, and peers defined as people with the same
# manager - no department fallback at all.
#
# Retiring the card is not retiring the endpoint. Leaving a whitelisted function
# in place because a screen stopped calling it is "a hidden menu is not a
# permission" in a different hat, so it is gone, and
# `test_week_presence_retired_042` fails if the name comes back anywhere in
# this app's source.
