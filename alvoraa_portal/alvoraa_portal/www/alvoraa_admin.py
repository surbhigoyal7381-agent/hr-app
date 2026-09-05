import frappe

no_cache = 1


def get_context(context):
    # Must be the CONTROL PLANE. A tenant site is an ordinary Frappe site whose
    # own admins legitimately hold System Manager, so a role check alone let a
    # tenant administrator open this console - verified on demo.alvoraa.co, which
    # returned 200 and rendered "Create New Tenant". The API refused the actions
    # (tenant_api._require_admin checks this same flag), but the console should
    # never appear on a tenant site at all.
    if not frappe.conf.get("alvoraa_control_plane"):
        raise frappe.DoesNotExistError

    # Must be logged in
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/alvoraa-login?redirect-to=/alvoraa-admin"
        raise frappe.Redirect


    # Must be System Manager on that control plane
    if "System Manager" not in frappe.get_roles(frappe.session.user):
        frappe.throw("Access denied. This page is for Alvoraa administrators only.",
                     frappe.PermissionError)

    context.no_cache   = 1
    context.no_header  = 1
    context.no_sidebar = 1
    context.title      = "Tenant Admin – Alvoraa"
