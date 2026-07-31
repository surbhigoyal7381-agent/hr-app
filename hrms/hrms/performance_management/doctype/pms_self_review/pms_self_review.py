import frappe
from frappe.model.document import Document


class PMSSelfReview(Document):
    def validate(self):
        if len(self.evidence or []) > 10:
            frappe.throw("Maximum 10 evidence attachments allowed per self-review.")

    def on_submit(self):
        self.submitted_on = frappe.utils.now()
        review = frappe.get_doc("PMS Review Record", self.review_record)
        review.self_review_submitted_on = self.submitted_on
        review.status = "Self Review Submitted"
        review.save(ignore_permissions=True)
