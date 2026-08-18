import frappe
from frappe import _
from frappe.utils import now_datetime, today
import json


def _get_vendor_id():
    """Get Vendor record for current logged-in user."""
    vendor_user = frappe.get_value(
        "Vendor User", {"frappe_user": frappe.session.user}, "vendor"
    )
    if not vendor_user:
        frappe.throw(_("No vendor account linked to this user"), frappe.PermissionError)
    return vendor_user


def _assert_vendor_owns_order(order_name, vendor_id):
    order_vendor = frappe.get_value("Vendor Order", order_name, "vendor")
    if order_vendor != vendor_id:
        frappe.throw(_("Access denied"), frappe.PermissionError)


@frappe.whitelist()
def get_vendor_orders(status=None, limit=20, offset=0):
    vendor_id = _get_vendor_id()
    filters = {"vendor": vendor_id}
    if status:
        filters["order_status"] = status
    orders = frappe.get_all(
        "Vendor Order",
        filters=filters,
        fields=[
            "name",
            "order_date",
            "total_amount",
            "order_status",
            "delivery_slot",
            "vendor_name",
            "rating_submitted",
        ],
        order_by="order_date desc",
        limit_page_length=int(limit),
        start=int(offset),
    )
    total = frappe.db.count("Vendor Order", filters)
    return {"orders": orders, "total": total}


@frappe.whitelist()
def get_order_detail(order_id):
    vendor_id = _get_vendor_id()
    _assert_vendor_owns_order(order_id, vendor_id)
    order = frappe.get_doc("Vendor Order", order_id)
    detail = order.as_dict()

    if order.delivery_assignment:
        from alvoraa_portal.controllers.delivery_tracking import get_latest_tracking

        da = frappe.get_doc("Delivery Assignment", order.delivery_assignment)
        detail["delivery"] = {
            "driver_name": da.driver_name,
            "driver_phone": da.driver_phone,
            "vehicle_reg": da.vehicle_reg,
            "status": da.status,
            "eta_minutes": None,
            "current_location": get_latest_tracking(da.name),
        }

    rating = frappe.get_value(
        "Order Rating",
        {"vendor_order": order_id},
        [
            "name",
            "order_quality_rating",
            "delivery_timeliness_rating",
            "driver_professionalism_rating",
            "comments",
            "issue_category",
        ],
        as_dict=True,
    )
    detail["rating"] = rating
    return detail


@frappe.whitelist()
def create_vendor_order(items, delivery_address, delivery_slot, special_instructions=None):
    vendor_id = _get_vendor_id()
    vendor = frappe.get_doc("Vendor", vendor_id)
    if vendor.account_status != "Active":
        frappe.throw(_("Vendor account is not active"))

    if isinstance(items, str):
        items = json.loads(items)

    order = frappe.new_doc("Vendor Order")
    order.vendor = vendor_id
    order.order_date = today()
    order.delivery_address = delivery_address
    order.delivery_slot = delivery_slot
    order.special_instructions = special_instructions
    order.order_status = "Draft"

    total = 0.0
    for item in items:
        qty = float(item.get("quantity", 1))
        price = float(item.get("unit_price", 0))
        line_total = qty * price
        total += line_total
        order.append(
            "items",
            {
                "sku": item["sku"],
                "quantity": qty,
                "unit_price": price,
                "line_total": line_total,
            },
        )
    order.total_amount = total
    order.insert()
    frappe.db.commit()
    return {"order_id": order.name, "status": "Created", "total_amount": total}


@frappe.whitelist()
def submit_order_rating(
    order_id,
    quality_rating,
    timeliness_rating,
    professionalism_rating,
    comments=None,
    issue_category=None,
):
    vendor_id = _get_vendor_id()
    _assert_vendor_owns_order(order_id, vendor_id)

    order = frappe.get_doc("Vendor Order", order_id)
    if order.order_status != "Delivered":
        frappe.throw(_("Can only rate delivered orders"))
    if order.rating_submitted:
        frappe.throw(_("Rating already submitted for this order"))

    driver = None
    if order.delivery_assignment:
        driver = frappe.get_value("Delivery Assignment", order.delivery_assignment, "driver")

    rating = frappe.new_doc("Order Rating")
    rating.vendor_order = order_id
    rating.vendor = vendor_id
    rating.driver = driver
    rating.rating_date = now_datetime()
    rating.order_quality_rating = int(quality_rating)
    rating.delivery_timeliness_rating = int(timeliness_rating)
    rating.driver_professionalism_rating = int(professionalism_rating)
    rating.average_rating = (
        int(quality_rating) + int(timeliness_rating) + int(professionalism_rating)
    ) / 3.0
    rating.comments = comments
    rating.issue_category = issue_category or "None"
    rating.insert()

    frappe.db.set_value("Vendor Order", order_id, "rating_submitted", 1)
    frappe.db.commit()
    return {"status": "Rating submitted", "rating_id": rating.name}


@frappe.whitelist()
def get_delivery_tracking(order_id):
    vendor_id = _get_vendor_id()
    _assert_vendor_owns_order(order_id, vendor_id)

    assignment_name = frappe.get_value("Vendor Order", order_id, "delivery_assignment")
    if not assignment_name:
        return {"status": "not_assigned"}

    from alvoraa_portal.controllers.delivery_tracking import get_latest_tracking

    da = frappe.get_doc("Delivery Assignment", assignment_name)
    tracking = get_latest_tracking(assignment_name)
    return {
        "assignment": assignment_name,
        "driver_name": da.driver_name,
        "driver_phone": da.driver_phone,
        "vehicle_reg": da.vehicle_reg,
        "status": da.status,
        "latest_tracking": tracking,
    }


@frappe.whitelist()
def get_vendor_dashboard():
    vendor_id = _get_vendor_id()

    pending = frappe.db.count(
        "Vendor Order",
        {
            "vendor": vendor_id,
            "order_status": [
                "in",
                ["Draft", "Under Review", "Approved", "Packing", "Ready for Dispatch"],
            ],
        },
    )
    in_transit = frappe.db.count(
        "Vendor Order",
        {
            "vendor": vendor_id,
            "order_status": ["in", ["Dispatched", "In Transit"]],
        },
    )
    delivered_this_month = frappe.db.count(
        "Vendor Order",
        {
            "vendor": vendor_id,
            "order_status": "Delivered",
            "order_date": [">=", frappe.utils.get_first_day(today())],
        },
    )

    recent_ratings = frappe.get_all(
        "Order Rating",
        filters={"vendor": vendor_id},
        fields=["rating_date", "order_quality_rating", "average_rating", "comments"],
        order_by="rating_date desc",
        limit=5,
    )

    vendor = frappe.get_doc("Vendor", vendor_id)
    return {
        "vendor_name": vendor.vendor_name,
        "company_name": vendor.company_name,
        "account_status": vendor.account_status,
        "account_balance": vendor.account_balance,
        "pending_orders": pending,
        "in_transit_orders": in_transit,
        "delivered_this_month": delivered_this_month,
        "recent_ratings": recent_ratings,
    }


@frappe.whitelist()
def get_vendor_notifications():
    vendor_id = _get_vendor_id()
    user = frappe.get_value("Vendor User", {"vendor": vendor_id}, "frappe_user")
    notifications = (
        frappe.get_all(
            "Notification Log",
            filters={"for_user": user, "read": 0},
            fields=[
                "subject",
                "type",
                "document_type",
                "document_name",
                "creation",
            ],
            order_by="creation desc",
            limit=20,
        )
        if user
        else []
    )
    return notifications
