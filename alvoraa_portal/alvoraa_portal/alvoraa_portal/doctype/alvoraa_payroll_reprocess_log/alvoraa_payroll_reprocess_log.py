import frappe  # noqa: F401
from frappe.model.document import Document


class AlvoraaPayrollReprocessLog(Document):
	"""Read-only by design: it is the record that a pay change happened,
	and a record somebody can edit afterwards is not a record."""

	def on_trash(self):
		frappe.throw("A reprocess log is the trail behind a change to pay. "
		             "It cannot be deleted.")
