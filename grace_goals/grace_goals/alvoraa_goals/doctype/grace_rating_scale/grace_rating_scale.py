import frappe
from frappe.model.document import Document

class GraceRatingScale(Document):
    def validate(self):
        if self.is_default:
            frappe.db.sql(
                "UPDATE `tabGrace Rating Scale` SET is_default=0 WHERE name != %s",
                self.name
            )
