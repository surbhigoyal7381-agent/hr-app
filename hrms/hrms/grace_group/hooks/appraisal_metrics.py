"""
Grace Group – Appraisal Metrics Auto-Fetch
Hook: Appraisal → before_save  (also exposed as a client-triggered "Fetch Metrics" button)

For Delivery Executive appraisals this hook:
  1. Queries Attendance for the appraisal cycle period to compute Attendance Reliability %.
  2. Queries Daily Route Log to sum completed_drops, rto_count, and count SLA penalties.
  3. Injects the computed data into the Appraisal remarks field and updates KRA goal completion.
"""

import frappe
from frappe.utils import getdate, date_diff


@frappe.whitelist()
def fetch_metrics(doc, method=None):
    """
    Entry point for both the before_save hook and the "Fetch Metrics" custom button.
    When called via custom button: doc is passed as a JSON string from the client.
    """
    if isinstance(doc, str):
        import json
        doc = frappe.get_doc(json.loads(doc))

    if not doc.employee:
        return

    emp = frappe.get_doc("Employee", doc.employee)
    if emp.designation != "Delivery Executive":
        return  # Only auto-compute for drivers

    start_date = getattr(doc, "start_date", None)
    end_date = getattr(doc, "end_date", None)

    if not start_date or not end_date:
        # Fall back to appraisal cycle dates
        if doc.appraisal_cycle:
            cycle = frappe.get_doc("Appraisal Cycle", doc.appraisal_cycle)
            start_date = cycle.start_date
            end_date = cycle.end_date

    if not start_date or not end_date:
        return

    attendance = _get_attendance_metrics(doc.employee, start_date, end_date)
    route_metrics = _get_route_metrics(doc.employee, start_date, end_date)

    remarks = _build_remarks(attendance, route_metrics, start_date, end_date)
    doc.remarks = remarks

    _update_kra_scores(doc, attendance, route_metrics)


# ─────────────────────────────────────────────────────────────────────────────
# Metric Queries
# ─────────────────────────────────────────────────────────────────────────────

def _get_attendance_metrics(employee, start_date, end_date):
    rows = frappe.db.get_all(
        "Attendance",
        filters={
            "employee": employee,
            "attendance_date": ["between", [start_date, end_date]],
            "docstatus": 1,
        },
        fields=["status"],
    )
    total = len(rows)
    present = sum(1 for r in rows if r.status in ("Present", "Work From Home", "Half Day"))
    return {
        "total_days": total,
        "present_days": present,
        "reliability_pct": round((present / total * 100), 2) if total else 0,
    }


def _get_route_metrics(employee, start_date, end_date):
    rows = frappe.db.get_all(
        "Daily Route Log",
        filters={
            "employee": employee,
            "date": ["between", [start_date, end_date]],
            "docstatus": 1,
        },
        fields=["completed_drops", "rto_count", "penalty_logged", "route_category"],
    )
    total_drops = sum(r.completed_drops or 0 for r in rows)
    total_rto = sum(r.rto_count or 0 for r in rows)
    penalties = sum(1 for r in rows if r.penalty_logged)
    qcomm_logs = [r for r in rows if r.route_category == "Q-Comm"]
    rto_pct = round((total_rto / total_drops * 100), 2) if total_drops else 0
    return {
        "log_count": len(rows),
        "total_drops": total_drops,
        "total_rto": total_rto,
        "rto_pct": rto_pct,
        "penalty_count": penalties,
        "qcomm_log_count": len(qcomm_logs),
    }


def _build_remarks(attendance, route_metrics, start_date, end_date):
    lines = [
        f"=== Auto-Fetched Metrics ({start_date} to {end_date}) ===",
        "",
        "[ Attendance Reliability ]",
        f"  Present Days   : {attendance['present_days']} / {attendance['total_days']}",
        f"  Reliability    : {attendance['reliability_pct']}%",
        "",
        "[ Route & Delivery Performance ]",
        f"  Route Log Days : {route_metrics['log_count']}",
        f"  Completed Drops: {route_metrics['total_drops']}",
        f"  RTO Count      : {route_metrics['total_rto']}",
        f"  RTO Rate       : {route_metrics['rto_pct']}%",
        f"  SLA Penalties  : {route_metrics['penalty_count']}",
        f"  Q-Comm Logs    : {route_metrics['qcomm_log_count']}",
    ]
    return "\n".join(lines)


def _update_kra_scores(doc, attendance, route_metrics):
    """Update the goal_completion % on the Appraisal KRA child table rows."""
    if not hasattr(doc, "appraisal_kra") or not doc.appraisal_kra:
        return

    kra_score_map = {
        "Attendance Reliability": attendance["reliability_pct"],
        "Route Efficiency": max(0, 100 - route_metrics["rto_pct"]),
        "Q-Comm SLA Protection": 100 if route_metrics["penalty_count"] == 0 else max(0, 100 - (route_metrics["penalty_count"] * 20)),
    }

    for kra_row in doc.appraisal_kra:
        kra_title = frappe.db.get_value("KRA", kra_row.kra, "title") if kra_row.kra else None
        if kra_title and kra_title in kra_score_map:
            kra_row.goal_completion = kra_score_map[kra_title]
