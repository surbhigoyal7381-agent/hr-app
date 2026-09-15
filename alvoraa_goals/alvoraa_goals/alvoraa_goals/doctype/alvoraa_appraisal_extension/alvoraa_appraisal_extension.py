import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr, flt, get_datetime, getdate

# Set on the document by alvoraa_goals.review_items, and only there. A desk or
# REST save cannot set document flags, so every other path is refused.
REVIEW_ITEMS_WRITE_FLAG = "alvoraa_review_items_write"

_NUMBER_TYPES = {"Float", "Percent", "Int", "Check", "Currency"}


class AlvoraaAppraisalExtension(Document):
    def before_validate(self):
        # before_validate, not validate: it runs even when a caller sets
        # flags.ignore_validate (frappe/model/document.py run_before_save_methods).
        self._refuse_direct_review_item_changes()

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

    def _refuse_direct_review_item_changes(self):
        """The review's copies change only through the review code (R1).

        The desk form shows them read-only, but the desk and /api/resource can
        still send a changed row. Without this, HR could edit a rating, a stamp
        or a number around every stage and stamp rule. No role is exempt.
        """
        if self.flags.get(REVIEW_ITEMS_WRITE_FLAG):
            return
        before = self.get_doc_before_save()
        if _review_item_snapshot(before) == _review_item_snapshot(self):
            return
        from hrms.alvoraa_hr_core.access import refuse

        refuse(
            _("Review items can only be changed from the review screens in the portal."),
            "R1",
            "Alvoraa Appraisal Extension save",
            self.doctype,
            self.name,
        )


def _review_item_snapshot(doc):
    """Comparable form of the review_items table: row name -> field values."""
    if not doc:
        return {}
    meta = frappe.get_meta("Alvoraa Review Item")
    fields = [df for df in meta.fields if df.fieldtype not in ("Section Break", "Column Break", "Tab Break")]
    out = {}
    for i, row in enumerate(doc.get("review_items") or []):
        values = []
        for df in fields:
            value = row.get(df.fieldname)
            if df.fieldtype in _NUMBER_TYPES:
                values.append(flt(value, 6))
            elif df.fieldtype == "Date":
                values.append(str(getdate(value)) if value else "")
            elif df.fieldtype == "Datetime":
                values.append(str(get_datetime(value)) if value else "")
            else:
                values.append(cstr(value))
        out[row.name or f"new-{i}"] = tuple(values)
    return out
