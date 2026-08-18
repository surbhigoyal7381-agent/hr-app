import frappe
from frappe.model.document import Document


class DeliveryAssignment(Document):
    def after_insert(self):
        from alvoraa_portal.controllers.delivery_assignment import after_insert
        after_insert(self)

    def on_update(self):
        from alvoraa_portal.controllers.delivery_assignment import on_update
        on_update(self)
