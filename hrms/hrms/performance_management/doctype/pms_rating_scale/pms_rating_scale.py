import frappe
from frappe.model.document import Document


class PMSRatingScale(Document):
    def validate(self):
        self._validate_level_count()
        self._validate_level_values()

    def _validate_level_count(self):
        if len(self.levels) != self.n_points:
            frappe.throw(
                f"You defined {self.n_points} points but provided {len(self.levels)} level rows. They must match."
            )

    def _validate_level_values(self):
        values = [int(l.level_value) for l in self.levels]
        if sorted(values) != list(range(1, self.n_points + 1)):
            frappe.throw("Level values must be consecutive integers from 1 to n_points.")
