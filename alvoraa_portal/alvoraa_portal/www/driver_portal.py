from alvoraa_portal.subscription import has_feature
from alvoraa_portal.tenant_context import get_branding

import frappe


def get_context(context):
    # A tenant that has not bought the vendor and driver portal does not have
    # this page either (slice 016). Without this the page rendered and then
    # every call behind it failed with "not included in your plan", which is a
    # broken screen advertising a product they were never sold. A 404 is the
    # honest answer.
    if not has_feature("vendor"):
        raise frappe.DoesNotExistError

    if frappe.session.user == "Guest":
        frappe.flags.redirect_location = "/alvoraa-login?redirect-to=/driver-portal"
        raise frappe.Redirect
    context.no_cache  = 1
    context.update(get_branding())
