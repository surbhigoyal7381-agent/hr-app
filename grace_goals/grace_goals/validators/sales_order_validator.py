import frappe
import json

DEFAULTS = {
    "min_order_count": 1,
    "max_order_count": None,
    "min_volume": 0,
    "max_volume": None,
    "allowed_volume_units": None,
    "min_amount": 0,
    "max_amount": None,
}


def validate_sales_order(evidence_doc, goal_doc):
    config, source_label = _get_config_with_source()

    # ── DEBUG ──────────────────────────────────────────────────────────────
    frappe.log_error(
        f"[DEBUG] Sales Order Validator\n"
        f"  config source : {source_label}\n"
        f"  config values : {config}",
        "[DEBUG] sales_order_validator"
    )
    # ── END DEBUG ───────────────────────────────────────────────────────────

    errors = []
    lines = [f"[Sales Order] Validator: {source_label}"]

    order_count = int(evidence_doc.extracted_order_count or 0)
    volume = float(evidence_doc.extracted_volume or 0)
    volume_unit = (evidence_doc.extracted_volume_unit or "").strip()
    amount = float(evidence_doc.extracted_amount or 0)

    min_count = config.get("min_order_count", DEFAULTS["min_order_count"])
    if min_count is not None and order_count < min_count:
        errors.append(f"Order count {order_count} is below minimum required {min_count}.")
        lines.append(f"  ✗ Order count: {order_count} — below minimum {min_count}")
    else:
        lines.append(f"  ✓ Order count: {order_count} ≥ {min_count} (min)")

    max_count = config.get("max_order_count", DEFAULTS["max_order_count"])
    if max_count is not None:
        if order_count > max_count:
            errors.append(f"Order count {order_count} exceeds maximum allowed {max_count}.")
            lines.append(f"  ✗ Order count: {order_count} — exceeds maximum {max_count}")
        else:
            lines.append(f"  ✓ Order count: {order_count} ≤ {max_count} (max)")

    allowed_units = config.get("allowed_volume_units", DEFAULTS["allowed_volume_units"])
    if allowed_units:
        if volume_unit and volume_unit not in allowed_units:
            errors.append(f"Volume unit '{volume_unit}' not accepted. Allowed: {', '.join(allowed_units)}.")
            lines.append(f"  ✗ Unit: '{volume_unit}' — not in allowed list {allowed_units}")
        else:
            lines.append(f"  ✓ Unit: '{volume_unit}' — accepted")
    else:
        lines.append(f"  ✓ Unit: '{volume_unit}' — all units accepted")

    min_vol = config.get("min_volume", DEFAULTS["min_volume"])
    if min_vol is not None and volume < min_vol:
        errors.append(f"Volume {volume} {volume_unit} is below minimum required {min_vol}.")
        lines.append(f"  ✗ Volume: {volume} {volume_unit} — below minimum {min_vol}")
    else:
        lines.append(f"  ✓ Volume: {volume} {volume_unit} ≥ {min_vol} (min)")

    max_vol = config.get("max_volume", DEFAULTS["max_volume"])
    if max_vol is not None:
        if volume > max_vol:
            errors.append(f"Volume {volume} {volume_unit} exceeds maximum allowed {max_vol}.")
            lines.append(f"  ✗ Volume: {volume} {volume_unit} — exceeds maximum {max_vol}")
        else:
            lines.append(f"  ✓ Volume: {volume} {volume_unit} ≤ {max_vol} (max)")

    min_amt = config.get("min_amount", DEFAULTS["min_amount"])
    if min_amt is not None and amount < min_amt:
        errors.append(f"Amount {amount} is below minimum required {min_amt}.")
        lines.append(f"  ✗ Amount: {amount} — below minimum {min_amt}")
    else:
        lines.append(f"  ✓ Amount: {amount} ≥ {min_amt} (min)")

    max_amt = config.get("max_amount", DEFAULTS["max_amount"])
    if max_amt is not None:
        if amount > max_amt:
            errors.append(f"Amount {amount} exceeds maximum allowed {max_amt}.")
            lines.append(f"  ✗ Amount: {amount} — exceeds maximum {max_amt}")
        else:
            lines.append(f"  ✓ Amount: {amount} ≤ {max_amt} (max)")

    if errors:
        frappe.log_error("\n".join(errors), f"Sales Order validation failed for {goal_doc.name}")

    return {"errors": errors, "notes": "\n".join(lines)}


def _get_config_with_source():
    try:
        records = frappe.get_all(
            "Evidence Validator",
            filters={"evidence_type": "Sales Order", "enabled": 1},
            fields=["validator_name", "validator_logic"],
            limit=1,
        )
        if records and records[0].get("validator_logic"):
            config = json.loads(records[0]["validator_logic"])
            return config, f'"{records[0]["validator_name"]}"'
    except Exception as e:
        frappe.log_error(str(e), "Sales Order Validator Config Error")
    return dict(DEFAULTS), "system defaults (no validator configured)"
