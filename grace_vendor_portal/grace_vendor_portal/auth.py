import frappe
from frappe import _

# Roles that are allowed to reach the Frappe desk (/app)
_DESK_ROLES = frozenset({
    "System Manager", "HR Manager", "HR User",
    "Accounts Manager", "Accounts User", "Administrator",
    "Stock Manager", "Stock User",
})


def on_login(login_manager=None):
    """Frappe hook — fires after every successful login.

    Portal users (vendors, drivers, employees) are sent to their portal.
    Desk-role users (admins) are left to reach /app as normal.
    """
    user = frappe.session.user
    if not user or user == "Guest":
        return

    roles = set(frappe.get_roles(user))
    if _DESK_ROLES.intersection(roles):
        return  # Admin — let Frappe default home_page logic apply

    frappe.local.response["home_page"] = _portal_home_for(user)


def _portal_home_for(user):
    """Return the correct portal URL for a non-admin user."""
    if frappe.db.exists("Vendor User", {"email": user}):
        return "/vendor-portal"
    if frappe.db.exists("Delivery Partner", {"primary_email": user}):
        return "/driver-portal"
    # Default: HRMS self-service portal (covers all employees)
    return "/hrms-home"


# ── Tenant branding API ────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def get_tenant_config():
    """Return branding and feature config for the current site.

    Values come from site_config.json, set by provision_tenant.sh.
    All fields have safe defaults so the login page always renders.
    """
    conf = frappe.conf
    return {
        "tenant_name":       conf.get("tenant_name",       "Kinexus HRMS"),
        "logo_url":          conf.get("tenant_logo_url",   ""),
        "primary_color":     conf.get("primary_color",     "#1a7f5a"),
        "accent_color":      conf.get("accent_color",      "#f59e0b"),
        "support_email":     conf.get("support_email",     "support@kinexus.in"),
        "subscription_plan": conf.get("subscription_plan", "starter"),
        "modules_enabled":   conf.get("modules_enabled",   ["hrms", "vendor_portal", "goals"]),
    }


@frappe.whitelist()
def get_portal_redirect():
    """Return the correct portal URL for the currently logged-in user.

    Used by the login page JS after a successful login to decide where
    to send the user without a page round-trip.
    """
    user = frappe.session.user
    if not user or user == "Guest":
        return {"url": "/kinexus-login"}

    roles = set(frappe.get_roles(user))
    if _DESK_ROLES.intersection(roles):
        return {"url": "/app", "role": "admin"}

    url = _portal_home_for(user)
    return {"url": url}
