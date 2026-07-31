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
