import frappe
from frappe.model.document import Document


class VendorOrder(Document):
    def validate(self):
        from grace_vendor_portal.controllers.vendor_order import validate
        validate(self)

    def before_submit(self):
        from grace_vendor_portal.controllers.vendor_order import before_submit
        before_submit(self)

    def on_submit(self):
        from grace_vendor_portal.controllers.vendor_order import on_submit
        on_submit(self)

    def on_update_after_submit(self):
        from grace_vendor_portal.controllers.vendor_order import on_update_after_submit
        on_update_after_submit(self)
