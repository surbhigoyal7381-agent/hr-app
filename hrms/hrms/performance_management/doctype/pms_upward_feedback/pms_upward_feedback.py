import hashlib
import frappe
from frappe.model.document import Document


class PMSUpwardFeedback(Document):
    def before_insert(self):
        employee_id = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name") or frappe.session.user
        self.respondent_hash = hashlib.sha256(employee_id.encode()).hexdigest()
        self.submitted_on = frappe.utils.now()
