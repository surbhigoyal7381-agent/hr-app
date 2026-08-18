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

    # `value` is the only measure Goal Evidence carries. extracted_order_count,
    # extracted_volume, extracted_volume_unit and extracted_amount were all removed with
    # the move to generic evidence, so the volume and unit rules below have no data to
    # read and are dropped rather than silently evaluating zero against a minimum.
    order_count = float(evidence_doc.value or 0)
    amount = order_count

    min_count = config.get("min_value", config.get("min_order_count", DEFAULTS["min_order_count"]))
    if min_count is not None and order_count < min_count:
        errors.append(f"Value {order_count} is below minimum required {min_count}.")
        lines.append(f"  ✗ Value: {order_count} — below minimum {min_count}")
    else:
        lines.append(f"  ✓ Value: {order_count} ≥ {min_count} (min)")

    max_count = config.get("max_value", config.get("max_order_count", DEFAULTS["max_order_count"]))
    if max_count is not None:
        if order_count > max_count:
            errors.append(f"Value {order_count} exceeds maximum allowed {max_count}.")
            lines.append(f"  ✗ Value: {order_count} — exceeds maximum {max_count}")
        else:
            lines.append(f"  ✓ Value: {order_count} ≤ {max_count} (max)")

    # The volume and unit rules that stood here are removed with their data. Goal
    # Evidence no longer carries extracted_volume or extracted_volume_unit, so these
    # checks could only ever have compared 0 against a minimum and failed every time,
    # or passed vacuously. Any min_volume / max_volume / allowed_volume_units left in a
    # saved validator config is now ignored, and says so in the notes.
    for stale in ("allowed_volume_units", "min_volume", "max_volume"):
        if config.get(stale) is not None:
            lines.append(f"  - {stale}: ignored, evidence no longer records volume")

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
