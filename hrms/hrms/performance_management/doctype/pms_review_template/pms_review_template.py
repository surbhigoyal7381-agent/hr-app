import frappe
import json
from frappe.model.document import Document


class PMSReviewTemplate(Document):
    def before_save(self):
        if self.status == "Active" and not self.is_new():
            # Copy-on-modify: creating a new version preserves the active one
            existing = frappe.get_doc("PMS Review Template", self.name)
            if existing.status == "Active":
                self._create_new_version()
                frappe.throw(
                    "The active template has been versioned. A new draft has been created. "
                    "Please activate the new version when ready.",
                    title="Template Versioned",
                )

    def _create_new_version(self):
        new_tmpl = frappe.copy_doc(self)
        new_tmpl.version = (self.version or 1) + 1
        new_tmpl.status = "Draft"
        new_tmpl.parent_template = self.name
        new_tmpl.save(ignore_permissions=True)

    def as_snapshot(self):
        """Return a JSON snapshot for embedding in PMS Cycle."""
        return json.dumps(self.as_dict(), default=str)

    def validate(self):
        if self.include_past_goals and self.past_goals_window_from and self.past_goals_window_to:
            if self.past_goals_window_from > self.past_goals_window_to:
                frappe.throw("Past Goals Window: From date must be before To date.")
        if self.additional_managers_enabled and not self.additional_managers_max:
            self.additional_managers_max = 2
