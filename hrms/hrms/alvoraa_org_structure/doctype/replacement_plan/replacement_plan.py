"""A replacement plan: HR's private note that the person in a seat may need replacing.

Every rule lives here, so the portal, the desk and REST behave the same
(slice 065, SEC-5). Who may see a plan at all is decided in one place,
`hrms.alvoraa_org_structure.plans` (SEC-1).
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

import hrms.alvoraa_org_structure.plans as plans


class ReplacementPlan(Document):
	# Frappe writes a "Deleted" comment naming the record and its creator on
	# every delete unless this is set. That comment would outlive the erase.
	no_feed_on_delete = True

	def validate(self):
		note = self.note or ""
		if len(note) > plans.NOTE_MAX:
			frappe.throw(
				_("The note can be at most {0} characters. Shorten it and save again.").format(plans.NOTE_MAX)
			)

		today = nowdate()
		if self.is_new():
			self.confirmed_on = today
		elif self.has_value_changed("confirmed_on") and str(self.confirmed_on) != today:
			# Moving the date forward would stretch the 90 days; moving it back
			# would fake a confirmation. Only "confirm today" is a real action.
			frappe.throw(_("A plan can only be confirmed for today. Use Confirm for 90 more days."))

		plans.check_assignment(self.assignment)

	def on_trash(self):
		if not self.flags.get(plans.ERASE_FLAG):
			# Any other delete keeps a full copy in Deleted Document, note and all.
			frappe.throw(_("Use Remove the plan on the Positions page. It erases the plan completely."))
