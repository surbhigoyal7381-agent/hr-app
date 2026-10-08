# Copyright (c) 2026, Alvoraa and contributors
# For license information, please see license.txt

"""One step of a sales journey (slice 057): lead type + status -> a CRM Task.

Checked when it is saved, so a typo is caught by the person typing it and not
by a salesperson changing a status later. The work itself is in crm_steps.py.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from alvoraa_portal.crm_steps import LEAD_TYPE_FIELD

STATUS_DOCTYPE = {"CRM Lead": "CRM Lead Status", "CRM Deal": "CRM Deal Status"}


class AlvoraaCRMStepTask(Document):
	def validate(self):
		if "crm" not in frappe.get_installed_apps():
			frappe.throw(_("Frappe CRM is not installed on this site."))

		field = frappe.get_meta(self.applies_to).get_field(LEAD_TYPE_FIELD)
		if not field:
			frappe.throw(_("{0} has no Lead Type field yet. Add it in Customize Form first (see the set-up guide).")
				.format(self.applies_to))
		options = [o.strip() for o in (field.options or "").split("\n") if o.strip()]
		if self.lead_type not in options:
			frappe.throw(_("Lead type {0} is not one of the Lead Type options on {1}: {2}.")
				.format(frappe.bold(self.lead_type), self.applies_to, ", ".join(options)))

		if not frappe.db.exists(STATUS_DOCTYPE[self.applies_to], self.status):
			frappe.throw(_("There is no {0} called {1}. Check the spelling against the CRM's status list.")
				.format(STATUS_DOCTYPE[self.applies_to], frappe.bold(self.status)))

		if not frappe.db.get_value("User", self.assign_to, "enabled"):
			frappe.throw(_("User {0} is disabled. Choose someone who can log in.").format(self.assign_to))

		if (self.due_in_days or 0) < 0:
			frappe.throw(_("Due in days cannot be negative. Use 0 for today."))
