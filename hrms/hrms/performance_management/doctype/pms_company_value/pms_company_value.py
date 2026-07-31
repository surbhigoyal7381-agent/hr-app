import frappe
from frappe.model.document import Document


class PMSCompanyValue(Document):
    def validate(self):
        self.value_name = self.value_name.strip()

    def after_save(self):
        frappe.cache().delete_key("pms_company_values")

    def on_trash(self):
        # Prevent delete if any goal/KPI has this tag
        refs = frappe.db.count("PMS Goal Value Tag", {"company_value": self.name})
        if refs:
            frappe.throw(
                f"Cannot delete '{self.value_name}' — it is tagged on {refs} goal(s)/KPI(s). Retire it instead."
            )


def get_active_values():
    cached = frappe.cache().get_value("pms_company_values")
    if cached:
        return cached
    values = frappe.get_all(
        "PMS Company Value",
        filters={"status": "Active"},
        fields=["name", "value_name", "description"],
        order_by="value_name asc",
    )
    frappe.cache().set_value("pms_company_values", values, expires_in_sec=3600)
    return values
