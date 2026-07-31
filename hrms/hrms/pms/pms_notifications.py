import frappe


NOTIFICATION_MATRIX = {
    "Self Review Open": {
        "recipients": ["employee"],
        "subject": "Your performance review is open for self-assessment",
        "template": "pms_self_review_open",
    },
    "Manager Preparation": {
        "recipients": ["primary_manager"],
        "subject": "Employee self-review submitted — please complete manager assessment",
        "template": "pms_manager_prep",
    },
    "Employee Invited to Dialogue": {
        "recipients": ["employee"],
        "subject": "You have been invited to your performance dialogue",
        "template": "pms_dialogue_invite",
    },
    "Dialogue Complete": {
        "recipients": ["employee", "primary_manager"],
        "subject": "Performance dialogue marked complete",
        "template": "pms_dialogue_complete",
    },
    "Final Form With Employee": {
        "recipients": ["employee"],
        "subject": "Your final performance review is ready for acknowledgement",
        "template": "pms_final_form",
    },
    "Returned for Amendment": {
        "recipients": ["employee"],
        "subject": "Your review has been returned for amendment",
        "template": "pms_returned",
    },
    "Submitted by Employee": {
        "recipients": ["primary_manager", "hr"],
        "subject": "Employee has acknowledged and submitted their review",
        "template": "pms_employee_submitted",
    },
}


def send_status_change_notification(review_record, old_status, new_status):
    cfg = NOTIFICATION_MATRIX.get(new_status)
    if not cfg:
        return

    doc = frappe.get_doc("PMS Review Record", review_record)
    employee_email = frappe.db.get_value("Employee", doc.employee, "company_email") or \
                     frappe.db.get_value("Employee", doc.employee, "prefered_email")
    manager_email = frappe.db.get_value("Employee", doc.primary_manager, "company_email") if doc.primary_manager else None

    recipients = []
    for r in cfg["recipients"]:
        if r == "employee" and employee_email:
            recipients.append(employee_email)
        elif r == "primary_manager" and manager_email:
            recipients.append(manager_email)
        elif r == "hr":
            hr_emails = frappe.get_all("User", filters={"role_profile_name": ["like", "%HR%"]}, pluck="email")
            recipients.extend(hr_emails)

    if not recipients:
        return

    frappe.sendmail(
        recipients=list(set(recipients)),
        subject=cfg["subject"],
        message=_build_message(doc, cfg["template"]),
    )


def _build_message(doc, template_key):
    return (
        f"<p>Review Record: <strong>{doc.name}</strong></p>"
        f"<p>Employee: <strong>{doc.employee_name}</strong></p>"
        f"<p>Cycle: <strong>{doc.cycle_name}</strong></p>"
        f"<p>Current Status: <strong>{doc.status}</strong></p>"
        f"<p>Please log in to the HR portal to take the required action.</p>"
    )


def send_overdue_stage_alerts():
    """Daily job: find records past their stage deadline and alert."""
    today = frappe.utils.today()
    overdue = frappe.db.sql(
        """
        SELECT r.name, r.employee, r.employee_name, r.status, r.cycle
        FROM `tabPMS Review Record` r
        JOIN `tabPMS Cycle` c ON c.name = r.cycle
        JOIN `tabPMS Cycle Stage Deadline` d ON d.parent = c.name AND d.stage = r.status
        WHERE DATE_ADD(d.deadline, INTERVAL d.grace_days DAY) < %s
          AND r.status NOT IN ('Closed','Calibrated','Submitted by Employee')
        """,
        (today,),
        as_dict=True,
    )
    for rec in overdue:
        frappe.enqueue(
            "hrms.pms.pms_notifications.send_status_change_notification",
            review_record=rec.name,
            old_status=rec.status,
            new_status=rec.status,  # re-send as reminder
        )


def send_checkin_nudges():
    """Daily job: nudge managers who have no check-in in the last 30 days."""
    cutoff = frappe.utils.add_days(frappe.utils.today(), -30)
    managers_with_recent = frappe.db.sql_list(
        "SELECT DISTINCT manager FROM `tabPMS Check In` WHERE check_in_date >= %s", (cutoff,)
    )
    all_managers = frappe.get_all("Employee", filters={"reports_to": ["!=", ""]}, pluck="reports_to")
    unique_managers = list(set(all_managers))
    nudge_targets = [m for m in unique_managers if m not in managers_with_recent]
    for mgr in nudge_targets:
        email = frappe.db.get_value("Employee", mgr, "company_email") or \
                frappe.db.get_value("Employee", mgr, "prefered_email")
        if email:
            frappe.sendmail(
                recipients=[email],
                subject="Reminder: Schedule a check-in with your team",
                message="<p>You haven't logged a check-in in the last 30 days. "
                        "Please schedule one to keep your team's goals on track.</p>",
            )


def process_notification_queue():
    """Hourly job placeholder — notifications are enqueued directly."""
    pass
