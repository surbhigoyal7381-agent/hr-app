import frappe
from frappe import _

# Roles that are allowed to reach the Frappe desk (/app) when the account is not
# tied to an Employee record — i.e. pure platform operators, not staff.
_DESK_ROLES = frozenset({
    "System Manager", "Administrator",
})


def on_login(login_manager=None):
    """Frappe hook — fires after every successful login.

    Anyone with an Employee record lands in the portal, HR and managers
    included: the portal now covers goal setting, KPI assignment, appraisal
    generation and manager scoring, so staff have no reason to see the desk.
    A tenant's HR admin usually also holds System Manager, so seniority alone
    must not route someone to /app — only the absence of an Employee record does.
    """
    user = frappe.session.user
    if not user or user == "Guest":
        return

    if user != "Administrator" and frappe.db.exists("Employee", {"user_id": user}):
        frappe.local.response["home_page"] = _portal_home_for(user)
        return

    roles = set(frappe.get_roles(user))
    if _DESK_ROLES.intersection(roles):
        return  # Platform operator — let Frappe's default home_page logic apply

    frappe.local.response["home_page"] = _portal_home_for(user)


def _portal_home_for(user):
    """Return the correct portal URL for a non-admin user."""
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

    # Same rule as on_login: staff go to the portal regardless of seniority.
    if user != "Administrator" and frappe.db.exists("Employee", {"user_id": user}):
        return {"url": _portal_home_for(user)}

    roles = set(frappe.get_roles(user))
    if _DESK_ROLES.intersection(roles):
        return {"url": "/app", "role": "admin"}

    return {"url": _portal_home_for(user)}
