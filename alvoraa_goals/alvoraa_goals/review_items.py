"""Review copies: each review's own record of the Objectives and KPIs it rates.

Slice 010, group D. The decisions are in
docs/slices/010-portal-security-fixes/00c-review-copies-decisions.md (R1-R16)
and 00e-group-d-approved-decisions.md, which wins where they differ.

This module owns:

  review_settings()   the three organisation settings, read safely
  after_migrate()     installs those settings on HR Settings (migrate and install)

Log lines and errors from here carry document and row names only. Never a
title, a number, a rating, a comment or a reason (PRIV-15).
"""

import frappe
from frappe import _
from frappe.utils import cint

# ── Organisation settings (R6, R9, R12) ─────────────────────────────────────
#
# Custom fields on HR Settings: organisation-level, typed, and HR Settings keeps
# a Version row for every change, so "who moved the freeze point" has an answer.
# Not Global Defaults: hr_api.set_org_setting lets HR write any key there with
# no history (SEC-28).

FREEZE_SELF_SENT = "Self-review sent"
FREEZE_MANAGER_SENT = "Manager review sent"
FREEZE_HR_SENT = "HR sent"
FREEZE_POINTS = (FREEZE_HR_SENT, FREEZE_MANAGER_SENT, FREEZE_SELF_SENT)

REMOVAL_DISCARD = "Discard the copy"
REMOVAL_KEEP = "Keep the copy with a reason"
REMOVAL_MODES = (REMOVAL_DISCARD, REMOVAL_KEEP)

DEFAULT_LOCK_RELEASE_DAYS = 30

SETTING_FIELDS = {
    "freeze_point": "alvoraa_review_freeze_point",
    "lock_release_days": "alvoraa_review_lock_release_days",
    "removal_mode": "alvoraa_review_removal",
}

DEFAULTS = {
    "freeze_point": FREEZE_HR_SENT,
    "lock_release_days": DEFAULT_LOCK_RELEASE_DAYS,
    "removal_mode": REMOVAL_DISCARD,
}


def review_settings():
    """The three settings, never throwing.

    An empty or unknown value falls back to the default. A lock release below
    zero is treated as 0, which means the lock is never released (fail closed,
    SEC-22).
    """
    out = dict(DEFAULTS)
    for key, fieldname in SETTING_FIELDS.items():
        try:
            value = frappe.db.get_single_value("HR Settings", fieldname)
        except Exception:
            # Field not installed yet on this site: keep the default.
            continue
        if key == "freeze_point" and value in FREEZE_POINTS:
            out[key] = value
        elif key == "removal_mode" and value in REMOVAL_MODES:
            out[key] = value
        elif key == "lock_release_days" and value is not None:
            out[key] = max(cint(value), 0)
    return out


def validate_hr_settings(doc, method=None):
    """doc_events HR Settings validate: refuse a value outside the choices (SEC-28)."""
    freeze = doc.get(SETTING_FIELDS["freeze_point"])
    if freeze and freeze not in FREEZE_POINTS:
        frappe.throw(_("Choose when review numbers freeze from the list."))
    removal = doc.get(SETTING_FIELDS["removal_mode"])
    if removal and removal not in REMOVAL_MODES:
        frappe.throw(_("Choose what happens to a removed review item from the list."))
    days = doc.get(SETTING_FIELDS["lock_release_days"])
    if days not in (None, "") and cint(days) < 0:
        frappe.throw(
            _("The number of days before the review lock is released cannot be below 0. Use 0 for never.")
        )


def after_migrate():
    """Add the three settings to HR Settings, on migrate AND on install.

    Both, because a site built with `bench install-app` never runs a migrate
    (see alvoraa_portal/hooks.py). Safe to run again: fields are updated in
    place, and a setting that already has a value keeps it.
    """
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    create_custom_fields(
        {
            "HR Settings": [
                {
                    "fieldname": "alvoraa_review_tab",
                    "fieldtype": "Tab Break",
                    "label": "Performance Reviews",
                    "insert_after": "hiring_sender_email",
                },
                {
                    "fieldname": SETTING_FIELDS["freeze_point"],
                    "fieldtype": "Select",
                    "label": "Freeze review numbers when",
                    "options": "\n".join(FREEZE_POINTS),
                    "default": FREEZE_HR_SENT,
                    "insert_after": "alvoraa_review_tab",
                    "description": "Until then, approved updates dated inside the review period still reach the review. "
                    "A review keeps the choice that was in force when it was first opened.",
                },
                {
                    "fieldname": SETTING_FIELDS["lock_release_days"],
                    "fieldtype": "Int",
                    "label": "Release the Objective and KPI lock this many days after the cycle ends",
                    "default": str(DEFAULT_LOCK_RELEASE_DAYS),
                    "non_negative": 1,
                    "insert_after": SETTING_FIELDS["freeze_point"],
                    "description": "0 means never. The lock always ends when the review is completed.",
                },
                {
                    "fieldname": SETTING_FIELDS["removal_mode"],
                    "fieldtype": "Select",
                    "label": "When an item is removed from a review",
                    "options": "\n".join(REMOVAL_MODES),
                    "default": REMOVAL_DISCARD,
                    "insert_after": SETTING_FIELDS["lock_release_days"],
                    "description": "An item that already has a rating is always kept, marked Removed.",
                },
            ]
        },
        update=True,
    )

    # A custom field's default does not fill a Single that already exists, and an
    # Int with no stored value reads as 0 - which would mean "never release".
    for key, fieldname in SETTING_FIELDS.items():
        stored = frappe.qb.get_query(
            table="Singles",
            filters={"doctype": "HR Settings", "field": fieldname},
            fields="value",
        ).run()
        if not stored:
            frappe.db.set_single_value("HR Settings", fieldname, DEFAULTS[key])
