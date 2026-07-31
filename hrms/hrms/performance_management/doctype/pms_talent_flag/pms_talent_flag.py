import frappe
from frappe.model.document import Document


class PMSTalentFlag(Document):
    def before_insert(self):
        self.flagged_on = frappe.utils.now()
