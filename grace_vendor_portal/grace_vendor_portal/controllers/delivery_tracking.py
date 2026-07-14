import frappe


def get_latest_tracking(assignment_name):
    tracking = frappe.get_all(
        "Delivery Tracking",
        filters={"parent": assignment_name},
        fields=["current_lat", "current_long", "updated_timestamp", "eta_minutes", "delivery_status"],
        order_by="updated_timestamp desc",
        limit=1,
    )
    return tracking[0] if tracking else None


def calculate_eta(current_lat, current_lng, dest_lat, dest_lng, avg_speed_kmh=30):
    """Simple Haversine distance + speed estimate, returns ETA in minutes."""
    import math

    R = 6371
    lat1, lon1 = math.radians(current_lat), math.radians(current_lng)
    lat2, lon2 = math.radians(dest_lat), math.radians(dest_lng)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    distance_km = R * 2 * math.asin(math.sqrt(a))
    eta_hours = distance_km / avg_speed_kmh
    return int(eta_hours * 60)  # minutes
