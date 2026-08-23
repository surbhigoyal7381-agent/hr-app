"""Alvoraa subscription plans — the single source of truth.

Everything Frappe HR does is an Alvoraa HR feature. Everything ERPNext does is
available only on the Custom plan. See MODULE_ACCESS_STRATEGY.md.

Before this file the plan definition existed in THREE places: `_preset_map` twice
in tenant_api.py and `MODULE_PRESETS` in the admin page's JavaScript. Three copies
of a pricing decision is three chances to disagree.

How a feature is switched off, and why it takes more than one mechanism:

    module_defs   hide it from the Frappe desk (a Module Profile blocks these).
                  UI ONLY - blocking Payroll removes the sidebar entry but does
                  NOT stop /api/resource/Salary Slip.
    roles         the actual boundary. Withhold these and the server refuses.
    app           our own apps only; if it is not installed the doctypes do not
                  exist. The strongest gate, but unavailable for anything inside
                  hrms or erpnext.

Two facts from the running site constrain this:

  * Recruitment has NO Module Def of its own - Job Opening, Job Applicant and
    Interview all live in the `HR` module - so it can only be gated by roles.
    Blocking a module would take Core HR with it.
  * Frappe HR DEPENDS on ERPNext: payroll posts Journal Entries, expenses link
    Supplier and Bank Account, payroll reads Timesheet. ERPNext can never be
    uninstalled on any plan, so it is hidden, never removed.
"""

import frappe

# ── Alvoraa HR features ──────────────────────────────────────────────────────
# `required` features cannot be switched off on any plan.

FEATURES = {
    "portal": {
        "desc": "Self-service app for every employee",
        "icon": "📱",
        "label": "Employee Portal",
        "required": True,
        "app": "alvoraa_portal",
    },
    "leaves": {
        "desc": "Applications, allocations, policies, encashment",
        "icon": "🌴",
        "label": "Leaves",
        "required": True,
        "workspaces": ["Leaves"],
    },
    "attendance": {
        "desc": "Shifts, check-ins, regularisation",
        "icon": "🕑",
        "label": "Shift & Attendance",
        "required": True,
        "workspaces": ["Shift & Attendance"],
    },
    "expenses": {
        "desc": "Expense claims, advances, travel",
        "icon": "🧾",
        "label": "Expenses",
        "required": True,
        "workspaces": ["Expenses"],
    },
    "hr_setup": {
        "desc": "Holiday lists, HR policy, settings",
        "icon": "⚙️",
        "label": "HR Setup",
        "required": True,
        "workspaces": ["HR Setup"],
    },
    "tenure": {
        "desc": "Onboarding, transfers, promotions, exit",
        "icon": "📈",
        "label": "Onboarding & Exit",
        "workspaces": ["Tenure"],
    },
    "recruitment": {
        "desc": "Job openings, applicants, interviews, offers",
        "icon": "🎯",
        # No Module Def of its own - roles are the only lever here.
        "label": "Recruitment",
        "workspaces": ["Recruitment"],
        "roles": ["Interviewer"],
    },
    "payroll": {
        "desc": "Salary structures, slips, payment entries",
        "icon": "💰",
        "label": "Payroll",
        "module_defs": ["Payroll"],
        "workspaces": ["Payroll"],
    },
    "tax_benefits": {
        "desc": "Tax slabs, exemptions, benefit claims",
        "icon": "📋",
        "label": "Tax & Benefits",
        "workspaces": ["Tax & Benefits"],
    },
    "performance": {
        "desc": "Appraisal cycles, calibration, scorecards",
        "icon": "⭐",
        # One sellable feature: Frappe HR's Performance workspace AND our
        # 37-doctype Performance Management module are sold together.
        "label": "Performance & Appraisals",
        "module_defs": ["Performance Management"],
        "workspaces": ["Performance"],
    },
    "goals": {
        "desc": "Objectives, KPIs, cascade, evidence",
        "icon": "🏁",
        "label": "Goals & KPIs",
        "app": "alvoraa_goals",
        "module_defs": ["Alvoraa Goals"],
    },
    "analytics": {
        "desc": "Dashboards and workforce reports",
        "icon": "📊",
        "label": "Analytics",
    },
    "vendor": {
        "desc": "Vendor portal, driver app, orders",
        "icon": "🚚",
        "label": "Vendor & Driver Portal",
        "app": "alvoraa_portal",
    },
}

# ── Plans ────────────────────────────────────────────────────────────────────
# Starter  - employee self-service
# Business - running an HR department: hiring, lifecycle, payroll
# Enterprise - managing performance: appraisals, goals, analytics, vendor
# Custom   - Enterprise plus individually chosen ERPNext modules

_STARTER = ["portal", "leaves", "attendance", "expenses", "hr_setup"]
_BUSINESS = _STARTER + ["tenure", "recruitment", "payroll", "tax_benefits"]
_ENTERPRISE = _BUSINESS + ["performance", "goals", "analytics", "vendor"]

PLANS = {
    "starter": _STARTER,
    "business": _BUSINESS,
    "enterprise": _ENTERPRISE,
    # Custom carries every Alvoraa HR feature; the ERPNext modules it adds are
    # chosen per tenant and stored separately in `erpnext_modules`.
    "custom": _ENTERPRISE,
}

# ── ERPNext ──────────────────────────────────────────────────────────────────
# Sellable on the Custom plan, picked individually.
ERPNEXT_SELLABLE = [
    "Accounts", "Assets", "Buying", "CRM", "Maintenance", "Manufacturing",
    "Projects", "Quality Management", "Selling", "Stock", "Support",
]

# Plumbing Frappe HR needs. Always installed, always hidden, never sold.
ERPNEXT_INFRASTRUCTURE = [
    "Bulk Transaction", "Communication", "EDI", "ERPNext Integrations",
    "Portal", "Regional", "Setup", "Subcontracting", "Telephony", "Utilities",
]

REQUIRED = [k for k, v in FEATURES.items() if v.get("required")]


def plan_features(plan):
    """Feature keys included in a plan. Unknown plan -> enterprise.

    Unknown means a tenant provisioned before this file existed, or a typo. The
    safe direction is to grant MORE, never to lock a paying customer out of
    something they had yesterday.
    """
    return list(PLANS.get((plan or "").lower(), PLANS["enterprise"]))


def enabled_features(conf=None):
    """Features enabled for the current site.

    Reads the site's own config, which a tenant cannot edit. A site with no
    `features` recorded gets everything - that covers every tenant provisioned
    before this existed, and a missing key must never lock anyone out.
    """
    conf = conf if conf is not None else frappe.conf
    feats = conf.get("features")
    # `is not None`, not truthiness: an explicitly EMPTY list means "nothing
    # beyond the required features", which is a real state a downgrade can
    # produce. Treating [] as "unset" would silently grant the full product.
    if feats is not None:
        return list(feats) + [f for f in REQUIRED if f not in feats]
    plan = conf.get("subscription_plan")
    if plan:
        return plan_features(plan)
    return list(FEATURES)


def has_feature(name, conf=None):
    """True when this site is entitled to `name`. Required features always are."""
    if FEATURES.get(name, {}).get("required"):
        return True
    return name in enabled_features(conf)


def blocked_module_defs(features):
    """Module Defs to block in the desk for a site with these features.

    ERPNext is always blocked here - Custom re-enables its chosen modules
    separately, because those are picked per tenant rather than by plan.
    """
    blocked = []
    for key, spec in FEATURES.items():
        if key not in features:
            blocked.extend(spec.get("module_defs", []))
    blocked.extend(ERPNEXT_SELLABLE)
    blocked.extend(ERPNEXT_INFRASTRUCTURE)
    return sorted(set(blocked))


def withheld_roles(features):
    """Roles a site must NOT grant, given its features. This is the real gate."""
    roles = []
    for key, spec in FEATURES.items():
        if key not in features:
            roles.extend(spec.get("roles", []))
    return sorted(set(roles))


def required_apps(features):
    """Our apps that must be installed for these features."""
    apps = {"alvoraa_portal"}          # the portal is on every plan
    for key in features:
        app = FEATURES.get(key, {}).get("app")
        if app:
            apps.add(app)
    return sorted(apps)


@frappe.whitelist()
def get_plan_catalogue():
    """Plans and features, for the admin console.

    Exists so the admin page stops carrying its own copy of the plan definition.
    """
    # An ordered LIST, not a dict: the admin page renders these as a checklist and
    # the order is part of the product - required features first, then the ladder.
    return {
        "features": [
            {
                "id": k,
                "label": v["label"],
                "desc": v.get("desc", ""),
                "icon": v.get("icon", ""),
                "required": bool(v.get("required")),
            }
            for k, v in FEATURES.items()
        ],
        "plans": {k: list(v) for k, v in PLANS.items()},
        "erpnext_sellable": list(ERPNEXT_SELLABLE),
    }
