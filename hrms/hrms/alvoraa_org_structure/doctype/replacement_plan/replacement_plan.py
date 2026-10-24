"""A replacement plan: HR's private note that the person in a seat may need replacing.

Every rule lives here, so the portal, the desk and REST behave the same
(slice 065, SEC-5). Who may see a plan at all is decided in one place,
`hrms.alvoraa_org_structure.plans` (SEC-1).
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, formatdate, getdate, nowdate

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
			self.check_improvement_period(today)
		else:
			if self.has_value_changed("confirmed_on") and str(self.confirmed_on) != today:
				# Moving the date forward would stretch the 90 days; moving it back
				# would fake a confirmation. Only "confirm today" is a real action.
				frappe.throw(_("A plan can only be confirmed for today. Use Confirm for 90 more days."))
			self.check_outcome(today)

		plans.check_assignment(self.assignment)

	def check_improvement_period(self, today):
		"""On create. The reason itself is checked by Frappe: it is required,
		and must be one of the field's options (the first option is blank, so
		nobody gets a reason by default). Reason and date are set once."""
		if self.not_improved_on or self.not_improved_by:
			frappe.throw(_("The outcome can only be recorded after the improvement period ends."))
		if self.reason != "Performance":
			if self.improvement_ends_on:
				frappe.throw(_("An improvement period is only set when the reason is Performance."))
			return
		first, last = getdate(add_days(today, 30)), getdate(add_days(today, 60))
		if not self.improvement_ends_on or not (first <= getdate(self.improvement_ends_on) <= last):
			frappe.throw(
				_("Choose an end date for the improvement period between {0} and {1}.").format(
					formatdate(first), formatdate(last)
				)
			)

	def check_outcome(self, today):
		""""Not improved" is written by `plans.record_outcome` only. The flag
		it sets cannot come from a request: Frappe drops a `flags` key sent
		through REST or set_value."""
		if not (self.has_value_changed("not_improved_on") or self.has_value_changed("not_improved_by")):
			return
		before = self.get_doc_before_save()
		if not (
			self.flags.get(plans.OUTCOME_FLAG)
			and not before.not_improved_on
			and not before.not_improved_by
			and self.reason == "Performance"
			and self.improvement_ends_on
			and str(self.improvement_ends_on) <= today
			and str(self.not_improved_on) == today
			and self.not_improved_by == frappe.session.user
		):
			frappe.throw(_("The outcome can only be recorded with Not improved on the Positions page."))

	def on_trash(self):
		if not self.flags.get(plans.ERASE_FLAG):
			# Any other delete keeps a full copy in Deleted Document, note and all.
			frappe.throw(_("Use Remove the plan on the Positions page. It erases the plan completely."))
