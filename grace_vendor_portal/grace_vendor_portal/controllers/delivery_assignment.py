import frappe
from frappe import _
from frappe.utils import now_datetime, today, add_days
import random
import string


_SLOT_DAYS = {
    "Today":       0,
    "Tomorrow":    1,
    "Next 2 Days": 2,
    "Next 3 Days": 3,
}


def _generate_otp(length=6):
    return "".join(random.choices(string.digits, k=length))


def after_insert(doc, method=None):
    # Generate OTP
    otp = _generate_otp()
    frappe.db.set_value("Delivery Assignment", doc.name, "delivery_otp", otp)
    frappe.db.commit()

    # Log notification for driver
    driver_name = doc.driver_name or frappe.db.get_value("Employee", doc.driver, "employee_name") or doc.driver
    frappe.log_error(
        f"Delivery assignment {doc.name} created for driver {driver_name}. OTP: {otp}",
        "Delivery Assignment Notification",
    )

    # Notify vendor by email
    vendor = frappe.db.get_value("Vendor Order", doc.vendor_order, "vendor")
    vendor_email = frappe.db.get_value("Vendor", vendor, "email")
    vendor_name = frappe.db.get_value("Vendor", vendor, "vendor_name")
    if vendor_email:
        try:
            frappe.sendmail(
                recipients=[vendor_email],
                subject=f"Your order {doc.vendor_order} has been assigned a driver",
                message=(
                    f"<p>Dear {vendor_name},</p>"
                    f"<p>Your order <strong>{doc.vendor_order}</strong> has been assigned to a driver.</p>"
                    f"<p><strong>Driver:</strong> {driver_name}<br>"
                    f"<strong>Phone:</strong> {doc.driver_phone or 'N/A'}<br>"
                    f"<strong>Vehicle:</strong> {doc.vehicle_reg}</p>"
                    f"<p>You will receive updates as your delivery progresses.</p>"
                    f"<p>Grace Drinks Operations</p>"
                ),
            )
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Driver assignment vendor notification failed")

    # ── Wire: assign driver to the pending DO, or create one if none exists ──
    _assign_or_create_delivery_order(doc)


def _assign_or_create_delivery_order(da_doc):
    """Wire a Delivery Assignment to its Delivery Order.

    Preferred path: a Pending DO was already created when the Vendor Order
    reached 'Ready for Dispatch'.  Find it, assign the partner, flip to Assigned.

    Fallback path: DA was created directly (bypassing the VO status flow).
    Create a fresh DO as before.
    """
    partner_name = frappe.db.get_value(
        "Delivery Partner", {"linked_employee": da_doc.driver}, "name"
    )
    if not partner_name:
        frappe.log_error(
            f"No Delivery Partner linked to Employee {da_doc.driver}. "
            f"Cannot wire DO for DA {da_doc.name}. "
            f"Set 'Linked Employee' on the Delivery Partner record.",
            "DA→DO Wiring: Missing Partner",
        )
        return

    # Look for a Pending DO pre-created at Ready-for-Dispatch (keyed by [VO:…] prefix)
    row = frappe.db.sql(
        "SELECT name FROM `tabDelivery Order`"
        " WHERE special_instructions LIKE %s AND current_status = 'Pending' LIMIT 1",
        (f"[VO: {da_doc.vendor_order}]%",), as_dict=True,
    )
    pending_do = row[0]["name"] if row else None

    if pending_do:
        # Assign the partner and activate the existing DO
        frappe.db.set_value("Delivery Order", pending_do, "assigned_to_partner", partner_name)
        frappe.db.set_value("Delivery Order", pending_do, "current_status", "Assigned")
        frappe.db.set_value("Delivery Order", pending_do, "assignment_status", "Assigned")
        frappe.db.set_value("Delivery Order", pending_do, "assigned_date", now_datetime())
        frappe.db.set_value("Delivery Assignment", da_doc.name, "delivery_order", pending_do)
        frappe.db.commit()
        frappe.log_error(
            f"Pending DO {pending_do} assigned to partner {partner_name} "
            f"via DA {da_doc.name} (VO: {da_doc.vendor_order})",
            "DA→DO Wiring: Existing DO Activated",
        )
    else:
        # Fallback: create a new DO from scratch
        _create_delivery_order(da_doc, partner_name)


def _create_delivery_order(da_doc, partner_name=None):
    """Create a fresh Delivery Order from a Delivery Assignment (fallback path)."""
    if not partner_name:
        partner_name = frappe.db.get_value(
            "Delivery Partner", {"linked_employee": da_doc.driver}, "name"
        )
    if not partner_name:
        frappe.log_error(
            f"No Delivery Partner linked to Employee {da_doc.driver}. "
            f"Delivery Order NOT created for DA {da_doc.name}.",
            "DA→DO Wiring: Missing Partner",
        )
        return

    vo = frappe.get_doc("Vendor Order", da_doc.vendor_order)
    vendor_email = frappe.db.get_value("Vendor", vo.vendor, "email") or ""
    vendor_phone = frappe.db.get_value("Vendor", vo.vendor, "phone") or ""
    delivery_date = add_days(today(), _SLOT_DAYS.get(vo.delivery_slot, 0))

    items = []
    for i in vo.items:
        item_meta = frappe.db.get_value("Item", i.sku, ["item_name", "stock_uom"], as_dict=True) or {}
        items.append({
            "item_code":  i.sku,
            "item_name":  item_meta.get("item_name") or getattr(i, "item_name", None) or i.sku,
            "quantity":   i.quantity,
            "uom":        item_meta.get("stock_uom") or "",
            "unit_price": i.unit_price,
            "total":      i.line_total or (i.quantity * i.unit_price),
        })

    do = frappe.get_doc({
        "doctype":            "Delivery Order",
        "source_order_type":  "Direct",
        "customer":           vo.vendor,
        "customer_name":      vo.vendor_name or frappe.db.get_value("Vendor", vo.vendor, "vendor_name"),
        "customer_phone":     vendor_phone,
        "customer_email":     vendor_email,
        "delivery_address":   vo.delivery_address,
        "delivery_date":      delivery_date,
        "special_instructions": f"[VO: {da_doc.vendor_order}]" + (f" {vo.special_instructions}" if vo.special_instructions else ""),
        "assigned_to_partner": partner_name,
        "assigned_date":      now_datetime(),
        "assignment_status":  "Assigned",
        "current_status":     "Assigned",
        "grand_total":        vo.total_amount or 0,
        "order_items":        items,
    })
    do.insert(ignore_permissions=True)
    frappe.db.commit()

    frappe.db.set_value("Delivery Assignment", da_doc.name, "delivery_order", do.name)
    frappe.db.commit()

    frappe.log_error(
        f"DO {do.name} created directly from DA {da_doc.name} "
        f"(VO: {da_doc.vendor_order}, Partner: {partner_name})",
        "DA→DO Wiring: New DO Created",
    )


def on_update(doc, method=None):
    doc_before = doc.get_doc_before_save()

    if doc_before and doc_before.status != doc.status and doc.status == "Delivered":
        frappe.db.set_value("Vendor Order", doc.vendor_order, "order_status", "Delivered")
        frappe.db.commit()

    if doc_before and not doc_before.otp_verified and doc.otp_verified:
        frappe.db.set_value("Delivery Assignment", doc.name, "status", "Delivered")
        frappe.db.set_value("Vendor Order", doc.vendor_order, "order_status", "Delivered")
        frappe.db.commit()


@frappe.whitelist()
def update_gps_location(assignment_name, lat, lng, eta_minutes=None):
    assignment = frappe.get_doc("Delivery Assignment", assignment_name)
    assignment.append(
        "tracking_history",
        {
            "current_lat":        float(lat),
            "current_long":       float(lng),
            "updated_timestamp":  now_datetime(),
            "eta_minutes":        int(eta_minutes) if eta_minutes is not None else None,
            "delivery_status":    "In Transit",
        },
    )
    assignment.save(ignore_permissions=True)
    frappe.db.commit()

    from grace_vendor_portal.websocket.delivery_tracking_updates import broadcast_gps_update
    broadcast_gps_update(assignment_name, float(lat), float(lng), int(eta_minutes) if eta_minutes else None)

    if eta_minutes is not None and int(eta_minutes) <= 10:
        vendor = frappe.db.get_value("Vendor Order", assignment.vendor_order, "vendor")
        vendor_email = frappe.db.get_value("Vendor", vendor, "email")
        if vendor_email:
            try:
                frappe.sendmail(
                    recipients=[vendor_email],
                    subject="Your delivery is arriving soon!",
                    message=(
                        f"<p>Your Grace Drinks order will arrive in approximately "
                        f"{eta_minutes} minutes. Please be available to receive it.</p>"
                    ),
                )
            except Exception:
                frappe.log_error(frappe.get_traceback(), "Arriving soon notification failed")

    return {"status": "updated", "lat": lat, "lng": lng, "eta_minutes": eta_minutes}


@frappe.whitelist()
def verify_delivery_otp(assignment_name, entered_otp):
    stored_otp = frappe.db.get_value("Delivery Assignment", assignment_name, "delivery_otp")
    vendor_order = frappe.db.get_value("Delivery Assignment", assignment_name, "vendor_order")

    if str(entered_otp).strip() != str(stored_otp).strip():
        frappe.throw(_("Invalid OTP. Please try again."))

    frappe.db.set_value(
        "Delivery Assignment",
        assignment_name,
        {"otp_verified": 1, "status": "Delivered"},
    )
    frappe.db.set_value("Vendor Order", vendor_order, "order_status", "Delivered")
    frappe.db.commit()

    return {"status": "verified", "assignment": assignment_name, "order": vendor_order}
