import frappe


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.flags.redirect_location = "/login?redirect-to=/pms-employee"
        raise frappe.Redirect
    context.no_cache = 1
