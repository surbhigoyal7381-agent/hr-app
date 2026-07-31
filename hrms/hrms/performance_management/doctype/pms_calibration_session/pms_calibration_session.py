import frappe
from frappe.model.document import Document


class PMSCalibrationSession(Document):
    def on_update(self):
        if self.status == "Locked" and not self.locked_on:
            self.locked_on = frappe.utils.now()
            self.db_set("locked_on", self.locked_on)
            self._apply_adjustments()

    def _apply_adjustments(self):
        for row in self.adjustments or []:
            if not row.review_record:
                continue
            frappe.db.set_value(
                "PMS Review Record",
                row.review_record,
                {
                    "calibrated_rating": row.calibrated_rating,
                    "calibration_session": self.name,
                    "status": "Calibrated",
                },
            )
        frappe.db.commit()
