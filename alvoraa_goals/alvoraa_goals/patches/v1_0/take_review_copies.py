"""Give reviews that existed before slice 010 group D their own copies (commit 12).

The work, the dry run and the rollback helpers are in alvoraa_goals.review_backfill;
read its docstring. Safe to run twice: a review that already has copies is skipped.

Dry run on a site before its migrate (read-only), on the user's word:
    bench --site <site> execute alvoraa_goals.review_backfill.report

Rollback: see review_backfill.undo_backfill and copy_ratings_back_for_rollback.
"""

import frappe


def execute():
    # A plain patches.txt line runs before Frappe syncs DocTypes, and on a site
    # that has never had group D the copy table does not exist yet. Sync the
    # three DocTypes this reads and writes first. HR Settings fields are added
    # after migrate; until then the settings reader gives the defaults.
    frappe.reload_doc("alvoraa_goals", "doctype", "alvoraa_review_item")
    frappe.reload_doc("alvoraa_goals", "doctype", "alvoraa_appraisal_extension")
    frappe.reload_doc("alvoraa_goals", "doctype", "kpi")

    import alvoraa_goals.review_backfill as review_backfill

    result = review_backfill.run()
    print(f"Review copies: {result['reviews_copied']} reviews, {result['copies_made']} copies, "
          f"{len(result['failed'])} failed")
