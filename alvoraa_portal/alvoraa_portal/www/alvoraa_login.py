import frappe

from alvoraa_portal.tenant_context import get_branding

no_cache = 1


def get_context(context):
    # Already logged in → send to the right portal immediately
    if frappe.session.user != "Guest":
        from alvoraa_portal.auth import JOINER_ROLE, JOINING_PAGE, _portal_home_for
        roles = set(frappe.get_roles(frappe.session.user))
        desk_roles = {"System Manager", "HR Manager", "HR User", "Administrator",
                      "Accounts Manager", "Accounts User"}
        if JOINER_ROLE in roles:
            # Slice 079. This door answered before `home_page_for` existed and
            # never learnt about it, so a signed-in joiner reloading the sign-in
            # page was sent to _portal_home_for() - the staff portal. The gate in
            # `auth.lock_to_the_joining_page` would turn that into a redirect
            # loop through a refusal screen; answering here is the honest fix.
            frappe.local.flags.redirect_location = JOINING_PAGE
        elif desk_roles.intersection(roles):
            frappe.local.flags.redirect_location = "/app"
        else:
            frappe.local.flags.redirect_location = _portal_home_for(frappe.session.user)
        raise frappe.Redirect

    context.no_cache   = 1
    context.no_header  = 1
    context.no_sidebar = 1
    # Branding server side, so brand_color.html paints the tenant's colour
    # before first paint. It used to arrive from get_tenant_config() after the
    # page had already drawn, so everybody saw a flash of the default purple
    # and then the real brand - on the sign-in page, which is the first thing
    # a customer's staff ever see.
    context.update(get_branding())
    # Set by JavaScript from the tenant config; a hardcoded brand here
    # flashed the wrong name before that ran.
    context.title      = "Sign In"
