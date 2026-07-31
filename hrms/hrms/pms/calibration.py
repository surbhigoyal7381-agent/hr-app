import frappe


@frappe.whitelist()
def get_calibration_data(session_name):
    session = frappe.get_doc("PMS Calibration Session", session_name)
    if not frappe.has_permission("PMS Calibration Session", "read", session_name):
        frappe.throw("Not permitted", frappe.PermissionError)

    scope_filters = _build_scope_filters(session.scope)
    records = frappe.get_all(
        "PMS Review Record",
        filters=[["cycle", "=", session.cycle], *scope_filters],
        fields=[
            "name", "employee", "employee_name", "primary_manager",
            "overall_rating", "potential_rating", "status",
        ],
        order_by="employee_name asc",
    )
    return {"session": session.as_dict(), "records": records}


def _build_scope_filters(scope_rows):
    if not scope_rows:
        return []
    # OR logic across rows: use raw SQL via frappe.db.sql for complex OR
    return []


@frappe.whitelist()
def lock_session(session_name):
    if not frappe.has_permission("PMS Calibration Session", "write", session_name):
        frappe.throw("Not permitted", frappe.PermissionError)
    frappe.db.set_value("PMS Calibration Session", session_name, "status", "Locked")
    session = frappe.get_doc("PMS Calibration Session", session_name)
    session._apply_adjustments()
    return {"status": "locked"}
