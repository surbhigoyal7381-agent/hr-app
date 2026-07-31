import frappe
from frappe.model.document import Document


class GraceAppraisalExtension(Document):
    def validate(self):
        if self.avg_potential_rating and self.avg_potential_rating > 0:
            v = self.avg_potential_rating
            if v <= 2:
                self.potential_category = "Low Potential"
            elif v <= 3:
                self.potential_category = "Moderate Potential"
            elif v <= 4:
                self.potential_category = "High Potential"
            else:
                self.potential_category = "Exceptional Potential"
