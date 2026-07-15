app_name = "grace_vendor_portal"
app_title = "Grace Vendor Portal"
app_publisher = "Grace Group"
app_description = "Multi-brand vendor portal with order tracking and delivery management"
app_email = "ops@gracedrinks.in"
app_license = "MIT"
required_apps = ["frappe/erpnext"]

# ── Post-login redirect: portal users → their portal; admins → /app ───────
on_login = "grace_vendor_portal.auth.on_login"

# ── Redirect /login to the branded Kinexus login page ─────────────────────
website_redirects = [
    {"source": r"^/login$", "target": "/kinexus-login"},
]

# ── Portal route rules ────────────────────────────────────────────────────
website_route_rules = [
    {"from_route": "/vendor-portal",   "to_route": "vendor-portal"},
    {"from_route": "/driver-portal",   "to_route": "driver-portal"},
    {"from_route": "/hrms-home",       "to_route": "hrms-home"},
    {"from_route": "/hrms-employee",   "to_route": "hrms-employee"},
    {"from_route": "/kinexus-login",   "to_route": "kinexus-login"},
]

# ── Doctype event hooks ────────────────────────────────────────────────────
doc_events = {
    # Vendor Order: is_submittable removed; on_update covers all lifecycle events
    "Vendor Order": {
        "validate":  "grace_vendor_portal.controllers.vendor_order.validate",
        "on_update": "grace_vendor_portal.controllers.vendor_order.on_update",
    },
    "Order Rating": {
        "validate":      "grace_vendor_portal.controllers.rating.validate",
        "before_insert": "grace_vendor_portal.controllers.rating.before_insert",
        "after_insert":  "grace_vendor_portal.controllers.rating.after_insert",
    },
    "Delivery Assignment": {
        "after_insert": "grace_vendor_portal.controllers.delivery_assignment.after_insert",
        "on_update":    "grace_vendor_portal.controllers.delivery_assignment.on_update",
    },
    "Delivery Partner": {
        "validate": "grace_vendor_portal.controllers.delivery_partner.validate",
    },
    "Delivery Order": {
        "before_save": "grace_vendor_portal.controllers.delivery_order.before_save",
        "on_update":   "grace_vendor_portal.controllers.delivery_order.on_update",
    },
    "Delivery Feedback": {
        "validate":     "grace_vendor_portal.controllers.delivery_feedback.validate",
        "after_insert": "grace_vendor_portal.controllers.delivery_feedback.after_insert",
    },
    "Vehicle Maintenance Compliance": {
        "before_save": "grace_vendor_portal.controllers.vehicle_compliance.before_save",
    },
    "Delivery Performance Scorecard": {
        "before_save": "grace_vendor_portal.controllers.scorecard.before_save",
    },
}

scheduler_events = {
    "all": [
        "grace_vendor_portal.scheduled_jobs.update_delivery_tracking",
    ],
    "hourly": [
        "grace_vendor_portal.scheduled_jobs.calculate_driver_ratings",
    ],
    "daily": [
        "grace_vendor_portal.scheduled_jobs.send_arrival_notifications",
        "grace_vendor_portal.scheduled_jobs.check_compliance_alerts",
    ],
    "monthly": [
        "grace_vendor_portal.scheduled_jobs.generate_monthly_scorecards",
    ],
}
