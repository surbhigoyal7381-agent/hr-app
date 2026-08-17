import frappe


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.flags.redirect_location = "/login?redirect-to=/driver-portal"
        raise frappe.Redirect
    context.no_cache  = 1
    context.no_footer = 1
