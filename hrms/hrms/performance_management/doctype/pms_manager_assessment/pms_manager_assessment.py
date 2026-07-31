import frappe
from frappe.model.document import Document


class PMSManagerAssessment(Document):
    def on_submit(self):
        self.submitted_on = frappe.utils.now()
        review = frappe.get_doc("PMS Review Record", self.review_record)
        review.status = "Manager Preparation"
        review.save(ignore_permissions=True)
