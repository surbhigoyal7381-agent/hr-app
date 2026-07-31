import frappe


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.flags.redirect_location = "/login?redirect-to=/pms-calibration"
        raise frappe.Redirect
    if not frappe.db.exists("Has Role", {"parent": frappe.session.user, "role": ["in", ["HR Manager", "System Manager"]]}):
        frappe.flags.redirect_location = "/pms-employee"
        raise frappe.Redirect
    context.no_cache = 1
