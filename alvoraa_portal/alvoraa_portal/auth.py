import frappe
from frappe import _

from alvoraa_portal.subscription import has_feature

# Roles that are allowed to reach the Frappe desk (/app) when the account is not
# tied to an Employee record — i.e. pure platform operators, not staff.
_DESK_ROLES = frozenset({
    "System Manager", "Administrator",
})


def home_page_for(user):
    """Where this user belongs when they ask for nothing in particular.

    One rule, used by three doors: the bare address (the
    `get_website_user_home_page` hook, slice 024), the moment of login
    (`on_login`), and the branded login page (`get_portal_redirect`). They used
    to answer only the last two, so typing https://<tenant>/ dropped an
    employee into the desk. Keeping the rule in one function is what stops the
    doors drifting apart again.

    Anyone with an Employee record lands in the portal, HR and managers
    included: the portal now covers goal setting, KPI assignment, appraisal
    generation and manager scoring, so staff have no reason to see the desk.
    A tenant's HR admin usually also holds System Manager, so seniority alone
    must not route someone to /app — only the absence of an Employee record does.

    Returns a path, or None meaning "Frappe, carry on as you would". None is the
    right answer for a platform operator (Frappe sends a System User to the
    desk) and for Guest (Frappe sends them to the login page). Never returning
    a page here is how /app and the sign-in screen keep working.
    """
    if not user or user == "Guest":
        return None
    if user == "Administrator":
        return None

    try:
        if frappe.db.exists("Employee", {"user_id": user}):
            return _portal_home_for(user)

        if _DESK_ROLES.intersection(set(frappe.get_roles(user))):
            return None  # Platform operator — the desk is their workplace

        return _portal_home_for(user)
    except Exception:
        # This runs on the front door of every tenant. A lookup that fails must
        # cost us the redirect, not the site. No user detail in the log line.
        frappe.log_error(title="Landing page lookup failed")
        return None


def on_login(login_manager=None):
    """Frappe hook — fires after every successful login.

    Sets the landing page only when we have an opinion. When `home_page_for`
    returns None the key is left alone, so Frappe's own logic decides — which
    is what a platform operator needs.
    """
    user = frappe.session.user
    if not user or user == "Guest":
        return

    home = home_page_for(user)
    if home:
        frappe.local.response["home_page"] = home


def _portal_home_for(user):
    """Return the correct portal URL for a non-admin user.

    The vendor and driver portals are checked only when the tenant actually has
    the `vendor` feature. Slice 016 made both pages 404 off-plan, so without
    this check a Starter tenant that happens to hold a Vendor User row landed
    that person on a missing page. `/hrms-employee` is always safe: `portal` is
    a required feature, so every tenant has it whatever the plan says.
    """
    if has_feature("vendor"):
        if frappe.db.exists("Vendor User", {"email": user}):
            return "/vendor-portal"
        if frappe.db.exists("Delivery Partner", {"primary_email": user}):
            return "/driver-portal"
    # Default: HRMS self-service portal (covers all employees)
    return "/hrms-employee"


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
        return {"url": "/alvoraa-login"}

    # The same rule as the bare address and as on_login: staff go to the portal
    # regardless of seniority, and no opinion means the desk.
    home = home_page_for(user)
    if home:
        return {"url": home}
    return {"url": "/app", "role": "admin"}
