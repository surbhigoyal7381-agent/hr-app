import frappe
from frappe.model.document import Document


class PMSActionItem(Document):
    def on_update(self):
        if self.status == "Closed" and not self.resolved_on:
            self.db_set("resolved_on", frappe.utils.today())
