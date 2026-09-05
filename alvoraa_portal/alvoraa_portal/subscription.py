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

import functools

import frappe
from frappe import _

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

# Not an ERPNext core module, but it lives in this catalogue rather than
# FEATURES for two reasons: `enterprise` is defined as every Alvoraa HR feature
# and this is not one, and it is useless without the ERPNext modules above.
# Putting it in FEATURES made six tests fail on exactly that invariant.
ERPNEXT_FEATURES["india_compliance"] = {
    "desc": "GST returns, e-invoicing, e-way bills, TDS, audit trail",
    "icon": "🇮🇳",
    "label": "Indian Compliance",
    "app": "india_compliance",
    "module_defs": ["GST India", "Income Tax India", "VAT India", "Audit Trail"],
    "workspaces": ["GST India", "Income Tax India"],
    "erpnext": True,
    # Refused without these rather than granted silently - see
    # unmet_requirements(). Every one of its doctypes hangs off Sales Invoice,
    # Purchase Invoice or the Accounts module, so without them the app installs
    # and then every screen is denied by our own access control.
    "requires": ["erp_accounts", "erp_selling", "erp_buying"],
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


def feature_spec(key):
    """A feature's definition, from whichever catalogue holds it.

    FEATURES is the Alvoraa HR product; ERPNEXT_FEATURES is what a tenant can
    add alongside it. Callers asking "what app does this need" or "what does it
    require" should not have to know which side a key lives on - and when
    india_compliance moved between them, every lookup that only checked FEATURES
    silently started returning nothing.
    """
    return FEATURES.get(key) or ERPNEXT_FEATURES.get(key) or {}


def unmet_requirements(selection):
    """Features in `selection` whose prerequisites are missing, as {key: [needed]}.

    Some features cannot stand on their own. india_compliance is the first: all
    25 of its doctypes hang off Sales Invoice, Purchase Invoice or the Accounts
    module, so ticking it without the ERPNext modules that provide them installs
    an app whose every screen is then denied by our own access control. The
    tenant sees a product they paid for and cannot open, and nothing in the UI
    explains why.

    Refused rather than auto-corrected. Quietly switching on Accounts, Selling
    and Buying because a fourth box was ticked would hand a tenant three modules
    they did not buy - a subscription bypass performed by the subscription
    system. The caller is expected to show these names and let a human decide.
    """
    chosen = set(selection or [])
    out = {}
    for key in chosen:
        needs = feature_spec(key).get("requires") or []
        missing = [n for n in needs if n not in chosen]
        if missing:
            out[key] = missing
    return out


def requirement_error(selection):
    """One sentence naming what is missing, or None when the selection is whole."""
    unmet = unmet_requirements(selection)
    if not unmet:
        return None
    parts = []
    for key, missing in sorted(unmet.items()):
        label = feature_spec(key).get("label", key)
        names = ", ".join(
            feature_spec(m).get("label", m)
            for m in missing
        )
        parts.append(f"{label} also needs {names}")
    return "; ".join(parts) + "."


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


def requires_feature(name):
    """Refuse an endpoint the tenant's plan does not include.

    Wave 6 hid the portal's Goals, Analytics and Vendor panels, and hiding was
    all it did - get_hr_analytics() and the eight vendor endpoints stayed
    whitelisted and answered anyone who called them. That is the same mistake
    the desk gates were criticised for: a menu that stops drawing something
    while the door behind it still opens.

    A decorator rather than an `if` in each function, so a new endpoint has to
    opt in deliberately instead of being forgotten. Applied ABOVE
    @frappe.whitelist() so the check runs before the body, not after.

    Required features never refuse: has_feature() short-circuits on them, so a
    misconfigured `features` list cannot lock a tenant out of its own leave
    screen.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if not has_feature(name):
                label = FEATURES.get(name, {}).get("label", name)
                frappe.throw(
                    _("{0} is not included in your plan.").format(label),
                    frappe.PermissionError,
                )
            return fn(*args, **kwargs)

        wrapper.__alvoraa_feature__ = name      # so tests can see the gate
        return wrapper

    return decorator


def linked_dependencies(features, links=None):
    """Doctypes outside the sold modules that the sold ones LINK to.

    Denying by module alone broke Frappe HR, and CI caught it before a customer
    did. ERPNext keeps the most fundamental HR entities in its `Setup` module:

        Employee, Company, Department, Designation, Branch, Holiday List

    Blocking Setup therefore denied `Employee` itself, and an HR Manager could
    not read a leave balance.

    The dependency list is DERIVED, not written down: whatever the sold modules
    link to, they need. 34 doctypes on a real site - Employee and Company among
    them, but also Bank Account, Journal Entry and Cost Center, because payroll
    posts to the ledger. A doctype a future Frappe HR release starts linking to
    is covered the day it appears.

    The trade, stated plainly: this grants READ on a handful of Accounts
    doctypes to every tenant. Payroll cannot work otherwise, and a broken
    product is worse than a slightly permeable one.
    """
    allowed = allowed_module_defs(features)
    if links is None:
        links = frappe.db.sql(
            """select distinct df.options
               from `tabDocField` df join `tabDocType` dt on dt.name = df.parent
               where df.fieldtype in ('Link', 'Table MultiSelect')
                 and df.options is not null and dt.module in %(m)s""",
            {"m": list(allowed) or [""]}, pluck=True)
    return sorted({d for d in (links or []) if d})


def workspace_scoped_doctypes(features, workspace_links=None):
    """Doctypes belonging to an unsold feature that shares a module with a sold one.

    Module-level denial cannot separate Recruitment from Leaves: Job Opening,
    Job Applicant and Interview all live in `HR`, and HR holds features every
    plan includes. So a tenant that never bought Recruitment could still open
    Job Opening by URL, and the desk still drew a Recruitment sidebar - because
    a sidebar is shown when at least one of its items is readable.

    The mapping we need is already in Frappe's own data: each Workspace lists
    the doctypes it contains. A feature names its workspace; the workspace names
    its doctypes. Nothing to write down, and a doctype added to the Recruitment
    workspace by a future Frappe HR release is covered the day it appears.

    Anything a SOLD workspace also lists is kept - Payroll lists Account,
    Currency and Journal Entry, which Leaves and Expenses need too. Overlap
    means shared, and shared means keep.
    """
    show, hide = sold_and_unsold_workspaces(features)

    if workspace_links is None:
        # TWO sources, because Frappe HR uses both and reading one is not enough.
        #
        # `Employee Separation` has no Workspace Link at all - it is referenced
        # only from the Tenure SIDEBAR. Reading links alone left it readable
        # while the rest of Tenure was denied, which is exactly how it was
        # spotted: with the feature switched off, Employee Separation was the
        # one thing still showing.
        #
        # A Workspace Sidebar carries the same name as its workspace, so both
        # sources key the same way.
        workspace_links = []
        for doctype, parent_type in (("Workspace Link", "Workspace"),
                                     ("Workspace Sidebar Item", "Workspace Sidebar")):
            if not frappe.db.table_exists(doctype):
                continue
            try:
                rows = frappe.get_all(
                    doctype,
                    filters={"link_type": "DocType", "parenttype": parent_type},
                    fields=["parent", "link_to"])
            except Exception:
                continue
            workspace_links += [(r.parent, r.link_to) for r in rows if r.link_to]

    sold, unsold = set(), set()
    for ws, dt in workspace_links:
        if ws in show:
            sold.add(dt)
        elif ws in hide:
            unsold.add(dt)

    return sorted(unsold - sold)


def blocked_doctypes(features, existing=None, links=None, module_apps=None,
                     workspace_links=None):
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

    # Never deny a doctype owned by FRAPPE itself.
    #
    # Frappe's own doctypes are framework machinery, not product: Notification
    # Log, File, Comment, ToDo, the whole desk. Deny-by-default swept 140 of
    # them up, and the first thing a real user saw was
    #
    #     Insufficient Permission for Notification Log
    #
    # every time the desk polled its notification bell. Withholding them sells
    # nothing and breaks everything.
    #
    # They are still HIDDEN from the module list by blocked_module_defs - which
    # is the right lever for framework clutter, and always was. Hiding tidies
    # the desk; denying breaks it.
    if module_apps is None:
        module_apps = {
            m.name: m.app_name
            for m in frappe.get_all("Module Def", fields=["name", "app_name"])
        }
    blocked -= {m for m, app in module_apps.items() if app == "frappe"}

    # Whatever the sold modules link to, they need - whichever module holds it.
    needed = set(linked_dependencies(features, links=links))

    # ...with one exception, or the exemption swallows the product. Something in
    # the HR module links to Salary Slip, so a plain dependency rule made Payroll
    # readable on a Starter plan - the exact thing the plan exists to withhold.
    #
    # A module claimed by an UNSOLD Alvoraa feature is never exempted. ERPNext
    # modules still are: Frappe HR posts payroll to Journal Entry and reads Bank
    # Account, and the strategy has always been that ERPNext keeps working
    # underneath while staying out of sight.
    sold = set(allowed_module_defs(features))
    never_exempt = {
        m
        for key, spec in FEATURES.items() if key not in set(features)
        for m in (spec.get("module_defs") or [])
    } - sold
    if never_exempt:
        needed -= {name for name, module in existing if module in never_exempt}

    # Features sharing a module with a sold one cannot be separated above, so
    # take them from the workspace contents instead.
    by_workspace = set(workspace_scoped_doctypes(features, workspace_links))

    # Only OUR product's doctypes, never ERPNext plumbing. The Payroll workspace
    # lists Account, Currency, Cost Center and Journal Entry - things Leaves and
    # Expenses need too. Denying those to withhold Payroll would break the plan
    # the tenant did buy.
    known = {name: module for name, module in existing}
    owning_app = module_apps or {}
    by_workspace = {d for d in by_workspace
                    if owning_app.get(known.get(d)) == "hrms"}

    # An unsold doctype is not rescued by being LINKED from a sold module.
    # Job Applicant lives in `HR` and links to Job Opening, so the dependency
    # exemption was quietly handing Recruitment back to a tenant that never
    # bought it. Belonging to an unsold feature wins.
    needed = needed - by_workspace

    by_module = {name for name, module in existing
                 if module in blocked and name not in needed}

    return sorted(by_module | by_workspace)


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
        app = feature_spec(key).get("app")
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
