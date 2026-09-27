"""The Wave 1 preview page, behind two locks (SEC-1, W1D-15, AC-40, AC-74).

`/hrms-employee-next` is where the new frame is looked at before it replaces
`/hrms-employee`. It is a thing built for us, not for customers, so the rule is
not "only the right people may open it" - it is **it does not exist on
production at all**.

Two locks, in this order and never the other way round:

1. **The site flag.** `frappe.conf` must carry `portal_preview`. The local bench
and the dev stack set it; no production config file and no production compose
environment in this repository does, and `test_preview_page_034` reads the
repository to prove it. Without the flag the route is **404 for everyone**,
System Manager included - not 403, because a 403 tells a stranger the page is
there.
2. **The role.** With the flag set, System Manager only. Everybody else signed
in gets 403, and Guest is sent to the login page.

The flag is tested FIRST, on purpose. That makes the role check the second of
two locks rather than the only one, so a mistake in the role check cannot expose
anything on production, where the first lock has already refused.

This is the same shape as `alvoraa_admin.py`, which learned it the hard way: a
role check on its own let a tenant's own System Manager open the Alvoraa console
on a tenant site.
"""

import frappe
from frappe import _
from frappe.sessions import get_csrf_token
from frappe.utils import get_build_version

from alvoraa_portal.tenant_context import get_branding

# Never cached, and never in the sitemap (OPS-12, AC-65). Frappe reads both off
# the page module (frappe 16.33.1, website/page_renderers/template_page.py:22).
no_cache = 1
sitemap = 0


def preview_is_enabled():
    """Is this a site where the preview page exists at all?

    Truthiness, so that an absent key and `portal_preview: 0` behave the same -
    both mean "not a preview site". Named rather than inlined so the test can
    ask the same question the page asks.
    """
    return bool(frappe.conf.get("portal_preview"))


def get_context(context):
    # LOCK 1 - the site. Before anything else, including the login check: on
    # production this page has no existence to reveal.
    if not preview_is_enabled():
        raise frappe.DoesNotExistError

    # Signed in, the same way the real portal page does it.
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/alvoraa-login?redirect-to=/hrms-employee-next"
        raise frappe.Redirect

    # LOCK 2 - the person.
    # The portal's own is_hr would be wrong here: this is not an HR screen, it
    # is an unfinished build of one.
    if "System Manager" not in frappe.get_roles(frappe.session.user):
        frappe.throw("This preview is for Alvora engineers only.", frappe.PermissionError)

    # The real page gives the session its CSRF token before the page is built,
    # because Frappe only mints one when a desk page loads. Without it every open
    # portal tab fails with "Invalid Request" the moment a desk page opens in any
    # tab. The preview needs the same, for the same reason.
    get_csrf_token()

    context.no_cache = 1
    context.no_header = 1
    context.no_sidebar = 1
    context.title = _("Employee portal")
    # OPS-31 / OPS-34. The frame's stylesheet and script are static files under
    # /assets/, so a browser is told to keep them for a month. This stamp is
    # what makes that safe: get_build_version() is the modified time of
    # sites/assets/assets.json, which every deploy rewrites last (ALV-112).
    # New release, new address, so no phone keeps last release's frame. One
    # os.stat, and it carries no personal data.
    context.asset_version = get_build_version()
    context.update(get_branding())
