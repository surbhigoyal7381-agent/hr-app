from alvoraa_portal.tenant_context import get_branding

import frappe
from frappe.sessions import get_csrf_token
from frappe.utils import get_build_version


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
    # OPS-31 / OPS-34. The frame's stylesheets and the portal script are static
    # files under /assets/, so a browser is told to keep them. This stamp is what
    # makes it safe to do that: get_build_version() is the modified time of
    # sites/assets/assets.json, which every deploy rewrites last (ALV-112,
    # scripts/refresh_bench_files.sh). New release, new address, so no phone can
    # keep last release's code. It is one os.stat and it carries no personal data.
    context.asset_version = get_build_version()
    context.update(get_branding())
