app_name = "hrms"
app_title = "Frappe HR"
app_publisher = "Frappe Technologies Pvt. Ltd."
app_description = "Modern HR and Payroll Software"
app_email = "contact@frappe.io"
app_license = "GNU General Public License (v3)"
source_link = "http://github.com/frappe/hrms"
app_logo_url = "/assets/hrms/images/frappe-hr-logo.svg"
app_home = "/desk/people"

add_to_apps_screen = [
	{
		"name": "hrms",
		"logo": "/assets/hrms/images/frappe-hr-logo.svg",
		"title": "Frappe HR",
		"route": "/desk/people",
		"has_permission": "hrms.hr.utils.check_app_permission",
	}
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/hrms/css/hrms.css"
app_include_js = [
	"hrms.bundle.js",
]
app_include_css = "hrms.bundle.css"

# website

# include js, css files in header of web template
# web_include_css = "/assets/hrms/css/hrms.css"
# web_include_js = "/assets/hrms/js/hrms.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "hrms/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	# ALV-178: restored from upstream Frappe HR v16 (removed by 48f5439). Employee,
	# Company, Department, Timesheet, Delivery Trip and Bank Transaction follow in
	# the full restore (step B).
	"Payment Entry": "public/js/erpnext/payment_entry.js",
	"Journal Entry": "public/js/erpnext/journal_entry.js",
	# ── PMS ──────────────────────────────────────────────────────────────────
	"PMS Review Record": "public/js/pms_review_record.js",
	"PMS Calibration Session": "public/js/pms_calibration_session.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

calendars = ["Leave Application"]

# Generators
# ----------

# automatically create page for each record of this doctype
website_generators = ["Job Opening"]

website_route_rules = [
	{"from_route": "/hrms/<path:app_path>", "to_route": "hrms"},
	{"from_route": "/hr/<path:app_path>", "to_route": "roster"},
	# ── PMS portal ───────────────────────────────────────────────────────────
	{"from_route": "/pms-employee", "to_route": "pms-employee"},
	{"from_route": "/pms-manager", "to_route": "pms-manager"},
	{"from_route": "/pms-calibration", "to_route": "pms-calibration"},
	{"from_route": "/pms-steering", "to_route": "pms-steering"},
]
# Jinja
# ----------

# add methods and filters to jinja environment
jinja = {
	"methods": [
		"hrms.utils.get_country",
	],
}

# Installation
# ------------

# before_install = "hrms.install.before_install"
after_install = "hrms.install.after_install"
after_migrate = "hrms.setup.update_select_perm_after_install"

# Uninstallation
# ------------

before_uninstall = "hrms.uninstall.before_uninstall"
# after_uninstall = "hrms.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "hrms.utils.before_app_install"
after_app_install = "hrms.setup.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

before_app_uninstall = "hrms.setup.before_app_uninstall"
# after_app_uninstall = "hrms.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "hrms.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

has_upload_permission = {"Employee": "erpnext.setup.doctype.employee.employee.has_upload_permission"}

# ── Grace PMS — Fixtures (auto-imported on bench migrate) ────────────────────
fixtures = [
	{"dt": "Workflow", "filters": [["document_type", "like", "PMS%"]]},
]

# ── Grace PMS — Row-level security ───────────────────────────────────────────
permission_query_conditions = {
	"Attendance Deduction":    "hrms.alvoraa_late_rules.permissions.attendance_deduction_query",
	"Policy Document":         "hrms.alvoraa_policy_library.access.permission_query_conditions",
	"Policy Acknowledgement":  "hrms.alvoraa_policy_library.access.acknowledgement_query_conditions",
	"PMS Review Record":       "hrms.pms.permissions.review_record_query",
	"PMS Business Goal":       "hrms.pms.permissions.business_goal_query",
	"PMS Check In":            "hrms.pms.permissions.checkin_query",
	"PMS Upward Feedback":     "hrms.pms.permissions.upward_feedback_query",
	"PMS Calibration Session": "hrms.pms.permissions.calibration_session_query",
	"PMS Talent Flag":         "hrms.pms.permissions.talent_flag_query",
	# ALV-117: Frappe HR ships this doctype with read AND export for every
	# Employee and no row filter at all. Lists, reports and exports.
	"Employee Performance Feedback": "hrms.alvoraa_hr_core.feedback_access.feedback_query_conditions",
}

has_permission = {
	"Attendance Deduction": "hrms.alvoraa_late_rules.permissions.has_attendance_deduction_permission",
	"Policy Document":      "hrms.alvoraa_policy_library.access.has_permission",
	"PMS Review Record":   "hrms.pms.permissions.has_review_record_permission",
	"PMS Check In":        "hrms.pms.permissions.has_checkin_permission",
	"PMS Upward Feedback": "hrms.pms.permissions.has_upward_feedback_permission",
	"PMS Talent Flag":     "hrms.pms.permissions.has_talent_flag_permission",
	# ALV-117, and the other half of the pair: the query condition above filters
	# lists, this guards one record at its own URL, and when it is printed,
	# emailed, shared or written to.
	"Employee Performance Feedback": "hrms.alvoraa_hr_core.feedback_access.has_feedback_permission",
}

# DocType Class
# ---------------
# Override standard doctype classes

# ALV-178: restored from upstream Frappe HR v16 (removed by 48f5439). Without it a
# Payment Entry for an Employee may only reference a Journal Entry, so it cannot pay
# an Expense Claim, Employee Advance, Leave Encashment or Gratuity. Project comes
# with it because a submitted expense claim updates its project's costing, and
# only this class counts claims in it. Employee and Timesheet come back in the full
# restore (step B).
override_doctype_class = {
	"Payment Entry": "hrms.overrides.employee_payment_entry.EmployeePaymentEntry",
	"Project": "hrms.overrides.employee_project.EmployeeProject",
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"User": {
		"validate": [
			"erpnext.setup.doctype.employee.employee.validate_employee_role",
			"hrms.overrides.employee_master.update_approver_user_roles",
		],
	},
	"Company": {
		"validate": "hrms.overrides.company.validate_default_accounts",
		"on_update": [
			"hrms.overrides.company.make_company_fixtures",
			"hrms.overrides.company.set_default_hr_accounts",
			# ALV-178 / upstream v16: give every Expense Claim Type an expense
			# account for this company, so claims can post to the ledger.
			"hrms.overrides.company.set_expense_claim_type_accounts",
		],
		"on_trash": "hrms.overrides.company.handle_linked_docs",
	},
	"Holiday List": {
		"on_update": "hrms.utils.holiday_list.invalidate_cache",
		"on_trash": "hrms.utils.holiday_list.invalidate_cache",
	},
	# ── ALV-178: restored from upstream Frappe HR v16 (removed by 48f5439) ──
	# These are what mark an Expense Claim, Full and Final Statement or Salary
	# Withholding as paid, and unlink salary slips when a payroll entry is cancelled.
	"Payment Entry": {
		"on_submit": "hrms.hr.doctype.expense_claim.expense_claim.update_payment_for_expense_claim",
		"on_cancel": "hrms.hr.doctype.expense_claim.expense_claim.update_payment_for_expense_claim",
		"on_update_after_submit": "hrms.hr.doctype.expense_claim.expense_claim.update_payment_for_expense_claim",
	},
	"Unreconcile Payment": {
		"on_submit": "hrms.hr.doctype.expense_claim.expense_claim.update_payment_for_expense_claim",
	},
	"Journal Entry": {
		"validate": "hrms.hr.doctype.expense_claim.expense_claim.validate_expense_claim_in_jv",
		"on_submit": [
			"hrms.hr.doctype.expense_claim.expense_claim.update_payment_for_expense_claim",
			"hrms.hr.doctype.full_and_final_statement.full_and_final_statement.update_full_and_final_statement_status",
			"hrms.payroll.doctype.salary_withholding.salary_withholding.update_salary_withholding_payment_status",
		],
		"on_update_after_submit": "hrms.hr.doctype.expense_claim.expense_claim.update_payment_for_expense_claim",
		"on_cancel": [
			"hrms.hr.doctype.expense_claim.expense_claim.update_payment_for_expense_claim",
			"hrms.payroll.doctype.salary_slip.salary_slip.unlink_ref_doc_from_salary_slip",
			"hrms.hr.doctype.full_and_final_statement.full_and_final_statement.update_full_and_final_statement_status",
			"hrms.payroll.doctype.salary_withholding.salary_withholding.update_salary_withholding_payment_status",
		],
	},
	"Employee": {
		"validate": [
			"hrms.overrides.employee_master.validate_onboarding_process",
			"hrms.alvoraa_employee_documents.employee_documents.validate_documents",
		],
		"on_update": [
			"hrms.overrides.employee_master.update_approver_role",
			"hrms.overrides.employee_master.publish_update",
			"hrms.alvoraa_employee_documents.employee_documents.sync_onboarding_summary",
		],
		"after_insert": [
			"hrms.overrides.employee_master.update_job_applicant_and_offer",
			"hrms.alvoraa_employee_documents.employee_documents.fill_checklist",
		],
		"on_trash": "hrms.overrides.employee_master.update_employee_transfer",
		"after_delete": "hrms.overrides.employee_master.publish_update",
	},
	"Project": {"validate": "hrms.controllers.employee_boarding_controller.update_employee_boarding_status"},
	"Task": {"on_update": "hrms.controllers.employee_boarding_controller.update_task"},
	# ── Grace Group custom hooks ──────────────────────────────────────────────
	"Leave Application": {
		"on_submit": "hrms.grace_group.hooks.fleet_reallocation.on_submit",
	},
	"Salary Structure Assignment": {
		"before_insert": "hrms.regional.india.utils.set_esi_applicable",
	},
	"Appraisal": {
		"before_save": [
			"hrms.grace_group.hooks.appraisal_metrics.fetch_metrics",
			"hrms.alvoraa_hr_core.attendance_score.compute",
		],
		# Ask the dotted-line managers once the solid-line manager has scored it -
		# after, not alongside, or the second opinion anchors on the first.
		"on_update": "hrms.alvoraa_org_structure.dotted_line.request_dotted_line_feedback",
		"before_submit": [
			"hrms.alvoraa_hr_core.attendance_score.compute",
			# A block, not a reminder. An optional second opinion never arrives
			# in a busy quarter, which leaves somebody rated by a manager who
			# saw half their work.
			"hrms.alvoraa_org_structure.dotted_line.require_dotted_line_feedback",
		],
	},
	"Appraisal Cycle": {
		"validate": "hrms.alvoraa_hr_core.attendance_score.apply_cycle_settings",
	},
	"Job Applicant": {
		"validate": "hrms.alvoraa_screening.screening.screen",
	},
	# ── Grace PMS ─────────────────────────────────────────────────────────────
	"PMS Review Record": {
		"validate":    "hrms.pms.pms_review.validate",
		"before_save": "hrms.pms.pms_review.before_save",
		"on_update":   "hrms.pms.pms_review.on_update",
	},
	"PMS Business Goal": {
		"validate":      "hrms.pms.pms_goals.validate_goal",
		"before_submit": "hrms.pms.pms_goals.before_submit_goal",
	},
	"PMS Check In": {
		"after_insert": "hrms.pms.pms_checkin.prefill_agenda",
	},
	"PMS Company Value": {
		"after_save": "hrms.pms.pms_config.clear_company_values_cache",
	},
	"PMS Review Template": {
		"before_save": "hrms.pms.pms_config.before_template_save",
	},
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"cron": {
		# Monday 02:00 server time: the quarter-day late rule for the week that just ended.
		"0 2 * * 1": ["hrms.alvoraa_late_rules.late_rules.process_previous_week"],
		"0 3 * * *": ["hrms.alvoraa_employee_documents.employee_documents.expire_documents"],
	},
	"all": [
		"hrms.hr.doctype.interview.interview.send_interview_reminder",
	],
	"hourly": [
		"hrms.hr.doctype.daily_work_summary_group.daily_work_summary_group.trigger_emails",
		"hrms.pms.pms_notifications.process_notification_queue",  # PMS
	],
	"hourly_long": [
		"hrms.hr.doctype.shift_type.shift_type.update_last_sync_of_checkin",
		"hrms.hr.doctype.shift_type.shift_type.process_auto_attendance_for_all_shifts",
		"hrms.hr.doctype.shift_schedule_assignment.shift_schedule_assignment.process_auto_shift_creation",
	],
	"daily": [
		"hrms.controllers.employee_reminders.send_birthday_reminders",
		"hrms.controllers.employee_reminders.send_work_anniversary_reminders",
		"hrms.hr.doctype.daily_work_summary_group.daily_work_summary_group.send_summary",
		"hrms.hr.doctype.interview.interview.send_daily_feedback_reminder",
		"hrms.hr.doctype.shift_assignment.shift_assignment.mark_expired_shift_assignments_as_inactive",
		"hrms.hr.doctype.job_opening.job_opening.close_expired_job_openings",
		# ── PMS ──────────────────────────────────────────────────────────────
		"hrms.pms.pms_notifications.send_overdue_stage_alerts",
		"hrms.pms.pms_notifications.send_checkin_nudges",
	],
	"daily_long": [
		"hrms.hr.doctype.leave_ledger_entry.leave_ledger_entry.process_expired_allocation",
		"hrms.hr.utils.generate_leave_encashment",
		"hrms.hr.utils.allocate_earned_leaves",
	],
	"weekly": ["hrms.controllers.employee_reminders.send_reminders_in_advance_weekly"],
	"monthly": ["hrms.controllers.employee_reminders.send_reminders_in_advance_monthly"],
}

# ── ALV-178: restored from upstream Frappe HR v16 (removed by 48f5439) ──────
# ERPNext reads these lists. advance_payment_payable_doctypes is how an Employee
# Advance learns it was paid; invoice_doctypes lets a Payment Entry allocate against
# an Expense Claim; repost_allowed_doctypes lets Repost Accounting Ledger rebuild a
# claim's ledger (the ALV-178 data repair uses it). accounting_dimension_doctypes,
# period_closing_doctypes and bank_reconciliation_doctypes follow in step B.
advance_payment_payable_doctypes = ["Leave Encashment", "Gratuity", "Employee Advance"]

invoice_doctypes = ["Expense Claim"]

repost_allowed_doctypes = ["Expense Claim"]

# Upstream v16, adopted 29 Sep 2026 (ALV-178 decision D9).
audit_trail_doctypes = ["Expense Claim", "Payroll Entry", "Salary Slip", "Leave Encashment", "Gratuity"]

# Testing
# -------

before_tests = "hrms.tests.test_utils.before_tests"

# Overriding Methods
# -----------------------------

# get matching queries for Bank Reconciliation
get_matching_queries = "hrms.hr.utils.get_matching_queries"

regional_overrides = {
	"India": {
		"hrms.hr.utils.calculate_annual_eligible_hra_exemption": "hrms.regional.india.utils.calculate_annual_eligible_hra_exemption",
		"hrms.hr.utils.calculate_hra_exemption_for_period": "hrms.regional.india.utils.calculate_hra_exemption_for_period",
		"hrms.hr.utils.calculate_tax_with_marginal_relief": "hrms.regional.india.utils.calculate_tax_with_marginal_relief",
	},
}

# ERPNext doctypes for Global Search
global_search_doctypes = {
	"Default": [
		{"doctype": "Salary Slip", "index": 19},
		{"doctype": "Leave Application", "index": 20},
		{"doctype": "Expense Claim", "index": 21},
		{"doctype": "Employee Grade", "index": 37},
		{"doctype": "Job Opening", "index": 39},
		{"doctype": "Job Applicant", "index": 40},
		{"doctype": "Job Offer", "index": 41},
		{"doctype": "Salary Structure Assignment", "index": 42},
		{"doctype": "Appraisal", "index": 43},
	],
}

# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "hrms.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
override_doctype_dashboards = {
	"Employee": "hrms.overrides.dashboard_overrides.get_dashboard_for_employee",
	"Holiday List": "hrms.overrides.dashboard_overrides.get_dashboard_for_holiday_list",
	"Task": "hrms.overrides.dashboard_overrides.get_dashboard_for_project",
	"Project": "hrms.overrides.dashboard_overrides.get_dashboard_for_project",
}

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

ignore_links_on_delete = ["PWA Notification"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"hrms.auth.validate"
# ]

# Translation
# --------------------------------

# Make link fields search translated document names for these DocTypes
# Recommended only for DocTypes which have limited documents with untranslated names
# For example: Role, Gender, etc.
# translated_search_doctypes = []

company_data_to_be_ignored = [
	"Salary Component Account",
	"Salary Structure",
	"Salary Structure Assignment",
	"Payroll Period",
	"Income Tax Slab",
	"Leave Period",
	"Leave Policy Assignment",
	"Employee Onboarding Template",
	"Employee Separation Template",
]

# List of apps whose translatable strings should be excluded from this app's translations.
ignore_translatable_strings_from = ["frappe"]
employee_holiday_list = ["hrms.utils.holiday_list.get_holiday_list_for_employee"]
export_python_type_annotations = True
require_type_annotated_api_methods = True
