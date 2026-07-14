import frappe
from frappe.utils import today, date_diff, now_datetime


# ─── DocType event hooks ──────────────────────────────────────────────────────

def before_save(doc, method=None):
    _calculate_expiry_fields(doc)
    _set_alert_status(doc)


def _calculate_expiry_fields(doc):
    if doc.compliance_expiry_date:
        days = date_diff(doc.compliance_expiry_date, today())
        doc.days_until_expiry = days
        doc.is_expired = 1 if days < 0 else 0
    else:
        doc.days_until_expiry = None
        doc.is_expired = 0


def _set_alert_status(doc):
    if not doc.compliance_expiry_date:
        doc.alert_status = "Clear"
        return
    days = doc.days_until_expiry if doc.days_until_expiry is not None else 9999
    if days < 0:
        doc.alert_status = "Overdue"
    elif days <= 7:
        doc.alert_status = "Critical"
    elif days <= 30:
        doc.alert_status = "Warning"
    else:
        doc.alert_status = "Clear"


# ─── Scheduled job (called daily) ────────────────────────────────────────────

def check_all_compliance_alerts():
    """Called by scheduler daily. Re-evaluate all compliance records and send alerts."""
    # First refresh expiry calculations on all active records
    records = frappe.get_all(
        "Vehicle Maintenance Compliance",
        filters={"compliance_expiry_date": ["is", "set"]},
        fields=[
            "name", "vehicle_registration", "partner", "compliance_type",
            "compliance_expiry_date", "notification_recipient",
        ],
    )

    for rec in records:
        days = date_diff(rec.compliance_expiry_date, today())
        if days < 0:
            alert = "Overdue"
        elif days <= 7:
            alert = "Critical"
        elif days <= 30:
            alert = "Warning"
        else:
            alert = "Clear"

        # Persist updated status and days
        frappe.db.set_value(
            "Vehicle Maintenance Compliance",
            rec.name,
            {
                "days_until_expiry": days,
                "is_expired": 1 if days < 0 else 0,
                "alert_status": alert,
                # Reset notification flag when compliance re-enters warning window
                "alert_notification_sent": 0 if alert in ("Warning", "Critical", "Overdue") and days > -30 else 1,
            },
        )

    frappe.db.commit()

    # Now send notifications for Critical/Overdue items not yet notified
    to_notify = frappe.get_all(
        "Vehicle Maintenance Compliance",
        filters={
            "alert_status": ["in", ["Critical", "Overdue"]],
            "alert_notification_sent": 0,
        },
        fields=[
            "name", "vehicle_registration", "partner", "compliance_type",
            "alert_status", "compliance_expiry_date", "days_until_expiry",
            "notification_recipient",
        ],
    )

    for rec in to_notify:
        _send_compliance_alert(rec)

    # Also send Warning notifications once (first time entering window)
    to_warn = frappe.get_all(
        "Vehicle Maintenance Compliance",
        filters={
            "alert_status": "Warning",
            "alert_notification_sent": 0,
        },
        fields=[
            "name", "vehicle_registration", "partner", "compliance_type",
            "alert_status", "compliance_expiry_date", "days_until_expiry",
            "notification_recipient",
        ],
    )
    for rec in to_warn:
        _send_compliance_alert(rec)


def _send_compliance_alert(rec):
    days = rec.days_until_expiry or 0
    if days < 0:
        timing_msg = f"<b>EXPIRED {abs(days)} days ago</b>"
        urgency = "OVERDUE"
    elif days <= 7:
        timing_msg = f"<b>CRITICAL: expires in {days} days</b>"
        urgency = "CRITICAL"
    else:
        timing_msg = f"due for renewal in {days} days"
        urgency = "WARNING"

    recipient = rec.notification_recipient or "ops@gracedrinks.in"
    try:
        frappe.sendmail(
            recipients=[recipient],
            subject=f"[{urgency}] Vehicle Compliance Alert — {rec.vehicle_registration} | {rec.compliance_type}",
            message=f"""
            <p><strong>Vehicle Compliance Alert — {urgency}</strong></p>
            <table border="1" cellpadding="6" cellspacing="0">
              <tr><td>Record</td><td>{rec.name}</td></tr>
              <tr><td>Vehicle Registration</td><td><b>{rec.vehicle_registration}</b></td></tr>
              <tr><td>Delivery Partner</td><td>{rec.partner}</td></tr>
              <tr><td>Compliance Type</td><td>{rec.compliance_type}</td></tr>
              <tr><td>Expiry Date</td><td><b>{rec.compliance_expiry_date}</b> ({timing_msg})</td></tr>
            </table>
            <p>Please take immediate action to renew this compliance item.
            A vehicle with an expired compliance document must not be used for deliveries.</p>
            """,
        )
        frappe.db.set_value(
            "Vehicle Maintenance Compliance",
            rec.name,
            {
                "alert_notification_sent": 1,
                "alert_notification_date": now_datetime(),
            },
        )
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(str(e), f"Compliance Alert Email Failed — {rec.name}")


@frappe.whitelist()
def get_compliance_dashboard(hub_name=None):
    """Return compliance summary for the manager dashboard."""
    filters = {}
    if hub_name:
        partner_names = frappe.get_all(
            "Delivery Partner",
            filters={"hub_assigned": hub_name},
            pluck="name",
        )
        if partner_names:
            filters["partner"] = ["in", partner_names]

    records = frappe.get_all(
        "Vehicle Maintenance Compliance",
        filters=filters,
        fields=["alert_status", "compliance_type", "vehicle_registration", "partner",
                "compliance_expiry_date", "days_until_expiry"],
    )

    summary = {"Clear": 0, "Warning": 0, "Critical": 0, "Overdue": 0}
    alerts = []
    for rec in records:
        status = rec.alert_status or "Clear"
        summary[status] = summary.get(status, 0) + 1
        if status in ("Warning", "Critical", "Overdue"):
            alerts.append(rec)

    alerts.sort(key=lambda r: r.days_until_expiry if r.days_until_expiry is not None else 9999)
    return {"summary": summary, "alerts": alerts[:20]}  # top 20 most urgent
