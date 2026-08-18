import frappe


def broadcast_gps_update(assignment_name, lat, lng, eta_minutes):
    """Broadcast GPS update to the vendor watching this delivery."""
    vendor_order = frappe.get_value("Delivery Assignment", assignment_name, "vendor_order")
    vendor = frappe.get_value("Vendor Order", vendor_order, "vendor")
    vendor_user = frappe.get_value("Vendor User", {"vendor": vendor}, "frappe_user")

    if vendor_user:
        frappe.publish_realtime(
            event="gps_update",
            message={
                "assignment": assignment_name,
                "lat": lat,
                "lng": lng,
                "eta_minutes": eta_minutes,
            },
            user=vendor_user,
        )
