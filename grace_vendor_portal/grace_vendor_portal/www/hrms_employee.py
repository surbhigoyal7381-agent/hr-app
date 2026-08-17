import frappe

from grace_vendor_portal.tenant_context import get_branding


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.flags.redirect_location = "/login?redirect-to=/hrms-employee"
        raise frappe.Redirect
    context.no_cache  = 1
    context.no_footer = 1
    context.update(get_branding())
