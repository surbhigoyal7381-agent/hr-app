import frappe
from frappe.utils import now_datetime, getdate


# Slot end-time map for on-time calculation
_SLOT_END_HOURS = {
    "8AM-12PM": 12,
    "12PM-3PM": 15,
    "3PM-6PM": 18,
    "6PM-9PM": 21,
}


def before_save(doc, method=None):
    _recalculate_totals(doc)
    _geocode_address(doc)
    if doc.delivery_actual_time and doc.delivery_date and doc.delivery_time_slot:
        _set_on_time_status(doc)


def _geocode_address(doc):
    """Geocode delivery_address via Nominatim and store lat,lng in delivery_coordinates.
    Also back-fills delivery_city, delivery_state, delivery_pin when empty.
    Only runs when the address has changed or coordinates are missing.

    Strategy:
      1. Full free-text query (fast, works for well-known places)
      2. Structured query using pin code + city extracted from the address string
         (better for specific Indian street addresses that Nominatim can't resolve verbatim)
    """
    if not doc.delivery_address:
        return

    prev = doc.get_doc_before_save()
    prev_address = prev.get("delivery_address") if prev else None
    if doc.delivery_coordinates and prev_address == doc.delivery_address:
        return  # address unchanged and coordinates already set

    try:
        from urllib.request import urlopen, Request
        from urllib.parse import urlencode
        import json as _json
        import re as _re

        headers = {"User-Agent": "GraceVendorPortal/1.0 (ops@gracedrinks.in)"}

        def _nominatim(params):
            url = "https://nominatim.openstreetmap.org/search?" + urlencode(params)
            with urlopen(Request(url, headers=headers), timeout=6) as r:
                return _json.loads(r.read())

        # ── Pass 1: full free-text query ─────────────────────────────────────
        results = _nominatim({
            "q": doc.delivery_address,
            "format": "json",
            "limit": "1",
            "addressdetails": "1",
            "countrycodes": "in",
        })

        # ── Pass 2: structured query using pin + city extracted from address ─
        if not results:
            pin_match = _re.search(r"\b(\d{6})\b", doc.delivery_address)
            # City is typically the word(s) just before "- PINCODE" at the end
            city_match = _re.search(
                r",\s*([^,\-]+?)\s*[-–]\s*\d{6}", doc.delivery_address
            )
            if pin_match and city_match:
                results = _nominatim({
                    "city":       city_match.group(1).strip(),
                    "postalcode": pin_match.group(1),
                    "country":    "India",
                    "format":     "json",
                    "limit":      "1",
                    "addressdetails": "1",
                })

        if not results:
            return

        hit = results[0]
        doc.delivery_coordinates = f"{float(hit['lat'])},{float(hit['lon'])}"

        addr = hit.get("address", {})
        city  = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("county") or ""
        state = addr.get("state", "")
        pin   = addr.get("postcode", "")

        if city  and not doc.delivery_city:  doc.delivery_city  = city
        if state and not doc.delivery_state: doc.delivery_state = state
        if pin   and not doc.delivery_pin:   doc.delivery_pin   = pin

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Geocoding failed for Delivery Order")


def on_update(doc, method=None):
    prev = doc.get_doc_before_save()
    if prev and prev.get("current_status") != doc.current_status:
        _append_status_history(doc, prev.get("current_status", ""))
        _sync_to_vendor_pipeline(doc)
        if doc.current_status == "Delivered":
            _handle_delivered(doc)


def _recalculate_totals(doc):
    subtotal = 0.0
    for item in doc.get("order_items", []):
        item.total = (item.quantity or 0) * (item.unit_price or 0)
        subtotal += item.total
    doc.subtotal = subtotal
    doc.grand_total = (
        subtotal
        + (doc.delivery_charges or 0)
        + (doc.tax or 0)
        - (doc.discount or 0)
    )


def _set_on_time_status(doc):
    from datetime import datetime, time as dtime
    slot_end_hour = _SLOT_END_HOURS.get(doc.delivery_time_slot)
    if slot_end_hour is None:
        return
    actual = frappe.utils.get_datetime(doc.delivery_actual_time)
    slot_end = datetime.combine(
        getdate(doc.delivery_date),
        dtime(slot_end_hour, 0, 0),
    )
    if actual <= slot_end:
        doc.on_time_status = "On-Time"
    else:
        doc.on_time_status = "Late"


def _append_status_history(doc, old_status):
    doc.append(
        "status_history",
        {
            "status": doc.current_status,
            "timestamp": now_datetime(),
            "updated_by": frappe.session.user,
            "notes": f"Status changed from {old_status or 'New'} to {doc.current_status}",
        },
    )
    doc.status_updated_at = now_datetime()
    doc.status_updated_by = frappe.session.user


_DA_STATUS = {
    "Assigned":    "Assigned",
    "Picked Up":   "In Transit",
    "In Transit":  "In Transit",
    "Nearby":      "In Transit",
    "At Location": "Arrived",
    "Delivered":   "Delivered",
    "Failed":      "Failed",
    "Cancelled":   "Failed",
    "Returned":    "Failed",
}

_VO_STATUS = {
    "Assigned":    "Dispatched",
    "Picked Up":   "In Transit",
    "In Transit":  "In Transit",
    "Nearby":      "In Transit",
    "At Location": "In Transit",
    "Delivered":   "Delivered",
    "Failed":      "Cancelled",
    "Cancelled":   "Cancelled",
    "Returned":    "Cancelled",
}


def _sync_to_vendor_pipeline(do_doc):
    """Mirror Delivery Order status back to the linked Delivery Assignment and Vendor Order."""
    # The vendor_order name was stored in the customer field during auto-creation
    vendor_order_name = do_doc.customer if do_doc.customer and do_doc.customer.startswith("GD-VO-") else None

    # Find the Delivery Assignment that created this DO
    da_name = frappe.db.get_value("Delivery Assignment", {"delivery_order": do_doc.name}, "name")

    new_da_status = _DA_STATUS.get(do_doc.current_status)
    new_vo_status = _VO_STATUS.get(do_doc.current_status)

    if da_name and new_da_status:
        frappe.db.set_value("Delivery Assignment", da_name, "status", new_da_status)
        if not vendor_order_name:
            vendor_order_name = frappe.db.get_value("Delivery Assignment", da_name, "vendor_order")

    if vendor_order_name and new_vo_status:
        frappe.db.set_value("Vendor Order", vendor_order_name, "order_status", new_vo_status)
        # Publish realtime so vendor portal card updates live
        frappe.publish_realtime(
            "vendor_order_update",
            {"order": vendor_order_name, "status": new_vo_status},
        )

    if da_name or vendor_order_name:
        frappe.db.commit()


def _handle_delivered(doc):
    """Post-delivery tasks: sync assignment status, trigger partner stat update."""
    if doc.assigned_to_partner:
        # Sync assignment_status
        doc.assignment_status = "Delivered"
        # Async update of partner-level stats to avoid blocking the save
        frappe.enqueue(
            "grace_vendor_portal.controllers.delivery_partner.update_partner_stats_from_orders",
            queue="short",
            partner_name=doc.assigned_to_partner,
        )


# ─── Whitelisted API endpoints ────────────────────────────────────────────────

@frappe.whitelist()
def update_delivery_status(order_name, new_status, gps_location=None, notes=None):
    """Update the status of a Delivery Order. Called from the driver portal / app."""
    doc = frappe.get_doc("Delivery Order", order_name)
    old_status = doc.current_status

    valid_transitions = {
        "Pending": ["Assigned", "Cancelled"],
        "Assigned": ["Picked Up", "Cancelled"],
        "Picked Up": ["In Transit", "Failed"],
        "In Transit": ["Nearby", "Delivered", "Failed"],
        "Nearby": ["At Location", "Delivered", "Failed"],
        "At Location": ["Delivered", "Failed"],
        "Failed": ["Returned", "Assigned"],
        "Delivered": [],
        "Returned": [],
        "Cancelled": [],
    }
    allowed = valid_transitions.get(old_status, [])
    if new_status not in allowed:
        frappe.throw(
            f"Cannot move Delivery Order from '{old_status}' to '{new_status}'. "
            f"Allowed transitions: {', '.join(allowed) or 'none'}."
        )

    doc.current_status = new_status
    doc.status_updated_at = now_datetime()
    doc.status_updated_by = frappe.session.user

    if new_status == "Delivered":
        doc.delivery_actual_time = now_datetime()
        doc.delivery_timestamp = now_datetime()
        doc.assignment_status = "Delivered"

    doc.append(
        "status_history",
        {
            "status": new_status,
            "timestamp": now_datetime(),
            "updated_by": frappe.session.user,
            "gps_location": gps_location or "",
            "notes": notes or f"Status updated from {old_status} to {new_status}",
        },
    )
    doc.flags.ignore_validate = True
    doc.save()
    frappe.db.commit()

    # Broadcast to any live watchers (logistics manager dashboard)
    frappe.publish_realtime(
        "delivery_order_update",
        {
            "order": order_name,
            "old_status": old_status,
            "new_status": new_status,
            "timestamp": str(now_datetime()),
            "partner": doc.assigned_to_partner,
        },
        room=f"delivery_order_{order_name}",
    )
    return {"success": True, "order": order_name, "new_status": new_status}


@frappe.whitelist()
def assign_partner_to_order(order_name, partner_name):
    """Assign a Delivery Partner to a Delivery Order."""
    doc = frappe.get_doc("Delivery Order", order_name)
    if doc.current_status not in ("Pending",):
        frappe.throw(f"Order must be in 'Pending' status to assign a partner. Current: {doc.current_status}")

    doc.assigned_to_partner = partner_name
    doc.assigned_date = now_datetime()
    doc.assignment_status = "Assigned"
    doc.current_status = "Assigned"
    doc.append(
        "status_history",
        {
            "status": "Assigned",
            "timestamp": now_datetime(),
            "updated_by": frappe.session.user,
            "notes": f"Assigned to partner {partner_name} by {frappe.session.user}",
        },
    )
    doc.flags.ignore_validate = True
    doc.save()
    frappe.db.commit()

    # Notify partner
    _notify_partner_assignment(doc, partner_name)
    return {"success": True, "partner": partner_name}


def _notify_partner_assignment(order_doc, partner_name):
    try:
        partner = frappe.get_doc("Delivery Partner", partner_name)
        if partner.primary_email:
            frappe.sendmail(
                recipients=[partner.primary_email],
                subject=f"New Delivery Assignment: {order_doc.name}",
                message=f"""
                <p>Dear {partner.partner_name},</p>
                <p>You have been assigned a new delivery order.</p>
                <ul>
                    <li>Order: <b>{order_doc.name}</b></li>
                    <li>Customer: {order_doc.customer_name}</li>
                    <li>Delivery Date: {order_doc.delivery_date}</li>
                    <li>Time Slot: {order_doc.delivery_time_slot}</li>
                    <li>Address: {order_doc.delivery_address}</li>
                </ul>
                <p>Please log in to the portal to confirm and start your delivery.</p>
                """,
            )
    except Exception as e:
        frappe.log_error(str(e), "Delivery Partner Assignment Notification Error")


@frappe.whitelist()
def mark_proof_of_delivery(order_name, delivery_photo=None, delivery_signature=None):
    """Record proof-of-delivery assets on the order."""
    doc = frappe.get_doc("Delivery Order", order_name)
    if delivery_photo:
        doc.delivery_photo = delivery_photo
    if delivery_signature:
        doc.delivery_signature = delivery_signature
    doc.delivery_timestamp = now_datetime()
    doc.flags.ignore_validate = True
    doc.save()
    frappe.db.commit()
    return {"success": True}


@frappe.whitelist()
def get_partner_today_orders(partner_name):
    """Return today's pending/in-transit orders for a partner (driver dashboard)."""
    from frappe.utils import today as frappe_today
    return frappe.get_all(
        "Delivery Order",
        filters={
            "assigned_to_partner": partner_name,
            "delivery_date": frappe_today(),
        },
        fields=[
            "name", "customer_name", "customer_phone",
            "delivery_address", "delivery_city", "delivery_coordinates",
            "delivery_time_slot", "current_status", "grand_total",
            "is_fragile", "requires_signature", "requires_photo",
            "special_instructions", "on_time_status",
        ],
        order_by="delivery_time_slot asc",
    )


@frappe.whitelist()
def get_hub_live_summary(hub_name):
    """Return real-time delivery summary for a hub (manager dashboard)."""
    partners = frappe.get_all(
        "Delivery Partner",
        filters={"hub_assigned": hub_name, "is_active": 1},
        pluck="name",
    )
    if not partners:
        return {"hub": hub_name, "partners": 0, "orders": {}}

    from frappe.utils import today as frappe_today
    orders = frappe.get_all(
        "Delivery Order",
        filters={
            "assigned_to_partner": ["in", partners],
            "delivery_date": frappe_today(),
        },
        fields=["current_status"],
    )

    summary = {}
    for order in orders:
        summary[order.current_status] = summary.get(order.current_status, 0) + 1

    return {
        "hub": hub_name,
        "active_partners": len(partners),
        "total_orders_today": len(orders),
        "by_status": summary,
    }
