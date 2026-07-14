import frappe
from frappe.utils import now_datetime


def validate(doc, method=None):
    if not doc.feedback_date:
        doc.feedback_date = now_datetime()
    _validate_all_ratings(doc)
    _calculate_average_rating(doc)
    doc.auto_calculated_score = doc.average_rating
    if doc.issue_reported and not doc.issue_type:
        frappe.throw("Please select an Issue Type when Issue Reported is checked.")


def after_insert(doc, method=None):
    _update_delivery_order_feedback_link(doc)
    _update_partner_satisfaction_rating(doc)
    _check_and_escalate(doc)


def _validate_all_ratings(doc):
    rating_fields = [
        ("on_time_rating", "Timeliness"),
        ("behavior_rating", "Behavior"),
        ("product_condition_rating", "Product Condition"),
        ("quantity_accuracy_rating", "Quantity Accuracy"),
        ("overall_experience_rating", "Overall Experience"),
        ("ease_of_contact", "Ease of Contact"),
        ("problem_resolution", "Problem Resolution"),
    ]
    for fieldname, label in rating_fields:
        val = doc.get(fieldname)
        if val is not None and val != 0 and not (1 <= val <= 5):
            frappe.throw(f"{label} rating must be between 1 and 5. Got: {val}")


def _calculate_average_rating(doc):
    """Average of the 5 main rating factors (exclude ease_of_contact / problem_resolution
    unless the customer filled them in — they are optional sub-factors)."""
    main_ratings = [
        doc.on_time_rating,
        doc.behavior_rating,
        doc.product_condition_rating,
        doc.quantity_accuracy_rating,
        doc.overall_experience_rating,
    ]
    filled = [r for r in main_ratings if r]
    doc.average_rating = round(sum(filled) / len(filled), 2) if filled else 0.0


def _update_delivery_order_feedback_link(doc):
    """Link back to the Delivery Order so the order shows feedback was provided."""
    if not doc.delivery_order:
        return
    try:
        frappe.db.set_value(
            "Delivery Order",
            doc.delivery_order,
            {
                "feedback_provided": 1,
                "feedback_rating": doc.average_rating,
                "feedback_details_link": doc.name,
            },
        )
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(str(e), "Delivery Feedback: update order link failed")


def _update_partner_satisfaction_rating(doc):
    """Recalculate and persist the rolling average rating on the Delivery Partner."""
    if not doc.delivery_partner:
        return
    try:
        result = frappe.db.sql(
            """
            SELECT AVG(average_rating) as avg_r, COUNT(*) as total
            FROM `tabDelivery Feedback`
            WHERE delivery_partner = %s AND docstatus < 2
            """,
            doc.delivery_partner,
            as_dict=True,
        )
        if result:
            avg = round(result[0].avg_r or 0, 2)
            frappe.db.set_value(
                "Delivery Partner",
                doc.delivery_partner,
                "customer_satisfaction_rating",
                avg,
            )
            frappe.db.commit()
    except Exception as e:
        frappe.log_error(str(e), "Delivery Feedback: partner rating update failed")


def _check_and_escalate(doc):
    """Flag and alert on low ratings or high-severity issues."""
    should_flag = False

    if doc.average_rating and doc.average_rating <= 2:
        should_flag = True
        _send_low_rating_alert(doc)

    if doc.issue_severity in ("High", "Critical"):
        should_flag = True
        _send_issue_escalation_alert(doc)

    if should_flag:
        frappe.db.set_value("Delivery Feedback", doc.name, "flagged_for_review", 1)
        frappe.db.commit()


def _send_low_rating_alert(doc):
    try:
        recipient = "ops@gracedrinks.in"
        frappe.sendmail(
            recipients=[recipient],
            subject=f"[LOW RATING] Delivery Feedback — {doc.delivery_order} | Rating: {doc.average_rating}/5",
            message=f"""
            <p><strong>Low Delivery Rating Alert</strong></p>
            <table border="1" cellpadding="6" cellspacing="0">
              <tr><td>Feedback Record</td><td>{doc.name}</td></tr>
              <tr><td>Delivery Order</td><td>{doc.delivery_order}</td></tr>
              <tr><td>Delivery Partner</td><td>{doc.delivery_partner or 'Unknown'}</td></tr>
              <tr><td>Customer</td><td>{doc.customer_name or 'Unknown'}</td></tr>
              <tr><td>Average Rating</td><td><b>{doc.average_rating} / 5</b></td></tr>
              <tr><td>Timeliness</td><td>{doc.on_time_rating or '-'}/5</td></tr>
              <tr><td>Behavior</td><td>{doc.behavior_rating or '-'}/5</td></tr>
              <tr><td>Product Condition</td><td>{doc.product_condition_rating or '-'}/5</td></tr>
              <tr><td>Quantity Accuracy</td><td>{doc.quantity_accuracy_rating or '-'}/5</td></tr>
              <tr><td>Overall Experience</td><td>{doc.overall_experience_rating or '-'}/5</td></tr>
              <tr><td>Comment</td><td>{doc.overall_comment or '—'}</td></tr>
            </table>
            <p>Please review and take corrective action.</p>
            """,
        )
    except Exception as e:
        frappe.log_error(str(e), "Low Rating Alert Email Failed")


def _send_issue_escalation_alert(doc):
    try:
        recipient = "ops@gracedrinks.in"
        frappe.sendmail(
            recipients=[recipient],
            subject=f"[{doc.issue_severity.upper()} ISSUE] Delivery Feedback — {doc.delivery_order}",
            message=f"""
            <p><strong>Delivery Issue Escalation — Severity: {doc.issue_severity}</strong></p>
            <table border="1" cellpadding="6" cellspacing="0">
              <tr><td>Feedback Record</td><td>{doc.name}</td></tr>
              <tr><td>Delivery Order</td><td>{doc.delivery_order}</td></tr>
              <tr><td>Partner</td><td>{doc.delivery_partner or 'Unknown'}</td></tr>
              <tr><td>Issue Type</td><td>{doc.issue_type}</td></tr>
              <tr><td>Severity</td><td><b>{doc.issue_severity}</b></td></tr>
              <tr><td>Requested Action</td><td>{doc.requested_action or '—'}</td></tr>
              <tr><td>Description</td><td>{doc.issue_description or '—'}</td></tr>
            </table>
            <p>Please investigate and resolve within 24 hours.</p>
            """,
        )
    except Exception as e:
        frappe.log_error(str(e), "Issue Escalation Email Failed")


@frappe.whitelist()
def get_partner_feedback_summary(partner_name, month=None, year=None):
    """Return feedback statistics for a partner, optionally filtered by month/year."""
    filters = {"delivery_partner": partner_name}
    if month and year:
        import calendar
        from datetime import date
        m, y = int(month), int(year)
        start = date(y, m, 1)
        end = date(y, m, calendar.monthrange(y, m)[1])
        filters["feedback_date"] = ["between", [start, end]]

    feedbacks = frappe.get_all(
        "Delivery Feedback",
        filters=filters,
        fields=[
            "average_rating", "on_time_rating", "behavior_rating",
            "product_condition_rating", "quantity_accuracy_rating",
            "overall_experience_rating", "issue_reported", "issue_severity",
        ],
    )

    if not feedbacks:
        return {"total": 0}

    total = len(feedbacks)
    avg = sum(f.average_rating or 0 for f in feedbacks) / total
    by_star = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for f in feedbacks:
        star = round(f.average_rating or 0)
        by_star[max(1, min(5, star))] += 1

    issues = [f for f in feedbacks if f.issue_reported]
    critical = [f for f in issues if f.issue_severity in ("High", "Critical")]

    return {
        "total": total,
        "average_rating": round(avg, 2),
        "by_star": by_star,
        "issues_count": len(issues),
        "critical_issues": len(critical),
    }
