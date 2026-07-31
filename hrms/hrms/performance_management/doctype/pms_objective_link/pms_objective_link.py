import frappe
from frappe.model.document import Document


class PMSObjectiveLink(Document):
    def validate(self):
        if self.parent_goal == self.child_goal:
            frappe.throw("Parent and child goal cannot be the same.")
