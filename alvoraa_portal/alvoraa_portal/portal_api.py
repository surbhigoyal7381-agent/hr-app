import frappe
from frappe.utils import now_datetime

HUB_LAT = 30.7060
HUB_LNG = 76.8001

WAREHOUSE_NAME  = "Grace Warehouse"
WAREHOUSE_PHONE = "98761-00099"

ACTIVE_STATUSES = ["In Transit", "At Location", "Nearby", "Assigned", "Picked Up"]

VALID_TRANSITIONS = {
    "Assigned": "Picked Up",
    "Picked Up": "In Transit",
    "In Transit": "Nearby",
    "Nearby": "At Location",
    "At Location": "Delivered",
}

# Known vendor → destination coordinates (for demo map rendering)
VENDOR_COORDS = {
    "Raj Wine Shop":        (30.7404, 76.7871),
    "Metro Wines & Spirits":(30.7333, 76.8000),
    "Hotel Regent (Bar)":   (30.7181, 76.7918),
    "QuickStop Beverages":  (30.7110, 76.7220),
    "Celebrations Banquets":(30.6440, 76.8180),
}


@frappe.whitelist()
def get_portal_context():
    user = frappe.session.user
    if user == "Guest":
        return {"type": "guest"}

    vendor_user = frappe.db.get_value(
        "Vendor User", {"email": user}, ["vendor", "name"], as_dict=True
    )
    if vendor_user:
        vendor_name = frappe.db.get_value("Vendor", vendor_user.vendor, "vendor_name")
        return {
            "type": "vendor",
            "vendor_id": vendor_user.vendor,
            "vendor_name": vendor_name,
            "vendor_user": vendor_user.name,
        }

    partner = frappe.db.get_value(
        "Delivery Partner",
        {"primary_email": user},
        ["name", "partner_name", "hub_assigned"],
        as_dict=True,
    )
    if partner:
        return {
            "type": "driver",
            "partner_id": partner.name,
            "partner_name": partner.partner_name,
            "hub_assigned": partner.hub_assigned,
        }

    return {"type": "admin"}


@frappe.whitelist()
def get_vendor_orders(vendor_id):
    """Return all Vendor Orders for a vendor with delivery assignment info."""
    orders = frappe.get_all(
        "Vendor Order",
        filters={"vendor": vendor_id},
        fields=["name", "order_date", "order_status", "total_amount",
                "rating_submitted", "delivery_assignment"],
        order_by="order_date desc",
        ignore_permissions=True,
    )

    for order in orders:
        order["has_tracking"] = order.get("order_status") in ("In Transit", "Dispatched", "Ready for Dispatch")
        order["driver_name"] = None
        order["vehicle_reg"] = None

        order["warehouse_name"]  = WAREHOUSE_NAME
        order["warehouse_phone"] = WAREHOUSE_PHONE
        order["driver_phone"]    = None

        if order.get("delivery_assignment"):
            assign = frappe.db.get_value(
                "Delivery Assignment",
                order["delivery_assignment"],
                ["driver", "driver_name", "vehicle_reg", "status"],
                as_dict=True,
            )
            if assign:
                order["driver_name"] = assign.get("driver_name")
                order["vehicle_reg"] = assign.get("vehicle_reg")
                if assign.get("driver"):
                    order["driver_phone"] = frappe.db.get_value(
                        "Delivery Partner", assign["driver"], "primary_phone"
                    )

    return orders


@frappe.whitelist()
def get_order_live_location(vendor_order):
    """
    Return live GPS location for a Vendor Order.
    Lookup: Vendor Order → Delivery Assignment → vehicle_reg → Vehicle Tracking.
    Falls back to most-recent demo tracking data so the map always shows something.
    """
    result = {
        "hub_lat": HUB_LAT,
        "hub_lng": HUB_LNG,
        "latest": None,
        "customer_lat": None,
        "customer_lng": None,
        "route_history": [],
        "driver_name": None,
        "vehicle_type": None,
    }

    # Resolve customer location for this vendor
    vendor = frappe.db.get_value("Vendor Order", vendor_order, "vendor")
    vendor_name = frappe.db.get_value("Vendor", vendor, "vendor_name") if vendor else ""
    cust_lat, cust_lng = VENDOR_COORDS.get(vendor_name, (30.7333, 76.7794))
    result["customer_lat"] = cust_lat
    result["customer_lng"] = cust_lng

    # Try chain: Vendor Order → Delivery Assignment → vehicle_reg → Vehicle Tracking
    assign_name = frappe.db.get_value("Vendor Order", vendor_order, "delivery_assignment")
    vehicle_reg = None
    if assign_name:
        row = frappe.db.get_value(
            "Delivery Assignment",
            assign_name,
            ["vehicle_reg", "driver_name"],
            as_dict=True,
        )
        if row:
            vehicle_reg = row.get("vehicle_reg")
            result["driver_name"] = row.get("driver_name")

    tracking_rows = []
    if vehicle_reg:
        tracking_rows = frappe.db.sql(
            "SELECT latitude, longitude, speed, heading, recorded_timestamp, delivery_partner "
            "FROM `tabVehicle Tracking` WHERE vehicle_id = %s "
            "ORDER BY recorded_timestamp DESC LIMIT 1",
            vehicle_reg, as_dict=True,
        )

    # Demo fallback: use most recent tracking from any active delivery partner
    if not tracking_rows:
        tracking_rows = frappe.db.sql(
            "SELECT latitude, longitude, speed, heading, recorded_timestamp, delivery_partner "
            "FROM `tabVehicle Tracking` "
            "ORDER BY recorded_timestamp DESC LIMIT 1",
            as_dict=True,
        )
        if tracking_rows and tracking_rows[0].get("delivery_partner"):
            pinfo = frappe.db.get_value(
                "Delivery Partner",
                tracking_rows[0]["delivery_partner"],
                ["partner_name", "vehicle_type"],
                as_dict=True,
            ) or {}
            if not result["driver_name"]:
                result["driver_name"] = pinfo.get("partner_name")
            result["vehicle_type"] = pinfo.get("vehicle_type")

    if tracking_rows:
        r = tracking_rows[0]
        result["latest"] = {
            "latitude": r["latitude"],
            "longitude": r["longitude"],
            "speed": r.get("speed") or 0,
            "heading": r.get("heading") or 0,
            "recorded_timestamp": str(r["recorded_timestamp"]),
        }

        # Breadcrumb trail
        partner_id = tracking_rows[0].get("delivery_partner")
        if vehicle_reg:
            history = frappe.db.sql(
                "SELECT latitude, longitude, recorded_timestamp FROM `tabVehicle Tracking` "
                "WHERE vehicle_id = %s ORDER BY recorded_timestamp ASC LIMIT 20",
                vehicle_reg, as_dict=True,
            )
        elif partner_id:
            history = frappe.db.sql(
                "SELECT latitude, longitude, recorded_timestamp FROM `tabVehicle Tracking` "
                "WHERE delivery_partner = %s ORDER BY recorded_timestamp ASC LIMIT 20",
                partner_id, as_dict=True,
            )
        else:
            history = []
        result["route_history"] = [
            {"latitude": h["latitude"], "longitude": h["longitude"],
             "recorded_timestamp": str(h["recorded_timestamp"])}
            for h in history
        ]

    return result


def _safe_float(val, default=0.0):
    """Convert a value to float, returning default for None/empty string."""
    try:
        return float(val) if val not in (None, "", "None", "null") else default
    except (ValueError, TypeError):
        return default


@frappe.whitelist()
def update_driver_location(delivery_order, lat, lng, speed=0, heading=0, accuracy=10):
    """Called by driver browser to post real GPS update."""
    partner = frappe.db.get_value("Delivery Order", delivery_order, "assigned_to_partner")
    spd = _safe_float(speed)
    hdg = _safe_float(heading)
    acc = _safe_float(accuracy, 10.0)

    doc = frappe.get_doc({
        "doctype": "Vehicle Tracking",
        "delivery_order": delivery_order,
        "delivery_partner": partner or "",
        "latitude": _safe_float(lat),
        "longitude": _safe_float(lng),
        "speed": spd,
        "heading": hdg,
        "accuracy": acc,
        "recorded_timestamp": now_datetime(),
        "speeding_alert": 1 if spd > 60 else 0,
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return "ok"


@frappe.whitelist()
def get_driver_deliveries(partner_id):
    """Return all Delivery Orders for a partner, active ones first."""
    orders = frappe.get_all(
        "Delivery Order",
        filters={"assigned_to_partner": partner_id},
        fields=[
            "name", "customer_name", "delivery_address", "current_status",
            "delivery_date", "grand_total", "feedback_provided",
            "delivery_coordinates", "on_time_status",
        ],
        ignore_permissions=True,
    )

    def sort_key(order):
        status = order.get("current_status", "")
        if status in ACTIVE_STATUSES:
            return (0, ACTIVE_STATUSES.index(status))
        if status == "Delivered":
            return (1, 0)
        return (2, 0)

    orders.sort(key=sort_key)

    return {"orders": orders, "hub_lat": HUB_LAT, "hub_lng": HUB_LNG}


@frappe.whitelist()
def driver_advance_status(delivery_order, new_status):
    """Advance a Delivery Order to the next status."""
    # Use db.get_value to bypass doctype permissions (drivers are Website Users)
    current = frappe.db.get_value("Delivery Order", delivery_order, "current_status")
    if not current:
        frappe.throw("Delivery Order not found")

    expected_next = VALID_TRANSITIONS.get(current)
    if expected_next != new_status:
        frappe.throw(
            f"Invalid transition: {current} → {new_status}. Expected: {expected_next}"
        )

    now = now_datetime()
    frappe.db.set_value("Delivery Order", delivery_order, "current_status", new_status)
    frappe.db.set_value("Delivery Order", delivery_order, "status_updated_at", now)

    if new_status == "Delivered":
        delivery_date = frappe.db.get_value("Delivery Order", delivery_order, "delivery_date")
        on_time = "On-Time" if delivery_date and now.date() <= delivery_date else "Late"
        frappe.db.set_value("Delivery Order", delivery_order, "delivery_timestamp", now)
        frappe.db.set_value("Delivery Order", delivery_order, "on_time_status", on_time)

    frappe.db.commit()
    return new_status


@frappe.whitelist()
def submit_order_rating(order_name, rating, comment=""):
    """Submit a star rating for a delivered Vendor Order."""
    rating = int(rating)
    if not (1 <= rating <= 5):
        frappe.throw("Rating must be between 1 and 5.")

    # Prevent duplicate ratings
    if frappe.db.get_value("Vendor Order", order_name, "rating_submitted"):
        frappe.throw("Rating already submitted for this order.")

    vendor = frappe.db.get_value("Vendor Order", order_name, "vendor")

    # Create Order Rating record
    doc = frappe.get_doc({
        "doctype": "Order Rating",
        "vendor_order": order_name,
        "vendor": vendor,
        "rating_date": frappe.utils.today(),
        "order_quality_rating": rating,
        "delivery_timeliness_rating": rating,
        "driver_professionalism_rating": rating,
        "average_rating": float(rating),
        "comments": comment or "",
    })
    doc.insert(ignore_permissions=True)

    # Mark Vendor Order as rated
    frappe.db.set_value("Vendor Order", order_name, "rating_submitted", 1)
    frappe.db.commit()

    return {"success": True, "rating": rating}


@frappe.whitelist()
def get_all_vendors():
    return frappe.get_all(
        "Vendor",
        fields=["name", "vendor_name", "account_status"],
        ignore_permissions=True,
    )


@frappe.whitelist()
def get_all_partners():
    return frappe.get_all(
        "Delivery Partner",
        fields=["name", "partner_name", "hub_assigned"],
        ignore_permissions=True,
    )


@frappe.whitelist()
def get_delivery_route(delivery_order):
    """Return GPS breadcrumb trail recorded for a delivery order (static snapshot)."""
    rows = frappe.db.sql(
        "SELECT latitude, longitude FROM `tabVehicle Tracking` "
        "WHERE delivery_order = %s ORDER BY recorded_timestamp ASC LIMIT 200",
        delivery_order, as_dict=True,
    )
    return [{"lat": float(r["latitude"]), "lng": float(r["longitude"])} for r in rows]


@frappe.whitelist()
def get_drivers_performance():
    """Return aggregate performance stats for all delivery partners. Admin use only."""
    from frappe.utils import today as frappe_today
    today_str = frappe_today()

    partners = frappe.get_all(
        "Delivery Partner",
        fields=["name", "partner_name", "hub_assigned", "is_active",
                "vehicle_type", "primary_phone"],
        order_by="partner_name asc",
        ignore_permissions=True,
    )

    for p in partners:
        rows = frappe.db.sql(
            "SELECT current_status, on_time_status, grand_total FROM `tabDelivery Order`"
            " WHERE assigned_to_partner = %s",
            p["name"], as_dict=True,
        )
        delivered_rows = [r for r in rows if r.get("current_status") == "Delivered"]
        on_time_count = sum(1 for r in delivered_rows if r.get("on_time_status") == "On-Time")
        total_delivered = len(delivered_rows)

        today_rows = frappe.db.sql(
            "SELECT current_status FROM `tabDelivery Order`"
            " WHERE assigned_to_partner = %s AND delivery_date = %s",
            (p["name"], today_str), as_dict=True,
        )
        today_done   = sum(1 for r in today_rows if r.get("current_status") == "Delivered")
        today_active = sum(1 for r in today_rows if r.get("current_status") in ACTIVE_STATUSES)

        rating_row = frappe.db.sql(
            "SELECT AVG(orr.average_rating) AS avg_r, COUNT(orr.name) AS cnt"
            " FROM `tabOrder Rating` orr"
            " INNER JOIN `tabDelivery Order` doo"
            "   ON doo.special_instructions LIKE CONCAT('[VO: ', orr.vendor_order, ']%')"
            " WHERE doo.assigned_to_partner = %s",
            p["name"], as_dict=True,
        )
        avg_rating   = round(float(rating_row[0]["avg_r"] or 0), 1) if rating_row else 0
        rating_count = int(rating_row[0]["cnt"] or 0) if rating_row else 0

        p.update({
            "total_orders":    len(rows),
            "total_delivered": total_delivered,
            "on_time_count":   on_time_count,
            "on_time_rate":    round(on_time_count / total_delivered * 100) if total_delivered else 0,
            "today_total":     len(today_rows),
            "today_delivered": today_done,
            "today_active":    today_active,
            "avg_rating":      avg_rating,
            "rating_count":    rating_count,
        })

    partners.sort(key=lambda x: x["total_delivered"], reverse=True)

    all_delivered = sum(p["total_delivered"] for p in partners)
    all_on_time   = sum(p["on_time_count"]   for p in partners)
    fleet = {
        "total_drivers":    len(partners),
        "active_drivers":   sum(1 for p in partners if p["today_active"] > 0),
        "today_delivered":  sum(p["today_delivered"] for p in partners),
        "fleet_on_time":    round(all_on_time / all_delivered * 100) if all_delivered else 0,
    }
    return {"partners": partners, "fleet": fleet}
