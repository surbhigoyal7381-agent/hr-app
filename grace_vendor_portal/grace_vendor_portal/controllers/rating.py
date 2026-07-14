import frappe
from frappe import _
from frappe.utils import now_datetime


def validate(doc, method=None):
    # Ensure ratings are 1-5
    for field, label in [
        ("order_quality_rating", "Order Quality Rating"),
        ("delivery_timeliness_rating", "Delivery Timeliness Rating"),
        ("driver_professionalism_rating", "Driver Professionalism Rating"),
    ]:
        value = getattr(doc, field, None)
        if value is None or not (1 <= int(value) <= 5):
            frappe.throw(_("{0} must be between 1 and 5").format(label))

    # Calculate average rating
    doc.average_rating = (
        int(doc.order_quality_rating)
        + int(doc.delivery_timeliness_rating)
        + int(doc.driver_professionalism_rating)
    ) / 3.0

    # Ensure vendor_order exists and status == Delivered
    order_status = frappe.get_value("Vendor Order", doc.vendor_order, "order_status")
    if order_status != "Delivered":
        frappe.throw(_("Ratings can only be submitted for Delivered orders. Current status: {0}").format(order_status))


def before_insert(doc, method=None):
    # Check no existing rating for this order
    existing = frappe.get_value("Order Rating", {"vendor_order": doc.vendor_order}, "name")
    if existing:
        frappe.throw(_("A rating has already been submitted for order {0}").format(doc.vendor_order))

    # Set driver from Delivery Assignment linked to the order
    if not doc.driver:
        assignment_name = frappe.get_value("Vendor Order", doc.vendor_order, "delivery_assignment")
        if assignment_name:
            doc.driver = frappe.get_value("Delivery Assignment", assignment_name, "driver")


def after_insert(doc, method=None):
    # If average_rating <= 2: set escalated=1, alert ops
    if doc.average_rating <= 2:
        frappe.db.set_value("Order Rating", doc.name, "escalated", 1)
        try:
            frappe.sendmail(
                recipients=["ops@gracedrinks.in"],
                subject=f"[ALERT] Low Rating for Order {doc.vendor_order}",
                message=(
                    f"<p>A low rating has been submitted for order <strong>{doc.vendor_order}</strong>.</p>"
                    f"<p><strong>Average Rating:</strong> {doc.average_rating:.1f}/5<br>"
                    f"<strong>Vendor:</strong> {doc.vendor}<br>"
                    f"<strong>Issue:</strong> {doc.issue_category or 'None'}<br>"
                    f"<strong>Comments:</strong> {doc.comments or '—'}</p>"
                    f"<p>Please follow up with the vendor.</p>"
                ),
            )
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Low rating alert email failed")

    # Update Driver Rating Summary
    if doc.driver:
        _recalculate_driver_rating(doc.driver)

    # Send thank-you email to vendor
    try:
        vendor_email = frappe.get_value("Vendor", doc.vendor, "email")
        vendor_name = frappe.get_value("Vendor", doc.vendor, "vendor_name")
        if vendor_email:
            frappe.sendmail(
                recipients=[vendor_email],
                subject=f"Thank you for your feedback on order {doc.vendor_order}",
                message=(
                    f"<p>Dear {vendor_name},</p>"
                    f"<p>Thank you for rating your experience with order <strong>{doc.vendor_order}</strong>.</p>"
                    f"<p>Your feedback helps us improve our service.</p>"
                    f"<p>Grace Drinks Operations</p>"
                ),
            )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Thank-you email failed")


def _recalculate_driver_rating(driver_id):
    ratings = frappe.get_all(
        "Order Rating",
        filters={"driver": driver_id},
        fields=[
            "order_quality_rating",
            "delivery_timeliness_rating",
            "driver_professionalism_rating",
        ],
    )

    if not ratings:
        return

    count = len(ratings)
    avg_quality = sum(r.order_quality_rating for r in ratings) / count
    avg_timeliness = sum(r.delivery_timeliness_rating for r in ratings) / count
    avg_professionalism = sum(r.driver_professionalism_rating for r in ratings) / count

    existing = frappe.get_value("Driver Rating Summary", {"driver": driver_id}, "name")
    if existing:
        frappe.db.set_value(
            "Driver Rating Summary",
            existing,
            {
                "avg_quality_rating": round(avg_quality, 2),
                "avg_timeliness_rating": round(avg_timeliness, 2),
                "avg_professionalism_rating": round(avg_professionalism, 2),
                "total_ratings": count,
                "last_updated": now_datetime(),
            },
        )
    else:
        summary = frappe.new_doc("Driver Rating Summary")
        summary.driver = driver_id
        summary.avg_quality_rating = round(avg_quality, 2)
        summary.avg_timeliness_rating = round(avg_timeliness, 2)
        summary.avg_professionalism_rating = round(avg_professionalism, 2)
        summary.total_ratings = count
        summary.last_updated = now_datetime()
        summary.insert(ignore_permissions=True)

    frappe.db.commit()


@frappe.whitelist()
def get_driver_ratings(driver_id):
    summary = frappe.get_value(
        "Driver Rating Summary",
        {"driver": driver_id},
        [
            "driver",
            "driver_name",
            "avg_quality_rating",
            "avg_timeliness_rating",
            "avg_professionalism_rating",
            "total_ratings",
            "last_updated",
        ],
        as_dict=True,
    )
    return summary
