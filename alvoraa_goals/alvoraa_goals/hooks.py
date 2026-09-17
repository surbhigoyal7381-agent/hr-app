app_name = "alvoraa_goals"
app_title = "Alvoraa Goals"
app_publisher = "AllAboutHR"
app_description = "Cascaded goal management with evidence-based progress tracking"
app_email = "hr@gracedrinks.in"
app_license = "MIT"
required_apps = ["frappe/hrms"]

doc_events = {
    "Individual Goal": {
        "validate": "alvoraa_goals.controllers.goal.validate_individual_goal",
        "after_insert": "alvoraa_goals.controllers.goal.after_insert_goal",
        "before_submit": "alvoraa_goals.controllers.goal.before_submit_goal",
        "on_submit": "alvoraa_goals.controllers.goal.on_submit_goal",
        # Slice 010 group D: while an open review holds the Objective, its
        # definition is locked (before_validate runs even with ignore_validate),
        # it cannot be deleted, and a fact change reaches the review's copy.
        "before_validate": "alvoraa_goals.review_items.enforce_definition_lock",
        "before_update_after_submit": "alvoraa_goals.review_items.enforce_definition_lock",
        "on_trash": "alvoraa_goals.review_items.refuse_delete_while_held",
        "on_update": "alvoraa_goals.review_items.refresh_copies_of",
    },
    "Goal Evidence": {
        "before_insert": "alvoraa_goals.controllers.evidence.validate_evidence",
        "after_insert": "alvoraa_goals.controllers.evidence.after_insert_evidence",
    },
    "KPI": {
        "validate": "alvoraa_goals.controllers.kpi.validate_kpi",
        # Slice 010 group D: the same review lock, delete rule and copy refresh.
        # Phase 3 adds the rating guard after the lock: nobody writes a rating on
        # the live KPI any more (SEC-2).
        "before_validate": [
            "alvoraa_goals.review_items.enforce_definition_lock",
            "alvoraa_goals.controllers.kpi.refuse_rating_changes",
        ],
        "on_trash": "alvoraa_goals.review_items.refuse_delete_while_held",
        "on_update": "alvoraa_goals.review_items.refresh_copies_of",
    },
    # Slice 010 group D: the three review settings accept only their own choices.
    "HR Settings": {
        "validate": "alvoraa_goals.review_items.validate_hr_settings",
    },
}

# ── Row-level scoping ─────────────────────────────────────────────────────
# Doctype permissions grant the Employee role read on the whole table; these
# narrow each query to the caller's own rows (plus their direct reports').
permission_query_conditions = {
    "Individual Goal": "alvoraa_goals.permissions.individual_goal_query",
    "KPI":             "alvoraa_goals.permissions.kpi_query",
    # Slice 010 group D (SEC-27): HR's desk follows the portal's stage rule.
    "Alvoraa Appraisal Extension": "alvoraa_goals.permissions.appraisal_extension_query",
    # Slice 010 group D fix round (security review B1, M4): a review's change
    # history and audit notes, and HRMS Appraisal scores, follow the same rule.
    # Frappe adds these to its own rules for the core doctypes; rows about any
    # other doctype are untouched.
    "Version": "alvoraa_goals.permissions.version_query",
    "Comment": "alvoraa_goals.permissions.comment_query",
    "Appraisal": "alvoraa_goals.permissions.appraisal_query",
}

has_permission = {
    "Individual Goal": "alvoraa_goals.permissions.has_employee_permission",
    "KPI":             "alvoraa_goals.permissions.has_employee_permission",
    # Slice 010 group D (SEC-27): read by stage and company; desk writes refused.
    "Alvoraa Appraisal Extension": "alvoraa_goals.permissions.has_appraisal_extension_permission",
    # Slice 010 group D fix round (security review B1, M4).
    "Version": "alvoraa_goals.permissions.has_review_history_permission",
    "Comment": "alvoraa_goals.permissions.has_review_history_permission",
    "Appraisal": "alvoraa_goals.permissions.has_appraisal_permission",
}

scheduler_events = {
    "hourly": [
        "alvoraa_goals.scheduled_jobs.recalculate_all_progress",
    ],
    "daily": [
        "alvoraa_goals.scheduled_jobs.check_cascade_alignment",
        "alvoraa_goals.scheduled_jobs.send_progress_reminders",
        # Slice 010 group D (R9): remind HR from day 15 when open reviews still lock items.
        "alvoraa_goals.review_items.remind_hr_of_held_items",
    ],
}

fixtures = ["Evidence Validator"]

# Slice 010 group D: the review settings on HR Settings. On install too, because
# a site built with `bench install-app` never runs a migrate.
after_migrate = [
    "alvoraa_goals.review_items.after_migrate",
]

after_install = [
    "alvoraa_goals.review_items.after_migrate",
]

doctype_js = {
    "Shift Request": "public/js/shift_request.js",
}

