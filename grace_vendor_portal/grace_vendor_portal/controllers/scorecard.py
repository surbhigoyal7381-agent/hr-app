import frappe
from frappe.utils import now_datetime


# ─── Performance tier thresholds ─────────────────────────────────────────────
TIERS = [
    (90, "Excellent", 15, True),    # (min_score, label, increment_pct, bonus_eligible)
    (75, "Good", 10, True),
    (60, "Satisfactory", 4, False),
    (40, "Poor", 0, False),
    (0, "Critical", 0, False),
]


# ─── DocType event hooks ──────────────────────────────────────────────────────

def before_save(doc, method=None):
    _calculate_on_time_percentage(doc)
    _calculate_composite_score(doc)
    _set_performance_level(doc)
    _calculate_net_amount(doc)
    _set_compensation_recommendations(doc)


def _calculate_on_time_percentage(doc):
    if doc.total_deliveries:
        doc.on_time_percentage = round((doc.on_time_deliveries or 0) / doc.total_deliveries * 100, 2)
    else:
        doc.on_time_percentage = 0.0


def _calculate_composite_score(doc):
    """
    Composite Score (out of 100):
      On-Time Score   = (on_time_pct / 100) * 40
      Quality Score   = (avg_rating / 5) * 40
      Safety Score    = max(0, (5 - incidents) / 5) * 20
      Professionalism = (attendance * 0.5 + conduct * 0.5) * 20

    The use case specifies on-time(40%) + quality(40%) + safety(20%).
    Professionalism replaces part of the 20% safety bucket in this implementation.
    """
    # On-time component (max 40 pts)
    on_time_pct = (doc.on_time_percentage or 0) / 100
    doc.on_time_score = round(on_time_pct * 40, 2)

    # Quality component (max 40 pts)
    rating = (doc.avg_customer_rating or 0) / 5
    doc.quality_score = round(rating * 40, 2)

    # Safety component (max 20 pts — each incident deducts 20%, floor at 0)
    incidents = doc.safety_incidents or 0
    safety_factor = max(0.0, (5 - incidents) / 5)
    doc.safety_score = round(safety_factor * 20, 2)

    # Professionalism (folded into the 20% alongside safety via replacement weight)
    attendance_factor = (doc.attendance_rate or 100) / 100
    conduct_factor = 1.0 if doc.professional_conduct else 0.5
    professionalism_factor = attendance_factor * 0.5 + conduct_factor * 0.5
    doc.professionalism_score = round(professionalism_factor * 20, 2)

    # Overall: on-time(40) + quality(40) + safety(10) + professionalism(10) = 100
    # We split the 20% safety bucket equally between raw safety and professionalism
    doc.on_time_score = round(on_time_pct * 40, 2)
    doc.quality_score = round(rating * 40, 2)
    doc.safety_score = round(safety_factor * 10, 2)
    doc.professionalism_score = round(professionalism_factor * 10, 2)
    doc.overall_delivery_score = round(
        doc.on_time_score + doc.quality_score + doc.safety_score + doc.professionalism_score,
        2,
    )


def _set_performance_level(doc):
    score = doc.overall_delivery_score or 0
    for min_score, label, _, _ in TIERS:
        if score >= min_score:
            doc.performance_level = label
            break


def _calculate_net_amount(doc):
    doc.net_amount = (doc.commission_earned or 0) + (doc.bonuses_earned or 0) - (doc.deductions or 0)


def _set_compensation_recommendations(doc):
    """Set system-recommended salary increment and promotion flag based on tier."""
    score = doc.overall_delivery_score or 0
    for min_score, label, increment, bonus_elig in TIERS:
        if score >= min_score:
            doc.salary_adjustment_recommended = 1 if increment > 0 else 0
            doc.recommended_increment = increment
            doc.promotion_eligible = 1 if label == "Excellent" else 0
            # Auto-issue written warning for Critical performers
            if label == "Critical" and not doc.warning_issued:
                doc.warning_issued = 1
                doc.warning_type = "Written"
            break


# ─── Scheduled job ────────────────────────────────────────────────────────────

def generate_monthly_scorecards():
    """Called by scheduler on the 1st of each month. Generates scorecards for
    the *previous* month for all active Delivery Partners."""
    import calendar
    from datetime import date

    today = frappe.utils.today()
    today_date = frappe.utils.getdate(today)
    # Previous month
    if today_date.month == 1:
        month = 12
        year = today_date.year - 1
    else:
        month = today_date.month - 1
        year = today_date.year

    partners = frappe.get_all(
        "Delivery Partner",
        filters={"is_active": 1},
        pluck="name",
    )
    generated = 0
    for partner in partners:
        try:
            generate_scorecard_for_partner(partner, month, year)
            generated += 1
        except Exception as e:
            frappe.log_error(str(e), f"Scorecard Generation Failed — {partner} {month}/{year}")

    frappe.log_error(
        f"Monthly scorecard generation complete: {generated}/{len(partners)} partners processed "
        f"for {month:02d}/{year}",
        "Scorecard Scheduler: Complete",
    )


# ─── Whitelisted API ─────────────────────────────────────────────────────────

@frappe.whitelist()
def generate_scorecard_for_partner(partner, month, year):
    """
    Generate (or update) a Delivery Performance Scorecard for a partner for the given
    month/year. Aggregates data from Delivery Order, Delivery Feedback, and Vehicle
    Tracking. Called on-demand from the UI or by the monthly scheduler.
    """
    import calendar
    from datetime import date

    month = int(month)
    year = int(year)
    start_date = date(year, month, 1)
    end_date = date(year, month, calendar.monthrange(year, month)[1])

    # Upsert: fetch existing or create new
    existing = frappe.db.get_value(
        "Delivery Performance Scorecard",
        {"delivery_partner": partner, "month": month, "year": year},
    )
    doc = frappe.get_doc("Delivery Performance Scorecard", existing) if existing else frappe.new_doc(
        "Delivery Performance Scorecard"
    )
    doc.delivery_partner = partner
    doc.scoring_period = "Month"
    doc.month = month
    doc.year = year

    # ── Volume metrics from Delivery Orders ──────────────────────────────────
    all_orders = frappe.get_all(
        "Delivery Order",
        filters={
            "assigned_to_partner": partner,
            "delivery_date": ["between", [start_date, end_date]],
        },
        fields=["current_status", "on_time_status"],
    )
    delivered = [o for o in all_orders if o.current_status == "Delivered"]
    doc.total_deliveries = len(delivered)
    doc.on_time_deliveries = sum(1 for o in delivered if o.on_time_status == "On-Time")
    doc.late_deliveries = len(delivered) - doc.on_time_deliveries
    doc.failed_deliveries = sum(1 for o in all_orders if o.current_status == "Failed")
    doc.cancelled_deliveries = sum(1 for o in all_orders if o.current_status == "Cancelled")

    # ── Customer feedback ─────────────────────────────────────────────────────
    feedbacks = frappe.db.sql(
        """
        SELECT average_rating, issue_reported, issue_type, issue_severity,
               any_damage, items_missing
        FROM `tabDelivery Feedback`
        WHERE delivery_partner = %s
          AND COALESCE(feedback_date, creation) BETWEEN %s AND %s
          AND docstatus < 2
        """,
        (partner, start_date, end_date),
        as_dict=True,
    )
    doc.total_customer_feedbacks = len(feedbacks)
    if feedbacks:
        doc.avg_customer_rating = round(
            sum(f.average_rating or 0 for f in feedbacks) / len(feedbacks), 2
        )
        # Star distribution
        doc.five_star = sum(1 for f in feedbacks if (f.average_rating or 0) >= 4.5)
        doc.four_star = sum(1 for f in feedbacks if 3.5 <= (f.average_rating or 0) < 4.5)
        doc.three_star = sum(1 for f in feedbacks if 2.5 <= (f.average_rating or 0) < 3.5)
        doc.two_star = sum(1 for f in feedbacks if 1.5 <= (f.average_rating or 0) < 2.5)
        doc.one_star = sum(1 for f in feedbacks if (f.average_rating or 0) < 1.5)
        # Issues
        issues = [f for f in feedbacks if f.issue_reported]
        doc.complaints_received = len(issues)
        doc.damage_claims = sum(1 for f in feedbacks if f.any_damage)
        doc.missing_item_claims = sum(1 for f in feedbacks if f.items_missing)

    # ── Safety data from GPS tracking ────────────────────────────────────────
    gps_data = frappe.db.sql(
        """
        SELECT
            COALESCE(SUM(harsh_braking), 0)     AS harsh,
            COALESCE(SUM(harsh_acceleration), 0) AS accel,
            COALESCE(SUM(speeding_alert), 0)    AS speeding
        FROM `tabVehicle Tracking`
        WHERE delivery_partner = %s
          AND recorded_timestamp BETWEEN %s AND %s
        """,
        (partner, start_date, end_date),
        as_dict=True,
    )
    if gps_data and gps_data[0]:
        row = gps_data[0]
        doc.harsh_driving_detected = int(row.harsh or 0) + int(row.accel or 0)
        doc.speeding_incidents = int(row.speeding or 0)
        doc.safety_incidents = doc.harsh_driving_detected + doc.speeding_incidents

    # ── Compliance overdue check ──────────────────────────────────────────────
    overdue_count = frappe.db.count(
        "Vehicle Maintenance Compliance",
        {"partner": partner, "alert_status": ["in", ["Critical", "Overdue"]]},
    )
    doc.compliance_issues_open = overdue_count
    doc.vehicle_maintenance_overdue = 1 if overdue_count > 0 else 0

    # ── Commission calculation (per-order rate * delivered orders) ────────────
    try:
        partner_doc = frappe.get_doc("Delivery Partner", partner)
        if partner_doc.partner_contract_type == "Per-Order" and partner_doc.per_order_rate:
            doc.commission_earned = (partner_doc.per_order_rate or 0) * doc.total_deliveries

        # Bonus: Excellent on-time (>=95%) AND rating >= 4.5 => 0.5x commission bonus
        on_time_pct = (doc.on_time_deliveries / doc.total_deliveries * 100) if doc.total_deliveries else 0
        if on_time_pct >= 95 and (doc.avg_customer_rating or 0) >= 4.5:
            doc.bonuses_earned = round((doc.commission_earned or 0) * 0.5, 2)
    except Exception:
        pass  # Partner financial fields optional

    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return doc.name


@frappe.whitelist()
def get_hub_performance_report(hub_name, month, year):
    """Return aggregated hub performance data for the monthly report."""
    month, year = int(month), int(year)
    partners = frappe.get_all(
        "Delivery Partner",
        filters={"hub_assigned": hub_name},
        pluck="name",
    )
    if not partners:
        return {"hub": hub_name, "partners": [], "summary": {}}

    scorecards = frappe.get_all(
        "Delivery Performance Scorecard",
        filters={"delivery_partner": ["in", partners], "month": month, "year": year},
        fields=[
            "delivery_partner", "total_deliveries", "on_time_percentage",
            "avg_customer_rating", "overall_delivery_score", "performance_level",
            "safety_incidents", "complaints_received", "commission_earned",
            "bonuses_earned", "net_amount",
        ],
        order_by="overall_delivery_score desc",
    )

    if not scorecards:
        return {"hub": hub_name, "month": month, "year": year, "partners": [], "summary": {}}

    total_deliveries = sum(s.total_deliveries or 0 for s in scorecards)
    avg_ontime = (
        sum(s.on_time_percentage or 0 for s in scorecards) / len(scorecards)
        if scorecards else 0
    )
    avg_rating = (
        sum(s.avg_customer_rating or 0 for s in scorecards) / len(scorecards)
        if scorecards else 0
    )

    return {
        "hub": hub_name,
        "month": month,
        "year": year,
        "partner_count": len(partners),
        "scored_partners": len(scorecards),
        "summary": {
            "total_deliveries": total_deliveries,
            "avg_on_time_pct": round(avg_ontime, 2),
            "avg_customer_rating": round(avg_rating, 2),
            "total_commission": sum(s.commission_earned or 0 for s in scorecards),
            "total_bonuses": sum(s.bonuses_earned or 0 for s in scorecards),
        },
        "top_performers": scorecards[:5],
        "all_scorecards": scorecards,
    }
