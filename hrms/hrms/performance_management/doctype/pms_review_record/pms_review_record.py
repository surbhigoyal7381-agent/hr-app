import frappe
from frappe.model.document import Document


class PMSReviewRecord(Document):
    def validate(self):
        self._guard_potential_rating_visibility()
        self._validate_dialogue_actions()

    def before_save(self):
        self._append_version_trail()

    def _guard_potential_rating_visibility(self):
        if frappe.session.user == "Guest":
            return
        employee_user = frappe.db.get_value("Employee", self.employee, "user_id")
        if frappe.session.user == employee_user and not self.overall_rating_visible_to_employee:
            # strip potential rating from employee-facing saves
            self.potential_rating = None

    def _validate_dialogue_actions(self):
        if self.status == "Dialogue Complete" and not self.dialogue_actions:
            frappe.throw("At least one action item is required before marking dialogue complete.")

    def _append_version_trail(self):
        import json
        trail = json.loads(self.version_trail or "[]")
        trail.append({
            "ts": frappe.utils.now(),
            "user": frappe.session.user,
            "status": self.status,
        })
        self.version_trail = json.dumps(trail)
