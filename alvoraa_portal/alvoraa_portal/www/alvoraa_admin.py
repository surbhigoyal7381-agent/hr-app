import frappe

no_cache = 1


def get_context(context):
    # Must be logged in
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/alvoraa-login?redirect-to=/alvoraa-admin"
        raise frappe.Redirect

    # Must be System Manager
    if "System Manager" not in frappe.get_roles(frappe.session.user):
        frappe.throw("Access denied. This page is for Alvoraa administrators only.",
                     frappe.PermissionError)

    context.no_cache   = 1
    context.no_header  = 1
    context.no_sidebar = 1
    context.title      = "Tenant Admin – Alvoraa"
