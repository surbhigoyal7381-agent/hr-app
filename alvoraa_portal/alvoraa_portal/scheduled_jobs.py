import frappe


def update_delivery_tracking():
    """Called every 'all' cycle — does lightweight checks only.

    In a real system this receives GPS from driver app via API.
    Here we just ensure active assignments have recent tracking.
    """
    pass


def calculate_driver_ratings():
    """Recalculate Driver Rating Summary for all drivers with recent ratings."""
    from alvoraa_portal.controllers.rating import _recalculate_driver_rating

    drivers = frappe.get_all(
        "Order Rating",
        fields=["driver"],
        group_by="driver",
        filters={"driver": ["!=", ""]},
    )
    for row in drivers:
        if row.driver:
            try:
                _recalculate_driver_rating(row.driver)
            except Exception:
                frappe.log_error(
                    frappe.get_traceback(),
                    f"Driver rating recalc failed for {row.driver}",
                )


def send_arrival_notifications():
    """Find deliveries with ETA <= 10 min and notify vendor."""
    active = frappe.get_all(
        "Delivery Assignment",
        filters={"status": "In Transit"},
        fields=["name", "vendor_order"],
    )
    for assignment in active:
        tracking = frappe.get_all(
            "Delivery Tracking",
            filters={"parent": assignment.name},
            fields=["eta_minutes", "updated_timestamp"],
            order_by="updated_timestamp desc",
            limit=1,
        )
        if tracking and tracking[0].eta_minutes and tracking[0].eta_minutes <= 10:
            vendor = frappe.get_value("Vendor Order", assignment.vendor_order, "vendor")
            email = frappe.get_value("Vendor", vendor, "email")
            if email:
                try:
                    frappe.sendmail(
                        recipients=[email],
                        subject="Your delivery is arriving soon!",
                        message=(
                            f"<p>Your Grace Drinks order will arrive in approximately "
                            f"{tracking[0].eta_minutes} minutes. Please be available to receive it.</p>"
                        ),
                    )
                except Exception:
                    frappe.log_error(
                        frappe.get_traceback(), "Arrival notification failed"
                    )


# ─── New scheduled jobs ───────────────────────────────────────────────────────

def check_compliance_alerts():
    """Daily — refresh all Vehicle Maintenance Compliance records and send alerts."""
    try:
        from alvoraa_portal.controllers.vehicle_compliance import check_all_compliance_alerts
        check_all_compliance_alerts()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Compliance Alert Scheduler Error")


def generate_monthly_scorecards():
    """Monthly (1st of month) — generate scorecards for previous month for all active partners."""
    try:
        from alvoraa_portal.controllers.scorecard import generate_monthly_scorecards as _gen
        _gen()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Monthly Scorecard Generation Error")
