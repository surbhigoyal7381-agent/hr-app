import frappe


_VALID_TRANSITIONS = {
    "Not Started": ["Self Review Open"],
    "Self Review Open": ["Self Review Submitted", "Manager Preparation"],
    "Self Review Submitted": ["Manager Preparation"],
    "Manager Preparation": ["Additional Manager Review", "Joint Manager Discussion"],
    "Additional Manager Review": ["Joint Manager Discussion"],
    "Joint Manager Discussion": ["Employee Invited to Dialogue"],
    "Employee Invited to Dialogue": ["Dialogue Complete"],
    "Dialogue Complete": ["Manager Adjustments"],
    "Manager Adjustments": ["Final Form With Employee", "Returned for Amendment"],
    "Returned for Amendment": ["Manager Adjustments"],
    "Final Form With Employee": ["Submitted by Employee"],
    "Submitted by Employee": ["In Calibration", "Calibrated", "Closed"],
    "In Calibration": ["Calibrated"],
    "Calibrated": ["Closed"],
    "Closed": [],
}


def validate(doc, method=None):
    _validate_status_transition(doc)
    _validate_return_count(doc)


def before_save(doc, method=None):
    _stamp_dialogue_date(doc)
    _stamp_employee_submission(doc)


def on_update(doc, method=None):
    _notify_on_status_change(doc)


def _validate_status_transition(doc):
    if doc.is_new():
        return
    old_status = frappe.db.get_value("PMS Review Record", doc.name, "status")
    if old_status == doc.status:
        return
    allowed = _VALID_TRANSITIONS.get(old_status, [])
    if doc.status not in allowed and not frappe.db.exists(
        "Has Role", {"parent": frappe.session.user, "role": ["in", ["HR Manager", "System Manager"]]}
    ):
        frappe.throw(
            f"Cannot move review from '{old_status}' to '{doc.status}'. "
            f"Allowed next states: {', '.join(allowed) or 'none'}."
        )


def _validate_return_count(doc):
    if doc.status == "Returned for Amendment":
        doc.return_count = (doc.return_count or 0) + 1
        if doc.return_count > 3:
            frappe.throw("Maximum 3 return-for-amendment cycles reached. Escalate to HR.")


def _stamp_dialogue_date(doc):
    if doc.status == "Dialogue Complete" and not doc.dialogue_completed_on:
        doc.dialogue_completed_on = frappe.utils.now()


def _stamp_employee_submission(doc):
    if doc.status == "Submitted by Employee" and not doc.employee_submitted_on:
        doc.employee_submitted_on = frappe.utils.now()


def _notify_on_status_change(doc):
    if doc.is_new():
        return
    old_status = frappe.db.get_value("PMS Review Record", doc.name, "status")
    if old_status == doc.status:
        return
    frappe.enqueue(
        "hrms.pms.pms_notifications.send_status_change_notification",
        review_record=doc.name,
        old_status=old_status,
        new_status=doc.status,
        now=False,
    )
