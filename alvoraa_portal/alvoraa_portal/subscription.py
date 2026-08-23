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
_BUSINESS = [*_STARTER, "tenure", "recruitment", "payroll", "tax_benefits"]
_ENTERPRISE = [*_BUSINESS, "performance", "goals", "analytics", "vendor"]

PLANS = {
    "starter": _STARTER,
    "business": _BUSINESS,
    "enterprise": _ENTERPRISE,
    # Custom carries every Alvoraa HR feature; the ERPNext modules it adds are
    # chosen per tenant and stored separately in `erpnext_modules`.
    "custom": _ENTERPRISE,
}

# ── ERPNext ──────────────────────────────────────────────────────────────────
# Selectable per tenant, alongside the Alvoraa HR features above. The control
# plane admin ticks whatever a tenant should have; the plan NAME is then derived
# from the selection (tenant_api), so choosing any ERPNext module makes the
# tenant "custom" automatically. There is no separate ERPNext-only flow.
ERPNEXT_SELLABLE = [
    "Accounts", "Assets", "Buying", "CRM", "Maintenance", "Manufacturing",
    "Projects", "Quality Management", "Selling", "Stock", "Support",
]

_ERP_DESC = {
    "Accounts": "Ledgers, invoices, payments, financial reports",
    "Assets": "Asset register, depreciation, maintenance",
    "Buying": "Suppliers, purchase orders, receipts",
    "CRM": "Leads, opportunities, customer pipeline",
    "Maintenance": "Schedules, visits, service contracts",
    "Manufacturing": "BOMs, work orders, production planning",
    "Projects": "Projects, tasks, timesheets, costing",
    "Quality Management": "Inspections, non-conformance, procedures",
    "Selling": "Customers, quotations, sales orders",
    "Stock": "Inventory, warehouses, stock movements",
    "Support": "Issues, tickets, service levels",
}


def erp_feature_id(module_def):
    """Selection id for an ERPNext module. `Quality Management` -> `erp_quality_management`."""
    return "erp_" + module_def.lower().replace(" ", "_")


# The same shape as FEATURES, so the admin renders one catalogue rather than two.
ERPNEXT_FEATURES = {
    erp_feature_id(m): {
        "label": m,
        "desc": _ERP_DESC.get(m, ""),
        "icon": "🧰",
        "module_defs": [m],
        "erpnext": True,
    }
    for m in ERPNEXT_SELLABLE
}

# ── Frappe's own framework modules ───────────────────────────────────────────
# Clutter for an HR tenant: Website, Integrations, Automation and the rest are
# not part of the product. Hidden from ordinary users, but NOT from the tenant's
# own administrators, who legitimately need Integrations to connect other systems.
FRAPPE_HIDDEN = [
    "Automation", "Contacts", "Custom", "Email", "Geo",
    "Integrations", "Printing", "Website", "Workflow",
    # Core and Desk are the desk's own machinery - user management, settings,
    # the module list itself. An ordinary employee has no business there; their
    # interface is the portal. Hidden from them too, by decision 2026-08-23.
    #
    # They are NOT hidden from the people who need them:
    #   * the tenant's own administrators - exempted in module_access.py
    #   * the control plane - sync_site refuses to run there at all
    "Core", "Desk",
]

# Kept as an explicit, empty statement of intent. Nothing is unconditionally
# visible any more: what an ordinary user sees is decided entirely by the plan.
FRAPPE_ALWAYS_VISIBLE = []

# The desk's own shell. Hidden from employees, but anyone who is expected to WORK
# in the desk needs it - an HR Manager sent to /app/hr with these blocked lands on
# a crippled screen. Kept for the HR variant of the profile.
DESK_SHELL = ["Core", "Desk"]

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


def blocked_module_defs_for_hr(features):
    """Block list for someone who works IN the desk - an HR Manager.

    Same as everyone else, minus the desk shell. They still lose Payroll,
    Accounts, Integrations and anything else the plan does not include; they just
    keep the screen those things would appear on.
    """
    return [m for m in blocked_module_defs(features) if m not in DESK_SHELL]


def blocked_module_defs(features):
    """Module Defs to block in the desk for a site with these features.

    ERPNext is always blocked here - Custom re-enables its chosen modules
    separately, because those are picked per tenant rather than by plan.
    """
    features = set(features)
    blocked = []

    # Alvoraa HR features that were not selected
    for key, spec in FEATURES.items():
        if key not in features:
            blocked.extend(spec.get("module_defs", []))

    # ERPNext modules the admin did not tick for this tenant
    for key, spec in ERPNEXT_FEATURES.items():
        if key not in features:
            blocked.extend(spec["module_defs"])

    # Plumbing Frappe HR needs. Always installed, always hidden, never sold.
    blocked.extend(ERPNEXT_INFRASTRUCTURE)

    # Frappe's own framework modules - clutter for a tenant.
    blocked.extend(FRAPPE_HIDDEN)

    # Core and Desk are the desk itself; blocking them breaks navigation.
    return sorted(set(blocked) - set(FRAPPE_ALWAYS_VISIBLE))


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
    def _row(k, v):
        return {
            "id": k,
            "label": v["label"],
            "desc": v.get("desc", ""),
            "icon": v.get("icon", ""),
            "required": bool(v.get("required")),
            "erpnext": bool(v.get("erpnext")),
        }

    # Two groups, one catalogue. The admin ticks freely across both; the plan
    # NAME is derived from what ends up ticked, so any ERPNext choice makes the
    # tenant custom without the admin having to pick a plan first.
    return {
        "groups": [
            {"key": "alvoraa_hr", "label": "Alvoraa HR",
             "features": [_row(k, v) for k, v in FEATURES.items()]},
            {"key": "erpnext", "label": "ERPNext",
             "features": [_row(k, v) for k, v in ERPNEXT_FEATURES.items()]},
        ],
        # Flat list too - the admin page renders one grid and the plan presets
        # are matched against ids from both groups.
        "features": [_row(k, v) for k, v in FEATURES.items()]
                    + [_row(k, v) for k, v in ERPNEXT_FEATURES.items()],
        "plans": {k: list(v) for k, v in PLANS.items()},
    }
