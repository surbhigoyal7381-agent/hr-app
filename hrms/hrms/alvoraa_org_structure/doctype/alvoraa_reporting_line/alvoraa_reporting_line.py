"""A dotted line: a second reporting relationship that is not part of the tree.

A regional manager who also answers to Finance. Deliberately NOT a second parent
on the position: nested sets assume one path to the root, and so does every
subtree count built on them. Put a matrix line in the tree and the counts start
lying.

So it lives here, is drawn over the tree, and nothing else reads it.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class AlvoraaReportingLine(Document):
	def validate(self):
		if self.from_position == self.to_position:
			frappe.throw(_("A position cannot have a dotted line to itself."))
		if self.from_date and self.to_date and str(self.to_date) < str(self.from_date):
			frappe.throw(_("This line ends before it starts."))

		# The solid line is already in the tree. Drawing it again as a dotted one
		# renders two lines between the same two boxes and tells a reader there
		# is a relationship that does not exist.
		if frappe.db.get_value("Alvoraa Position", self.from_position,
		                       "reports_to_position") == self.to_position:
			frappe.throw(
				_("{0} already reports to {1} on the solid line. A dotted line "
				  "as well would draw the same relationship twice.")
				.format(frappe.bold(self.from_position), frappe.bold(self.to_position)))
