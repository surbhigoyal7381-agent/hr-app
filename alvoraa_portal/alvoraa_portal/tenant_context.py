"""Per-tenant branding, resolved from the current site only.

Portal pages used to build a path to site_config.json out of the raw HTTP Host
header::

    _host = (frappe.request.host or "").split(":")[0]
    _path = os.path.join("/home/frappe/frappe-bench/sites", _host, "site_config.json")

That reads another tenant's config file whenever the header and the resolved
site disagree, and a crafted Host ("../..") walks out of the sites directory
entirely. `frappe.conf` is already the *current* site's config — the site Frappe
actually resolved and connected to — so there is nothing to look up by hand.
"""

import frappe

from alvoraa_portal import brand

DEFAULTS = {
    "primary_color": "#1a7f5a",
    "accent_color": "#f59e0b",
    "tenant_name": "Alvoraa",
    "tenant_logo_url": "",
    "support_email": "",
}


def get_branding():
    """Branding for the site serving this request. Never touches other sites.

    Two of these keys are derived, not read: `brand_mark_url` and `brand_logo_url`
    apply the product's one branding rule -

        a tenant's own logo if it has one, otherwise the Alvoraa mark.

    They live here rather than in each page because every branded page already
    calls this function, and `01b-ux-design.md` / `appendix-a-frame.md` FR-18 say
    the redesigned rail will keep calling it too. Putting the rule here means the
    new frame inherits it instead of reinventing it.

    `tenant_logo_url` is left exactly as it was, so anything that wants to know
    "did this tenant set a logo of its own?" can still ask.

    No query. `frappe.conf` is a dict already in memory, and the asset paths are
    constants, so this costs nothing on any request path.
    """
    conf = frappe.conf
    own_logo = conf.get("tenant_logo_url") or DEFAULTS["tenant_logo_url"]
    return {
        "primary_color":   conf.get("primary_color")   or DEFAULTS["primary_color"],
        "accent_color":    conf.get("accent_color")    or DEFAULTS["accent_color"],
        "tenant_name":     conf.get("tenant_name")     or DEFAULTS["tenant_name"],
        "tenant_logo_url": own_logo,
        "support_email":   conf.get("support_email")   or DEFAULTS["support_email"],
        # Small square, for a 32-42 px tile next to the tenant's name.
        "brand_mark_url":  own_logo or brand.MARK,
        # The full lockup, where there is room to read a wordmark.
        #
        # NOTHING RENDERS THIS YET, ON PURPOSE. The Alvoraa half of it is built
        # from placeholder artwork whose wordmark reads ALVORAA, and the chosen
        # spelling is ALVORA. A tenant that set `tenant_logo_url` gets its own
        # logo here and is safe. Before putting this on a screen, check that
        # `alvoraa_portal/brand/alvoraa-logo-master.*` is the real artwork.
        "brand_logo_url":  own_logo or brand.LOGO,
    }
