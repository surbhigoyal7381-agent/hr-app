"""
Grace Group – Fleet Reallocation Warning
Hook: Leave Application → on_submit

When a Logistics-department driver submits a Leave Application,
this hook checks for an active vehicle assignment and fires an urgent
real-time alert + Notification document to the Logistics Manager.
"""

import frappe
from frappe.utils import getdate


def on_submit(doc, method=None):
    """Triggered on Leave Application submit."""
    emp = frappe.get_doc("Employee", doc.employee)

    # Only act for Logistics department employees
    if not emp.department or "Logistics" not in emp.department:
        return

    # Only drivers (Delivery Executives) need vehicle reallocation
    if emp.designation != "Delivery Executive":
        return

    vehicle = _find_active_vehicle(doc.employee, doc.from_date, doc.to_date)
    if not vehicle:
        return

    logistics_manager = _get_logistics_manager()
    if not logistics_manager:
        frappe.log_error(
            "Logistics Manager not found for fleet reallocation alert",
            "Fleet Reallocation Warning",
        )
        return

    message = (
        f"URGENT: {emp.employee_name} is on approved leave "
        f"from {doc.from_date} to {doc.to_date}. "
        f"Please reallocate Vehicle {vehicle} immediately "
        f"to prevent Q-Comm SLA breaches."
    )

    _send_realtime_alert(logistics_manager["user"], message)
    _create_notification_doc(
        employee=doc.employee,
        employee_name=emp.employee_name,
        from_date=doc.from_date,
        to_date=doc.to_date,
        vehicle=vehicle,
        recipient_employee=logistics_manager["employee"],
        recipient_user=logistics_manager["user"],
        message=message,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _find_active_vehicle(employee, from_date, to_date):
    """Return the most recent vehicle linked to this employee via Vehicle Log."""
    vehicle = frappe.db.get_value(
        "Vehicle Log",
        filters={"employee": employee},
        fieldname="license_plate",
        order_by="date desc",
    )
    return vehicle


def _get_logistics_manager():
    """Return the Logistics Manager's employee ID and linked user."""
    emp_id = frappe.db.get_value(
        "Employee",
        {"designation": "Logistics Manager", "status": "Active"},
        "name",
    )
    if not emp_id:
        return None

    # Prefer company_email, fall back to user record
    user_email = frappe.db.get_value("Employee", emp_id, "user_id") or \
                 frappe.db.get_value("Employee", emp_id, "company_email")

    if not user_email:
        # Try to find user by employee_name
        emp_name = frappe.db.get_value("Employee", emp_id, "employee_name")
        user_email = frappe.db.get_value("User", {"full_name": emp_name}, "name")

    return {"employee": emp_id, "user": user_email} if user_email else None


def _send_realtime_alert(user, message):
    """Push a real-time toast notification to the Logistics Manager's desk."""
    try:
        frappe.publish_realtime(
            event="msgprint",
            message=message,
            user=user,
            after_commit=True,
        )
    except Exception as e:
        frappe.log_error(f"Realtime alert failed: {e}", "Fleet Reallocation Warning")


def _create_notification_doc(
    employee,
    employee_name,
    from_date,
    to_date,
    vehicle,
    recipient_employee,
    recipient_user,
    message,
):
    """Create a persistent Notification Log entry for audit trail."""
    try:
        frappe.get_doc({
            "doctype": "Notification Log",
            "subject": f"Fleet Reallocation Required – {employee_name}",
            "email_content": message,
            "for_user": recipient_user,
            "type": "Alert",
            "document_type": "Leave Application",
            "from_user": frappe.session.user,
        }).insert(ignore_permissions=True)
    except Exception:
        # Notification Log may not exist in all Frappe versions — use frappe.sendmail as fallback
        try:
            frappe.sendmail(
                recipients=[recipient_user],
                subject=f"URGENT: Fleet Reallocation Required – {employee_name}",
                message=message,
                now=True,
            )
        except Exception as mail_err:
            frappe.log_error(
                f"Fleet reallocation email failed: {mail_err}",
                "Fleet Reallocation Warning",
            )
