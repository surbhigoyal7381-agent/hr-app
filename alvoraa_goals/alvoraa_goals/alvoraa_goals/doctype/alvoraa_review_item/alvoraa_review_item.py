from frappe.model.document import Document


class AlvoraaReviewItem(Document):
    """One review's own copy of an Objective or KPI.

    No logic here. Copies are made, counted and rated by
    alvoraa_goals.review_items, and the Extension refuses any other change.
    """

    pass
