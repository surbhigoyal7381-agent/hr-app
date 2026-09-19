from alvoraa_portal.tenant_context import get_branding

import frappe
from frappe.sessions import get_csrf_token


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.flags.redirect_location = "/alvoraa-login?redirect-to=/hrms-employee"
        raise frappe.Redirect
    context.no_cache  = 1
    # Give the login session its CSRF token before the page is built, so the
    # page carries a real one. Frappe only creates the token when a desk page
    # loads. Until then this page carried "None", and the first desk page opened
    # afterwards - in any tab - made every open portal tab fail with
    # "Invalid Request". An existing token is reused, never replaced.
    get_csrf_token()
    context.update(get_branding())
