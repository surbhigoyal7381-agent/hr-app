app_name = "alvoraa_portal"
app_title = "Alvora HRMS"
app_publisher = "AllAboutHR"
app_description = "Multi-brand vendor portal with order tracking and delivery management"
app_email = "support@alvoraa.co"
app_license = "MIT"
required_apps = ["frappe/erpnext"]

# ── Alvora colours on the desk ────────────────────────────────────────────
# `app_include_css` is served on DESK pages only (/app/*). It does NOT reach
# the employee portal: `hrms-employee.html` and the other www pages are website
# pages, they carry their own design system, and `scripts/check_design_system.py`
# counts the colours on them in CI. So this changes what HR and admins see, and
# leaves what an employee sees exactly as it was.
app_include_css = "/assets/alvoraa_portal/css/alvora_theme.css"

# ── Post-login redirect: portal users → their portal; admins → /app ───────
on_login = ["alvoraa_portal.auth.on_login",
            # ALV-249 D-3: a login linked by a direct database write, or whose
            # role lost Employee read, gets its own-record row before it is in.
            "alvoraa_portal.own_record_permission.on_login"]

# ── Nothing but the password screen, until they choose one (ALV-242) ──────
# ALV-232 only chose where a first-use session LANDS. The back button walked
# straight past it into the whole app, and since HR issues one password per
# batch that meant signing in as a colleague and reading their pay. This runs
# on every request, so it covers the portal, /me, /checkin and the desk at once.
# It fails open by design - see alvoraa_portal.auth.lock_until_password_chosen.
before_request = [
    # ALV-249: no request may ask Frappe to skip User Permissions or
    # permissions. Every path, "/" with cmd included. See request_guard.py.
    "alvoraa_portal.request_guard.drop_permission_skips",
    "alvoraa_portal.auth.lock_until_password_chosen",
    # The bare "/" again. The get_website_user_home_page hook below is
    # asked fourth and can be overruled by a default workspace, so it is
    # not enough on its own. See auth.route_the_bare_root.
    "alvoraa_portal.auth.route_the_bare_root",
]

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
    # ATT-07: the "Reprocess Attendance" button, offered where the employees and
    # the dates are already chosen. The first click only previews - it writes
    # nothing until the numbers have been seen and agreed.
    "Payroll Entry": "public/js/payroll_entry_reprocess.js",
}

# The phone list (slice 013 step 5, US-18): default "joined in the last 7
# days", status with its reason or date, and the note that there is no "last
# seen" column on purpose.
doctype_list_js = {
    "Alvoraa Field Device": "public/js/alvoraa_field_device_list.js",
}

doc_events = {
    # The payroll rules engine prices the slip from attendance (slice 059).
    # It runs AFTER Frappe's own validate, replaces payment_days with the
    # engine's paid days, and re-runs the calculation over them. It swallows
    # its own errors: a slip that cannot be produced is a person who cannot
    # be paid.
    "Salary Slip": {
        "validate": "alvoraa_portal.payroll_slip.on_salary_slip_validate",
        # Slice 067: the notes the validate hook leaves for HR (held days, red
        # and green lines not applied). A new slip is not in the database yet
        # during validate, so a comment on it is refused; it is posted here.
        "on_update": "alvoraa_portal.payroll_slip.post_slip_notes",
        # Slice 066 (SEC-9, D2): a slip is not submitted with a stale grooming
        # line or one above the legal limit. Does nothing without a rule set.
        "before_submit": "alvoraa_portal.payroll_slip.check_grooming_before_submit",
    },
    "Attendance": {
        "on_submit": "alvoraa_portal.payroll_rules_apply.on_attendance_submit",
    },
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
        # Slice 063, OD-1 remedy (iv): a half-day correction can reach a
        # half-day leave day at a company with an enabled pay rule set.
        "before_insert": "alvoraa_portal.leave_rules.prepare_half_day_correction",
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
            # A manager may act for their own reports and nobody else. Moving
            # somebody's reporting line moves the permission with it, in the
            # same save, so the two can never disagree. See manager_scope.py.
            "alvoraa_portal.manager_scope.on_employee_update",
            # ALV-249: a staff login sees its own record and nobody else's.
            "alvoraa_portal.own_record_permission.on_employee_update",
        ],
        "on_trash":  "alvoraa_portal.hr_api.invalidate_portal_context_cache",
        # ALV-215 (063 SEC-17, R4): nobody changes a locked job, pay or bank
        # field on their own record, HR included. See employee_field_rights.py.
        "validate": ["alvoraa_portal.employee_field_rights.refuse_own_locked_change",
                     # Slice 076 Part C (AC-105): only the person sets their
                     # birthday opt-out; any other save puts it back.
                     "alvoraa_portal.home_people.keep_hide_birthday"],
    },
    # ALV-215: an Employee import with a column the importer may not change is
    # refused with a message, instead of Frappe dropping the values silently.
    "Data Import": {
        "validate": "alvoraa_portal.employee_field_rights.refuse_import_of_locked_columns",
    },
    # ALV-215: a Promotion or Transfer that changes a field the submitter may
    # not change is refused, instead of Frappe silently putting the value back.
    # Cancel too: it writes the old values back the same way.
    "Employee Promotion": {
        "before_submit": "alvoraa_portal.employee_field_rights.refuse_locked_promotion_fields",
        "before_cancel": "alvoraa_portal.employee_field_rights.refuse_locked_promotion_fields",
    },
    "Employee Transfer": {
        "before_submit": "alvoraa_portal.employee_field_rights.refuse_locked_promotion_fields",
        "before_cancel": "alvoraa_portal.employee_field_rights.refuse_locked_promotion_fields",
    },
    # ALV-215: PAN, ESI, PF, IFSC and MICR are created when the first Indian
    # company is set up, after install. Lock them the moment they exist.
    "Custom Field": {
        "after_insert": "alvoraa_portal.employee_field_rights.lock_new_custom_field",
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
                         "alvoraa_portal.field_app_device.block_phones_for_disabled_login",
                         # ALV-249: promoted to HR loses the own-record row,
                         # a disabled login loses it, back to staff gets it.
                         "alvoraa_portal.own_record_permission.on_user_update"],
    },
    # ── Global features cache invalidation ───────────────────────────────
    # Clear portal_features_global when HR configuration changes
    "Shift Type": {
        # ALV-211: a new shift accepts punches 3 h before and 3 h after.
        "before_insert": "alvoraa_portal.attendance_correction.default_shift_window",
        "after_insert": "alvoraa_portal.hr_api.invalidate_features_cache",
        "on_update":    "alvoraa_portal.hr_api.invalidate_features_cache",
        "on_trash":     "alvoraa_portal.hr_api.invalidate_features_cache",
    },
    "Leave Type": {
        "after_insert": "alvoraa_portal.hr_api.invalidate_features_cache",
        "on_update":    "alvoraa_portal.hr_api.invalidate_features_cache",
        "on_trash":     ["alvoraa_portal.hr_api.invalidate_features_cache",
                         # Slice 063 (D1): "Paid Leaves" cannot be deleted.
                         "alvoraa_portal.leave_rules.lock_paid_leaves"],
        # Slice 063 (D1): "Paid Leaves" is created once with the right flags,
        # then locked - only where a company's pay rule set is switched on.
        "validate":     "alvoraa_portal.leave_rules.lock_paid_leaves",
        "before_rename": "alvoraa_portal.leave_rules.lock_paid_leaves",
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
    # ── The account an expense claim is owed from (slice 058) ─────────────
    # Frappe HR reads `Company.default_expense_claim_payable_account` and never
    # fills it; upstream expects a human to choose. Nobody did, so when ALV-178
    # restored ledger posting every claim hit "Payable Account is mandatory".
    # Filled from here rather than from `hrms.overrides.company` so no new edit
    # lands inside the vendored Frappe HR tree (ALV-169).
    "Company": {
        "after_insert": "alvoraa_portal.expense_accounts.set_expense_claim_payable_account",
        "on_update":    "alvoraa_portal.expense_accounts.set_expense_claim_payable_account",
        "validate":     "alvoraa_portal.expense_accounts.validate_expense_claim_payable_account",
    },
    # The other half of the same gap. A claim needs an expense account on its
    # TYPE as well. ALV-178 fills that, but only when a COMPANY is saved - so a
    # type added later has none, and every claim against it is refused.
    "Expense Claim Type": {
        "after_insert": "alvoraa_portal.expense_accounts.set_expense_claim_type_account",
    },
    # ── Nobody approves their own leave ───────────────────────────────────
    # Submitting a Leave Application is what approves or rejects it. Hung off
    # the document so the desk and REST API get the same rule as the portal,
    # even where HR Settings allows self-approval (slice 010, SEC-9).
    "Leave Application": {
        "before_submit": "hrms.alvoraa_hr_core.access.refuse_own_submit",
        # Slice 063, DTC only (an enabled pay rule set): current month only and
        # Leave Without Pay up to 5 a month, at filing and at approval, on
        # every door (SEC-6, SEC-13). Then the managers up the chain are told.
        "validate":      "alvoraa_portal.leave_rules.validate_leave_application",
        "on_submit":     "alvoraa_portal.leave_rules.notify_chain_on_approval",
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
    # Slice 057 (A): a lead or deal reaching a status creates that step's CRM
    # Tasks (rows of Alvoraa CRM Step Task). No query unless the status changed.
    "CRM Lead": {
        "on_update": [
            "alvoraa_portal.crm_steps.on_status_change",
            # 4 Oct: a changed name or company reaches the "Lead / Deal" column on its tasks.
            "alvoraa_portal.crm_steps.refresh_task_labels",
        ],
    },
    "CRM Deal": {
        "on_update": [
            "alvoraa_portal.crm_steps.on_status_change",
            # 4 Oct: a changed name or company reaches the "Lead / Deal" column on its tasks.
            "alvoraa_portal.crm_steps.refresh_task_labels",
        ],
    },
    # Slice 057, 4 Oct: the "Lead / Deal" column on every CRM Task, ours or made by
    # hand. One read of the lead or deal, only when the task is new or re-pointed.
    "CRM Task": {
        "validate": "alvoraa_portal.crm_steps.set_task_label",
    },
    # Slice 057 (B): a message forwarded by a listed salesperson goes to AI lead
    # intake (a queued job, only after Meta's signature is checked). A site-config
    # read and nothing more for any other message.
    "WhatsApp Message": {
        "after_insert": "alvoraa_portal.ai_leads.whatsapp.on_whatsapp_message",
    },
    # Slice 066: nobody submits a grooming red on themselves, on any door.
    "Grooming Mark": {
        "before_submit": "hrms.alvoraa_hr_core.access.refuse_own_submit",
    },
    # Slice 066 (SEC-8): no comment, assignment or share on a grooming red or a
    # grooming review. One doctype-name comparison for every other row.
    "Comment": {
        "validate": "alvoraa_portal.grooming.refuse_side_record",
    },
    "ToDo": {
        "validate": "alvoraa_portal.grooming.refuse_side_record",
    },
    "DocShare": {
        "validate": "alvoraa_portal.grooming.refuse_side_record",
    },
    # Slice 066, 25 Oct (security verification B2): no file, no tag on a mark.
    "File": {
        "validate": "alvoraa_portal.grooming.refuse_side_record",
    },
    "Tag Link": {
        "validate": "alvoraa_portal.grooming.refuse_side_record",
    },
    # Slice 076 Part C (SEC-13): nobody approves their own expense claim, on
    # any door, whatever HR Settings says about self-approval.
    "Expense Claim": {
        "before_submit": "hrms.alvoraa_hr_core.access.refuse_own_submit",
        # Review C: the claimant cannot pick their own approver (HR may).
        "validate": "alvoraa_portal.hr_api.keep_claim_approver",
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
    # Slice 066 (SEC-4): the records' own read gate, NOT manager_scope's User
    # Permissions - those cannot say "today", and leave a new doctype open.
    "Grooming Mark": "alvoraa_portal.grooming.mark_query_conditions",
    "Grooming Review": "alvoraa_portal.grooming.review_query_conditions",
}

has_permission = {
    "Employee Checkin": "alvoraa_portal.field_app_access.checkin_has_permission",
    "Alvoraa Field Device": "alvoraa_portal.field_app_access.device_has_permission",
    "Alvoraa App Invite": "alvoraa_portal.field_app_access.invite_has_permission",
    "Alvoraa Notice Acknowledgement": "alvoraa_portal.field_app_access.acknowledgement_has_permission",
    # Slice 066 (SEC-4): one gate per record, the same rules as the list above.
    "Grooming Mark": "alvoraa_portal.grooming.mark_has_permission",
    "Grooming Review": "alvoraa_portal.grooming.review_has_permission",
}

scheduler_events = {
    "all": [
        "alvoraa_portal.scheduled_jobs.update_delivery_tracking",
        # Slice 076: hands at most two due notices to the long queue; writes
        # nothing itself. A notice goes out up to one tick after its time.
        "alvoraa_portal.announcements.send_due_announcements",
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
        # Slice 066 retention: erases a leaver's grooming marks and reviews 6
        # months after the relieving date. OFF until the site config holds
        # grooming_erase_enabled = 1 - see the note above erase_daily.
        "alvoraa_portal.grooming.erase_daily",
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
        # Slice 057 (C): the founders' CRM summary, 09:00 site time. Returns
        # before any query unless the site config names a recipient.
        "0 9 * * *": [
            "alvoraa_portal.crm_summary.send_daily",
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
    # 059: the salary working's link in the Payroll menu. The Payroll
    # workspace is a STANDARD one shipped by Frappe HR, so every upgrade
    # re-imports its file and replaces the record - a link added by hand
    # disappears silently at the next upgrade. Re-applied here instead.
    "alvoraa_portal.payroll_menu.after_migrate",
    # The reporting lines that already existed when manager review arrived, and
    # any that drifted through a direct database write. The doc_event above
    # keeps them right from here on.
    "alvoraa_portal.manager_scope.after_migrate",
    # Slice 166/167: LMS and Helpdesk ship with public defaults (guest course
    # access, a public jobs board, guest ticket creation). provision_tenant.sh
    # already applies the safe values right after each app installs, but this
    # is the safety net for a site where either app reaches a site by some
    # other path - a no-op on every site until the app is actually installed,
    # and a no-op forever after the one-time write. See lms_defaults.py and
    # helpdesk_defaults.py for why this never flips a value HR chose back.
    "alvoraa_portal.lms_defaults.after_migrate",
    "alvoraa_portal.helpdesk_defaults.after_migrate",
    # Slice 059: the columns the pay-rule engine writes each day's verdict
    # into. The engine and its tests were committed without them, and nothing
    # noticed because both its hooks return early on a company with no rule
    # set - which, until DTC's exists, is every company. See payroll_fields.py.
    "alvoraa_portal.payroll_fields.after_migrate",
    # Slice 057, 4 Oct: the "Lead / Deal" column on CRM Task. A no-op without CRM.
    # ALV-194: the link from a Job Opening back to the seat it is filling, so
    # the chart can say "this hole is being recruited for" rather than only
    # "this hole". A no-op until Frappe HR is installed. See org_job_link.py.
    "alvoraa_portal.org_job_link.after_migrate",
    "alvoraa_portal.crm_steps.ensure_task_label_field",
    # ALV-215 (063 SEC-17): job, pay and approver fields HR-only (level 2), bank
    # and ID fields HR Manager only (level 1). Re-applied every migrate, so a
    # reset in Role Permission Manager is put right. See employee_field_rights.py.
    "alvoraa_portal.employee_field_rights.apply",
    # Slice 076 Part C: the birthdays switch (ships off), the opt-out tick and
    # the expense decline reason. See home_people.py.
    "alvoraa_portal.home_people.after_migrate",
]

# Slice 057, 4 Oct: CRM installed after this app gets the "Lead / Deal" column at once.
after_app_install = ["alvoraa_portal.crm_steps.on_app_install"]

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
    # 059: the salary working's link in the Payroll menu. The Payroll
    # workspace is a STANDARD one shipped by Frappe HR, so every upgrade
    # re-imports its file and replaces the record - a link added by hand
    # disappears silently at the next upgrade. Re-applied here instead.
    "alvoraa_portal.payroll_menu.after_migrate",
    # The reporting lines that already existed when manager review arrived, and
    # any that drifted through a direct database write. The doc_event above
    # keeps them right from here on.
    "alvoraa_portal.manager_scope.after_migrate",
    # ALV-149: a new tenant's app name is "Alvora HRMS", not Frappe's default.
    # Same once-only reasoning as brand.after_install above.
    "alvoraa_portal.brand_text.after_install",
    # ALV-174: outgoing email stops saying "Sent via ERPNext" and gets the
    # Alvora lockup in its header, from a tenant's first email onward. Safe to
    # run again later (a patch does, on migrate) if the sending Email Account
    # is set up after this point - apply() is idempotent either way.
    # Slice 059: the columns the pay-rule engine writes each day's verdict
    # into. The engine and its tests were committed without them, and nothing
    # noticed because both its hooks return early on a company with no rule
    # set - which, until DTC's exists, is every company. See payroll_fields.py.
    "alvoraa_portal.payroll_fields.after_migrate",
    # ALV-194: the link from a Job Opening back to the seat it is filling, so
    # the chart can say "this hole is being recruited for" rather than only
    # "this hole". A no-op until Frappe HR is installed. See org_job_link.py.
    "alvoraa_portal.org_job_link.after_migrate",
    "alvoraa_portal.email_brand.after_install",
    # ALV-215: same as after_migrate - a new tenant must not start open.
    "alvoraa_portal.employee_field_rights.apply",
    # Slice 076: the Notice Sender role without desk access. Frappe makes it
    # WITH desk access while syncing the Announcement permissions; this runs
    # after that. Live sites get the same from the notice_sender_role patch.
    "alvoraa_portal.announcements.make_role",
    # Slice 076 Part C: same three fields as after_migrate.
    "alvoraa_portal.home_people.after_migrate",
]

# ALV-215 step B: the Promotion / Transfer field picker returned any Employee
# field, bank number included, ignoring field levels. Ours checks the level and
# then calls the upstream function unchanged.
# One dict only. A second `override_whitelisted_methods = {...}` later in this
# file would replace this one and silently drop the override above.
override_whitelisted_methods = {
    "hrms.hr.utils.get_employee_field_property": "alvoraa_portal.employee_field_rights.get_employee_field_property",
    # ALV-232: Frappe hands a System User "/desk" after a password change, and
    # every staff account is a System User. The wrapper calls Frappe's function
    # unchanged and only swaps the path it returns. See auth.update_password.
    "frappe.core.doctype.user.user.update_password": "alvoraa_portal.auth.update_password",
}

# ── Replace one upstream method wholesale, not monkeypatch it (ALV-174) ────
# CRM's own invitation email hardcodes "Frappe CRM" in the SUBJECT (Python, not
# a template) and in the body (a template that never reads the `title` it is
# passed) - see overrides/crm_invitation.py for why a template override cannot
# fix this and `override_doctype_class` is the right mechanism instead.
override_doctype_class = {
    "CRM Invitation": "alvoraa_portal.overrides.crm_invitation.AlvoraCRMInvitation",
}
