import frappe
import json
from frappe.utils import getdate, today


def validate_invoice(evidence_doc, goal_doc):
    config, source_label = _get_config_with_source()
    errors = []
    lines = [f"[Invoice] Validator: {source_label}"]

    max_age_days = config.get("max_age_days", 90)
    if evidence_doc.extracted_date:
        age = (getdate(today()) - getdate(evidence_doc.extracted_date)).days
        if age > max_age_days:
            errors.append(f"Invoice date is {age} days old (max allowed: {max_age_days})")
            lines.append(f"  ✗ Date: {evidence_doc.extracted_date} — {age} days old (max {max_age_days})")
        else:
            lines.append(f"  ✓ Date: {evidence_doc.extracted_date} — {age} days old (max {max_age_days})")
    else:
        lines.append("  — Date: not provided (skipped)")

    amount = float(evidence_doc.extracted_amount or 0)
    min_amount = config.get("min_amount", 0)
    if amount < min_amount:
        errors.append(f"Amount {amount} is below minimum {min_amount}")
        lines.append(f"  ✗ Amount: {amount} — below minimum {min_amount}")
    else:
        lines.append(f"  ✓ Amount: {amount} ≥ {min_amount} (min)")

    max_amount = config.get("max_amount")
    if max_amount is not None:
        if amount > max_amount:
            errors.append(f"Amount {amount} exceeds maximum {max_amount}")
            lines.append(f"  ✗ Amount: {amount} — exceeds maximum {max_amount}")
        else:
            lines.append(f"  ✓ Amount: {amount} ≤ {max_amount} (max)")

    if errors:
        frappe.log_error("\n".join(errors), f"Invoice validation failed for {goal_doc.name}")

    return {"errors": errors, "notes": "\n".join(lines)}


def _get_config_with_source():
    try:
        records = frappe.get_all(
            "Evidence Validator",
            filters={"evidence_type": "Invoice", "enabled": 1},
            fields=["validator_name", "validator_logic"],
            limit=1,
        )
        if records and records[0].get("validator_logic"):
            config = json.loads(records[0]["validator_logic"])
            return config, f'"{records[0]["validator_name"]}"'
    except Exception as e:
        frappe.log_error(str(e), "Invoice Validator Config Error")
    return {}, "system defaults (no validator configured)"
