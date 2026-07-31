import frappe
from frappe.model.document import Document


class Company(Document):
    def validate(self):
        if not self.abbr:
            self.abbr = "".join([c[0].upper() for c in self.company_name.split() if c])
        self.abbr = self.abbr.strip()

    def on_update(self):
        frappe.clear_cache()
