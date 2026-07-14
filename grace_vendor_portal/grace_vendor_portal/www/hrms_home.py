import frappe


def get_context(context):
    frappe.flags.redirect_location = "/hrms-employee"
    raise frappe.Redirect
