import frappe


def clear_company_values_cache(doc, method=None):
    frappe.cache().delete_key("pms_company_values")


def before_template_save(doc, method=None):
    """Copy-on-modify: saving an Active template creates a new Draft version."""
    if doc.is_new():
        return
    old_status = frappe.db.get_value("PMS Review Template", doc.name, "status")
    if old_status != "Active":
        return
    # clone current Active to a new Draft
    clone = frappe.copy_doc(doc)
    clone.status = "Draft"
    clone.version = (doc.version or 1) + 1
    clone.insert(ignore_permissions=True)
    frappe.msgprint(
        f"Active template copied to new Draft version {clone.version} ({clone.name}). "
        "Your changes are saved on the new draft.",
        alert=True,
    )
    # prevent overwriting the active one by reverting unsaved fields
    frappe.flags.redirect_location = f"/app/pms-review-template/{clone.name}"
    raise frappe.Redirect
