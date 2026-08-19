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

DEFAULTS = {
    "primary_color": "#1a7f5a",
    "accent_color": "#f59e0b",
    "tenant_name": "Alvoraa",
    "tenant_logo_url": "",
    "support_email": "",
}


def get_branding():
    """Branding for the site serving this request. Never touches other sites."""
    conf = frappe.conf
    return {
        "primary_color":   conf.get("primary_color")   or DEFAULTS["primary_color"],
        "accent_color":    conf.get("accent_color")    or DEFAULTS["accent_color"],
        "tenant_name":     conf.get("tenant_name")     or DEFAULTS["tenant_name"],
        "tenant_logo_url": conf.get("tenant_logo_url") or DEFAULTS["tenant_logo_url"],
        "support_email":   conf.get("support_email")   or DEFAULTS["support_email"],
    }
