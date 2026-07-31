import frappe


def activate_review_goals(review_record_name):
    """
    Atomically promote draft goal clones to live goals when employee submits.
    Deletes is_review_draft=1 goals that were removed during review,
    and clears is_review_draft on the ones that should go live.
    """
    review = frappe.get_doc("PMS Review Record", review_record_name)
    employee = review.employee
    cycle = review.cycle

    # live goals before review
    live_goals = frappe.get_all(
        "PMS Business Goal",
        filters={"employee": employee, "cycle": cycle, "is_review_draft": 0},
        pluck="name",
    )

    # draft clones created during review
    draft_goals = frappe.get_all(
        "PMS Business Goal",
        filters={"employee": employee, "cycle": cycle, "is_review_draft": 1},
        fields=["name", "carried_over_from"],
    )

    draft_originals = {d.carried_over_from for d in draft_goals if d.carried_over_from}

    # delete live goals that were removed in the review draft
    for g in live_goals:
        if g not in draft_originals:
            frappe.delete_doc("PMS Business Goal", g, ignore_permissions=True)

    # promote drafts to live
    for d in draft_goals:
        frappe.db.set_value("PMS Business Goal", d.name, "is_review_draft", 0)
        if d.carried_over_from and frappe.db.exists("PMS Business Goal", d.carried_over_from):
            frappe.delete_doc("PMS Business Goal", d.carried_over_from, ignore_permissions=True)

    frappe.db.commit()
