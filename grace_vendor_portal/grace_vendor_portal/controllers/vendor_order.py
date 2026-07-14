import frappe
from frappe import _
from frappe.utils import now_datetime, today, add_days

VALID_TRANSITIONS = {
    "Draft": ["Under Review", "Cancelled"],
    "Under Review": ["Approved", "Cancelled"],
    "Approved": ["Packing", "Cancelled"],
    "Packing": ["Ready for Dispatch", "Cancelled"],
    "Ready for Dispatch": ["Dispatched"],
    "Dispatched": ["In Transit"],
    "In Transit": ["Delivered"],
    "Delivered": [],
    "Cancelled": [],
}


def validate(doc, method=None):
    # Validate vendor is active
    vendor = frappe.get_doc("Vendor", doc.vendor)
    if vendor.account_status != "Active":
        frappe.throw(_("Vendor account is not active. Cannot create or modify order."))

    # Recalculate line totals + total_amount
    total = 0.0
    for item in doc.items:
        item.line_total = (item.quantity or 0) * (item.unit_price or 0)
        total += item.line_total
    doc.total_amount = total


def on_update(doc, method=None):
    doc_before = doc.get_doc_before_save()
    old_status = doc_before.order_status if doc_before else None

    if doc.order_status == "Ready for Dispatch" and old_status != "Ready for Dispatch":
        _prepare_delivery_pipeline(doc.name, doc)

    if old_status and old_status != doc.order_status:
        frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Info",
            "reference_doctype": doc.doctype,
            "reference_name": doc.name,
            "content": f"Status changed from {old_status} to {doc.order_status}",
        }).insert(ignore_permissions=True)

        _notify_vendor(
            doc.vendor,
            f"Order {doc.name} Status Update: {doc.order_status}",
            (
                f"<p>Dear {doc.vendor_name},</p>"
                f"<p>Your order <strong>{doc.name}</strong> status has been updated to: "
                f"<strong>{doc.order_status}</strong>.</p>"
                f"<p>Grace Drinks Operations</p>"
            ),
        )

        vendor_user = get_vendor_user_for_vendor(doc.vendor)
        if vendor_user:
            frappe.publish_realtime(
                "vendor_order_update",
                {"order": doc.name, "status": doc.order_status},
                user=vendor_user,
            )

    if doc.order_status == "Delivered" and not doc.rating_submitted:
        vendor_user = get_vendor_user_for_vendor(doc.vendor)
        if vendor_user:
            frappe.publish_realtime(
                "vendor_order_update",
                {
                    "order": doc.name,
                    "status": doc.order_status,
                    "prompt_rating": True,
                },
                user=vendor_user,
            )


@frappe.whitelist()
def change_order_status(order_name, new_status, reason=None):
    # Validate permission
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    allowed_roles = {"HR Manager", "System Manager"}
    user_roles = set(frappe.get_roles(frappe.session.user))
    if not allowed_roles.intersection(user_roles):
        frappe.throw(_("Only HR Manager or System Manager can change order status"), frappe.PermissionError)

    order = frappe.get_doc("Vendor Order", order_name)
    current_status = order.order_status

    if new_status not in VALID_TRANSITIONS.get(current_status, []):
        frappe.throw(
            _("Cannot transition from {0} to {1}").format(current_status, new_status)
        )

    frappe.db.set_value("Vendor Order", order_name, "order_status", new_status)
    frappe.db.commit()

    # Ops email when a new order enters review
    if current_status == "Draft" and new_status == "Under Review":
        try:
            frappe.sendmail(
                recipients=["ops@gracedrinks.in"],
                subject=f"[Grace Vendor Portal] New Order {order_name} Under Review",
                message=(
                    f"<p>A vendor order requires review.</p>"
                    f"<p><strong>Order:</strong> {order_name}<br>"
                    f"<strong>Vendor:</strong> {order.vendor_name} ({order.vendor})<br>"
                    f"<strong>Date:</strong> {order.order_date}<br>"
                    f"<strong>Slot:</strong> {order.delivery_slot}<br>"
                    f"<strong>Total:</strong> ₹{order.total_amount:,.2f}</p>"
                ),
            )
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Vendor Order ops notification failed")

    # Trigger delivery pipeline (bypasses on_update since we use set_value)
    if new_status == "Ready for Dispatch":
        _prepare_delivery_pipeline(order_name, order)

    # Log in comments
    comment_text = f"Status changed from {current_status} to {new_status}"
    if reason:
        comment_text += f". Reason: {reason}"
    frappe.get_doc({
        "doctype": "Comment",
        "comment_type": "Info",
        "reference_doctype": "Vendor Order",
        "reference_name": order_name,
        "content": comment_text,
    }).insert(ignore_permissions=True)

    # Notify vendor
    _notify_vendor(
        order.vendor,
        f"Order {order_name} Status Update: {new_status}",
        (
            f"<p>Your order <strong>{order_name}</strong> status is now: "
            f"<strong>{new_status}</strong>.</p>"
            + (f"<p>Reason: {reason}</p>" if reason else "")
            + "<p>Grace Drinks Operations</p>"
        ),
    )

    return frappe.get_doc("Vendor Order", order_name).as_dict()


@frappe.whitelist()
def assign_delivery(order_name, driver_id, vehicle_reg, eta_time=None):
    order = frappe.get_doc("Vendor Order", order_name)

    assignment = frappe.new_doc("Delivery Assignment")
    assignment.vendor_order = order_name
    assignment.driver = driver_id
    assignment.vehicle_reg = vehicle_reg
    assignment.assigned_datetime = frappe.utils.now_datetime()
    if eta_time:
        assignment.estimated_delivery = eta_time
    assignment.status = "Assigned"
    assignment.insert(ignore_permissions=True)

    # Link to Vendor Order
    frappe.db.set_value("Vendor Order", order_name, "delivery_assignment", assignment.name)
    frappe.db.set_value("Vendor Order", order_name, "order_status", "Dispatched")
    frappe.db.commit()

    # Notify vendor
    driver_name = frappe.get_value("Employee", driver_id, "employee_name") or driver_id
    _notify_vendor(
        order.vendor,
        f"Order {order_name} Dispatched",
        (
            f"<p>Your order <strong>{order_name}</strong> has been dispatched.</p>"
            f"<p><strong>Driver:</strong> {driver_name}<br>"
            f"<strong>Vehicle:</strong> {vehicle_reg}</p>"
            f"<p>Grace Drinks Operations</p>"
        ),
    )

    return assignment.name


def _notify_vendor(vendor_id, subject, message):
    try:
        email = frappe.get_value("Vendor", vendor_id, "email")
        if email:
            frappe.sendmail(recipients=[email], subject=subject, message=message)
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"Vendor notification failed for {vendor_id}")


def get_vendor_user_for_vendor(vendor_id):
    return frappe.get_value("Vendor User", {"vendor": vendor_id}, "frappe_user")


_SLOT_DAYS = {"Today": 0, "Tomorrow": 1, "Next 2 Days": 2, "Next 3 Days": 3}


def _get_warehouse_manager_emails():
    """Return emails of all active users holding the Logistics Manager role."""
    rows = frappe.get_all(
        "Has Role",
        filters={"role": "Logistics Manager", "parenttype": "User"},
        fields=["parent"],
    )
    emails = [r["parent"] for r in rows if r["parent"] not in ("Administrator", "Guest")]
    if not emails:
        # Fallback: first employee with Logistics Manager designation
        emp_email = frappe.db.get_value(
            "Employee", {"designation": "Logistics Manager"}, "company_email"
        )
        if emp_email:
            emails = [emp_email]
    return emails or ["ops@gracedrinks.in"]


def _prepare_delivery_pipeline(order_name, vo=None):
    """Called when a Vendor Order reaches 'Ready for Dispatch'.

    Creates a Pending Delivery Order (no driver yet) and emails warehouse
    managers to create the Delivery Assignment and assign a driver.
    Idempotent — skips if a Delivery Order already exists for this VO.
    """
    if vo is None:
        vo = frappe.get_doc("Vendor Order", order_name)

    # Idempotency: one DO per Vendor Order — keyed by the [VO: …] prefix in special_instructions
    existing = frappe.db.sql(
        "SELECT name FROM `tabDelivery Order` WHERE special_instructions LIKE %s LIMIT 1",
        (f"[VO: {order_name}]%",), as_dict=True,
    )
    if existing:
        return existing[0]["name"]

    # Pull vendor contact details to populate customer section
    vendor = frappe.get_doc("Vendor", vo.vendor)

    delivery_date = add_days(today(), _SLOT_DAYS.get(vo.delivery_slot, 1))

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
        "customer":           vendor.name,
        "customer_name":      vendor.vendor_name,
        "customer_phone":     vendor.phone or "",
        "customer_email":     vendor.email or "",
        "delivery_address":   vo.delivery_address,
        "delivery_date":      delivery_date,
        "special_instructions": f"[VO: {order_name}]" + (f" {vo.special_instructions}" if vo.special_instructions else ""),
        "current_status":     "Pending",
        "assignment_status":  "Not-Assigned",
        "grand_total":        vo.total_amount or 0,
        "order_items":        items,
    })
    do.insert(ignore_permissions=True)
    frappe.db.commit()

    # Notify warehouse managers
    manager_emails = _get_warehouse_manager_emails()
    base_url = frappe.utils.get_url()
    da_new_url = f"{base_url}/app/delivery-assignment/new-delivery-assignment-1"

    try:
        frappe.sendmail(
            recipients=manager_emails,
            subject=f"[Action Required] Assign Driver — Vendor Order {order_name}",
            message=(
                f"<p>Dear Warehouse Manager,</p>"
                f"<p>Vendor order <strong>{order_name}</strong> from "
                f"<strong>{vo.vendor_name}</strong> is now "
                f"<strong>Ready for Dispatch</strong> and requires a driver.</p>"
                f"<table border='1' cellpadding='8' cellspacing='0' "
                f"style='border-collapse:collapse;font-family:sans-serif;'>"
                f"<tr><th align='left'>Order</th><td>{order_name}</td></tr>"
                f"<tr><th align='left'>Vendor</th><td>{vo.vendor_name}</td></tr>"
                f"<tr><th align='left'>Delivery Slot</th><td>{vo.delivery_slot}</td></tr>"
                f"<tr><th align='left'>Delivery Date</th><td>{delivery_date}</td></tr>"
                f"<tr><th align='left'>Items</th><td>{len(items)} line(s)</td></tr>"
                f"<tr><th align='left'>Order Value</th><td>&#8377;{vo.total_amount or 0:,.2f}</td></tr>"
                f"<tr><th align='left'>Delivery Order</th><td>{do.name} (Pending)</td></tr>"
                f"</table>"
                f"<br>"
                f"<p><a href='{da_new_url}' "
                f"style='background:#1a7f5a;color:#fff;padding:10px 22px;"
                f"text-decoration:none;border-radius:4px;font-family:sans-serif;'>"
                f"Create Delivery Assignment &rarr;</a></p>"
                f"<p style='color:#666;font-size:12px;'>"
                f"Set Vendor Order to <em>{order_name}</em>, select a driver and vehicle, "
                f"then save — the driver portal will update automatically.</p>"
                f"<p>Grace Operations System</p>"
            ),
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"Warehouse manager notification failed for {order_name}")

    frappe.log_error(
        f"DO {do.name} (Pending) created for VO {order_name}. "
        f"Notified managers: {manager_emails}",
        "Ready for Dispatch: Pipeline Ready",
    )
    return do.name
