app_name = "alvoraa_portal"
app_title = "Alvora HRMS"
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

# ── Page parts for the employee portal (slice 034, OPS-31) ──────────
# `{{ ess_part("home") }}` pastes one piece of the portal's markup into the page.
# It exists because Frappe compiles at most 32 Jinja templates per worker, and
# the portal page's chain already uses about 25 - so splitting its markup into
# one file per area with `{% include %}` runs into the cache and costs +33 %.
# A part holds no Jinja, so it is read and pasted rather than compiled, and the
# number of parts stops mattering. See ess_parts.py for the rules it keeps.
jinja = {"methods": [
    "alvoraa_portal.ess_parts.ess_part",
    # ALV-175: our own templates/emails/standard.html calls this to close the
    # gap where no outgoing Email Account has our lockup set at all.
    "alvoraa_portal.email_brand.resolve_header_logo",
]}

# ── Doctype event hooks ────────────────────────────────────────────────────
# No desk-side JavaScript. portal_switch.js was removed in ALV-152: it bound
# to markup Frappe 16 never shows. "Switch to Employee Portal" is now an Action
# row in Navbar Settings, which Frappe's own menu runs (module_access.py).

# The "Field attendance app" tab on HR Settings (slice 013 step 2): the counts
# beside the switch, the confirm before turning it off or removing a
# designation, and the change history. The rules themselves are on the server
# (field_app_settings.py); this only asks before HR does something that stops
# phones working.
doctype_js = {
    "HR Settings": "public/js/hr_settings_field_app.js",
    # The "Field attendance app" section on the Employee form (slice 013 step
    # 5): the state line, the invite and block dialogs, the phones and the code
    # history. The QR encoder loads first; the section draws the code from E7's
    # answer in the browser, so no other request ever carries it (AC-47).
    "Employee": ["public/js/alvoraa_qr.js", "public/js/employee_field_app.js"],
}

# The phone list (slice 013 step 5, US-18): default "joined in the last 7
# days", status with its reason or date, and the note that there is no "last
# seen" column on purpose.
doctype_list_js = {
    "Alvoraa Field Device": "public/js/alvoraa_field_device_list.js",
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
            # ALV-128 SEC-28: an unlinked login stops the app phones it signed in.
            "alvoraa_portal.field_app_device.block_phones_for_unlinked_login",
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
        # Slice 043 (V-6): a user may not hold an AI intake mailbox unless they
        # are a sales user without an HR role. Silent on sites without the field.
        "validate":     "alvoraa_portal.ai_leads.guards.validate_user",
        "after_insert": "alvoraa_portal.module_access.apply_on_user_insert",
        "on_update":    ["alvoraa_portal.hr_api.invalidate_portal_context_cache",
                         "alvoraa_portal.module_access.apply_on_user_update",
                         # ALV-128: a disabled login stops the app phones it signed
                         # in. (A changed password signs them out on their next
                         # call instead - field_checkin, 26 Sep 2026.)
                         "alvoraa_portal.field_app_device.block_phones_for_disabled_login"],
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
    # ── A check-in radius a phone can honestly check (slice 013 step 4) ───
    # Under 100 m a phone's own position error refuses people standing at the
    # door. Refused when the Shift Location is saved, on every door; never at
    # punch time. 0 keeps Frappe HR's meaning, "no radius". A hook here, not
    # an edit to hrms, so `bench update` stays safe.
    "Shift Location": {
        "validate": "alvoraa_portal.field_checkin.refuse_small_radius",
    },
    # Slice 043 (SEC-8, V-1 to V-7): which mailboxes AI lead intake may read.
    # Refused on the document, so the desk, the REST API and imports all obey it.
    "Email Account": {
        "validate": "alvoraa_portal.ai_leads.guards.validate_email_account",
    },
    # Slice 043: a newly pulled email goes to AI lead intake at once (a queued
    # job, never inside the mail pull). The five-minute sweep is the safety net.
    "Communication": {
        "after_insert": "alvoraa_portal.ai_leads.intake.on_new_email",
    },
}

# ── Row-level security ───────────────────────────────────────────────────────
permission_query_conditions = {
    "Employee Checkin": "alvoraa_portal.field_app_access.checkin_query_conditions",
    # A phone record links Employee but not Company, so a Company User Permission
    # never reached it and an HR user limited to one company could list every
    # company's phones (slice 013 step 2, C-11c).
    "Alvoraa Field Device": "alvoraa_portal.field_app_access.device_query_conditions",
    # The code record and the acknowledgement record (slice 013 step 3) link
    # only Employee too, so they are scoped the same way.
    "Alvoraa App Invite": "alvoraa_portal.field_app_access.invite_query_conditions",
    "Alvoraa Notice Acknowledgement": "alvoraa_portal.field_app_access.acknowledgement_query_conditions",
}

has_permission = {
    "Employee Checkin": "alvoraa_portal.field_app_access.checkin_has_permission",
    "Alvoraa Field Device": "alvoraa_portal.field_app_access.device_has_permission",
    "Alvoraa App Invite": "alvoraa_portal.field_app_access.invite_has_permission",
    "Alvoraa Notice Acknowledgement": "alvoraa_portal.field_app_access.acknowledgement_has_permission",
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
        # Slice 013 step 6 (US-21, US-22): the field app's clean-up. Marks
        # codes that ran out and retires their hash; deletes codes that never
        # set up a phone twelve months after they ended; checks that no stopped
        # record still holds a live secret; writes the day's counts, with no
        # names in them. Separate from the photo purge above on purpose - the
        # two answer different questions and one failing must not stop the other.
        "alvoraa_portal.field_app_housekeeping.daily",
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
        # Slice 043: enquiry emails into CRM leads. Returns before any query on a
        # site that has not switched it on; 25 emails at most per run (OPS-2).
        "*/5 * * * *": [
            "alvoraa_portal.ai_leads.intake.sweep",
        ],
        # Slice 043: fetch intake mailboxes every minute (Frappe fetches all mail
        # every ten). Each new email then goes to the AI at once (on_new_email).
        # Returns before any query on a site that has not switched intake on.
        "* * * * *": [
            "alvoraa_portal.ai_leads.intake.pull_intake_mailboxes",
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
    # Slice 013 step 5: the field app section on the Employee form.
    "alvoraa_portal.field_app_desk.after_migrate",
    # Slice 166/167: LMS and Helpdesk ship with public defaults (guest course
    # access, a public jobs board, guest ticket creation). provision_tenant.sh
    # already applies the safe values right after each app installs, but this
    # is the safety net for a site where either app reaches a site by some
    # other path - a no-op on every site until the app is actually installed,
    # and a no-op forever after the one-time write. See lms_defaults.py and
    # helpdesk_defaults.py for why this never flips a value HR chose back.
    "alvoraa_portal.lms_defaults.after_migrate",
    "alvoraa_portal.helpdesk_defaults.after_migrate",
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
    # Slice 013 step 5: the field app section on the Employee form.
    "alvoraa_portal.field_app_desk.after_migrate",
    # ALV-149: a new tenant's app name is "Alvora HRMS", not Frappe's default.
    # Same once-only reasoning as brand.after_install above.
    "alvoraa_portal.brand_text.after_install",
    # ALV-174: outgoing email stops saying "Sent via ERPNext" and gets the
    # Alvora lockup in its header, from a tenant's first email onward. Safe to
    # run again later (a patch does, on migrate) if the sending Email Account
    # is set up after this point - apply() is idempotent either way.
    "alvoraa_portal.email_brand.after_install",
]

# ── Replace one upstream method wholesale, not monkeypatch it (ALV-174) ────
# CRM's own invitation email hardcodes "Frappe CRM" in the SUBJECT (Python, not
# a template) and in the body (a template that never reads the `title` it is
# passed) - see overrides/crm_invitation.py for why a template override cannot
# fix this and `override_doctype_class` is the right mechanism instead.
override_doctype_class = {
    "CRM Invitation": "alvoraa_portal.overrides.crm_invitation.AlvoraCRMInvitation",
}
