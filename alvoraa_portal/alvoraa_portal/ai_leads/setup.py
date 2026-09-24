"""Switching AI lead intake on or off for one tenant. No screen in slice one.

Run by us on the server, after the tenant has the `crm_ai_intake` feature:

    bench --site <site> execute alvoraa_portal.ai_leads.setup.switch_on \\
        --kwargs "{'mailbox': 'Sales', 'daily_cap': 200}"

The API key is set separately, by a person, and never passed through here:

    bench --site <site> set-config ai_lead_intake_api_key "$KEY"   (typed, not pasted into a file)

switch_on does, in order: checks the CRM and the feature, adds the AI fields to CRM Lead
and the opt-in field to Email Account, adds the "Needs Review" lead status and a public
"Needs review" list in the CRM, creates the service user the leads are made by, checks
the mailbox against every mailbox rule, ticks it, and turns the sweep on. Safe to run twice.
"""
import json

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.installer import update_site_config
from frappe.utils import now_datetime

import alvoraa_portal.ai_leads.guards as guards
import alvoraa_portal.ai_leads.intake as intake

LEAD_FIELDS = [
    {"fieldname": "alvoraa_ai_section", "label": "AI intake", "fieldtype": "Section Break",
     "insert_after": "lost_notes", "collapsible": 1},
    {"fieldname": "alvoraa_ai_created", "label": "Created from an email by AI", "fieldtype": "Check",
     "insert_after": "alvoraa_ai_section", "read_only": 1},
    {"fieldname": "alvoraa_ai_needs_review", "label": "Needs review", "fieldtype": "Check",
     "insert_after": "alvoraa_ai_created"},
    {"fieldname": "alvoraa_ai_confidence", "label": "AI confidence", "fieldtype": "Percent",
     "insert_after": "alvoraa_ai_needs_review", "read_only": 1},
    {"fieldname": "alvoraa_ai_mailbox", "label": "Mailbox", "fieldtype": "Link",
     "options": "Email Account", "insert_after": "alvoraa_ai_confidence", "read_only": 1},
    {"fieldname": "alvoraa_ai_communication", "label": "Source email", "fieldtype": "Link",
     "options": "Communication", "insert_after": "alvoraa_ai_mailbox", "read_only": 1},
    {"fieldname": "alvoraa_ai_model", "label": "AI model", "fieldtype": "Data",
     "insert_after": "alvoraa_ai_communication", "read_only": 1},
    {"fieldname": "alvoraa_ai_prompt_version", "label": "Prompt version", "fieldtype": "Data",
     "insert_after": "alvoraa_ai_model", "read_only": 1},
]
ACCOUNT_FIELDS = [
    {"fieldname": guards.INTAKE_FIELD, "label": "Read this mailbox for sales leads (AI)",
     "fieldtype": "Check", "insert_after": "enable_incoming",
     "description": "New enquiries become CRM leads with the columns filled by AI. "
                    "Refused for HR, payroll and default mailboxes."},
    {"fieldname": guards.SINCE_FIELD, "label": "Read for leads since", "fieldtype": "Datetime",
     "insert_after": guards.INTAKE_FIELD, "read_only": 1},
]
VIEW_LABEL = "Needs review"


def _require():
    if "crm" not in frappe.get_installed_apps():
        frappe.throw(_("Frappe CRM is not installed on this site."))
    from alvoraa_portal.subscription import has_feature
    if not has_feature("crm_ai_intake"):
        frappe.throw(_("Tick 'AI lead intake' for this tenant in the admin console first."))


def ensure_fields():
    create_custom_fields({"CRM Lead": LEAD_FIELDS, "Email Account": ACCOUNT_FIELDS},
                         ignore_validate=True, update=True)


def ensure_status():
    if frappe.db.exists("CRM Lead Status", intake.NEEDS_REVIEW):
        return
    top = max(frappe.get_all("CRM Lead Status", pluck="position") or [0])
    doc = frappe.new_doc("CRM Lead Status")
    doc.lead_status = intake.NEEDS_REVIEW
    doc.type = "Open"
    doc.color = "amber"
    doc.position = (top or 0) + 1
    doc.insert(ignore_permissions=True)


def ensure_view():
    if frappe.db.exists("CRM View Settings", {"label": VIEW_LABEL, "dt": "CRM Lead"}):
        return
    doc = frappe.new_doc("CRM View Settings")
    doc.label = VIEW_LABEL
    doc.dt = "CRM Lead"
    doc.type = "list"
    doc.filters = json.dumps({"status": intake.NEEDS_REVIEW})
    doc.public = 1
    doc.user = ""   # CRM's get_views lists public views where user == "", not NULL (review P2)
    doc.load_default_columns = 1
    doc.icon = ""
    doc.insert(ignore_permissions=True)


def ensure_service_user():
    email = intake.service_user_email()
    if not frappe.db.exists("User", email):
        user = frappe.new_doc("User")
        user.email = email
        user.first_name = "AI lead intake"
        user.user_type = "System User"
        user.send_welcome_email = 0
        user.append("roles", {"role": "Sales User"})
        user.flags.ignore_permissions = True
        user.insert(ignore_permissions=True)
    return email


def switch_on(mailbox, daily_cap=intake.DEFAULT_CAP, owner=None):
    _require()
    ensure_fields()
    ensure_status()
    ensure_view()
    service_user = ensure_service_user()

    if not frappe.db.exists("Email Account", mailbox):
        frappe.throw(_("No Email Account called {0}.").format(mailbox))
    acc = frappe.get_doc("Email Account", mailbox)
    acc.set(guards.INTAKE_FIELD, 1)
    found = guards.problems(acc, guards._linked_user_roles(mailbox), True)
    if found:
        frappe.throw("<br>".join(found), title=_("This mailbox cannot be read for leads"))
    # set_value, not save(): saving an Email Account with a password tests the IMAP
    # connection, which is not this step's business. The same rules ran just above.
    frappe.db.set_value("Email Account", mailbox,
                        {guards.INTAKE_FIELD: 1, guards.SINCE_FIELD: now_datetime()})

    update_site_config("ai_lead_intake_enabled", 1)
    update_site_config("ai_lead_intake_daily_cap", int(min(int(daily_cap), intake.CEILING)))
    update_site_config("ai_lead_intake_user", service_user)
    if owner:
        update_site_config("ai_lead_intake_owner", owner)
    frappe.db.commit()
    return {
        "mailbox": mailbox,
        "daily_cap": min(int(daily_cap), intake.CEILING),
        "service_user": service_user,
        "api_key_set": bool((frappe.get_site_config().get("ai_lead_intake_api_key") or "").strip()),
    }


def switch_off():
    """The kill switch (SEC-21). Stops every model call from the next sweep on."""
    update_site_config("ai_lead_intake_enabled", 0)
    return {"enabled": False}
