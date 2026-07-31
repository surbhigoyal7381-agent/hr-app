import frappe
from frappe.model.document import Document


class OrderRating(Document):
    def validate(self):
        from grace_vendor_portal.controllers.rating import validate
        validate(self)

    def before_insert(self):
        from grace_vendor_portal.controllers.rating import before_insert
        before_insert(self)

    def after_insert(self):
        from grace_vendor_portal.controllers.rating import after_insert
        after_insert(self)
