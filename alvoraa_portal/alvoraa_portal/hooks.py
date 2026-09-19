app_name = "alvoraa_portal"
app_title = "Alvoraa Portal"
app_publisher = "AllAboutHR"
app_description = "Multi-brand vendor portal with order tracking and delivery management"
app_email = "support@alvoraa.co"
app_license = "MIT"
required_apps = ["frappe/erpnext"]

# ── Post-login redirect: portal users → their portal; admins → /app ───────
on_login = "alvoraa_portal.auth.on_login"

# ── The bare address "/" lands where login does (slice 024) ───────────────
# Frappe resolves "/" through get_home_page(), which asks this hook. Without
# it, typing https://<tenant>/ dropped a signed-in employee into the desk,
# and every tenant had to be configured by hand to avoid that. The function
# returns None for a platform operator and for Guest, so /app and the sign-in
# page keep working untouched.
get_website_user_home_page = "alvoraa_portal.auth.home_page_for"

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
    # The field app. Short and typeable, because a driver is given this address
    # verbally or on a slip of paper, not as a link.
    {"from_route": "/checkin",         "to_route": "field-checkin"},
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

# The "Field attendance app" tab on HR Settings (slice 013 step 2): the counts
# beside the switch, the confirm before turning it off or removing a
# designation, and the change history. The rules themselves are on the server
# (field_app_settings.py); this only asks before HR does something that stops
# phones working.
doctype_js = {
    "HR Settings": "public/js/hr_settings_field_app.js",
}

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
        # Nobody approves their own correction - desk, REST or import (slice 010, SEC-9)
        "before_submit": "hrms.alvoraa_hr_core.access.refuse_own_submit",
    },

    # ── Portal context cache invalidation ─────────────────────────────────
    # Clear per-user portal_ctx_{user} cache when role or employee record changes
    # ── A punch, and the face on it, is not public inside the company ─────
    # Frappe HR ships no row filter for Employee Checkin and the Employee role
    # holds plain read on it, so without these two the only thing keeping one
    # employee out of another's photos is whether ERPNext happened to create a
    # User Permission row. The query condition filters lists; has_permission
    # guards opening one record by name. Both are needed - a list filter alone
    # leaves /app/employee-checkin/<name> open to anyone who guesses a name.
    "Employee Checkin": {
        "onload": "alvoraa_portal.field_app_access.log_photo_view",
    },

    "Employee": {
        # Two handlers, one event. The second stops a field phone working the
        # day its owner leaves: the punch endpoint already refuses a non-Active
        # employee, but a status that comes back to Active - a rehire, a
        # correction, a script - would otherwise re-arm a device secret that
        # somebody took with them.
        "on_update": [
            "alvoraa_portal.hr_api.invalidate_portal_context_cache",
            "alvoraa_portal.field_checkin.block_devices_for_leaver",
        ],
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
    # ── Nobody approves their own leave ───────────────────────────────────
    # Submitting a Leave Application is what approves or rejects it. Hung off
    # the document so the desk and REST API get the same rule as the portal,
    # even where HR Settings allows self-approval (slice 010, SEC-9).
    "Leave Application": {
        "before_submit": "hrms.alvoraa_hr_core.access.refuse_own_submit",
    },
    # ── The field app's switches on HR Settings (slice 013 step 2) ────────
    # Turning the app off or removing a designation needs a reason in the same
    # save, on every door (desk, REST, set_value); the reason is emptied after
    # the Version row has kept it. alvoraa_goals validates its own three fields
    # on the same Single; each hook looks only at its own fields.
    "HR Settings": {
        "validate": "alvoraa_portal.field_app_settings.validate_hr_settings",
        "on_change": "alvoraa_portal.field_app_settings.clear_reason_after_save",
    },
}

# ── Row-level security ───────────────────────────────────────────────────────
permission_query_conditions = {
    "Employee Checkin": "alvoraa_portal.field_app_access.checkin_query_conditions",
    # A phone record links Employee but not Company, so a Company User Permission
    # never reached it and an HR user limited to one company could list every
    # company's phones (slice 013 step 2, C-11c).
    "Alvoraa Field Device": "alvoraa_portal.field_app_access.device_query_conditions",
}

has_permission = {
    "Employee Checkin": "alvoraa_portal.field_app_access.checkin_has_permission",
    "Alvoraa Field Device": "alvoraa_portal.field_app_access.device_has_permission",
}

scheduler_events = {
    "all": [
        "alvoraa_portal.scheduled_jobs.update_delivery_tracking",
    ],
    "hourly": [
        "alvoraa_portal.scheduled_jobs.calculate_driver_ratings",
    ],
    "daily": [
        # Faces have a shelf life. Deletes check-in photos past the retention
        # period the organisation set (default 90 days, 0 = keep for ever).
        # The punch, the time and the place stay - they are the record of work
        # done. Only the photo goes.
        "alvoraa_portal.field_app_photos.purge_old_checkin_photos",
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
    # Slice 012: 06:30 site time, after overnight device sync and auto attendance.
    # Only queues the job on the long queue (a cron entry runs on default).
    # Finds doubtful attendance days and figures whose data needs review.
    "cron": {
        "30 6 * * *": [
            "alvoraa_portal.data_review.enqueue_morning_checks",
        ],
    },
}


# ── Attendance corrections: the field's own option list, and the review fields
#
# after_migrate rather than the `baseline` seeder: baseline seeds NEW tenants
# only, so every site already live would never have received these - including
# the one the missing "forgot to punch in" reason was reported on. Both calls
# are idempotent.
after_migrate = [
    "alvoraa_portal.attendance_correction.after_migrate",
    # The photo, GPS accuracy and offline columns on Employee Checkin. Same
    # reasoning as the line above: sites already live never get a baseline run.
    "alvoraa_portal.field_checkin.after_migrate",
    # A branch on attendance, leave, claims and the rest, so location HR's
    # Branch permission applies to them (slice 011). See branch_scope.py.
    "alvoraa_portal.branch_scope.after_migrate",
    # Slice 012: indexes for the scoped figures, then the first data check.
    # Must stay AFTER branch_scope - two of the indexes need its column.
    "alvoraa_portal.data_review.after_migrate",
    # Slice 013 step 2: the field app's switches on HR Settings.
    "alvoraa_portal.field_app_settings.after_migrate",
]

# And on a fresh install, which never runs a migrate. Without this a brand new
# tenant has no review columns at all, and every correction fails on "Unknown
# column alvoraa_review_status". CI is what found it - it builds its site with
# `bench install-app` and nothing else.
after_install = [
    "alvoraa_portal.attendance_correction.after_migrate",
    "alvoraa_portal.field_checkin.after_migrate",
    "alvoraa_portal.branch_scope.after_migrate",
    # Slice 012: indexes only - a new site has no data to check. After branch_scope.
    "alvoraa_portal.data_review.after_install",
    # Slice 025: the Alvoraa logo, so a brand new tenant is branded before anyone
    # logs in - no upload, no docker cp, nothing to copy at provisioning time.
    # provision_tenant.sh already runs `install-app alvoraa_portal`, so this is the
    # one place it needs to live. Deliberately NOT in after_migrate: see brand.py
    # and baseline.py on why a default a tenant may change is applied once.
    "alvoraa_portal.brand.after_install",
    # Slice 013 step 2: the field app's switches on HR Settings.
    "alvoraa_portal.field_app_settings.after_migrate",
]
