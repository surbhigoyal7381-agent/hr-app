"""Which mailboxes may ever be read (01c SEC-8, spec V-1 to V-7).

Refused on save, not warned about - a rule on the document holds for the desk, the
REST API and any import alike. The sweep runs the same check again before every run
(V-7), so a mailbox that was changed by some other route stops being read.
"""
import re

import frappe
from frappe import _

INTAKE_FIELD = "alvoraa_ai_lead_intake"
SINCE_FIELD = "alvoraa_ai_since"
SALES_ROLES = {"Sales User", "Sales Manager", "System Manager"}
HR_ROLES = {"HR Manager", "HR User"}

# Local parts that mean HR, payroll or recruitment mail, on any domain.
_HR_LOCAL = re.compile(
    r"^(hr|hrd|hrm|payroll|salary|salaries|careers?|jobs?|recruit(ment|ing|er)?|"
    r"people|talent|leaves?|attendance|employees?)([._+-].*)?$",
    re.IGNORECASE,
)


def _roles_ok(roles):
    roles = set(roles or [])
    return bool(roles & SALES_ROLES) and not (roles & HR_ROLES)


def problems(doc, linked_user_roles=None, feature_on=True):
    """Every reason this mailbox may not be an intake mailbox. Empty = fine.

    `linked_user_roles` maps each user who has this mailbox in their own email
    settings to their roles; passed in so the check can be tested without a site.
    """
    found = []
    if not feature_on:
        found.append(_("AI lead intake is not part of this tenant's plan."))
    if doc.get("default_incoming"):
        found.append(_("It is the default incoming mailbox. Use a dedicated sales mailbox."))
    local = (doc.get("email_id") or "").split("@")[0]
    if _HR_LOCAL.match(local):
        found.append(_("Its address ({0}) looks like an HR, payroll or recruitment mailbox.").format(
            doc.get("email_id")))
    folders = doc.get("imap_folder") or []
    if doc.get("append_to") or any((f.get("append_to") if isinstance(f, dict) else f.append_to)
                                   for f in folders):
        found.append(_("It files mail into a document type ('Append To'). Clear it - the AI "
                       "creates the lead itself, and both together would make two."))
    if doc.get("create_lead_from_incoming_email"):
        found.append(_("Frappe CRM's own 'Create lead from incoming email' is on. Turn it off - "
                       "it would make a second, empty lead for every email."))
    if not doc.get("enable_incoming"):
        found.append(_("Incoming mail is switched off on this mailbox."))
    for user, roles in (linked_user_roles or {}).items():
        if not _roles_ok(roles):
            found.append(_("{0} has this mailbox in their own email settings but is not a sales "
                           "user, or holds an HR role.").format(user))
    return found


def _linked_user_roles(account_name):
    if not account_name or not frappe.db.exists("Email Account", account_name):
        return {}
    users = frappe.get_all("User Email", filters={"email_account": account_name}, pluck="parent")
    return {u: frappe.get_roles(u) for u in set(users)}


def _feature_on():
    from alvoraa_portal.subscription import has_feature
    return has_feature("crm_ai_intake")


def validate_email_account(doc, method=None):
    """Email Account validate hook. Silent unless the intake box is ticked."""
    if not doc.get(INTAKE_FIELD):
        return
    found = problems(doc, _linked_user_roles(doc.name if not doc.is_new() else None), _feature_on())
    if found:
        frappe.throw("<br>".join(found), title=_("This mailbox cannot be read for leads"))
    if not doc.get(SINCE_FIELD):
        doc.set(SINCE_FIELD, frappe.utils.now_datetime())


def validate_user(doc, method=None):
    """User validate hook: the mirror of the rule above (V-6).

    Cheap on every save: returns at once unless the user has mailboxes of their own
    and the site has the intake field at all.
    """
    rows = doc.get("user_emails") or []
    if not rows or not frappe.get_meta("Email Account").has_field(INTAKE_FIELD):
        return
    intake = set(frappe.get_all("Email Account", filters={INTAKE_FIELD: 1}, pluck="name"))
    if not intake:
        return
    linked = {r.email_account for r in rows} & intake
    if linked and not _roles_ok([r.role for r in doc.get("roles") or []]):
        frappe.throw(
            _("{0} is read for sales leads by AI. Only sales users without an HR role may have it "
              "in their email settings.").format(", ".join(sorted(linked))),
            title=_("Mailbox not allowed for this user"),
        )


def account_still_ok(account_name):
    """V-7: the sweep's own re-check before reading a mailbox."""
    doc = frappe.get_doc("Email Account", account_name)
    return not problems(doc, _linked_user_roles(account_name), _feature_on())
