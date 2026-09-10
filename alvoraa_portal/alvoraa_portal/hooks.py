app_name = "alvoraa_portal"
app_title = "Alvoraa Portal"
app_publisher = "AllAboutHR"
app_description = "Multi-brand vendor portal with order tracking and delivery management"
app_email = "ops@gracedrinks.in"
app_license = "MIT"
required_apps = ["frappe/erpnext"]

# ── Post-login redirect: portal users → their portal; admins → /app ───────
on_login = "alvoraa_portal.auth.on_login"

# ── Redirect /login to the branded login page ─────────────────────────────
website_redirects = [
    # Was r"^/login$", which NEVER matched: Frappe strips slashes off `source`
    # and compares against a path with no leading slash, so an anchored regex
    # cannot match (see the note on /hrms-home below). The effect was that
    # /login quietly served Frappe's own unbranded login page instead of ours.
    {"source": "/login", "target": "/alvoraa-login"},

    # The control plane was renamed from kinexus-* to alvoraa-*. These keep
    # existing bookmarks and any live session working.
    {"source": "/kinexus-login", "target": "/alvoraa-login"},
    {"source": "/kinexus-admin", "target": "/alvoraa-admin"},
    # /hrms-home was retired — its role is now covered by /hrms-employee.
    # Kept as a redirect so existing bookmarks and live sessions don't 404.
    # NOTE: Frappe strips slashes off `source` and matches it against a path with
    # no leading slash, so an "^/…$"-anchored source never matches. Keep it plain.
    {"source": "/hrms-home", "target": "/hrms-employee"},
]

# ── Portal route rules ────────────────────────────────────────────────────
website_route_rules = [
    {"from_route": "/vendor-portal",   "to_route": "vendor-portal"},
    {"from_route": "/driver-portal",   "to_route": "driver-portal"},
    {"from_route": "/hrms-employee",   "to_route": "hrms-employee"},
    {"from_route": "/goals-portal",    "to_route": "goals-portal"},
    {"from_route": "/alvoraa-login",   "to_route": "alvoraa-login"},
    {"from_route": "/alvoraa-admin",   "to_route": "alvoraa-admin"},
]

# ── Doctype event hooks ────────────────────────────────────────────────────
# Desk-side JavaScript.
#
# One job: make the "Switch to Employee Portal" item in the sidebar menu work.
# Frappe v16 renders Navbar Settings items but never gives them a url or an
# onClick, so the click throws and nothing happens. See the file for the detail.
app_include_js = [
    "/assets/alvoraa_portal/js/portal_switch.js",
]

doc_events = {
    # ── Objectives must sit under a Key Result Area, when HR requires it ───
    # Enforced on the document, not only in the portal form: the rule is about
    # what the organisation accepts, so it has to hold for the desk, the API and
    # any import as well.
    "Individual Goal": {
        "validate": "alvoraa_portal.kra_api.validate_goal_kra",
    },

    # ── An attendance correction must report its real state ───────────────
    # Submitting an Attendance Request IS approving it - the submit is what
    # writes the corrected Attendance row. So a request decided from the Desk
    # has to stop saying "Waiting" to the person who raised it. Hung off the
    # document, not the portal endpoint, because the Desk is the other half of
    # where these get decided.
    "Attendance Request": {
        "on_submit": "alvoraa_portal.attendance_correction.on_submit",
        "on_cancel": "alvoraa_portal.attendance_correction.on_cancel",
    },

    # ── Portal context cache invalidation ─────────────────────────────────
    # Clear per-user portal_ctx_{user} cache when role or employee record changes
    "Employee": {
        "on_update": "alvoraa_portal.hr_api.invalidate_portal_context_cache",
        "on_trash":  "alvoraa_portal.hr_api.invalidate_portal_context_cache",
    },
    # ── Module access follows the plan, for the whole life of the tenant ──
    # A plan is chosen once; users arrive and change roles for years afterwards.
    # Without these the gate would apply only to whoever existed on sync day.
    #
    # Both hang off USER, never off Has Role. Editing roles in the user form does
    # not create or delete a Has Role document - Frappe deletes the removed rows
    # with one SQL statement and writes the rest with db_update() - so hooks on
    # that child doctype look correct and never fire.
    "User": {
        "after_insert": "alvoraa_portal.module_access.apply_on_user_insert",
        "on_update":    ["alvoraa_portal.hr_api.invalidate_portal_context_cache",
                         "alvoraa_portal.module_access.apply_on_user_update"],
    },
    # ── Global features cache invalidation ───────────────────────────────
    # Clear portal_features_global when HR configuration changes
    "Shift Type": {
        "after_insert": "alvoraa_portal.hr_api.invalidate_features_cache",
        "on_update":    "alvoraa_portal.hr_api.invalidate_features_cache",
        "on_trash":     "alvoraa_portal.hr_api.invalidate_features_cache",
    },
    "Leave Type": {
        "after_insert": "alvoraa_portal.hr_api.invalidate_features_cache",
        "on_update":    "alvoraa_portal.hr_api.invalidate_features_cache",
        "on_trash":     "alvoraa_portal.hr_api.invalidate_features_cache",
    },
    # Vendor Order: is_submittable removed; on_update covers all lifecycle events
    "Vendor Order": {
        "validate":  "alvoraa_portal.controllers.vendor_order.validate",
        "on_update": "alvoraa_portal.controllers.vendor_order.on_update",
    },
    "Order Rating": {
        "validate":      "alvoraa_portal.controllers.rating.validate",
        "before_insert": "alvoraa_portal.controllers.rating.before_insert",
        "after_insert":  "alvoraa_portal.controllers.rating.after_insert",
    },
    "Delivery Assignment": {
        "after_insert": "alvoraa_portal.controllers.delivery_assignment.after_insert",
        "on_update":    "alvoraa_portal.controllers.delivery_assignment.on_update",
    },
    "Delivery Partner": {
        "validate": "alvoraa_portal.controllers.delivery_partner.validate",
    },
    "Delivery Order": {
        "before_save": "alvoraa_portal.controllers.delivery_order.before_save",
        "on_update":   "alvoraa_portal.controllers.delivery_order.on_update",
    },
    "Delivery Feedback": {
        "validate":     "alvoraa_portal.controllers.delivery_feedback.validate",
        "after_insert": "alvoraa_portal.controllers.delivery_feedback.after_insert",
    },
    "Vehicle Maintenance Compliance": {
        "before_save": "alvoraa_portal.controllers.vehicle_compliance.before_save",
    },
    "Delivery Performance Scorecard": {
        "before_save": "alvoraa_portal.controllers.scorecard.before_save",
    },
}

scheduler_events = {
    "all": [
        "alvoraa_portal.scheduled_jobs.update_delivery_tracking",
    ],
    "hourly": [
        "alvoraa_portal.scheduled_jobs.calculate_driver_ratings",
    ],
    "daily": [
        "alvoraa_portal.scheduled_jobs.send_arrival_notifications",
        "alvoraa_portal.scheduled_jobs.check_compliance_alerts",
        # Pulls each tenant's error counts and scheduler state up to the control
        # plane, so a broken customer is visible before they telephone. Silent on
        # a tenant site. Titles and counts only, never tracebacks - health.py
        # explains why that line matters.
        "alvoraa_portal.health.collect_scheduled",
    ],
    "monthly": [
        "alvoraa_portal.scheduled_jobs.generate_monthly_scorecards",
        # Counts every tenant's employees and pack users for the month just
        # ended. Returns silently on a tenant site - only the control plane has
        # anything to count. See usage.py.
        "alvoraa_portal.usage.collect_scheduled",
    ],
}


# ── Attendance corrections: the field's own option list, and the review fields
#
# after_migrate rather than the `baseline` seeder: baseline seeds NEW tenants
# only, so every site already live would never have received these - including
# the one the missing "forgot to punch in" reason was reported on. Both calls
# are idempotent.
after_migrate = [
    "alvoraa_portal.attendance_correction.after_migrate",
]

# And on a fresh install, which never runs a migrate. Without this a brand new
# tenant has no review columns at all, and every correction fails on "Unknown
# column alvoraa_review_status". CI is what found it - it builds its site with
# `bench install-app` and nothing else.
after_install = [
    "alvoraa_portal.attendance_correction.after_migrate",
]
