import frappe


def handle_vendor_order_update(data):
    """
    Frappe realtime event handler.
    Called when vendor_order_update event is published.
    """
    order_name = data.get("order")
    status = data.get("status")
    vendor_user = data.get("vendor_user")

    if vendor_user:
        frappe.publish_realtime(
            event="vendor_order_update",
            message={"order": order_name, "status": status},
            user=vendor_user,
        )
