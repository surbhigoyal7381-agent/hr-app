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
        "module_defs": ["Alvoraa Portal"],
    },
    "leaves": {
        "desc": "Applications, allocations, policies, encashment",
        "icon": "🌴",
        "label": "Leaves",
        "required": True,
        "workspaces": ["Leaves"],
        "module_defs": ["HR"],
    },
    "attendance": {
        "desc": "Shifts, check-ins, regularisation",
        "icon": "🕑",
        "label": "Shift & Attendance",
        "required": True,
        "workspaces": ["Shift & Attendance"],
        "module_defs": ["HR"],
    },
    "expenses": {
        "desc": "Expense claims, advances, travel",
        "icon": "🧾",
        "label": "Expenses",
        "required": True,
        "workspaces": ["Expenses"],
        "module_defs": ["HR"],
    },
    "hr_setup": {
        "desc": "Holiday lists, HR policy, settings",
        "icon": "⚙️",
        "label": "HR Setup",
        "required": True,
        "workspaces": ["HR Setup"],
        "module_defs": ["HR"],
    },
    "tenure": {
        "desc": "Onboarding, transfers, promotions, exit",
        "icon": "📈",
        "label": "Onboarding & Exit",
        "workspaces": ["Tenure"],
        "module_defs": ["HR"],
    },
    "recruitment": {
        "desc": "Job openings, applicants, interviews, offers",
        "icon": "🎯",
        # No Module Def of its own - roles are the only lever here.
        "label": "Recruitment",
        "workspaces": ["Recruitment"],
        "roles": ["Interviewer"],
        "module_defs": ["HR"],
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
        "module_defs": ["Payroll"],
    },
    "performance": {
        "desc": "Appraisal cycles, calibration, scorecards",
        "icon": "⭐",
        # One sellable feature: Frappe HR's Performance workspace AND our
        # 37-doctype Performance Management module are sold together.
        "label": "Performance & Appraisals",
        "module_defs": ["Performance Management", "HR"],
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
        "module_defs": ["Alvoraa Portal"],
    },
    "vendor": {
        "desc": "Vendor portal, driver app, orders",
        "icon": "🚚",
        "label": "Vendor & Driver Portal",
        "app": "alvoraa_portal",
        "module_defs": ["Alvoraa Portal"],
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


def sold_and_unsold_workspaces(features):
    """(show, hide) — desk workspaces for a site with these features.

    Module blocking cannot do this job. Frappe HR puts Leaves, Expenses, HR
    Setup, Recruitment, Tenure, Performance and Shift & Attendance ALL inside
    one module called `HR`, so blocking that module hides the features a tenant
    bought alongside the ones it did not. Payroll and Tax & Benefits share
    `Payroll` the same way.

    Frappe hides a public workspace from everyone but a Workspace Manager when
    `is_hidden` is set, and that flag is per WORKSPACE - which is exactly the
    granularity the feature list needs.

    Both lists are returned, not just the hidden one: an upgrade has to put
    workspaces back, and a sync that only ever hides would make every plan
    change one-way.
    """
    features = set(features)
    show, hide = [], []
    for key, spec in FEATURES.items():
        for ws in spec.get("workspaces") or []:
            (show if (key in features or spec.get("required")) else hide).append(ws)
    # A workspace sold under ANY enabled feature stays visible, whatever else
    # claims it. Nothing shares one today; relying on that would be fragile.
    hide = [w for w in hide if w not in show]
    return sorted(set(show)), sorted(set(hide))


def blocked_module_defs_for_hr(features):
    """Block list for someone who works IN the desk - an HR Manager.

    Same as everyone else, minus the desk shell. They still lose Payroll,
    Accounts, Integrations and anything else the plan does not include; they just
    keep the screen those things would appear on.
    """
    return [m for m in blocked_module_defs(features) if m not in DESK_SHELL]


def allowed_module_defs(features):
    """Modules a site with these features may see. The allow-list.

    Everything else is blocked, which is the point: a module that appears in a
    future ERPNext release, or arrives with a third-party app, is not something
    the tenant bought, so it is denied until somebody sells it.

    Derived entirely from the registry: each feature names the module it lives in.

    DESK_SHELL is deliberately NOT here. Core and Desk stay hidden from ordinary
    users - that was a decision, not an oversight - and are given back only to
    people who work IN the desk, by blocked_module_defs_for_hr(). Adding them
    here would quietly reverse it for every employee.
    """
    features = set(features)
    allowed = set()

    for key, spec in FEATURES.items():
        if key in features:
            allowed.update(spec.get("module_defs") or [])

    for key, spec in ERPNEXT_FEATURES.items():
        if key in features:
            allowed.update(spec["module_defs"])

    return sorted(allowed)


def blocked_module_defs(features, existing=None):
    """Modules to block for a site with these features.

    DENY BY DEFAULT. This used to build an explicit blocked list - unsold
    features, unticked ERPNext modules, ERPNext plumbing, Frappe clutter - which
    meant anything nobody had thought of was allowed. A module from a future
    ERPNext release, or from a third-party app somebody installs, was visible to
    every tenant the day it appeared, because it was on nobody's list.

    Now the ALLOW-list is the definition and everything else is blocked. New
    modules are denied by default and stay denied until a feature claims them.

    `existing` is injected so this stays testable without a database, and so a
    caller that has already read the module list does not read it twice.
    """
    allowed = set(allowed_module_defs(features))

    if existing is None:
        existing = [m.name for m in frappe.get_all("Module Def", fields=["name"])]

    blocked = set(existing) - allowed

    # Belt and braces for a site whose Module Def table is unreadable or empty:
    # the plumbing and clutter that must never be visible, whatever else happens.
    blocked.update(m for m in ERPNEXT_INFRASTRUCTURE if m not in allowed)
    blocked.update(m for m in FRAPPE_HIDDEN if m not in allowed)

    return sorted(blocked - set(FRAPPE_ALWAYS_VISIBLE))


def blocked_doctypes(features, existing=None):
    """Doctypes a site with these features must not expose.

    DERIVED, never listed. The modules come from blocked_module_defs(), which is
    deny-by-default, and the doctypes come from whatever actually lives in those
    modules on this site. So a doctype from a future ERPNext release, or from a
    third-party app, is denied the day it appears - it belongs to a module nobody
    sold.

    `existing` is injected by the caller so this stays a pure function and can be
    tested without a database.
    """
    if existing is None:
        existing = [
            (d.name, d.module)
            for d in frappe.get_all(
                "DocType",
                filters={"istable": 0, "custom": 0, "issingle": 0},
                fields=["name", "module"],
            )
        ]
    modules = sorted({m for _n, m in existing if m})
    blocked = set(blocked_module_defs(features, existing=modules))
    return sorted({name for name, module in existing if module in blocked})


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
