from alvoraa_portal.tenant_context import get_branding

import frappe


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.flags.redirect_location = "/alvoraa-login?redirect-to=/hrms-employee"
        raise frappe.Redirect
    context.no_cache  = 1
    context.update(get_branding())
