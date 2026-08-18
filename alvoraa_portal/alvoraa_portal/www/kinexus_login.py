import frappe

no_cache = 1


def get_context(context):
    # Already logged in → send to the right portal immediately
    if frappe.session.user != "Guest":
        from alvoraa_portal.auth import _portal_home_for
        roles = set(frappe.get_roles(frappe.session.user))
        desk_roles = {"System Manager", "HR Manager", "HR User", "Administrator",
                      "Accounts Manager", "Accounts User"}
        if desk_roles.intersection(roles):
            frappe.local.flags.redirect_location = "/app"
        else:
            frappe.local.flags.redirect_location = _portal_home_for(frappe.session.user)
        raise frappe.Redirect

    context.no_cache   = 1
    context.no_header  = 1
    context.no_footer  = 1
    context.no_sidebar = 1
    context.title      = "Sign In – Kinexus HRMS"
