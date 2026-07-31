import frappe
from frappe.model.document import Document


class PMSBusinessGoal(Document):
    def validate(self):
        self._validate_weights()
        if self.is_review_draft:
            return  # draft clones skip live validation
        if self.status == "Active" and not self.kpis and self.goal_type == "Quantitative":
            frappe.msgprint("Quantitative goals should have at least one KPI defined.", alert=True)

    def _validate_weights(self):
        if not self.employee or not self.cycle:
            return
        peers = frappe.get_all(
            "PMS Business Goal",
            filters={
                "employee": self.employee,
                "cycle": self.cycle,
                "is_review_draft": 0,
                "status": ["not in", ["Cancelled"]],
                "name": ["!=", self.name or ""],
            },
            pluck="weight",
        )
        total = sum(peers) + (self.weight or 0)
        if total > 100:
            frappe.throw(f"Total goal weight cannot exceed 100%. Current total would be {total:.0f}%.")
