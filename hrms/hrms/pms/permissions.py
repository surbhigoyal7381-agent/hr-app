import frappe


def _get_employee(user=None):
    user = user or frappe.session.user
    return frappe.db.get_value("Employee", {"user_id": user}, "name")


def _is_hr(user=None):
    user = user or frappe.session.user
    return frappe.db.exists("Has Role", {"parent": user, "role": ["in", ["HR Manager", "HR User", "System Manager"]]})


# ── PMS Review Record ────────────────────────────────────────────────────────

def review_record_query(user):
    if _is_hr(user):
        return ""
    emp = _get_employee(user)
    if not emp:
        return "1=0"
    reports = frappe.get_all("Employee", filters={"reports_to": emp}, pluck="name")
    accessible = [f"'{e}'" for e in [emp] + reports]
    return f"`tabPMS Review Record`.employee in ({','.join(accessible)})"


def has_review_record_permission(doc, user=None, ptype="read"):
    user = user or frappe.session.user
    if _is_hr(user):
        return True
    emp = _get_employee(user)
    if not emp:
        return False
    if doc.employee == emp:
        # employees can read/write but not see potential_rating unless unlocked
        return True
    reports = frappe.get_all("Employee", filters={"reports_to": emp}, pluck="name")
    if doc.employee in reports:
        return True
    additional_managers = [r.manager for r in (doc.additional_managers or [])]
    return emp in additional_managers


# ── PMS Business Goal ────────────────────────────────────────────────────────

def business_goal_query(user):
    if _is_hr(user):
        return ""
    emp = _get_employee(user)
    if not emp:
        return "1=0"
    reports = frappe.get_all("Employee", filters={"reports_to": emp}, pluck="name")
    accessible = [f"'{e}'" for e in [emp] + reports]
    return (
        f"`tabPMS Business Goal`.employee in ({','.join(accessible)}) "
        f"AND `tabPMS Business Goal`.is_review_draft = 0"
    )


# ── PMS Check-in ─────────────────────────────────────────────────────────────

def checkin_query(user):
    if _is_hr(user):
        return ""
    emp = _get_employee(user)
    if not emp:
        return "1=0"
    return (
        f"(`tabPMS Check In`.employee = '{emp}' OR `tabPMS Check In`.manager = '{emp}')"
    )


def has_checkin_permission(doc, user=None, ptype="read"):
    user = user or frappe.session.user
    if _is_hr(user):
        return True
    emp = _get_employee(user)
    return emp in (doc.employee, doc.manager)


# ── PMS Upward Feedback ───────────────────────────────────────────────────────

def upward_feedback_query(user):
    if _is_hr(user):
        return ""
    emp = _get_employee(user)
    if not emp:
        return "1=0"
    respondent_hash = _respondent_hash(emp)
    return (
        f"(`tabPMS Upward Feedback`.manager_being_reviewed = '{emp}' "
        f"OR `tabPMS Upward Feedback`.respondent_hash = '{respondent_hash}')"
    )


def has_upward_feedback_permission(doc, user=None, ptype="read"):
    user = user or frappe.session.user
    if _is_hr(user):
        return True
    emp = _get_employee(user)
    if not emp:
        return False
    if doc.manager_being_reviewed == emp:
        return ptype == "read"
    return doc.respondent_hash == _respondent_hash(emp)


def _respondent_hash(emp):
    import hashlib
    return hashlib.sha256(emp.encode()).hexdigest()


# ── PMS Calibration Session ───────────────────────────────────────────────────

def calibration_session_query(user):
    if _is_hr(user):
        return ""
    return "1=0"


# ── PMS Talent Flag ───────────────────────────────────────────────────────────

def talent_flag_query(user):
    if _is_hr(user):
        return ""
    return "1=0"


def has_talent_flag_permission(doc, user=None, ptype="read"):
    user = user or frappe.session.user
    return bool(_is_hr(user))
