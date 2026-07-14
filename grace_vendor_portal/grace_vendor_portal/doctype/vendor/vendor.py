import frappe
from frappe.model.document import Document


class Vendor(Document):
    def validate(self):
        if self.account_balance is None:
            self.account_balance = 0
