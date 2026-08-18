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
    },
    "Goal Evidence": {
        "before_insert": "alvoraa_goals.controllers.evidence.validate_evidence",
        "after_insert": "alvoraa_goals.controllers.evidence.after_insert_evidence",
    },
    "KPI": {
        "validate": "alvoraa_goals.controllers.kpi.validate_kpi",
    },
}

# ── Row-level scoping ─────────────────────────────────────────────────────
# Doctype permissions grant the Employee role read on the whole table; these
# narrow each query to the caller's own rows (plus their direct reports').
permission_query_conditions = {
    "Individual Goal": "alvoraa_goals.permissions.individual_goal_query",
    "KPI":             "alvoraa_goals.permissions.kpi_query",
}

has_permission = {
    "Individual Goal": "alvoraa_goals.permissions.has_employee_permission",
    "KPI":             "alvoraa_goals.permissions.has_employee_permission",
}

scheduler_events = {
    "hourly": [
        "alvoraa_goals.scheduled_jobs.recalculate_all_progress",
    ],
    "daily": [
        "alvoraa_goals.scheduled_jobs.check_cascade_alignment",
        "alvoraa_goals.scheduled_jobs.send_progress_reminders",
    ],
}

fixtures = ["Evidence Validator"]

doctype_js = {
    "Shift Request": "public/js/shift_request.js",
}

