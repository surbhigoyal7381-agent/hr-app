"""Org-tree helpers and row-level scoping for employee-owned performance records.

Doctype-level permissions in Frappe are all-or-nothing: granting the Employee
role write on Individual Goal would let every employee edit every colleague's.
These hooks narrow each operation to what the person actually owns or manages:

    read            self + everyone below them in the reporting tree
    create          self + subordinates (the API validates the target employee)
    write / delete  additionally, only records that person created
    HR / admin      everything inside their own tenant

"Subordinate" means the whole subtree, not just direct reports — a head of
department manages their managers' teams too, and goals cascade further than one
level.

The write/delete rule is deliberately about the *creator*, not the subject: a
KPI HR assigned to you is yours to work against but not to redefine, while one
you raised yourself you can revise or withdraw. Logging progress and self-rating
are separate operations and stay open to the record's employee either way.

Cross-*tenant* isolation is not handled here and does not need to be: every
Frappe site has its own database, so a query issued on one tenant can never
reach another tenant's tables.
"""

import frappe

# Roles that legitimately see and manage all employees' records within a tenant.
FULL_ACCESS_ROLES = frozenset({"System Manager", "HR Manager", "HR User"})

# Doctypes scoped by an `employee` link field.
EMPLOYEE_SCOPED_DOCTYPES = ("Individual Goal", "KPI")

# Depth guard: a reports_to cycle would otherwise recurse forever.
MAX_TREE_DEPTH = 12


def _has_full_access(user):
    return bool(FULL_ACCESS_ROLES.intersection(frappe.get_roles(user)))


def employee_for(user=None):
    user = user or frappe.session.user
    return frappe.db.get_value("Employee", {"user_id": user}, "name")


def get_hr_manager_employee():
    """Return the employee record id of the first active HR Manager user."""
    hr_users = frappe.get_all(
        "Has Role",
        filters={"role": "HR Manager", "parenttype": "User"},
        pluck="parent",
        ignore_permissions=True,
    )
    for user in hr_users:
        emp = frappe.db.get_value(
            "Employee", {"user_id": user, "status": "Active"}, "name",
        )
        if emp:
            return emp
    return None


def get_effective_manager(employee_id):
    """Return the employee's direct reporting manager, falling back to the HR
    Manager employee when reports_to is not set.  This means employees without
    a configured manager are never left without one for approval/notification."""
    mgr = frappe.db.get_value("Employee", employee_id, "reports_to")
    if mgr:
        return mgr
    return get_hr_manager_employee()


def descendants(employee_id):
    """Every employee below `employee_id`, at any depth."""
    if not employee_id:
        return []
    found = []
    seen = {employee_id}
    frontier = [employee_id]
    depth = 0
    while frontier and depth < MAX_TREE_DEPTH:
        rows = frappe.get_all(
            "Employee",
            filters={"reports_to": ["in", frontier], "status": "Active"},
            pluck="name",
            ignore_permissions=True,
        )
        frontier = [r for r in rows if r not in seen]
        seen.update(frontier)
        found.extend(frontier)
        depth += 1
    return found


def manager_chain(employee_id):
    """Employee ids up the reporting line, nearest manager first.
    If the employee has no reports_to, the HR Manager employee is treated as
    their effective manager so they are never outside all reporting chains."""
    chain = []
    seen = {employee_id}
    current = get_effective_manager(employee_id)
    while current and current not in seen and len(chain) < MAX_TREE_DEPTH:
        seen.add(current)
        chain.append(current)
        current = frappe.db.get_value("Employee", current, "reports_to")
    return chain


def manageable_employees(user=None):
    """Employee ids `user` may act for: themselves plus their whole subtree."""
    own = employee_for(user)
    if not own:
        return []
    return [own, *descendants(own)]


# Kept for callers that predate the subtree change.
visible_employees = manageable_employees


def employee_query_conditions(user=None, doctype=None):
    """SQL fragment appended to list queries for employee-scoped doctypes."""
    user = user or frappe.session.user
    if user == "Administrator" or _has_full_access(user):
        return ""
    if not doctype:
        return "1=0"

    allowed = manageable_employees(user)
    if not allowed:
        # Signed in, but not an employee — no personal records to see.
        return "1=0"

    table = f"`tab{doctype}`"
    joined = ", ".join(frappe.db.escape(e) for e in allowed)
    return f"{table}.employee in ({joined})"


def has_employee_permission(doc, ptype=None, user=None):
    """Document-level counterpart of employee_query_conditions."""
    user = user or frappe.session.user
    if user == "Administrator" or _has_full_access(user):
        return True

    allowed = manageable_employees(user)
    if not allowed:
        return False

    employee = doc.get("employee") if hasattr(doc, "get") else None
    if not employee or employee not in allowed:
        return False

    if ptype in ("write", "delete", "cancel"):
        # Only the person who raised the record may revise or withdraw it.
        # `owner` is unset while a doc is still being built, which is the create
        # path — that is covered by the `employee in allowed` check above.
        owner = doc.get("owner")
        return not owner or owner == user

    return True


# ── Per-doctype entry points ─────────────────────────────────────────────────
# Frappe calls query conditions as fn(user) with the doctype baked into the hook
# key, so each doctype needs its own thin wrapper.

def individual_goal_query(user=None):
    return employee_query_conditions(user, "Individual Goal")


def kpi_query(user=None):
    return employee_query_conditions(user, "KPI")


# ── The review record: Alvoraa Appraisal Extension (slice 010, SEC-5, SEC-27) ─
#
# Employees and managers have no role on it at all; every portal read and write
# goes through the review endpoints and their stage rules. HR Manager, HR User
# and System Manager keep a desk role, but the desk now follows the SAME rule as
# the portal (decision 15):
#
#   read   a review in HR Review or Completed, for a company they look after;
#          or a review in their own line once the self-review has been sent.
#          Never their own review (it holds their potential rating, PRIV-1).
#   write  nobody below Administrator. Desk edits would skip every stage and
#          stamp rule the portal enforces.
#
# The copies (Alvoraa Review Item) are child rows, read through this record.
# A tenant's Custom DocPerm that re-grants Employee does not reopen it either:
# these hooks deny anyone without an HR role.

REVIEW_DRAFT_STAGES = ("", "Not Started", "Employee Review")
REVIEW_HR_STAGES = ("HR Review", "Completed")


def appraisal_extension_query(user=None):
    user = user or frappe.session.user
    if user == "Administrator":
        return ""
    if not _has_full_access(user):
        return "1=0"

    from hrms.alvoraa_hr_core.access import permitted_companies

    table = "`tabAlvoraa Appraisal Extension`"
    clauses = []
    companies = permitted_companies(user)
    if companies:
        joined = ", ".join(frappe.db.escape(c) for c in companies)
        clauses.append(
            f"({table}.review_status in ('HR Review', 'Completed') and {table}.employee in "
            f"(select `name` from `tabEmployee` where `company` in ({joined})))"
        )
    own = employee_for(user)
    if own:
        line = frappe.db.get_value("Employee", own, ["lft", "rgt"], as_dict=True)
        if line and line.lft and line.rgt:
            clauses.append(
                f"(ifnull({table}.review_status, '') not in ('', 'Not Started', 'Employee Review') "
                f"and {table}.employee in (select `name` from `tabEmployee` "
                f"where `lft` > {int(line.lft)} and `rgt` < {int(line.rgt)}))"
            )
    if not clauses:
        return "1=0"
    condition = "(" + " or ".join(clauses) + ")"
    if own:
        condition += f" and ifnull({table}.employee, '') != {frappe.db.escape(own)}"
    return condition


def has_appraisal_extension_permission(doc, ptype=None, user=None):
    user = user or frappe.session.user
    if user == "Administrator":
        return True
    if ptype not in ("read", "select"):
        return False
    if not _has_full_access(user):
        return False

    employee = doc.get("employee") if hasattr(doc, "get") else None
    if not employee:
        return False
    own = employee_for(user)
    if own and employee == own:
        return False

    status = doc.get("review_status") or ""
    if status in REVIEW_HR_STAGES:
        from hrms.alvoraa_hr_core.access import permitted_companies

        if frappe.db.get_value("Employee", employee, "company") in permitted_companies(user):
            return True
    if own and status not in REVIEW_DRAFT_STAGES and employee in descendants(own):
        return True
    return False


# ── A review's change history and notes: Version and Comment (security review B1) ─
#
# Frappe keeps a Version row for every save of the review record (track_changes),
# and group D writes its audit notes (removal reasons, answers for a former rater)
# as Comment rows. Both core doctypes let every System Manager, and for Comment
# every Website Manager, list all rows over REST. A Version row holds whole copy
# rows: ratings, potential, self-review drafts.
#
# So a Version or Comment about a review record, one of its copies, or an HRMS
# Appraisal is readable only by someone who may read that record itself, under
# the same stage, company and "never your own" rule. Rows about every other
# doctype are untouched. Audit notes on the review record are never edited or
# deleted below Administrator.

REVIEW_HISTORY_DOCTYPES = ("Alvoraa Appraisal Extension", "Alvoraa Review Item", "Appraisal")
_HISTORY_FIELDS = {"Version": ("ref_doctype", "docname"), "Comment": ("reference_doctype", "reference_name")}
_READ_PTYPES = ("read", "select", "report", "export", "print", "email", "share")


def _readable_names_sql(doctype, user):
    """A SELECT of the names of `doctype` this user may read under the review rule."""
    if doctype == "Alvoraa Appraisal Extension":
        return (f"select `name` from `tabAlvoraa Appraisal Extension` "
                f"where {appraisal_extension_query(user) or '1=1'}")
    if doctype == "Alvoraa Review Item":
        return ("select `name` from `tabAlvoraa Review Item` "
                "where `parenttype` = 'Alvoraa Appraisal Extension' and `parent` in ("
                + _readable_names_sql("Alvoraa Appraisal Extension", user) + ")")
    return f"select `name` from `tabAppraisal` where {appraisal_query(user) or '1=1'}"


def _history_query(table, user):
    user = user or frappe.session.user
    if user == "Administrator":
        return ""
    dt_field, name_field = _HISTORY_FIELDS[table]
    t = f"`tab{table}`"
    guarded = ", ".join(frappe.db.escape(dt) for dt in REVIEW_HISTORY_DOCTYPES)
    condition = f"ifnull({t}.`{dt_field}`, '') not in ({guarded})"
    if _has_full_access(user):
        for dt in REVIEW_HISTORY_DOCTYPES:
            condition += (f" or ({t}.`{dt_field}` = {frappe.db.escape(dt)} "
                          f"and {t}.`{name_field}` in ({_readable_names_sql(dt, user)}))")
    return f"({condition})"


def version_query(user=None, doctype=None):
    return _history_query("Version", user)


def comment_query(user=None, doctype=None):
    return _history_query("Comment", user)


def _may_read_review_record(doctype, name, user):
    """Can this user read that review record, copy or appraisal? Fails closed."""
    if not name:
        return False
    if doctype == "Alvoraa Review Item":
        parent = frappe.db.get_value(
            "Alvoraa Review Item", {"name": name, "parenttype": "Alvoraa Appraisal Extension"}, "parent"
        )
        return _may_read_review_record("Alvoraa Appraisal Extension", parent, user)
    if doctype == "Alvoraa Appraisal Extension":
        row = frappe.db.get_value(doctype, name, ["employee", "review_status"], as_dict=True)
        return bool(row) and has_appraisal_extension_permission(row, "read", user)
    row = frappe.db.get_value("Appraisal", name, ["name", "employee", "docstatus"], as_dict=True)
    return bool(row) and has_appraisal_permission(row, "read", user)


def has_review_history_permission(doc, ptype=None, user=None):
    """has_permission for Version and Comment: the rule of the record the row is about."""
    user = user or frappe.session.user
    if user == "Administrator":
        return True
    dt_field, name_field = _HISTORY_FIELDS.get(doc.get("doctype"), (None, None))
    ref_doctype = doc.get(dt_field) if dt_field else None
    if ref_doctype not in REVIEW_HISTORY_DOCTYPES:
        return True
    if ptype not in _READ_PTYPES and ref_doctype != "Appraisal":
        # The review record's history and audit notes are a record: nobody
        # below Administrator adds to, edits or deletes them by hand.
        return False
    return _may_read_review_record(ref_doctype, doc.get(name_field), user)


# ── HRMS Appraisal in the desk (security review M4) ─────────────────────────
#
# The Appraisal holds the scores the review's manager ratings produce. HR's desk
# reads of it follow the review record's rule (decisions 15, 16, 27):
#
#   read / write  the review is in HR Review or Completed, for a subject in a
#                 company the caller looks after; or the review is in the
#                 caller's own line once the self-review has been sent. A
#                 submitted appraisal with no review record at all is history
#                 and counts as completed.
#   create        for a subject in a company the caller looks after.
#   never         the caller's own appraisal, and nobody without an HR role.


def appraisal_query(user=None, doctype=None):
    user = user or frappe.session.user
    if user == "Administrator":
        return ""
    if not _has_full_access(user):
        return "1=0"

    from hrms.alvoraa_hr_core.access import permitted_companies

    t = "`tabAppraisal`"
    ext = "`tabAlvoraa Appraisal Extension`"
    clauses = []
    companies = permitted_companies(user)
    if companies:
        joined = ", ".join(frappe.db.escape(c) for c in companies)
        clauses.append(
            f"({t}.employee in (select `name` from `tabEmployee` where `company` in ({joined})) and ("
            f"exists (select 1 from {ext} where {ext}.appraisal = {t}.name "
            f"and {ext}.review_status in ('HR Review', 'Completed')) "
            f"or ({t}.docstatus = 1 and not exists (select 1 from {ext} where {ext}.appraisal = {t}.name))))"
        )
    own = employee_for(user)
    if own:
        line = frappe.db.get_value("Employee", own, ["lft", "rgt"], as_dict=True)
        if line and line.lft and line.rgt:
            clauses.append(
                f"(exists (select 1 from {ext} where {ext}.appraisal = {t}.name "
                f"and ifnull({ext}.review_status, '') not in ('', 'Not Started', 'Employee Review')) "
                f"and {t}.employee in (select `name` from `tabEmployee` "
                f"where `lft` > {int(line.lft)} and `rgt` < {int(line.rgt)}))"
            )
    if not clauses:
        return "1=0"
    condition = "(" + " or ".join(clauses) + ")"
    if own:
        condition += f" and ifnull({t}.employee, '') != {frappe.db.escape(own)}"
    return condition


def has_appraisal_permission(doc, ptype=None, user=None):
    user = user or frappe.session.user
    if user == "Administrator":
        return True
    if not _has_full_access(user):
        return False
    employee = doc.get("employee") if hasattr(doc, "get") else None
    if not employee:
        # An appraisal being built in the desk before its employee is chosen.
        return ptype == "create" and not doc.get("name")
    own = employee_for(user)
    if own and employee == own:
        return False

    from hrms.alvoraa_hr_core.access import permitted_companies

    in_company = frappe.db.get_value("Employee", employee, "company") in permitted_companies(user)
    name = doc.get("name")
    if ptype == "create" or not name or not frappe.db.exists("Appraisal", name):
        return in_company

    status = frappe.db.get_value("Alvoraa Appraisal Extension", {"appraisal": name}, "review_status")
    if status is None:
        # No review record: only a submitted appraisal (history) is readable.
        return in_company and frappe.db.get_value("Appraisal", name, "docstatus") == 1
    if in_company and status in REVIEW_HR_STAGES:
        return True
    return bool(own and (status or "") not in REVIEW_DRAFT_STAGES and employee in descendants(own))
