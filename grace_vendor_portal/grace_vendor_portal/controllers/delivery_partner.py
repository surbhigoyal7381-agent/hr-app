import frappe
from frappe.utils import today, date_diff, now_datetime


def validate(doc, method=None):
    _sync_operational_status(doc)
    _check_compliance_expiry(doc)


def _sync_operational_status(doc):
    """Keep operational_status in sync with is_active and status fields."""
    if not doc.is_active or doc.status == "Terminated":
        doc.operational_status = "Inactive"
    elif doc.status == "Suspended":
        doc.operational_status = "Suspended"
    elif doc.status in ("Active", "On Leave"):
        doc.operational_status = "Active"


def _check_compliance_expiry(doc):
    """Warn if license, fitness cert, or insurance is expiring within 30 days."""
    warnings = []
    checks = [
        ("license_expiry", "Driving License"),
        ("vehicle_fitness_cert_expiry", "Vehicle Fitness Certificate"),
        ("insurance_expiry", "Vehicle Insurance"),
    ]
    for field, label in checks:
        expiry = doc.get(field)
        if expiry:
            days = date_diff(expiry, today())
            if days < 0:
                warnings.append(f"<b>{label}</b> EXPIRED {abs(days)} days ago. Action required immediately!")
            elif days <= 7:
                warnings.append(f"<b>{label}</b> expires in <b>{days} days</b> — CRITICAL, renew now.")
            elif days <= 30:
                warnings.append(f"<b>{label}</b> expires in {days} days — please renew.")
    if warnings:
        frappe.msgprint(
            "<br>".join(warnings),
            title="Compliance Warnings",
            indicator="orange",
        )


@frappe.whitelist()
def get_partner_performance_summary(partner_name):
    """Return aggregated performance summary for a delivery partner (for dashboard)."""
    partner = frappe.get_doc("Delivery Partner", partner_name)

    latest_scorecard = frappe.db.get_value(
        "Delivery Performance Scorecard",
        {"delivery_partner": partner_name},
        [
            "overall_delivery_score", "performance_level",
            "commission_earned", "bonuses_earned", "net_amount",
            "month", "year", "on_time_percentage", "avg_customer_rating",
        ],
        order_by="year desc, month desc",
        as_dict=True,
    )

    upcoming_maintenance = frappe.db.get_value(
        "Vehicle Maintenance Compliance",
        {"partner": partner_name, "alert_status": ["in", ["Warning", "Critical", "Overdue"]]},
        ["name", "compliance_type", "compliance_expiry_date", "alert_status"],
        order_by="compliance_expiry_date asc",
        as_dict=True,
    )

    return {
        "partner_name": partner.partner_name,
        "partner_type": partner.partner_type,
        "status": partner.status,
        "hub_assigned": partner.hub_assigned,
        "total_deliveries": partner.total_deliveries,
        "on_time_percentage": partner.on_time_delivery_percentage,
        "customer_rating": partner.customer_satisfaction_rating,
        "safety_incidents": partner.safety_incidents,
        "latest_scorecard": latest_scorecard,
        "compliance_alert": upcoming_maintenance,
    }


@frappe.whitelist()
def update_partner_stats_from_orders(partner_name):
    """Recalculate and persist delivery performance stats on the partner record.
    Call after bulk import or for manual refresh."""
    from frappe.utils import get_first_day, get_last_day
    from datetime import date

    today_date = frappe.utils.today()
    first_day = get_first_day(today_date)
    last_day = get_last_day(today_date)

    total = frappe.db.count(
        "Delivery Order",
        {"assigned_to_partner": partner_name, "current_status": "Delivered"},
    )
    on_time = frappe.db.count(
        "Delivery Order",
        {
            "assigned_to_partner": partner_name,
            "current_status": "Delivered",
            "on_time_status": "On-Time",
        },
    )
    cancellations = frappe.db.count(
        "Delivery Order",
        {
            "assigned_to_partner": partner_name,
            "current_status": "Cancelled",
            "delivery_date": ["between", [first_day, last_day]],
        },
    )
    returns_ = frappe.db.count(
        "Delivery Order",
        {
            "assigned_to_partner": partner_name,
            "current_status": "Returned",
            "delivery_date": ["between", [first_day, last_day]],
        },
    )

    avg_rating_row = frappe.db.sql(
        "SELECT AVG(average_rating) as r FROM `tabDelivery Feedback` WHERE delivery_partner=%s",
        partner_name,
        as_dict=True,
    )
    avg_rating = avg_rating_row[0].r if avg_rating_row else 0

    # GPS-based safety incidents (harsh_braking + speeding)
    safety_row = frappe.db.sql(
        """SELECT (SUM(harsh_braking) + SUM(speeding_alert)) as incidents
           FROM `tabVehicle Tracking` WHERE delivery_partner=%s""",
        partner_name,
        as_dict=True,
    )
    safety = int(safety_row[0].incidents or 0) if safety_row else 0

    frappe.db.set_value(
        "Delivery Partner",
        partner_name,
        {
            "total_deliveries": total,
            "on_time_delivery_percentage": round((on_time / total * 100), 2) if total else 0,
            "customer_satisfaction_rating": round(avg_rating or 0, 2),
            "safety_incidents": safety,
            "cancellations_this_month": cancellations,
            "returns_initiated_this_month": returns_,
        },
    )
    frappe.db.commit()
    return {"updated": True, "total_deliveries": total}


@frappe.whitelist()
def get_today_orders_for_partner(partner_name):
    """Used by the vendor portal / driver app to load today's order list."""
    from frappe.utils import today as frappe_today
    orders = frappe.get_all(
        "Delivery Order",
        filters={
            "assigned_to_partner": partner_name,
            "delivery_date": frappe_today(),
            "current_status": ["not in", ["Delivered", "Cancelled", "Returned"]],
        },
        fields=[
            "name", "customer_name", "customer_phone",
            "delivery_address", "delivery_city", "delivery_coordinates",
            "delivery_time_slot", "current_status", "grand_total",
            "is_fragile", "requires_signature", "requires_photo",
            "special_instructions",
        ],
        order_by="delivery_time_slot asc",
    )
    return orders
