import frappe
from frappe.utils import getdate


def check_duplicate(evidence_doc, goal_name):
    if not evidence_doc.extracted_amount and not evidence_doc.extracted_order_count:
        return None
    existing = frappe.db.sql("""
        SELECT ge.name, ge.extracted_amount, ge.extracted_date, ge.extracted_order_count,
               ge.parent as goal_name
        FROM `tabGoal Evidence` ge
        WHERE ge.validation_status != 'Rejected'
          AND ge.name != %(name)s
          AND (
              (ge.extracted_amount IS NOT NULL AND ge.extracted_amount = %(amount)s)
              OR (ge.extracted_order_count IS NOT NULL AND ge.extracted_order_count = %(count)s)
          )
    """, {
        "name": evidence_doc.name or "new",
        "amount": evidence_doc.extracted_amount,
        "count": evidence_doc.extracted_order_count,
    }, as_dict=True)
    for dup in existing:
        score = _similarity_score(evidence_doc, dup)
        if score >= 80:
            _log_duplicate(evidence_doc, dup, score, goal_name)
            return {"score": score, "duplicate_name": dup.name}
    return None


def _similarity_score(ev1, ev2):
    score = 0
    if ev1.extracted_amount and ev2.get("extracted_amount") and ev1.extracted_amount == ev2["extracted_amount"]:
        score += 40
    if ev1.extracted_order_count and ev2.get("extracted_order_count") and ev1.extracted_order_count == ev2["extracted_order_count"]:
        score += 30
    if ev1.extracted_date and ev2.get("extracted_date"):
        delta = abs((getdate(ev1.extracted_date) - getdate(ev2["extracted_date"])).days)
        if delta == 0:
            score += 30
        elif delta <= 1:
            score += 15
    return min(score, 100)


def _log_duplicate(ev1, ev2, score, goal_name):
    try:
        dup_check = frappe.new_doc("Evidence Duplicate Check")
        dup_check.evidence_1 = ev1.name or "pending"
        dup_check.evidence_2 = ev2.name
        dup_check.goal_1 = goal_name
        dup_check.goal_2 = ev2.get("goal_name")
        dup_check.similarity_score = score
        dup_check.flagged_by = "System"
        dup_check.action_taken = "Pending Review"
        dup_check.flags.ignore_permissions = True
        dup_check.insert()
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Duplicate log failed")
