import frappe
from frappe.model.document import Document


class VendorUser(Document):
    def validate(self):
        if self.failed_attempts is None:
            self.failed_attempts = 0
