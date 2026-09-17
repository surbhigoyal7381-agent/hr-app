"""Stamp each review's lock release days (slice 010 group D fix round, security review m1).

Reviews keep the freeze point and removal setting that were in force when their
copies were taken; the lock release days were read live from HR Settings, so a
later change released (or extended) every running review's lock at once. The
field is new, so every review that already has copies gets today's setting,
which is the value it has been following. Safe to run twice: it writes the same
value again.
"""

import frappe


def execute():
    frappe.reload_doc("alvoraa_goals", "doctype", "alvoraa_appraisal_extension")

    import alvoraa_goals.review_items as review_items

    days = review_items.review_settings()["lock_release_days"]
    ext = frappe.qb.DocType("Alvoraa Appraisal Extension")
    (
        frappe.qb.update(ext)
        .set(ext.lock_release_days, days)
        .where(ext.items_taken_on.isnotnull())
    ).run()
