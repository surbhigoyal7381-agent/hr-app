import frappe
from frappe import _
from frappe.utils import now_datetime
from alvoraa_goals.validators.invoice_validator import validate_invoice
from alvoraa_goals.validators.sales_order_validator import validate_sales_order
from alvoraa_goals.validators.duplicate_detector import check_duplicate
from alvoraa_goals.controllers.goal import recalculate_progress, _append_audit_log


def validate_evidence(doc, method=None):
    # The debug blocks that wrote the goal, value and file link into the Error
    # Log and on-screen popups are gone (slice 010, PRIV-8).
    goal = frappe.get_doc("Individual Goal", doc.parent)
    if not doc.upload_date:
        doc.upload_date = now_datetime()
    if not doc.uploaded_by:
        doc.uploaded_by = frappe.session.user

    # Every new row waits for a person (slice 010, SEC-3). The automated rules
    # still run, and their result is a note for the approver - not an approval.
    if doc.evidence_type in ("Invoice", "Sales Order"):
        check = validate_invoice if doc.evidence_type == "Invoice" else validate_sales_order
        result = check(doc, goal)
        doc.validation_status = "Pending"
        doc.validation_notes = result["notes"] + (
            "\n→ Rule(s) failed — check before approving" if result["errors"]
            else "\n→ Rules passed — waiting for approval")

    else:
        doc.validation_status = "Pending"
        doc.validation_notes = "[Manual Entry] No automated validation — pending HR review"

    dup_result = check_duplicate(doc, goal.name)
    if dup_result:
        doc.validation_status = "Pending"
        doc.validation_notes += f"\n⚠ Duplicate detected (similarity: {dup_result['score']}%) — overriding to Pending for HR review"
        frappe.msgprint(f"Possible duplicate evidence detected (similarity: {dup_result['score']}%). Sent for HR review.", alert=True)


def after_insert_evidence(doc, method=None):
    _append_audit_log(doc.parent, "Evidence Added", None, doc.evidence_type, frappe.session.user, f"Evidence type: {doc.evidence_type}, status: {doc.validation_status}")
    if doc.validation_status == "Approved":
        recalculate_progress(doc.parent)


def can_validate_evidence(goal_name, goal=None):
    """May the current user approve or reject evidence on this goal?

    Validating somebody's evidence is the MANAGER's job - the person the goal's
    owner reports to - or HR's. It used to be anyone who could write the goal,
    which is far looser: a colleague with write access could sign off work they
    had no part in supervising, and the audit trail would carry their name as
    though they had.

    Same shape as the leave approver rule: a named responsibility, resolved from
    the employee record, not something a permission happens to imply.
    """
    try:
        goal = goal or frappe.get_doc("Individual Goal", goal_name)
    except Exception:
        return False

    # Never your own goal's evidence, whatever roles you hold (SEC-9).
    from hrms.alvoraa_hr_core.access import is_own_record
    if is_own_record(goal.employee):
        return False

    # READ, not write. Write on a goal belongs to whoever created it, so asking
    # for write shut out every manager who had not created their report's goal.
    # Read still keeps out anyone the goal is hidden from (slice 010, decision 5).
    if not frappe.has_permission("Individual Goal", "read", goal.name):
        return False

    roles = set(frappe.get_roles(frappe.session.user))
    if {"HR Manager", "HR User", "Administrator"} & roles:
        return True

    manager = frappe.db.get_value("Employee", goal.employee, "reports_to")
    mine = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
    return bool(manager and mine and manager == mine)


def _assert_can_validate(goal_name, goal=None):
    goal = goal or frappe.get_doc("Individual Goal", goal_name)
    from hrms.alvoraa_hr_core.access import refuse_own_decision
    refuse_own_decision(goal.employee, "Individual Goal", goal.name, "evidence.validate")
    if can_validate_evidence(goal_name, goal=goal):
        return
    owner = frappe.db.get_value("Individual Goal", goal_name, "employee")
    manager = frappe.db.get_value("Employee", owner, "reports_to") if owner else None
    if manager:
        who = frappe.db.get_value("Employee", manager, "employee_name") or manager
        frappe.throw(
            _("Only {0} or HR can validate evidence on this goal.").format(who),
            frappe.PermissionError)
    frappe.throw(
        _("No manager is set for this goal's owner, so only HR can validate its "
          "evidence. HR can set 'Reports To' on the employee record."),
        frappe.PermissionError)


def _pending_row(goal, evidence_row):
    """The evidence row, found by its NAME and still waiting. Fails closed.

    By name, not list position: a position points at a different row the
    moment another row is added or the list is sorted (slice 010, SEC-3).
    """
    row = next((r for r in (goal.evidence_items or []) if r.name == evidence_row), None)
    if not row:
        frappe.throw(_("That evidence is not on this goal."), frappe.DoesNotExistError)
    if (row.validation_status or "Pending") != "Pending":
        frappe.throw(_("This evidence has already been decided."))
    return row


@frappe.whitelist()
def approve_evidence(goal_name, evidence_row):
    goal = frappe.get_doc("Individual Goal", goal_name)
    _assert_can_validate(goal_name, goal=goal)
    row = _pending_row(goal, evidence_row)
    # The row alone, not a save of the whole goal: the approver is the manager
    # or HR, who can read the goal but may not be allowed to write it.
    frappe.db.set_value("Goal Evidence", row.name, {
        "validation_status": "Approved",
        "approved_by": frappe.session.user,
        "approved_on": now_datetime(),
        "validation_notes": (row.validation_notes or "") + f"\n→ Manually approved by {frappe.session.user}",
    })
    frappe.db.commit()
    # Progress moves here, and only here: on approval.
    recalculate_progress(goal_name)
    _append_audit_log(goal_name, "Evidence Approved", "Pending", "Approved", frappe.session.user)
    return {"status": "approved"}


@frappe.whitelist()
def reject_evidence(goal_name, evidence_row, reason=""):
    goal = frappe.get_doc("Individual Goal", goal_name)
    _assert_can_validate(goal_name, goal=goal)
    row = _pending_row(goal, evidence_row)
    frappe.db.set_value("Goal Evidence", row.name, {
        "validation_status": "Rejected",
        "rejection_reason": reason,
        "validation_notes": (row.validation_notes or "") + f"\n→ Rejected by {frappe.session.user}: {reason}",
    })
    frappe.db.commit()
    _append_audit_log(goal_name, "Evidence Rejected", "Pending", "Rejected", frappe.session.user, reason)
    return {"status": "rejected"}


# ── Evidence files ──────────────────────────────────────────────────────────

def claim_evidence_file(file_url, doctype, name, endpoint):
    """Accept an evidence file only if the caller uploaded it, privately.

    Used by every path that stores an evidence or progress file: goal
    evidence, goal progress updates and KPI progress logs (slice 010, SEC-4).
    The browser sends the file URL, so it is treated as hostile: a public
    link, an outside address, a `javascript:` string or somebody else's file
    is refused, and nothing is written.

    The accepted file is attached to the goal or KPI, so reading it follows
    reading that record: the owner, their manager line and HR can open it; a
    colleague cannot. Returns the URL to store, or None when there is no file.
    """
    if file_url in (None, ""):
        return None
    from hrms.alvoraa_hr_core.access import refuse

    file_url = str(file_url).strip()
    message = _("Attach a file you uploaded yourself, as a private file.")
    if not file_url.startswith("/private/files/"):
        refuse(message, "SEC-4", endpoint, doctype, name)
    files = frappe.get_all(
        "File",
        filters={"file_url": file_url, "owner": frappe.session.user, "is_private": 1, "is_folder": 0},
        fields=["name", "attached_to_doctype", "attached_to_name"],
        limit=20,
    )
    if not files:
        refuse(message, "SEC-4", endpoint, doctype, name)
    if any(f.attached_to_doctype == doctype and f.attached_to_name == name for f in files):
        return file_url
    free = next((f for f in files if not f.attached_to_name), None)
    if not free:
        # Already attached to a different record: evidence for one goal is not
        # evidence for another.
        refuse(message, "SEC-4", endpoint, doctype, name)
    frappe.db.set_value("File", free.name, {"attached_to_doctype": doctype, "attached_to_name": name})
    return file_url
